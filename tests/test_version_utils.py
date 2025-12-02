"""Tests for version parsing and sorting utilities."""

from datetime import datetime

import pytest

from mhw_mod_manager.core.models import NexusModFile
from mhw_mod_manager.nexus.version_utils import (
    ParsedVersion,
    SortOrder,
    compare_versions,
    create_sort_key,
    extract_version_from_filename,
    format_version_display,
    get_newest_file,
    is_newer_version,
    parse_version,
    sort_mod_files,
)


class TestParseVersion:
    """Tests for parse_version function."""

    def test_standard_semver(self):
        """Test parsing standard semantic versions."""
        result = parse_version("1.2.3")
        assert result.is_parsed is True
        assert result.major == 1
        assert result.minor == 2
        assert result.patch == 3
        assert result.prerelease == ""

    def test_semver_with_v_prefix(self):
        """Test parsing versions with 'v' prefix."""
        result = parse_version("v1.2.3")
        assert result.is_parsed is True
        assert result.major == 1
        assert result.minor == 2
        assert result.patch == 3

    def test_semver_with_capital_v_prefix(self):
        """Test parsing versions with 'V' prefix."""
        result = parse_version("V2.0.0")
        assert result.is_parsed is True
        assert result.major == 2
        assert result.minor == 0
        assert result.patch == 0

    def test_partial_version_major_minor(self):
        """Test parsing partial versions (major.minor only)."""
        result = parse_version("1.0")
        assert result.is_parsed is True
        assert result.major == 1
        assert result.minor == 0
        assert result.patch == 0

    def test_partial_version_major_only(self):
        """Test parsing single number versions."""
        result = parse_version("2")
        assert result.is_parsed is True
        assert result.major == 2
        assert result.minor == 0
        assert result.patch == 0

    def test_prerelease_alpha(self):
        """Test parsing versions with alpha prerelease."""
        result = parse_version("1.0.0-alpha")
        assert result.is_parsed is True
        assert result.prerelease.lower() == "alpha"

    def test_prerelease_beta_with_number(self):
        """Test parsing versions with numbered beta prerelease."""
        result = parse_version("2.0.0-beta.1")
        assert result.is_parsed is True
        assert "beta" in result.prerelease.lower()

    def test_prerelease_rc(self):
        """Test parsing versions with release candidate."""
        result = parse_version("3.0.0-rc1")
        assert result.is_parsed is True
        assert "rc" in result.prerelease.lower()

    def test_date_based_version(self):
        """Test parsing date-based versions."""
        result = parse_version("2024.01.15")
        assert result.is_parsed is True
        assert result.major == 2024
        assert result.minor == 1
        assert result.patch == 15

    def test_date_based_version_compact(self):
        """Test parsing compact date versions.

        Note: Compact dates without separators (e.g., "20240115") are parsed
        as simple numeric versions since they're ambiguous. Use separators
        like "2024.01.15" or "2024-01-15" for proper date parsing.
        """
        result = parse_version("20240115")
        assert result.is_parsed is True
        # Compact dates are parsed as a single number (no separators to detect date format)
        assert result.major == 20240115
        assert result.minor == 0
        assert result.patch == 0

    def test_unparseable_version(self):
        """Test handling of unparseable versions."""
        result = parse_version("Final")
        assert result.is_parsed is False
        assert result.original == "Final"

    def test_empty_version(self):
        """Test handling of empty version string."""
        result = parse_version("")
        assert result.is_parsed is False

    def test_version_with_whitespace(self):
        """Test parsing version with leading/trailing whitespace."""
        result = parse_version("  1.2.3  ")
        assert result.is_parsed is True
        assert result.major == 1

    def test_version_with_build_metadata(self):
        """Test parsing version with build metadata."""
        result = parse_version("1.0.0+build.123")
        assert result.is_parsed is True
        assert result.build == "build.123"


