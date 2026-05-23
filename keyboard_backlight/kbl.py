#!/usr/bin/env python3
"""
kbl — minimal keyboard backlight toggle (curses, no external deps)
"""

import curses
import os
import signal
import subprocess
import shutil
import json
import sys
import termios
import tty
import unicodedata
from pathlib import Path
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path.home() / ".config" / "kblight" / "state.json"
DEFAULT_STATE = {"backlight_on": False}

KVMSWITCH_HINTS = [
    Path.home() / "OSX-KVM" / "kvmswitch",
    Path("/usr/local/bin/kvmswitch"),
    Path("/opt/homebrew/bin/kvmswitch"),
]


def find_kvmswitch() -> Optional[Path]:
    if which := shutil.which("kvmswitch"):
        return Path(which)
    for hint in KVMSWITCH_HINTS:
        if hint.exists():
            return hint
    return None


def load_state() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception:
        return DEFAULT_STATE.copy()


def save_state(state: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(state, indent=2))


def run_kvmswitch(path: Path) -> bool:
    try:
        subprocess.run([str(path)], check=True, capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def run_kvmleds(args: list[str]) -> bool:
    """Run kvmleds with given args (e.g. ['+scroll'] or ['-scroll']). Returns True on success."""
    try:
        kvm_dir = Path(os.environ.get("OSX_KVM", "/Users/iamefe/OSX-KVM"))
        subprocess.run([kvm_dir / "kvmleds"] + args, check=True, capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def read_kvmleds_scroll() -> bool | None:
    """Read current scroll lock state via kvmleds -v. Returns True if scroll ON, False if OFF, None if unknown."""
    try:
        kvm_dir = Path(os.environ.get("OSX_KVM", "/Users/iamefe/OSX-KVM"))
        result = subprocess.run([kvm_dir / "kvmleds", "-v"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0 or not result.stdout.strip():
            return None
        for line in result.stdout.strip().splitlines():
            if "(null)" not in line and "USB Keyboard" in line:
                parts = line.split()
                return "scroll" in parts and "-scroll" not in parts
        return None
    except Exception:
        return None


# ── Colors ────────────────────────────────────────────────────────────────────

def init_colors() -> None:
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)   # selected
    curses.init_pair(2, curses.COLOR_RED, -1)     # error
    curses.init_pair(3, curses.COLOR_WHITE, -1)   # unselected
    curses.init_pair(4, curses.COLOR_CYAN, -1)    # header
    curses.init_pair(5, curses.COLOR_YELLOW, -1)  # footer


def safe_add(stdscr, y: int, x: int, text: str, attr: int) -> None:
    try:
        stdscr.addnstr(y, x, text, stdscr.getmaxyx()[1] - x, attr)
    except curses.error:
        pass


# ── Main loop ────────────────────────────────────────────────────────────────

def run(stdscr) -> None:
    curses.curs_set(0)

    kvmswitch = find_kvmswitch()
    state = load_state()
    # Read actual hardware state first, fall back to saved
    hw = read_kvmleds_scroll()
    backlight_on = hw if hw is not None else state.get("backlight_on", False)

    selected = 0  # 0 = On, 1 = Off
    error = None

    labels = ["On", "Off"]
    sel_icons = ["\u2600\uFE0F", "\U0001F311"]   # sun ☀️, moon 🌑

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Header
        safe_add(stdscr, 1, 0, "  💡 Welcome to kbl controls",
                 curses.color_pair(4) | curses.A_BOLD)

        # Prompt
        safe_add(stdscr, 2, 0, "  Choose a keyboard light mode:", curses.color_pair(3))

        # Menu items — fixed-width icon column so text always aligns
        # The icon column uses the max display width (2 cells for 🌑)
        def dwidth(s):
            w = 0
            for c in s:
                cp = ord(c)
                # Skip variation selectors and ZWJ — they have 0 display width
                if 0xFE00 <= cp <= 0xFE0F or 0xE0020 <= cp <= 0xE007F:
                    continue
                wc = unicodedata.east_asian_width(c)
                w += 2 if wc in ('W', 'F') else 1
            return w

        for idx, label in enumerate(labels):
            y = 4 + idx
            if idx == selected:
                icon = sel_icons[idx]
                attr = curses.color_pair(1) | curses.A_BOLD
                safe_add(stdscr, y, 0, f"  {label} {icon}", attr)
            else:
                attr = curses.color_pair(3)
                safe_add(stdscr, y, 0, f"  {label}", attr)

        # Error
        if error:
            safe_add(stdscr, h - 2, 0, f"  ✗ {error}",
                     curses.color_pair(2) | curses.A_BOLD)

        # Footer
        safe_add(stdscr, h - 1, 0,
                 "  ↑↓ Navigate   Enter Select   Ctrl+C/Q Quit",
                 curses.color_pair(5))

        stdscr.refresh()

        # ── Input ──
        key = stdscr.getch()

        if key == 17:          # Ctrl+Q
            return
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            if kvmswitch is None:
                error = "kvmleds not found — check OSX-KVM path"
                continue
            # Use kvmleds directly: '+scroll' turns ON, '-scroll' turns OFF
            target_on = (selected == 0)
            if target_on:
                ok = run_kvmleds(["+scroll"])
            else:
                ok = run_kvmleds(["-scroll"])
            if ok:
                backlight_on = target_on
                save_state({"backlight_on": backlight_on})
            else:
                error = "kvmleds failed"
            error = None
        elif key == curses.KEY_UP or key == ord("k"):
            selected = (selected - 1) % len(labels)
            error = None
        elif key == curses.KEY_DOWN or key == ord("j"):
            selected = (selected + 1) % len(labels)
            error = None


def main() -> None:
    # Replace curses.wrapper with our own version that guarantees terminal reset.
    # curses.wrapper's cleanup handler crashes on SIGINT in some terminal setups.
    fd = sys.stdin.fileno()
    orig = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        stdscr = curses.initscr()
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        curses.init_pair(3, curses.COLOR_WHITE, -1)
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        curses.init_pair(5, curses.COLOR_YELLOW, -1)
        curses.curs_set(0)
        stdscr.keypad(True)  # enable keypad keys (arrow keys, F1, etc.)
        stdscr.nodelay(True)

        run(stdscr)
    except KeyboardInterrupt:
        pass
    except curses.error:
        pass
    finally:
        try:
            curses.endwin()
        except curses.error:
            pass
        termios.tcsetattr(fd, termios.TCSADRAIN, orig)


if __name__ == "__main__":
    main()
