# MHW Mod Manager

A Linux-first desktop mod manager for **Monster Hunter: World** (PC/Steam). Simple, opinionated, and built with modern Python tooling.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)

## Features

- **Linux-First Design**: Native support for Linux desktops (X11/Wayland)
- **Profile Management**: Create multiple mod configurations and switch between them
- **Conflict Detection**: Automatically detect and visualize file conflicts between mods
- **Flexible Deployment**: Choose between symlink (recommended) or copy deployment modes
- **Modern UI**: Material 3-inspired interface with Catppuccin Mocha dark theme
- **Auto-Discovery**: Automatically detect Steam MHW installations
- **Load Order Control**: Manage mod priority with drag-and-drop reordering
- **Archive Support**: Install mods from ZIP archives or folders
- **Logging Console**: Built-in log viewer for troubleshooting

## Screenshots

The application features a clean, modern interface with:
- Left sidebar for profile management
- Main area with tabbed interface (Mods, Conflicts, Logs)
- Material 3 design with Catppuccin Mocha theming
- Responsive layout and smooth interactions

## Requirements

- **Python**: 3.12 or higher
- **uv**: Modern Python package manager ([installation guide](https://github.com/astral-sh/uv))
- **Linux**: Tested on modern distributions (X11/Wayland)
- **Monster Hunter: World**: PC version via Steam

## Installation

### 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone the repository

```bash
git clone <repository-url>
cd claude-mm
```

### 3. Create virtual environment and install dependencies

```bash
# Create virtual environment with Python 3.12+
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On Linux/macOS

# Install the package and dependencies
uv pip install -e .
```

### 4. Install development dependencies (optional)

```bash
uv pip install -e ".[dev]"
```

## Usage

### Running the Application

After installation, run the mod manager with:

```bash
mhw-mod-manager
```

Or directly with Python:

```bash
python -m mhw_mod_manager.app
```

### First-Time Setup

1. **Game Directory Detection**: On first launch, the app will attempt to auto-detect your MHW installation
   - Default location: `~/.local/share/Steam/steamapps/common/Monster Hunter World/`
   - If auto-detection fails, you'll be prompted to select the directory manually

2. **Configure Settings**: Open Settings to customize:
   - Game directory path
   - Staging directory (where mods are stored)
   - Deployment mode (symlink recommended)
   - Archive retention policy

### Adding Mods

1. Click **Add Mod** in the toolbar
2. Choose source type:
   - **From ZIP archive**: Select a mod archive file
   - **From folder**: Select a folder containing mod files
3. Enter a mod name (auto-detected from filename)
4. Click OK to install

The mod will be:
- Extracted to the staging directory
- Added to the current profile (enabled by default)
- Ready for deployment

### Managing Profiles

**Profiles** let you maintain different mod configurations:

1. Use the profile selector in the left sidebar
2. **New**: Create a new profile
3. **Rename**: Rename the current profile
4. **Delete**: Remove a profile (keep at least one)

Each profile tracks:
- Which mods are enabled
- Load order for each mod

### Deploying Mods

1. Enable/disable mods using checkboxes in the Mods tab
2. Adjust load order if needed (later mods override earlier ones)
3. Click **Deploy** to apply mods to the game directory

**Deployment creates symlinks** (or copies) from your staging area into the game's `nativePC` folder.

To remove all mods from the game:
- Click **Undeploy** to clean up deployed files

### Conflict Detection

The **Conflicts** tab shows files targeted by multiple mods:

- **File Path**: The conflicting file location
- **Conflicting Mods**: Which mods want to deploy this file
- **Winner**: Which mod will actually deploy (based on load order)

Click **Refresh Conflicts** to update the conflict view after changing mod configurations.

### Viewing Logs

The **Log** tab displays application events:
- Mod installations
- Deployment operations
- Errors and warnings
- File operations

Use **Clear** to reset the log view.

## Project Structure

```
claude-mm/
├── src/
│   └── mhw_mod_manager/
│       ├── core/              # Domain logic
│       │   ├── config.py      # Configuration management
│       │   ├── models.py      # Data models
│       │   ├── discovery.py   # Game detection
│       │   └── mods/          # Mod subsystem
│       │       ├── repository.py   # Mod storage
│       │       ├── installer.py    # Mod installation
│       │       ├── deployment.py   # Deployment engine
│       │       ├── profiles.py     # Profile management
│       │       └── conflicts.py    # Conflict detection
│       ├── theme/             # UI theming
│       │   ├── catppuccin.py  # Color palette
│       │   └── material3.py   # Material 3 styles
│       ├── ui/                # User interface
│       │   ├── widgets/       # Reusable widgets
│       │   └── dialogs/       # Dialog windows
│       ├── services/          # Application services
│       │   ├── logging_service.py
│       │   └── task_runner.py
│       ├── app.py             # Entry point
│       └── main_window.py     # Main window
├── tests/                     # Test suite
├── pyproject.toml            # Project configuration
├── README.md                 # This file
└── LICENSE                   # MIT License
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mhw_mod_manager --cov-report=html

# Run specific test file
pytest tests/test_mods.py
```

### Code Quality

```bash
# Type checking
mypy src/

# Linting
ruff check src/

# Formatting
ruff format src/
```

### Project Commands (uv)

```bash
# Sync dependencies
uv pip sync

# Add new dependency
uv pip install <package>

# Update dependencies
uv pip install --upgrade <package>
```

## Configuration Files

The application stores data in standard XDG directories:

- **Config**: `~/.config/mhw-mod-manager/`
  - `config.toml`: Application settings
  
- **Data**: `~/.local/share/mhw-mod-manager/`
  - `mods.json`: Mod metadata
  - `profiles.json`: Profile configurations
  - `mods/`: Staging directory for mod files
  - `downloads/`: Archived mod files
  
- **Logs**: `~/.local/share/mhw-mod-manager/` or `~/.cache/mhw-mod-manager/`
  - `mhw_mod_manager.log`: Application logs

## Deployment Modes

### Symlink Mode (Recommended)

Creates symbolic links from the staging area to the game directory:

**Advantages:**
- No file duplication (saves disk space)
- Instant deployment/undeployment
- Easy to track which files are mods

**Requirements:**
- Filesystem support for symlinks (ext4, btrfs, etc.)
- Staging and game directories on same filesystem (or relaxed symlink restrictions)

### Copy Mode

Copies files from staging to game directory:

**Advantages:**
- Works on any filesystem
- No symlink restrictions

**Disadvantages:**
- Duplicates files (uses more disk space)
- Slower deployment
- Harder to track mod files vs. vanilla files

## Troubleshooting

### Game Directory Not Found

If auto-detection fails:
1. Open **Settings**
2. Click **Browse** next to Game Directory
3. Navigate to your MHW installation (usually `~/.local/share/Steam/steamapps/common/Monster Hunter World/`)
4. Verify the directory contains a `nativePC` folder

### Symlinks Not Working

If symlink deployment fails:
1. Check filesystem support (ext4, btrfs support symlinks)
2. Verify staging and game directories permissions
3. Try switching to Copy mode in Settings

### Mods Not Loading In-Game

1. Verify mods are deployed (check Mods tab)
2. Check the Log tab for errors
3. Ensure mod files are in correct structure (inside `nativePC/`)
4. Try undeploying and redeploying

### Performance Issues

For large mod collections (100+ mods):
1. Use symlink mode for faster operations
2. Consider splitting mods across multiple profiles
3. Check log file rotation settings

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass (`pytest`)
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Catppuccin**: Beautiful color palette ([catppuccin.com](https://catppuccin.com))
- **Material Design 3**: Design system inspiration
- **PySide6**: Qt for Python bindings
- **uv**: Modern Python package management

## Disclaimer

This is an unofficial tool. Monster Hunter: World and all related properties are owned by Capcom. Use mods at your own risk.
