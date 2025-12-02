"""Application entry point."""

import argparse
import logging
import sys

from PySide6.QtWidgets import QApplication

from .core.config import ConfigManager
from .main_window import MainWindow
from .services.logging_service import LoggingService
from .theme import apply_palette, get_stylesheet

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="MHW Mod Manager")
    parser.add_argument(
        "--nxm-link",
        type=str,
        help="NXM protocol link to process",
    )
    return parser.parse_args()


def main() -> int:
    """Main application entry point.

    Returns:
        Exit code.
    """
    # Parse arguments
    args = parse_arguments()

    # Initialize logging first
    logging_service = LoggingService(log_level=logging.INFO)
    logger.info("MHW Mod Manager starting")

    # Log NXM link if provided
    if args.nxm_link:
        logger.info(f"Received NXM link: {args.nxm_link}")

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
    window = MainWindow(config_manager, logging_service, nxm_link=args.nxm_link)
    window.show()

    logger.info("Main window created and shown")

    # Run application
    exit_code = app.exec()

    logger.info(f"Application exiting with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
