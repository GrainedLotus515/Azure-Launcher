"""Mod list widget displaying installed mods."""

import logging
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.models import Mod, Profile

logger = logging.getLogger(__name__)


class ModListWidget(QWidget):
    """Widget displaying a list of mods with enable/disable and load order."""

    mod_toggled = Signal(UUID, bool)  # mod_id, enabled
    mod_selected = Signal(UUID)  # mod_id
    load_order_changed = Signal(UUID, int)  # mod_id, new_order
    mod_remove_requested = Signal(UUID)  # mod_id

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the mod list widget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._mods: list[Mod] = []
        self._profile: Optional[Profile] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Enabled", "Name", "Version", "Load Order", "Actions"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 300)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 120)

        layout.addWidget(self.table)

        # Connect signals
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def set_mods(self, mods: list[Mod], profile: Optional[Profile] = None) -> None:
        """Set the list of mods to display.

        Args:
            mods: List of mods to display.
            profile: Current profile (for enabled state and load order).
        """
        self._mods = mods
        self._profile = profile
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the table display."""
        self.table.setRowCount(0)

        if not self._mods:
            return

        # Sort mods by load order if profile is set
        mods_to_display = list(self._mods)
        if self._profile:
            # Sort by load order (enabled mods first, then by order)
            def sort_key(mod: Mod) -> tuple[int, int]:
                entry = self._profile.get_mod_entry(mod.id)
                if entry and entry.enabled:
                    return (0, entry.load_order)
                else:
                    return (1, 0)

            mods_to_display.sort(key=sort_key)

        # Populate table
        for mod in mods_to_display:
            self._add_mod_row(mod)

    def _add_mod_row(self, mod: Mod) -> None:
        """Add a row for a mod.

        Args:
            mod: Mod to add.
        """
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Get profile entry if available
        enabled = False
        load_order = 0
        if self._profile:
            entry = self._profile.get_mod_entry(mod.id)
            if entry:
                enabled = entry.enabled
                load_order = entry.load_order

        # Enabled checkbox
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(8, 0, 8, 0)
        checkbox = QCheckBox()
        checkbox.setChecked(enabled)
        checkbox.stateChanged.connect(
            lambda state, m=mod: self._on_mod_toggled(m, state == Qt.CheckState.Checked.value)
        )
        checkbox_layout.addWidget(checkbox)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setCellWidget(row, 0, checkbox_widget)

        # Name
        name_item = QTableWidgetItem(mod.name)
        name_item.setData(Qt.ItemDataRole.UserRole, str(mod.id))
        self.table.setItem(row, 1, name_item)

        # Version
        version_item = QTableWidgetItem(mod.version or "N/A")
        self.table.setItem(row, 2, version_item)

        # Load order
        order_item = QTableWidgetItem(str(load_order))
        self.table.setItem(row, 3, order_item)

        # Actions
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(4, 4, 4, 4)

        remove_btn = QPushButton("Remove")
        remove_btn.setProperty("outlined", True)
        remove_btn.clicked.connect(lambda: self.mod_remove_requested.emit(mod.id))
        actions_layout.addWidget(remove_btn)

        self.table.setCellWidget(row, 4, actions_widget)

    def _on_mod_toggled(self, mod: Mod, enabled: bool) -> None:
        """Handle mod enable/disable toggle.

        Args:
            mod: Mod that was toggled.
            enabled: New enabled state.
        """
        self.mod_toggled.emit(mod.id, enabled)

    def _on_selection_changed(self) -> None:
        """Handle selection change."""
        selected_rows = self.table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            name_item = self.table.item(row, 1)
            if name_item:
                mod_id_str = name_item.data(Qt.ItemDataRole.UserRole)
                try:
                    mod_id = UUID(mod_id_str)
                    self.mod_selected.emit(mod_id)
                except (ValueError, TypeError):
                    pass

    def refresh(self) -> None:
        """Refresh the display."""
        self._refresh_table()
