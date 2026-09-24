#include <algorithm>
#include <stdexcept>
#include <iostream>
#include <fstream>
#include <sstream>
#include <cstdlib>
#include <cstdio>
#include <vector>
#include <map>
#include <set>

#if defined(__APPLE__) || defined(__MACOSX)
#include <OpenCL/cl.h>
#include <OpenCL/cl_ext.h> // Included to get topology to get an actual unique identifier per device
#else
#include <CL/cl.h>
#include <CL/cl_ext.h> // Included to get topology to get an actual unique identifier per device
#endif

#define CL_DEVICE_PCI_BUS_ID_NV 0x4008
#define CL_DEVICE_PCI_SLOT_ID_NV 0x4009

#include "Dispatcher.hpp"
#include "ArgParser.hpp"
#include "Mode.hpp"
#include "help.hpp"
#include "kernel_profanity.hpp"
#include "kernel_sha256.hpp"
#include "kernel_keccak.hpp"

std::string readFile(const char *const szFilename)
{
	std::ifstream in(szFilename, std::ios::in | std::ios::binary);
	std::ostringstream contents;
	contents << in.rdbuf();
	return contents.str();
}

std::vector<cl_device_id> getAllDevices(cl_device_type deviceType = CL_DEVICE_TYPE_GPU)
{
	std::vector<cl_device_id> vDevices;

	cl_uint platformIdCount = 0;
	clGetPlatformIDs(0, NULL, &platformIdCount);

	std::vector<cl_platform_id> platformIds(platformIdCount);
	clGetPlatformIDs(platformIdCount, platformIds.data(), NULL);

	for (auto it = platformIds.cbegin(); it != platformIds.cend(); ++it)
	{
		cl_uint countDevice = 0;
		if (clGetDeviceIDs(*it, deviceType, 0, NULL, &countDevice) == CL_SUCCESS && countDevice > 0)
		{
			std::vector<cl_device_id> deviceIds(countDevice);
			if (clGetDeviceIDs(*it, deviceType, countDevice, deviceIds.data(), &countDevice) == CL_SUCCESS)
			{
				std::copy(deviceIds.begin(), deviceIds.end(), std::back_inserter(vDevices));
			}
		}
	}

	return vDevices;
}

template <typename T, typename U, typename V, typename W>
T clGetWrapper(U function, V param, W param2)
{
	T t;
	function(param, param2, sizeof(t), &t, NULL);
	return t;
}

template <typename U, typename V, typename W>
std::string clGetWrapperString(U function, V param, W param2)
{
	size_t len = 0;
	if (function(param, param2, 0, NULL, &len) != CL_SUCCESS || len == 0) {
		return "";
	}
	char *const szString = new char[len];
	function(param, param2, len, szString, NULL);
	std::string r(szString);
	delete[] szString;
	return r;
}

template <typename T, typename U, typename V, typename W>
std::vector<T> clGetWrapperVector(U function, V param, W param2)
{
	size_t len;
	function(param, param2, 0, NULL, &len);
	len /= sizeof(T);
	std::vector<T> v;
	if (len > 0)
	{
		T *pArray = new T[len];
		function(param, param2, len * sizeof(T), pArray, NULL);
		for (size_t i = 0; i < len; ++i)
		{
			v.push_back(pArray[i]);
		}
		delete[] pArray;
	}
	return v;
}

std::vector<std::string> getBinaries(cl_program &clProgram)
{
	std::vector<std::string> vReturn;
	auto vSizes = clGetWrapperVector<size_t>(clGetProgramInfo, clProgram, CL_PROGRAM_BINARY_SIZES);
	if (!vSizes.empty())
	{
		unsigned char **pBuffers = new unsigned char *[vSizes.size()];
		for (size_t i = 0; i < vSizes.size(); ++i)
		{
			pBuffers[i] = new unsigned char[vSizes[i]];
		}

		clGetProgramInfo(clProgram, CL_PROGRAM_BINARIES, vSizes.size() * sizeof(unsigned char *), pBuffers, NULL);
		for (size_t i = 0; i < vSizes.size(); ++i)
		{
			std::string strData(reinterpret_cast<char *>(pBuffers[i]), vSizes[i]);
			vReturn.push_back(strData);
			delete[] pBuffers[i];
		}
		delete[] pBuffers;
	}
	return vReturn;
}

void printResult(cl_int result)
{
	if (result == CL_SUCCESS)
	{
		std::cout << "OK" << std::endl;
	}
	else
	{
		std::cout << "    error: " << result << std::endl;
	}
}

