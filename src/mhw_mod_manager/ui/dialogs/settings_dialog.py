"""Settings dialog for application configuration."""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.config import ConfigManager
from ...core.discovery import GameDiscovery
from ...core.models import DeploymentMode

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Dialog for editing application settings."""

    def __init__(
        self,
        config_manager: ConfigManager,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the settings dialog.

        Args:
            config_manager: Configuration manager instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Settings")
        self.setMinimumWidth(600)

        layout = QVBoxLayout(self)

        # Game & Paths section
        paths_group = QGroupBox("Game && Paths")
        paths_layout = QFormLayout()

        # Game directory
        game_dir_layout = QHBoxLayout()
        self.game_dir_edit = QLineEdit()
        game_dir_layout.addWidget(self.game_dir_edit)

        browse_game_btn = QPushButton("Browse...")
        browse_game_btn.setProperty("outlined", True)
        browse_game_btn.clicked.connect(self._browse_game_directory)
        game_dir_layout.addWidget(browse_game_btn)

        detect_btn = QPushButton("Auto-detect")
        detect_btn.setProperty("outlined", True)
        detect_btn.clicked.connect(self._auto_detect_game)
        game_dir_layout.addWidget(detect_btn)

        paths_layout.addRow("Game Directory:", game_dir_layout)

        # Staging directory
        staging_dir_layout = QHBoxLayout()
        self.staging_dir_edit = QLineEdit()
        staging_dir_layout.addWidget(self.staging_dir_edit)

        browse_staging_btn = QPushButton("Browse...")
        browse_staging_btn.setProperty("outlined", True)
        browse_staging_btn.clicked.connect(self._browse_staging_directory)
        staging_dir_layout.addWidget(browse_staging_btn)

        paths_layout.addRow("Staging Directory:", staging_dir_layout)

        # Downloads directory
        downloads_dir_layout = QHBoxLayout()
        self.downloads_dir_edit = QLineEdit()
        downloads_dir_layout.addWidget(self.downloads_dir_edit)

        browse_downloads_btn = QPushButton("Browse...")
        browse_downloads_btn.setProperty("outlined", True)
        browse_downloads_btn.clicked.connect(self._browse_downloads_directory)
        downloads_dir_layout.addWidget(browse_downloads_btn)

        paths_layout.addRow("Downloads Directory:", downloads_dir_layout)

        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)

        # Deployment settings section
        deployment_group = QGroupBox("Deployment Settings")
        deployment_layout = QFormLayout()

        # Deployment mode
        self.deployment_mode_combo = QComboBox()
        self.deployment_mode_combo.addItem("Symlink (recommended)", DeploymentMode.SYMLINK.value)
        self.deployment_mode_combo.addItem("Copy", DeploymentMode.COPY.value)
        deployment_layout.addRow("Deployment Mode:", self.deployment_mode_combo)

        # Keep archives
        self.keep_archives_check = QCheckBox("Keep mod archives after installation")
        deployment_layout.addRow("", self.keep_archives_check)

        deployment_group.setLayout(deployment_layout)
        layout.addWidget(deployment_group)

        # Help text
        help_label = QLabel(
            "<i>Symlink mode creates symbolic links (recommended for Linux). "
            "Copy mode duplicates files.</i>"
        )
        help_label.setProperty("secondary", True)
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        layout.addStretch()

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_settings(self) -> None:
        """Load current settings into the form."""
        config = self.config_manager.get()

        # Paths
        if config.game_directory:
            self.game_dir_edit.setText(str(config.game_directory))
        self.staging_dir_edit.setText(str(config.staging_directory))
        self.downloads_dir_edit.setText(str(config.downloads_directory))

        # Deployment settings
        mode_index = self.deployment_mode_combo.findData(config.deployment_mode.value)
        if mode_index >= 0:
            self.deployment_mode_combo.setCurrentIndex(mode_index)

        self.keep_archives_check.setChecked(config.keep_archives)

    def _save_and_accept(self) -> None:
        """Save settings and close dialog."""
        # Validate game directory
        game_dir_text = self.game_dir_edit.text().strip()
        if game_dir_text:
            game_dir = Path(game_dir_text)
            if not GameDiscovery.validate_game_directory(game_dir):
                logger.warning("Game directory validation failed, but saving anyway")
        else:
            game_dir = None

        # Get deployment mode
        mode_value = self.deployment_mode_combo.currentData()
        deployment_mode = DeploymentMode(mode_value)

        # Update configuration
        self.config_manager.update(
            game_directory=game_dir,
            staging_directory=Path(self.staging_dir_edit.text()),
            downloads_directory=Path(self.downloads_dir_edit.text()),
            deployment_mode=deployment_mode,
            keep_archives=self.keep_archives_check.isChecked(),
        )

        logger.info("Settings saved")
        self.accept()

    def _browse_game_directory(self) -> None:
        """Browse for game directory."""
        current = self.game_dir_edit.text() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Monster Hunter: World Directory",
            current,
        )
        if directory:
            self.game_dir_edit.setText(directory)

    def _browse_staging_directory(self) -> None:
        """Browse for staging directory."""
        current = self.staging_dir_edit.text() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Staging Directory",
            current,
        )
        if directory:
            self.staging_dir_edit.setText(directory)

    def _browse_downloads_directory(self) -> None:
        """Browse for downloads directory."""
        current = self.downloads_dir_edit.text() or str(Path.home())
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Downloads Directory",
            current,
        )
        if directory:
            self.downloads_dir_edit.setText(directory)

    def _auto_detect_game(self) -> None:
        """Auto-detect game directory."""
        detected = GameDiscovery.auto_detect()
        if detected:
            self.game_dir_edit.setText(str(detected))
            logger.info(f"Auto-detected game directory: {detected}")
        else:
            logger.warning("Could not auto-detect game directory")
