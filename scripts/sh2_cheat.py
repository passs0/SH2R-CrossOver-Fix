#!/usr/bin/env python3
"""
Silent Hill 2 Remake - Save Cheat & Item Injector CLI
A clean, modular offline save modifier to inspect, toggle cheats, and inject any
memo, glimpse of the past, ending item, weapon, or arbitrary game item.
Includes Progression Protection Guard to prevent level streaming crashes.
"""

import sys
import os
import glob
import struct
import zlib
import shutil
import argparse
import re
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

# Progression Stages
PROG_STAGES = [
    (0, "Prologue", ["RtSH_"]),
    (1, "East South Vale", ["EcFW_"]),
    (2, "Wood Side Apartments", ["WsaFW_"]),
    (3, "Blue Creek Apartments", ["BcaOW_"]),
    (4, "West South Vale", ["WcFW_", "End_Bliss_"]),
    (5, "Brookhaven Hospital", ["HosFW_", "A_HospitalFW"]),
    (6, "Hospital Otherworld", ["HosOW_", "HospitalOW"]),
    (7, "South Vale Otherworld", ["EcOW_"]),
    (8, "Historical Society", ["Hist_"]),
    (9, "Toluca Prison", ["PriOW_"]),
    (10, "The Labyrinth", ["LhFW_", "LabyrinthOW"]),
    (11, "Toluca Lake", ["Lake_"]),
    (12, "Lakeview Hotel", ["LhOW_", "HotelOW", "HotelFW"]),
]

ALL_GLIMPSES = [
    ("cb79a1a402597b48bf9f447532e175d0", "Glimpse #01 - Observation Deck Path"),
    ("2e3b6ffad031c34fa9e28022b74b5881", "Glimpse #02 - Silent Hill Entrance Trail"),
    ("876ee3c6fa5df1438786be750c84fce9", "Glimpse #03 - East South Vale Cemetery"),
    ("9dbcf3152db409419645721c0c487e21", "Glimpse #04 - Martin Street Alleyway"),
    ("348b1421262ee145bfbc51c834e41084", "Glimpse #05 - Katz Street Roadblock"),
    ("5d673b2f089c594393ecb1d3899c57a1", "Glimpse #06 - Wood Side Apartments Garbage Chute"),
    ("68e1b0e451972e4798e5e376ade911e2", "Glimpse #07 - Wood Side Apartments Room 213"),
    ("32d003c840c4714f8e240dce2ad6fceb", "Glimpse #08 - Blue Creek Apartments Clock Room"),
    ("cb4be69d9800734cbcb8e631c7c035e4", "Glimpse #09 - Blue Creek Apartments Room 109"),
    ("6f8ce80c6e7a3d41bb3c4bae4e48a7f2", "Glimpse #10 - Rosewater Park Pier"),
    ("676e1484b75c6747a4da3ab3a8fadc9e", "Glimpse #11 - Rosewater Park Statue"),
    ("434572a42998414abf12f80462e63067", "Glimpse #12 - Brookhaven Hospital Entrance"),
    ("51dccdbd4cacf248be354791ac5804b7", "Glimpse #13 - Brookhaven Hospital Examination Room"),
    ("e1853cd42ccf7340bba56f19b2522635", "Glimpse #14 - Brookhaven Hospital Basement"),
    ("e9aca85caf4518419b32068d14e5b00c", "Glimpse #15 - Brookhaven Hospital Otherworld Rooftop"),
    ("e9e189e223625947b728a10c5b0d76ce", "Glimpse #16 - West South Vale Historical Society Gate"),
    ("1fb122ed91a05544ba03e6d07dddcf08", "Glimpse #17 - Silent Hill Historical Society Gallery"),
    ("72902cd28bd2a94a982fb30dac10428b", "Glimpse #18 - Toluca Prison Shower Room"),
    ("dcac4e89d8e89d4f96ff1143c425a0c9", "Glimpse #19 - Toluca Prison Execution Yard"),
    ("28a9d98e12ed534a9f2dad930032a6b3", "Glimpse #20 - Labyrinth Despair Hallway"),
    ("f22c569015175243a78acaeab547c6a2", "Glimpse #21 - Labyrinth Rotten Area Room"),
    ("a985c7907a3f7d47a64fea1cea53ba29", "Glimpse #22 - Toluca Lake Dock Pier"),
    ("186e97749af94a4189a15e347187e045", "Glimpse #23 - Lakeview Hotel Pier Boat"),
    ("45400dbd15b0b840914b82ad9bd25049", "Glimpse #24 - Lakeview Hotel Garden"),
    ("688d251f1fcb7546905d79c4e430324b", "Glimpse #25 - Lakeview Hotel Reading Room"),
    ("cb7cf6d325ee794f8c27bdb6a7291e78", "Glimpse #26 - Lakeview Hotel Employee Stairwell"),
]

