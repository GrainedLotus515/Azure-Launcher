"""Application configuration management."""

import tomllib
from pathlib import Path
from typing import Optional

import tomli_w
from platformdirs import user_config_dir, user_data_dir, user_log_dir
from pydantic import BaseModel, Field

from .models import DeploymentMode


class AppConfig(BaseModel):
    """Application-wide configuration."""

    # Game paths
    game_directory: Optional[Path] = None

    # Mod manager paths
    staging_directory: Path = Field(
        default_factory=lambda: Path(user_data_dir("mhw-mod-manager", "MHW")) / "mods"
    )
    downloads_directory: Path = Field(
        default_factory=lambda: Path(user_data_dir("mhw-mod-manager", "MHW")) / "downloads"
    )

    # Deployment settings
    deployment_mode: DeploymentMode = DeploymentMode.SYMLINK
    keep_archives: bool = True

    # UI settings
    window_width: int = 1200
    window_height: int = 800

    # Active profile
    active_profile_id: Optional[str] = None

    # Nexus Mods integration
    nexus_api_key: Optional[str] = None

    class Config:
        json_encoders = {Path: str}


class ConfigManager:
    """Manages loading and saving application configuration."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize the config manager.

        Args:
            config_dir: Directory to store config. If None, uses platform default.
        """
        if config_dir is None:
            config_dir = Path(user_config_dir("mhw-mod-manager", "MHW"))

        self.config_dir = config_dir
        self.config_file = config_dir / "config.toml"
        self._config: Optional[AppConfig] = None

    def load(self) -> AppConfig:
        """Load configuration from file or create default."""
        if self._config is not None:
            return self._config

        if self.config_file.exists():
            with open(self.config_file, "rb") as f:
                data = tomllib.load(f)
                self._config = AppConfig(**data)
        else:
            self._config = AppConfig()
            self.save()

        # Ensure directories exist
        self._config.staging_directory.mkdir(parents=True, exist_ok=True)
        self._config.downloads_directory.mkdir(parents=True, exist_ok=True)

        return self._config

    def save(self) -> None:
        """Save current configuration to file."""
        if self._config is None:
            return

        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Convert to dict with proper serialization, excluding None values
        data = self._config.model_dump(mode="json", exclude_none=True)

        with open(self.config_file, "wb") as f:
            tomli_w.dump(data, f)

    def get(self) -> AppConfig:
        """Get current configuration, loading if necessary."""
        if self._config is None:
            return self.load()
        return self._config

    def update(self, **kwargs: object) -> None:
        """Update configuration values and save.

        Args:
            **kwargs: Configuration fields to update.
        """
        config = self.get()
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.save()


def get_data_dir() -> Path:
    """Get the user data directory for the application."""
    path = Path(user_data_dir("mhw-mod-manager", "MHW"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_log_dir() -> Path:
    """Get the user log directory for the application."""
    path = Path(user_log_dir("mhw-mod-manager", "MHW"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_dir() -> Path:
    """Get the user config directory for the application."""
    path = Path(user_config_dir("mhw-mod-manager", "MHW"))
    path.mkdir(parents=True, exist_ok=True)
    return path
