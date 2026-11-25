"""
core/meter_selection.py — Bi-directional Net Metering & Grid Connection Sizing
Complies with IEC 62053-22, IEC 61869-2, and Master Data Meter Policy:
  - 1–5 kW: Single Phase (COMPANY_STANDARD)
  - 6–20 kW: 3-Phase 30A (COMPANY_STANDARD)
  - 21–40 kW: 3-Phase 60A (COMPANY_STANDARD)
  - >40 kW: CEB / Utility Assessment Required (MANUAL_REVIEW_REQUIRED)
Authored by Eng. Aashir © 2026.
"""
import math
from typing import Dict, Any
from .string_sizing import rnd
from .master_data import (
    evaluate_meter_rule,
    RULE_SOURCE_COMPANY,
    RULE_SOURCE_CEB,
    RULE_SOURCE_MANUAL_REVIEW
)

CT_STANDARD_PRIMARY_RATINGS_A = [
    50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 800, 1000, 1200, 1500, 2000, 2500, 3000
]


def select_meter_system(
    ac_power_kw: float,
    grid_voltage_v: float = 400.0,
    phases: int = 3,
    power_factor: float = 0.95,
    safety_factor: float = 1.25,
    scheme_type: str = "Net Metering"
) -> Dict[str, Any]:
    """
    Evaluates utility/company meter policy for the project capacity.
    Integrates Master Data rules with explicit sourcing:
      1-5 kW: Single Phase (COMPANY_STANDARD)
      6-20 kW: 3-Phase 30A (COMPANY_STANDARD)
      21-40 kW: 3-Phase 60A (COMPANY_STANDARD)
      >40 kW: CEB / Utility Assessment Required (MANUAL_REVIEW_REQUIRED)
    """
    v_nom = max(100.0, grid_voltage_v)
    pf = min(1.0, max(0.70, power_factor))
    
    # Check Master Data Rule Policy
    rule_eval = evaluate_meter_rule(ac_power_kw)
    
    # Calculate electrical current values
    calc_phases = rule_eval.get("phases", phases)
    if calc_phases == 3:
        rated_current_a = (ac_power_kw * 1000.0) / (math.sqrt(3.0) * v_nom * pf)
    else:
        rated_current_a = (ac_power_kw * 1000.0) / (v_nom * pf)

    rated_current_a = rnd(rated_current_a, 2)
    design_current_a = rnd(rated_current_a * safety_factor, 2)

    if rule_eval.get("rule_source") == RULE_SOURCE_MANUAL_REVIEW or ac_power_kw > 40.0:
        return {
            "status": "MANUAL_REVIEW",
            "ac_power_kw": ac_power_kw,
            "grid_voltage_v": v_nom,
            "phases": 3,
            "rated_current_a": rated_current_a,
            "design_current_a": design_current_a,
            "connection_type": "Utility Discretion (CT / VT Operated Substation Feeder)",
            "meter_type": "CEB / Utility Assessment Required",
            "rating": "Utility Discretion",
            "ct_required": True,
            "ct_ratio": f"{int(math.ceil(design_current_a / 50.0) * 50)}/5 A (Subject to CEB Approval)",
            "ct_accuracy_class": "Class 0.2s / 0.5s",
            "meter_accuracy_class": "Class 0.2s / Class 0.5s (IEC 62053-22)",
            "rated_meter_current": "3×230/400V, -/5A",
            "communication_protocol": "DLMS / COSEM GSM/GPRS Modem",
            "scheme_type": scheme_type,
            "rule_source": RULE_SOURCE_MANUAL_REVIEW,
            "applicable_standards": "CEB Guide for Grid Interconnection, IEC 62053-22",
            "message": "Capacity exceeds 40 kW threshold — formal CEB / Utility interconnection assessment and meter allocation required. Do not assume automated meter sizing.",
            "show_calculation": {
                "capacity": f"{ac_power_kw} kW > 40 kW threshold",
                "rule_source": RULE_SOURCE_MANUAL_REVIEW,
                "current_formula": f"I_rated = ({ac_power_kw} * 1000) / (sqrt(3) * {v_nom} * {pf}) = {rated_current_a} A",
                "design_current": f"I_design = {rated_current_a} * {safety_factor} = {design_current_a} A"
            }
        }
    
    # Under 40 kW standard policy
    status_label = "PASS"
    ct_required = rule_eval.get("ct_required", False)
    connection_type = "Direct Connected (Whole Current)" if not ct_required else "CT-Operated"
    
    return {
        "status": status_label,
        "ac_power_kw": ac_power_kw,
        "grid_voltage_v": v_nom,
        "phases": calc_phases,
        "rated_current_a": rated_current_a,
        "design_current_a": design_current_a,
        "connection_type": connection_type,
        "meter_type": rule_eval["meter_type"],
        "rating": rule_eval["rating"],
        "ct_required": ct_required,
        "ct_ratio": "N/A (Direct Connected)" if not ct_required else f"{int(math.ceil(design_current_a / 50.0) * 50)}/5 A",
        "ct_accuracy_class": "Class 0.5 / 5VA" if ct_required else "N/A",
        "meter_accuracy_class": "Class 1.0 (IEC 62053-21)",
        "rated_meter_current": rule_eval["rating"],
        "communication_protocol": "Optical Port / RS-485 Modbus",
        "scheme_type": scheme_type,
        "rule_source": rule_eval.get("rule_source", RULE_SOURCE_COMPANY),
        "applicable_standards": "IEC 62053-21, BS 7671, Company Interconnection Standard",
        "message": f"Assigned {rule_eval['meter_type']} under standard installer policy ({rule_eval.get('rule_source')}).",
        "show_calculation": {
            "capacity_bracket": f"Target AC {ac_power_kw} kW",
            "assigned_meter": f"{rule_eval['meter_type']} ({rule_eval['rating']})",
            "rule_source": rule_eval.get("rule_source", RULE_SOURCE_COMPANY),
            "design_current": f"I_rated = {rated_current_a} A | I_design = {design_current_a} A"
        }
    }
