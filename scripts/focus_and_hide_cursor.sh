#!/bin/sh
# Waits for Silent Hill 2 Remake (SHProto-Win64-Shipping.exe) to create its
# on-screen D3D11 window, releases foreground focus from CrossOver's windowless
# Menu Helper process, activates the game window, and hides the macOS cursor.

for w in $(seq 1 45); do
  sh_pid=$(pgrep -f "SHProto-Win64-Shipping.exe" | head -n 1)
  if [ -n "$sh_pid" ]; then
    break
  fi
  sleep 1
done

[ -z "$sh_pid" ] && exit 0

for i in 1 2 3 4 5 6 7 8 9 10 12 15 18 22; do
  sleep 1
  sh_pid=$(pgrep -f "SHProto-Win64-Shipping.exe" | head -n 1)
  [ -z "$sh_pid" ] && exit 0
  mh_pid=$(pgrep -f "Silent Hill 2.app/Contents/MacOS/Menu Helper" | head -n 1)
  osascript -e 'tell application "System Events" to set frontmost of (every process whose unix id is '"$sh_pid"' or name contains "SHProto" or name contains "wine") to true' >/dev/null 2>&1
  osascript -l JavaScript -e '
    ObjC.import("AppKit");
    ObjC.import("CoreGraphics");
    var shPid = '"$sh_pid"';
    var mhPid = '"${mh_pid:-0}"';
    var wins = ObjC.unwrap($.CGWindowListCopyWindowInfo($.kCGWindowListOptionOnScreenOnly, 0));
    var hasWin = false;
    if (wins) {
      for (var w = 0; w < wins.length; w++) {
        var win = ObjC.unwrap(wins[w]);
        if (ObjC.unwrap(win.kCGWindowOwnerPID) === shPid && ObjC.unwrap(win.kCGWindowLayer) === 0) {
          hasWin = true;
          break;
        }
      }
    }
    if (hasWin && mhPid > 0) {
      var mhApp = $.NSRunningApplication.runningApplicationWithProcessIdentifier(mhPid);
      if (mhApp && !mhApp.isNil()) {
        mhApp.hide();
      }
    }
    var app = $.NSRunningApplication.runningApplicationWithProcessIdentifier(shPid);
    if (app && !app.isNil()) {
      app.activateWithOptions(3);
      if (hasWin && !app.isActive()) {
        var cp = {x: 756, y: 491};
        var down = $.CGEventCreateMouseEvent(null, $.kCGEventLeftMouseDown, cp, 0);
        var up = $.CGEventCreateMouseEvent(null, $.kCGEventLeftMouseUp, cp, 0);
        $.CGEventPost($.kCGHIDEventTap, down);
        $.CGEventPost($.kCGHIDEventTap, up);
      }
    }
    var p1 = {x: 756 + ('"$i"' % 2), y: 491};
    $.CGWarpMouseCursorPosition(p1);
    var e = $.CGEventCreateMouseEvent(null, $.kCGEventMouseMoved, p1, 0);
    $.CGEventPost($.kCGHIDEventTap, e);
  ' >/dev/null 2>&1
done
