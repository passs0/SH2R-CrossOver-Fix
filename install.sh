#!/bin/zsh
set -euo pipefail

BOTTLES_DIR="$HOME/Library/Application Support/CrossOver/Bottles"
CX_BIN="/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin"

echo "========================================================"
echo "  SH2R-CrossOver-Fix — Silent Hill 2 Remake (GOG) Fix"
echo "========================================================"

if [[ ! -d "$CX_BIN" ]]; then
  echo "❌ Error: CrossOver.app not found at /Applications/CrossOver.app"
  exit 1
fi

# Auto-detect the bottle containing Silent Hill 2 Remake
TARGET_BOTTLE=""
SH2_EXE_REL="drive_c/GOG Games/Silent Hill 2/SHProto/Binaries/Win64/SHProto-Win64-Shipping.exe"

if [[ $# -ge 1 ]]; then
  TARGET_BOTTLE="$BOTTLES_DIR/$1"
else
  for b in "$BOTTLES_DIR"/*(/N); do
    if [[ -f "$b/$SH2_EXE_REL" ]]; then
      TARGET_BOTTLE="$b"
      break
    fi
  done
fi

if [[ -z "$TARGET_BOTTLE" || ! -f "$TARGET_BOTTLE/$SH2_EXE_REL" ]]; then
  echo "❌ Error: Could not locate Silent Hill 2 (GOG) in any CrossOver bottle."
  echo "Usage: ./install.sh \"<Bottle Name>\""
  exit 1
fi

BOTTLE_NAME="$(basename "$TARGET_BOTTLE")"
SH2_WIN64_DIR="$TARGET_BOTTLE/drive_c/GOG Games/Silent Hill 2/SHProto/Binaries/Win64"
SH2_EXE="$SH2_WIN64_DIR/SHProto-Win64-Shipping.exe"

echo "✅ Found Silent Hill 2 Remake in bottle: $BOTTLE_NAME"

# 1. Build and install sh2_focus helper & ensure ROSETTA_ADVERTISE_AVX=1 in cxbottle.conf
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if command -v clang >/dev/null 2>&1; then
  clang -O2 -framework Cocoa -framework Carbon -Wno-deprecated-declarations \
    "$SCRIPT_DIR/src/sh2_focus.m" -o "$TARGET_BOTTLE/sh2_focus"
  chmod +x "$TARGET_BOTTLE/sh2_focus"
fi
cp "$SCRIPT_DIR/scripts/focus_and_hide_cursor.sh" "$TARGET_BOTTLE/focus_and_hide_cursor.sh"
chmod +x "$TARGET_BOTTLE/focus_and_hide_cursor.sh"
if [[ -f "$TARGET_BOTTLE/cxbottle.conf" ]] && ! grep -q '"ROSETTA_ADVERTISE_AVX"' "$TARGET_BOTTLE/cxbottle.conf"; then
  sed -i '' 's/\[EnvironmentVariables\]/[EnvironmentVariables]\
"ROSETTA_ADVERTISE_AVX" = "1"/' "$TARGET_BOTTLE/cxbottle.conf"
fi
echo "✅ Installed native sh2_focus helper, focus_and_hide_cursor.sh, and verified ROSETTA_ADVERTISE_AVX=1"

# 2. Configure cxmenu.conf with Type = raw and -dx11 SAVEWINPOS=1
ICON_PATH=$(find "$TARGET_BOTTLE/windata/cxmenu/icons/hicolor/256x256" -name "*goggame-2051029707*.png" 2>/dev/null | head -n 1)
[[ -z "$ICON_PATH" ]] && ICON_PATH="2BF3_goggame-2051029707.0"

RAW_CMD="sh -c 'sh \\\"$TARGET_BOTTLE/focus_and_hide_cursor.sh\\\" & cd \\\"$SH2_WIN64_DIR\\\" && exec \\\"$CX_BIN/wine\\\" --bottle \\\"$BOTTLE_NAME\\\" --check --wait-children \\\"$SH2_EXE\\\" SHProto -dx11 SAVEWINPOS=1'"

cat > "$TARGET_BOTTLE/cxmenu.conf" <<EOF
[StartMenu.C^3A_ProgramData_Microsoft_Windows_Start+Menu/Programs/Silent Hill 2 [GOG.com]/Silent Hill 2.lnk]
"Type" = "raw"
"Command" = "$RAW_CMD"
"Icon" = "$ICON_PATH"
"Mode" = "install"
"StartupWMClass" = "shproto.exe"

[StartMenu.C^3A_ProgramData_Microsoft_Windows_Start+Menu/Programs/Silent Hill 2 [GOG.com]/Uninstall Silent Hill 2.lnk]
"Type" = "Windows"
"Icon" = "E62F_unins000.0"
"Mode" = "install"
"StartupWMClass" = "unins000.exe"

[Desktop.C^3A_users_Public_Desktop/Silent Hill 2.lnk]
"Type" = "raw"
"Command" = "$RAW_CMD"
"Icon" = "$ICON_PATH"
"Mode" = "install"
"StartupWMClass" = "shproto.exe"
EOF

# 3. Temporarily allow cxmenu --install to write native cxmenu_macosx.plist, then freeze MenuMode
if [[ -f "$TARGET_BOTTLE/cxbottle.conf" ]]; then
  sed -i '' 's/"MenuMode" = "frozen"/"MenuMode" = "install"/g' "$TARGET_BOTTLE/cxbottle.conf"
fi

"$CX_BIN/cxmenu" --bottle "$BOTTLE_NAME" --install >/dev/null 2>&1 || true

if [[ -f "$TARGET_BOTTLE/cxbottle.conf" ]]; then
  sed -i '' 's/"MenuMode" = "install"/"MenuMode" = "frozen"/g' "$TARGET_BOTTLE/cxbottle.conf"
fi

# 4. Update .lnk wrapper scripts in desktopdata/cxmenu
for lnk in \
  "$TARGET_BOTTLE/desktopdata/cxmenu/StartMenu.C^5E3A_ProgramData_Microsoft_Windows_Start^2BMenu/Programs/Silent+Hill+2+[GOG.com]/Silent+Hill+2.lnk" \
  "$TARGET_BOTTLE/desktopdata/cxmenu/Desktop.C^5E3A_users_Public_Desktop/Silent+Hill+2.lnk"; do
  if [[ -f "$lnk" ]]; then
    cat > "$lnk" <<EOF
#!/bin/sh
sh "$TARGET_BOTTLE/focus_and_hide_cursor.sh" >/dev/null 2>&1 &
cd "$SH2_WIN64_DIR" && exec "$CX_BIN/wine" --bottle "$BOTTLE_NAME" --check --wait-children "$SH2_EXE" SHProto -dx11 SAVEWINPOS=1 "\$@"
EOF
    chmod +x "$lnk"
  fi
done
echo "✅ Configured CrossOver launcher shortcuts (-dx11 + Auto-Focus + Cursor Hide)"

# 5. Apply 60 FPS cap in GameUserSettings.ini while preserving CRLF and existing shader settings
GUS_INI="$TARGET_BOTTLE/drive_c/users/crossover/AppData/Local/SilentHill2/Saved/Config/Windows/GameUserSettings.ini"
if [[ -f "$GUS_INI" ]]; then
  python3 -c '
import sys
p = sys.argv[1]
with open(p, "rb") as f:
    data = f.read().decode("utf-8", errors="ignore")
data = data.replace("FpsCap=Fps30", "FpsCap=Fps60").replace("FpsCap=Unlimited", "FpsCap=Fps60")
data = data.replace("FrameRateLimit=30.000000", "FrameRateLimit=60.000000").replace("FrameRateLimit=0.000000", "FrameRateLimit=60.000000")
with open(p, "wb") as f:
    f.write(data.encode("utf-8"))
' "$GUS_INI"
  echo "✅ Applied 60 FPS frame pacing cap in GameUserSettings.ini (existing shader cache preserved)"
fi

# 6. Clean unneeded crash/temp logs in the bottle
setopt NULL_GLOB
rm -rf "$TARGET_BOTTLE/drive_c/users/crossover/AppData/Local/SilentHill2/Saved/Logs" \
       "$TARGET_BOTTLE/drive_c/users/crossover/AppData/Local/SilentHill2/Saved/Config/CrashReportClient" \
       "$TARGET_BOTTLE/drive_c/users/crossover/AppData/Local/Temp/"* 2>/dev/null || true
echo "✅ Cleaned temporary and log files"
echo ""
echo "🎉 Done! Launch Silent Hill 2 from CrossOver or Applications."
