#!/bin/sh
# Native focus and cursor manager for Silent Hill 2 Remake on CrossOver.
# Hides CrossOver.app & Menu Helper, activates SHProto-Win64-Shipping.exe,
# and brings the game window to the foreground.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HELPER_BIN="$SCRIPT_DIR/sh2_focus"

if [ -x "$HELPER_BIN" ]; then
    exec "$HELPER_BIN" "$@"
fi

# Fallback: Hide CrossOver and bring game process to front
for i in $(seq 1 45); do
    sleep 1
    osascript -e '
    tell application "System Events"
        if exists (application process "CrossOver") then
            set visible of application process "CrossOver" to false
        end if
        set g to every application process whose name contains "SHProto" or name contains "Silent"
        if (count of g) > 0 then
            set frontmost of (item 1 of g) to true
        end if
    end tell' >/dev/null 2>&1
    pgrep -f "SHProto-Win64-Shipping.exe" >/dev/null 2>&1 && break
done
