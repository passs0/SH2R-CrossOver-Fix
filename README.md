<h1 align="center">SH2R-CrossOver-Fix</h1>

<p align="center">
  <strong>Launch, Window Auto-Focus, Cursor Hide & Frame-Pacing Fix for <em>Silent Hill 2 Remake (GOG)</em> on CrossOver macOS (Apple Silicon)</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/macOS-Apple%20Silicon-black?logo=apple" alt="macOS" />
  <img src="https://img.shields.io/badge/target-CrossOver%20%7C%20Silent%20Hill%202%20Remake-007AFF" alt="Target" />
  <img src="https://img.shields.io/badge/framework-Cocoa%20%7C%20Shell-blue" alt="Frameworks" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" /></a>
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

### 2. Low Framerate (~20 FPS Lock) & Unreal Engine 5 Benchmark Overwrites
On Apple Silicon Macs (such as M2 Pro / M3), two compounding issues can trap the game at an unplayable ~20 FPS:
- **Double-Buffered VSync Frame Drop:** When VSync is enabled under Wine/DXMT, a missed 33.3ms (30 FPS) frame deadline on a 60Hz/120Hz display causes macOS presentation to instantly quantize down to the next integer divisor: `60 / 3 = 20 FPS`.
- **UE5 Startup Benchmark Overwrite:** Because Unreal Engine 5 cannot recognize the virtualized GPU vendor under Wine, its startup hardware benchmark frequently defaults or resets `GameUserSettings.ini` back to **Epic** preset (`sg.*=3`) with **100% native resolution** (`sg.ResolutionQuality=100`). At native 1800p with Epic Lumen and heavy volumetric fog, the GPU cannot maintain 30 FPS.

**How `SH2R-CrossOver-Fix` solves it:**
- Enforces `"CX_GRAPHICS_BACKEND" = "d3dmetal"` in `cxbottle.conf` to utilize Apple's official Game Porting Toolkit (GPTK) Metal translation layer.
- Locks `GameUserSettings.ini` to read-only (`chmod 444`) with **Medium/Low preset** and **Low Shadows** (`sg.ShadowQuality=0`), preventing UE5's startup benchmark from resetting to unplayable Epic 100% settings.
- Targets a console-style stable **30 FPS cap with VSync enabled**: because the M2 Pro GPU never dips below the 33.3ms threshold on Medium/Low, VSync locks smoothly to 30 FPS without tearing and without dropping to 20 FPS.
- Injects clean post-processing and memory-capping overrides into `Engine.ini`:
  - `r.VSync=1` — Synchronizes presentation with zero screen tearing.
  - `r.Streaming.PoolSize=3072` & `r.Streaming.LimitPoolSizeToVRAM=1` — Caps texture streaming memory strictly to 3 GB, preventing runaway RAM exhaustion and macOS SSD swap thrashing that causes framerates to collapse into single digits over time.
  - `r.SceneColorFringe.Max=0` & `r.SceneColorFringeQuality=0` — Completely disables chromatic aberration color-channel separation (fixing unblurred red, green, and blue fringing artifacts).
  - `r.VolumetricFog.GridPixelSizeFactor=16` — Halves volumetric fog shader overhead in outdoor town sections.
  - `r.DepthOfFieldQuality=0` & `r.motionblurquality=0` — Eliminates heavy blur passes that bottleneck the GPU.
  - `r.FilmGrain=0` — Cleans up noisy image artifacts.

