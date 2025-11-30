"""Pytest configuration and fixtures."""

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for tests that need Qt."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
