"""
Engine orchestrator — runs the full engineering design pipeline:
combination search -> string sizing -> mppt allocation -> current checks
-> dc/ac ratio -> physical layout -> multi-criteria ranking.
"""
from .combination_search import find_exact_combinations, find_combinations_with_tolerance
from .string_sizing import panels_per_string_range, voltage_check, rnd
from .mppt_allocation import allocate_mppt
from .current_check import current_check
from .dc_ac_ratio import dc_ac_ratio
from .physical_layout import physical_layout
from .ranking import rank_configs
from .cable_sizing import select_cable, voltage_drop_estimate
from .protection_sizing import select_protective_device, select_busbar


def breakdown_summary(breakdown):
    return " + ".join(
        f'{b["quantity"]} x {b["inverter"].manufacturer} {b["inverter"].model} '
        f'({b["inverter"].rated_ac_power_kw}kW)'
        for b in breakdown
    )


def evaluate_combination(panel, project, breakdown):
    """
    Evaluates a single multi-inverter combination.
    Ensures string length and electrical limits are verified across ALL inverters in the mix.
    """
    if not breakdown:
        return {"overall_status": "FAIL", "fail_reason": "Inverter breakdown cannot be empty."}

    # Verify string length range across all inverters in breakdown
    min_allowable_panels = 1
    max_allowable_panels = 999
    primary_inverter = breakdown[0]["inverter"]
    primary_rng = None

    for b in breakdown:
        inv = b["inverter"]
        rng = panels_per_string_range(panel, inv, project)
        if not rng["valid"]:
            return {
                "overall_status": "FAIL",
                "fail_reason": (
                    f"No valid panels-per-string range for {inv.manufacturer} {inv.model} "
                    f"(min {rng['min_panels_per_string']} > max {rng['max_panels_per_string']})."
                ),
            }
        min_allowable_panels = max(min_allowable_panels, rng["min_panels_per_string"])
        max_allowable_panels = min(max_allowable_panels, rng["max_panels_per_string"])
        if primary_rng is None:
            primary_rng = rng

    if min_allowable_panels > max_allowable_panels:
        return {
            "overall_status": "FAIL",
            "fail_reason": (
                f"Incompatible inverter mix: No common string length exists across models "
                f"({min_allowable_panels} > {max_allowable_panels})."
            ),
        }

    panels_per_string = max_allowable_panels

    # Verify voltage limits for all inverters in the breakdown
    v_check = None
    for b in breakdown:
        inv = b["inverter"]
        vc = voltage_check(panel, inv, project, panels_per_string)
        if vc["cold"]["status"] == "FAIL" or vc["hot"]["status"] == "FAIL":
            return {
                "overall_status": "FAIL",
                "fail_reason": f"Voltage check failed on {inv.manufacturer} {inv.model}.",
            }
        if v_check is None:
            v_check = vc

    unit_count = sum(b["quantity"] for b in breakdown)
    ac_capacity_kw = sum(b["inverter"].rated_ac_power_kw * b["quantity"] for b in breakdown)

    target_dc_kwp = ac_capacity_kw * project.dc_ac_ratio_preferred
    raw_qty = round((target_dc_kwp * 1000) / panel.rated_power_wp / panels_per_string) * panels_per_string
    panel_qty = min(project.panel_available_qty, raw_qty)

    if panel_qty <= 0:
        return {"overall_status": "FAIL", "fail_reason": "Insufficient panel quantity available."}

    strings_total = panel_qty // panels_per_string

    mppt_result = allocate_mppt(breakdown, strings_total)

    max_strings_on_one_mppt = max(
        a["strings_assigned"]
        for u in mppt_result["per_inverter_unit"]
        for a in u["allocation"]
    ) if mppt_result["per_inverter_unit"] else 0

    cur_check = current_check(panel, primary_inverter, max_strings_on_one_mppt)
    if cur_check["status"] == "FAIL":
        return {
            "overall_status": "FAIL",
            "fail_reason": "Current check failed (exceeds MPPT operating Imp or short-circuit Isc limit).",
        }

    dc_ac = dc_ac_ratio(panel_qty, panel.rated_power_wp, breakdown, project)
    if dc_ac["status"] == "FAIL":
        return {"overall_status": "FAIL", "fail_reason": "DC/AC ratio outside acceptable range."}

    layout = physical_layout(panel, project, panel_qty)
    if layout["status"] == "NOT_FITTING":
        return {"overall_status": "FAIL", "fail_reason": "Physical layout cannot fit required panel quantity."}

    total_mppts = sum(u["mppt_count"] for u in mppt_result["per_inverter_unit"])
    used_mppt_strings = sum(
        a["strings_assigned"] for u in mppt_result["per_inverter_unit"] for a in u["allocation"]
    )
    max_possible_strings_on_mppts = total_mppts * primary_inverter.string_inputs_per_mppt
    avg_mppt_utilization_pct = rnd((used_mppt_strings / max_possible_strings_on_mppts) * 100, 1) if max_possible_strings_on_mppts > 0 else 0

    area_utilization_pct = rnd((layout["required_panel_qty"] / layout["total_fitting"]) * 100, 1) if layout["total_fitting"] > 0 else 0

    warnings = []
    if primary_rng and primary_rng["vmp_hot_used_pmax_fallback"]:
        warnings.append({
            "code": "TEMP_COEFF_FALLBACK",
            "message": "temp_coeff_vmp not on datasheet — used temp_coeff_pmax as approximation.",
        })
    for w in mppt_result["warnings"]:
        warnings.append({"code": "UNEVEN_MPPT", "message": w})
    if v_check["cold"]["status"] == "WARNING":
        warnings.append({
            "code": "VOLTAGE_MARGIN",
            "message": f'Cold string Voc at {v_check["cold"]["margin_pct"]}% of max DC voltage — within WARNING band.',
        })
    if cur_check["status"] == "WARNING":
        warnings.append({
            "code": "CURRENT_MARGIN",
            "message": f'String current within 90-100% of MPPT limit — within WARNING band.',
        })
    if dc_ac["status"] == "WARNING":
        warnings.append({
            "code": "DCAC_MARGIN",
            "message": f'DC/AC ratio {dc_ac["ratio"]} is outside preferred range but within WARNING grace zone.',
        })

    return {
        "overall_status": "PASS",
        "breakdown": breakdown,
        "inverter_breakdown": breakdown_summary(breakdown),
        "unit_count": unit_count,
        "ac_capacity_kw": ac_capacity_kw,
        "panel_qty": panel_qty,
        "panels_per_string": panels_per_string,
        "strings_total": strings_total,
        "voltage_check": v_check,
        "current_check": cur_check,
        "dc_ac": dc_ac,
        "layout": layout,
        "mppt_allocation": mppt_result,
        "avg_mppt_utilization_pct": avg_mppt_utilization_pct,
        "area_utilization_pct": area_utilization_pct,
        "warnings": warnings,
    }


