"""
Background worker: runs ProVanity repeatedly (matching only the suffix,
since that's all ProVanity's generate-tron supports natively), verifies
the prefix in Python, and keeps going until both match or the job is
cancelled / times out / hits too many consecutive failures.
"""

import time
import threading
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging_config import logger
from app.services import provanity
from app.services.job_store import job_store
from app.models.schemas import JobStatusEnum

MAX_CONSECUTIVE_FAILURES = 10


def run_job(job_id: str, prefix: str, suffix: str, case_insensitive: bool):
    job_store.update(job_id, status=JobStatusEnum.RUNNING)
    logger.info(f"Job {job_id} started: prefix={prefix!r} suffix={suffix!r} "
                f"case_insensitive={case_insensitive}")

    start = time.time()
    total_attempts = 0
    consecutive_failures = 0

    while True:
        if job_store.is_cancelled(job_id):
            logger.info(f"Job {job_id} cancelled by user")
            return

        elapsed = time.time() - start
        if elapsed > settings.max_runtime_seconds:
            job_store.update(
                job_id,
                status=JobStatusEnum.ERROR,
                error=f"Exceeded max runtime of {settings.max_runtime_seconds}s without finding a match",
                finished_at=datetime.now(timezone.utc).isoformat(),
                elapsed_seconds=elapsed,
            )
            logger.warning(f"Job {job_id} exceeded max runtime, giving up")
            return

        try:
            result = provanity.run_once(suffix=suffix)
            consecutive_failures = 0
        except provanity.ProVanityError as e:
            consecutive_failures += 1
            logger.error(f"Job {job_id}: ProVanity run failed ({consecutive_failures}/"
                         f"{MAX_CONSECUTIVE_FAILURES}): {e}")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                job_store.update(
                    job_id,
                    status=JobStatusEnum.ERROR,
                    error=f"ProVanity failed {MAX_CONSECUTIVE_FAILURES} times in a row: {e}",
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    elapsed_seconds=time.time() - start,
                )
                return
            time.sleep(min(2 ** consecutive_failures, 30))  # exponential backoff
            continue

        total_attempts += result.attempts
        elapsed = time.time() - start

        job_store.update(job_id, attempts_total=total_attempts, elapsed_seconds=elapsed)

        prefix_ok = provanity.check_prefix(result.address, prefix, case_insensitive)
        suffix_ok = provanity.check_suffix(result.address, suffix, case_insensitive)

        if prefix_ok and suffix_ok:
            job_store.update(
                job_id,
                status=JobStatusEnum.DONE,
                finished_at=datetime.now(timezone.utc).isoformat(),
                result={
                    "address": result.address,
                    "private_key": result.private_key,
                    "offset": result.offset,
                },
            )
            logger.info(f"Job {job_id} DONE: address={result.address} "
                        f"(total_attempts={total_attempts:,}, elapsed={elapsed:.1f}s)")
            return
        else:
            # Suffix matched (ProVanity guarantees this) but prefix didn't --
            # this is expected and normal, just keep looping.
            logger.debug(f"Job {job_id}: suffix ok, prefix mismatch on {result.address}, retrying")


def start_job_thread(job_id: str, prefix: str, suffix: str, case_insensitive: bool) -> threading.Thread:
    t = threading.Thread(
        target=run_job,
        args=(job_id, prefix, suffix, case_insensitive),
        daemon=True,
        name=f"job-{job_id[:8]}",
    )
    t.start()
    return t
