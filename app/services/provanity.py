"""
Wraps TRON Profanity GPU binaries as subprocesses.
Supports simultaneous 1-pass Prefix + Suffix matching via C++ OpenCL Profanity.
"""

import os
import re
import time
import subprocess
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings
from app.core.logging_config import logger


class ProVanityError(Exception):
    """Raised when GPU engine fails to run or produces unusable output."""
    pass


@dataclass
class ProVanityResult:
    address: str
    private_key: str
    offset: Optional[str] = None
    attempts: int = 0


_ADDRESS_RE = re.compile(r"address:\s*(\S+)", re.IGNORECASE)
_PRIVKEY_RE = re.compile(r"private key:\s*(\S+)", re.IGNORECASE)


def run_profanity_simultaneous(prefix: str = "", suffix: str = "") -> ProVanityResult:
    """
    Executes C++ OpenCL Profanity Engine with simultaneous Prefix and Suffix matching.
    Uses -b for prefix-count, -e for suffix-count, -q for quit-count, and -o for output file.
    """
    base58_pad = "123456789ABCDEFGHJKLMNPQRSTUV"
    pad_needed = 34 - 1 - len(prefix) - len(suffix)
    dummy_fill = base58_pad[:max(0, pad_needed)]
    target_address = f"T{prefix}{dummy_fill}{suffix}"

    result_file = f"res_{int(time.time())}.txt"
    if os.path.exists(result_file):
        try: os.remove(result_file)
        except: pass

    cmd = [
        settings.provanity_binary,
        "-m", target_address,
        "-b", str(len(prefix)),
        "-e", str(len(suffix)),
        "-q", "1",
        "-o", result_file
    ]

    logger.debug(f"Executing GPU Command: {' '.join(cmd)}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        start_t = time.time()
        while time.time() - start_t < settings.provanity_timeout_seconds:
            if os.path.exists(result_file) and os.path.getsize(result_file) > 10:
                with open(result_file, "r") as f:
                    content = f.read().strip()
                if "," in content:
                    pk, addr = content.split(",", 1)
                    proc.terminate()
                    try: os.remove(result_file)
                    except: pass
                    return ProVanityResult(address=addr.strip(), private_key=pk.strip())

            if proc.poll() is not None and not os.path.exists(result_file):
                out, _ = proc.communicate()
                raise ProVanityError(f"GPU process exited prematurely. Output: {out[-500:]!r}")

            time.sleep(0.5)

        proc.terminate()
        raise ProVanityError(f"GPU process timed out after {settings.provanity_timeout_seconds}s")

    except Exception as e:
        raise ProVanityError(f"GPU Execution Error: {e}")


def run_once(prefix: str = "", suffix: str = "", devices: Optional[str] = None) -> ProVanityResult:
    return run_profanity_simultaneous(prefix, suffix)


def check_prefix(address: str, prefix: str, case_insensitive: bool) -> bool:
    if not prefix:
        return True
    if len(address) <= len(prefix):
        return False
    addr_body = address[1:]
    candidate = addr_body[: len(prefix)]
    return candidate.lower() == prefix.lower() if case_insensitive else candidate == prefix


def check_suffix(address: str, suffix: str, case_insensitive: bool) -> bool:
    if not suffix:
        return True
    if len(address) < len(suffix):
        return False
    candidate = address[-len(suffix):]
    return candidate.lower() == suffix.lower() if case_insensitive else candidate == suffix
