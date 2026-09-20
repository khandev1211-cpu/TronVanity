"""
API key authentication dependency, with constant-time comparison to
avoid timing side-channel attacks on the key.
"""

import hmac
from typing import Optional

from fastapi import Header, HTTPException, status

from app.core.config import settings


def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    if not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return True
