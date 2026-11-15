#!/bin/bash
# Flow installer:  curl -fsSL https://raw.githubusercontent.com/nikolaigeorgie/flow/main/install.sh | bash
set -euo pipefail
REPO="https://github.com/nikolaigeorgie/flow.git"
DIR="${FLOW_DIR:-$HOME/.flow}"
pink=$'\033[38;5;205m'; dim=$'\033[2m'; off=$'\033[0m'
say() { echo "${pink}▸${off} $*"; }
die() { echo "✗ $*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "Flow is macOS only."
[[ "$(uname -m)" == "arm64" ]] || die "Flow needs an Apple Silicon Mac (M1 or newer)."
major="$(sw_vers -productVersion | cut -d. -f1)"
(( major >= 14 )) || die "Flow needs macOS 14 (Sonoma) or newer."
xcode-select -p >/dev/null 2>&1 || { xcode-select --install || true; die "Install Apple's Command Line Tools (a window just opened), then run this again."; }

if ! command -v uv >/dev/null 2>&1; then
  say "Installing uv (Python package manager)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
  export PATH="$HOME/.local/bin:$PATH"
fi

if [[ -d "$DIR/.git" ]]; then
  say "Updating Flow in ${DIR}…"
  git -C "$DIR" pull --ff-only --quiet
else
  say "Downloading Flow to ${DIR}…"
  git clone --quiet --depth 1 "$REPO" "$DIR"
fi

say "Setting up Python environment…"
cd "$DIR"
uv venv --quiet --python 3.12 .venv
uv pip install --quiet --python .venv/bin/python -r requirements.txt

say "Building Flow.app…"
osascript -e 'quit app "Flow"' >/dev/null 2>&1 || true
./build_app.sh --login >/dev/null

open "$HOME/Applications/Flow.app"
cat <<MSG

${pink}Flow is installed.${off}

  1. macOS will ask for ${pink}Accessibility${off} and ${pink}Input Monitoring${off}: turn Flow on
     in System Settings → Privacy & Security (it restarts by itself).
  2. First launch downloads the AI models (~8GB, one time).
     You'll see "Flow is on" at the bottom of your screen when it's ready.
  3. Press ${pink}Ctrl+Space${off} anywhere and talk. Tap again (or hold & release) to paste.

${dim}Esc cancels · Menu bar mic icon for settings · Uninstall: ~/.flow/uninstall.sh${off}
MSG
