"""
Configuration loader and validator.
Reads all settings from .env and fails fast with clear error messages
if anything required is missing or invalid.
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
        self.api_key: str = self._require_str("VANITY_API_KEY")
        self.provanity_binary: str = os.environ.get("PROVANITY_BINARY", "/workspace/provanity")
        self.devices: str = os.environ.get("PROVANITY_DEVICES", "all")
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

    def _require_str(self, key: str) -> str:
        value = os.environ.get(key)
        if not value or value.strip() == "" or "REPLACE_WITH" in value:
            raise ConfigError(
                f"Required environment variable '{key}' is not set (or still has its "
                f"placeholder value). Copy .env.example to .env and fill it in."
            )
        return value.strip()

    def _get_int(self, key: str, default: int) -> int:
        raw = os.environ.get(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(f"Environment variable '{key}' must be an integer, got: {raw!r}")

    def _validate(self):
        if len(self.api_key) < 16:
            raise ConfigError(
                "VANITY_API_KEY looks too short to be secure (< 16 chars). "
                "Generate one with: python3 -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if not os.path.exists(self.provanity_binary):
            raise ConfigError(
                f"PROVANITY_BINARY points to '{self.provanity_binary}' but that file doesn't exist. "
                f"Check the path or download ProVanity first."
            )
        if not os.access(self.provanity_binary, os.X_OK):
            raise ConfigError(
                f"PROVANITY_BINARY at '{self.provanity_binary}' exists but is not executable. "
                f"Run: chmod +x {self.provanity_binary}"
            )
        if self.port < 1 or self.port > 65535:
            raise ConfigError(f"PORT must be between 1 and 65535, got: {self.port}")
        if self.max_runtime_seconds < 1:
            raise ConfigError("MAX_RUNTIME_SECONDS must be positive")


def load_settings() -> Settings:
    """Load and validate settings, exiting with a clear message on failure."""
    try:
        return Settings()
    except ConfigError as e:
        print(f"\n[CONFIG ERROR] {e}\n", file=sys.stderr)
        sys.exit(1)


settings = load_settings()
