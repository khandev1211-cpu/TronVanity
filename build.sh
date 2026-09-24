#!/usr/bin/env bash
# Automatically builds native Linux 64-bit OpenCL C++ binary profanity.x64
set -e

echo "[*] Installing OpenCL & libcurl development libraries if missing..."
apt update -qq && apt install -y -qq build-essential ocl-icd-opencl-dev opencl-headers libcurl4-openssl-dev > /dev/null 2>&1 || true

echo "[*] Compiling native Linux OpenCL C++ binary inside src/..."
cd "$(dirname "$0")/src"
make clean > /dev/null 2>&1 || true
make

if [ -f profanity.x64 ]; then
    mv profanity.x64 ../profanity.x64
    chmod +x ../profanity.x64
    echo "[✅ SUCCESS] Native Linux binary 'profanity.x64' compiled successfully!"
else
    echo "[❌ ERROR] Compilation failed."
    exit 1
fi
