"""
Pydantic request/response schemas.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator

# TRON addresses use Base58 (Bitcoin alphabet): digits and letters, excluding
# the visually-confusing 0, O, I, l.
BASE58_ALPHABET = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")


class JobStatusEnum(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class GenerateRequest(BaseModel):
    prefix: str = Field("", max_length=12, description="Desired prefix after the leading 'T'")
    suffix: str = Field("", max_length=12, description="Desired suffix at the end of the address")
    case_insensitive: bool = Field(False, description="Match prefix/suffix ignoring case")

    @field_validator("prefix", "suffix")
    @classmethod
    def validate_base58(cls, v: str) -> str:
        if v == "":
            return v
        invalid_chars = set(v) - BASE58_ALPHABET
        if invalid_chars:
            raise ValueError(
                f"Contains characters not valid in a TRON (Base58) address: {sorted(invalid_chars)}. "
                f"Avoid 0, O, I, l — they don't appear in Base58 addresses."
            )
        return v

    @field_validator("suffix")
    @classmethod
    def validate_at_least_one(cls, v: str, info) -> str:
        prefix = info.data.get("prefix", "")
        if not prefix and not v:
            raise ValueError("At least one of 'prefix' or 'suffix' must be non-empty")
        return v


class GenerateResponse(BaseModel):
    job_id: str
    status: JobStatusEnum


class JobResult(BaseModel):
    address: str
    private_key: str
    offset: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: JobStatusEnum
    prefix: str
    suffix: str
    case_insensitive: bool
    created_at: str
    finished_at: Optional[str] = None
    attempts_total: int = 0
    elapsed_seconds: float = 0.0
    result: Optional[JobResult] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    provanity_binary_found: bool
    active_jobs: int
