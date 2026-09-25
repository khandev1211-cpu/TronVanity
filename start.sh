#!/usr/bin/env bash
# TronVanity Automated Setup & Worker Launcher Script for Vast.ai / Linux GPU Instances
set -e

echo "=================================================="
echo "🚀 TronVanity GPU Node Setup & Worker Launcher"
echo "=================================================="

echo "[1/4] Pulling latest code from GitHub..."
git reset --hard
git pull origin main

echo "[2/4] Installing Python requirements..."
pip install -q -r requirements.txt || pip install -q fastapi uvicorn redis pydantic requests python-dotenv

echo "[3/4] Building native OpenCL C++ binary (profanity.x64)..."
chmod +x build.sh
./build.sh

echo "[4/4] Configuring environment (.env)..."
if [ ! -f .env ]; then
    cat << 'EOF' > .env
REDIS_HOST=167.172.140.20
REDIS_PORT=6379
REDIS_PASSWORD=
PROFANITY_BINARY=/workspace/TronVanity/profanity.x64
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
EOF
    echo "[OK] Created default .env configured for Main VPS Redis (167.172.140.20)"
fi

echo "=================================================="
echo "✅ SETUP COMPLETE! Starting GPU Redis Worker..."
echo "=================================================="

python3 run.py
