import os
import logging
from datetime import datetime
from pathlib import Path

from config.logging_settings import (
    DEFAULT_LOG_LEVEL,
    LOG_DATE_FORMAT,
    LOG_DATE_TIME_FORMAT,
    LOG_FILE_PREFIX,
    LOG_MESSAGE_FORMAT,
)
from config.path_settings import LOGS_DIR

LOG_CONSOLE_ENV_KEY = "IDMS_LOG_CONSOLE"
LOG_CONSOLE_LEVEL = "WARNING"

class LoggerFactory:
    """
    Creates production-style loggers that write to logs folder.

    One log file is created per run:
    logs/idms_db2_conversion_DD-MM-YYYY_HHMMSS.log
    """

@staticmethod
def create_logger(
    name: str,
    logs_dir: Path | None = None,
    level: str = DEFAULT_LOG_LEVEL,
    console: bool | None = None,
) -> logging.Logger:
    target_logs_dir = Path(logs_dir or LOGS_DIR)
    target_logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime(LOG_DATE_TIME_FORMAT)
    log_file = target_logs_dir / f"{LOG_FILE_PREFIX}_{timestamp}.log"

    logger = logging.getLogger(name)
    logger.setLevel(LoggerFactory._level_value(level))
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        fmt=LOG_MESSAGE_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(LoggerFactory._level_value(level))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if console is None:
        console = os.environ.get(LOG_CONSOLE_ENV_KEY, "").strip() in ("1", "true", "TRUE")

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LoggerFactory._level_value(LOG_CONSOLE_LEVEL))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.info("Logger initialized.")
    logger.info("Log file: %s", log_file)
    return logger


    @staticmethod   
    def _level_value(
        level: str,
    ) -> int:
        return getattr(
            logging,
            str(level or DEFAULT_LOG_LEVEL).upper(),
            logging.INFO,
        )