class TestParsedVersionComparison:
    """Tests for ParsedVersion comparison operations."""

    def test_equal_versions(self):
        """Test equality of identical versions."""
        v1 = parse_version("1.2.3")
        v2 = parse_version("1.2.3")
        assert v1 == v2

    def test_greater_major(self):
        """Test comparison when major version differs."""
        v1 = parse_version("2.0.0")
        v2 = parse_version("1.0.0")
        assert v1 > v2
        assert v2 < v1

    def test_greater_minor(self):
        """Test comparison when minor version differs."""
        v1 = parse_version("1.2.0")
        v2 = parse_version("1.1.0")
        assert v1 > v2

    def test_greater_patch(self):
        """Test comparison when patch version differs."""
        v1 = parse_version("1.0.2")
        v2 = parse_version("1.0.1")
        assert v1 > v2

    def test_release_greater_than_prerelease(self):
        """Test that release version is greater than prerelease."""
        release = parse_version("1.0.0")
        prerelease = parse_version("1.0.0-beta")
        assert release > prerelease

    def test_parsed_greater_than_unparsed(self):
        """Test that parsed versions sort before unparsed."""
        parsed = parse_version("1.0.0")
        unparsed = parse_version("Final")
        assert parsed > unparsed

    def test_unparsed_versions_compared_alphabetically(self):
        """Test that unparsed versions are compared by string."""
        v1 = parse_version("Beta")
        v2 = parse_version("Alpha")
        # "Alpha" < "Beta" alphabetically
        assert v2 < v1

    def test_less_than_or_equal(self):
        """Test less than or equal comparison."""
        v1 = parse_version("1.0.0")
        v2 = parse_version("1.0.0")
        v3 = parse_version("2.0.0")
        assert v1 <= v2
        assert v1 <= v3

    def test_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        v1 = parse_version("2.0.0")
        v2 = parse_version("2.0.0")
        v3 = parse_version("1.0.0")
        assert v1 >= v2
        assert v1 >= v3


class TestCompareVersions:
    """Tests for compare_versions function."""

    def test_first_greater(self):
        """Test when first version is greater."""
        assert compare_versions("2.0.0", "1.0.0") == 1

    def test_second_greater(self):
        """Test when second version is greater."""
        assert compare_versions("1.0.0", "2.0.0") == -1

    def test_equal(self):
        """Test when versions are equal."""
        assert compare_versions("1.0.0", "1.0.0") == 0

    def test_with_different_formats(self):
        """Test comparing versions with different formats."""
        # v prefix should not affect comparison
        assert compare_versions("v1.0.0", "1.0.0") == 0


class TestFormatVersionDisplay:
    """Tests for format_version_display function."""

    def test_numeric_version(self):
        """Test formatting numeric version adds 'v' prefix."""
        assert format_version_display("1.2.3") == "v1.2.3"

    def test_already_prefixed(self):
        """Test that already prefixed versions are unchanged."""
        assert format_version_display("v1.2.3") == "v1.2.3"

    def test_capital_v_prefix(self):
        """Test capital V prefix is preserved."""
        assert format_version_display("V1.2.3") == "V1.2.3"

    def test_non_standard_version(self):
        """Test non-standard versions are returned as-is."""
        assert format_version_display("Final Release") == "Final Release"

    def test_empty_version(self):
        """Test empty version returns 'Unknown'."""
        assert format_version_display("") == "Unknown"

    def test_none_like_empty(self):
        """Test None-like values."""
        assert format_version_display(None) == "Unknown"


