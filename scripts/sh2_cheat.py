#!/usr/bin/env python3
"""
Silent Hill 2 Remake - Save Cheat CLI
A clean, one-time offline save modifier to toggle cheats on or off.
"""

import sys
import os
import glob
import struct
import zlib
import shutil
import argparse
from datetime import datetime

def find_save_dir():
    """Smart detection of save directory across CrossOver bottles and native OS."""
    if "SH2_SAVE_DIR" in os.environ and os.path.isdir(os.environ["SH2_SAVE_DIR"]):
        return os.environ["SH2_SAVE_DIR"]

    # Check any CrossOver bottle
    crossover_pattern = os.path.expanduser(
        "~/Library/Application Support/CrossOver/Bottles/*/drive_c/users/*/AppData/Local/SilentHill2/Saved/SaveGames*"
    )
    matches = [p for p in glob.glob(crossover_pattern) if os.path.isdir(p)]
    if matches:
        return max(matches, key=lambda d: os.path.getmtime(d))

    # Windows / Wine %LOCALAPPDATA%
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        win_path = os.path.join(local_app_data, "SilentHill2", "Saved", "SaveGames")
        if os.path.isdir(win_path):
            return win_path

    return os.path.expanduser(
        "~/Library/Application Support/CrossOver/Bottles/GOG Galaxy/drive_c/users/crossover/AppData/Local/SilentHill2/Saved/SaveGames"
    )

DEFAULT_SAVE_DIR = find_save_dir()

PROPERTY_HEADER = b"Quantity\x00\x0c\x00\x00\x00IntProperty\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00"
HEALTH_HEADER = b"HealthValue\x00\x0e\x00\x00\x00FloatProperty\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00"

def get_latest_save(save_dir=DEFAULT_SAVE_DIR):
    if not os.path.isdir(save_dir):
        return None
    saves = [
        f for f in glob.glob(os.path.join(save_dir, "SaveGameData_*.sav"))
        if not f.endswith(".bak") and ".bak" not in f
    ]
    if not saves:
        return None
    return max(saves, key=os.path.getmtime)

def read_decompressed(save_path):
    with open(save_path, "rb") as f:
        raw_data = f.read()

    ydbx_idx = raw_data.find(b"YDBx")
    if ydbx_idx == -1:
        raise ValueError("Invalid save format: Missing YDBx container.")

    comp_len = struct.unpack("<I", raw_data[ydbx_idx+4:ydbx_idx+8])[0]
    uncomp_len = struct.unpack("<I", raw_data[ydbx_idx+8:ydbx_idx+12])[0]
    zlib_start = ydbx_idx + 12

    decomp = bytearray(zlib.decompress(raw_data[zlib_start:zlib_start+comp_len]))
    if len(decomp) != uncomp_len:
        raise ValueError("Decompression length mismatch.")

    return raw_data, ydbx_idx, decomp

def write_repacked(save_path, raw_data, ydbx_idx, decomp):
    # Create safety backup
    bak_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{save_path}.bak_{bak_time}"
    shutil.copy2(save_path, backup_path)

    new_comp = zlib.compress(bytes(decomp), level=zlib.Z_DEFAULT_COMPRESSION)
    header = raw_data[:ydbx_idx+4]
    repacked = (
        header +
        struct.pack("<I", len(new_comp)) +
        struct.pack("<I", len(decomp)) +
        new_comp
    )

    with open(save_path, "wb") as f:
        f.write(repacked)

    return backup_path

def set_player_health(decomp, new_hp=100.0):
    hp_pos = decomp.find(HEALTH_HEADER)
    if hp_pos != -1:
        val_pos = hp_pos + len(HEALTH_HEADER)
        decomp[val_pos:val_pos+4] = struct.pack("<f", float(new_hp))
        return True
    return False

def get_player_health(decomp):
    hp_pos = decomp.find(HEALTH_HEADER)
    if hp_pos != -1:
        val_pos = hp_pos + len(HEALTH_HEADER)
        return struct.unpack("<f", decomp[val_pos:val_pos+4])[0]
    return None

def get_item_quantity(decomp, item_name):
    target = item_name.encode("ascii")
    pos = 0
    while True:
        pos = decomp.find(target, pos)
        if pos == -1:
            return None
        window = decomp[pos:pos+150]
        q_off = window.find(PROPERTY_HEADER)
        if q_off != -1:
            val_pos = pos + q_off + len(PROPERTY_HEADER)
            return struct.unpack("<I", decomp[val_pos:val_pos+4])[0]
        pos += len(target)

