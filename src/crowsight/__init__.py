# src/crowsight/__init__.py

from loguru import logger
import os
import sys


def configure_logger(
    *,
    level: str = "INFO",
    fmt: str = "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    sink=None,
):
    """
    Configure Loguru for CrowSight.

    - level: log level ("DEBUG", "INFO", etc.)
    - fmt: format string
    - sink: output target (e.g., file path or sys.stdout)

    Honor the CROWSIGHT_LOG_LEVEL environment variable if set.
    """
    logger.remove()
    sink = sink or sys.stdout
    logger.add(sink, level=level, format=fmt)
    env_level = os.getenv("CROWSIGHT_LOG_LEVEL")
    if env_level:
        logger.remove()
        logger.add(sink, level=env_level, format=fmt)
        logger.debug(f"Overriding log level from CROWSIGHT_LOG_LEVEL={env_level}")
