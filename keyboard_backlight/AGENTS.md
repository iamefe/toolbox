# keyboard_backlight

curses-based keyboard backlight toggle TUI for macOS with OSX-KVM.

## File Index

| File | Purpose |
|------|---------|
| `kbl.py` | Main TUI — arrow key navigation, kvmleds toggle, state persistence |
| `install.sh` | Auto-installs to `~/.local/share/kblight/kbl.py` via launcher |
| `README.md` | Project documentation |

## Current State

**Completed:**
- Fixed arrow key handling (`keypad(True)`, removed `nodelay`)
- Fixed emoji alignment (☀️ 1 cell, 🌑 2 cells, dynamic spacer)
- Reversed layout (`  On ☀️` / `  Off 🌑`)
- Flushed left (column 0)
- Added 💡 header emoji
- Pushed to GitHub

## Decisions

- **No external dependencies** — pure Python stdlib + curses
- **Zero deps install** — only needs Python 3 and OSX-KVM
- **Auto-detect shell/platform** — handles zsh/bash/fish, arm64/x86_64
- **State file** — `~/.config/kblight/state.json`
