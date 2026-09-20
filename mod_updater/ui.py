"""Terminal UI helpers, color formatting, and table printing."""

import os
import sys
from typing import Optional


class Colors:
    """ANSI color codes with auto-disable support."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # Colors
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"
    GRAY = "\033[90m"
    WHITE = "\033[97m"

    # Bright variants
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_RED = "\033[91m"


# Check whether ANSI color codes should be disabled
def colors_enabled() -> bool:
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb":
        return False
    # Windows 10+ supports ANSI natively; enable virtual terminal processing if possible
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # STD_OUTPUT_HANDLE = -11
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
                return True
        except Exception:
            return False
    return sys.stdout.isatty()


USE_COLORS = colors_enabled()


def color(text: str, color_code: str) -> str:
    """Wraps text in ANSI color code if supported."""
    if not USE_COLORS:
        return text
    return f"{color_code}{text}{Colors.RESET}"


def print_banner() -> None:
    """Prints a styled banner for the application."""
    border = color("================================================================", Colors.CYAN)
    title = color("             MINECRAFT MOD UPDATER v2.0.0                      ", Colors.BOLD + Colors.BRIGHT_CYAN)
    subtitle = color("             Fast, Safe & Smart Mod Manager                     ", Colors.DIM + Colors.WHITE)
    print(f"\n{border}")
    print(title)
    print(subtitle)
    print(f"{border}\n")


def print_status_table(rows: list[dict[str, str]]) -> None:
    """
    Prints a formatted table for mod update results.
    Each item in rows has keys: 'name', 'installed', 'target', 'status'.
    """
    col_name = 32
    col_inst = 18
    col_target = 18
    col_status = 24

    header_border = color("+" + "-" * (col_name + 2) + "+" + "-" * (col_inst + 2) + "+" + "-" * (col_target + 2) + "+" + "-" * (col_status + 2) + "+", Colors.GRAY)
    header_text = (
        f"| {color('Mod Name', Colors.BOLD):<{col_name + (len(color('', Colors.BOLD)) if USE_COLORS else 0)}} "
        f"| {color('Installed', Colors.BOLD):<{col_inst + (len(color('', Colors.BOLD)) if USE_COLORS else 0)}} "
        f"| {color('Latest / Target', Colors.BOLD):<{col_target + (len(color('', Colors.BOLD)) if USE_COLORS else 0)}} "
        f"| {color('Status', Colors.BOLD):<{col_status + (len(color('', Colors.BOLD)) if USE_COLORS else 0)}} |"
    )

    print(header_border)
    print(header_text)
    print(header_border)

    for row in rows:
        name = row.get("name", "Unknown")[:col_name]
        inst = row.get("installed", "---")[:col_inst]
        target = row.get("target", "---")[:col_target]
        status = row.get("status", "")

        status_colored = status
        if "UP TO DATE" in status.upper():
            status_colored = color(status, Colors.BRIGHT_GREEN)
        elif "UPDATE" in status.upper():
            status_colored = color(status, Colors.BRIGHT_YELLOW)
        elif "NO COMPATIBLE" in status.upper():
            status_colored = color(status, Colors.YELLOW)
        elif "NOT FOUND" in status.upper() or "UNKNOWN" in status.upper():
            status_colored = color(status, Colors.GRAY)
        elif "ERROR" in status.upper():
            status_colored = color(status, Colors.BRIGHT_RED)

        # Pad string accounting for ANSI escape codes
        def pad(colored_str: str, raw_str: str, width: int) -> str:
            extra = len(colored_str) - len(raw_str)
            return f"{colored_str:<{width + extra}}"

        print(
            f"| {name:<{col_name}} "
            f"| {inst:<{col_inst}} "
            f"| {target:<{col_target}} "
            f"| {pad(status_colored, status, col_status)} |"
        )

    print(header_border)


def prompt_user(prompt: str, default: Optional[str] = None) -> str:
    """Prompts the user with a default fallback."""
    if default:
        display = f"{color('>>', Colors.BRIGHT_CYAN)} {prompt} [{color(default, Colors.BOLD)}]: "
    else:
        display = f"{color('>>', Colors.BRIGHT_CYAN)} {prompt}: "
    
    try:
        val = input(display).strip()
        return val if val else (default or "")
    except (EOFError, KeyboardInterrupt):
        print("\n[Cancelled]")
        sys.exit(0)
