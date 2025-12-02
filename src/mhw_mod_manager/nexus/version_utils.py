"""Version parsing and comparison utilities for Nexus Mods files.

This module provides robust version parsing and comparison functionality
for sorting Nexus mod files by newest version. It handles various version
formats including semantic versions, date-based versions, and non-standard
formats gracefully.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Optional

from ..core.models import NexusModFile

logger = logging.getLogger(__name__)


class SortOrder(IntEnum):
    """Sort order options for file lists."""

    NEWEST_FIRST = 1
    OLDEST_FIRST = 2


@dataclass(frozen=True)
class ParsedVersion:
    """Represents a parsed version with comparable components.

    Attributes:
        major: Major version number (e.g., 1 in 1.2.3).
        minor: Minor version number (e.g., 2 in 1.2.3).
        patch: Patch version number (e.g., 3 in 1.2.3).
        prerelease: Pre-release tag (e.g., "alpha", "beta", "rc1").
        build: Build metadata or additional version info.
        original: The original version string.
        is_parsed: Whether the version was successfully parsed as semver.
    """

    major: int = 0
    minor: int = 0
    patch: int = 0
    prerelease: str = ""
    build: str = ""
    original: str = ""
    is_parsed: bool = False

    def __lt__(self, other: "ParsedVersion") -> bool:
        """Compare versions for sorting (less than).

        Pre-release versions are considered older than release versions.
        """
        if not isinstance(other, ParsedVersion):
            return NotImplemented

        # If neither is parsed, compare original strings
        if not self.is_parsed and not other.is_parsed:
            return self.original.lower() < other.original.lower()

        # Parsed versions are "greater" than unparsed ones (sort first)
        if self.is_parsed != other.is_parsed:
            return not self.is_parsed  # Unparsed < Parsed

        # Compare major.minor.patch
        self_tuple = (self.major, self.minor, self.patch)
        other_tuple = (other.major, other.minor, other.patch)

        if self_tuple != other_tuple:
            return self_tuple < other_tuple

        # If one has prerelease and other doesn't, release is newer
        if self.prerelease and not other.prerelease:
            return True  # self is older (prerelease)
        if not self.prerelease and other.prerelease:
            return False  # self is newer (release)

        # Both have prerelease or neither does
        return self.prerelease.lower() < other.prerelease.lower()

    def __eq__(self, other: object) -> bool:
        """Check version equality."""
        if not isinstance(other, ParsedVersion):
            return NotImplemented

        if self.is_parsed and other.is_parsed:
            return (
                self.major == other.major
                and self.minor == other.minor
                and self.patch == other.patch
                and self.prerelease.lower() == other.prerelease.lower()
            )

        return self.original.lower() == other.original.lower()

    def __le__(self, other: "ParsedVersion") -> bool:
        """Compare versions (less than or equal)."""
        return self == other or self < other

    def __gt__(self, other: "ParsedVersion") -> bool:
        """Compare versions (greater than)."""
        return not self <= other

    def __ge__(self, other: "ParsedVersion") -> bool:
        """Compare versions (greater than or equal)."""
        return not self < other


# Regex patterns for version parsing
SEMVER_PATTERN = re.compile(
    r"""
    ^
    [vV]?                           # Optional 'v' or 'V' prefix
    (?P<major>\d+)                  # Major version (required)
    (?:\.(?P<minor>\d+))?           # Minor version (optional)
    (?:\.(?P<patch>\d+))?           # Patch version (optional)
    (?:[-_.]?(?P<prerelease>        # Pre-release (optional)
        (?:alpha|beta|rc|pre|dev|snapshot|a|b|c)
        (?:[-_.]?\d+)?
    ))?
    (?:\+(?P<build>.+))?            # Build metadata (optional)
    $
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Pattern for date-based versions
DATE_VERSION_PATTERN = re.compile(
    r"""
    ^
    [vV]?                           # Optional 'v' prefix
    (?P<year>\d{4})                 # Year
    [-_.]?(?P<month>\d{2})          # Month
    [-_.]?(?P<day>\d{2})            # Day
    (?:[-_.]?(?P<extra>.+))?        # Extra info
    $
    """,
    re.VERBOSE,
)

