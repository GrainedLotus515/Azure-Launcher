"""Tests for mod management."""

import tempfile
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest

from mhw_mod_manager.core.config import ConfigManager
from mhw_mod_manager.core.models import Mod, Profile, ProfileModEntry
from mhw_mod_manager.core.mods.conflicts import ConflictDetector
from mhw_mod_manager.core.mods.deployment import DeploymentEngine
from mhw_mod_manager.core.mods.installer import ModInstaller
from mhw_mod_manager.core.mods.profiles import ProfileManager
from mhw_mod_manager.core.mods.repository import ModRepository


class TestModRepository:
    """Tests for ModRepository."""

    def test_add_and_get(self):
        """Test adding and retrieving a mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModRepository(Path(tmpdir))

            mod = Mod(
                name="Test Mod",
                staging_path=Path("/test/staging"),
            )

            repo.add(mod)

            retrieved = repo.get(mod.id)
            assert retrieved is not None
            assert retrieved.name == "Test Mod"

    def test_get_all(self):
        """Test getting all mods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModRepository(Path(tmpdir))

            mod1 = Mod(name="Mod 1", staging_path=Path("/test/1"))
            mod2 = Mod(name="Mod 2", staging_path=Path("/test/2"))

            repo.add(mod1)
            repo.add(mod2)

            all_mods = repo.get_all()
            assert len(all_mods) == 2

    def test_remove(self):
        """Test removing a mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ModRepository(Path(tmpdir))

            mod = Mod(name="Test Mod", staging_path=Path("/test"))
            repo.add(mod)

            assert repo.remove(mod.id) is True
            assert repo.get(mod.id) is None

    def test_persistence(self):
        """Test that mods persist across repository instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            # Create and add mod
            repo1 = ModRepository(data_dir)
            mod = Mod(name="Persistent Mod", staging_path=Path("/test"))
            repo1.add(mod)

            # Create new repository and load
            repo2 = ModRepository(data_dir)
            repo2.load()

            retrieved = repo2.get(mod.id)
            assert retrieved is not None
            assert retrieved.name == "Persistent Mod"


class TestProfileManager:
    """Tests for ProfileManager."""

    def test_create_profile(self):
        """Test creating a profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProfileManager(Path(tmpdir))

            profile = manager.create("Test Profile")

            assert profile.name == "Test Profile"
            assert len(profile.mods) == 0

    def test_get_all_profiles(self):
        """Test getting all profiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProfileManager(Path(tmpdir))

            manager.create("Profile 1")
            manager.create("Profile 2")

            profiles = manager.get_all()
            # Default profile is created automatically, so we have 3 total
            assert len(profiles) == 3

    def test_delete_profile(self):
        """Test deleting a profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProfileManager(Path(tmpdir))

            profile = manager.create("To Delete")
            assert manager.delete(profile.id) is True
            assert manager.get(profile.id) is None

    def test_default_profile(self):
        """Test getting default profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ProfileManager(Path(tmpdir))

            default = manager.get_default_profile()
            assert default.name == "Default"


class TestProfile:
    """Tests for Profile model."""

    def test_set_mod_enabled(self):
        """Test enabling/disabling a mod."""
        profile = Profile(name="Test")
        mod_id = uuid4()

        profile.set_mod_enabled(mod_id, True)
        entry = profile.get_mod_entry(mod_id)

        assert entry is not None
        assert entry.enabled is True

    def test_get_enabled_mods_ordered(self):
        """Test getting enabled mods in load order."""
        profile = Profile(name="Test")

        mod1 = uuid4()
        mod2 = uuid4()
        mod3 = uuid4()

        profile.mods = [
            ProfileModEntry(mod_id=mod1, enabled=True, load_order=2),
            ProfileModEntry(mod_id=mod2, enabled=False, load_order=0),
            ProfileModEntry(mod_id=mod3, enabled=True, load_order=1),
        ]

        enabled = profile.get_enabled_mods_ordered()

        assert len(enabled) == 2
        assert enabled[0] == mod3  # load_order 1
        assert enabled[1] == mod1  # load_order 2


