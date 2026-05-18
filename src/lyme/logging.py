"""Logging — structured logging for Lyme components."""
from __future__ import annotations
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%H:%M:%S"

_LOGGERS: dict[str, logging.Logger] = {}
_LOG_FILE: Optional[Path] = None


def get_logger(name: str) -> logging.Logger:
    if name not in _LOGGERS:
        logger = logging.getLogger(f"lyme.{name}")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
            logger.addHandler(handler)
            if _LOG_FILE:
                file_handler = logging.FileHandler(str(_LOG_FILE))
                file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
                logger.addHandler(file_handler)
        _LOGGERS[name] = logger
    return _LOGGERS[name]


def configure(
    level: str = "INFO",
    log_file: Optional[str] = None,
    verbose: bool = False,
) -> None:
    global _LOG_FILE
    level = "DEBUG" if verbose else level.upper()
    if log_file:
        _LOG_FILE = Path(log_file)
        _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    for logger in _LOGGERS.values():
        logger.setLevel(getattr(logging, level, logging.INFO))
    root = logging.getLogger("lyme")
    root.setLevel(getattr(logging, level, logging.INFO))