# Pattern for simple numeric versions (e.g., "2", "10")
SIMPLE_NUMERIC_PATTERN = re.compile(r"^[vV]?(\d+)$")


def parse_version(version_string: str) -> ParsedVersion:
    """Parse a version string into comparable components.

    Handles various version formats:
    - Semantic versions: "1.0.0", "2.3.1", "1.0.0-beta.1"
    - Prefixed versions: "v1.2.3", "V2.0"
    - Partial versions: "1.0", "2"
    - Pre-release tags: "1.0-alpha", "2.0-rc1", "3.0a"
    - Date versions: "2024.01.15", "20240115"
    - Non-standard: "Final", "Release", etc.

    Args:
        version_string: The version string to parse.

    Returns:
        ParsedVersion with extracted components.
    """
    if not version_string:
        return ParsedVersion(original=version_string, is_parsed=False)

    # Clean up the version string
    cleaned = version_string.strip()

    # Try semantic version pattern first
    match = SEMVER_PATTERN.match(cleaned)
    if match:
        groups = match.groupdict()
        return ParsedVersion(
            major=int(groups["major"]),
            minor=int(groups["minor"] or 0),
            patch=int(groups["patch"] or 0),
            prerelease=groups["prerelease"] or "",
            build=groups["build"] or "",
            original=version_string,
            is_parsed=True,
        )

    # Try date-based version
    match = DATE_VERSION_PATTERN.match(cleaned)
    if match:
        groups = match.groupdict()
        # Convert date to comparable numbers
        # Year as major, month as minor, day as patch
        return ParsedVersion(
            major=int(groups["year"]),
            minor=int(groups["month"]),
            patch=int(groups["day"]),
            prerelease=groups["extra"] or "",
            original=version_string,
            is_parsed=True,
        )

    # Try simple numeric version
    match = SIMPLE_NUMERIC_PATTERN.match(cleaned)
    if match:
        return ParsedVersion(
            major=int(match.group(1)),
            original=version_string,
            is_parsed=True,
        )

    # Couldn't parse - return unparsed version
    logger.debug(f"Could not parse version string: '{version_string}'")
    return ParsedVersion(original=version_string, is_parsed=False)


def compare_versions(version1: str, version2: str) -> int:
    """Compare two version strings.

    Args:
        version1: First version string.
        version2: Second version string.

    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    """
    parsed1 = parse_version(version1)
    parsed2 = parse_version(version2)

    if parsed1 < parsed2:
        return -1
    elif parsed1 > parsed2:
        return 1
    else:
        return 0


def format_version_display(version: str) -> str:
    """Format a version string for display in the UI.

    Ensures consistent formatting with 'v' prefix for cleaner display.

    Args:
        version: The version string to format.

    Returns:
        Formatted version string (e.g., "v1.2.3").
    """
    if not version:
        return "Unknown"

    cleaned = version.strip()

    # Already has a version prefix
    if cleaned.lower().startswith("v"):
        return cleaned

    # Check if it looks like a version number
    parsed = parse_version(cleaned)
    if parsed.is_parsed:
        return f"v{cleaned}"

    # Return as-is for non-standard versions
    return cleaned


@dataclass
class ModFileSortKey:
    """Sort key for NexusModFile objects.

    Provides a composite key for sorting mod files by version (primary)
    and upload date (secondary fallback).
    """

    parsed_version: ParsedVersion
    uploaded_time: datetime
    file_id: int

    def __lt__(self, other: "ModFileSortKey") -> bool:
        """Compare sort keys (for sorting newest first)."""
        if not isinstance(other, ModFileSortKey):
            return NotImplemented

        # If both versions are parsed, compare by version
        if self.parsed_version.is_parsed and other.parsed_version.is_parsed:
            if self.parsed_version != other.parsed_version:
                # Note: We want NEWEST first, so greater version comes first
                return self.parsed_version > other.parsed_version

        # If one is parsed and one isn't, parsed comes first
        if self.parsed_version.is_parsed != other.parsed_version.is_parsed:
            return self.parsed_version.is_parsed

        # Fall back to upload time (newest first)
        if self.uploaded_time != other.uploaded_time:
            return self.uploaded_time > other.uploaded_time

        # Final fallback: file_id (highest first, usually newest)
        return self.file_id > other.file_id


