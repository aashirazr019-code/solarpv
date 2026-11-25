"""
Cable / MCB / Busbar reference data.

Cable ampacity table transcribed from the uploaded chart:
Kelani Cables — Single-core PVC insulated, non-armoured, BS 6004/BS 6346,
Table A1 — Current Carrying Capacity. Ambient air 30°C, conductor
operating temp 70°C. Source: BS 7671:2008 (IEE Wiring Regs, 17th Ed).

Column keys match installation method + arrangement exactly as printed
on the chart, so a UI label maps 1:1 to a chart column — no guessing.
"""

# ---------------------------------------------------------------------------
# CABLE AMPACITY TABLE (Table A1)
# ---------------------------------------------------------------------------
# a_2c / a_34c   = Method A, enclosed in conduit in insulated wall
# b_2c / b_34c   = Method B, enclosed in conduit on wall / in trunking
# c_2c / c_34c   = Method C, clipped direct
# f_touch_*      = Method F, in free air / on tray, cables touching
# f_spaced_*     = Method F, in free air / on tray, spaced by one diameter
# Values are Amps. None = not published on the chart for that size/method.

CABLE_AMPACITY_TABLE = [
    {"csa_mm2": 1,    "a_2c": 11,  "a_34c": 10.5, "b_2c": 13.5, "b_34c": 12,   "c_2c": 15.5, "c_34c": 14,   "f_touch_2c": None, "f_touch_3flat": None, "f_touch_3trefoil": None, "f_spaced_h": None, "f_spaced_v": None},
    {"csa_mm2": 1.5,  "a_2c": 14.5,"a_34c": 13.5, "b_2c": 17.5, "b_34c": 15.5, "c_2c": 20,   "c_34c": 18,   "f_touch_2c": None, "f_touch_3flat": None, "f_touch_3trefoil": None, "f_spaced_h": None, "f_spaced_v": None},
    {"csa_mm2": 2.5,  "a_2c": 20,  "a_34c": 18,   "b_2c": 24,   "b_34c": 21,   "c_2c": 27,   "c_34c": 25,   "f_touch_2c": None, "f_touch_3flat": None, "f_touch_3trefoil": None, "f_spaced_h": None, "f_spaced_v": None},
    {"csa_mm2": 4,    "a_2c": 26,  "a_34c": 24,   "b_2c": 32,   "b_34c": 28,   "c_2c": 37,   "c_34c": 33,   "f_touch_2c": None, "f_touch_3flat": None, "f_touch_3trefoil": None, "f_spaced_h": None, "f_spaced_v": None},
    {"csa_mm2": 6,    "a_2c": 34,  "a_34c": 31,   "b_2c": 41,   "b_34c": 36,   "c_2c": 47,   "c_34c": 43,   "f_touch_2c": None, "f_touch_3flat": None, "f_touch_3trefoil": None, "f_spaced_h": None, "f_spaced_v": None},
    {"csa_mm2": 10,   "a_2c": 46,  "a_34c": 42,   "b_2c": 57,   "b_34c": 50,   "c_2c": 65,   "c_34c": 59,   "f_touch_2c": None, "f_touch_3flat": None, "f_touch_3trefoil": None, "f_spaced_h": None, "f_spaced_v": None},
    {"csa_mm2": 16,   "a_2c": 61,  "a_34c": 56,   "b_2c": 76,   "b_34c": 68,   "c_2c": 87,   "c_34c": 79,   "f_touch_2c": None, "f_touch_3flat": None, "f_touch_3trefoil": None, "f_spaced_h": None, "f_spaced_v": None},
    {"csa_mm2": 25,   "a_2c": 80,  "a_34c": 73,   "b_2c": 101,  "b_34c": 89,   "c_2c": 114,  "c_34c": 104,  "f_touch_2c": 131,  "f_touch_3flat": 114,   "f_touch_3trefoil": 110,   "f_spaced_h": 146,   "f_spaced_v": 130},
    {"csa_mm2": 35,   "a_2c": 99,  "a_34c": 89,   "b_2c": 125,  "b_34c": 110,  "c_2c": 141,  "c_34c": 129,  "f_touch_2c": 162,  "f_touch_3flat": 143,   "f_touch_3trefoil": 137,   "f_spaced_h": 181,   "f_spaced_v": 162},
    {"csa_mm2": 50,   "a_2c": 119, "a_34c": 108,  "b_2c": 151,  "b_34c": 134,  "c_2c": 182,  "c_34c": 167,  "f_touch_2c": 196,  "f_touch_3flat": 174,   "f_touch_3trefoil": 167,   "f_spaced_h": 219,   "f_spaced_v": 197},
    {"csa_mm2": 70,   "a_2c": 151, "a_34c": 136,  "b_2c": 192,  "b_34c": 171,  "c_2c": 234,  "c_34c": 214,  "f_touch_2c": 251,  "f_touch_3flat": 225,   "f_touch_3trefoil": 216,   "f_spaced_h": 281,   "f_spaced_v": 254},
    {"csa_mm2": 95,   "a_2c": 182, "a_34c": 164,  "b_2c": 232,  "b_34c": 207,  "c_2c": 284,  "c_34c": 261,  "f_touch_2c": 304,  "f_touch_3flat": 275,   "f_touch_3trefoil": 264,   "f_spaced_h": 341,   "f_spaced_v": 311},
    {"csa_mm2": 120,  "a_2c": 210, "a_34c": 188,  "b_2c": 269,  "b_34c": 239,  "c_2c": 330,  "c_34c": 303,  "f_touch_2c": 352,  "f_touch_3flat": 321,   "f_touch_3trefoil": 308,   "f_spaced_h": 396,   "f_spaced_v": 362},
    {"csa_mm2": 150,  "a_2c": 240, "a_34c": 216,  "b_2c": 300,  "b_34c": 262,  "c_2c": 381,  "c_34c": 349,  "f_touch_2c": 406,  "f_touch_3flat": 372,   "f_touch_3trefoil": 356,   "f_spaced_h": 456,   "f_spaced_v": 419},
    {"csa_mm2": 185,  "a_2c": 273, "a_34c": 245,  "b_2c": 341,  "b_34c": 296,  "c_2c": 436,  "c_34c": 400,  "f_touch_2c": 463,  "f_touch_3flat": 427,   "f_touch_3trefoil": 409,   "f_spaced_h": 521,   "f_spaced_v": 480},
    {"csa_mm2": 240,  "a_2c": 321, "a_34c": 286,  "b_2c": 400,  "b_34c": 346,  "c_2c": 515,  "c_34c": 472,  "f_touch_2c": 546,  "f_touch_3flat": 507,   "f_touch_3trefoil": 485,   "f_spaced_h": 615,   "f_spaced_v": 569},
    {"csa_mm2": 300,  "a_2c": 367, "a_34c": 328,  "b_2c": 458,  "b_34c": 394,  "c_2c": 594,  "c_34c": 545,  "f_touch_2c": 629,  "f_touch_3flat": 587,   "f_touch_3trefoil": 561,   "f_spaced_h": 709,   "f_spaced_v": 659},
    {"csa_mm2": 400,  "a_2c": None,"a_34c": None, "b_2c": 546,  "b_34c": 467,  "c_2c": 694,  "c_34c": 634,  "f_touch_2c": 754,  "f_touch_3flat": 689,   "f_touch_3trefoil": 656,   "f_spaced_h": 852,   "f_spaced_v": 795},
    {"csa_mm2": 500,  "a_2c": None,"a_34c": None, "b_2c": 626,  "b_34c": 533,  "c_2c": 792,  "c_34c": 723,  "f_touch_2c": 868,  "f_touch_3flat": 789,   "f_touch_3trefoil": 749,   "f_spaced_h": 982,   "f_spaced_v": 920},
    {"csa_mm2": 630,  "a_2c": None,"a_34c": None, "b_2c": 720,  "b_34c": 611,  "c_2c": 904,  "c_34c": 826,  "f_touch_2c": 1005, "f_touch_3flat": 905,   "f_touch_3trefoil": 855,   "f_spaced_h": 1138,  "f_spaced_v": 1070},
    {"csa_mm2": 800,  "a_2c": None,"a_34c": None, "b_2c": None, "b_34c": None, "c_2c": 1030, "c_34c": 943,  "f_touch_2c": 1086, "f_touch_3flat": 1020,  "f_touch_3trefoil": 971,   "f_spaced_h": 1265,  "f_spaced_v": 1188},
    {"csa_mm2": 1000, "a_2c": None,"a_34c": None, "b_2c": None, "b_34c": None, "c_2c": 1154, "c_34c": 1058, "f_touch_2c": 1216, "f_touch_3flat": 1149,  "f_touch_3trefoil": 1079,  "f_spaced_h": 1420,  "f_spaced_v": 1337},
]

