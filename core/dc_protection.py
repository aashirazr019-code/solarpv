"""
core/dc_protection.py — DC Protection Sizing Engine
Handles DC String Fuses (IEC 60269-6), DC SPDs, and DC Isolators from Master Catalog.
Authored by Eng. Aashir © 2026.
"""
import math
from .string_sizing import rnd
from .master_data import (
    get_dc_isolator_candidates,
    get_dc_spd_candidates,
    RULE_SOURCE_COMPANY,
    RULE_SOURCE_ENGINEERING,
    RULE_SOURCE_MANUAL_REVIEW
)


def size_dc_string_fuse(panel_isc: float, panel_max_series_fuse: float, strings_per_mppt: int):
    """
    Fuse required if strings_per_mppt >= 3.
    I_fuse >= 1.5 × Isc_panel AND I_fuse <= panel_max_series_fuse
    Per IEC 60269-6.
    """
    fuse_required = strings_per_mppt >= 3
    fuse_rating_a = rnd(panel_isc * 1.5, 2) if fuse_required else None
    status = "PASS"
    if fuse_required and fuse_rating_a > panel_max_series_fuse:
        status = "FAIL"
    return {
        "fuse_required": fuse_required,
        "fuse_rating_a": fuse_rating_a,
        "status": status,
        "show_calculation": {"rating": f"{panel_isc} * 1.5 = {fuse_rating_a}" if fuse_required else "N/A"}
    }


def size_dc_spd(max_string_voc_cold: float):
    """
    SPD Uc >= 1.2 × V_string_oc_cold.
    Standard DC SPD voltage ratings: 600, 1000, 1200, 1500V.
    """
    min_uc = rnd(max_string_voc_cold * 1.2, 2)
    spd_voltage_rating_v = next((v for v in [600, 1000, 1200, 1500] if v >= min_uc), None)
    return {
        "spd_voltage_rating_v": spd_voltage_rating_v,
        "status": "PASS" if spd_voltage_rating_v else "FAIL",
        "show_calculation": {"min_uc": f"{max_string_voc_cold} * 1.2 = {min_uc}"}
    }


def size_dc_isolator(max_string_voc_cold: float, max_string_isc: float):
    """Basic rating calculation for DC isolator."""
    return {
        "voltage_rating_v": rnd(max_string_voc_cold * 1.15, 2),
        "current_rating_a": rnd(max_string_isc * 1.25, 2),
        "status": "PASS",
        "show_calculation": {
            "voltage_rating_v": f"{max_string_voc_cold} * 1.15 = {rnd(max_string_voc_cold * 1.15, 2)}",
            "current_rating_a": f"{max_string_isc} * 1.25 = {rnd(max_string_isc * 1.25, 2)}"
        }
    }


def size_dc_isolator_from_master(
    max_string_voc_cold: float,
    max_string_isc: float,
    total_strings: int = 1,
    preferred_poles: str = None,
    strings_per_isolator: int = 1
):
    """
    Selects real DC isolator device from Master Data catalog.
    Applies Company Rule: 1 isolator per string (default) -> Quantity = total_strings.
    If no catalog match is found, reports 'No suitable DC isolator found — Engineering Review Required.'
    """
    min_v = rnd(max_string_voc_cold * 1.15, 1)
    min_i = rnd(max_string_isc * 1.25, 1)
    
    candidates = get_dc_isolator_candidates(min_voltage_v=min_v, min_current_a=min_i, preferred_poles=preferred_poles)
    
    qty = max(1, math.ceil(total_strings / max(1, strings_per_isolator)))
    
    if not candidates:
        return {
            "status": "MANUAL_REVIEW",
            "device": None,
            "quantity": qty,
            "min_voltage_v": min_v,
            "min_current_a": min_i,
            "model": "No suitable DC isolator found — Engineering Review Required.",
            "rule_source": RULE_SOURCE_MANUAL_REVIEW,
            "message": "No suitable DC isolator found — Engineering Review Required.",
            "show_calculation": {
                "min_voltage": f"Voc,cold ({max_string_voc_cold}V) × 1.15 = {min_v} V",
                "min_current": f"Isc ({max_string_isc}A) × 1.25 = {min_i} A",
                "quantity": f"Company Rule: {total_strings} strings / {strings_per_isolator} per isolator = {qty} units"
            }
        }
    
    selected = candidates[0]
    return {
        "status": "PASS",
        "device": selected,
        "model": selected["model"],
        "rating": f"{selected['current_rating_a']}A, {selected['voltage_rating_v']}V ({selected['poles']})",
        "voltage_rating_v": selected["voltage_rating_v"],
        "current_rating_a": selected["current_rating_a"],
        "poles": selected["poles"],
        "quantity": qty,
        "rule_source": selected.get("rule_source", RULE_SOURCE_COMPANY),
        "message": f"Selected {selected['model']} ({selected['current_rating_a']}A / {selected['voltage_rating_v']}V).",
        "show_calculation": {
            "min_voltage": f"Voc,cold ({max_string_voc_cold}V) × 1.15 = {min_v} V (Selected: {selected['voltage_rating_v']}V)",
            "min_current": f"Isc ({max_string_isc}A) × 1.25 = {min_i} A (Selected: {selected['current_rating_a']}A)",
            "quantity": f"Company Rule: {total_strings} strings -> {qty} DC isolators required ({RULE_SOURCE_COMPANY})"
        }
    }


def size_dc_spd_from_master(max_string_voc_cold: float, num_inverters: int = 1):
    """
    Selects real DC SPD device from Master Data catalog where Uc >= 1.2 * Voc,cold.
    """
    min_uc = rnd(max_string_voc_cold * 1.2, 1)
    candidates = get_dc_spd_candidates(min_voltage_v=min_uc)
    
    if not candidates:
        return {
            "status": "MANUAL_REVIEW",
            "device": None,
            "quantity": num_inverters,
            "min_uc_v": min_uc,
            "uc_v": min_uc,
            "imax_ka": 40.0,
            "up_kv": 3.8,
            "poles": "3P",
            "model": "No suitable DC SPD found — Engineering Review Required.",
            "rule_source": RULE_SOURCE_MANUAL_REVIEW,
            "message": "No suitable DC SPD found — Engineering Review Required.",
            "show_calculation": {
                "min_uc": f"Voc,cold ({max_string_voc_cold}V) × 1.20 = {min_uc} V"
            }
        }
    
    selected = candidates[0]
    return {
        "status": "PASS",
        "device": selected,
        "model": selected["model"],
        "rating": f"Uc {selected['uc_v']}V, Imax {selected['imax_ka']}kA ({selected['poles']})",
        "min_uc_v": min_uc,
        "uc_v": selected["uc_v"],
        "imax_ka": selected["imax_ka"],
        "up_kv": selected.get("up_kv", 3.8),
        "poles": selected.get("poles", "3P"),
        "quantity": num_inverters,
        "rule_source": selected.get("rule_source", RULE_SOURCE_ENGINEERING),
        "message": f"Selected {selected['model']} with Uc {selected['uc_v']}V.",
        "show_calculation": {
            "min_uc": f"Voc,cold ({max_string_voc_cold}V) × 1.20 = {min_uc} V (Selected Uc: {selected['uc_v']}V)",
            "quantity": f"1 SPD per inverter DC section × {num_inverters} inverters = {num_inverters} units"
        }
    }
