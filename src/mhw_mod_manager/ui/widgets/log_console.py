"""Log console widget for displaying application logs."""

import logging
from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...theme.catppuccin import CatppuccinMocha

logger = logging.getLogger(__name__)


class LogConsoleWidget(QWidget):
    """Widget displaying application log messages."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the log console widget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Log text display
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)  # Limit to 1000 lines
        layout.addWidget(self.log_text)

        # Control buttons
        button_layout = QHBoxLayout()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setProperty("outlined", True)
        self.clear_btn.setProperty("small", True)
        self.clear_btn.setFixedHeight(32)
        self.clear_btn.clicked.connect(self.clear)
        button_layout.addWidget(self.clear_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)

    @Slot(str, str, str)
    def append_log(self, level: str, message: str, timestamp: str) -> None:
        """Append a log message to the console.

        Args:
            level: Log level (INFO, WARNING, ERROR, etc.).
            message: Log message.
            timestamp: Timestamp string.
        """
        # Color code by level
        color = self._get_level_color(level)

        # Format message
        formatted = f'<span style="color: {color};">[{timestamp}] [{level}]</span> {message}'

        self.log_text.appendHtml(formatted)

        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def clear(self) -> None:
        """Clear the log console."""
        self.log_text.clear()

    @staticmethod
    def _get_level_color(level: str) -> str:
        """Get color for log level.

        Args:
            level: Log level string.

        Returns:
            Hex color code.
        """
        colors = {
            "DEBUG": CatppuccinMocha.subtext0,
            "INFO": CatppuccinMocha.blue,
            "WARNING": CatppuccinMocha.peach,
            "ERROR": CatppuccinMocha.red,
            "CRITICAL": CatppuccinMocha.red,
        }
        return colors.get(level, CatppuccinMocha.text)
