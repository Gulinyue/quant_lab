"""Log configuration."""

from __future__ import annotations

import sys

from loguru import logger

from quant_lab.common.paths import LOG_DIR


def setup_logger() -> None:
    """Configure loguru sinks once per process."""
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(LOG_DIR / "quant_lab.log", level="DEBUG", encoding="utf-8", rotation="5 MB")
