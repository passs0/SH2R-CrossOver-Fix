<h1 align="center">SH2R-CrossOver-Fix</h1>

<p align="center">
  <strong>Launch, Window Auto-Focus, Cursor Hide & Frame-Pacing Fix for <em>Silent Hill 2 Remake (GOG)</em> on CrossOver macOS (Apple Silicon)</strong>
</p>

---

> [!NOTE]
> **AI-Generated Tool Disclosure**
> **SH2R-CrossOver-Fix** is an AI-generated configuration and launcher patcher created with **Antigravity** (Google DeepMind) to resolve macOS `WindowServer` focus race conditions, stuck mouse cursors, and Unreal Engine 5 D3D11/DXMT frame-pacing issues when running the GOG version of *Silent Hill 2 Remake* (`SHProto-Win64-Shipping.exe`) in CodeWeavers CrossOver.

---

## 🔍 What Problems Does This Solve?

### 1. Game Launches in the Background & Never Comes to the Front
When launching *Silent Hill 2 Remake* from CrossOver or its macOS `.app` shortcut (`Silent Hill 2.app`), two problems occur simultaneously:
- **macOS `WindowServer` Early Focus Rejection:** `SHProto-Win64-Shipping.exe` calls `SetFrontProcessWithInfo` ~1.7 seconds after spawning—**before** its D3D11 window exists (~3.1 seconds after launch). macOS `WindowServer` logs:
  ```text
  WindowServer: [SetFrontProcessWithInfo]: CPS: The requested process presents 0 windows, is not a UI element and is frontable. Denying the request.
  ```
- **CrossOver `Menu Helper` Holds Foreground Focus & Ignores `.lnk` Wrappers:** CrossOver's `Menu Helper` (`Silent Hill 2.app`) becomes the frontmost process with 0 windows and executes `cxmenu --start`. When an entry in `cxmenu.conf` has `"Type" = "Windows"`, `cxmenu --start` calls `wine --start` directly and **completely bypasses** custom `.lnk` shell wrappers in `desktopdata/cxmenu/`. Furthermore, because `Menu Helper` is signed with Hardened Runtime without the `com.apple.security.automation.apple-events` entitlement, child processes inherit its TCC identity.

**How `SH2R-CrossOver-Fix` solves it:**
- Configures `cxmenu.conf` with `"Type" = "raw"` and runs CrossOver's native `cxmenu --install` to register the launch command in `cxmenu_macosx.plist`, then locks `"MenuMode" = "frozen"` in `cxbottle.conf`.
- Installs `focus_and_hide_cursor.sh`, which polls `CGWindowListCopyWindowInfo` until `SHProto-Win64-Shipping.exe` has created its layer-0 on-screen window, hides `Menu Helper` (`NSRunningApplication.hide()`) so it yields foreground focus, activates the game window, and warps/moves the cursor to trigger UE5 cursor hiding.

### 2. D3D12 Lighting Bugs, Cutscene Freezes & Stutter on 16 GB Apple Silicon Macs
- **D3D11 (`-dx11`) + DXMT:** Running *Silent Hill 2 Remake* with `-dx11 SAVEWINPOS=1` on **DXMT** avoids Unreal Engine 5's D3D12 Lumen/Nanite pipeline state object (PSO) compilation stalls and indoor lighting glitches on 16 GB Unified Memory Macs while preserving full **High** graphics quality.
- **Shader Cache Preservation:** Modifies only `FpsCap=Fps60` and `FrameRateLimit=60.000000` in `GameUserSettings.ini` (preserving Windows `CRLF` line endings) without altering scalability group CVars that would force Unreal Engine 5 to recompile shaders mid-level.
- **In-Game Video Cutscenes (`winegstreamer`):** For FMV cutscenes that freeze due to stock CrossOver missing `libgstlibav.dylib` (FFmpeg), pair this fix with **[HexAid](https://github.com/passs0/HexAid)** to upgrade CrossOver's `GStreamer.framework` and `DXMT` in place.

---

## 🚀 Installation

```zsh
git clone https://github.com/passs0/SH2R-CrossOver-Fix.git
cd SH2R-CrossOver-Fix
chmod +x install.sh
./install.sh
```

`install.sh` automatically locates your CrossOver bottle containing `drive_c/GOG Games/Silent Hill 2/SHProto/Binaries/Win64/SHProto-Win64-Shipping.exe` (or you can pass a bottle name explicitly: `./install.sh "GOG Galaxy"`).

---

## 📁 Repository Structure

- [`install.sh`](install.sh) — One-step installer that configures `cxmenu.conf`, updates `cxmenu_macosx.plist` via CrossOver's native `cxmenu --install`, updates `.lnk` wrappers, applies the 60 FPS frame-pacing cap, and cleans temporary/crash logs.
- [`scripts/focus_and_hide_cursor.sh`](scripts/focus_and_hide_cursor.sh) — Background helper that waits for the `SHProto-Win64-Shipping.exe` window, hides `Menu Helper`, brings the game to the front, and hides the macOS cursor.

---

## 📄 License

Released under the [MIT License](LICENSE).
