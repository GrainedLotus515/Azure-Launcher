"""Tests for configuration management."""

import tempfile
from pathlib import Path

import pytest

from mhw_mod_manager.core.config import AppConfig, ConfigManager
from mhw_mod_manager.core.models import DeploymentMode


class TestAppConfig:
    """Tests for AppConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AppConfig()

        assert config.game_directory is None
        assert config.deployment_mode == DeploymentMode.SYMLINK
        assert config.keep_archives is True
        assert config.window_width == 1200
        assert config.window_height == 800

    def test_custom_config(self):
        """Test custom configuration values."""
        config = AppConfig(
            game_directory=Path("/test/path"),
            deployment_mode=DeploymentMode.COPY,
            keep_archives=False,
        )

        assert config.game_directory == Path("/test/path")
        assert config.deployment_mode == DeploymentMode.COPY
        assert config.keep_archives is False


class TestConfigManager:
    """Tests for ConfigManager."""

    def test_load_creates_default(self):
        """Test that load creates default config if file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir)

            config = manager.load()

            assert config is not None
            assert config.deployment_mode == DeploymentMode.SYMLINK
            assert (config_dir / "config.toml").exists()

    def test_save_and_load(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir)

            # Load and modify
            config = manager.get()
            config.game_directory = Path("/test/game")
            config.deployment_mode = DeploymentMode.COPY
            manager.save()

            # Create new manager and load
            manager2 = ConfigManager(config_dir)
            loaded_config = manager2.load()

            assert loaded_config.game_directory == Path("/test/game")
            assert loaded_config.deployment_mode == DeploymentMode.COPY

    def test_update(self):
        """Test updating configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigManager(config_dir)

            manager.update(
                game_directory=Path("/updated/path"),
                keep_archives=False,
            )

            config = manager.get()
            assert config.game_directory == Path("/updated/path")
            assert config.keep_archives is False