class TestModInstaller:
    """Tests for ModInstaller."""

    def test_install_from_zip_nativepc_at_root(self):
        """Test installing a mod from a ZIP with nativePC at root.

        The nativePC folder should be preserved since mods are deployed
        directly to the game folder.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test ZIP with nativePC at root
            zip_path = Path(tmpdir) / "test_mod.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("nativePC/test_file.txt", "test content")
                zf.writestr("nativePC/subdir/another.txt", "more content")

            # Setup config
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_manager = ConfigManager(config_dir)
            config_manager.update(
                staging_directory=Path(tmpdir) / "staging",
                downloads_directory=Path(tmpdir) / "downloads",
            )

            # Install
            installer = ModInstaller(config_manager)
            mod = installer.install_from_zip(zip_path, "Test Mod")

            assert mod.name == "Test Mod"
            assert mod.staging_path.exists()
            # nativePC should be preserved in staging
            assert (mod.staging_path / "nativePC/test_file.txt").exists()
            assert (mod.staging_path / "nativePC/subdir/another.txt").exists()

    def test_install_from_zip_wrapper_folder(self):
        """Test installing a mod with wrapper folder around nativePC.

        Archives like "ModName/nativePC/files" should strip only the wrapper,
        keeping nativePC intact.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test ZIP with wrapper folder
            zip_path = Path(tmpdir) / "test_mod.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("MyMod/nativePC/test_file.txt", "test content")
                zf.writestr("MyMod/nativePC/subdir/another.txt", "more content")

            # Setup config
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_manager = ConfigManager(config_dir)
            config_manager.update(
                staging_directory=Path(tmpdir) / "staging",
                downloads_directory=Path(tmpdir) / "downloads",
            )

            # Install
            installer = ModInstaller(config_manager)
            mod = installer.install_from_zip(zip_path, "Test Mod")

            assert mod.name == "Test Mod"
            assert mod.staging_path.exists()
            # Wrapper stripped, nativePC preserved
            assert (mod.staging_path / "nativePC/test_file.txt").exists()
            assert (mod.staging_path / "nativePC/subdir/another.txt").exists()
            # Wrapper should be gone
            assert not (mod.staging_path / "MyMod").exists()

    def test_install_from_zip_no_nativepc(self):
        """Test installing a mod without nativePC folder.

        Some mods may not have the nativePC structure and should be
        extracted as-is (or with wrapper folder stripped).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test ZIP without nativePC
            zip_path = Path(tmpdir) / "test_mod.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("ModFolder/test_file.txt", "test content")
                zf.writestr("ModFolder/subdir/another.txt", "more content")

            # Setup config
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_manager = ConfigManager(config_dir)
            config_manager.update(
                staging_directory=Path(tmpdir) / "staging",
                downloads_directory=Path(tmpdir) / "downloads",
            )

            # Install
            installer = ModInstaller(config_manager)
            mod = installer.install_from_zip(zip_path, "Test Mod")

            assert mod.name == "Test Mod"
            assert mod.staging_path.exists()
            # Wrapper folder should be stripped, files at root
            assert (mod.staging_path / "test_file.txt").exists()
            assert (mod.staging_path / "subdir/another.txt").exists()

    def test_install_from_zip_nested_nativepc_intentional(self):
        """Test installing a mod with intentional nested nativePC structure.

        Some mods intentionally have nativePC/nativePC/... structure.
        The entire structure should be preserved as-is.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test ZIP with intentional nested nativePC
            zip_path = Path(tmpdir) / "test_mod.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                # This structure is intentional - both nativePCs should be preserved
                zf.writestr("nativePC/nativePC/test_file.txt", "test content")
                zf.writestr("nativePC/nativePC/subdir/another.txt", "more content")
                # Also include a regular file at first nativePC level
                zf.writestr("nativePC/regular_file.txt", "regular content")

            # Setup config
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_manager = ConfigManager(config_dir)
            config_manager.update(
                staging_directory=Path(tmpdir) / "staging",
                downloads_directory=Path(tmpdir) / "downloads",
            )

            # Install
            installer = ModInstaller(config_manager)
            mod = installer.install_from_zip(zip_path, "Test Mod")

            assert mod.name == "Test Mod"
            assert mod.staging_path.exists()
            # Both nativePCs preserved - entire structure kept
            assert (mod.staging_path / "nativePC/nativePC/test_file.txt").exists()
            assert (mod.staging_path / "nativePC/nativePC/subdir/another.txt").exists()
            assert (mod.staging_path / "nativePC/regular_file.txt").exists()

    def test_install_from_zip_wrapper_with_nested_nativepc(self):
        """Test wrapper folder with nested nativePC structure.

        Archive structure: ModName/nativePC/nativePC/file.txt
        Should strip only "ModName/" wrapper, preserving both nativePCs.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test_mod.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("MyMod/nativePC/nativePC/deep_file.txt", "deep content")
                zf.writestr("MyMod/nativePC/normal_file.txt", "normal content")

            # Setup config
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_manager = ConfigManager(config_dir)
            config_manager.update(
                staging_directory=Path(tmpdir) / "staging",
                downloads_directory=Path(tmpdir) / "downloads",
            )

            # Install
            installer = ModInstaller(config_manager)
            mod = installer.install_from_zip(zip_path, "Test Mod")

            assert mod.name == "Test Mod"
            assert mod.staging_path.exists()
            # Wrapper stripped, both nativePCs preserved
            assert (mod.staging_path / "nativePC/nativePC/deep_file.txt").exists()
            assert (mod.staging_path / "nativePC/normal_file.txt").exists()
            # Verify wrapper is gone
            assert not (mod.staging_path / "MyMod").exists()

    def test_install_from_folder(self):
        """Test installing a mod from a folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test folder structure
            source_folder = Path(tmpdir) / "test_mod"
            source_folder.mkdir()
            (source_folder / "test_file.txt").write_text("test content")

            # Setup config
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_manager = ConfigManager(config_dir)
            config_manager.update(
                staging_directory=Path(tmpdir) / "staging",
            )

            # Install
            installer = ModInstaller(config_manager)
            mod = installer.install_from_folder(source_folder, "Test Mod")

            assert mod.name == "Test Mod"
            assert mod.staging_path.exists()
            assert (mod.staging_path / "test_file.txt").exists()


