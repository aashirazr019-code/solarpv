"""
core/ac_protection.py — AC Protection & Switchgear Sizing Engine
Handles AC SPDs, RCDs, AC Local Isolators, and Utility Lockable Isolators.
Authored by Eng. Aashir © 2026.
"""
from typing import Dict, Any, Optional
from .string_sizing import rnd
from .master_data import (
    get_ac_isolator_candidates,
    get_lockable_isolator_candidates,
    get_ac_spd_candidates,
    RULE_SOURCE_CEB,
    RULE_SOURCE_COMPANY,
    RULE_SOURCE_ENGINEERING,
    RULE_SOURCE_MANUAL_REVIEW
)

AC_SPD_STANDARD_RATINGS_V = [275, 320, 440, 750]


def size_ac_spd(ac_voltage_v: float, system_type: str = '3-phase'):
    """
    AC SPD Uc >= 1.15 × V_line_neutral.
    For 3-phase 400V system: V_LN = 230V, Uc >= 265V -> select 275V.
    For 1-phase 230V system: V_LN = 230V, Uc >= 265V -> select 275V.
    """
    if system_type == '3-phase':
        v_ln = ac_voltage_v / 1.732
    else:
        v_ln = ac_voltage_v
    
    required_uc = rnd(v_ln * 1.15, 1)
    
    chosen = None
    for rating in AC_SPD_STANDARD_RATINGS_V:
        if rating >= required_uc:
            chosen = rating
            break
    
    if chosen is None:
        return {
            'status': 'FAIL',
            'message': f'Required SPD Uc ({required_uc}V) exceeds available standard ratings.',
            'required_uc_v': required_uc,
        }
    
    return {
        'status': 'PASS',
        'spd_type': 'Type II',
        'voltage_rating_v': chosen,
        'required_uc_v': required_uc,
        'ac_voltage_v': ac_voltage_v,
        'system_type': system_type,
        'show_calculation': {
            'ac_voltage_v': ac_voltage_v,
            'v_line_neutral': rnd(v_ln, 1),
            'multiplier': 1.15,
            'required_uc_v': required_uc,
            'selected_rating_v': chosen,
        },
    }


def select_rcd(inverter_type: str = 'string', has_transformer: bool = False):
    """
    RCD type selection per IEC 62423 / IEC 60364-7-712.
    Type B RCD required for transformerless inverters.
    Type A acceptable for isolated (transformer-based) inverters.
    """
    if has_transformer:
        rcd_type = 'Type A'
        reason = 'Transformer-isolated inverter blocks DC fault currents — Type A RCD is sufficient.'
    else:
        rcd_type = 'Type B'
        reason = ('Transformerless inverter may inject DC residual currents — '
                  'Type B RCD required unless inverter has certified DC injection < 6mA '
                  '(IEC 62109-2 compliant). REQUIRES ENGINEERING CONFIRMATION.')
    
    return {
        'status': 'PASS',
        'rcd_type': rcd_type,
        'sensitivity_ma': 30,
        'fire_protection_sensitivity_ma': 300,
        'inverter_type': inverter_type,
        'has_transformer': has_transformer,
        'reason': reason,
        'show_calculation': {
            'inverter_type': inverter_type,
            'has_transformer': has_transformer,
            'selected_rcd_type': rcd_type,
            'personal_protection': '30mA',
            'fire_protection': '300mA',
        },
    }


def size_ac_isolator_from_master(ac_current_a: float, phases: int = 3, safety_factor: float = 1.25) -> Dict[str, Any]:
    """
    Selects real AC Isolator from Master Data catalog.
    Design Current = ac_current_a * safety_factor (default 1.25).
    """
    min_current = rnd(ac_current_a * safety_factor, 1)
    candidates = get_ac_isolator_candidates(min_current_a=min_current, phases=phases)
    
    if not candidates:
        return {
            "status": "MANUAL_REVIEW",
            "device": None,
            "min_current_a": min_current,
            "model": "No suitable AC isolator found — Engineering Review Required.",
            "rule_source": RULE_SOURCE_MANUAL_REVIEW,
            "message": "No suitable AC isolator found — Engineering Review Required.",
            "show_calculation": {
                "design_current": f"AC Current ({ac_current_a}A) × {safety_factor} = {min_current} A"
            }
        }
    
    selected = candidates[0]
    return {
        "status": "PASS",
        "device": selected,
        "model": selected["model"],
        "rating": f"{selected['rated_current_a']}A, {selected['voltage_rating_v']}V ({selected['poles']})",
        "rated_current_a": selected["rated_current_a"],
        "voltage_rating_v": selected["voltage_rating_v"],
        "poles": selected["poles"],
        "phases": selected.get("phases", phases),
        "ac_type": selected.get("ac_type", "AC-23A"),
        "rule_source": RULE_SOURCE_COMPANY,
        "message": f"Selected {selected['model']} ({selected['rated_current_a']}A / {selected['voltage_rating_v']}V {selected['poles']}).",
        "show_calculation": {
            "design_current": f"AC Current ({ac_current_a}A) × {safety_factor} = {min_current} A (Selected: {selected['rated_current_a']}A)"
        }
    }