def create_sort_key(mod_file: NexusModFile) -> ModFileSortKey:
    """Create a sort key for a NexusModFile.

    Args:
        mod_file: The mod file to create a sort key for.

    Returns:
        ModFileSortKey for comparison.
    """
    # Use file version or mod_version, preferring file version
    version_str = mod_file.version or mod_file.mod_version or ""
    parsed = parse_version(version_str)

    return ModFileSortKey(
        parsed_version=parsed,
        uploaded_time=mod_file.uploaded_time,
        file_id=mod_file.file_id,
    )


def sort_mod_files(
    files: list[NexusModFile],
    order: SortOrder = SortOrder.NEWEST_FIRST,
    category_order: Optional[list[str]] = None,
) -> list[NexusModFile]:
    """Sort mod files by version and upload date.

    Primary sort is by parsed semantic version (newest first by default).
    Falls back to upload date when versions can't be compared.
    Optionally groups by file category.

    Args:
        files: List of NexusModFile objects to sort.
        order: Sort order (NEWEST_FIRST or OLDEST_FIRST).
        category_order: Optional list of category names to group by.
                       Common values: ["main", "update", "optional", "old"]
                       Files in categories not listed appear at the end.

    Returns:
        Sorted list of NexusModFile objects.
    """
    if not files:
        return []

    # Default category ordering (main files first, old files last)
    if category_order is None:
        category_order = ["main", "update", "optional", "miscellaneous", "old"]

    def get_category_priority(category_name: str) -> int:
        """Get sort priority for a category (lower = first)."""
        category_lower = category_name.lower()
        try:
            return category_order.index(category_lower)
        except ValueError:
            # Unknown categories go after known ones
            return len(category_order)

    # Create list of (file, sort_key, category_priority)
    sortable = [(f, create_sort_key(f), get_category_priority(f.category_name)) for f in files]

    # Sort by category first, then by version/date
    # For OLDEST_FIRST, we reverse the sort key comparison
    if order == SortOrder.NEWEST_FIRST:
        sortable.sort(key=lambda x: (x[2], x[1]))
    else:
        # For oldest first, we need to invert the comparison
        # We can't easily invert ModFileSortKey, so we sort descending
        sortable.sort(key=lambda x: (x[2], x[1]), reverse=True)

    return [item[0] for item in sortable]


def get_newest_file(
    files: list[NexusModFile],
    category: Optional[str] = None,
) -> Optional[NexusModFile]:
    """Get the newest file from a list, optionally filtered by category.

    Args:
        files: List of NexusModFile objects.
        category: Optional category to filter by (e.g., "main").

    Returns:
        The newest NexusModFile, or None if list is empty.
    """
    if not files:
        return None

    # Filter by category if specified
    if category:
        files = [f for f in files if f.category_name.lower() == category.lower()]
        if not files:
            return None

    sorted_files = sort_mod_files(files, SortOrder.NEWEST_FIRST)
    return sorted_files[0] if sorted_files else None


def is_newer_version(version1: str, version2: str) -> bool:
    """Check if version1 is newer than version2.

    Args:
        version1: Version to check.
        version2: Version to compare against.

    Returns:
        True if version1 is newer than version2.
    """
    return compare_versions(version1, version2) > 0


def extract_version_from_filename(filename: str) -> Optional[str]:
    """Attempt to extract a version from a filename.

    Useful when version metadata is missing but encoded in filename.

    Args:
        filename: The filename to parse (e.g., "ModName-1.2.3.zip").

    Returns:
        Extracted version string, or None if not found.
    """
    if not filename:
        return None

    # Remove common extensions
    name = re.sub(r"\.(zip|rar|7z|tar\.gz)$", "", filename, flags=re.IGNORECASE)

    # Common patterns for versions in filenames
    patterns = [
        r"[-_]v?(\d+\.\d+(?:\.\d+)?(?:[-_.]\w+)?)\s*$",  # name-1.2.3 or name_v1.2.3
        r"[-_](\d{8})\s*$",  # name-20240115
        r"[-_]v?(\d+)\s*$",  # name-v2 or name_2
    ]

    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return match.group(1)

    return None
