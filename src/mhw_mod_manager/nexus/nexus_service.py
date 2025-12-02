"""Nexus Mods service integrating API, cache, and downloads."""

import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from PySide6.QtCore import QObject, Signal

from ..core.config import ConfigManager
from ..core.models import NexusMod, NexusModFile, NexusUser, PendingDownload
from ..core.mods.installer import ModInstaller
from ..core.mods.repository import ModRepository
from .api_client import NexusAPIClient, NexusAuthError
from .cache import NexusCache
from .download_manager import DownloadManager

logger = logging.getLogger(__name__)


class NexusService(QObject):
    """High-level service for Nexus Mods integration."""

    # Signals
    user_validated = Signal(NexusUser)
    mods_loaded = Signal(str, list)  # list_type, mods
    mod_details_loaded = Signal(NexusMod, list)  # mod, files
    download_started = Signal(PendingDownload)
    download_progress = Signal(UUID, float, int, int)
    download_completed = Signal(UUID, Path)
    download_failed = Signal(UUID, str)
    mod_installed = Signal(UUID)  # mod UUID
    error_occurred = Signal(str)

    def __init__(
        self,
        config_manager: ConfigManager,
        mod_installer: ModInstaller,
        mod_repository: ModRepository,
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize Nexus service.

        Args:
            config_manager: Configuration manager.
            mod_installer: Mod installer.
            mod_repository: Mod repository.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.mod_installer = mod_installer
        self.mod_repository = mod_repository

        self.api_client: Optional[NexusAPIClient] = None
        self.cache = NexusCache()
        self.download_manager = DownloadManager(config_manager)
        self.current_user: Optional[NexusUser] = None

        # Connect download manager signals
        self.download_manager.download_added.connect(self.download_started.emit)
        self.download_manager.download_progress.connect(self.download_progress.emit)
        self.download_manager.download_completed.connect(self._on_download_completed)
        self.download_manager.download_failed.connect(self.download_failed.emit)

        # Initialize if API key is configured
        self._initialize_from_config()

    def _initialize_from_config(self) -> None:
        """Initialize API client from config if available."""
        config = self.config_manager.get()
        if config.nexus_api_key:
            try:
                self.set_api_key(config.nexus_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Nexus API client: {e}")

    def set_api_key(self, api_key: str) -> NexusUser:
        """Set API key and validate.

        Args:
            api_key: Nexus API key.

        Returns:
            User information.

        Raises:
            NexusAuthError: If API key is invalid.
        """
        self.api_client = NexusAPIClient(api_key)
        self.download_manager.api_client = self.api_client

        # Validate and get user info
        self.current_user = self.api_client.validate_api_key()
        self.user_validated.emit(self.current_user)

        logger.info(f"Nexus API client initialized for user: {self.current_user.username}")
        return self.current_user

    def is_configured(self) -> bool:
        """Check if Nexus integration is configured.

        Returns:
            True if API client is initialized.
        """
        return self.api_client is not None

    def is_premium(self) -> bool:
        """Check if user has premium.

        Returns:
            True if user has premium.
        """
        return self.current_user is not None and self.current_user.is_premium

    def load_trending_mods(self, use_cache: bool = True) -> list[NexusMod]:
        """Load trending mods.

        Args:
            use_cache: Whether to use cached data.

        Returns:
            List of trending mods.
        """
        if not self.api_client:
            raise RuntimeError("Nexus API not configured")

        # Try cache first
        if use_cache:
            cached = self.cache.get_mod_list("trending", max_age_minutes=15)
            if cached:
                logger.debug("Loaded trending mods from cache")
                self.mods_loaded.emit("trending", cached)
                return cached

        # Fetch from API
        try:
            mods = self.api_client.get_trending_mods()
            self.cache.cache_mod_list("trending", mods)
            logger.info(f"Loaded {len(mods)} trending mods")
            self.mods_loaded.emit("trending", mods)
            return mods
        except Exception as e:
            error_msg = f"Failed to load trending mods: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []

    def load_latest_mods(self, use_cache: bool = True) -> list[NexusMod]:
        """Load latest mods.

        Args:
            use_cache: Whether to use cached data.

        Returns:
            List of latest mods.
        """
        if not self.api_client:
            raise RuntimeError("Nexus API not configured")

        if use_cache:
            cached = self.cache.get_mod_list("latest", max_age_minutes=15)
            if cached:
                logger.debug("Loaded latest mods from cache")
                self.mods_loaded.emit("latest", cached)
                return cached

        try:
            mods = self.api_client.get_latest_added_mods()
            self.cache.cache_mod_list("latest", mods)
            logger.info(f"Loaded {len(mods)} latest mods")
            self.mods_loaded.emit("latest", mods)
            return mods
        except Exception as e:
            error_msg = f"Failed to load latest mods: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []

    def load_updated_mods(self, period: str = "1d", use_cache: bool = True) -> list[NexusMod]:
        """Load recently updated mods.

        Args:
            period: Time period (1d, 1w, 1m).
            use_cache: Whether to use cached data.

        Returns:
            List of updated mods.
        """
        if not self.api_client:
            raise RuntimeError("Nexus API not configured")

        cache_key = f"updated_{period}"

        if use_cache:
            cached = self.cache.get_mod_list(cache_key, max_age_minutes=15)
            if cached:
                logger.debug("Loaded updated mods from cache")
                self.mods_loaded.emit("updated", cached)
                return cached

        try:
            mods = self.api_client.get_updated_mods(period)
            self.cache.cache_mod_list(cache_key, mods)
            logger.info(f"Loaded {len(mods)} updated mods")
            self.mods_loaded.emit("updated", mods)
            return mods
        except Exception as e:
            error_msg = f"Failed to load updated mods: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []

    def load_mod_details(
        self, mod_id: int, use_cache: bool = True
    ) -> tuple[NexusMod, list[NexusModFile]]:
        """Load detailed information about a mod.

        Args:
            mod_id: Mod ID.
            use_cache: Whether to use cached data.

        Returns:
            Tuple of (mod, files).
        """
        if not self.api_client:
            raise RuntimeError("Nexus API not configured")

        # Try cache
        if use_cache:
            cached_mod = self.cache.get_mod(mod_id, max_age_hours=1)
            cached_files = self.cache.get_mod_files(mod_id, max_age_minutes=15)

            if cached_mod and cached_files:
                logger.debug(f"Loaded mod {mod_id} details from cache")
                self.mod_details_loaded.emit(cached_mod, cached_files)
                return cached_mod, cached_files

        # Fetch from API
        try:
            mod = self.api_client.get_mod(mod_id)
            files = self.api_client.get_mod_files(mod_id)

            # Cache results
            self.cache.cache_mod(mod)
            self.cache.cache_mod_files(mod_id, files)

            logger.info(f"Loaded mod details for '{mod.name}' with {len(files)} files")
            self.mod_details_loaded.emit(mod, files)
            return mod, files
        except Exception as e:
            error_msg = f"Failed to load mod details: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            raise

    def create_download(self, mod: NexusMod, mod_file: NexusModFile) -> PendingDownload:
        """Create a pending download.

        Args:
            mod: Mod to download.
            mod_file: File to download.

        Returns:
            Pending download entry.
        """
        download = self.download_manager.create_pending_download(mod, mod_file)
        return download

    def start_premium_download(self, download_id: UUID) -> None:
        """Start a premium download (direct download).

        Args:
            download_id: Download ID.
        """
        if not self.is_premium():
            logger.error("Premium download requested but user is not premium")
            self.error_occurred.emit("Premium account required for direct downloads")
            return

        self.download_manager.download_premium(
            download_id,
            on_complete=lambda path: self._install_downloaded_mod(download_id, path),
            on_error=lambda err: logger.error(f"Download failed: {err}"),
        )

    def handle_nxm_link(self, nxm_url: str) -> None:
        """Handle an NXM protocol link.

        Args:
            nxm_url: NXM URL.
        """
        download_id = self.download_manager.download_from_nxm(
            nxm_url,
            on_complete=lambda path: self._install_downloaded_mod(download_id, path),
            on_error=lambda err: logger.error(f"NXM download failed: {err}"),
        )

        if download_id:
            logger.info(f"Started NXM download: {download_id}")

    def _on_download_completed(self, download_id: UUID, file_path: Path) -> None:
        """Handle download completion.

        Args:
            download_id: Download ID.
            file_path: Downloaded file path.
        """
        logger.info(f"Download completed: {file_path}")
        self.download_completed.emit(download_id, file_path)

    def _install_downloaded_mod(self, download_id: UUID, file_path: Path) -> None:
        """Install a downloaded mod.

        Args:
            download_id: Download ID.
            file_path: Path to downloaded file.
        """
        download = self.download_manager.get_download(download_id)
        if not download:
            logger.error(f"Download {download_id} not found")
            return

        try:
            # Try to get additional mod info from cache
            author = None
            cached_mod = self.cache.get_mod(download.mod_id, max_age_hours=24)
            if cached_mod:
                author = cached_mod.author

            # Get upload time from cached file info if available
            uploaded_at = None
            cached_files = self.cache.get_mod_files(download.mod_id, max_age_minutes=60)
            if cached_files:
                for cf in cached_files:
                    if cf.file_id == download.file_id:
                        uploaded_at = cf.uploaded_time
                        break

            # Install the mod with version metadata
            mod = self.mod_installer.install_from_zip(
                file_path,
                name=download.mod_name,
                version=download.file_version if download.file_version else None,
                author=author,
                nexus_mod_id=download.mod_id,
                nexus_file_id=download.file_id,
                nexus_uploaded_at=uploaded_at,
            )

            # Add to repository
            self.mod_repository.add(mod)

            logger.info(f"Installed downloaded mod: {mod.name} (version: {mod.version})")
            self.mod_installed.emit(mod.id)

        except Exception as e:
            error_msg = f"Failed to install downloaded mod: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)

    def get_all_downloads(self) -> list[PendingDownload]:
        """Get all downloads.

        Returns:
            List of all downloads.
        """
        return self.download_manager.get_all_downloads()

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache.clear_all()
        logger.info("Nexus cache cleared")