ALL_MEMOS = [
    "EcFW_BackRoomNote",
    "EcFW_BigJaysNote",
    "EcFW_Blockage_Note",
    "EcFW_CamperNote_Hard",
    "EcFW_FlowerShopNote",
    "EcFW_GrandMarketCodeNote",
    "EcFW_GroovyMusicNote",
    "EcFW_MartinStBody_Note",
    "EcFW_Matchbox",
    "EcFW_MotorHomeNote",
    "EcFW_NeelysBarNote",
    "EcFW_OldMap",
    "EcFW_SandersStBody_Note",
    "EcFW_SaulApt_Lobby_Note",
    "EcFW_SaulStBody_Note1",
    "EcFW_SaulStBody_Note2",
    "EcFW_SaulStBody_Note3",
    "EcFW_TenantsNote",
    "EcFW_TexansFlyer",
    "EcOW_LetterTrailer",
    "EcOW_LetterWrench",
    "End_Bliss_Bowling_Note",
    "End_Bliss_Nathan_Note_FirstGame",
    "End_Bliss_Nathan_Note_NG+",
    "HosFW_CodeLocation_Note",
    "HosFW_HeadNursesNote_Hard",
    "HosFW_HospitalSafeNote",
    "HosFW_KeyLockerNote",
    "HosFW_PatientFile1_Note",
    "HosFW_PatientFile2_Note",
    "HosFW_PatientFile3_Note",
    "HosFW_PatientNo22Note",
    "HosFW_PatientNo30Note",
    "HosFW_PatientNo48Note",
    "HosFW_RooftopDiaryPageNote",
    "HosFW_SecurityGuardNoteHard",
    "HosFW_Xray_Note",
    "HosOW_Director_Note1",
    "HosOW_Director_Note2",
    "HosOW_Director_Note3",
    "HosOW_Director_Note4",
    "HosOW_Electroshock_Note1",
    "HosOW_Electroshock_Note2",
    "HosOW_Evaluation_Note",
    "HosOW_Lobotomy_Note",
    "LhFW_CleanUp_Note",
    "LhOW_CleanGardenNote",
    "LhOW_CleanHotelRoomNote",
    "LhOW_CleanUpNote",
    "LhOW_LaurasLetter",
    "LhOW_LostMemories_Note",
    "LhOW_ManagerOfficeKeypadNote",
    "LhOW_Polariod_01_Hard",
    "LhOW_Polaroid_02_Hard",
    "LhOW_Polaroid_03_Hard",
    "LhOW_RecepcionistMemo",
    "PriOW_Boar_Disease_Note3",
    "PriOW_Boar_Prisoner_On_Guards_Note",
    "PriOW_Dove_Kidnapper_Note",
    "PriOW_Ox_Assaulter_Bathroom_Note",
    "PriOW_Ox_Assaulter_Cell_Note",
    "PriOW_Ox_Guards_Noticing_Stalker",
    "PriOW_Ox_Isolation_Cell_Note",
    "PriOW_Photo_Murderer",
    "PriOW_Rifle_Hint",
    "WcFW_Code_Note_Hard",
    "WcFW_Reception_Note",
    "WsaFW_Gun_Note",
    "WsaFW_Surface_Note1",
    "WsaFW_Surface_Note2",
]

ENDING_ITEMS = {
    "Rebirth Ending (NG+)": [
        ("End_Reb_CrimsonCeremony", "Crimson Ceremony Book"),
        ("End_Reb_WhiteChrism", "White Chrism"),
        ("End_Reb_ObsidianGoblet", "Obsidian Goblet"),
        ("LhOW_LostMemories_Note", "Book of Lost Memories"),
    ],
    "Dog Ending (NG+)": [
        ("End_Dog_Key_Full", "Dog Key"),
    ],
    "UFO Ending (NG+)": [
        ("End_UFO_ChannelingStone", "Blue Gem (Channeling Stone)"),
    ],
    "Bliss / Stillness / Others": [
        ("End_Silence_KeyofSorrow", "Key of Sorrow"),
        ("End_Silence_Postcard", "Postcard"),
        ("End_Bliss_RustedKey", "Rusted Key"),
    ],
}

ALL_STRANGE_PHOTOS = [f"Reflections_Photo_{i}" for i in range(1, 27)]

def get_save_location(raw_data):
    """Extract location name from save header."""
    idx = raw_data.find(b"YDBx")
    if idx == -1:
        return "Unknown"
    header = raw_data[:idx]
    matches = re.findall(rb"([A-Za-z0-9_]{5,})", header)
    ignore = {"Script", "SHProto", "SHSaveGame", "SavePoint", "Autosave", "VASb", "VASbp", "VASbw", "VASby", "VASbz"}
    for m in matches:
        s = m.decode(errors="ignore")
        if s not in ignore and not s.startswith("VASb"):
            return s
    return "Unknown"

def get_progression_tier(location_name):
    """Returns (tier_number, zone_description) from a save location tag."""
    loc = location_name.lower()
    if "hotel" in loc or "lhow" in loc:
        return 12, "Lakeview Hotel (Endgame)"
    if "lake" in loc:
        return 11, "Toluca Lake"
    if "labyrinth" in loc or "lhfw" in loc:
        return 10, "The Labyrinth"
    if "prison" in loc or "priow" in loc:
        return 9, "Toluca Prison"
    if "historical" in loc or "hist" in loc:
        return 8, "Silent Hill Historical Society"
    if "hospitalow" in loc or "hosow" in loc:
        return 6, "Brookhaven Hospital (Otherworld)"
    if "hospital" in loc or "hosfw" in loc:
        return 5, "Brookhaven Hospital"
    if any(k in loc for k in ["westcity", "wcfw", "rosewater", "jacksinn"]):
        return 4, "West South Vale"
    if "bluecreek" in loc or "bcaow" in loc:
        return 3, "Blue Creek Apartments"
    if "woodside" in loc or "wsafw" in loc:
        return 2, "Wood Side Apartments"
    if "eastcity" in loc or "ecfw" in loc:
        return 1, "East South Vale"
    return 0, "Prologue / Silent Hill Trail"

