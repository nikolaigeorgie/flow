#!/bin/bash
# Removes Flow. Add --all to also delete your dictionary/settings and the downloaded AI models (~8GB).
set -uo pipefail
osascript -e 'quit app "Flow"' >/dev/null 2>&1; pkill -f "flow.py" 2>/dev/null
osascript -e 'tell application "System Events" to delete (every login item whose name is "Flow")' >/dev/null 2>&1
rm -rf "$HOME/Applications/Flow.app"
DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ "${1:-}" == "--all" ]]; then
  rm -rf "$HOME/Library/Application Support/Flow"
  rm -rf "$HOME/.cache/huggingface/hub/models--mlx-community--Qwen3-ASR-1.7B-8bit" \
         "$HOME/.cache/huggingface/hub/models--mlx-community--Qwen3.5-9B-MLX-4bit"
  echo "Removed app, data and models."
else
  echo "Removed app. Your dictionary/settings and models were kept (run with --all to delete them)."
fi
[[ "$DIR" == "$HOME/.flow" ]] && rm -rf "$DIR"
