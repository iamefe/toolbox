# ⌨ kbl

A lightweight terminal UI for controlling your keyboard backlight on macOS. Wraps [`kvmswitch`](https://github.com/stoutput/OSX-KVM) with zero external Python dependencies — uses only the standard library (`curses`).

![Platform](https://img.shields.io/badge/platform-macOS-lightgrey) ![Python](https://img.shields.io/badge/python-3.11+-blue) ![Dependencies](https://img.shields.io/badge/deps-none-brightgreen)

---

## Requirements

- macOS (Intel or Apple Silicon)
- Python 3.11+ (auto-installed if missing)
- Homebrew (auto-installed if missing)
- A USB keyboard supported by `kvmswitch`

---

## Install

```bash
chmod +x install.sh && ./install.sh
```

The installer will automatically:

1. Detect your architecture (Intel or Apple Silicon)
2. Install Homebrew if not present
3. Install Python via Homebrew if not present
4. Clone [`OSX-KVM`](https://github.com/stoutput/OSX-KVM) and set up `kvmswitch` if not already present
5. Add `kvmswitch` to your PATH via your shell's rc file (`.zshrc`, `.bashrc`, `.bash_profile`, or `config.fish`)
6. Copy `kbl.py` to `~/.local/share/kblight/`
7. Install the `kbl` launcher to `/usr/local/bin` (Intel) or `/opt/homebrew/bin` (Apple Silicon)
8. Reload your shell config

> **Note:** On a completely clean Mac, `git clone` may trigger an Apple Xcode Command Line Tools installation prompt. This is expected — follow the on-screen prompt and re-run the installer after it completes.

---

## Usage

```bash
kbl
```

### What you see

```
  > Welcome to kbl controls

  Choose a keyboard light mode:
    ☀️ On
    ⚪ Off

  ↑↓ Navigate   Enter Select   Ctrl+Q Quit
```

### Controls

| Key | Action |
|---|---|
| `↑` / `↓` (or `k` / `j`) | Navigate menu |
| `Enter` | Select (toggle backlight) |
| `Ctrl+Q` | Quit |

---

## How it works

kbl shells out to `kvmswitch` when you select a mode. `kvmswitch` sends a HID signal to your keyboard that toggles the backlight — something macOS doesn't expose natively for third-party keyboards.

State (on/off) is persisted between sessions at:

```
~/.config/kblight/state.json
```

---

## File layout

```
install.sh                        # installer
kbl.py                            # source (copied during install)

~/.local/share/kblight/
  kbl.py                          # stable runtime copy

/usr/local/bin/kbl                # launcher (Intel)
/opt/homebrew/bin/kbl             # launcher (Apple Silicon)

~/.config/kblight/
  state.json                      # persisted state
```

---

## Supported keyboards

kbl works with any keyboard supported by `kvmswitch`. This includes many generic USB keyboards with the Sunplus (`0x1c4f`) chipset that are not detected by OpenRGB or manufacturer software on macOS.

To check if your keyboard is detected by macOS:

```bash
system_profiler SPUSBDataType | grep -A 5 -i keyboard
```

---

## Uninstall

```bash
rm /usr/local/bin/kbl             # Intel
# or
rm /opt/homebrew/bin/kbl          # Apple Silicon

rm -rf ~/.local/share/kblight
rm -rf ~/.config/kblight
```

Remove the lines added to your rc file manually if desired.

---

## Troubleshooting

**`kvmswitch not found — check PATH`**
Run `source ~/.zshrc` (or your shell's rc file) and try again. If it persists, check that `~/OSX-KVM/kvmswitch` exists and is executable (`chmod +x ~/OSX-KVM/kvmswitch`).

**`kvmswitch failed — check permissions`**
Try running `kvmswitch` directly in your terminal to see the error. You may need to allow it in **System Settings → Privacy & Security**.

**Backlight doesn't respond**
Your keyboard may not be supported by `kvmswitch`. Try the `Fn` key combos on your keyboard directly (e.g. `Fn + ↑/↓`, `Fn + Scroll Lock`).

---

## License

MIT
