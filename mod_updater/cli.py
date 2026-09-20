"""Command-line interface and interactive wizard for Minecraft Mod Updater."""

import argparse
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from .api import ModrinthClient
from .inspector import LocalMod
from .ui import Colors, color, print_banner, print_status_table, prompt_user
from .updater import (
    apply_mod_updates,
    check_for_updates,
    scan_local_mods,
)
from .version_checker import UpdateStatus


def get_default_minecraft_dir() -> Optional[Path]:
    """Attempts to find the standard Minecraft directory on this system."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            p = Path(appdata) / ".minecraft"
            if p.exists():
                return p
    elif sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / "minecraft"
        if p.exists():
            return p
    else:  # Linux / Unix
        p = Path.home() / ".minecraft"
        if p.exists():
            return p
    return None


def log_crash(exception: Exception) -> None:
    """Logs unexpected exceptions to debug.txt."""
    log_file = Path("debug.txt")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"--- CRASH LOG: {now} ---\n")
        f.write(traceback.format_exc())
        f.write("\n--- END OF LOG ---\n\n")
    print(f"\n{color('[CRITICAL]', Colors.BRIGHT_RED)} An unexpected error occurred. Details saved to '{log_file}'.")


def run_cli(args: argparse.Namespace) -> int:
    """Executes the CLI logic based on parsed arguments."""
    print_banner()

    # Determine mods directory
    mods_path_str: str = args.path
    is_interactive = args.interactive or (not args.version and not args.loader and sys.stdin.isatty())

    # Interactive path prompt if needed
    if is_interactive and not args.path_specified:
        default_candidate = ".mods"
        mc_dir = get_default_minecraft_dir()
        if not Path(".mods").exists() and mc_dir and (mc_dir / "mods").exists():
            print(f"{color('[INFO]', Colors.CYAN)} Standard Minecraft mods folder found: {mc_dir / 'mods'}")
        
        mods_path_str = prompt_user("Enter path to your mods directory", default=default_candidate)

    mods_dir = Path(os.path.expanduser(mods_path_str)).resolve()

    if not mods_dir.exists():
        if is_interactive:
            create_choice = prompt_user(f"Directory '{mods_dir}' does not exist. Create it? (y/n)", default="y").lower()
            if create_choice.startswith("y"):
                mods_dir.mkdir(parents=True, exist_ok=True)
            else:
                print(color("[INFO] Aborted.", Colors.YELLOW))
                return 1
        else:
            mods_dir.mkdir(parents=True, exist_ok=True)

    print(f"{color('[INFO]', Colors.CYAN)} Mods directory: {color(str(mods_dir), Colors.BOLD)}")

    # Scan mods
    local_mods: list[LocalMod] = scan_local_mods(mods_dir)
    if not local_mods:
        print(f"\n{color('[INFO]', Colors.YELLOW)} No .jar mod files found in {mods_dir}.")
        print(f"Place some mods into '{mods_dir}' and run again.")
        return 0

    print(f"{color('[INFO]', Colors.GREEN)} Found {len(local_mods)} mod(s) to inspect.")

    # Target version and loader
    game_version = args.version
    loader = (args.loader or "").lower()

    if is_interactive:
        if not game_version:
            game_version = prompt_user("Enter desired Minecraft version (e.g., 1.21.1, 1.20.1)", default="1.21.1")
        if not loader:
            print("\nAvailable Mod Loaders:")
            print("  1) Fabric (default)")
            print("  2) Forge")
            print("  3) NeoForge")
            print("  4) Quilt")
            loader_choice = prompt_user("Choose loader [1-4 or name]", default="1").lower()
            mapping = {"1": "fabric", "2": "forge", "3": "neoforge", "4": "quilt"}
            loader = mapping.get(loader_choice, loader_choice)

    if not game_version:
        print(color("[ERROR] Minecraft version must be specified via -v / --version or interactively.", Colors.RED))
        return 1

    if not loader:
        loader = "fabric"

    check_mode = args.check
    if is_interactive and not args.check:
        action_choice = prompt_user("\nAction: [1] Check for updates only (test)  [2] Update mods now", default="2")
        if action_choice.strip() == "1":
            check_mode = True

    print(f"\n{color('[CONFIG]', Colors.CYAN)} Target MC: {color(game_version, Colors.BOLD)} | Loader: {color(loader, Colors.BOLD)} | Mode: {color('TEST / CHECK ONLY' if check_mode else 'UPDATE', Colors.BOLD)}")
    print(f"{color('[INFO]', Colors.CYAN)} Checking Modrinth for updates...")

    client = ModrinthClient()
    updates = check_for_updates(local_mods, game_version, loader, client)

    # Format table output
    table_rows = []
    up_to_date_count = 0
    update_available_count = 0
    not_found_count = 0
    incompatible_count = 0

    for u in updates:
        target_v = u.target_version or "---"
        status_str = u.status
        if u.status == UpdateStatus.UP_TO_DATE:
            up_to_date_count += 1
        elif u.status == UpdateStatus.UPDATE_AVAILABLE:
            update_available_count += 1
        elif u.status == UpdateStatus.NO_COMPATIBLE:
            incompatible_count += 1
        else:
            not_found_count += 1

        table_rows.append({
            "name": u.project_title,
            "installed": u.installed_version,
            "target": target_v,
            "status": status_str,
        })

    print("\n")
    print_status_table(table_rows)

    print(f"\n{color('Summary:', Colors.BOLD)}")
    print(f"  Total mods scanned:   {len(updates)}")
    print(f"  Up-to-date:           {color(str(up_to_date_count), Colors.GREEN)}")
    print(f"  Updates available:    {color(str(update_available_count), Colors.BRIGHT_YELLOW)}")
    if incompatible_count:
        print(f"  Incompatible version: {color(str(incompatible_count), Colors.YELLOW)}")
    if not_found_count:
        print(f"  Unmatched / unknown:  {color(str(not_found_count), Colors.GRAY)}")

    if check_mode:
        print(f"\n{color('[TEST COMPLETE]', Colors.BRIGHT_GREEN)} No files were downloaded or modified.")
        return 0

    if update_available_count == 0:
        print(f"\n{color('[DONE]', Colors.BRIGHT_GREEN)} All compatible mods are already up-to-date!")
        return 0

    # Confirmation in interactive mode
    if is_interactive:
        confirm = prompt_user(f"\nProceed with updating {update_available_count} mod(s)? (y/n)", default="y").lower()
        if not confirm.startswith("y"):
            print(color("[INFO] Update cancelled by user.", Colors.YELLOW))
            return 0

    # Apply updates
    print(f"\n{color('[STARTING UPDATE]', Colors.BRIGHT_CYAN)} Applying updates...")
    result = apply_mod_updates(
        updates=updates,
        mods_dir=mods_dir,
        backup=not args.no_backup,
        client=client,
        download_dependencies=not args.no_deps,
        game_version=game_version,
        loader=loader,
    )

    print(f"\n{color('[UPDATE COMPLETED]', Colors.BRIGHT_GREEN)}")
    print(f"  Updated:      {result['updated']}")
    print(f"  Dependencies: {result['dependencies']}")
    if result["errors"]:
        print(f"  Errors:       {color(str(result['errors']), Colors.RED)}")

    return 0 if result["errors"] == 0 else 1


def main() -> None:
    """Entry point for CLI command."""
    parser = argparse.ArgumentParser(
        prog="update-mod",
        description="Fast, safe, and automated Minecraft mod updater powered by Modrinth.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-p", "--path", "-d", "--mods-dir",
        dest="path",
        default=".mods",
        help="Path to the mods directory (default: .mods)",
    )
    parser.add_argument(
        "-v", "--version",
        dest="version",
        help="Target Minecraft version (e.g., 1.21.1, 1.20.1)",
    )
    parser.add_argument(
        "-l", "--loader", "--platform",
        dest="loader",
        help="Mod loader: fabric, forge, neoforge, quilt (default: fabric)",
    )
    parser.add_argument(
        "-c", "--check", "--test",
        action="store_true",
        dest="check",
        help="Test / Check mode: check for newer versions without downloading or modifying files",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not back up replaced mods before updating",
    )
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="Do not automatically download missing required mod dependencies",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in guided interactive mode",
    )

    # Track if user explicitly specified path
    path_args = {"-p", "--path", "-d", "--mods-dir"}
    raw_args = sys.argv[1:]
    path_specified = any(arg in path_args or any(arg.startswith(f"{p}=") for p in path_args) for arg in raw_args)

    args = parser.parse_args()
    args.path_specified = path_specified

    exit_code = 0
    try:
        exit_code = run_cli(args)
    except KeyboardInterrupt:
        print("\n[Aborted]")
        exit_code = 130
    except Exception as e:
        log_crash(e)
        exit_code = 1

    # Keep console open if running directly without flags in interactive terminal or on Windows
    if ("--check" not in raw_args and "--test" not in raw_args and len(raw_args) == 0 and sys.stdin.isatty()):
        try:
            input("\nPress Enter to exit...")
        except (EOFError, KeyboardInterrupt):
            pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