def size_lockable_isolator_from_master(ac_current_a: float, phases: int = 3, safety_factor: float = 1.25) -> Dict[str, Any]:
    """
    Selects utility lockable isolator switch required at point of utility interconnection.
    Standards:
      Single-Phase (1P): 32A, 40A, or 63A (2-Pole)
      Three-Phase (3P): 63A, 100A, 160A, 250A (4-Pole)
    Padlockable in OFF position.
    """
    min_current = rnd(ac_current_a * safety_factor, 1)
    candidates = get_lockable_isolator_candidates(min_current_a=min_current, phases=phases)
    
    if not candidates:
        return {
            "status": "MANUAL_REVIEW",
            "device": None,
            "min_current_a": min_current,
            "model": "No suitable Lockable Isolator found — Engineering Review Required.",
            "rule_source": RULE_SOURCE_MANUAL_REVIEW,
            "message": "No suitable Lockable Isolator found — Engineering Review Required.",
            "show_calculation": {
                "design_current": f"AC Current ({ac_current_a}A) × {safety_factor} = {min_current} A"
            }
        }
    
    selected = candidates[0]
    return {
        "status": "PASS",
        "device": selected,
        "model": selected["model"],
        "rating": f"{selected['rated_current_a']}A, {selected['voltage_rating_v']}V ({selected['poles']})",
        "rated_current_a": selected["rated_current_a"],
        "voltage_rating_v": selected["voltage_rating_v"],
        "poles": selected["poles"],
        "phases": selected.get("phases", phases),
        "features": selected.get("features", "Padlockable in OFF position"),
        "rule_source": RULE_SOURCE_CEB,
        "message": f"Selected Utility Lockable Isolator: {selected['model']} ({selected['rated_current_a']}A {selected['poles']}).",
        "show_calculation": {
            "design_current": f"AC Current ({ac_current_a}A) × {safety_factor} = {min_current} A (Selected: {selected['rated_current_a']}A)",
            "rule": f"CEB/Utility Interconnection Rule: Must be lockable in OFF position ({RULE_SOURCE_CEB})"
        }
    }


def size_ac_spd_from_master(phases: int = 3, ac_voltage_v: float = 400.0) -> Dict[str, Any]:
    """
    Selects AC SPD from Master Data catalog for single or three-phase configurations.
    """
    candidates = get_ac_spd_candidates(phases=phases)
    if not candidates:
        # Fallback to analytical calculation
        return size_ac_spd(ac_voltage_v, system_type='3-phase' if phases == 3 else '1-phase')
    
    selected = candidates[0]
    return {
        "status": "PASS",
        "device": selected,
        "model": selected.get("id", "ac-spd"),
        "rating": f"Uc {selected['uc_v']}V, Imax {selected['imax_ka']}kA ({selected['poles']})",
        "uc_v": selected["uc_v"],
        "imax_ka": selected["imax_ka"],
        "poles": selected["poles"],
        "phases": selected["phases"],
        "spd_type": selected.get("spd_type", "Type II (IEC 61643-11)"),
        "rule_source": RULE_SOURCE_ENGINEERING,
        "message": f"Selected AC SPD Uc {selected['uc_v']}V ({selected['poles']}).",
        "show_calculation": {
            "phases": f"{phases}-Phase System ({ac_voltage_v}V)",
            "standard": f"IEC 61643-11 Type II surge protection ({RULE_SOURCE_ENGINEERING})"
        }
    }
