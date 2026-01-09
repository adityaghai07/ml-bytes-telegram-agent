"""
Logging Configuration

Sets up structured logging for the application.
Logs go to both console (for development) and file (for production).

Usage:
    from bot.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Bot started")
    logger.error("Something went wrong", extra={"user_id": 123})
"""

import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger

from bot.utils.config import settings


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance

    Args:
        name: Usually __name__ of the calling module

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if logger.handlers:
        return logger

    logger.setLevel(settings.LOG_LEVEL)

    # Console Handler (human-readable for development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler (JSON format for production, easier to parse)
    if settings.is_production:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(log_dir / "bot.log")
        json_formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
        )
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)

    return logger


# Example usage logger for testing
if __name__ == "__main__":
    test_logger = get_logger(__name__)
    test_logger.debug("Debug message")
    test_logger.info("Info message")
    test_logger.warning("Warning message")
    test_logger.error("Error message")
