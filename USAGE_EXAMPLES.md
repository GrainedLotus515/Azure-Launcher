# Usage Examples

Complete workflow examples for using the MHW Mod Manager.

## Installation and First Run

```bash
# 1. Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Set up the project
cd /home/lotus/Gitea/claude-mm
uv venv
source .venv/bin/activate
uv pip install -e .

# 3. Launch the application
mhw-mod-manager
```

## Testing the Application

```bash
# Activate environment
source .venv/bin/activate

# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run tests with coverage report
pytest --cov=mhw_mod_manager --cov-report=html

# Run specific test file
pytest tests/test_mods.py -v

# Run specific test
pytest tests/test_config.py::TestConfigManager::test_save_and_load -v
```

## Development Workflow

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Type checking
mypy src/

# Linting
ruff check src/

# Auto-format code
ruff format src/

# Run all quality checks
pytest && mypy src/ && ruff check src/
```

## Running in Different Modes

### Normal GUI Mode
```bash
mhw-mod-manager
```

### With Debug Logging
```bash
# Set logging level via environment
export LOG_LEVEL=DEBUG
mhw-mod-manager
```

### Headless Mode (for future CLI features)
```bash
# Currently launches GUI only
# CLI subcommands can be added in future versions
mhw-mod-manager --help
```

## Example Mod Installation Workflow

### Scenario 1: Installing a Texture Mod from ZIP

1. **Download mod** (e.g., `improved_textures_v1.2.zip`)
2. **Launch MHW Mod Manager**
3. **Click "Add Mod"** in toolbar
4. **Select "From ZIP archive"**
5. **Browse to** `~/Downloads/improved_textures_v1.2.zip`
6. **Name it** "Improved Textures" (or keep auto-detected name)
7. **Click OK**

The mod is now:
- Extracted to staging directory
- Added to your current profile
- Ready to deploy

### Scenario 2: Installing from a Folder

1. **Extract mod** to `~/mods/weapon_pack/`
2. **Launch MHW Mod Manager**
3. **Click "Add Mod"**
4. **Select "From folder"**
5. **Browse to** `~/mods/weapon_pack/`
6. **Click OK**

### Scenario 3: Managing Multiple Profiles

**Create a "Visual Mods Only" profile:**
1. Click **New** in profile selector
2. Name it "Visual Mods Only"
3. Enable only texture/appearance mods
4. Click **Deploy**

**Create a "Performance" profile:**
1. Click **New** again
2. Name it "Performance"
3. Enable only performance-enhancing mods
4. Disable all texture mods
5. Click **Deploy**

**Switch between profiles:**
1. Select profile from dropdown
2. Click **Deploy** to apply changes

### Scenario 4: Resolving Conflicts

Two mods modify the same file:

1. Go to **Conflicts** tab
2. View conflicting files
3. Note which mod "wins" (based on load order)
4. Adjust load order in **Mods** tab if needed
5. Higher load order = wins conflicts
6. Click **Refresh Conflicts** to update
7. Click **Deploy** when satisfied

## Configuration Examples

### Changing Game Directory

**Settings → Game Directory → Browse**
```
~/.local/share/Steam/steamapps/common/Monster Hunter World/
```

### Changing Deployment Mode

**Settings → Deployment Mode**
- **Symlink** (recommended): Fast, no duplication
- **Copy**: Slower, uses more space, but more compatible

### Changing Staging Directory

**Settings → Staging Directory → Browse**
```
/mnt/games/mhw-mods/  # Example: external drive
```

## Backup and Restore

### Backing Up Your Configuration

```bash
# Backup all configuration and mods
tar -czf mhw-mod-manager-backup.tar.gz \
    ~/.config/mhw-mod-manager/ \
    ~/.local/share/mhw-mod-manager/
```

### Restoring from Backup

```bash
# Restore configuration
tar -xzf mhw-mod-manager-backup.tar.gz -C ~/
```

### Exporting a Profile

```bash
# Profiles are stored in JSON
cp ~/.local/share/mhw-mod-manager/profiles.json \
   ~/my-profile-backup.json
```

## Advanced Usage

### Batch Operations (Future Feature)

The architecture supports adding CLI commands:

```python
# In app.py, you could add:
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--deploy', help='Deploy profile by name')
    parser.add_argument('--list-mods', action='store_true')
    args = parser.parse_args()
    
    if args.list_mods:
        # List mods without GUI
        pass
    elif args.deploy:
        # Deploy specific profile
        pass
    else:
        # Launch GUI (current behavior)
        launch_gui()
```

### Integration with Steam

Add to Steam as Non-Steam Game:
1. Open Steam
2. Games → Add Non-Steam Game
3. Browse to `.venv/bin/mhw-mod-manager`
4. Add game

### Scripting

```bash
#!/bin/bash
# Example: Auto-deploy script

source /path/to/claude-mm/.venv/bin/activate

# Future: Add CLI commands
# mhw-mod-manager --deploy "Performance"
# mhw-mod-manager --enable-mod "some-mod-id"
# mhw-mod-manager --undeploy

# For now, you'd use the GUI
mhw-mod-manager
```

## Performance Tips

1. **Use Symlink Mode**: Much faster than copy mode
2. **Limit Active Mods**: Only enable what you need
3. **Use Profiles**: Switch between configurations easily
4. **Regular Cleanup**: Remove unused mods
5. **SSD Storage**: Store staging directory on SSD if possible

## Maintenance

### Checking Log Files

```bash
# View recent logs
tail -f ~/.cache/mhw-mod-manager/mhw_mod_manager.log

# Search for errors
grep ERROR ~/.cache/mhw-mod-manager/mhw_mod_manager.log

# View in the app
# Go to "Log" tab in the application
```

### Cleaning Up

```bash
# Remove all deployed mods (via app)
# Click "Undeploy" in toolbar

# Clean staging directory of unused mods
# Remove mods via the app UI (removes from staging)

# Manual cleanup (advanced)
ls ~/.local/share/mhw-mod-manager/mods/
```

## Troubleshooting Common Issues

### Mod Not Loading In-Game

1. Check deployment status (Mods tab)
2. Verify files in game directory:
   ```bash
   ls -la ~/.local/share/Steam/steamapps/common/Monster\ Hunter\ World/nativePC/
   ```
3. Check for symlink (should show `->` arrow)
4. Try Copy mode if symlinks aren't working

### Conflicts Not Showing

1. Click **Refresh Conflicts**
2. Ensure mods are enabled
3. Check that mod files actually overlap

### Application Crashes

1. Check logs: `~/.cache/mhw-mod-manager/mhw_mod_manager.log`
2. Run from terminal to see errors:
   ```bash
   source .venv/bin/activate
   python -m mhw_mod_manager.app
   ```
3. Report issue with log excerpt

## Community and Support

- Check documentation in `README.md`
- Review `SETUP.md` for installation issues
- Check logs before reporting issues
- Include system info (distro, Python version) in bug reports