def set_item_quantity(decomp, item_name, new_qty):
    target = item_name.encode("ascii")
    pos = 0
    updated = False
    old_val = None
    while True:
        pos = decomp.find(target, pos)
        if pos == -1:
            break
        window = decomp[pos:pos+150]
        q_off = window.find(PROPERTY_HEADER)
        if q_off != -1:
            val_pos = pos + q_off + len(PROPERTY_HEADER)
            old_val = struct.unpack("<I", decomp[val_pos:val_pos+4])[0]
            decomp[val_pos:val_pos+4] = struct.pack("<I", new_qty)
            updated = True
            break
        pos += len(target)
    return updated, old_val

def get_weapon_status(decomp):
    pipe = b"\t\x00\x00\x00IronPipe\x00"
    saw = b"\t\x00\x00\x00Chainsaw\x00"
    if saw in decomp:
        return "Chainsaw"
    elif pipe in decomp:
        return "Iron Pipe"
    return "Unknown"

def set_weapon(decomp, to_chainsaw=True):
    pipe = b"\t\x00\x00\x00IronPipe\x00"
    saw = b"\t\x00\x00\x00Chainsaw\x00"
    
    from_pat = pipe if to_chainsaw else saw
    to_pat = saw if to_chainsaw else pipe

    if from_pat in decomp:
        pos = 0
        while True:
            pos = decomp.find(from_pat, pos)
            if pos == -1:
                break
            decomp[pos:pos+len(from_pat)] = to_pat
            pos += len(to_pat)
        return True
    return False

def get_pyramid_head_status(decomp):
    import re
    for m in re.finditer(b"PyramidHead_Sword_AI_C", decomp):
        pos = m.start()
        ign_pos = decomp.find(b"_IgnoreAll\x00\r\x00\x00\x00BoolProperty", pos)
        if ign_pos != -1 and (ign_pos - pos) < 500:
            val_off = ign_pos + len(b"_IgnoreAll\x00\r\x00\x00\x00BoolProperty\x00\x00\x00\x00\x00\x00\x00\x00\x00")
            return "Pacified (Ignoring)" if decomp[val_off] == 1 else "Active & Hostile"
    return "Not in current area"

def set_pyramid_head_pacify(decomp, pacify=False):
    import re
    val = 1 if pacify else 0
    count = 0
    for m in re.finditer(b"PyramidHead_Sword_AI_C", decomp):
        pos = m.start()
        ign_pos = decomp.find(b"_IgnoreAll\x00\r\x00\x00\x00BoolProperty", pos)
        if ign_pos != -1 and (ign_pos - pos) < 500:
            val_off = ign_pos + len(b"_IgnoreAll\x00\r\x00\x00\x00BoolProperty\x00\x00\x00\x00\x00\x00\x00\x00\x00")
            decomp[val_off] = val
            count += 1
    return count

def restore_latest_backup(save_dir=DEFAULT_SAVE_DIR):
    saves = glob.glob(os.path.join(save_dir, "SaveGameData_*.sav.bak_*"))
    if not saves:
        print("❌ No backup files found to restore.")
        return False
    latest_bak = max(saves, key=os.path.getmtime)
    base_name = latest_bak.split(".bak_")[0]
    shutil.copy2(latest_bak, base_name)
    print(f"🛡️  Restored {os.path.basename(base_name)} from {os.path.basename(latest_bak)}")
    return True

def apply_cheats(save_path, ammo=True, health=True, chainsaw=True, pacify_ph=False):
    raw_data, ydbx_idx, decomp = read_decompressed(save_path)
    fname = os.path.basename(save_path)
    print(f"\n📂 Applying to: {fname}")
    print("-" * 50)

    # Ammo
    if ammo:
        for item in ["HandgunAmmo", "ShotgunAmmo", "RifleAmmo"]:
            set_item_quantity(decomp, item, 9999)
        print("  🔫  Ammo (Handgun, Shotgun, Rifle) : 9,999 [ON]")
    else:
        print("  🔫  Ammo                          : Unchanged [OFF]")

    # Health Items & Restoration
    if health:
        set_player_health(decomp, 100.0)
        for item in ["HealthDrink", "Syringe"]:
            set_item_quantity(decomp, item, 999)
        print("  ❤️  Health (HP & 999 Healing Items): 100% Full + 999 Drinks/Syringes [ON]")
    else:
        print("  ❤️  Health Items                   : Unchanged [OFF]")

    # Chainsaw
    if chainsaw:
        set_weapon(decomp, to_chainsaw=True)
        print("  🪚  Melee Weapon                   : NG+ Chainsaw [ON]")
    else:
        set_weapon(decomp, to_chainsaw=False)
        print("  🦯  Melee Weapon                   : Iron Pipe [RESTORED]")

    # Pyramid Head
    set_pyramid_head_pacify(decomp, pacify=pacify_ph)
    if pacify_ph:
        print("  ⚔️  Pyramid Head                   : Pacified (Ignore Mode) [ON]")
    else:
        print("  ⚔️  Pyramid Head                   : Active & Hostile [NORMAL]")

    print("-" * 50)
    bak = write_repacked(save_path, raw_data, ydbx_idx, decomp)
    print(f"🛡️  Backup created: {os.path.basename(bak)}")
    print(f"✅ {fname} updated successfully! Ready to load.")

