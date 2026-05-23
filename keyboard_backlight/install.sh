#!/usr/bin/env bash
set -e

echo ""
echo "⌨  kbl installer"
echo "────────────────────────────────"

# ── 0. Detect architecture ────────────────────────────────────────────────────

ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
  echo "→ Apple Silicon detected (arm64)"
  BREW_PREFIX="/opt/homebrew"
else
  echo "→ Intel Mac detected (x86_64)"
  BREW_PREFIX="/usr/local"
fi

BREW_BIN="$BREW_PREFIX/bin"
KBLIGHT_DATA="$HOME/.local/share/kblight"

# ── Ensure Homebrew is available ──────────────────────────────────────────────

ensure_brew() {
  if command -v brew &>/dev/null; then
    return 0
  fi
  echo "  → Homebrew not found, installing..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  if [ "$ARCH" = "arm64" ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  else
    eval "$(/usr/local/bin/brew shellenv)"
  fi

  if ! command -v brew &>/dev/null; then
    echo "  ✗ Homebrew install failed. Visit https://brew.sh and try again."
    exit 1
  fi
  echo "  ✓ Homebrew installed"
}

# ── Resolve Python ────────────────────────────────────────────────────────────

echo ""
echo "→ Resolving Python..."

if [ -x "$BREW_BIN/python3" ]; then
  PYTHON="$BREW_BIN/python3"
elif command -v python3 &>/dev/null; then
  PYTHON=$(command -v python3)
else
  echo "  → python3 not found, installing via Homebrew..."
  ensure_brew
  brew install python
  PYTHON="$BREW_BIN/python3"
  if [ ! -x "$PYTHON" ]; then
    echo "  ✗ Python install failed. Try manually: brew install python"
    exit 1
  fi
  echo "  ✓ Python installed"
fi

echo "  ✓ Python: $PYTHON"

# ── 1. kvmswitch ─────────────────────────────────────────────────────────────

echo ""
echo "→ Setting up kvmswitch..."

KVM_DIR="$HOME/OSX-KVM"
KVM_BIN="$KVM_DIR/kvmswitch"

EXISTING=$(command -v kvmswitch 2>/dev/null || echo "")

if [ -n "$EXISTING" ]; then
  echo "  ✓ kvmswitch found at $EXISTING"
  KVM_BIN="$EXISTING"
elif [ -f "$KVM_BIN" ]; then
  echo "  ✓ kvmswitch already at $KVM_BIN"
else
  echo "  → kvmswitch not found, cloning OSX-KVM..."
  # git may trigger Xcode CLT install prompt on a clean Mac — expected
  if [ ! -d "$KVM_DIR" ]; then
    git clone https://github.com/stoutput/OSX-KVM "$KVM_DIR"
  else
    echo "  ✓ ~/OSX-KVM already exists, skipping clone"
  fi

  if [ ! -f "$KVM_BIN" ]; then
    echo "  ✗ kvmswitch binary not found in $KVM_DIR after clone"
    echo "    Please check https://github.com/stoutput/OSX-KVM manually"
    exit 1
  fi
fi

chmod +x "$KVM_BIN"
echo "  ✓ kvmswitch ready at $KVM_BIN"

# ── 2. Detect shell and rc file ───────────────────────────────────────────────

echo ""
echo "→ Detecting shell..."

CURRENT_SHELL=$(basename "$SHELL")

case "$CURRENT_SHELL" in
  zsh)  RC_FILE="$HOME/.zshrc" ;;
  bash)
    RC_FILE="$HOME/.bashrc"
    [ -f "$HOME/.bash_profile" ] && RC_FILE="$HOME/.bash_profile"
    ;;
  fish) RC_FILE="$HOME/.config/fish/config.fish" ;;
  *)    RC_FILE="$HOME/.profile" ;;
esac

echo "  ✓ Shell: $CURRENT_SHELL → $RC_FILE"

# ── 3. Patch rc file ──────────────────────────────────────────────────────────

echo ""
echo "→ Patching $RC_FILE..."

add_if_missing() {
  local line="$1"
  local file="$2"
  if ! grep -qF "$line" "$file" 2>/dev/null; then
    echo "$line" >> "$file"
    echo "  + Added: $line"
  else
    echo "  ✓ Already present: $(echo "$line" | cut -c1-60)"
  fi
}

if [ "$CURRENT_SHELL" = "fish" ]; then
  add_if_missing "set -gx PATH $KVM_DIR \$PATH" "$RC_FILE"
  add_if_missing "alias kvmswitch '$KVM_BIN'" "$RC_FILE"
else
  add_if_missing "export PATH=\"$KVM_DIR:\$PATH\"" "$RC_FILE"
  add_if_missing "alias kvmswitch='$KVM_BIN'" "$RC_FILE"
  # Only add BREW_BIN to PATH if not already resolvable
  if ! command -v brew &>/dev/null; then
    add_if_missing "export PATH=\"$BREW_BIN:\$PATH\"" "$RC_FILE"
  fi
fi

# ── 4. Install kbl ────────────────────────────────────────────────────────────

echo ""
echo "→ Installing kbl..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$SCRIPT_DIR/kbl.py" ]; then
  echo "  ✗ kbl.py not found next to install.sh"
  exit 1
fi

# Copy kbl.py to a stable data dir so the launcher doesn't depend on source folder
mkdir -p "$KBLIGHT_DATA"
cp "$SCRIPT_DIR/kbl.py" "$KBLIGHT_DATA/kbl.py"

# Ensure install bin dir exists
mkdir -p "$BREW_BIN"

# Write launcher pointing to stable data path
cat > "$BREW_BIN/kbl" << LAUNCHEREOF
#!/usr/bin/env bash
exec "$PYTHON" "$KBLIGHT_DATA/kbl.py" "\$@"
LAUNCHEREOF

chmod +x "$BREW_BIN/kbl"
echo "  ✓ kbl.py copied → $KBLIGHT_DATA/kbl.py"
echo "  ✓ launcher installed → $BREW_BIN/kbl"

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "────────────────────────────────"
echo "✓ All done!"
echo ""
echo "→ Reloading $RC_FILE..."
# shellcheck disable=SC1090
source "$RC_FILE" 2>/dev/null \
  && echo "  ✓ Sourced $RC_FILE" \
  || echo "  ⚠ Could not auto-source — run manually: source $RC_FILE"
echo ""
echo "  Run: kbl"
echo ""
