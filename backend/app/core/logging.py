import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


class PerformanceJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.msg
        if isinstance(message, dict):
            return json.dumps(message, sort_keys=True)
        return json.dumps(
            {
                "event": "performance_log_message",
                "message": record.getMessage(),
            },
            sort_keys=True,
        )


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    configure_performance_file_logging()


def configure_performance_file_logging() -> None:
    performance_logger = logging.getLogger("ctv_one.performance")
    performance_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    log_path = Path(settings.performance_log_path)

    if any(
        isinstance(handler, RotatingFileHandler)
        and getattr(handler, "baseFilename", None) == str(log_path)
        for handler in performance_logger.handlers
    ):
        return

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_path,
            maxBytes=settings.performance_log_max_bytes,
            backupCount=settings.performance_log_backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(PerformanceJsonFormatter())
        performance_logger.addHandler(handler)
    except OSError:
        logging.getLogger(__name__).warning("performance.file_logging_unavailable")