class TestDeploymentEngine:
    """Tests for DeploymentEngine."""

    def test_deploy_with_symlinks(self):
        """Test deploying mods with symlinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup game directory
            game_dir = Path(tmpdir) / "game"
            game_dir.mkdir(parents=True)

            # Setup staging with nativePC structure (as mods should have)
            staging_dir = Path(tmpdir) / "staging"
            mod_staging = staging_dir / "test_mod"
            mod_native_pc = mod_staging / "nativePC"
            mod_native_pc.mkdir(parents=True)
            (mod_native_pc / "test_file.txt").write_text("content")

            # Create mod and profile
            mod = Mod(
                name="Test Mod",
                staging_path=mod_staging,
            )

            profile = Profile(name="Test")
            profile.set_mod_enabled(mod.id, True)

            # Setup config
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_manager = ConfigManager(config_dir)

            # Deploy - deploys directly to game folder
            engine = DeploymentEngine(config_manager, game_dir)
            state = engine.deploy([mod], profile)

            assert mod.id in state.deployed_mods
            # File should be at game/nativePC/test_file.txt
            deployed_file = game_dir / "nativePC" / "test_file.txt"
            assert deployed_file.exists()


class TestConflictDetector:
    """Tests for ConflictDetector."""

    def test_detect_conflicts(self):
        """Test detecting file conflicts between mods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two mods with conflicting files
            mod1_staging = Path(tmpdir) / "mod1"
            mod1_staging.mkdir()
            (mod1_staging / "conflict.txt").write_text("mod1")

            mod2_staging = Path(tmpdir) / "mod2"
            mod2_staging.mkdir()
            (mod2_staging / "conflict.txt").write_text("mod2")

            mod1 = Mod(name="Mod 1", staging_path=mod1_staging)
            mod2 = Mod(name="Mod 2", staging_path=mod2_staging)

            # Create profile with both mods enabled
            profile = Profile(name="Test")
            profile.mods = [
                ProfileModEntry(mod_id=mod1.id, enabled=True, load_order=0),
                ProfileModEntry(mod_id=mod2.id, enabled=True, load_order=1),
            ]

            # Detect conflicts
            detector = ConflictDetector()
            report = detector.analyze([mod1, mod2], profile)

            assert len(report.conflicts) == 1
            conflict = report.conflicts[0]
            assert conflict.target_path == Path("conflict.txt")
            assert mod1.id in conflict.conflicting_mods
            assert mod2.id in conflict.conflicting_mods
            assert conflict.winner_mod_id == mod2.id  # Higher load order wins

    def test_no_conflicts(self):
        """Test when there are no conflicts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two mods with different files
            mod1_staging = Path(tmpdir) / "mod1"
            mod1_staging.mkdir()
            (mod1_staging / "file1.txt").write_text("mod1")

            mod2_staging = Path(tmpdir) / "mod2"
            mod2_staging.mkdir()
            (mod2_staging / "file2.txt").write_text("mod2")

            mod1 = Mod(name="Mod 1", staging_path=mod1_staging)
            mod2 = Mod(name="Mod 2", staging_path=mod2_staging)

            profile = Profile(name="Test")
            profile.set_mod_enabled(mod1.id, True)
            profile.set_mod_enabled(mod2.id, True)

            detector = ConflictDetector()
            report = detector.analyze([mod1, mod2], profile)

            assert len(report.conflicts) == 0
            assert not report.has_conflicts()