def get_memo_tier(memo_name):
    """Determine minimum safe progression tier for a memo."""
    if memo_name.startswith("LhOW_") or "Hotel" in memo_name:
        return 12
    if memo_name.startswith("LhFW_"):
        return 10
    if memo_name.startswith("PriOW_"):
        return 9
    if memo_name.startswith("EcOW_"):
        return 7
    if memo_name.startswith("HosOW_"):
        return 6
    if memo_name.startswith("HosFW_"):
        return 5
    if memo_name.startswith("WcFW_") or "End_Bliss" in memo_name:
        return 4
    if memo_name.startswith("WsaFW_"):
        return 2
    if memo_name.startswith("EcFW_"):
        return 1
    return 0

def get_glimpse_tier(glimpse_idx_1_based):
    """Determine minimum safe progression tier for a glimpse (1-26)."""
    if glimpse_idx_1_based <= 5:
        return 1
    if glimpse_idx_1_based <= 7:
        return 2
    if glimpse_idx_1_based <= 9:
        return 3
    if glimpse_idx_1_based <= 11:
        return 4
    if glimpse_idx_1_based <= 15:
        return 5
    if glimpse_idx_1_based <= 17:
        return 8
    if glimpse_idx_1_based <= 19:
        return 9
    if glimpse_idx_1_based <= 21:
        return 10
    return 12

def get_item_tier(item_name):
    """Determine minimum safe progression tier for an item."""
    if item_name in ["End_Reb_LostMemories", "LhOW_LostMemories_Note", "End_Silence_Postcard", "LhOW_312Key", "LhOW_VideoTape"] or item_name.startswith("LhOW_"):
        return 12
    if item_name.startswith("LhFW_"):
        return 10
    if item_name in ["RifleAmmo", "HuntingRifle"] or item_name.startswith("PriOW_"):
        return 9
    if item_name in ["End_Reb_ObsidianGoblet"]:
        return 8
    if item_name in ["ShotgunAmmo", "Shotgun"] or item_name.startswith("Hos"):
        return 5
    if item_name in ["End_Reb_WhiteChrism", "End_Dog_Key_Full", "End_Silence_KeyofSorrow", "End_Bliss_RustedKey"] or item_name.startswith("WcFW_") or "End_Bliss" in item_name:
        return 4
    if item_name.startswith("BcaOW_"):
        return 3
    if item_name.startswith("WsaFW_"):
        return 2
    if item_name in ["End_Reb_CrimsonCeremony", "End_UFO_ChannelingStone", "Pistol", "HandgunAmmo", "Chainsaw", "IronPipe", "HealthDrink", "Syringe"] or item_name.startswith("EcFW_"):
        return 1
    return 0

def get_latest_save(save_dir=DEFAULT_SAVE_DIR):
    pattern = os.path.join(save_dir, "SaveGameData_*.sav")
    saves = [f for f in glob.glob(pattern) if not f.endswith(".bak") and ".bak_" not in f]
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
    target = item_name.encode("ascii") + b"\x00"
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
    target = item_name.encode("ascii") + b"\x00"
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

    if to_chainsaw:
        if saw in decomp:
            return True
        if pipe in decomp:
            pos = 0
            while True:
                pos = decomp.find(pipe, pos)
                if pos == -1:
                    break
                decomp[pos:pos+len(pipe)] = saw
                pos += len(saw)
            return True
    else:
        if saw in decomp:
            pos = 0
            while True:
                pos = decomp.find(saw, pos)
                if pos == -1:
                    break
                decomp[pos:pos+len(saw)] = pipe
                pos += len(pipe)
            return True
    return False

def make_collected_item_struct(item_name, quantity=1):
    name_bytes = item_name.encode("ascii") + b"\x00"
    prop_size = len(name_bytes) + 4
    entry = (
        b"\x0c\x00\x00\x00ItemRowName\x00"
        b"\r\x00\x00\x00NameProperty\x00" +
        struct.pack("<Q", prop_size) +
        b"\x00" +
        struct.pack("<I", len(name_bytes)) +
        name_bytes +
        b"\t\x00\x00\x00Quantity\x00\x0c\x00\x00\x00IntProperty\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00" +
        struct.pack("<I", quantity) +
        b"\x05\x00\x00\x00None\x00"
    )
    return entry

