#!/usr/bin/env python3
"""
Entrypoint script. Run this directly: python3 run.py
Config is validated (app.core.config) before the server starts, so
misconfiguration fails fast with a clear message instead of starting
a broken server.
"""

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_config=None,  # we handle our own logging (app.core.logging_config)
    )
