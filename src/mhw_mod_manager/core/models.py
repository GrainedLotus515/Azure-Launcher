"""Domain models for mods, profiles, and conflicts."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DeploymentMode(str, Enum):
    """Deployment strategy for mods."""

    SYMLINK = "symlink"
    COPY = "copy"


class ModStatus(str, Enum):
    """Installation status of a mod."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MISSING = "missing"
    ERROR = "error"


class Mod(BaseModel):
    """Represents a single mod installation."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    version: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None  # URL or local path reference
    tags: list[str] = Field(default_factory=list)

    # Installation metadata
    installed_at: datetime = Field(default_factory=datetime.now)
    staging_path: Path
    deployed_files: list[Path] = Field(default_factory=list)

    # Archive info
    archive_path: Optional[Path] = None
    archive_checksum: Optional[str] = None

    # Nexus Mods metadata (for tracking updates and provenance)
    nexus_mod_id: Optional[int] = None
    nexus_file_id: Optional[int] = None
    nexus_uploaded_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            Path: str,
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }


class ProfileModEntry(BaseModel):
    """Represents a mod's configuration within a profile."""

    mod_id: UUID
    enabled: bool = True
    load_order: int = 0

    class Config:
        json_encoders = {UUID: str}


class Profile(BaseModel):
    """A named collection of mod configurations."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)

    # Mod configurations for this profile
    mods: list[ProfileModEntry] = Field(default_factory=list)

    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }

    def get_mod_entry(self, mod_id: UUID) -> Optional[ProfileModEntry]:
        """Get the configuration entry for a specific mod."""
        for entry in self.mods:
            if entry.mod_id == mod_id:
                return entry
        return None

    def set_mod_enabled(self, mod_id: UUID, enabled: bool) -> None:
        """Enable or disable a mod in this profile."""
        entry = self.get_mod_entry(mod_id)
        if entry:
            entry.enabled = enabled
            self.modified_at = datetime.now()
        else:
            self.mods.append(ProfileModEntry(mod_id=mod_id, enabled=enabled))
            self.modified_at = datetime.now()

    def set_mod_load_order(self, mod_id: UUID, load_order: int) -> None:
        """Set the load order for a mod."""
        entry = self.get_mod_entry(mod_id)
        if entry:
            entry.load_order = load_order
            self.modified_at = datetime.now()

    def get_enabled_mods_ordered(self) -> list[UUID]:
        """Get list of enabled mod IDs sorted by load order."""
        enabled = [e for e in self.mods if e.enabled]
        enabled.sort(key=lambda e: e.load_order)
        return [e.mod_id for e in enabled]


class FileConflict(BaseModel):
    """Represents a conflict between multiple mods targeting the same file."""

    target_path: Path  # Relative path in game directory
    conflicting_mods: list[UUID]  # Mod IDs in load order
    winner_mod_id: UUID  # The mod that actually deploys (last in load order)

    class Config:
        json_encoders = {
            Path: str,
            UUID: str,
        }


class ConflictReport(BaseModel):
    """Collection of conflicts for a profile."""

    profile_id: UUID
    conflicts: list[FileConflict] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }

    def get_conflicts_for_mod(self, mod_id: UUID) -> list[FileConflict]:
        """Get all conflicts involving a specific mod."""
        return [c for c in self.conflicts if mod_id in c.conflicting_mods]

    def has_conflicts(self) -> bool:
        """Check if there are any conflicts."""
        return len(self.conflicts) > 0


class DeploymentState(BaseModel):
    """Tracks the current deployment state."""

    profile_id: UUID
    deployed_at: datetime = Field(default_factory=datetime.now)
    deployed_mods: list[UUID] = Field(default_factory=list)
    deployment_mode: DeploymentMode = DeploymentMode.SYMLINK

    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }


# Nexus Mods Integration Models


class NexusUser(BaseModel):
    """Represents a Nexus Mods user account."""

    user_id: int
    username: str
    is_premium: bool
    is_supporter: bool
    profile_url: str

    class Config:
        json_encoders = {}


class NexusMod(BaseModel):
    """Represents a mod from Nexus Mods."""

    mod_id: int
    name: str
    summary: str
    description: str
    author: str
    uploaded_by: str
    picture_url: Optional[str] = None
    endorsement_count: int = 0
    download_count: int = 0
    category_id: int
    version: str
    created_time: datetime
    updated_time: datetime
    game_domain: str = "monsterhunterworld"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class NexusModFile(BaseModel):
    """Represents a downloadable file for a Nexus mod."""

    file_id: int
    mod_id: int
    name: str
    version: str
    category_name: str  # main, optional, old, etc.
    size_kb: int
    size_in_bytes: Optional[int] = None
    uploaded_time: datetime
    mod_version: Optional[str] = None
    description: Optional[str] = None
    changelog_html: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class DownloadStatus(str, Enum):
    """Status of a download."""

    PENDING = "pending"  # Waiting for user action (free tier)
    QUEUED = "queued"  # In download queue
    DOWNLOADING = "downloading"  # Actively downloading
    EXTRACTING = "extracting"  # Extracting archive
    INSTALLING = "installing"  # Installing to staging
    COMPLETE = "complete"  # Successfully installed
    FAILED = "failed"  # Failed with error
    CANCELLED = "cancelled"  # Cancelled by user


class PendingDownload(BaseModel):
    """Represents a pending or active download from Nexus."""

    id: UUID = Field(default_factory=uuid4)
    mod_id: int
    file_id: int
    mod_name: str
    file_name: str
    file_version: str
    size_bytes: int
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    error_message: Optional[str] = None
    download_path: Optional[Path] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            Path: str,
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