def inject_collected_item(decomp, item_name, quantity=1, max_tier=None):
    if max_tier is not None:
        tier = get_item_tier(item_name)
        if tier > max_tier:
            return False, f"Progression Guard: Skipped {item_name} (Requires Stage {tier}, Save is Stage {max_tier})"

    name_bytes = item_name.encode("ascii") + b"\x00"
    name_entry = struct.pack("<I", len(name_bytes)) + name_bytes

    # 1. SkipInvestigationItems
    sii_pos = decomp.find(b"\x17\x00\x00\x00SkipInvestigationItems\x00")
    if sii_pos != -1:
        sii_ds_pos = sii_pos + 45
        sii_cnt_pos = sii_pos + 71
        old_ds = struct.unpack("<Q", decomp[sii_ds_pos:sii_ds_pos+8])[0]
        old_cnt = struct.unpack("<I", decomp[sii_cnt_pos:sii_cnt_pos+4])[0]
        sii_payload = decomp[sii_cnt_pos+4:sii_cnt_pos+old_ds]
        if name_entry not in sii_payload:
            decomp[sii_ds_pos:sii_ds_pos+8] = struct.pack("<Q", old_ds + len(name_entry))
            decomp[sii_cnt_pos:sii_cnt_pos+4] = struct.pack("<I", old_cnt + 1)
            insert_pos_sii = sii_cnt_pos + old_ds
            decomp[insert_pos_sii:insert_pos_sii] = name_entry

    # 2. CollectedItems
    ci_pos = decomp.find(b"\x0f\x00\x00\x00CollectedItems\x00")
    if ci_pos == -1:
        return False, "CollectedItems array not found in save"

    ci_ads_pos = ci_pos + 37
    ci_cnt_pos = ci_pos + 65
    ci_sds_pos = ci_pos + 107
    old_ads = struct.unpack("<Q", decomp[ci_ads_pos:ci_ads_pos+8])[0]
    old_cnt = struct.unpack("<I", decomp[ci_cnt_pos:ci_cnt_pos+4])[0]
    old_sds = struct.unpack("<Q", decomp[ci_sds_pos:ci_sds_pos+8])[0]

    items_payload = decomp[ci_pos+156:ci_pos+156+old_sds]
    if name_bytes in items_payload:
        set_item_quantity(decomp, item_name, quantity)
        return True, "Already in inventory (updated quantity)"

    entry = make_collected_item_struct(item_name, quantity)
    decomp[ci_ads_pos:ci_ads_pos+8] = struct.pack("<Q", old_ads + len(entry))
    decomp[ci_cnt_pos:ci_cnt_pos+4] = struct.pack("<I", old_cnt + 1)
    decomp[ci_sds_pos:ci_sds_pos+8] = struct.pack("<Q", old_sds + len(entry))
    insert_pos_ci = ci_pos + 156 + old_sds
    decomp[insert_pos_ci:insert_pos_ci] = entry

    return True, f"Injected {item_name} (Qty: {quantity})"

def inject_memo(decomp, memo_name, max_tier=None):
    if max_tier is not None:
        tier = get_memo_tier(memo_name)
        if tier > max_tier:
            return False, f"Progression Guard: Skipped {memo_name} (Requires Stage {tier}, Save is Stage {max_tier})"

    name_bytes = memo_name.encode("ascii") + b"\x00"
    name_entry = struct.pack("<I", len(name_bytes)) + name_bytes

    m_pos = decomp.find(b"\x13\x00\x00\x00MemosItemsPickedUp\x00")
    if m_pos != -1:
        m_ds_pos = m_pos + 41
        m_cnt_pos = m_pos + 67
        old_ds = struct.unpack("<Q", decomp[m_ds_pos:m_ds_pos+8])[0]
        old_cnt = struct.unpack("<I", decomp[m_cnt_pos:m_cnt_pos+4])[0]
        memos_payload = decomp[m_cnt_pos+4:m_cnt_pos+old_ds]
        if name_entry not in memos_payload:
            decomp[m_ds_pos:m_ds_pos+8] = struct.pack("<Q", old_ds + len(name_entry))
            decomp[m_cnt_pos:m_cnt_pos+4] = struct.pack("<I", old_cnt + 1)
            insert_pos_m = m_cnt_pos + old_ds
            decomp[insert_pos_m:insert_pos_m] = name_entry

    inject_collected_item(decomp, memo_name, quantity=1, max_tier=max_tier)
    return True, f"Injected Memo: {memo_name}"

def inject_glimpse(decomp, guid_bytes, max_tier=None):
    if isinstance(guid_bytes, str):
        guid_hex = guid_bytes.lower()
        guid_bytes = bytes.fromhex(guid_bytes)
    else:
        guid_hex = guid_bytes.hex().lower()

    if max_tier is not None:
        idx_1_based = None
        for i, (g, _) in enumerate(ALL_GLIMPSES, 1):
            if g.lower() == guid_hex:
                idx_1_based = i
                break
        if idx_1_based is not None:
            tier = get_glimpse_tier(idx_1_based)
            if tier > max_tier:
                return False, f"Progression Guard: Skipped Glimpse #{idx_1_based:02d} (Requires Stage {tier}, Save is Stage {max_tier})"

    g_pos = decomp.find(b"\x0f\x00\x00\x00GlimpsesOfPast\x00")
    if g_pos == -1:
        return False, "GlimpsesOfPast array not found in save"

    g_cnt = struct.unpack("<I", decomp[g_pos+19:g_pos+23])[0]
    existing_guids = decomp[g_pos+23:g_pos+23+g_cnt*16]
    if guid_bytes in existing_guids:
        return False, "Glimpse already registered in save"

    decomp[g_pos+19:g_pos+23] = struct.pack("<I", g_cnt + 1)
    insert_pos_g = g_pos + 23 + g_cnt * 16
    decomp[insert_pos_g:insert_pos_g] = guid_bytes
    return True, f"Injected Glimpse {guid_hex}"

