"""Main application window."""

import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .core.config import ConfigManager
from .core.discovery import GameDiscovery
from .core.models import Mod, Profile
from .core.mods.conflicts import ConflictDetector
from .core.mods.deployment import DeploymentEngine
from .core.mods.installer import ModInstaller
from .core.mods.profiles import ProfileManager
from .core.mods.repository import ModRepository
from .services.logging_service import LoggingService
from .services.task_runner import TaskRunner
from .ui.dialogs.add_mod_dialog import AddModDialog
from .ui.dialogs.settings_dialog import SettingsDialog
from .ui.widgets.conflict_view import ConflictViewWidget
from .ui.widgets.log_console import LogConsoleWidget
from .ui.widgets.mod_list import ModListWidget
from .ui.widgets.profile_selector import ProfileSelectorWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(
        self,
        config_manager: ConfigManager,
        logging_service: LoggingService,
    ) -> None:
        """Initialize the main window.

        Args:
            config_manager: Configuration manager.
            logging_service: Logging service.
        """
        super().__init__()

        self.config_manager = config_manager
        self.logging_service = logging_service

        # Core services
        self.mod_repository = ModRepository()
        self.profile_manager = ProfileManager()
        self.task_runner = TaskRunner()

        self.mod_installer: Optional[ModInstaller] = None
        self.deployment_engine: Optional[DeploymentEngine] = None
        self.conflict_detector = ConflictDetector()

        # State
        self.current_profile: Optional[Profile] = None

        self._setup_ui()
        self._connect_signals()
        self._initialize()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Monster Hunter: World - Mod Manager")

        # Restore window size
        config = self.config_manager.get()
        self.resize(config.window_width, config.window_height)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter for left sidebar and main area
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left sidebar
        sidebar = self._create_sidebar()
        splitter.addWidget(sidebar)

        # Main area with tabs
        main_area = self._create_main_area()
        splitter.addWidget(main_area)

        # Set splitter sizes (sidebar narrower)
        splitter.setSizes([250, 950])

        main_layout.addWidget(splitter)

        # Toolbar
        self._create_toolbar()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _create_sidebar(self) -> QWidget:
        """Create the left sidebar.

        Returns:
            Sidebar widget.
        """
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)

        # Profile selector
        self.profile_selector = ProfileSelectorWidget()
        sidebar_layout.addWidget(self.profile_selector)

        sidebar_layout.addStretch()

        return sidebar

    def _create_main_area(self) -> QWidget:
        """Create the main content area.

        Returns:
            Main area widget.
        """
        # Tab widget
        self.tab_widget = QTabWidget()

        # Mods tab
        self.mod_list = ModListWidget()
        self.tab_widget.addTab(self.mod_list, "Mods")

        # Conflicts tab
        self.conflict_view = ConflictViewWidget()
        self.tab_widget.addTab(self.conflict_view, "Conflicts")

        # Log tab
        self.log_console = LogConsoleWidget()
        self.tab_widget.addTab(self.log_console, "Log")

        return self.tab_widget

    def _create_toolbar(self) -> None:
        """Create the toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Add mod button
        add_mod_btn = QPushButton("Add Mod")
        add_mod_btn.clicked.connect(self._on_add_mod)
        toolbar.addWidget(add_mod_btn)

        toolbar.addSeparator()

        # Deploy button
        deploy_btn = QPushButton("Deploy")
        deploy_btn.clicked.connect(self._on_deploy)
        toolbar.addWidget(deploy_btn)

        # Undeploy button
        undeploy_btn = QPushButton("Undeploy")
        undeploy_btn.setProperty("outlined", True)
        undeploy_btn.clicked.connect(self._on_undeploy)
        toolbar.addWidget(undeploy_btn)

        toolbar.addSeparator()

        # Refresh conflicts button
        refresh_btn = QPushButton("Refresh Conflicts")
        refresh_btn.setProperty("outlined", True)
        refresh_btn.clicked.connect(self._refresh_conflicts)
        toolbar.addWidget(refresh_btn)

        # Stretch to push settings to the right
        from PySide6.QtWidgets import QSizePolicy

        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        toolbar.addWidget(spacer)

        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.setProperty("outlined", True)
        settings_btn.clicked.connect(self._on_settings)
        toolbar.addWidget(settings_btn)

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        # Profile selector
        self.profile_selector.profile_changed.connect(self._on_profile_changed)
        self.profile_selector.new_profile_requested.connect(self._on_new_profile)
        self.profile_selector.delete_profile_requested.connect(self._on_delete_profile)
        self.profile_selector.rename_profile_requested.connect(self._on_rename_profile)

        # Mod list
        self.mod_list.mod_toggled.connect(self._on_mod_toggled)
        self.mod_list.mod_remove_requested.connect(self._on_remove_mod)

        # Logging
        qt_handler = self.logging_service.get_qt_handler()
        if qt_handler:
            qt_handler.log_message.connect(self.log_console.append_log)

    def _initialize(self) -> None:
        """Initialize the application state."""
        logger.info("Initializing main window")

        # Check for game directory
        config = self.config_manager.get()
        if not config.game_directory or not GameDiscovery.validate_game_directory(
            config.game_directory
        ):
            logger.warning("Game directory not configured or invalid")
            self._prompt_game_directory()

        # Initialize services that need game directory
        if config.game_directory:
            self.mod_installer = ModInstaller(self.config_manager)
            self.deployment_engine = DeploymentEngine(self.config_manager, config.game_directory)

        # Load data
        self.mod_repository.load()
        self.profile_manager.load()

        # Set current profile
        profiles = self.profile_manager.get_all()
        if profiles:
            # Try to load saved active profile
            if config.active_profile_id:
                try:
                    profile_id = UUID(config.active_profile_id)
                    self.current_profile = self.profile_manager.get(profile_id)
                except (ValueError, TypeError):
                    pass

            # Fall back to first profile
            if not self.current_profile:
                self.current_profile = profiles[0]
        else:
            # Create default profile
            self.current_profile = self.profile_manager.get_default_profile()

        # Update UI
        self._refresh_all()

    def _prompt_game_directory(self) -> None:
        """Prompt user to configure game directory."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Game Directory Not Found")
        msg_box.setText(
            "Monster Hunter: World installation directory not found.\n\n"
            "Would you like to auto-detect it or select it manually?"
        )
        msg_box.addButton("Auto-detect", QMessageBox.ButtonRole.AcceptRole)
        msg_box.addButton("Select Manually", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton("Later", QMessageBox.ButtonRole.RejectRole)

        result = msg_box.exec()

        if result == 0:  # Auto-detect
            detected = GameDiscovery.auto_detect()
            if detected:
                self.config_manager.update(game_directory=detected)
                logger.info(f"Auto-detected game directory: {detected}")
            else:
                QMessageBox.warning(
                    self,
                    "Auto-detect Failed",
                    "Could not auto-detect game directory. Please select it manually in Settings.",
                )
        elif result == 1:  # Manual
            self._on_settings()

    def _refresh_all(self) -> None:
        """Refresh all UI components."""
        # Profile selector
        profiles = self.profile_manager.get_all()
        current_id = self.current_profile.id if self.current_profile else None
        self.profile_selector.set_profiles(profiles, current_id)

        # Mod list
        mods = self.mod_repository.get_all()
        self.mod_list.set_mods(mods, self.current_profile)

        # Conflicts
        self._refresh_conflicts()

        # Status
        self.status_bar.showMessage(
            f"Profile: {self.current_profile.name if self.current_profile else 'None'} | "
            f"Mods: {len(mods)}"
        )

    def _refresh_conflicts(self) -> None:
        """Refresh conflict view."""
        if not self.current_profile:
            return

        mods = self.mod_repository.get_all()
        report = self.conflict_detector.analyze(mods, self.current_profile)
        self.conflict_view.set_conflict_report(report, mods)

    @Slot(UUID)
    def _on_profile_changed(self, profile_id: UUID) -> None:
        """Handle profile selection change.

        Args:
            profile_id: Selected profile ID.
        """
        profile = self.profile_manager.get(profile_id)
        if profile:
            self.current_profile = profile
            self.config_manager.update(active_profile_id=str(profile_id))
            self._refresh_all()
            logger.info(f"Switched to profile: {profile.name}")

    @Slot()
    def _on_new_profile(self) -> None:
        """Handle new profile creation."""
        name, ok = QInputDialog.getText(
            self,
            "New Profile",
            "Profile name:",
        )
        if ok and name:
            profile = self.profile_manager.create(name)
            self.current_profile = profile
            self._refresh_all()
            logger.info(f"Created new profile: {name}")

    @Slot(UUID)
    def _on_delete_profile(self, profile_id: UUID) -> None:
        """Handle profile deletion.

        Args:
            profile_id: Profile ID to delete.
        """
        profile = self.profile_manager.get(profile_id)
        if not profile:
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Are you sure you want to delete profile '{profile.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.profile_manager.delete(profile_id)

            # Switch to default profile
            self.current_profile = self.profile_manager.get_default_profile()
            self._refresh_all()
            logger.info(f"Deleted profile: {profile.name}")

    @Slot(UUID)
    def _on_rename_profile(self, profile_id: UUID) -> None:
        """Handle profile rename.

        Args:
            profile_id: Profile ID to rename.
        """
        profile = self.profile_manager.get(profile_id)
        if not profile:
            return

        name, ok = QInputDialog.getText(
            self,
            "Rename Profile",
            "New name:",
            text=profile.name,
        )
        if ok and name:
            self.profile_manager.rename(profile_id, name)
            self._refresh_all()
            logger.info(f"Renamed profile to: {name}")

    @Slot()
    def _on_add_mod(self) -> None:
        """Handle add mod action."""
        if not self.mod_installer:
            QMessageBox.warning(
                self,
                "Configuration Required",
                "Please configure the game directory in Settings first.",
            )
            return

        dialog = AddModDialog(self)
        if dialog.exec():
            path, name, is_archive = dialog.get_result()
            if path and name:
                self._install_mod(path, name, is_archive)

    def _install_mod(self, path: Path, name: str, is_archive: bool) -> None:
        """Install a mod in the background.

        Args:
            path: Path to mod archive or folder.
            name: Mod name.
            is_archive: Whether path is an archive.
        """

        def install() -> Mod:
            if is_archive:
                return self.mod_installer.install_from_zip(path, name)
            else:
                return self.mod_installer.install_from_folder(path, name)

        def on_finished(mod: Mod) -> None:
            self.mod_repository.add(mod)

            # Add to current profile
            if self.current_profile:
                self.current_profile.set_mod_enabled(mod.id, True)
                self.profile_manager.update(self.current_profile)

            self._refresh_all()
            self.status_bar.showMessage(f"Installed: {mod.name}", 3000)
            logger.info(f"Successfully installed mod: {mod.name}")

        def on_error(e: Exception) -> None:
            QMessageBox.critical(
                self,
                "Installation Failed",
                f"Failed to install mod: {e}",
            )
            logger.error(f"Mod installation failed: {e}")

        self.status_bar.showMessage(f"Installing {name}...")
        self.task_runner.run(
            install,
            on_finished=on_finished,
            on_error=on_error,
        )

    @Slot(UUID, bool)
    def _on_mod_toggled(self, mod_id: UUID, enabled: bool) -> None:
        """Handle mod enable/disable toggle.

        Args:
            mod_id: Mod ID.
            enabled: New enabled state.
        """
        if self.current_profile:
            self.current_profile.set_mod_enabled(mod_id, enabled)
            self.profile_manager.update(self.current_profile)
            self._refresh_conflicts()

            mod = self.mod_repository.get(mod_id)
            action = "enabled" if enabled else "disabled"
            logger.info(f"Mod {action}: {mod.name if mod else mod_id}")

    @Slot(UUID)
    def _on_remove_mod(self, mod_id: UUID) -> None:
        """Handle mod removal.

        Args:
            mod_id: Mod ID to remove.
        """
        mod = self.mod_repository.get(mod_id)
        if not mod:
            return

        # Confirm removal
        reply = QMessageBox.question(
            self,
            "Remove Mod",
            f"Are you sure you want to remove '{mod.name}'?\n\n"
            "This will delete the mod files from the staging directory.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Uninstall and remove
            if self.mod_installer:
                self.mod_installer.uninstall(mod)
            self.mod_repository.remove(mod_id)
            self._refresh_all()
            logger.info(f"Removed mod: {mod.name}")

    @Slot()
    def _on_deploy(self) -> None:
        """Handle deploy action."""
        if not self.deployment_engine:
            QMessageBox.warning(
                self,
                "Configuration Required",
                "Please configure the game directory in Settings first.",
            )
            return

        if not self.current_profile:
            QMessageBox.warning(self, "No Profile", "No active profile selected.")
            return

        def deploy() -> None:
            mods = self.mod_repository.get_all()
            self.deployment_engine.deploy(mods, self.current_profile)

        def on_finished(_: None) -> None:
            self.status_bar.showMessage("Deployment complete", 3000)
            logger.info("Mods deployed successfully")

        def on_error(e: Exception) -> None:
            QMessageBox.critical(self, "Deployment Failed", f"Failed to deploy mods: {e}")
            logger.error(f"Deployment failed: {e}")

        self.status_bar.showMessage("Deploying mods...")
        self.task_runner.run(
            deploy,
            on_finished=on_finished,
            on_error=on_error,
        )

    @Slot()
    def _on_undeploy(self) -> None:
        """Handle undeploy action."""
        if not self.deployment_engine:
            return

        reply = QMessageBox.question(
            self,
            "Undeploy Mods",
            "This will remove all deployed mod files from the game directory.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:

            def undeploy() -> None:
                self.deployment_engine.undeploy()

            def on_finished(_: None) -> None:
                self.status_bar.showMessage("Mods undeployed", 3000)
                logger.info("Mods undeployed successfully")

            def on_error(e: Exception) -> None:
                QMessageBox.critical(self, "Undeploy Failed", f"Failed to undeploy: {e}")
                logger.error(f"Undeploy failed: {e}")

            self.status_bar.showMessage("Undeploying mods...")
            self.task_runner.run(
                undeploy,
                on_finished=on_finished,
                on_error=on_error,
            )

    @Slot()
    def _on_settings(self) -> None:
        """Handle settings action."""
        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec():
            # Reload config-dependent services
            config = self.config_manager.get()
            if config.game_directory:
                self.mod_installer = ModInstaller(self.config_manager)
                self.deployment_engine = DeploymentEngine(
                    self.config_manager, config.game_directory
                )
                logger.info("Configuration updated")

    def closeEvent(self, event: object) -> None:
        """Handle window close event.

        Args:
            event: Close event.
        """
        # Save window size
        self.config_manager.update(
            window_width=self.width(),
            window_height=self.height(),
        )

        # Wait for background tasks
        self.task_runner.wait_for_done(5000)

        logger.info("Application closing")
        super().closeEvent(event)