bool printResult(cl_program program, cl_int result)
{
	if (result == CL_SUCCESS)
	{
		std::cout << "OK" << std::endl;
		return false;
	}
	else
	{
		std::cout << "    error: " << result << std::endl;

		size_t sizeBuildLog = 0;
		clGetProgramBuildInfo(program, NULL, CL_PROGRAM_BUILD_LOG, 0, NULL, &sizeBuildLog);

		char *szBuildLog = new char[sizeBuildLog + 1];

		clGetProgramBuildInfo(program, NULL, CL_PROGRAM_BUILD_LOG, sizeBuildLog, szBuildLog, NULL);
		szBuildLog[sizeBuildLog] = '\0';

		std::cout << "Build log:" << std::endl;
		std::cout << szBuildLog << std::endl;

		delete[] szBuildLog;

		return true;
	}
}

bool printResult(void *pNull, cl_int result)
{
	if (result == CL_SUCCESS)
	{
		std::cout << "OK" << std::endl;
		return false;
	}
	else
	{
		std::cout << "    error: " << result << std::endl;
		return true;
	}
}

std::string getDeviceCacheFilename(cl_device_id &deviceId, const size_t inverseSize)
{

	cl_device_type deviceType = clGetWrapper<cl_device_type>(clGetDeviceInfo, deviceId, CL_DEVICE_TYPE);
	std::string strVendor = clGetWrapperString(clGetDeviceInfo, deviceId, CL_DEVICE_VENDOR);
	std::string strName = clGetWrapperString(clGetDeviceInfo, deviceId, CL_DEVICE_NAME);
	std::string strDriver = clGetWrapperString(clGetDeviceInfo, deviceId, CL_DRIVER_VERSION);

	// Transform strVendor
	std::transform(strVendor.begin(), strVendor.end(), strVendor.begin(), ::tolower);
	strVendor.erase(std::remove_if(strVendor.begin(), strVendor.end(), [](char c)
								   { return !::isalnum(c); }),
					strVendor.end());

	// Transform strName
	std::transform(strName.begin(), strName.end(), strName.begin(), ::tolower);
	strName.erase(std::remove_if(strName.begin(), strName.end(), [](char c)
								 { return !::isalnum(c); }),
				  strName.end());

	// Transform strDriver
	std::transform(strDriver.begin(), strDriver.end(), strDriver.begin(), ::tolower);
	strDriver.erase(std::remove_if(strDriver.begin(), strDriver.end(), [](char c)
								   { return !::isalnum(c); }),
					strDriver.end());

	std::ostringstream ssFilename;
	ssFilename << "cache-opencl";
	ssFilename << "-" << strVendor;
	ssFilename << "-" << strName;
	ssFilename << "-" << strDriver;
	ssFilename << "-" << inverseSize;

	return ssFilename.str();
}

