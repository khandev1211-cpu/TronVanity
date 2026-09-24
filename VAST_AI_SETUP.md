# Vast.ai GPU Node Setup Guide for `TronVanity`

This guide details how to deploy and run the `TronVanity` GPU generation node on a [Vast.ai](https://vast.ai) Linux GPU instance.

---

## ⚡ Quick Copy-Paste Installation (No Compilation Needed)

The pre-compiled Linux 64-bit C++ OpenCL binary (`profanity.x64`) is already included inside this repository! 

Simply connect to your Vast.ai instance terminal and run these commands:

```bash
# 1. Update system packages
apt update && apt install -y python3 python3-pip git

# 2. Clone repository to /workspace
cd /workspace
git clone https://github.com/khandev1211-cpu/TronVanity.git
cd TronVanity

# 3. Install Python dependencies
pip3 install -r requirements.txt

# 4. Make scripts and C++ GPU binary executable
chmod +x profanity.x64 start.sh stop.sh status.sh

# 5. Create .env configuration (Replace YOUR_MAIN_VPS_IP with your VPS IP)
cat << 'EOF' > .env
REDIS_HOST=YOUR_MAIN_VPS_IP
REDIS_PORT=6379
REDIS_PASSWORD=
VANITY_API_KEY=your_secret_api_key_12345
PROFANITY_BINARY=/workspace/TronVanity/profanity.x64
GPU_SKIP_DEVICE=0
PROVANITY_DEVICES=all
HOST=0.0.0.0
PORT=8000
MAX_RUNTIME_SECONDS=259200
PROVANITY_TIMEOUT_SECONDS=3600
LOG_LEVEL=INFO
MAX_JOBS_HISTORY=500
EOF

# 6. Start the GPU Worker Node in background
./start.sh
```

---

## 📊 Management Commands

- **Check Live Status:**
  ```bash
  ./status.sh
  ```
- **View Output Logs:**
  ```bash
  tail -f logs/server.log
  ```
- **Stop Node Worker:**
  ```bash
  ./stop.sh
  ```

---

## 🛠️ (Optional) Manual Compilation Instructions

If you ever wish to re-compile `profanity.x64` directly from C++ OpenCL source on Ubuntu:

```bash
# Install g++ and OpenCL development headers
apt install -y build-essential ocl-icd-opencl-dev opencl-headers

# Inside C++ source directory containing Makefile, compile binary:
make

# Move generated executable to TronVanity directory:
cp profanity.x64 /workspace/TronVanity/profanity.x64
chmod +x /workspace/TronVanity/profanity.x64
```
