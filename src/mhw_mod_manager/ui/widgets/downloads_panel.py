"""Downloads panel widget for tracking Nexus downloads."""

import logging
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.models import DownloadStatus, PendingDownload
from ...nexus.version_utils import format_version_display

logger = logging.getLogger(__name__)


class DownloadItemWidget(QWidget):
    """Widget representing a single download item."""

    def __init__(self, download: PendingDownload, parent: Optional[QWidget] = None) -> None:
        """Initialize download item widget.

        Args:
            download: Download information.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.download = download
        self._setup_ui()
        self.update_from_download(download)

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Apply card styling
        self.setProperty("card", True)

        # Top row: name and status
        top_layout = QHBoxLayout()

        self.name_label = QLabel()
        self.name_label.setWordWrap(True)
        top_layout.addWidget(self.name_label, 1)

        self.status_label = QLabel()
        self.status_label.setProperty("secondary", True)
        top_layout.addWidget(self.status_label)

        layout.addLayout(top_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        # Bottom row: size info and action button
        bottom_layout = QHBoxLayout()

        self.size_label = QLabel()
        self.size_label.setProperty("secondary", True)
        bottom_layout.addWidget(self.size_label, 1)

        self.action_button = QPushButton()
        self.action_button.setProperty("outlined", True)
        self.action_button.setProperty("small", True)
        self.action_button.setFixedHeight(28)
        bottom_layout.addWidget(self.action_button)

        layout.addLayout(bottom_layout)

    def update_from_download(self, download: PendingDownload) -> None:
        """Update widget from download state.

        Args:
            download: Download information.
        """
        self.download = download

        # Update name with version prominently displayed
        version_display = format_version_display(download.file_version)
        self.name_label.setText(f"{download.mod_name} [{version_display}] - {download.file_name}")

        # Update status
        status_text = self._get_status_text(download.status)
        self.status_label.setText(status_text)

        # Update progress
        progress_pct = int(download.progress * 100)
        self.progress_bar.setValue(progress_pct)

        # Update size
        if download.size_bytes > 0:
            size_mb = download.size_bytes / (1024 * 1024)
            downloaded_mb = (download.size_bytes * download.progress) / (1024 * 1024)
            self.size_label.setText(f"{downloaded_mb:.1f} / {size_mb:.1f} MB")
        else:
            self.size_label.setText("Size unknown")

        # Update action button
        self._update_action_button(download.status)

    def _get_status_text(self, status: DownloadStatus) -> str:
        """Get human-readable status text.

        Args:
            status: Download status.

        Returns:
            Status text.
        """
        status_map = {
            DownloadStatus.PENDING: "Waiting for download",
            DownloadStatus.QUEUED: "Queued",
            DownloadStatus.DOWNLOADING: "Downloading",
            DownloadStatus.EXTRACTING: "Extracting",
            DownloadStatus.INSTALLING: "Installing",
            DownloadStatus.COMPLETE: "Complete",
            DownloadStatus.FAILED: "Failed",
            DownloadStatus.CANCELLED: "Cancelled",
        }
        return status_map.get(status, str(status))

    def _update_action_button(self, status: DownloadStatus) -> None:
        """Update action button based on status.

        Args:
            status: Download status.
        """
        if status == DownloadStatus.PENDING:
            self.action_button.setText("Open Nexus")
            self.action_button.setVisible(True)
        elif status in (DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED):
            self.action_button.setText("Cancel")
            self.action_button.setVisible(True)
        elif status == DownloadStatus.FAILED:
            self.action_button.setText("Retry")
            self.action_button.setVisible(True)
        elif status in (DownloadStatus.COMPLETE, DownloadStatus.CANCELLED):
            self.action_button.setText("Remove")
            self.action_button.setVisible(True)
        else:
            self.action_button.setVisible(False)


class DownloadsPanelWidget(QWidget):
    """Panel widget for managing downloads."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize downloads panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.download_widgets: dict[UUID, DownloadItemWidget] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Downloads")
        header_label.setProperty("heading", True)
        header_layout.addWidget(header_label)

        clear_completed_btn = QPushButton("Clear Completed")
        clear_completed_btn.setProperty("outlined", True)
        clear_completed_btn.setProperty("small", True)
        clear_completed_btn.setFixedHeight(32)
        header_layout.addWidget(clear_completed_btn)

        layout.addLayout(header_layout)

        # Scroll area for downloads
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container for download items
        self.downloads_container = QWidget()
        self.downloads_layout = QVBoxLayout(self.downloads_container)
        self.downloads_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.downloads_layout.setSpacing(8)
        self.downloads_layout.setContentsMargins(4, 4, 4, 4)

        scroll_area.setWidget(self.downloads_container)
        layout.addWidget(scroll_area)

        # Empty state
        self.empty_label = QLabel("No downloads")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setProperty("secondary", True)
        self.downloads_layout.addWidget(self.empty_label)

    def add_download(self, download: PendingDownload) -> None:
        """Add a download to the panel.

        Args:
            download: Download to add.
        """
        if download.id in self.download_widgets:
            return

        # Hide empty state
        self.empty_label.setVisible(False)

        # Create widget
        widget = DownloadItemWidget(download)
        self.download_widgets[download.id] = widget
        self.downloads_layout.addWidget(widget)

        logger.debug(f"Added download widget for {download.id}")

    def update_download(self, download: PendingDownload) -> None:
        """Update a download's display.

        Args:
            download: Updated download.
        """
        widget = self.download_widgets.get(download.id)
        if widget:
            widget.update_from_download(download)

    def remove_download(self, download_id: UUID) -> None:
        """Remove a download from the panel.

        Args:
            download_id: Download ID to remove.
        """
        widget = self.download_widgets.get(download_id)
        if widget:
            self.downloads_layout.removeWidget(widget)
            widget.deleteLater()
            del self.download_widgets[download_id]

        # Show empty state if no downloads
        if not self.download_widgets:
            self.empty_label.setVisible(True)

    def set_downloads(self, downloads: list[PendingDownload]) -> None:
        """Set the complete list of downloads.

        Args:
            downloads: List of downloads to display.
        """
        # Clear existing
        for widget in self.download_widgets.values():
            self.downloads_layout.removeWidget(widget)
            widget.deleteLater()
        self.download_widgets.clear()

        # Add new downloads
        for download in downloads:
            self.add_download(download)

        # Update empty state
        self.empty_label.setVisible(len(downloads) == 0)

    @Slot(UUID, float, int, int)
    def on_download_progress(
        self, download_id: UUID, progress: float, downloaded: int, total: int
    ) -> None:
        """Handle download progress update.

        Args:
            download_id: Download ID.
            progress: Progress (0.0 to 1.0).
            downloaded: Bytes downloaded.
            total: Total bytes.
        """
        widget = self.download_widgets.get(download_id)
        if widget:
            widget.download.progress = progress
            widget.update_from_download(widget.download)

    @Slot(UUID, DownloadStatus)
    def on_download_status_changed(self, download_id: UUID, status: DownloadStatus) -> None:
        """Handle download status change.

        Args:
            download_id: Download ID.
            status: New status.
        """
        widget = self.download_widgets.get(download_id)
        if widget:
            widget.download.status = status
            widget.update_from_download(widget.download)
