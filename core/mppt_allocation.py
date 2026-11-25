"""
core/mppt_allocation.py — MPPT String Allocation & Electrical Validation Engine
Distributes photovoltaic strings across inverter MPPT trackers, calculates per-tracker currents
(Imp and Isc), verifies voltage limits, hardware input terminals, and inverter capacities.
Authored by Eng. Aashir © 2026.
"""
from typing import Dict, List, Optional, Any
from .string_sizing import rnd, cold_voc, hot_vmp, cold_vmp
from .models import Inverter, Panel


def allocate_mppt_comprehensive(
    inverter: Inverter,
    total_strings: int = 0,
    panels_per_string: int = 0,
    panel: Optional[Panel] = None,
    t_min: float = 15.0,
    t_max: float = 45.0,
    num_inverters: int = 1,
    **kwargs
) -> Dict[str, Any]:
    """
    Comprehensive MPPT Allocation calculation engine.
    Calculates per-MPPT Operating Current (Imp), Short-Circuit Current (Isc), Operating Voltages,
    and checks against hardware inputs, MPPT voltage windows, and current limits.
    """
    if "t_min_c" in kwargs:
        t_min = kwargs["t_min_c"]
    if "t_max_c" in kwargs:
        t_max = kwargs["t_max_c"]
    if "panel" in kwargs and panel is None:
        panel = kwargs["panel"]
    if "total_strings" in kwargs and total_strings == 0:
        total_strings = kwargs["total_strings"]
    if "panels_per_string" in kwargs and panels_per_string == 0:
        panels_per_string = kwargs["panels_per_string"]
    if "num_inverters" in kwargs:
        num_inverters = kwargs["num_inverters"]
    num_inverters = max(1, num_inverters)
    if total_strings <= 0:
        return {
            "valid": False,
            "status": "FAIL",
            "message": "Total strings must be greater than 0.",
            "allocation_table": [],
            "max_mppt_current_a": 0.0,
            "max_mppt_isc_a": 0.0,
            "total_dc_current_a": 0.0,
            "max_strings_per_mppt": 0
        }

    base_strings_per_inv = total_strings // num_inverters
    rem_inv_strings = total_strings % num_inverters

    all_table_rows = []
    has_failure = False
    has_warning = False
    failure_reasons = []
    warnings = []

    global_max_mppt_current = 0.0
    global_max_mppt_isc = 0.0
    global_total_dc_current = 0.0
    global_max_str_per_mppt = 0

    # Calculate voltage extremes for this string configuration
    vmp_h_mod, _ = hot_vmp(panel, t_max)
    vmp_c_mod, _ = cold_vmp(panel, t_min)
    voc_c_mod = cold_voc(panel, t_min)

    v_string_vmp_hot = rnd(vmp_h_mod * panels_per_string, 1)
    v_string_vmp_cold = rnd(vmp_c_mod * panels_per_string, 1)
    v_string_voc_cold = rnd(voc_c_mod * panels_per_string, 1)

    # Inverter voltage checks
    voc_exceeded = v_string_voc_cold > inverter.max_dc_voltage_v
    vmp_low = v_string_vmp_hot < inverter.mppt_voltage_min_v
    vmp_high = v_string_vmp_cold > inverter.mppt_voltage_max_v

    if voc_exceeded:
        has_failure = True
        failure_reasons.append(f"Cold Voc ({v_string_voc_cold}V) exceeds Inverter Max DC Voltage ({inverter.max_dc_voltage_v}V).")
    if vmp_low:
        has_failure = True
        failure_reasons.append(f"Hot Vmp ({v_string_vmp_hot}V) is below Inverter Min MPPT Voltage ({inverter.mppt_voltage_min_v}V).")
    if vmp_high:
        has_failure = True
        failure_reasons.append(f"Cold Vmp ({v_string_vmp_cold}V) exceeds Inverter Max MPPT Voltage ({inverter.mppt_voltage_max_v}V).")

    for inv_idx in range(num_inverters):
        inv_label = f"Inverter {inv_idx + 1}"
        strings_for_this_inv = base_strings_per_inv + (1 if inv_idx < rem_inv_strings else 0)

        mppt_count = inverter.mppt_count
        max_inputs_per_mppt = inverter.string_inputs_per_mppt
        base_mppt_strings = strings_for_this_inv // mppt_count
        rem_mppt_strings = strings_for_this_inv % mppt_count

        inv_dc_current = 0.0

        for mppt_i in range(mppt_count):
            assigned_strings = base_mppt_strings + (1 if mppt_i < rem_mppt_strings else 0)
            mppt_label = f"MPPT {mppt_i + 1}"

            if assigned_strings > global_max_str_per_mppt:
                global_max_str_per_mppt = assigned_strings

            if assigned_strings == 0:
                mppt_curr = 0.0
                mppt_isc = 0.0
                m_status = "PASS (Unused)"
                v_display = f"{v_string_vmp_hot} V"
            else:
                mppt_curr = rnd(assigned_strings * panel.imp, 2)
                mppt_isc = rnd(assigned_strings * panel.isc, 2)
                inv_dc_current += mppt_curr

                if mppt_curr > global_max_mppt_current:
                    global_max_mppt_current = mppt_curr
                if mppt_isc > global_max_mppt_isc:
                    global_max_mppt_isc = mppt_isc

                # Check tracker limits
                isc_limit_exceeded = mppt_isc > inverter.max_isc_per_mppt_a
                clipping_warning = mppt_curr > inverter.max_input_current_per_mppt_a
                terminals_exceeded = assigned_strings > max_inputs_per_mppt

                v_display = f"{v_string_vmp_hot}V - {v_string_voc_cold}V"

                if voc_exceeded or vmp_low or vmp_high or isc_limit_exceeded or terminals_exceeded:
                    m_status = "FAIL"
                    has_failure = True
                    if isc_limit_exceeded:
                        failure_reasons.append(f"{inv_label} {mppt_label}: Isc ({mppt_isc}A) > Max Inverter Isc ({inverter.max_isc_per_mppt_a}A).")
                    if terminals_exceeded:
                        failure_reasons.append(f"{inv_label} {mppt_label}: {assigned_strings} strings exceed physical {max_inputs_per_mppt} inputs/MPPT.")
                elif clipping_warning:
                    m_status = "WARNING (Clipping)"
                    has_warning = True
                    warnings.append(f"{inv_label} {mppt_label}: Imp ({mppt_curr}A) slightly exceeds nominal input ({inverter.max_input_current_per_mppt_a}A); safe clipping will occur.")
                else:
                    m_status = "PASS"

            all_table_rows.append({
                "Inverter": inv_label,
                "MPPT": mppt_label,
                "Strings": assigned_strings,
                "Panels/String": panels_per_string if assigned_strings > 0 else 0,
                "MPPT Current": f"{mppt_curr:.2f} A",
                "MPPT Isc": f"{mppt_isc:.2f} A",
                "Voltage": v_display,
                "Status": m_status
            })

        global_total_dc_current += inv_dc_current

        # Check inverter total DC current limit if specified
        if hasattr(inverter, "max_total_dc_current_a") and inverter.max_total_dc_current_a:
            if inv_dc_current > inverter.max_total_dc_current_a:
                has_failure = True
                failure_reasons.append(f"{inv_label}: Total DC Current ({inv_dc_current:.1f}A) exceeds inverter maximum DC limit ({inverter.max_total_dc_current_a}A).")

    is_valid = not has_failure
    status_label = "FAIL" if has_failure else ("WARNING" if has_warning else "PASS")
    
    if not is_valid:
        msg = "No valid MPPT allocation found — change string configuration or inverter selection."
    elif has_warning:
        msg = "Valid MPPT allocation achieved with operational power clipping warnings."
    else:
        msg = "Valid and fully compliant MPPT allocation verified."

    return {
        "valid": is_valid,
        "status": status_label,
        "message": msg,
        "failure_reasons": list(set(failure_reasons)),
        "warnings": list(set(warnings)),
        "allocation_table": all_table_rows,
        "max_mppt_current_a": global_max_mppt_current,
        "max_mppt_isc_a": global_max_mppt_isc,
        "total_dc_current_a": round(global_total_dc_current, 2),
        "max_strings_per_mppt": global_max_str_per_mppt,
        "string_voc_cold_v": v_string_voc_cold,
        "string_vmp_hot_v": v_string_vmp_hot,
        "string_vmp_cold_v": v_string_vmp_cold
    }


