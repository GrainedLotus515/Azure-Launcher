"""Application entry point."""

import logging
import sys

from PySide6.QtWidgets import QApplication

from .core.config import ConfigManager
from .main_window import MainWindow
from .services.logging_service import LoggingService
from .theme import apply_palette, get_stylesheet

logger = logging.getLogger(__name__)


def main() -> int:
    """Main application entry point.

    Returns:
        Exit code.
    """
    # Initialize logging first
    logging_service = LoggingService(log_level=logging.INFO)
    logger.info("MHW Mod Manager starting")

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("MHW Mod Manager")
    app.setOrganizationName("MHW")

    # Apply theme
    apply_palette(app)
    app.setStyleSheet(get_stylesheet())

    # Load configuration
    config_manager = ConfigManager()
    config_manager.load()

    # Create and show main window
    window = MainWindow(config_manager, logging_service)
    window.show()

    logger.info("Main window created and shown")

    # Run application
    exit_code = app.exec()

    logger.info(f"Application exiting with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
