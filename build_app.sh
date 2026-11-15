#!/bin/zsh
# Builds ~/Applications/Flow.app: a tiny signed launcher that runs flow.py from this folder.
# Usage: ./build_app.sh [--login]   (--login also adds Flow to Login Items)
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Applications/Flow.app"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

[[ -x "$DIR/.venv/bin/python" ]] || { echo "Missing $DIR/.venv - run install.sh first"; exit 1; }
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# App icon from the 1024px master
mkdir -p "$TMP/Flow.iconset"
for s in 16 32 128 256 512; do
  sips -z $s $s "$DIR/assets/icon_1024.png" --out "$TMP/Flow.iconset/icon_${s}x${s}.png" >/dev/null
  sips -z $((s*2)) $((s*2)) "$DIR/assets/icon_1024.png" --out "$TMP/Flow.iconset/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$TMP/Flow.iconset" -o "$APP/Contents/Resources/Flow.icns"

# Launcher: the app process spawns Python, so macOS attributes mic/keyboard permissions to "Flow".
cat > "$TMP/launcher.c" <<'C'
#include <spawn.h>
#include <stdlib.h>
#include <sys/wait.h>
extern char **environ;
int main(void) {
    char *argv[] = {FLOW_DIR "/.venv/bin/python", "-u", FLOW_DIR "/flow.py", NULL};
    setenv("FLOW_LOG", "1", 1);
    pid_t pid;
    if (posix_spawn(&pid, argv[0], NULL, NULL, argv, environ) != 0) return 1;
    int st; waitpid(pid, &st, 0);
    return WEXITSTATUS(st);
}
C
clang -O2 -DFLOW_DIR="\"$DIR\"" -o "$APP/Contents/MacOS/Flow" "$TMP/launcher.c"

cat > "$APP/Contents/Info.plist" <<'P'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Flow</string>
  <key>CFBundleDisplayName</key><string>Flow</string>
  <key>CFBundleIdentifier</key><string>local.flow.dictation</string>
  <key>CFBundleExecutable</key><string>Flow</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>CFBundleIconFile</key><string>Flow</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>LSUIElement</key><true/>
  <key>NSMicrophoneUsageDescription</key><string>Flow listens only while you're dictating. Audio never leaves your Mac.</string>
</dict></plist>
P
codesign --force -s - "$APP" 2>/dev/null

if [[ "${1:-}" == "--login" ]]; then
  osascript -e 'tell application "System Events" to delete (every login item whose name is "Flow")' >/dev/null 2>&1 || true
  osascript -e "tell application \"System Events\" to make login item at end with properties {path:\"$APP\", hidden:true}" >/dev/null
fi
echo "Built $APP"