def evaluate_project(panel, project, inverter_options, max_combinations=200, top_n=5):
    """
    Searches for exact-match inverter combinations and evaluates/ranks valid designs.
    """
    raw_combos = find_exact_combinations(
        inverter_options, project.target_ac_capacity_kw, max_combinations=max_combinations
    )

    valid_configs = []
    rejected_configs = []

    for combo in raw_combos:
        evaluation = evaluate_combination(panel, project, combo)
        if evaluation["overall_status"] == "PASS":
            valid_configs.append(evaluation)
        else:
            rejected_configs.append({
                "breakdown": breakdown_summary(combo),
                "reason": evaluation.get("fail_reason", "Failed validation check."),
            })

    ranked_configs = rank_configs(valid_configs, project.dc_ac_ratio_preferred)

    return {
        "target_ac_kw": project.target_ac_capacity_kw,
        "total_combos_found": len(raw_combos),
        "valid_count": len(valid_configs),
        "valid": ranked_configs[:top_n],
        "rejected": rejected_configs,
    }


def evaluate_project_with_tolerance(panel, project, inverter_options, tolerance_pct=5.0, mode="closest", max_combinations=200, top_n=5):
    """
    Searches for inverter combinations within a specified tolerance of target AC power.
    """
    raw_combos = find_combinations_with_tolerance(
        inverter_options, project.target_ac_capacity_kw, tolerance_pct=tolerance_pct, max_combinations=max_combinations, mode=mode
    )

    valid_configs = []
    rejected_configs = []

    for combo in raw_combos:
        evaluation = evaluate_combination(panel, project, combo)
        if evaluation["overall_status"] == "PASS":
            valid_configs.append(evaluation)
        else:
            rejected_configs.append({
                "breakdown": breakdown_summary(combo),
                "reason": evaluation.get("fail_reason", "Failed validation check."),
            })

    ranked_configs = rank_configs(valid_configs, project.dc_ac_ratio_preferred)

    return {
        "target_ac_kw": project.target_ac_capacity_kw,
        "tolerance_pct": tolerance_pct,
        "mode": mode,
        "total_combos_found": len(raw_combos),
        "valid_count": len(valid_configs),
        "valid": ranked_configs[:top_n],
        "rejected": rejected_configs,
    }
