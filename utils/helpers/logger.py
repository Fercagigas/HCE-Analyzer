"""
Logger utilities - re-exports from config.logging_config for backwards compatibility.
"""
import logging
import structlog
from config.logging_config import get_logger, get_structured_logger


class StructuredLogger:
    """Wrapper around structlog for structured logging."""

    def __init__(self, name: str):
        self._logger = structlog.get_logger(name)
        self._std_logger = logging.getLogger(name)

    def debug(self, msg: str, **kwargs):
        self._logger.debug(msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self._logger.info(msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self._logger.warning(msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self._logger.error(msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        self._logger.critical(msg, **kwargs)


# Default module-level logger instance
logger = logging.getLogger("utils.helpers")

__all__ = ["logger", "StructuredLogger"]
