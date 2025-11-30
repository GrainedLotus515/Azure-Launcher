"""Centralized logging service."""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from ..core.config import get_log_dir


class QtLogHandler(logging.Handler, QObject):
    """Custom logging handler that emits Qt signals for UI display."""

    log_message = Signal(str, str, str)  # level, message, timestamp

    def __init__(self) -> None:
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit log record as Qt signal.

        Args:
            record: Log record to emit.
        """
        try:
            msg = self.format(record)
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            self.log_message.emit(record.levelname, msg, timestamp)
        except Exception:
            self.handleError(record)


class LoggingService:
    """Manages application logging."""

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        log_level: int = logging.INFO,
    ) -> None:
        """Initialize the logging service.

        Args:
            log_dir: Directory for log files. If None, uses platform default.
            log_level: Logging level (e.g., logging.INFO, logging.DEBUG).
        """
        self.log_dir = log_dir or get_log_dir()
        self.log_file = self.log_dir / "mhw_mod_manager.log"
        self.log_level = log_level
        self.qt_handler: Optional[QtLogHandler] = None

        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging handlers and formatters."""
        # Create logger
        logger = logging.getLogger()
        logger.setLevel(self.log_level)

        # Clear existing handlers
        logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # File handler with rotation
        self.log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(self.log_level)
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

        # Qt handler for UI display
        self.qt_handler = QtLogHandler()
        self.qt_handler.setLevel(logging.INFO)
        qt_format = logging.Formatter("%(message)s")
        self.qt_handler.setFormatter(qt_format)
        logger.addHandler(self.qt_handler)

        logger.info("Logging service initialized")

    def get_qt_handler(self) -> Optional[QtLogHandler]:
        """Get the Qt log handler for connecting to UI.

        Returns:
            Qt log handler instance.
        """
        return self.qt_handler

    def set_level(self, level: int) -> None:
        """Change the logging level.

        Args:
            level: New logging level (e.g., logging.DEBUG).
        """
        logger = logging.getLogger()
        logger.setLevel(level)
        self.log_level = level

        for handler in logger.handlers:
            handler.setLevel(level)

    def get_log_file_path(self) -> Path:
        """Get path to the current log file.

        Returns:
            Path to log file.
        """
        return self.log_file
