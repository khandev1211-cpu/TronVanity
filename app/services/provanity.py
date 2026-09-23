"""
Wraps TRON Profanity / ProVanity GPU binaries as subprocesses.
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
    """
    base58_pad = "123456789ABCDEFGHJKLMNPQRSTUV"
    pad_needed = 34 - 1 - len(prefix) - len(suffix)
    dummy_fill = base58_pad[:max(0, pad_needed)]
    target_address = f"T{prefix}{dummy_fill}{suffix}"

    # Use simple relative file name to avoid path spaces issues in C++ executable
    result_file = f"res_{int(time.time())}.txt"
    if os.path.exists(result_file):
        try: os.remove(result_file)
        except: pass

    cmd = [
        settings.provanity_binary,
        "--matching", target_address,
        "--prefix-count", str(len(prefix)),
        "--suffix-count", str(len(suffix)),
        "--quit-count", "1",
        "--skip", str(settings.gpu_skip),
        "--output", result_file
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
    """
    Unified entry point. Automatically uses simultaneous 1-pass Profanity if available,
    otherwise falls back to ProVanity.
    """
    binary_name = os.path.basename(settings.provanity_binary).lower()

    if "profanity" in binary_name and "provanity" not in binary_name:
        return run_profanity_simultaneous(prefix, suffix)

    # Fallback for ProVanity
    cmd = [settings.provanity_binary, "generate-tron", "--devices", devices or settings.devices]
    if suffix:
        cmd += ["--pattern", f"suffix:{suffix}"]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.provanity_timeout_seconds,
        )
        output = (proc.stdout or "") + (proc.stderr or "")

        address_match = _ADDRESS_RE.search(output)
        privkey_match = _PRIVKEY_RE.search(output)

        if address_match and privkey_match:
            return ProVanityResult(
                address=address_match.group(1),
                private_key=privkey_match.group(1)
            )
        raise ProVanityError("Could not parse output")
    except Exception as e:
        # Final fallback to simultaneous Profanity if ProVanity failed
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
