"""Mod detail view widget for Nexus Mods."""

import logging
import webbrowser
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.models import NexusMod, NexusModFile
from ...nexus.version_utils import SortOrder, format_version_display, sort_mod_files

logger = logging.getLogger(__name__)


class FileListItem(QWidget):
    """Widget for a file list item."""

    download_requested = Signal(int, int)  # mod_id, file_id

    def __init__(
        self,
        mod_id: int,
        mod_file: NexusModFile,
        is_premium: bool,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize file list item.

        Args:
            mod_id: Mod ID.
            mod_file: File information.
            is_premium: Whether user has premium.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.mod_id = mod_id
        self.mod_file = mod_file
        self.is_premium = is_premium
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # File info - vertically centered
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        info_layout.addStretch()

        # File name with version badge - no wrapping, will be elided
        version_display = format_version_display(self.mod_file.version)
        name_label = QLabel(f"{self.mod_file.name}  [{version_display}]")
        name_label.setProperty("heading", True)
        name_label.setWordWrap(False)
        name_label.setTextFormat(Qt.TextFormat.PlainText)
        info_layout.addWidget(name_label)

        # Details - no wrapping, will be elided
        upload_date = self.mod_file.uploaded_time.strftime("%Y-%m-%d")
        details_label = QLabel(
            f"Uploaded: {upload_date} | "
            f"Size: {self.mod_file.size_kb / 1024:.1f} MB | "
            f"Category: {self.mod_file.category_name}"
        )
        details_label.setProperty("secondary", True)
        details_label.setWordWrap(False)
        details_label.setTextFormat(Qt.TextFormat.PlainText)
        info_layout.addWidget(details_label)

        info_layout.addStretch()

        layout.addLayout(info_layout, 1)

        # Download button - fixed width and vertically centered
        if self.is_premium:
            download_btn = QPushButton("Download")
            download_btn.clicked.connect(self._on_download)
        else:
            download_btn = QPushButton("Download on Nexus")
            download_btn.clicked.connect(self._on_download_browser)
            download_btn.setProperty("outlined", True)

        download_btn.setFixedWidth(160)
        download_btn.setFixedHeight(36)
        layout.addWidget(download_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        # Set minimum height for the entire widget
        self.setMinimumHeight(80)

        # Style as card
        self.setProperty("card", True)

    def _on_download(self) -> None:
        """Handle direct download (premium)."""
        self.download_requested.emit(self.mod_id, self.mod_file.file_id)

    def _on_download_browser(self) -> None:
        """Handle browser download (free tier)."""
        url = (
            f"https://www.nexusmods.com/monsterhunterworld/mods/{self.mod_id}"
            f"?tab=files&file_id={self.mod_file.file_id}"
        )
        webbrowser.open(url)


class ModDetailViewWidget(QWidget):
    """Detail view for a single Nexus mod."""

    back_requested = Signal()
    download_requested = Signal(int, int)  # mod_id, file_id

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize mod detail view.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.current_mod: Optional[NexusMod] = None
        self.current_files: list[NexusModFile] = []
        self.is_premium = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header with back button
        header_layout = QHBoxLayout()

        back_btn = QPushButton("← Back to Browse")
        back_btn.setProperty("outlined", True)
        back_btn.setProperty("small", True)
        back_btn.setFixedHeight(32)
        back_btn.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(back_btn)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Content container
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(12)

        # Mod name
        self.name_label = QLabel()
        self.name_label.setProperty("title", True)
        self.name_label.setWordWrap(True)
        self.content_layout.addWidget(self.name_label)

        # Author and stats
        self.meta_label = QLabel()
        self.meta_label.setProperty("secondary", True)
        self.content_layout.addWidget(self.meta_label)

        # Summary
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.content_layout.addWidget(self.summary_label)

        # Description
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setTextFormat(Qt.TextFormat.RichText)
        self.description_label.setOpenExternalLinks(True)
        self.content_layout.addWidget(self.description_label)

        # Files section
        files_header = QLabel("Available Files")
        files_header.setProperty("heading", True)
        self.content_layout.addWidget(files_header)

        self.files_list = QListWidget()
        self.files_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.content_layout.addWidget(self.files_list)

        # View on Nexus button
        view_nexus_layout = QHBoxLayout()
        view_nexus_layout.addStretch()

        self.view_nexus_btn = QPushButton("View on Nexus Mods")
        self.view_nexus_btn.setProperty("outlined", True)
        self.view_nexus_btn.setProperty("small", True)
        self.view_nexus_btn.setFixedHeight(32)
        self.view_nexus_btn.clicked.connect(self._on_view_nexus)
        view_nexus_layout.addWidget(self.view_nexus_btn)

        self.content_layout.addLayout(view_nexus_layout)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def set_mod(
        self,
        mod: NexusMod,
        files: list[NexusModFile],
        is_premium: bool = False,
    ) -> None:
        """Set the mod to display.

        Args:
            mod: Mod information.
            files: List of available files.
            is_premium: Whether user has premium.
        """
        self.current_mod = mod
        self.current_files = files
        self.is_premium = is_premium

        # Update name
        self.name_label.setText(mod.name)

        # Update meta
        meta_text = (
            f"by {mod.author} | "
            f"⭐ {mod.endorsement_count} endorsements | "
            f"⬇ {mod.download_count} downloads | "
            f"Version {mod.version}"
        )
        self.meta_label.setText(meta_text)

        # Update summary
        self.summary_label.setText(mod.summary)

        # Update description (convert basic BBCode/HTML)
        description = self._format_description(mod.description)
        self.description_label.setText(description)

        # Sort files by newest version first
        sorted_files = sort_mod_files(files, order=SortOrder.NEWEST_FIRST)

        # Update files list
        self.files_list.clear()
        for mod_file in sorted_files:
            item_widget = FileListItem(mod.mod_id, mod_file, is_premium)
            item_widget.download_requested.connect(self.download_requested.emit)

            list_item = QListWidgetItem()
            # Set a proper size hint with minimum height
            size_hint = item_widget.sizeHint()
            size_hint.setHeight(max(size_hint.height(), 80))
            list_item.setSizeHint(size_hint)
            self.files_list.addItem(list_item)
            self.files_list.setItemWidget(list_item, item_widget)

    def _format_description(self, description: str) -> str:
        """Format description text.

        Args:
            description: Raw description.

        Returns:
            Formatted HTML description.
        """
        # Basic formatting - convert newlines to <br>
        if not description:
            return ""

        # Simple HTML/BBCode handling
        formatted = description.replace("\n", "<br>")

        # Limit length for display
        if len(formatted) > 1000:
            formatted = formatted[:1000] + "... <i>(view full description on Nexus)</i>"

        return formatted

    def _on_view_nexus(self) -> None:
        """Open mod page on Nexus Mods website."""
        if self.current_mod:
            url = f"https://www.nexusmods.com/monsterhunterworld/mods/{self.current_mod.mod_id}"
            webbrowser.open(url)

    def clear(self) -> None:
        """Clear the view."""
        self.current_mod = None
        self.current_files = []
        self.name_label.setText("")
        self.meta_label.setText("")
        self.summary_label.setText("")
        self.description_label.setText("")
        self.files_list.clear()