# UI label -> table column key. Order matters (shown as a dropdown).
INSTALLATION_METHODS = [
    ("Method A — 2 cables single-phase/DC, enclosed in conduit (insulated wall)", "a_2c"),
    ("Method A — 3/4 cables three-phase, enclosed in conduit (insulated wall)", "a_34c"),
    ("Method B — 2 cables single-phase/DC, enclosed in conduit on wall / trunking", "b_2c"),
    ("Method B — 3/4 cables three-phase, enclosed in conduit on wall / trunking", "b_34c"),
    ("Method C — 2 cables single-phase/DC, clipped direct", "c_2c"),
    ("Method C — 3/4 cables three-phase, clipped direct", "c_34c"),
    ("Method F — 2 cables single-phase/DC, free air / tray, touching", "f_touch_2c"),
    ("Method F — 3 cables three-phase flat, free air / tray, touching", "f_touch_3flat"),
    ("Method F — 3 cables three-phase trefoil, free air / tray, touching", "f_touch_3trefoil"),
    ("Method F — 2 cables single-phase/DC, free air / tray, spaced — horizontal", "f_spaced_h"),
    ("Method F — 2 cables single-phase/DC, free air / tray, spaced — vertical", "f_spaced_v"),
]

# Aliases mapping common engineering names to Table A1 column keys
METHOD_KEY_ALIASES = {
    # Method A
    "method_a_1ph": "a_2c",
    "method_a_2c": "a_2c",
    "method_a_3ph": "a_34c",
    "method_a_34c": "a_34c",
    # Method B
    "method_b_1ph": "b_2c",
    "method_b_2c": "b_2c",
    "method_b_3ph": "b_34c",
    "method_b_34c": "b_34c",
    "enclosed_conduit_1ph": "b_2c",
    "enclosed_conduit_1phase": "b_2c",
    "enclosed_conduit_3ph": "b_34c",
    "enclosed_conduit_3phase": "b_34c",
    "enclosed_conduit": "b_34c",
    "multicore_copper": "b_34c",
    # Method C
    "method_c_1ph": "c_2c",
    "method_c_2c": "c_2c",
    "method_c_3ph": "c_34c",
    "method_c_34c": "c_34c",
    "clipped_direct": "c_34c",
    "clipped_direct_1ph": "c_2c",
    "clipped_direct_3ph": "c_34c",
    "dc_solar": "c_2c",
    "solar_dc": "c_2c",
    # Method F
    "method_f_touch_2c": "f_touch_2c",
    "method_f_touch_3flat": "f_touch_3flat",
    "method_f_touch_3trefoil": "f_touch_3trefoil",
    "method_f_spaced_h": "f_spaced_h",
    "method_f_spaced_v": "f_spaced_v",
    "free_air": "f_touch_3flat",
    "cable_tray": "f_touch_3flat",
}

