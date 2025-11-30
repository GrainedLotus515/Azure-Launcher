# Quick Start Guide

Get up and running with MHW Mod Manager in 5 minutes.

## Installation (One-Time Setup)

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart terminal

# 2. Navigate to project directory
cd /home/lotus/Gitea/claude-mm

# 3. Create and activate virtual environment
uv venv
source .venv/bin/activate

# 4. Install the application
uv pip install -e .
```

## Running the Application

```bash
# Make sure virtual environment is activated
source .venv/bin/activate  # if not already active

# Launch the mod manager
mhw-mod-manager
```

That's it! The application will:
- Auto-detect your MHW installation (if installed via Steam)
- Create necessary directories
- Open the GUI

## Basic Usage

1. **Add a Mod**: Click "Add Mod" → Select ZIP or folder → OK
2. **Enable/Disable**: Use checkboxes in the Mods tab
3. **Deploy**: Click "Deploy" to apply mods to game
4. **Undeploy**: Click "Undeploy" to remove all mods

## Testing

```bash
# Run tests to verify installation
pytest
```

## Common Commands

```bash
# Run the application
mhw-mod-manager

# Run with activated environment
source .venv/bin/activate && mhw-mod-manager

# Run tests
pytest

# Run tests with coverage
pytest --cov=mhw_mod_manager

# Install development tools
uv pip install -e ".[dev]"
```

## File Locations

- **Config**: `~/.config/mhw-mod-manager/config.toml`
- **Mod Data**: `~/.local/share/mhw-mod-manager/`
- **Logs**: `~/.cache/mhw-mod-manager/mhw_mod_manager.log`

## Getting Help

- Full documentation: `README.md`
- Setup details: `SETUP.md`
- Usage examples: `USAGE_EXAMPLES.md`
- Check logs in the app: Go to "Log" tab
