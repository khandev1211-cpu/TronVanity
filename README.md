# TRON Vanity Address Generator — GPU Node (`TronVanity`)

High-performance GPU service for TRON vanity address generation, supporting **simultaneous Prefix + Suffix matching** in a single GPU pass.

Designed to run on GPU instances (Vast.ai, AWS, local NVIDIA Windows/Linux GPUs) and communicate with your Main Brain VPS.

---

## ⚡ Key Features

1. **Simultaneous Prefix + Suffix GPU Matching:**
   Uses C++ OpenCL Profanity engine to search both prefix AND suffix simultaneously on the GPU in ~8-13 seconds.
2. **Dual Mode Operation:**
   - **Mode A (Automated Redis Queue Worker):** Automatically connects to your Main VPS Redis (`REDIS_HOST`) and listens to `gpu_queue` tasks.
   - **Mode B (REST API Service):** Authenticated FastAPI endpoints (`/generate`, `/status`, `/jobs`, `/health`).

---

## ⚙️ Configuration (`.env`)

Simply edit `.env` on your GPU node to point to your Main VPS IP or domain:

```env
# =========================================================
# VPS Connection (Main Brain VPS)
# =========================================================
# Replace with your Main VPS IP address, domain, or ngrok host
REDIS_HOST=your-main-vps-ip-or-domain.com
REDIS_PORT=6379
REDIS_PASSWORD=

# =========================================================
# GPU Server Configuration
# =========================================================
VANITY_API_KEY=your_secret_api_key_12345

# Path to Profanity / ProVanity binary
# On Linux / Vast.ai: /workspace/profanity.x64
# On Windows: C:\Users\CHAND COMPUTER\Desktop\Tron\tools\profanity_windows\windows\profanity.exe
PROFANITY_BINARY=/workspace/profanity.x64

# GPU Device Configuration
# 0 on Linux Vast.ai, 1 on Windows with integrated GPU
GPU_SKIP_DEVICE=0
PROVANITY_DEVICES=all

# Server bind address/port
HOST=0.0.0.0
PORT=8000
```

---

## 🚀 Quick Start

### 1. Install Dependencies:
```bash
pip3 install -r requirements.txt
```

### 2. Configure `.env`:
```bash
cp .env.example .env
nano .env  # Edit REDIS_HOST and PROFANITY_BINARY
```

### 3. Start the GPU Node:
```bash
chmod +x start.sh stop.sh status.sh
./start.sh
```

---

## 📊 Status & Management
- **Check Status:** `./status.sh`
- **Tail Logs:** `tail -f logs/server.log`
- **Stop Server:** `./stop.sh`