### 3. D3D12 Lighting Bugs, Cutscene Freezes & Stutter on 16 GB Apple Silicon Macs
- **D3D11 (`-dx11`) + DXMT:** Running *Silent Hill 2 Remake* with `-dx11 SAVEWINPOS=1` on **DXMT** avoids Unreal Engine 5's D3D12 Lumen/Nanite pipeline state object (PSO) compilation stalls and indoor lighting glitches on 16 GB Unified Memory Macs.
- **In-Game Video Cutscenes (`winegstreamer`):** For FMV cutscenes that freeze due to stock CrossOver missing `libgstlibav.dylib` (FFmpeg), pair this fix with **[HexAid](https://github.com/passs0/HexAid)** to upgrade CrossOver's `GStreamer.framework` and `DXMT` in place.

### 4. Persistent "Select a Profile" Prompt on Standalone/Offline Launches
When launching the GOG version directly through CrossOver shortcuts without the GOG Galaxy client running in the background, Unreal Engine fails its online identity handshake (which defaults to checking Steam/Galaxy). This causes the game to pause at the start screen on **every single boot** prompting you to "Select a Profile" before it will load your saves.
- **How it's resolved:** `install.sh` adds `DefaultPlatformService=Null` and `bAutoLogin=true` under `[OnlineSubsystem]` in your bottle's `Engine.ini`. This bypasses online storefront handshakes, auto-authenticates the local player profile, and loads your transferred save games immediately.

---

## 🛠️ Troubleshooting & Known Edge Cases

### "The command ... returned 5" / Immediate Crash on Launch (`0xc0000005`)

If the game crashes instantly upon launch with return code `5`:

1. **Rosetta AVX Advertisement:** Unreal Engine 5 requires AVX instructions. `install.sh` automatically adds `"ROSETTA_ADVERTISE_AVX" = "1"` under `[EnvironmentVariables]` in your bottle's `cxbottle.conf`.
2. **Apple GPTK Version Mismatch:** If you manually upgrade CrossOver's Apple Game Porting Toolkit (GPTK) binaries in `CrossOver.app/Contents/SharedSupport/CrossOver/lib64/apple_gptk/`:
   - Updating `external/D3DMetal.framework` and `external/libd3dshared.dylib` **requires** also updating the companion Wine bridge DLLs in `apple_gptk/wine/x86_64-windows/` (`d3d11.dll`, `d3d12.dll`, `dxgi.dll`, etc.) from the **exact same** GPTK release DMG (`redist/lib/wine/x86_64-windows/`).
   - Mismatched versions will shift the internal `_gGFXTDispatch` table offset, causing `d3d11.dll` to jump into an invalid function pointer and crash with `EXCEPTION_ACCESS_VIOLATION` (`0xc0000005`) during `DllMain`.

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

- [`install.sh`](install.sh) — One-step installer that compiles `src/sh2_focus.m`, configures `cxmenu.conf`, updates `cxmenu_macosx.plist` via CrossOver's native `cxmenu --install`, updates `.lnk` wrappers, applies the 60 FPS frame-pacing cap, and cleans temporary/crash logs.
- [`src/sh2_focus.m`](src/sh2_focus.m) — Native compiled Cocoa/Carbon helper that monitors for the game's layer-0 window, hides `CrossOver.app` and `Menu Helper`, brings the game process to the foreground, activates it via window click, and hides the macOS cursor.
- [`scripts/focus_and_hide_cursor.sh`](scripts/focus_and_hide_cursor.sh) — Shell wrapper that invokes the native `sh2_focus` binary (or falls back to AppleScript).
- [`scripts/sh2_cheat.py`](scripts/sh2_cheat.py) — Standalone offline save modifier CLI to view game stats and toggle infinite ammo, healing items, NG+ Chainsaw, and difficulty options.

---

## 🧰 Optional Companion Tool: Offline Save Modifier (Cheats)

Windows memory trainers (*Cheat Engine*, *FLiNG*, *WeMod*) often fail, crash, or freeze under Wine/CrossOver due to restricted macOS debugging entitlements and DXMT/Metal memory conflicts.

Included in [`scripts/sh2_cheat.py`](scripts/sh2_cheat.py) is a **standalone, zero-dependency offline save modifier** written in pure Python 3. It directly parses Unreal Engine 5's compressed `VASb` / `YDBx` GVAS save container and repacks it cleanly while preserving exact byte alignment and generating automatic timestamped backups.

### Features
- 🔫 **Infinite Ammo**: Sets Handgun, Shotgun, and Hunting Rifle ammo to 9,999.
- ❤️ **Infinite Healing**: Sets Health Drinks and Syringes to 999.
- 🪚 **NG+ Chainsaw Early Access**: Safely swaps the Iron Pipe for the Chainsaw in inventory.
- ⚔️ **Pyramid Head Control**: Toggle Pyramid Head between normal aggressive mode and pacified ignore mode.
- 🛡️ **Automatic Safety Backups**: Creates `.sav.bak_<timestamp>` before making changes; one-command rollback with `--restore`.

### Usage

```zsh
# View current save file stats and inventory
python3 scripts/sh2_cheat.py --status

# Interactive menu to toggle individual cheats
python3 scripts/sh2_cheat.py

# Instant one-click apply to latest save
python3 scripts/sh2_cheat.py --apply

# Restore previous backup
python3 scripts/sh2_cheat.py --restore
```

---

## 📄 License

Released under the [MIT License](LICENSE).