class TestSortModFiles:
    """Tests for sort_mod_files function."""

    def _create_mod_file(
        self,
        file_id: int,
        version: str,
        uploaded_time: datetime,
        category: str = "main",
    ) -> NexusModFile:
        """Helper to create NexusModFile instances."""
        return NexusModFile(
            file_id=file_id,
            mod_id=1,
            name=f"File {file_id}",
            version=version,
            category_name=category,
            size_kb=1000,
            uploaded_time=uploaded_time,
        )

    def test_sort_by_version_newest_first(self):
        """Test sorting by version with newest first."""
        files = [
            self._create_mod_file(1, "1.0.0", datetime(2024, 1, 1)),
            self._create_mod_file(2, "2.0.0", datetime(2024, 1, 2)),
            self._create_mod_file(3, "1.5.0", datetime(2024, 1, 3)),
        ]

        sorted_files = sort_mod_files(files, SortOrder.NEWEST_FIRST)

        assert sorted_files[0].version == "2.0.0"
        assert sorted_files[1].version == "1.5.0"
        assert sorted_files[2].version == "1.0.0"

    def test_sort_by_version_oldest_first(self):
        """Test sorting by version with oldest first."""
        files = [
            self._create_mod_file(1, "1.0.0", datetime(2024, 1, 1)),
            self._create_mod_file(2, "2.0.0", datetime(2024, 1, 2)),
            self._create_mod_file(3, "1.5.0", datetime(2024, 1, 3)),
        ]

        sorted_files = sort_mod_files(files, SortOrder.OLDEST_FIRST)

        # Oldest version first
        assert sorted_files[0].version == "1.0.0"

    def test_fallback_to_upload_date(self):
        """Test fallback to upload date when versions are unparseable."""
        files = [
            self._create_mod_file(1, "Final", datetime(2024, 1, 1)),
            self._create_mod_file(2, "Release", datetime(2024, 1, 15)),
            self._create_mod_file(3, "Beta", datetime(2024, 1, 10)),
        ]

        sorted_files = sort_mod_files(files, SortOrder.NEWEST_FIRST)

        # Should sort by upload date since versions can't be parsed
        assert sorted_files[0].file_id == 2  # Jan 15
        assert sorted_files[1].file_id == 3  # Jan 10
        assert sorted_files[2].file_id == 1  # Jan 1

    def test_category_ordering(self):
        """Test that files are grouped by category."""
        files = [
            self._create_mod_file(1, "1.0.0", datetime(2024, 1, 1), "old"),
            self._create_mod_file(2, "2.0.0", datetime(2024, 1, 2), "main"),
            self._create_mod_file(3, "1.5.0", datetime(2024, 1, 3), "optional"),
        ]

        sorted_files = sort_mod_files(files, SortOrder.NEWEST_FIRST)

        # Main files should come before optional, which should come before old
        assert sorted_files[0].category_name == "main"
        assert sorted_files[1].category_name == "optional"
        assert sorted_files[2].category_name == "old"

    def test_empty_list(self):
        """Test sorting empty list."""
        result = sort_mod_files([], SortOrder.NEWEST_FIRST)
        assert result == []

    def test_single_file(self):
        """Test sorting single file."""
        files = [self._create_mod_file(1, "1.0.0", datetime(2024, 1, 1))]
        result = sort_mod_files(files)
        assert len(result) == 1
        assert result[0].file_id == 1


class TestGetNewestFile:
    """Tests for get_newest_file function."""

    def _create_mod_file(
        self,
        file_id: int,
        version: str,
        uploaded_time: datetime,
        category: str = "main",
    ) -> NexusModFile:
        """Helper to create NexusModFile instances."""
        return NexusModFile(
            file_id=file_id,
            mod_id=1,
            name=f"File {file_id}",
            version=version,
            category_name=category,
            size_kb=1000,
            uploaded_time=uploaded_time,
        )

    def test_get_newest_from_list(self):
        """Test getting newest file from list."""
        files = [
            self._create_mod_file(1, "1.0.0", datetime(2024, 1, 1)),
            self._create_mod_file(2, "2.0.0", datetime(2024, 1, 2)),
            self._create_mod_file(3, "1.5.0", datetime(2024, 1, 3)),
        ]

        result = get_newest_file(files)
        assert result is not None
        assert result.version == "2.0.0"

    def test_get_newest_with_category_filter(self):
        """Test getting newest file filtered by category."""
        files = [
            self._create_mod_file(1, "3.0.0", datetime(2024, 1, 1), "old"),
            self._create_mod_file(2, "2.0.0", datetime(2024, 1, 2), "main"),
            self._create_mod_file(3, "1.5.0", datetime(2024, 1, 3), "main"),
        ]

        result = get_newest_file(files, category="main")
        assert result is not None
        assert result.version == "2.0.0"

    def test_get_newest_empty_list(self):
        """Test getting newest from empty list."""
        result = get_newest_file([])
        assert result is None

    def test_get_newest_no_matching_category(self):
        """Test when no files match category."""
        files = [
            self._create_mod_file(1, "1.0.0", datetime(2024, 1, 1), "old"),
        ]
        result = get_newest_file(files, category="main")
        assert result is None


