# MHW Mod Manager - Setup Guide

Complete setup instructions for the Monster Hunter: World Mod Manager on Linux.

## Prerequisites

- **Python 3.12+** (check with `python3 --version`)
- **uv** package manager
- **Linux** desktop environment (X11 or Wayland)
- **Monster Hunter: World** installed via Steam

## Quick Start

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, restart your terminal or run:
```bash
source ~/.bashrc  # or ~/.zshrc for zsh users
```

### 2. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd claude-mm

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install the application
uv pip install -e .
```

### 3. Run the Application

```bash
mhw-mod-manager
```

Or directly:
```bash
python -m mhw_mod_manager.app
```

## Development Setup

If you want to contribute or modify the code:

```bash
# Install with development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=mhw_mod_manager --cov-report=html

# Type checking
mypy src/

# Linting
ruff check src/

# Auto-formatting
ruff format src/
```

## Directory Structure After Installation

The application creates these directories on first run:

```
~/.config/mhw-mod-manager/
    config.toml              # Application settings

~/.local/share/mhw-mod-manager/
    mods.json                # Mod metadata database
    profiles.json            # Profile configurations
    mods/                    # Staged mod files
        <mod-uuid-1>/
        <mod-uuid-2>/
    downloads/               # Archived mod files

~/.cache/mhw-mod-manager/    # Or ~/.local/share/
    mhw_mod_manager.log      # Application log file
```

## Verifying Installation

Check that everything is installed correctly:

```bash
# Check the package is installed
uv pip list | grep mhw-mod-manager

# Check the command is available
which mhw-mod-manager

# Run tests to verify functionality
pytest -v
```

Expected output:
```
mhw-mod-manager   1.0.0  ...
/path/to/.venv/bin/mhw-mod-manager
===================== 24 passed in 0.38s =====================
```

## First Run Configuration

1. **Launch the application**:
   ```bash
   mhw-mod-manager
   ```

2. **Game Directory Setup**:
   - The app will attempt to auto-detect your MHW installation
   - If detection fails, click "Select Manually" and browse to:
     ```
     ~/.local/share/Steam/steamapps/common/Monster Hunter World/
     ```
   - For Flatpak Steam installations:
     ```
     ~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/Monster Hunter World/
     ```

3. **Verify nativePC folder exists**:
   ```bash
   ls ~/.local/share/Steam/steamapps/common/Monster\ Hunter\ World/nativePC
   ```

## Troubleshooting

### uv command not found

After installing uv, you may need to add it to your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add this to your `~/.bashrc` or `~/.zshrc` to make it permanent.

### Python version too old

Install Python 3.12+ using your distribution's package manager:

**Ubuntu/Debian:**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv
```

**Arch Linux:**
```bash
sudo pacman -S python
```

**Fedora:**
```bash
sudo dnf install python3.12
```

### Qt Platform Plugin Error

If you get a Qt platform plugin error, install Qt dependencies:

**Ubuntu/Debian:**
```bash
sudo apt install libxcb-cursor0 libxcb-xinerama0
```

**Arch Linux:**
```bash
sudo pacman -S qt6-base
```

### Game Directory Not Found

Manually locate your MHW installation:

```bash
# Search for Monster Hunter World
find ~ -name "Monster Hunter World" -type d 2>/dev/null
```

Then configure the path in Settings.

## Uninstallation

To remove the application:

```bash
# Uninstall the package
uv pip uninstall mhw-mod-manager

# Optionally remove data directories
rm -rf ~/.config/mhw-mod-manager
rm -rf ~/.local/share/mhw-mod-manager
rm -rf ~/.cache/mhw-mod-manager
```

## Updating

To update to the latest version:

```bash
cd claude-mm
git pull
uv pip install -e . --force-reinstall
```

## Support

For issues, check:
- The log file: `~/.cache/mhw-mod-manager/mhw_mod_manager.log`
- The Log tab in the application
- GitHub Issues (if available)
