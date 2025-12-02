"""Profile selector widget."""

import logging
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.models import Profile

logger = logging.getLogger(__name__)


class ProfileSelectorWidget(QWidget):
    """Widget for selecting and managing profiles."""

    profile_changed = Signal(UUID)  # profile_id
    new_profile_requested = Signal()
    delete_profile_requested = Signal(UUID)
    rename_profile_requested = Signal(UUID)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the profile selector widget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._profiles: list[Profile] = []
        self._current_profile_id: Optional[UUID] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Profile combo box
        combo_layout = QHBoxLayout()
        combo_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        combo_layout.addWidget(self.profile_combo)

        layout.addLayout(combo_layout)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        self.new_btn = QPushButton("New")
        self.new_btn.setProperty("outlined", True)
        self.new_btn.setProperty("small", True)
        self.new_btn.setFixedHeight(32)
        self.new_btn.clicked.connect(self.new_profile_requested.emit)
        button_layout.addWidget(self.new_btn)

        self.rename_btn = QPushButton("Rename")
        self.rename_btn.setProperty("flat", True)
        self.rename_btn.setProperty("small", True)
        self.rename_btn.setFixedHeight(32)
        self.rename_btn.clicked.connect(self._on_rename_clicked)
        button_layout.addWidget(self.rename_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("flat", True)
        self.delete_btn.setProperty("small", True)
        self.delete_btn.setFixedHeight(32)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        button_layout.addWidget(self.delete_btn)

        layout.addLayout(button_layout)

    def set_profiles(self, profiles: list[Profile], current_id: Optional[UUID] = None) -> None:
        """Set the list of available profiles.

        Args:
            profiles: List of profiles.
            current_id: ID of currently selected profile.
        """
        self._profiles = profiles
        self._current_profile_id = current_id
        self._refresh_combo()

    def _refresh_combo(self) -> None:
        """Refresh the combo box contents."""
        # Block signals while updating
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()

        current_index = 0
        for i, profile in enumerate(self._profiles):
            self.profile_combo.addItem(profile.name, str(profile.id))
            if profile.id == self._current_profile_id:
                current_index = i

        self.profile_combo.setCurrentIndex(current_index)
        self.profile_combo.blockSignals(False)

        # Update button states
        has_profiles = len(self._profiles) > 0
        can_delete = has_profiles and len(self._profiles) > 1  # Keep at least one
        self.rename_btn.setEnabled(has_profiles)
        self.delete_btn.setEnabled(can_delete)

    def _on_profile_selected(self, index: int) -> None:
        """Handle profile selection change.

        Args:
            index: Selected index in combo box.
        """
        if index < 0 or index >= len(self._profiles):
            return

        profile = self._profiles[index]
        self._current_profile_id = profile.id
        self.profile_changed.emit(profile.id)

    def _on_rename_clicked(self) -> None:
        """Handle rename button click."""
        if self._current_profile_id:
            self.rename_profile_requested.emit(self._current_profile_id)

    def _on_delete_clicked(self) -> None:
        """Handle delete button click."""
        if self._current_profile_id:
            self.delete_profile_requested.emit(self._current_profile_id)

    def get_current_profile_id(self) -> Optional[UUID]:
        """Get the currently selected profile ID.

        Returns:
            Current profile ID or None.
        """
        return self._current_profile_id
