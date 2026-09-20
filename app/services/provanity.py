"""
Wraps the ProVanity binary as a subprocess, with proper error handling
for every way it can fail: missing binary, timeout, crash, unparseable
output, or a GPU/driver failure mid-run.
"""

import re
import subprocess
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings
from app.core.logging_config import logger


class ProVanityError(Exception):
    """Raised when ProVanity fails to run or produces unusable output."""
    pass


@dataclass
class ProVanityResult:
    address: str
    private_key: str
    offset: Optional[str]
    attempts: int


_ADDRESS_RE = re.compile(r"address:\s*(\S+)")
_PRIVKEY_RE = re.compile(r"private key:\s*(\S+)")
_OFFSET_RE = re.compile(r"offset:\s*(\S+)")
_ATTEMPTS_RE = re.compile(r"attempts:\s*(\d+)")


def run_once(suffix: str = "", devices: Optional[str] = None) -> ProVanityResult:
    """
    Runs ProVanity exactly once with the given suffix pattern (prefix is
    NOT supported natively by `generate-tron` — that's verified separately
    by the caller). Raises ProVanityError on any failure.
    """
    cmd = [settings.provanity_binary, "generate-tron", "--devices", devices or settings.devices]
    if suffix:
        cmd += ["--pattern", f"suffix:{suffix}"]

    logger.debug(f"Running: {' '.join(cmd)}")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.provanity_timeout_seconds,
        )
    except subprocess.TimeoutExpired as e:
        raise ProVanityError(
            f"ProVanity did not finish within {settings.provanity_timeout_seconds}s "
            f"(pattern may be too long, or GPU is stuck)"
        ) from e
    except FileNotFoundError as e:
        raise ProVanityError(f"ProVanity binary not found at '{settings.provanity_binary}'") from e
    except PermissionError as e:
        raise ProVanityError(f"ProVanity binary at '{settings.provanity_binary}' is not executable") from e
    except OSError as e:
        raise ProVanityError(f"OS error while launching ProVanity: {e}") from e

    output = (proc.stdout or "") + (proc.stderr or "")

    if proc.returncode != 0:
        raise ProVanityError(
            f"ProVanity exited with code {proc.returncode}. Output tail: {output[-500:]!r}"
        )

    address_match = _ADDRESS_RE.search(output)
    privkey_match = _PRIVKEY_RE.search(output)
    offset_match = _OFFSET_RE.search(output)
    attempts_match = _ATTEMPTS_RE.search(output)

    if not address_match or not privkey_match:
        raise ProVanityError(
            f"Could not parse ProVanity output (address/private key missing). "
            f"Output tail: {output[-500:]!r}"
        )

    return ProVanityResult(
        address=address_match.group(1),
        private_key=privkey_match.group(1),
        offset=offset_match.group(1) if offset_match else None,
        attempts=int(attempts_match.group(1)) if attempts_match else 0,
    )


def check_prefix(address: str, prefix: str, case_insensitive: bool) -> bool:
    """TRON addresses always start with 'T' — the prefix applies after that."""
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
