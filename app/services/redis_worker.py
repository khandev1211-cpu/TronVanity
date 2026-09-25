"""
Redis Queue Worker: Automatically connects to main VPS Redis (REDIS_HOST)
and processes vanity generation tasks directly from 'gpu_queue'.
Supports simultaneous Prefix + Suffix matching on GPU.
"""

import time
import json
import threading
import redis
from datetime import datetime

from app.core.config import settings
from app.core.logging_config import logger
from app.services import provanity


def start_redis_worker_thread():
    if not settings.redis_host:
        logger.info("REDIS_HOST not set. Skipping Redis queue worker.")
        return None

    def worker_loop():
        logger.info(f"Connecting to VPS Redis at {settings.redis_host}:{settings.redis_port}...")
        while True:
            try:
                r = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    password=settings.redis_password or None,
                    protocol=2,
                    decode_responses=True,
                    socket_timeout=None,
                    socket_keepalive=True,
                    retry_on_timeout=True
                )
                r.ping()
                logger.info(f"[OK] Connected to VPS Redis ({settings.redis_host}). Listening to 'gpu_queue'...")

                while True:
                    task_data = r.brpop("gpu_queue", timeout=10)
                    if task_data is None:
                        continue

                    task = json.loads(task_data[1])
                    pattern = task.get('pattern', '')
                    logger.info(f"[TASK] Received task from VPS Redis: {pattern}")

                    r.set(f"mine_status:{pattern}", "mining")
                    r.set(f"mine_mode:{pattern}", f"Vast.ai GPU Node ({settings.redis_host})")

                    if '*' in pattern:
                        parts = pattern.split('*')
                    elif '...' in pattern:
                        parts = pattern.split('...')
                    else:
                        parts = [pattern[:3], pattern[-3:]]

                    raw_prefix = parts[0][1:] if parts[0].startswith('T') else parts[0]
                    raw_suffix = parts[1] if len(parts) > 1 else ""

                    # Supports up to 6 characters prefix and suffix
                    prefix = raw_prefix[:6]
                    suffix = raw_suffix[-6:] if len(raw_suffix) >= 6 else raw_suffix

                    logger.info(f"[EXEC] Generating pattern on GPU: Prefix='{prefix}' (from {raw_prefix}), Suffix='{suffix}' (from {raw_suffix})")

                    res = provanity.run_once(prefix=prefix, suffix=suffix)

                    if res and res.address and res.private_key:
                        result_payload = {
                            "address": res.address,
                            "private_key": res.private_key,
                            "time": datetime.now().strftime("%H:%M:%S")
                        }
                        r.set(f"mine_result:{pattern}", json.dumps(result_payload))
                        r.set(f"mine_status:{pattern}", "completed")
                        logger.info(f"[SUCCESS] Sync'd match to VPS Redis -> {res.address}")
                    else:
                        r.set(f"mine_status:{pattern}", "error")
                        logger.error(f"[ERROR] Failed to find match for {pattern}")

            except Exception as e:
                logger.error(f"Redis Worker Connection Error: {e}. Retrying in 5s...")
                time.sleep(5)

    t = threading.Thread(target=worker_loop, daemon=True, name="vps-redis-worker")
    t.start()
    return t