def get_save_stats(decomp):
    hp = get_player_health(decomp)
    hg = get_item_quantity(decomp, "HandgunAmmo") or 0
    sg = get_item_quantity(decomp, "ShotgunAmmo") or 0
    rf = get_item_quantity(decomp, "RifleAmmo") or 0
    hd = get_item_quantity(decomp, "HealthDrink") or 0
    syr = get_item_quantity(decomp, "Syringe") or 0
    wpn = get_weapon_status(decomp)

    m_cnt = 0
    m_pos = decomp.find(b"\x13\x00\x00\x00MemosItemsPickedUp\x00")
    if m_pos != -1:
        m_cnt = struct.unpack("<I", decomp[m_pos+67:m_pos+71])[0]

    g_cnt = 0
    g_pos = decomp.find(b"\x0f\x00\x00\x00GlimpsesOfPast\x00")
    if g_pos != -1:
        g_cnt = struct.unpack("<I", decomp[g_pos+19:g_pos+23])[0]

    end_items_cnt = 0
    total_end_items = 0
    for cat_items in ENDING_ITEMS.values():
        for item_id, _ in cat_items:
            total_end_items += 1
            if item_id.encode() in decomp:
                end_items_cnt += 1

    return {
        "hp": hp,
        "hg": hg,
        "sg": sg,
        "rf": rf,
        "hd": hd,
        "syr": syr,
        "wpn": wpn,
        "m_cnt": m_cnt,
        "g_cnt": g_cnt,
        "end_items_cnt": end_items_cnt,
        "total_end_items": total_end_items,
    }

def print_status(save_path):
    raw_data, ydbx_idx, decomp = read_decompressed(save_path)
    fname = os.path.basename(save_path)
    mtime = datetime.fromtimestamp(os.path.getmtime(save_path)).strftime("%Y-%m-%d %H:%M:%S")
    stats = get_save_stats(decomp)
    loc = get_save_location(raw_data)
    tier, tier_desc = get_progression_tier(loc)

    hp_str = f"{stats['hp']:.0f} / 100" if stats["hp"] is not None else "Unknown"
    print(f"\n📂 Target Save: {fname} (Modified: {mtime})")
    print(f"📍 Location   : {loc} (Stage {tier}/12: {tier_desc})")
    print("-" * 52)
    print(f"  ❤️  Player Health       : {hp_str}")
    print(f"  ❤️  Health Drinks       : {stats['hd']}")
    print(f"  ❤️  Syringes            : {stats['syr']}")
    print(f"  🔫  Handgun Ammo        : {stats['hg']}")
    print(f"  🔫  Shotgun Ammo        : {stats['sg']}")
    print(f"  🔫  Hunting Rifle Ammo  : {stats['rf']}")
    print(f"  🪚  Equipped Melee      : {stats['wpn']}")
    print(f"  📖  Memos (Archivist)   : {stats['m_cnt']} / 70")
    print(f"  👁️  Glimpses (Echoes)   : {stats['g_cnt']} / 26")
    print(f"  🔑  Ending/Key Items    : {stats['end_items_cnt']} / {stats['total_end_items']}")
    print("-" * 52)

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

