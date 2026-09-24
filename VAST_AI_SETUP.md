# Vast.ai GPU Node Setup Guide for `TronVanity`

This guide details how to deploy and run the `TronVanity` GPU generation node on a [Vast.ai](https://vast.ai) Linux GPU instance.

---

## 📋 Prerequisites

- A Vast.ai account with available credits.
- Your Main VPS IP address or domain (where Redis is running).
- SSH client or Vast.ai Web Terminal access.

---

## 1. Select & Rent a Vast.ai Instance

1. Log in to **Vast.ai Console** and go to **Create Instance**.
2. Filter for GPU instances:
   - **Recommended GPUs:** RTX 3080, RTX 3090, RTX 4080, RTX 4090, or GTX 1080/2080.
   - **Image/Template:** Standard `Ubuntu 22.04` or `PyTorch` image (includes NVIDIA CUDA/OpenCL drivers).
   - **Disk Space:** Allocate at least 10–20 GB.
3. Click **Rent** and wait for the instance to transition to `Running`.

---

## 2. Connect & Clone the Repository

Connect to your Vast.ai instance via SSH or Web Terminal and run:

```bash
# Update system packages and install python/git
apt update && apt install -y python3 python3-pip git wget

# Navigate to working directory
cd /workspace

# Clone TronVanity repository
git clone https://github.com/khandev1211-cpu/TronVanity.git
cd TronVanity

# Install Python dependencies
pip3 install -r requirements.txt
```

---

## 3. Verify / Compile the C++ GPU Binary

Ensure the C++ OpenCL binary `profanity.x64` is executable:

```bash
chmod +x profanity.x64 start.sh stop.sh status.sh
```

*(If compiling from C++ source is required, run `make` inside the C++ source directory to produce `profanity.x64`).*

---

## 4. Configure Environment (`.env`)

Create the `.env` configuration file on your Vast.ai instance:

```bash
cp .env.example .env
nano .env
```

Set the following parameters in `.env`:

```env
# =========================================================
# VPS Redis Connection
# =========================================================
# Set this to your Main VPS Public IP address
REDIS_HOST=YOUR_MAIN_VPS_IP
REDIS_PORT=6379
REDIS_PASSWORD=

# =========================================================
# GPU Node Settings
# =========================================================
VANITY_API_KEY=your_secret_api_key_12345
PROFANITY_BINARY=/workspace/TronVanity/profanity.x64

# OpenCL Device configuration (0 for standard Linux single GPU)
GPU_SKIP_DEVICE=0
PROVANITY_DEVICES=all

# Server & Timeout parameters
HOST=0.0.0.0
PORT=8000
MAX_RUNTIME_SECONDS=259200
PROVANITY_TIMEOUT_SECONDS=3600
LOG_LEVEL=INFO
```

---

## 5. Launch & Manage the Node

Start the background service using the included shell scripts:

### Start Node
```bash
./start.sh
```

### Check Status
```bash
./status.sh
```

### View Live Output Logs
```bash
tail -f logs/server.log
```

### Stop Node
```bash
./stop.sh
```

---

## 6. Verification

Upon starting, `logs/server.log` should display:

```text
TRON Vanity Address Generator API starting up
VPS Redis Queue Worker Target: YOUR_MAIN_VPS_IP:6379
Connecting to VPS Redis at YOUR_MAIN_VPS_IP:6379...
[OK] Connected to VPS Redis (YOUR_MAIN_VPS_IP). Listening to 'gpu_queue'...
```

The Vast.ai GPU node is now active and ready to process incoming generation tasks from your Main VPS Redis queue.
