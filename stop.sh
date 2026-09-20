#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f server.pid ]; then
    echo "No server.pid found — is the server running via start.sh?"
    exit 1
fi

PID=$(cat server.pid)
if kill "$PID" 2>/dev/null; then
    echo "Stopped server (PID $PID)"
else
    echo "Process $PID not found (already stopped?)"
fi
rm -f server.pid
