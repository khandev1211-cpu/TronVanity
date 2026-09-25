#!/usr/bin/env bash
# Automatically builds native Linux 64-bit OpenCL C++ binary profanity.x64
set -e

echo "[*] Installing OpenCL & libcurl development libraries..."
apt update -qq && apt install -y -qq build-essential ocl-icd-opencl-dev opencl-headers libcurl4-openssl-dev > /dev/null 2>&1 || true

echo "[*] Cleaning old OpenCL binary cache and object files..."
rm -f cache-opencl* src/*.o profanity.x64

echo "[*] Compiling native Linux OpenCL C++ binary..."
cd "$(dirname "$0")/src"

g++ -c -std=c++11 -Wall -mmmx -O2 -mcmodel=large Dispatcher.cpp -o Dispatcher.o
g++ -c -std=c++11 -Wall -mmmx -O2 -mcmodel=large Mode.cpp -o Mode.o
g++ -c -std=c++11 -Wall -mmmx -O2 -mcmodel=large precomp.cpp -o precomp.o
g++ -c -std=c++11 -Wall -mmmx -O2 -mcmodel=large profanity.cpp -o profanity.o
g++ -c -std=c++11 -Wall -mmmx -O2 -mcmodel=large SpeedSample.cpp -o SpeedSample.o

g++ Dispatcher.o Mode.o precomp.o profanity.o SpeedSample.o -s -lOpenCL -lcurl -mcmodel=large -o profanity.x64

if [ -f profanity.x64 ]; then
    mv profanity.x64 ../profanity.x64
    chmod +x ../profanity.x64
    echo "[✅ SUCCESS] Native Linux binary 'profanity.x64' compiled successfully!"
else
    echo "[❌ ERROR] Compilation failed."
    exit 1
fi
