"""
Centralized logging configuration. Logs to both console and a rotating
file so nothing is lost if the process runs for days.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import settings


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("tron_vanity")
    logger.setLevel(settings.log_level)
    logger.propagate = False

    if logger.handlers:
        return logger  # already configured (e.g. reloaded module)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        settings.logs_dir / "server.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()