class TestIsNewerVersion:
    """Tests for is_newer_version function."""

    def test_newer_version(self):
        """Test detecting newer version."""
        assert is_newer_version("2.0.0", "1.0.0") is True

    def test_older_version(self):
        """Test detecting older version."""
        assert is_newer_version("1.0.0", "2.0.0") is False

    def test_equal_version(self):
        """Test equal versions."""
        assert is_newer_version("1.0.0", "1.0.0") is False


class TestExtractVersionFromFilename:
    """Tests for extract_version_from_filename function."""

    def test_standard_format(self):
        """Test extracting version from standard filename format."""
        result = extract_version_from_filename("ModName-1.2.3.zip")
        assert result == "1.2.3"

    def test_underscore_format(self):
        """Test extracting version with underscore separator."""
        result = extract_version_from_filename("ModName_v2.0.0.zip")
        assert result == "2.0.0"

    def test_date_format(self):
        """Test extracting date-based version."""
        result = extract_version_from_filename("ModName-20240115.zip")
        assert result == "20240115"

    def test_simple_number(self):
        """Test extracting simple numeric version."""
        result = extract_version_from_filename("ModName-v2.zip")
        assert result == "2"

    def test_no_version(self):
        """Test filename without version."""
        result = extract_version_from_filename("ModName.zip")
        assert result is None

    def test_empty_filename(self):
        """Test empty filename."""
        result = extract_version_from_filename("")
        assert result is None

    def test_rar_extension(self):
        """Test with .rar extension."""
        result = extract_version_from_filename("ModName-1.0.0.rar")
        assert result == "1.0.0"

    def test_7z_extension(self):
        """Test with .7z extension."""
        result = extract_version_from_filename("ModName-1.0.0.7z")
        assert result == "1.0.0"


class TestCreateSortKey:
    """Tests for create_sort_key function."""

    def test_creates_valid_sort_key(self):
        """Test creating a sort key from mod file."""
        mod_file = NexusModFile(
            file_id=1,
            mod_id=100,
            name="Test File",
            version="1.2.3",
            category_name="main",
            size_kb=1000,
            uploaded_time=datetime(2024, 1, 15),
        )

        key = create_sort_key(mod_file)

        assert key.parsed_version.is_parsed is True
        assert key.parsed_version.major == 1
        assert key.parsed_version.minor == 2
        assert key.parsed_version.patch == 3
        assert key.uploaded_time == datetime(2024, 1, 15)
        assert key.file_id == 1

    def test_prefers_file_version_over_mod_version(self):
        """Test that file version is preferred over mod_version field."""
        mod_file = NexusModFile(
            file_id=1,
            mod_id=100,
            name="Test File",
            version="2.0.0",
            mod_version="1.0.0",
            category_name="main",
            size_kb=1000,
            uploaded_time=datetime(2024, 1, 15),
        )

        key = create_sort_key(mod_file)
        assert key.parsed_version.major == 2


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_version_with_special_characters(self):
        """Test handling versions with special characters."""
        # Should not crash
        result = parse_version("1.0.0-beta+build.123")
        assert result is not None

    def test_very_long_version_string(self):
        """Test handling very long version strings."""
        long_version = "1." + "0." * 100 + "0"
        result = parse_version(long_version)
        # Should not crash, may or may not parse
        assert result is not None

    def test_unicode_version(self):
        """Test handling unicode in version string."""
        result = parse_version("1.0.0-αβγ")
        assert result is not None

    def test_prerelease_variations(self):
        """Test various prerelease tag formats."""
        variations = [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0a",
            "1.0.0-ALPHA",
            "1.0.0-beta",
            "1.0.0b",
            "1.0.0-rc1",
            "1.0.0-RC.1",
            "1.0.0-pre",
            "1.0.0-dev",
            "1.0.0-snapshot",
        ]

        for version in variations:
            result = parse_version(version)
            # All should parse without error
            assert result is not None
            assert result.original == version
