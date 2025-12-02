"""Download manager for Nexus Mods."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import httpx
from PySide6.QtCore import QObject, Signal

from ..core.config import ConfigManager
from ..core.models import DownloadStatus, NexusMod, NexusModFile, PendingDownload
from .api_client import NexusAPIClient

logger = logging.getLogger(__name__)


class DownloadProgress:
    """Progress information for a download."""

    def __init__(self, download_id: UUID, total_bytes: int) -> None:
        """Initialize progress tracker.

        Args:
            download_id: Download ID.
            total_bytes: Total size in bytes.
        """
        self.download_id = download_id
        self.total_bytes = total_bytes
        self.downloaded_bytes = 0
        self.progress = 0.0

    def update(self, bytes_downloaded: int) -> None:
        """Update progress.

        Args:
            bytes_downloaded: Cumulative bytes downloaded.
        """
        self.downloaded_bytes = bytes_downloaded
        if self.total_bytes > 0:
            self.progress = min(1.0, self.downloaded_bytes / self.total_bytes)


class DownloadManager(QObject):
    """Manages downloading mods from Nexus."""

    # Signals
    download_added = Signal(PendingDownload)
    download_progress = Signal(UUID, float, int, int)  # id, progress, downloaded, total
    download_status_changed = Signal(UUID, DownloadStatus)
    download_completed = Signal(UUID, Path)
    download_failed = Signal(UUID, str)

    def __init__(
        self, config_manager: ConfigManager, api_client: Optional[NexusAPIClient] = None
    ) -> None:
        """Initialize the download manager.

        Args:
            config_manager: Configuration manager.
            api_client: Nexus API client (optional).
        """
        super().__init__()
        self.config_manager = config_manager
        self.api_client = api_client
        self.downloads: dict[UUID, PendingDownload] = {}
        self._active_downloads = 0
        self._max_concurrent = 2  # Respect Nexus ToS

    def create_pending_download(self, mod: NexusMod, mod_file: NexusModFile) -> PendingDownload:
        """Create a pending download entry.

        Args:
            mod: Mod information.
            mod_file: File to download.

        Returns:
            Pending download entry.
        """
        download = PendingDownload(
            mod_id=mod.mod_id,
            file_id=mod_file.file_id,
            mod_name=mod.name,
            file_name=mod_file.name,
            file_version=mod_file.version,
            size_bytes=mod_file.size_in_bytes or 0,
            status=DownloadStatus.PENDING,
        )

        self.downloads[download.id] = download
        self.download_added.emit(download)
        logger.info(f"Created pending download: {mod.name} - {mod_file.name} (ID: {download.id})")
        return download

    def download_premium(
        self,
        download_id: UUID,
        on_complete: Optional[Callable[[Path], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Download a file using premium API (direct download).

        Args:
            download_id: Download ID.
            on_complete: Callback on successful download.
            on_error: Callback on error.
        """
        download = self.downloads.get(download_id)
        if not download:
            logger.error(f"Download {download_id} not found")
            return

        if not self.api_client:
            error_msg = "API client not configured"
            self._handle_download_error(download, error_msg, on_error)
            return

        try:
            # Update status
            download.status = DownloadStatus.QUEUED
            download.started_at = datetime.now()
            self.download_status_changed.emit(download_id, download.status)

            # Get download URLs (premium users don't need key/expires)
            logger.info(
                f"Requesting download link for mod {download.mod_id}, file {download.file_id}"
            )
            urls = self.api_client.get_download_link(
                download.mod_id,
                download.file_id,
                key=None,
                expires=None,
            )

            if not urls:
                raise ValueError("No download URLs returned from API")

            logger.info(f"Received {len(urls)} download URL(s)")
            download_url = urls[0]  # Use first CDN

            # Download file
            self._download_file(download, download_url, on_complete, on_error)

        except Exception as e:
            # Provide user-friendly error messages
            error_str = str(e)
            if "404" in error_str or "not found" in error_str.lower():
                error_msg = (
                    "This file is no longer available for download via API. "
                    "It may have been removed or updated. Try downloading from the Nexus website instead."
                )
            elif "401" in error_str or "unauthorized" in error_str.lower():
                error_msg = "Authentication failed. Please check your API key in Settings."
            elif "403" in error_str or "forbidden" in error_str.lower():
                error_msg = "Access denied. This file may require premium membership."
            else:
                error_msg = f"Failed to get download URL: {e}"

            self._handle_download_error(download, error_msg, on_error)

    def download_from_nxm(
        self,
        nxm_url: str,
        on_complete: Optional[Callable[[Path], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> Optional[UUID]:
        """Download a file from an NXM protocol link.

        Args:
            nxm_url: NXM protocol URL.
            on_complete: Callback on successful download.
            on_error: Callback on error.

        Returns:
            Download ID if successful, None otherwise.
        """
        try:
            # Parse NXM URL: nxm://monsterhunterworld/mods/{mod_id}/files/{file_id}?key=...
            parsed = urlparse(nxm_url)
            if parsed.scheme != "nxm":
                raise ValueError("Invalid NXM URL scheme")

            # Extract mod_id and file_id from path
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) < 4 or path_parts[0] != "mods" or path_parts[2] != "files":
                raise ValueError("Invalid NXM URL format")

            mod_id = int(path_parts[1])
            file_id = int(path_parts[3])

            # Extract query parameters
            query_params = parse_qs(parsed.query)
            key = query_params.get("key", [None])[0]
            expires = query_params.get("expires", [None])[0]
            user_id = query_params.get("user_id", [None])[0]

            if not key or not expires:
                raise ValueError("Missing required NXM parameters")

            # Find or create download entry
            download = self._find_download(mod_id, file_id)
            if not download:
                logger.warning(f"No pending download found for mod {mod_id}, file {file_id}")
                # Create a basic entry
                download = PendingDownload(
                    mod_id=mod_id,
                    file_id=file_id,
                    mod_name=f"Mod {mod_id}",
                    file_name=f"File {file_id}",
                    file_version="unknown",
                    size_bytes=0,
                    status=DownloadStatus.QUEUED,
                )
                self.downloads[download.id] = download
                self.download_added.emit(download)

            # Construct download URL
            download_url = (
                f"https://www.nexusmods.com/{parsed.netloc}/mods/{mod_id}/files/{file_id}"
                f"?key={key}&expires={expires}&user_id={user_id}"
            )

            # Start download
            download.status = DownloadStatus.QUEUED
            download.started_at = datetime.now()
            self.download_status_changed.emit(download.id, download.status)

            self._download_file(download, download_url, on_complete, on_error)
            return download.id

        except Exception as e:
            error_msg = f"Failed to parse NXM URL: {e}"
            logger.error(error_msg)
            if on_error:
                on_error(error_msg)
            return None

    def _find_download(self, mod_id: int, file_id: int) -> Optional[PendingDownload]:
        """Find a download by mod and file ID.

        Args:
            mod_id: Mod ID.
            file_id: File ID.

        Returns:
            Download if found, None otherwise.
        """
        for download in self.downloads.values():
            if download.mod_id == mod_id and download.file_id == file_id:
                return download
        return None

    def _download_file(
        self,
        download: PendingDownload,
        url: str,
        on_complete: Optional[Callable[[Path], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Download a file from URL.

        Args:
            download: Download entry.
            url: Download URL.
            on_complete: Callback on success.
            on_error: Callback on error.
        """
        config = self.config_manager.get()
        download_dir = config.downloads_directory
        download_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        filename = f"{download.mod_name}_{download.file_name}".replace(" ", "_")
        # Remove invalid characters
        filename = "".join(c for c in filename if c.isalnum() or c in ("_", "-", "."))
        if not filename.endswith(".zip"):
            filename += ".zip"

        download_path = download_dir / filename

        try:
            download.status = DownloadStatus.DOWNLOADING
            self.download_status_changed.emit(download.id, download.status)

            # Download with progress tracking
            with httpx.stream("GET", url, follow_redirects=True, timeout=300.0) as response:
                response.raise_for_status()

                total_bytes = int(response.headers.get("content-length", 0))
                if total_bytes == 0 and download.size_bytes > 0:
                    total_bytes = download.size_bytes

                downloaded_bytes = 0

                with open(download_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded_bytes += len(chunk)

                        # Emit progress
                        if total_bytes > 0:
                            progress = downloaded_bytes / total_bytes
                            self.download_progress.emit(
                                download.id, progress, downloaded_bytes, total_bytes
                            )
                            download.progress = progress

            # Download complete
            download.status = DownloadStatus.COMPLETE
            download.download_path = download_path
            download.completed_at = datetime.now()
            self.download_status_changed.emit(download.id, download.status)
            self.download_completed.emit(download.id, download_path)

            logger.info(f"Download completed: {download_path}")

            if on_complete:
                on_complete(download_path)

        except Exception as e:
            error_msg = f"Download failed: {e}"
            self._handle_download_error(download, error_msg, on_error)

    def _handle_download_error(
        self,
        download: PendingDownload,
        error_msg: str,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Handle download error.

        Args:
            download: Download entry.
            error_msg: Error message.
            on_error: Error callback.
        """
        logger.error(f"Download {download.id} failed: {error_msg}")
        download.status = DownloadStatus.FAILED
        download.error_message = error_msg
        self.download_status_changed.emit(download.id, download.status)
        self.download_failed.emit(download.id, error_msg)

        if on_error:
            on_error(error_msg)

    def cancel_download(self, download_id: UUID) -> bool:
        """Cancel a download.

        Args:
            download_id: Download ID.

        Returns:
            True if cancelled successfully.
        """
        download = self.downloads.get(download_id)
        if not download:
            return False

        if download.status in (DownloadStatus.COMPLETE, DownloadStatus.FAILED):
            return False

        download.status = DownloadStatus.CANCELLED
        self.download_status_changed.emit(download_id, download.status)
        logger.info(f"Download cancelled: {download_id}")
        return True

    def get_download(self, download_id: UUID) -> Optional[PendingDownload]:
        """Get a download by ID.

        Args:
            download_id: Download ID.

        Returns:
            Download if found.
        """
        return self.downloads.get(download_id)

    def get_all_downloads(self) -> list[PendingDownload]:
        """Get all downloads.

        Returns:
            List of all downloads.
        """
        return list(self.downloads.values())

    def get_pending_downloads(self) -> list[PendingDownload]:
        """Get downloads waiting for user action.

        Returns:
            List of pending downloads.
        """
        return [d for d in self.downloads.values() if d.status == DownloadStatus.PENDING]

    def remove_download(self, download_id: UUID) -> bool:
        """Remove a download from the list.

        Args:
            download_id: Download ID.

        Returns:
            True if removed.
        """
        if download_id in self.downloads:
            del self.downloads[download_id]
            return True
        return False
