#!/usr/bin/env bash
# Quick status check: is the process alive, and does the API respond?
set -euo pipefail
cd "$(dirname "$0")"

if [ -f server.pid ] && kill -0 "$(cat server.pid)" 2>/dev/null; then
    echo "Process: RUNNING (PID $(cat server.pid))"
else
    echo "Process: NOT RUNNING"
fi

PORT=$(grep -E '^PORT=' .env 2>/dev/null | cut -d= -f2 || echo 8000)
echo ""
echo "Health check:"
curl -sf "http://localhost:${PORT}/health" | python3 -m json.tool || echo "  (no response)"
