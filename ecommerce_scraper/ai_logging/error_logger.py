"""Centralized error-only logger utility.

Writes errors to file for postmortem debugging while ignoring info/warn logs.
Usage:
  from ecommerce_scraper.ai_logging.error_logger import get_error_logger
  logger = get_error_logger("product_search_flow")
  logger.error("Something failed", exc_info=True)
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_error_logger(name: str, session_id: Optional[str] = None) -> logging.Logger:
    """Return a logger configured to write ONLY errors to a file.

    - Logs are written under logs/errors/ (optionally per session)
    - Logger and handler levels are set to ERROR
    - Duplicate handlers are avoided
    """
    logger_name = f"{name}_errors" + (f"_{session_id}" if session_id else "")
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.ERROR)

    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    # Create directory
    base_dir = Path("logs") / "errors"
    if session_id:
        base_dir = base_dir / session_id
    base_dir.mkdir(parents=True, exist_ok=True)

    # Use a stable filename per process start (with date stamp)
    filename = f"{datetime.now().strftime('%Y%m%d')}_{name}.log"
    log_path = base_dir / filename

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(pathname)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Do not propagate to root to avoid duplicate console logs
    logger.propagate = False

    return logger

