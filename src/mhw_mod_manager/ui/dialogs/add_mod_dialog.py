"""Dialog for adding new mods."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class AddModDialog(QDialog):
    """Dialog for adding a new mod from file or folder."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the add mod dialog.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.selected_path: Optional[Path] = None
        self.mod_name: Optional[str] = None
        self.is_archive = True
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Add Mod")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Source type selection
        type_label = QLabel("Select mod source:")
        type_label.setProperty("heading", "h3")
        layout.addWidget(type_label)

        self.archive_radio = QRadioButton("From ZIP archive")
        self.archive_radio.setChecked(True)
        self.archive_radio.toggled.connect(self._on_source_type_changed)
        layout.addWidget(self.archive_radio)

        self.folder_radio = QRadioButton("From folder")
        layout.addWidget(self.folder_radio)

        layout.addSpacing(16)

        # File/folder selection
        form_layout = QFormLayout()

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(self.path_edit)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(self.browse_btn)

        form_layout.addRow("Source:", path_layout)

        # Mod name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Auto-detected from file name")
        form_layout.addRow("Mod Name:", self.name_edit)

        layout.addLayout(form_layout)

        layout.addStretch()

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        layout.addWidget(self.button_box)

    def _on_source_type_changed(self) -> None:
        """Handle source type radio button change."""
        self.is_archive = self.archive_radio.isChecked()
        self.path_edit.clear()
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _browse(self) -> None:
        """Browse for mod file or folder."""
        if self.is_archive:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Mod Archive",
                str(Path.home()),
                "ZIP Archives (*.zip);;All Files (*)",
            )
            if file_path:
                self.selected_path = Path(file_path)
                self.path_edit.setText(file_path)
                # Auto-fill name
                if not self.name_edit.text():
                    self.name_edit.setText(Path(file_path).stem)
                self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        else:
            directory = QFileDialog.getExistingDirectory(
                self,
                "Select Mod Folder",
                str(Path.home()),
            )
            if directory:
                self.selected_path = Path(directory)
                self.path_edit.setText(directory)
                # Auto-fill name
                if not self.name_edit.text():
                    self.name_edit.setText(Path(directory).name)
                self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def _accept(self) -> None:
        """Validate and accept the dialog."""
        if not self.selected_path or not self.selected_path.exists():
            logger.warning("Invalid mod source path")
            return

        # Use provided name or default to file/folder name
        self.mod_name = self.name_edit.text().strip()
        if not self.mod_name:
            self.mod_name = self.selected_path.stem if self.is_archive else self.selected_path.name

        self.accept()

    def get_result(self) -> tuple[Optional[Path], Optional[str], bool]:
        """Get the dialog result.

        Returns:
            Tuple of (path, mod_name, is_archive).
        """
        return self.selected_path, self.mod_name, self.is_archive
