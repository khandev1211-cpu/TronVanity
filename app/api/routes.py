"""
Route handlers for job submission, status polling, listing, and cancellation.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.logging_config import logger
from app.api.auth import verify_api_key
from app.models.schemas import (
    GenerateRequest,
    GenerateResponse,
    JobStatus,
    HealthResponse,
)
from app.services.job_store import job_store
from app.services.worker import start_job_thread

router = APIRouter()


@router.post(
    "/generate",
    response_model=GenerateResponse,
    dependencies=[Depends(verify_api_key)],
    status_code=status.HTTP_201_CREATED,
)
def generate(req: GenerateRequest):
    """Start a new vanity address generation job. Returns immediately with a job_id."""
    job_id = str(uuid.uuid4())
    job = job_store.create(job_id, req.prefix, req.suffix, req.case_insensitive)
    start_job_thread(job_id, req.prefix, req.suffix, req.case_insensitive)
    logger.info(f"Accepted new job {job_id}: prefix={req.prefix!r} suffix={req.suffix!r}")
    return GenerateResponse(job_id=job_id, status=job["status"])


@router.get(
    "/status/{job_id}",
    response_model=JobStatus,
    dependencies=[Depends(verify_api_key)],
)
def get_status(job_id: str):
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


@router.get(
    "/jobs",
    response_model=list[JobStatus],
    dependencies=[Depends(verify_api_key)],
)
def list_jobs():
    """Debug/admin endpoint: list all known jobs, most recent first."""
    jobs = job_store.list_all()
    jobs.sort(key=lambda j: j["created_at"], reverse=True)
    return jobs[: settings.max_jobs_history]


@router.delete(
    "/jobs/{job_id}",
    dependencies=[Depends(verify_api_key)],
)
def cancel_job(job_id: str):
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job["status"] not in ("queued", "running"):
        raise HTTPException(
            status_code=400,
            detail=f"Job '{job_id}' is already {job['status']}, cannot cancel",
        )
    from datetime import datetime, timezone
    job_store.update(job_id, status="cancelled", finished_at=datetime.now(timezone.utc).isoformat())
    logger.info(f"Job {job_id} cancelled by client request")
    return {"job_id": job_id, "status": "cancelled"}


@router.get("/health", response_model=HealthResponse)
def health():
    """Unauthenticated health check — safe to expose for uptime monitoring."""
    import os
    active = sum(1 for j in job_store.list_all() if j["status"] in ("queued", "running"))
    return HealthResponse(
        status="ok",
        provanity_binary_found=os.path.exists(settings.provanity_binary),
        active_jobs=active,
    )
