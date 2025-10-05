# Minecraft Mod Updater

This script helps you update Minecraft mods by scanning a local `mods` folder, finding compatible versions on Modrinth, and downloading them.

Author: slogiker

## Core features

- Scan and update mods automatically.
- Queue and download required dependencies when found.
- Prefer stable "release" versions; fall back to beta/alpha if necessary.
- Back up existing mods to an `old mods` folder before applying changes.
- Command-line flags for automation and dry-run support (`--test`).
- Error details are written to `debug.txt` on unexpected failures.

## Requirements

- Python 3.7 or newer
- The `requests` Python package

Create a `requirements.txt` file with the required packages (a sample is included in this repository).

## Installation

1. Clone the repository or download the files:

```powershell
git clone https://github.com/slogiker/mod-updator-python.git
cd mod-updator-python
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

## Usage

Run the script from the project folder.

Interactive mode (prompts for Minecraft version and loader):

```powershell
python updater.py
```

Command-line mode:

- `--version` / `-v` : Minecraft version (for example `-v 1.21.1`).
- `--platform` / `-p`: Mod loader (`fabric`, `forge`, `quilt`).
- `--test`           : Dry-run; no files are downloaded or changed.

Examples:

```powershell
python updater.py -v 1.21.1 -p fabric
python updater.py -v 1.20.4 -p forge --test
```

## Customization

If the script cannot reliably map a JAR filename to a Modrinth project, add a mapping to the `MOD_ID_OVERRIDES` dictionary in `updater.py`.

Example:

```python
MOD_ID_OVERRIDES = {
    "voicechat": "simple-voice-chat",
    "voicechat-fabric": "simple-voice-chat",
}
```

## Contributing

Open an issue or submit a pull request for bug reports or improvements.

## Notes

- The script tries to detect the Minecraft directory using the `APPDATA` environment variable on Windows. It falls back to common macOS/Linux locations if not found.
- Backups are created in a folder named `old mods` (or `old mods-N` if previous backups exist) in the same parent directory as the `mods` folder.


