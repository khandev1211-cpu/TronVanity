"""
TRON Vanity Address Generator — GPU Server
============================================
FastAPI application entrypoint. Wires up routes, global exception
handlers, and startup/shutdown logging.

Run with:
    python3 run.py
or:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.logging_config import logger
from app.api.routes import router
from app.services.redis_worker import start_redis_worker_thread

app = FastAPI(
    title="TRON Vanity Address Generator API",
    description="Submit prefix/suffix patterns and poll for a matching TRON address + private key.",
    version="1.0.0",
)

app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Turn Pydantic validation errors into a clean, client-friendly response."""
    errors = [
        {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    logger.warning(f"Validation error on {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid request", "errors": errors},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all so an unexpected bug never leaks a raw stack trace to the client."""
    logger.exception(f"Unhandled exception on {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Check server logs for details."},
    )


@app.on_event("startup")
async def on_startup():
    logger.info("=" * 60)
    logger.info("TRON Vanity Address Generator API starting up")
    logger.info(f"Profanity/ProVanity binary: {settings.provanity_binary}")
    logger.info(f"Devices: {settings.devices}")
    logger.info(f"Listening on {settings.host}:{settings.port}")
    logger.info(f"Max job runtime: {settings.max_runtime_seconds}s")
    if settings.redis_host:
        logger.info(f"VPS Redis Queue Worker Target: {settings.redis_host}:{settings.redis_port}")
        start_redis_worker_thread()
    logger.info("=" * 60)


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Server shutting down")