def allocate_mppt_for_inverter(inverter, strings_for_this_inverter, unit_number=1):
    """
    Backward-compatible tracker allocation for a single inverter unit.
    """
    mppt_count = inverter.mppt_count
    max_inputs_per_mppt = inverter.string_inputs_per_mppt
    max_inverter_strings = mppt_count * max_inputs_per_mppt

    base = strings_for_this_inverter // mppt_count
    remainder = strings_for_this_inverter % mppt_count

    allocation = []
    exceeded_hardware_limit = False
    
    for i in range(mppt_count):
        strings = base + (1 if i < remainder else 0)
        is_over = strings > max_inputs_per_mppt
        if is_over:
            exceeded_hardware_limit = True
        allocation.append({
            "mppt_index": i + 1,
            "strings_assigned": strings,
            "max_inputs": max_inputs_per_mppt,
            "hardware_ok": not is_over
        })

    balanced = (remainder == 0)
    warnings = []
    if not balanced:
        warnings.append(
            f"Uneven MPPT allocation on {inverter.manufacturer} {inverter.model} "
            f"(unit {unit_number}): {remainder} of {mppt_count} MPPTs carry one extra string."
        )

    if exceeded_hardware_limit:
        warnings.append(
            f"HARDWARE LIMIT EXCEEDED on {inverter.manufacturer} {inverter.model} "
            f"(unit {unit_number}): Some MPPTs require {base + 1} strings, but hardware only supports "
            f"{max_inputs_per_mppt} inputs/MPPT. External combiner box required."
        )

    return {
        "unit_number": unit_number,
        "inverter_id": inverter.id,
        "mppt_count": mppt_count,
        "string_inputs_per_mppt": max_inputs_per_mppt,
        "max_inverter_strings": max_inverter_strings,
        "strings_total": strings_for_this_inverter,
        "allocation": allocation,
        "balanced": balanced,
        "exceeded_hardware_limit": exceeded_hardware_limit,
        "warning": " | ".join(warnings) if warnings else None,
        "warnings": warnings,
    }


def allocate_mppt(breakdown, strings_total):
    """
    Backward-compatible string distributor across a breakdown of inverters.
    """
    total_units = sum(b["quantity"] for b in breakdown)
    if total_units <= 0:
        return {"per_inverter_unit": [], "warnings": ["No inverter units available."]}

    base_strings_per_unit = strings_total // total_units
    remainder_units = strings_total % total_units

    per_inverter_unit = []
    warnings = []
    unit_index = 0

    for b in breakdown:
        inverter, quantity = b["inverter"], b["quantity"]
        for _ in range(quantity):
            strings_for_unit = base_strings_per_unit + (1 if unit_index < remainder_units else 0)
            result = allocate_mppt_for_inverter(inverter, strings_for_unit, unit_index + 1)
            per_inverter_unit.append(result)
            if result["warnings"]:
                warnings.extend(result["warnings"])
            unit_index += 1

    return {"per_inverter_unit": per_inverter_unit, "warnings": warnings}
