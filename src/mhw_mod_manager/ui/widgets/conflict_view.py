"""Conflict view widget for displaying mod file conflicts."""

import logging
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.models import ConflictReport, Mod

logger = logging.getLogger(__name__)


class ConflictViewWidget(QWidget):
    """Widget displaying file conflicts between mods."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the conflict view widget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._conflict_report: Optional[ConflictReport] = None
        self._mods: dict[UUID, Mod] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Header
        self.header_label = QLabel("No conflicts detected")
        self.header_label.setProperty("heading", "h3")
        layout.addWidget(self.header_label)

        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["File Path", "Conflicting Mods", "Winner"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 400)
        self.table.setColumnWidth(1, 300)

        layout.addWidget(self.table)

    def set_conflict_report(
        self,
        report: Optional[ConflictReport],
        mods: list[Mod],
    ) -> None:
        """Set the conflict report to display.

        Args:
            report: Conflict report to display.
            mods: List of all mods (for name lookup).
        """
        self._conflict_report = report
        self._mods = {mod.id: mod for mod in mods}
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the table display."""
        self.table.setRowCount(0)

        if not self._conflict_report or not self._conflict_report.conflicts:
            self.header_label.setText("No conflicts detected")
            return

        conflict_count = len(self._conflict_report.conflicts)
        self.header_label.setText(f"{conflict_count} conflict(s) detected")

        # Populate table
        for conflict in self._conflict_report.conflicts:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # File path
            path_item = QTableWidgetItem(str(conflict.target_path))
            self.table.setItem(row, 0, path_item)

            # Conflicting mods
            mod_names = []
            for mod_id in conflict.conflicting_mods:
                mod = self._mods.get(mod_id)
                if mod:
                    mod_names.append(mod.name)
                else:
                    mod_names.append(f"Unknown ({mod_id})")

            mods_item = QTableWidgetItem(", ".join(mod_names))
            self.table.setItem(row, 1, mods_item)

            # Winner
            winner_mod = self._mods.get(conflict.winner_mod_id)
            winner_name = winner_mod.name if winner_mod else f"Unknown ({conflict.winner_mod_id})"
            winner_item = QTableWidgetItem(winner_name)
            self.table.setItem(row, 2, winner_item)

    def refresh(self) -> None:
        """Refresh the display."""
        self._refresh_table()
