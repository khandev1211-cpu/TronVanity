"""
Configuration loader and validator for TronVanity GPU Node.
Reads all settings from .env and supports both REST API & Redis connection to main VPS.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


class Settings:
    def __init__(self):
        # API Key for REST API
        self.api_key: str = os.environ.get("VANITY_API_KEY", "default_secret_key_change_me_12345")

        # Remote/Local VPS Redis Connection Parameters
        self.redis_host: str = os.environ.get("REDIS_HOST", "localhost")
        self.redis_port: int = self._get_int("REDIS_PORT", 6379)
        self.redis_password: str = os.environ.get("REDIS_PASSWORD", "")

        # Binary Path (Supports profanity.x64 / profanity.exe / provanity)
        self.provanity_binary: str = (
            os.environ.get("PROFANITY_BINARY") or
            os.environ.get("PROVANITY_BINARY") or
            str(BASE_DIR / "profanity.x64")
        )
        self.devices: str = os.environ.get("PROVANITY_DEVICES", "all")
        self.gpu_skip: str = os.environ.get("GPU_SKIP_DEVICE", "1" if os.name == "nt" else "0")

        self.host: str = os.environ.get("HOST", "0.0.0.0")
        self.port: int = self._get_int("PORT", 8000)
        self.max_runtime_seconds: int = self._get_int("MAX_RUNTIME_SECONDS", 60 * 60 * 24 * 3)
        self.provanity_timeout_seconds: int = self._get_int("PROVANITY_TIMEOUT_SECONDS", 3600)
        self.log_level: str = os.environ.get("LOG_LEVEL", "INFO").upper()
        self.max_jobs_history: int = self._get_int("MAX_JOBS_HISTORY", 500)

        self.jobs_dir: Path = BASE_DIR / "jobs"
        self.logs_dir: Path = BASE_DIR / "logs"
        self.jobs_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        self._validate()

    def _get_int(self, key: str, default: int) -> int:
        raw = os.environ.get(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(f"Environment variable '{key}' must be an integer, got: {raw!r}")

    def _validate(self):
        if self.port < 1 or self.port > 65535:
            raise ConfigError(f"PORT must be between 1 and 65535, got: {self.port}")
        if self.max_runtime_seconds < 1:
            raise ConfigError("MAX_RUNTIME_SECONDS must be positive")


def load_settings() -> Settings:
    """Load settings smoothly."""
    try:
        return Settings()
    except ConfigError as e:
        print(f"\n[CONFIG ERROR] {e}\n", file=sys.stderr)
        sys.exit(1)


settings = load_settings()
