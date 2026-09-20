# Minecraft Mod Updater v2.0

A fast, smart, and safe command-line tool to check and update Minecraft mods directly from [Modrinth](https://modrinth.com).

## What's New in v2.0 (Full Rework)

- **Dedicated Launchers**:
  - **Linux / macOS**: Direct `update-mod` command with flags (no need to invoke `python` manually).
  - **Windows**: `update-mod.bat` and `run.bat` scripts with automatic Python & dependency detection, double-click support, and pause on completion.
- **Check / Test Mode (`-c`, `--check`, `--test`)**:
  - Checks if newer versions exist on Modrinth without downloading or modifying any local files.
  - Generates a clear status table (`Up to date`, `Update available`, `No compatible version`, `Not found`).
- **Configurable Mods Path (`-p`, `--path`, `-d`, `--mods-dir`)**:
  - Defaults to `.mods`.
  - Supports custom paths (`-p ~/.minecraft/mods` or relative directories).
  - Auto-creates directory or detects standard Minecraft directories.
- **Smart Version Detection & Batch API Queries**:
  - Multi-tiered mod identification: Modrinth SHA-1 hash lookup endpoint, `fabric.mod.json`, `quilt.mod.json`, `mods.toml` (Forge/NeoForge), and filename heuristic fallback.
  - Accurate version comparison (identifies if mod is already latest, only downloads actual updates).
- **Safe Partial Updates & Backups**:
  - Never wipes your mods folder blindly.
  - Backs up only the specific files being replaced to `old mods` (or `old mods-N`).
  - Automatically resolves and downloads missing required mod dependencies.

---

## Quick Start

### Linux / macOS

1. Run the one-line installer to link `update-mod` to `~/.local/bin`:
   ```bash
   ./install.sh
   ```

2. Run `update-mod` from anywhere:
   ```bash
   # Check for updates only (test mode)
   update-mod -v 1.21.1 -l fabric --check

   # Update mods in the default .mods directory
   update-mod -v 1.21.1 -l fabric

   # Specify a custom mods path
   update-mod -p ~/.minecraft/mods -v 1.21.1 -l fabric

   # Interactive wizard
   update-mod
   ```

### Windows

- **Double-click**: Simply double-click `update-mod.bat` or `run.bat` in Windows Explorer. It will check for Python/dependencies and guide you through an interactive menu.
- **Command Prompt / PowerShell**:
   ```cmd
   update-mod.bat -v 1.21.1 -l fabric --check
   update-mod.bat -p "%APPDATA%\.minecraft\mods" -v 1.21.1 -l fabric
   ```

---

## Command-Line Options

```
usage: update-mod [-h] [-p PATH] [-v VERSION] [-l LOADER] [-c] [--no-backup]
                  [--no-deps] [-i]

options:
  -h, --help                         Show this help message and exit
  -p, --path, -d, --mods-dir PATH    Path to the mods directory (default: .mods)
  -v, --version VERSION              Target Minecraft version (e.g., 1.21.1, 1.20.1)
  -l, --loader, --platform LOADER    Mod loader: fabric, forge, neoforge, quilt (default: fabric)
  -c, --check, --test                Test / Check mode: check for newer versions without modifying files
  --no-backup                        Do not back up replaced mods before updating
  --no-deps                          Do not automatically download missing required dependencies
  -i, --interactive                  Run in guided interactive mode
```

---

## Examples

### 1. Test / Check if updates exist (Safe dry-run)
```bash
update-mod -v 1.21.1 -l fabric --check
```
Outputs a formatted table:
```
+----------------------------------+--------------------+--------------------+--------------------------+
| Mod Name                         | Installed          | Latest / Target    | Status                   |
+----------------------------------+--------------------+--------------------+--------------------------+
| Fabric API                       | 0.90.0             | 0.116.17+1.21.1    | Update available         |
| Sodium                           | 0.5.8+mc1.20.4     | 0.6.0+mc1.21.1     | Update available         |
| Iris Shaders                     | 1.8.0+1.21.1       | 1.8.0+1.21.1       | Up to date               |
+----------------------------------+--------------------+--------------------+--------------------------+

Summary:
  Total mods scanned:   3
  Up-to-date:           1
  Updates available:    2

[TEST COMPLETE] No files were downloaded or modified.
```

### 2. Apply updates to custom Minecraft folder
```bash
update-mod -p ~/.minecraft/mods -v 1.21.1 -l fabric
```

### 3. Interactive Mode
Run `update-mod` without arguments. You will be prompted for:
1. Mods folder path (default: `.mods`)
2. Target Minecraft version (e.g. `1.21.1`)
3. Loader (`fabric`, `forge`, `neoforge`, `quilt`)
4. Action (`Check for updates only` or `Update mods now`)

---

## Running Tests

Run the test suite using Python's built-in `unittest`:
```bash
python3 -m unittest discover -s tests
```

---

## Architecture

- `mod_updater/api.py`: Modrinth API client with batch SHA-1 hash lookup and version file updates.
- `mod_updater/inspector.py`: Local JAR scanner supporting Fabric, Quilt, Forge, and NeoForge metadata.
- `mod_updater/version_checker.py`: Semantic version parsing, publication date comparison, and update determination.
- `mod_updater/updater.py`: Core update orchestrator (scans, checks, creates backups, applies updates).
- `mod_updater/ui.py`: ANSI color management and table formatting.
- `mod_updater/cli.py`: Command-line interface and interactive menu.
- `update-mod`: Linux/macOS executable wrapper.
- `update-mod.bat` / `run.bat`: Windows batch launchers.
