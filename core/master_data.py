"""
core/master_data.py — Central Master Data & Rule Engine
Loads, queries, and filters master equipment specifications and applies explicit rule sourcing:
- "CEB_REQUIRED"
- "ENGINEERING_RULE"
- "COMPANY_STANDARD"
- "INSTALLER_RULE"
- "MANUAL_REVIEW_REQUIRED"
- "USER_DEFINED"
Authored by Eng. Aashir © 2026.
"""
import os
import json
from typing import Dict, List, Optional, Any

MASTER_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "master_data.json")

# Standardized Rule Sources per Engineering Requirements
RULE_SOURCE_CEB = "CEB_REQUIRED"
RULE_SOURCE_ENGINEERING = "ENGINEERING_RULE"
RULE_SOURCE_COMPANY = "COMPANY_STANDARD"
RULE_SOURCE_INSTALLER = "INSTALLER_RULE"
RULE_SOURCE_MANUAL_REVIEW = "MANUAL_REVIEW_REQUIRED"
RULE_SOURCE_USER = "USER_DEFINED"


def load_master_data() -> Dict[str, Any]:
    """Loads central master catalog from JSON file."""
    if os.path.exists(MASTER_DATA_FILE):
        try:
            with open(MASTER_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_dc_isolator_candidates(min_voltage_v: float = 600.0, min_current_a: float = 15.0, preferred_poles: Optional[str] = None) -> List[Dict]:
    """
    Finds matching DC isolator options from master data satisfying voltage and current limits.
    """
    md = load_master_data()
    isolators = md.get("dc_isolators", [])
    matches = []
    for iso in isolators:
        if not iso.get("is_active", True):
            continue
        if iso["voltage_rating_v"] >= min_voltage_v and iso["current_rating_a"] >= min_current_a:
            if preferred_poles and iso.get("poles") != preferred_poles:
                continue
            matches.append(iso)
    # Sort by current rating ascending, then voltage rating ascending
    matches.sort(key=lambda x: (x["current_rating_a"], x["voltage_rating_v"]))
    return matches


def get_dc_spd_candidates(min_voltage_v: float = 600.0) -> List[Dict]:
    """Finds matching DC SPDs where Uc >= min_voltage_v."""
    md = load_master_data()
    spds = md.get("dc_spds", [])
    matches = [s for s in spds if s.get("is_active", True) and s["uc_v"] >= min_voltage_v]
    matches.sort(key=lambda x: x["uc_v"])
    return matches


def get_dc_fuse_candidates(min_voltage_v: float = 1000.0, min_current_a: float = 15.0) -> List[Dict]:
    """Finds matching DC gPV fuse links from master data or standard ratings."""
    md = load_master_data()
    fuses = md.get("dc_fuses", [])
    if fuses:
        matches = [f for f in fuses if f.get("is_active", True) and f.get("voltage_rating_v", 1000) >= min_voltage_v and f.get("current_rating_a", 15) >= min_current_a]
        if matches:
            return matches
    return [
        {"brand": "Suntree", "model": "SRD-30 1000V 15A", "voltage_rating_v": 1000, "current_rating_a": 15},
        {"brand": "Suntree", "model": "SRD-30 1000V 20A", "voltage_rating_v": 1000, "current_rating_a": 20},
        {"brand": "Suntree", "model": "SRD-30 1000V 25A", "voltage_rating_v": 1000, "current_rating_a": 25},
        {"brand": "Suntree", "model": "SRD-30 1000V 30A", "voltage_rating_v": 1000, "current_rating_a": 30},
        {"brand": "Projoy", "model": "PEV-1500V 30A", "voltage_rating_v": 1500, "current_rating_a": 30},
    ]


def get_ac_breaker_candidates(min_current_a: float = 16.0, phases: int = 1) -> List[Dict]:
    """Finds matching AC circuit breakers (MCB / MCCB)."""
    ratings = [16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250]
    poles = "2P" if phases == 1 else "4P"
    return [{"brand": "Schneider / ABB", "model": f"{r}A {poles} {'MCB' if r <= 63 else 'MCCB'}", "current_rating_a": r, "type": "MCB" if r <= 63 else "MCCB"} for r in ratings if r >= min_current_a]


def get_ac_isolator_candidates(min_current_a: float = 16.0, phases: int = 3) -> List[Dict]:
    """Finds matching AC isolators for the given current and phase."""
    md = load_master_data()
    isolators = md.get("ac_isolators", [])
    req_poles = "4P" if phases == 3 else "2P"
    matches = [
        iso for iso in isolators
        if iso["rated_current_a"] >= min_current_a and (iso.get("phases") == phases or iso.get("poles") == req_poles)
    ]
    matches.sort(key=lambda x: x["rated_current_a"])
    return matches


def get_lockable_isolator_candidates(min_current_a: float = 16.0, phases: int = 3) -> List[Dict]:
    """Finds matching utility lockable isolator options."""
    md = load_master_data()
    isolators = md.get("lockable_isolators", [])
    req_poles = "4P" if phases == 3 else "2P"
    matches = [
        iso for iso in isolators
        if iso["rated_current_a"] >= min_current_a and (iso.get("phases") == phases or iso.get("poles") == req_poles)
    ]
    matches.sort(key=lambda x: x["rated_current_a"])
    return matches


def get_ac_spd_candidates(phases: int = 3) -> List[Dict]:
    """Finds matching AC SPDs for single or three-phase systems."""
    md = load_master_data()
    spds = md.get("ac_spds", [])
    matches = [s for s in spds if s.get("phases") == phases]
    return matches


def evaluate_meter_rule(ac_power_kw: float) -> Dict[str, Any]:
    """
    Evaluates utility/company meter policy for the project capacity.
    Applies explicit rule sources:
      1-5 kW: Single Phase (COMPANY_STANDARD)
      6-20 kW: 3-Phase 30A (COMPANY_STANDARD)
      21-40 kW: 3-Phase 60A (COMPANY_STANDARD)
      >40 kW: CEB / Utility Assessment Required (MANUAL_REVIEW_REQUIRED)
    """
    md = load_master_data()
    rules = md.get("meter_rules", [])

    for r in rules:
        if r["capacity_min_kw"] <= ac_power_kw <= r["capacity_max_kw"]:
            if r.get("rule_source") == RULE_SOURCE_MANUAL_REVIEW:
                return {
                    "status": "MANUAL_REVIEW",
                    "ac_power_kw": ac_power_kw,
                    "meter_type": r["meter_type"],
                    "rating": r["rating"],
                    "phases": r["phases"],
                    "ct_required": r["ct_required"],
                    "rule_source": RULE_SOURCE_MANUAL_REVIEW,
                    "note": "Capacity exceeds 40 kW threshold — formal CEB / Utility interconnection assessment and meter allocation required. Do not assume automated meter sizing."
                }
            else:
                return {
                    "status": "PASS",
                    "ac_power_kw": ac_power_kw,
                    "meter_type": r["meter_type"],
                    "rating": r["rating"],
                    "phases": r["phases"],
                    "ct_required": r["ct_required"],
                    "rule_source": r.get("rule_source", RULE_SOURCE_COMPANY),
                    "note": f"Meter assigned under installer standard policy ({r.get('rule_source')})."
                }

    return {
        "status": "MANUAL_REVIEW",
        "ac_power_kw": ac_power_kw,
        "meter_type": "CEB / Utility Assessment Required",
        "rating": "Utility Discretion",
        "phases": 3,
        "ct_required": True,
        "rule_source": RULE_SOURCE_MANUAL_REVIEW,
        "note": "Engineering Review Required."
    }
