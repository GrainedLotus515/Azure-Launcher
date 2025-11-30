"""Tests for game discovery."""

import tempfile
from pathlib import Path

import pytest

from mhw_mod_manager.core.discovery import GameDiscovery


class TestGameDiscovery:
    """Tests for GameDiscovery."""

    def test_validate_valid_directory(self):
        """Test validation of a valid game directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            game_dir = Path(tmpdir)
            native_pc = game_dir / "nativePC"
            native_pc.mkdir()

            # Create a dummy file
            (native_pc / "test.txt").touch()

            assert GameDiscovery.validate_game_directory(game_dir)

    def test_validate_missing_directory(self):
        """Test validation fails for non-existent directory."""
        assert not GameDiscovery.validate_game_directory(Path("/nonexistent/path"))

    def test_validate_missing_native_pc(self):
        """Test validation fails without nativePC directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            game_dir = Path(tmpdir)

            assert not GameDiscovery.validate_game_directory(game_dir)

    def test_get_native_pc_path(self):
        """Test getting nativePC path."""
        game_dir = Path("/test/game")
        native_pc = GameDiscovery.get_native_pc_path(game_dir)

        assert native_pc == Path("/test/game/nativePC")
