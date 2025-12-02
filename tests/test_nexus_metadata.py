"""Tests for Nexus metadata persistence in mod repository."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from mhw_mod_manager.core.models import Mod
from mhw_mod_manager.core.mods.repository import ModRepository


class TestNexusMetadataPersistence:
    """Tests for persisting Nexus Mods metadata in the repository."""

    def test_save_and_load_mod_with_nexus_metadata(self):
        """Test that Nexus metadata is saved and loaded correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create a mod with Nexus metadata
            mod = Mod(
                name="Test Mod",
                version="1.2.3",
                author="Test Author",
                staging_path=Path("/test/staging"),
                nexus_mod_id=12345,
                nexus_file_id=67890,
                nexus_uploaded_at=datetime(2024, 1, 15, 10, 30, 0),
            )

            # Save to repository
            repo1 = ModRepository(data_dir)
            repo1.add(mod)

            # Load from a fresh repository instance
            repo2 = ModRepository(data_dir)
            repo2.load()

            loaded_mod = repo2.get(mod.id)

            assert loaded_mod is not None
            assert loaded_mod.name == "Test Mod"
            assert loaded_mod.version == "1.2.3"
            assert loaded_mod.author == "Test Author"
            assert loaded_mod.nexus_mod_id == 12345
            assert loaded_mod.nexus_file_id == 67890
            assert loaded_mod.nexus_uploaded_at == datetime(2024, 1, 15, 10, 30, 0)

    def test_load_mod_without_nexus_metadata_backward_compat(self):
        """Test that mods without Nexus metadata load correctly (backward compatibility)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create a JSON file with old-format mod data (no Nexus fields)
            old_mod_data = {
                "mods": [
                    {
                        "id": "12345678-1234-5678-1234-567812345678",
                        "name": "Old Mod",
                        "version": None,
                        "author": None,
                        "description": None,
                        "source": None,
                        "tags": [],
                        "installed_at": "2024-01-01T00:00:00",
                        "staging_path": "/test/old/staging",
                        "deployed_files": [],
                        "archive_path": None,
                        "archive_checksum": None,
                        # Note: no nexus_mod_id, nexus_file_id, nexus_uploaded_at
                    }
                ]
            }

            mods_file = data_dir / "mods.json"
            data_dir.mkdir(parents=True, exist_ok=True)
            with open(mods_file, "w") as f:
                json.dump(old_mod_data, f)

            # Load repository - should not crash
            repo = ModRepository(data_dir)
            repo.load()

            mods = repo.get_all()
            assert len(mods) == 1

            mod = mods[0]
            assert mod.name == "Old Mod"
            # Nexus fields should be None
            assert mod.nexus_mod_id is None
            assert mod.nexus_file_id is None
            assert mod.nexus_uploaded_at is None

    def test_update_mod_adds_nexus_metadata(self):
        """Test updating a mod to add Nexus metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create a mod without Nexus metadata
            mod = Mod(
                name="Upgradeable Mod",
                staging_path=Path("/test/staging"),
            )

            repo = ModRepository(data_dir)
            repo.add(mod)

            # Update with Nexus metadata
            mod.version = "2.0.0"
            mod.nexus_mod_id = 99999
            mod.nexus_file_id = 88888
            mod.nexus_uploaded_at = datetime(2024, 6, 1, 12, 0, 0)

            repo.update(mod)

            # Reload and verify
            repo2 = ModRepository(data_dir)
            repo2.load()

            loaded_mod = repo2.get(mod.id)

            assert loaded_mod is not None
            assert loaded_mod.version == "2.0.0"
            assert loaded_mod.nexus_mod_id == 99999
            assert loaded_mod.nexus_file_id == 88888
            assert loaded_mod.nexus_uploaded_at == datetime(2024, 6, 1, 12, 0, 0)

    def test_mod_with_null_nexus_fields(self):
        """Test that null Nexus fields are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            mod = Mod(
                name="Local Mod",
                staging_path=Path("/test/staging"),
                nexus_mod_id=None,
                nexus_file_id=None,
                nexus_uploaded_at=None,
            )

            repo1 = ModRepository(data_dir)
            repo1.add(mod)

            repo2 = ModRepository(data_dir)
            repo2.load()

            loaded_mod = repo2.get(mod.id)

            assert loaded_mod is not None
            assert loaded_mod.nexus_mod_id is None
            assert loaded_mod.nexus_file_id is None
            assert loaded_mod.nexus_uploaded_at is None

    def test_version_field_persistence(self):
        """Test that version field is persisted correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Test various version formats
            versions_to_test = [
                "1.0.0",
                "v2.3.4",
                "2024.01.15",
                "Final Release",
                "1.0.0-beta.1",
                "",
                None,
            ]

            repo = ModRepository(data_dir)

            created_mods = []
            for i, version in enumerate(versions_to_test):
                mod = Mod(
                    name=f"Mod {i}",
                    version=version,
                    staging_path=Path(f"/test/staging/{i}"),
                )
                repo.add(mod)
                created_mods.append(mod)

            # Reload
            repo2 = ModRepository(data_dir)
            repo2.load()

            for original_mod, version in zip(created_mods, versions_to_test):
                loaded_mod = repo2.get(original_mod.id)
                assert loaded_mod is not None
                assert loaded_mod.version == version

    def test_multiple_mods_with_nexus_metadata(self):
        """Test persisting multiple mods with various Nexus metadata states."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            mods = [
                Mod(
                    name="Full Nexus Mod",
                    version="1.0.0",
                    staging_path=Path("/test/1"),
                    nexus_mod_id=111,
                    nexus_file_id=222,
                    nexus_uploaded_at=datetime(2024, 1, 1),
                ),
                Mod(
                    name="Partial Nexus Mod",
                    version="2.0.0",
                    staging_path=Path("/test/2"),
                    nexus_mod_id=333,
                    nexus_file_id=None,
                    nexus_uploaded_at=None,
                ),
                Mod(
                    name="Local Only Mod",
                    version=None,
                    staging_path=Path("/test/3"),
                    nexus_mod_id=None,
                    nexus_file_id=None,
                    nexus_uploaded_at=None,
                ),
            ]

            repo1 = ModRepository(data_dir)
            for mod in mods:
                repo1.add(mod)

            repo2 = ModRepository(data_dir)
            repo2.load()

            all_loaded = repo2.get_all()
            assert len(all_loaded) == 3

            # Verify each mod
            for original in mods:
                loaded = repo2.get(original.id)
                assert loaded is not None
                assert loaded.name == original.name
                assert loaded.version == original.version
                assert loaded.nexus_mod_id == original.nexus_mod_id
                assert loaded.nexus_file_id == original.nexus_file_id
                assert loaded.nexus_uploaded_at == original.nexus_uploaded_at


class TestModModelNexusFields:
    """Tests for Mod model Nexus fields."""

    def test_mod_creation_with_nexus_fields(self):
        """Test creating a Mod with all Nexus fields."""
        mod = Mod(
            name="Test",
            staging_path=Path("/test"),
            version="1.0.0",
            nexus_mod_id=123,
            nexus_file_id=456,
            nexus_uploaded_at=datetime(2024, 5, 15),
        )

        assert mod.version == "1.0.0"
        assert mod.nexus_mod_id == 123
        assert mod.nexus_file_id == 456
        assert mod.nexus_uploaded_at == datetime(2024, 5, 15)

    def test_mod_creation_defaults(self):
        """Test that Nexus fields default to None."""
        mod = Mod(
            name="Test",
            staging_path=Path("/test"),
        )

        assert mod.version is None
        assert mod.nexus_mod_id is None
        assert mod.nexus_file_id is None
        assert mod.nexus_uploaded_at is None

    def test_mod_json_serialization(self):
        """Test that Mod with Nexus fields serializes to JSON correctly."""
        mod = Mod(
            name="Test",
            staging_path=Path("/test"),
            version="1.0.0",
            nexus_mod_id=123,
            nexus_file_id=456,
            nexus_uploaded_at=datetime(2024, 5, 15, 10, 30, 0),
        )

        json_data = mod.model_dump(mode="json")

        assert json_data["version"] == "1.0.0"
        assert json_data["nexus_mod_id"] == 123
        assert json_data["nexus_file_id"] == 456
        assert json_data["nexus_uploaded_at"] is not None

    def test_mod_json_serialization_with_nulls(self):
        """Test that Mod with null Nexus fields serializes correctly."""
        mod = Mod(
            name="Test",
            staging_path=Path("/test"),
        )

        json_data = mod.model_dump(mode="json")

        assert json_data["version"] is None
        assert json_data["nexus_mod_id"] is None
        assert json_data["nexus_file_id"] is None
        assert json_data["nexus_uploaded_at"] is None