def apply_cheats(
    save_path,
    ammo=False,
    health=False,
    max_hp=False,
    chainsaw=None,
    all_memos=False,
    all_glimpses=False,
    all_endings=False,
    all_photos=False,
    max_safe=False,
    guard=True,
    custom_items=None,
    custom_memos=None,
    custom_glimpses=None,
):
    raw_data, ydbx_idx, decomp = read_decompressed(save_path)
    fname = os.path.basename(save_path)
    loc = get_save_location(raw_data)
    tier, tier_desc = get_progression_tier(loc)
    effective_guard_tier = tier if guard else None

    print(f"\n📂 Applying modifications to: {fname}")
    print(f"📍 Location: {loc} (Stage {tier}/12: {tier_desc})")
    print(f"🛡️  Progression Guard: [{'ENABLED' if guard else 'DISABLED (UNSAFE)'}]")
    print("-" * 52)

    changes_made = 0

    if max_safe:
        # Maximize safe progression for current zone
        print(f"⚡ Applying Maximum Safe Progression for Stage {tier} ({tier_desc})...")
        set_player_health(decomp, 100.0)
        set_item_quantity(decomp, "HandgunAmmo", 9999)
        if tier >= 5:
            set_item_quantity(decomp, "ShotgunAmmo", 9999)
        if tier >= 9:
            set_item_quantity(decomp, "RifleAmmo", 9999)
        set_item_quantity(decomp, "HealthDrink", 999)
        set_item_quantity(decomp, "Syringe", 999)
        set_weapon(decomp, to_chainsaw=True)

        m_added = 0
        for m in ALL_MEMOS:
            if get_memo_tier(m) <= tier:
                ok, _ = inject_memo(decomp, m, max_tier=tier)
                if ok: m_added += 1

        g_added = 0
        for i, (guid, _) in enumerate(ALL_GLIMPSES, 1):
            if get_glimpse_tier(i) <= tier:
                ok, _ = inject_glimpse(decomp, guid, max_tier=tier)
                if ok: g_added += 1

        e_added = 0
        for cat, items in ENDING_ITEMS.items():
            for item_id, _ in items:
                if get_item_tier(item_id) <= tier:
                    ok, _ = inject_collected_item(decomp, item_id, quantity=1, max_tier=tier)
                    if ok: e_added += 1

        print(f"  ✅ Safe Injections Complete: +{m_added} Memos, +{g_added} Glimpses, +{e_added} Key Items")
        changes_made += 1

    if ammo:
        set_item_quantity(decomp, "HandgunAmmo", 9999)
        if not guard or tier >= 5:
            set_item_quantity(decomp, "ShotgunAmmo", 9999)
        if not guard or tier >= 9:
            set_item_quantity(decomp, "RifleAmmo", 9999)
        print("  🔫  Ammo (Handgun/Shotgun/Rifle)     : 9,999 [APPLIED]")
        changes_made += 1

    if health:
        for item in ["HealthDrink", "Syringe"]:
            set_item_quantity(decomp, item, 999)
        print("  ❤️  Healing Items (Drinks/Syringes): 999 [APPLIED]")
        changes_made += 1

    if max_hp:
        set_player_health(decomp, 100.0)
        print("  ❤️  Player Health                   : 100% Full [APPLIED]")
        changes_made += 1

    if chainsaw is True:
        set_weapon(decomp, to_chainsaw=True)
        print("  🪚  Melee Weapon                   : NG+ Chainsaw [APPLIED]")
        changes_made += 1
    elif chainsaw is False:
        set_weapon(decomp, to_chainsaw=False)
        print("  🦯  Melee Weapon                   : Iron Pipe [RESTORED]")
        changes_made += 1

    if all_memos:
        count = 0
        skipped = 0
        for m in ALL_MEMOS:
            ok, msg = inject_memo(decomp, m, max_tier=effective_guard_tier)
            if ok: count += 1
            else: skipped += 1
        print(f"  📖  Memos                          : {count} Injected ({skipped} skipped by guard) [APPLIED]")
        changes_made += 1

    if all_glimpses:
        count = 0
        skipped = 0
        for guid_hex, _ in ALL_GLIMPSES:
            ok, _ = inject_glimpse(decomp, guid_hex, max_tier=effective_guard_tier)
            if ok: count += 1
            else: skipped += 1
        print(f"  👁️  Glimpses of the Past           : {count} Injected ({skipped} skipped by guard) [APPLIED]")
        changes_made += 1

    if all_endings:
        count = 0
        skipped = 0
        for cat, items in ENDING_ITEMS.items():
            for item_id, _ in items:
                ok, _ = inject_collected_item(decomp, item_id, quantity=1, max_tier=effective_guard_tier)
                if ok: count += 1
                else: skipped += 1
        print(f"  🔑  Key & Ending Items             : {count} Injected ({skipped} skipped by guard) [APPLIED]")
        changes_made += 1

    if all_photos:
        for p in ALL_STRANGE_PHOTOS:
            inject_collected_item(decomp, p, quantity=1, max_tier=effective_guard_tier)
        print("  📷  Strange Photos                 : Injected [APPLIED]")
        changes_made += 1

    if custom_items:
        for item_name, qty in custom_items:
            ok, msg = inject_collected_item(decomp, item_name, quantity=qty, max_tier=effective_guard_tier)
            print(f"  📦  Custom Item                    : {msg} [APPLIED]")
            changes_made += 1

    if custom_memos:
        for memo_name in custom_memos:
            ok, msg = inject_memo(decomp, memo_name, max_tier=effective_guard_tier)
            print(f"  📝  Custom Memo                    : {msg} [APPLIED]")
            changes_made += 1

    if custom_glimpses:
        for g in custom_glimpses:
            ok, msg = inject_glimpse(decomp, g, max_tier=effective_guard_tier)
            print(f"  👁️  Custom Glimpse                 : {msg} [APPLIED]")
            changes_made += 1

    if changes_made == 0:
        print("  ℹ️  No changes selected. Save file left untouched.")
        return None

    print("-" * 52)
    bak = write_repacked(save_path, raw_data, ydbx_idx, decomp)
    print(f"🛡️  Backup created: {os.path.basename(bak)}")
    print(f"✅ {fname} updated successfully! Ready to load.")
    return bak