VALID_TABLE_A1_COLUMNS = {
    "a_2c", "a_34c", "b_2c", "b_34c", "c_2c", "c_34c",
    "f_touch_2c", "f_touch_3flat", "f_touch_3trefoil", "f_spaced_h", "f_spaced_v"
}


def resolve_method_key(key: str, default: str = "b_34c") -> str:
    """Resolves an installation method key or alias to a valid Table A1 column key."""
    if not key:
        return default
    k = str(key).strip().lower()
    if k in VALID_TABLE_A1_COLUMNS:
        return k
    return METHOD_KEY_ALIASES.get(k, default)


# ---------------------------------------------------------------------------
# MCB / MCCB standard ratings (IEC 60898 / IEC 60947-2 common series)
# ---------------------------------------------------------------------------
MCB_STANDARD_RATINGS_A = [6, 10, 13, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125]
MCCB_STANDARD_RATINGS_A = [100, 125, 160, 200, 250, 320, 400, 500, 630, 800, 1000, 1250, 1600, 2000]

# ---------------------------------------------------------------------------
# Busbar standard current ratings — common panel-board/switchboard series
# ---------------------------------------------------------------------------
BUSBAR_STANDARD_RATINGS_A = [40, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3200, 4000]

# Copper resistivity at 20°C (standard value ohm.mm²/m)
COPPER_RESISTIVITY = 0.01724
COPPER_RESISTIVITY_20C = 0.01724

# Approximate copper resistivity at typical PVC conductor operating temp
# (70°C), used only for an indicative voltage-drop estimate — not a
# substitute for a manufacturer's Table A2 mV/A/m voltage-drop table.
COPPER_RESISTIVITY_OHM_MM2_PER_M_AT_70C = 0.0225
