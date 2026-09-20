"""
Thread-safe in-memory job registry with disk persistence (one JSON file
per job, so jobs survive a server restart and can be inspected directly).
"""

import json
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging_config import logger
from app.models.schemas import JobStatusEnum


class JobStore:
    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._load_from_disk()

    def _job_path(self, job_id: str) -> Path:
        return settings.jobs_dir / f"{job_id}.json"

    def _load_from_disk(self):
        """On startup, reload any jobs that were left running/queued and
        mark them as errored (since their worker threads are gone)."""
        loaded = 0
        for path in settings.jobs_dir.glob("*.json"):
            try:
                with open(path) as f:
                    job = json.load(f)
                if job.get("status") in (JobStatusEnum.QUEUED, JobStatusEnum.RUNNING):
                    job["status"] = JobStatusEnum.ERROR
                    job["error"] = "Server restarted while this job was in progress"
                    job["finished_at"] = datetime.now(timezone.utc).isoformat()
                self._jobs[job["job_id"]] = job
                loaded += 1
            except (json.JSONDecodeError, KeyError, OSError) as e:
                logger.warning(f"Skipping corrupt job file {path}: {e}")
        if loaded:
            logger.info(f"Loaded {loaded} job(s) from disk")

    def create(self, job_id: str, prefix: str, suffix: str, case_insensitive: bool) -> dict:
        job = {
            "job_id": job_id,
            "status": JobStatusEnum.QUEUED,
            "prefix": prefix,
            "suffix": suffix,
            "case_insensitive": case_insensitive,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "attempts_total": 0,
            "elapsed_seconds": 0.0,
            "result": None,
            "error": None,
        }
        with self._lock:
            self._jobs[job_id] = job
        self._save(job_id)
        return job

    def get(self, job_id: str) -> Optional[dict]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def update(self, job_id: str, **fields) -> Optional[dict]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.update(fields)
        self._save(job_id)
        return job

    def list_all(self) -> list[dict]:
        with self._lock:
            return list(self._jobs.values())

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return job is not None and job["status"] == JobStatusEnum.CANCELLED

    def _save(self, job_id: str):
        job = self.get(job_id)
        if job is None:
            return
        try:
            tmp_path = self._job_path(job_id).with_suffix(".tmp")
            with open(tmp_path, "w") as f:
                json.dump(job, f, indent=2, default=str)
            tmp_path.replace(self._job_path(job_id))  # atomic on POSIX
        except OSError as e:
            logger.error(f"Failed to persist job {job_id} to disk: {e}")


job_store = JobStore()