def sub_menu_custom_injections():
    custom_items = []
    custom_memos = []
    custom_glimpses = []

    while True:
        print("\n" + "=" * 52)
        print("   🔍 CUSTOM ITEM / MEMO / GLIMPSE INJECTOR")
        print("=" * 52)
        print("SELECT INJECTION TYPE:")
        print("  [1] Inject Specific Ending Pack (Rebirth, Dog, UFO, Bliss, Stillness)")
        print("  [2] Select Individual Memo from Catalog (70 available)")
        print("  [3] Select Individual Glimpse from Catalog (26 available)")
        print("  [4] Type Exact Item Row Name to Inject")
        print("  [5] Type Exact Memo Row Name to Inject")
        print("  [B] Back to Main Menu")
        print("-" * 52)
        if custom_items or custom_memos or custom_glimpses:
            print("QUEUED CUSTOM INJECTIONS:")
            for i, q in custom_items:
                print(f"  • Item: {i} (x{q})")
            for m in custom_memos:
                print(f"  • Memo: {m}")
            for g in custom_glimpses:
                print(f"  • Glimpse: {g}")
            print("-" * 52)

        try:
            ch = input("Select an option [B]: ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            break

        if ch in ("", "B"):
            break
        elif ch == "1":
            print("\nSelect Ending Pack:")
            cats = list(ENDING_ITEMS.keys())
            for idx, c in enumerate(cats, 1):
                print(f"  [{idx}] {c}")
            sel = input("Enter choice: ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(cats):
                chosen_cat = cats[int(sel)-1]
                for item_id, item_label in ENDING_ITEMS[chosen_cat]:
                    custom_items.append((item_id, 1))
                print(f"✅ Added items for {chosen_cat}")
        elif ch == "2":
            filter_str = input("\nEnter search filter for memos (or press Enter for all): ").strip().lower()
            filtered = [m for m in ALL_MEMOS if filter_str in m.lower()]
            for idx, m in enumerate(filtered[:20], 1):
                print(f"  [{idx}] {m}")
            if len(filtered) > 20:
                print(f"  ... ({len(filtered)-20} more, refine search)")
            sel = input("Select memo index (or 0 to cancel): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= min(20, len(filtered)):
                custom_memos.append(filtered[int(sel)-1])
                print(f"✅ Queued memo: {filtered[int(sel)-1]}")
        elif ch == "3":
            print("\nGlimpses Catalog (1-26):")
            for idx, (guid, desc) in enumerate(ALL_GLIMPSES, 1):
                print(f"  [{idx:02d}] {desc}")
            sel = input("Select glimpse index (1-26): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(ALL_GLIMPSES):
                custom_glimpses.append(ALL_GLIMPSES[int(sel)-1][0])
                print(f"✅ Queued: {ALL_GLIMPSES[int(sel)-1][1]}")
        elif ch == "4":
            name = input("\nEnter exact item row name: ").strip()
            if name:
                qty_str = input("Enter quantity [1]: ").strip()
                qty = int(qty_str) if qty_str.isdigit() and int(qty_str) > 0 else 1
                custom_items.append((name, qty))
                print(f"✅ Queued item: {name} (x{qty})")
        elif ch == "5":
            name = input("\nEnter exact memo row name: ").strip()
            if name:
                custom_memos.append(name)
                print(f"✅ Queued memo: {name}")

    return custom_items, custom_memos, custom_glimpses

def interactive_cli(save_path):
    opt_ammo = False
    opt_health = False
    opt_max_hp = False
    opt_chainsaw = False
    opt_all_memos = False
    opt_all_glimpses = False
    opt_all_endings = False
    opt_all_photos = False
    opt_guard = True

    queued_items = []
    queued_memos = []
    queued_glimpses = []

    while True:
        print("\n" + "=" * 52)
        print("   🎮 SILENT HILL 2 REMAKE — SAVE CHEAT & INJECTOR")
        print("=" * 52)
        print_status(save_path)

        print("SELECT CHEATS & INJECTIONS (All OFF by default):")
        print(f"  [1] Max Ammo (Handgun / Shotgun / Rifle)     : [{'ON' if opt_ammo else 'OFF'}]")
        print(f"  [2] Max Healing Items (999 Drinks, Syringes) : [{'ON' if opt_health else 'OFF'}]")
        print(f"  [3] Full Player Health (100% HP)             : [{'ON' if opt_max_hp else 'OFF'}]")
        print(f"  [4] Equip NG+ Chainsaw                       : [{'ON' if opt_chainsaw else 'OFF'}]")
        print(f"  [5] Inject Memos (Archivist Trophy)          : [{'ON' if opt_all_memos else 'OFF'}]")
        print(f"  [6] Inject Glimpses of the Past (Echoes)     : [{'ON' if opt_all_glimpses else 'OFF'}]")
        print(f"  [7] Inject Key & Ending Items                : [{'ON' if opt_all_endings else 'OFF'}]")
        print(f"  [8] Inject Strange Photos                    : [{'ON' if opt_all_photos else 'OFF'}]")
        print(f"  [9] Custom Item / Memo / Glimpse Selector... ({len(queued_items) + len(queued_memos) + len(queued_glimpses)} queued)")
        print(f"  [0] Toggle Progression Guard                 : [{'ENABLED (Safe)' if opt_guard else 'DISABLED (Warning: Can Crash)'}]")
        print("\nQUICK ACTIONS:")
        print("  [S] Maximize Safe Progression (Inject all safe items/memos for current area)")
        print("  [A] Apply Selected Cheats to Save")
        print("  [R] Restore Latest Backup")
        print("  [Q] Quit")
        print("-" * 52)

        try:
            choice = input("Select an option [A]: ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

        if choice == "S":
            apply_cheats(save_path, max_safe=True, guard=True)
            break
        elif choice in ("", "A"):
            apply_cheats(
                save_path,
                ammo=opt_ammo,
                health=opt_health,
                max_hp=opt_max_hp,
                chainsaw=True if opt_chainsaw else None,
                all_memos=opt_all_memos,
                all_glimpses=opt_all_glimpses,
                all_endings=opt_all_endings,
                all_photos=opt_all_photos,
                guard=opt_guard,
                custom_items=queued_items,
                custom_memos=queued_memos,
                custom_glimpses=queued_glimpses,
            )
            break
        elif choice == "1":
            opt_ammo = not opt_ammo
        elif choice == "2":
            opt_health = not opt_health
        elif choice == "3":
            opt_max_hp = not opt_max_hp
        elif choice == "4":
            opt_chainsaw = not opt_chainsaw
        elif choice == "5":
            opt_all_memos = not opt_all_memos
        elif choice == "6":
            opt_all_glimpses = not opt_all_glimpses
        elif choice == "7":
            opt_all_endings = not opt_all_endings
        elif choice == "8":
            opt_all_photos = not opt_all_photos
        elif choice == "0":
            opt_guard = not opt_guard
        elif choice == "9":
            items, memos, glimpses = sub_menu_custom_injections()
            queued_items.extend(items)
            queued_memos.extend(memos)
            queued_glimpses.extend(glimpses)
        elif choice == "R":
            restore_latest_backup(os.path.dirname(save_path))
            break
        elif choice == "Q":
            print("Exiting.")
            break

def main():
    parser = argparse.ArgumentParser(
        description="Silent Hill 2 Save Cheat & Item Injector CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--save", "-s", type=str, help="Target specific .sav file")
    parser.add_argument("--dir", "-d", type=str, default=DEFAULT_SAVE_DIR, help="Save directory")
    parser.add_argument("--status", action="store_true", help="Print save status and exit")
    parser.add_argument("--restore", "-r", action="store_true", help="Restore latest backup and exit")
    parser.add_argument("--max-safe", action="store_true", help="Inject maximum safe memos, echoes, and items for current location")
    parser.add_argument("--ammo", action="store_true", help="Set 9,999 ammo for unlocked weapons")
    parser.add_argument("--health", action="store_true", help="Set 999 Health Drinks and Syringes")
    parser.add_argument("--max-hp", action="store_true", help="Restore player HP to 100%")
    parser.add_argument("--chainsaw", action="store_true", help="Equip NG+ Chainsaw")
    parser.add_argument("--pipe", action="store_true", help="Revert melee weapon to Iron Pipe")
    parser.add_argument("--all-memos", action="store_true", help="Inject Memos (filtered by Progression Guard)")
    parser.add_argument("--all-glimpses", action="store_true", help="Inject Glimpses of the Past (filtered by Progression Guard)")
    parser.add_argument("--all-endings", action="store_true", help="Inject Key & Ending Items (filtered by Progression Guard)")
    parser.add_argument("--all-photos", action="store_true", help="Inject Strange Photos (filtered by Progression Guard)")
    parser.add_argument("--no-guard", "--force", action="store_true", help="Disable Progression Guard (Warning: premature items may crash game)")
    parser.add_argument("--inject-memo", type=str, help="Inject specific memo by row name")
    parser.add_argument("--inject-glimpse", type=str, help="Inject specific glimpse by index (1-26) or 32-char GUID")
    parser.add_argument("--inject-item", nargs=2, metavar=("NAME", "QTY"), help="Inject any item row name and quantity")

    args = parser.parse_args()

    if args.restore:
        restore_latest_backup(args.dir)
        return

    save_path = args.save
    if not save_path:
        save_path = get_latest_save(args.dir)
        if not save_path:
            print(f"❌ No .sav files found in {args.dir}")
            sys.exit(1)

    if not os.path.isfile(save_path):
        print(f"❌ File not found: {save_path}")
        sys.exit(1)

    if args.status:
        print_status(save_path)
        return

    custom_items = []
    custom_memos = []
    custom_glimpses = []

    if args.inject_item:
        custom_items.append((args.inject_item[0], int(args.inject_item[1])))
    if args.inject_memo:
        custom_memos.append(args.inject_memo)
    if args.inject_glimpse:
        g_in = args.inject_glimpse
        if g_in.isdigit() and 1 <= int(g_in) <= len(ALL_GLIMPSES):
            custom_glimpses.append(ALL_GLIMPSES[int(g_in)-1][0])
        else:
            custom_glimpses.append(g_in)

    non_interactive = any([
        args.max_safe,
        args.ammo,
        args.health,
        args.max_hp,
        args.chainsaw,
        args.pipe,
        args.all_memos,
        args.all_glimpses,
        args.all_endings,
        args.all_photos,
        custom_items,
        custom_memos,
        custom_glimpses,
    ])

    if non_interactive:
        chainsaw_val = True if args.chainsaw else (False if args.pipe else None)
        apply_cheats(
            save_path,
            ammo=args.ammo,
            health=args.health,
            max_hp=args.max_hp,
            chainsaw=chainsaw_val,
            all_memos=args.all_memos,
            all_glimpses=args.all_glimpses,
            all_endings=args.all_endings,
            all_photos=args.all_photos,
            max_safe=args.max_safe,
            guard=not args.no_guard,
            custom_items=custom_items,
            custom_memos=custom_memos,
            custom_glimpses=custom_glimpses,
        )
    else:
        interactive_cli(save_path)

if __name__ == "__main__":
    main()
