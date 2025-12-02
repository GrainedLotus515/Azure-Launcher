"""Nexus Mods browser widget."""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.models import NexusMod

logger = logging.getLogger(__name__)


class ModCardWidget(QWidget):
    """Widget representing a single mod card."""

    mod_clicked = Signal(int)  # mod_id

    def __init__(self, mod: NexusMod, parent: Optional[QWidget] = None) -> None:
        """Initialize mod card.

        Args:
            mod: Mod information.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.mod = mod
        self._setup_ui()
        self.setMaximumHeight(150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Mod name with text elision
        name_label = QLabel(self.mod.name)
        name_label.setProperty("heading", True)
        name_label.setWordWrap(False)
        name_label.setTextFormat(Qt.TextFormat.PlainText)
        name_label.setSizePolicy(
            name_label.sizePolicy().horizontalPolicy(), name_label.sizePolicy().verticalPolicy()
        )
        # Use a fixed maximum width to force elision
        name_label.setMaximumWidth(400)
        layout.addWidget(name_label)

        # Author with text elision
        author_label = QLabel(f"by {self.mod.author}")
        author_label.setProperty("secondary", True)
        author_label.setWordWrap(False)
        author_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(author_label)

        # Summary - word wrap for 2 lines max
        summary_label = QLabel(self.mod.summary)
        summary_label.setWordWrap(True)
        summary_label.setTextFormat(Qt.TextFormat.PlainText)
        summary_label.setMaximumHeight(40)
        summary_label.setFixedHeight(40)
        layout.addWidget(summary_label)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)

        stats_layout.addWidget(QLabel(f"⭐ {self.mod.endorsement_count}"))
        stats_layout.addWidget(QLabel(f"⬇ {self.mod.download_count}"))

        version_label = QLabel(f"v{self.mod.version}")
        version_label.setWordWrap(False)
        version_label.setTextFormat(Qt.TextFormat.PlainText)
        stats_layout.addWidget(version_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        layout.addStretch()

        # Style
        self.setProperty("card", True)

    def mousePressEvent(self, event: object) -> None:
        """Handle mouse press event."""
        self.mod_clicked.emit(self.mod.mod_id)
        super().mousePressEvent(event)


class ModGridWidget(QWidget):
    """Grid widget for displaying mods."""

    mod_clicked = Signal(int)  # mod_id
    load_more_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize mod grid.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.mod_cards: list[ModCardWidget] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container
        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area.setWidget(self.container)
        layout.addWidget(scroll_area)

        # Empty state
        self.empty_label = QLabel("No mods to display")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("secondary", True)
        self.grid_layout.addWidget(self.empty_label, 0, 0)

    def set_mods(self, mods: list[NexusMod]) -> None:
        """Set the mods to display.

        Args:
            mods: List of mods.
        """
        # Clear existing
        self.clear()

        if not mods:
            self.empty_label.setVisible(True)
            return

        self.empty_label.setVisible(False)

        # Add mod cards in grid (2 columns)
        columns = 2
        for i, mod in enumerate(mods):
            card = ModCardWidget(mod)
            card.mod_clicked.connect(self.mod_clicked.emit)
            self.mod_cards.append(card)

            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(card, row, col)

    def clear(self) -> None:
        """Clear all mod cards."""
        for card in self.mod_cards:
            self.grid_layout.removeWidget(card)
            card.deleteLater()
        self.mod_cards.clear()


class NexusBrowserWidget(QWidget):
    """Browser widget for Nexus Mods."""

    mod_selected = Signal(int)  # mod_id
    download_requested = Signal(int, int)  # mod_id, file_id
    refresh_requested = Signal(str)  # tab name

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize Nexus browser.

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

        # Header with search
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search mods...")
        self.search_edit.setFixedHeight(36)
        header_layout.addWidget(self.search_edit, 1)

        search_btn = QPushButton("Search")
        search_btn.setFixedHeight(36)
        header_layout.addWidget(search_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("outlined", True)
        refresh_btn.setFixedHeight(36)
        refresh_btn.clicked.connect(self._on_refresh)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Tab widget
        self.tab_widget = QTabWidget()

        # Trending tab
        self.trending_grid = ModGridWidget()
        self.trending_grid.mod_clicked.connect(self.mod_selected.emit)
        self.tab_widget.addTab(self.trending_grid, "Trending")

        # Latest tab
        self.latest_grid = ModGridWidget()
        self.latest_grid.mod_clicked.connect(self.mod_selected.emit)
        self.tab_widget.addTab(self.latest_grid, "Latest")

        # Updated tab
        self.updated_grid = ModGridWidget()
        self.updated_grid.mod_clicked.connect(self.mod_selected.emit)
        self.tab_widget.addTab(self.updated_grid, "Updated")

        # Search results tab (hidden by default)
        self.search_grid = ModGridWidget()
        self.search_grid.mod_clicked.connect(self.mod_selected.emit)
        self.search_tab_index = self.tab_widget.addTab(self.search_grid, "Search Results")
        self.tab_widget.setTabVisible(self.search_tab_index, False)

        layout.addWidget(self.tab_widget)

        # Status label
        self.status_label = QLabel()
        self.status_label.setProperty("secondary", True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def set_trending_mods(self, mods: list[NexusMod]) -> None:
        """Set trending mods.

        Args:
            mods: List of trending mods.
        """
        self.trending_grid.set_mods(mods)

    def set_latest_mods(self, mods: list[NexusMod]) -> None:
        """Set latest mods.

        Args:
            mods: List of latest mods.
        """
        self.latest_grid.set_mods(mods)

    def set_updated_mods(self, mods: list[NexusMod]) -> None:
        """Set updated mods.

        Args:
            mods: List of updated mods.
        """
        self.updated_grid.set_mods(mods)

    def set_search_results(self, mods: list[NexusMod]) -> None:
        """Set search results.

        Args:
            mods: List of search result mods.
        """
        self.search_grid.set_mods(mods)
        self.tab_widget.setTabVisible(self.search_tab_index, True)
        self.tab_widget.setCurrentIndex(self.search_tab_index)

    def set_status(self, message: str) -> None:
        """Set status message.

        Args:
            message: Status message.
        """
        self.status_label.setText(message)

    def clear_status(self) -> None:
        """Clear status message."""
        self.status_label.setText("")

    def _on_refresh(self) -> None:
        """Handle refresh button click."""
        current_index = self.tab_widget.currentIndex()
        tab_names = ["trending", "latest", "updated", "search"]
        if current_index < len(tab_names):
            self.refresh_requested.emit(tab_names[current_index])