int main(int argc, char **argv)
{
	try
	{
		ArgParser argParser(argc, argv);

		bool bHelp = false;
		std::string matchingInput = "";
		int prefixCount = 0;
		int suffixCount = 0;
		int quitCount = 0;

		std::vector<size_t> vDeviceSkipIndex;
		std::string strOutput = "";
		std::string strPost = "";

		bool bNoCache = false;

		argParser.addSwitch('h', "help", bHelp);
		argParser.addSwitch('m', "matching", matchingInput);
		argParser.addSwitch('p', "prefix-count", prefixCount);
		argParser.addSwitch('s', "suffix-count", suffixCount);
		argParser.addSwitch('q', "quit-count", quitCount);
		argParser.addMultiSwitch('k', "skip", vDeviceSkipIndex);
		argParser.addSwitch('o', "output", strOutput);
		argParser.addSwitch('t', "post", strPost);
		argParser.addSwitch('n', "no-cache", bNoCache);

		if (!argParser.parse())
		{
			std::cout << "error: bad arguments, try again :<" << std::endl;
			return 1;
		}

		if (bHelp)
		{
			std::cout << g_strHelp << std::endl;
			return 0;
		}

		if (matchingInput.empty())
		{
			std::cout << "error: matching file must be specified :<" << std::endl;
			return 1;
		}

		if (prefixCount < 0)
		{
			prefixCount = 0;
		}

		if (prefixCount > 10)
		{
			std::cout << "error: the number of prefix matches cannot be greater than 10 :<" << std::endl;
			return 1;
		}

		if (suffixCount < 0)
		{
			suffixCount = 6;
		}

		if (suffixCount > 10)
		{
			std::cout << "error: the number of suffix matches cannot be greater than 10 :<" << std::endl;
			return 1;
		}

		Mode mode = Mode::matching(matchingInput);

		if (mode.matchingCount <= 0)
		{
			std::cout << "error: please check your matching file to make sure the path and format are correct :<" << std::endl;
			return 1;
		}

		mode.prefixCount = prefixCount;
		mode.suffixCount = suffixCount;

		std::vector<cl_device_id> vFoundDevices = getAllDevices();
		std::vector<cl_device_id> vDevices;
		std::map<cl_device_id, size_t> mDeviceIndex;

		std::vector<std::string> vDeviceBinary;
		std::vector<size_t> vDeviceBinarySize;
		cl_int errorCode;
		bool bUsedCache = false;

		std::cout << "Devices:" << std::endl;
		for (size_t i = 0; i < vFoundDevices.size(); ++i)
		{
			if (std::find(vDeviceSkipIndex.begin(), vDeviceSkipIndex.end(), i) != vDeviceSkipIndex.end())
			{
				continue;
			}
			cl_device_id &deviceId = vFoundDevices[i];

			const auto globalMemSize = clGetWrapper<cl_ulong>(clGetDeviceInfo, deviceId, CL_DEVICE_GLOBAL_MEM_SIZE);
			const auto strName = clGetWrapperString(clGetDeviceInfo, deviceId, CL_DEVICE_NAME);

			// Filter out invalid phantom/virtual devices that don't have enough VRAM or valid GPU names
			if (globalMemSize < 100 * 1024 * 1024 || strName.empty() || strName.length() < 3) {
				continue;
			}

			const auto computeUnits = clGetWrapper<cl_uint>(clGetDeviceInfo, deviceId, CL_DEVICE_MAX_COMPUTE_UNITS);
			bool precompiled = false;

			if (!bNoCache)
			{
				std::ifstream fileIn(getDeviceCacheFilename(deviceId, inverseSize), std::ios::binary);
				if (fileIn.is_open())
				{
					vDeviceBinary.push_back(std::string((std::istreambuf_iterator<char>(fileIn)), std::istreambuf_iterator<char>()));
					vDeviceBinarySize.push_back(vDeviceBinary.back().size());
					precompiled = true;
				}
			}

			std::cout << "  GPU-" << (vDevices.size() + 1) << ": " << strName << ", " << globalMemSize << " bytes available, " << computeUnits << " compute units (precompiled = " << (precompiled ? "yes" : "no") << ")" << std::endl;
			vDevices.push_back(deviceId);
			mDeviceIndex[deviceId] = vDevices.size() - 1;
		}

		if (vDevices.empty())
		{
			std::cout << "error: no valid GPU devices found!" << std::endl;
			return 1;
		}

		std::cout << std::endl;
		std::cout << "OpenCL:" << std::endl;
		std::cout << "  Context creating ..." << std::flush;
		auto clContext = clCreateContext(NULL, vDevices.size(), vDevices.data(), NULL, NULL, &errorCode);
		if (printResult(clContext, errorCode))
		{
			return 1;
		}

		cl_program clProgram;
		if (vDeviceBinary.size() == vDevices.size())
		{
			// Create program from binaries
			bUsedCache = true;

			std::cout << "  Binary kernel loading..." << std::flush;
			const unsigned char **pKernels = new const unsigned char *[vDevices.size()];
			for (size_t i = 0; i < vDeviceBinary.size(); ++i)
			{
				pKernels[i] = reinterpret_cast<const unsigned char *>(vDeviceBinary[i].data());
			}

			cl_int *pStatus = new cl_int[vDevices.size()];

			clProgram = clCreateProgramWithBinary(clContext, vDevices.size(), vDevices.data(), vDeviceBinarySize.data(), pKernels, pStatus, &errorCode);
			if (printResult(clProgram, errorCode))
			{
				return 1;
			}
		}
		else
		{
			// Create program from source
			std::cout << "  Compiling OpenCL kernel..." << std::flush;

			std::string strKernel = kernel_profanity + kernel_sha256 + kernel_keccak;

			const char *szKernel = strKernel.c_str();
			const size_t sizeKernel = strKernel.size();

			clProgram = clCreateProgramWithSource(clContext, 1, &szKernel, &sizeKernel, &errorCode);
			if (printResult(clProgram, errorCode))
			{
				return 1;
			}
		}

		std::cout << "  Building program..." << std::flush;
		const std::string strCompileFlags = "-I.";
		errorCode = clBuildProgram(clProgram, vDevices.size(), vDevices.data(), strCompileFlags.c_str(), NULL, NULL);
		if (printResult(clProgram, errorCode))
		{
			return 1;
		}

		// Save binary to cache if not loaded from cache
		if (!bNoCache && !bUsedCache)
		{
			auto vBinaries = getBinaries(clProgram);
			for (size_t i = 0; i < vDevices.size(); ++i)
			{
				std::ofstream fileOut(getDeviceCacheFilename(vDevices[i], inverseSize), std::ios::binary);
				if (fileOut.is_open())
				{
					fileOut.write(vBinaries[i].data(), vBinaries[i].size());
				}
			}
		}

		std::cout << std::endl;

		Dispatcher dispatcher(clContext, clProgram, mode, quitCount, strOutput, strPost);
		for (auto &deviceId : vDevices)
		{
			dispatcher.addDevice(deviceId, mDeviceIndex[deviceId], worksizeLocal, worksizeMax);
		}

		dispatcher.run();

		clReleaseProgram(clProgram);
		clReleaseContext(clContext);

		return 0;
	}
	catch (std::exception &e) {
		std::cout << "Exception: " << e.what() << std::endl;
		return 1;
	}
}
