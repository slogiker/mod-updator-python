#!/usr/bin/env bash
# ==============================================================================
# install.sh: Installs 'update-mod' command to ~/.local/bin for Linux/macOS
# ==============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
TARGET_DIR="$HOME/.local/bin"
COMMAND_NAME="update-mod"
TARGET_BIN="$TARGET_DIR/$COMMAND_NAME"

if [ "$1" == "--uninstall" ]; then
    if [ -f "$TARGET_BIN" ] || [ -L "$TARGET_BIN" ]; then
        rm "$TARGET_BIN"
        echo -e "\033[32mSuccessfully removed $TARGET_BIN\033[0m"
    else
        echo "No existing installation found at $TARGET_BIN."
    fi
    exit 0
fi

echo -e "\033[36m=============================================\033[0m"
echo -e "\033[1;36m  Installing Minecraft Mod Updater (update-mod) \033[0m"
echo -e "\033[36m=============================================\033[0m"

# Ensure target directory exists
mkdir -p "$TARGET_DIR"

# Ensure script is executable
chmod +x "$SCRIPT_DIR/update-mod"

# Create symlink
ln -sf "$SCRIPT_DIR/update-mod" "$TARGET_BIN"

echo -e "\033[32m[SUCCESS] Linked $COMMAND_NAME -> $TARGET_BIN\033[0m"

# Verify PATH
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
    echo -e "\033[33m[NOTE] $TARGET_DIR is not in your current PATH.\033[0m"
    echo "To make '$COMMAND_NAME' accessible anywhere, add this line to your ~/.bashrc or ~/.zshrc:"
    echo -e "  \033[1mexport PATH=\"\$HOME/.local/bin:\$PATH\"\033[0m"
else
    echo -e "\033[32m[READY] You can now run:\033[0m"
    echo -e "  \033[1;97mupdate-mod --help\033[0m"
    echo -e "  \033[1;97mupdate-mod -v 1.21.1 -p fabric --check\033[0m"
fi