def print_status(save_path):
    raw_data, ydbx_idx, decomp = read_decompressed(save_path)
    fname = os.path.basename(save_path)
    mtime = datetime.fromtimestamp(os.path.getmtime(save_path)).strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n📂 Target Save: {fname} (Modified: {mtime})")
    print("-" * 50)
    hp = get_player_health(decomp)
    hg = get_item_quantity(decomp, "HandgunAmmo") or 0
    sg = get_item_quantity(decomp, "ShotgunAmmo") or 0
    rf = get_item_quantity(decomp, "RifleAmmo") or 0
    hd = get_item_quantity(decomp, "HealthDrink") or 0
    syr = get_item_quantity(decomp, "Syringe") or 0
    wpn = get_weapon_status(decomp)
    ph = get_pyramid_head_status(decomp)

    hp_str = f"{hp:.0f} / 100" if hp is not None else "Unknown"
    print(f"  ❤️  Player Health   : {hp_str}")
    print(f"  ❤️  Health Drinks   : {hd}")
    print(f"  ❤️  Syringes        : {syr}")
    print(f"  🔫  Handgun Ammo    : {hg}")
    print(f"  🔫  Shotgun Ammo    : {sg}")
    print(f"  🔫  Rifle Ammo      : {rf}")
    print(f"  🪚  Melee Weapon    : {wpn}")
    print(f"  ⚔️  Pyramid Head    : {ph}")
    print("-" * 50)

def interactive_cli(save_path):
    opt_ammo = True
    opt_health = True
    opt_chainsaw = True
    opt_pacify = False

    while True:
        print("\n" + "=" * 52)
        print("   🎮 SILENT HILL 2 REMAKE — SAVE CHEAT TOOL")
        print("=" * 52)
        print_status(save_path)

        print("TOGGLE CHEATS:")
        print(f"  [1] Infinite Ammo (9,999)     : [{'ON' if opt_ammo else 'OFF'}]")
        print(f"  [2] Infinite Health Items (999): [{'ON' if opt_health else 'OFF'}]")
        print(f"  [3] NG+ Chainsaw Weapon       : [{'ON' if opt_chainsaw else 'OFF'}]")
        print(f"  [4] Pacify Pyramid Head       : [{'ON' if opt_pacify else 'OFF'}]")
        print("\nACTIONS:")
        print("  [A] Apply to Save (Press Enter)")
        print("  [R] Restore Latest Backup")
        print("  [Q] Quit")
        print("-" * 52)

        try:
            choice = input("Select an option [A]: ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

        if choice in ("", "A"):
            apply_cheats(save_path, ammo=opt_ammo, health=opt_health, chainsaw=opt_chainsaw, pacify_ph=opt_pacify)
            break
        elif choice == "1":
            opt_ammo = not opt_ammo
        elif choice == "2":
            opt_health = not opt_health
        elif choice == "3":
            opt_chainsaw = not opt_chainsaw
        elif choice == "4":
            opt_pacify = not opt_pacify
        elif choice == "R":
            restore_latest_backup()
            break
        elif choice == "Q":
            print("Exited without making changes.")
            break

def main():
    parser = argparse.ArgumentParser(description="Silent Hill 2 Save Cheat CLI")
    parser.add_argument("--save", "-s", help="Target specific .sav file")
    parser.add_argument("--dir", "-d", default=DEFAULT_SAVE_DIR, help="Save directory")
    parser.add_argument("--apply", "-a", action="store_true", help="Apply cheats immediately and exit")
    parser.add_argument("--status", action="store_true", help="Print save status and exit")
    parser.add_argument("--restore", "-r", action="store_true", help="Restore latest backup and exit")
    parser.add_argument("--no-ammo", action="store_true", help="Do not touch ammo")
    parser.add_argument("--no-health", action="store_true", help="Do not touch health items")
    parser.add_argument("--no-chainsaw", action="store_true", help="Revert to Iron Pipe")
    parser.add_argument("--pacify-ph", action="store_true", help="Pacify Pyramid Head")

    args = parser.parse_args()

    save_path = args.save if args.save else get_latest_save(args.dir)
    if not save_path:
        print("❌ No save file found.")
        sys.exit(1)

    if args.restore:
        restore_latest_backup(args.dir)
    elif args.status:
        print_status(save_path)
    elif args.apply or args.no_ammo or args.no_health or args.no_chainsaw or args.pacify_ph:
        apply_cheats(
            save_path,
            ammo=not args.no_ammo,
            health=not args.no_health,
            chainsaw=not args.no_chainsaw,
            pacify_ph=args.pacify_ph
        )
    else:
        interactive_cli(save_path)

if __name__ == "__main__":
    main()
