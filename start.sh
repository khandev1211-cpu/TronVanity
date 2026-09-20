#!/usr/bin/env bash
# Starts the server in the background, validating config first.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "ERROR: .env not found."
    echo "Run: cp .env.example .env   then edit it and set VANITY_API_KEY."
    exit 1
fi

if [ -f server.pid ] && kill -0 "$(cat server.pid)" 2>/dev/null; then
    echo "Server already running (PID $(cat server.pid)). Run ./stop.sh first if you want to restart."
    exit 1
fi

echo "Validating configuration and starting server..."
nohup python3 run.py > /dev/null 2>&1 &
PID=$!
echo $PID > server.pid

# Give it a moment to either come up or crash on config validation
sleep 2

if ! kill -0 "$PID" 2>/dev/null; then
    echo ""
    echo "ERROR: server failed to start. Check logs/server.log for details."
    rm -f server.pid
    exit 1
fi

echo "Server started (PID $PID)."
echo "Logs: tail -f $(pwd)/logs/server.log"
echo ""
echo "Checking health endpoint..."
sleep 1
PORT=$(grep -E '^PORT=' .env | cut -d= -f2 || echo 8000)
curl -sf "http://localhost:${PORT}/health" && echo "" || echo "(health check did not respond yet — check logs)"
