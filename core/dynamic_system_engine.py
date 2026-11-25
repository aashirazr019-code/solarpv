"""
core/dynamic_system_engine.py — Dynamic Solar System Design Engine
Comprehensive rule-based calculation engine enforcing the strict engineering dependency chain:
Required Capacity -> Inverter Combination -> Panel Qty -> String Config -> MPPT Allocation
-> DC Protection -> DC Cable -> Individual AC Protection/Cable -> Main AC Protection/Cable
-> Dynamic Earthing -> Dynamic BOM/BOQ.

Designed & Engineered by Eng. Aashir (c) 2026. All Rights Reserved.
Standards Applied:
  - BS 7671:2008 Requirements for Electrical Installations
  - Kelani Cables Table A1 Current Carrying Capacities
  - IEC 60364-7-712 Solar Photovoltaic Power Supply Systems
  - IEC 60269-6 Low-voltage Fuses for PV Protection (gPV)
  - BS 7430 Code of Practice for Protective Earthing
  - CEB / LECO Grid Interconnection Standards
"""
import math
from typing import List, Dict, Any, Optional, Tuple

from .models import Panel, Inverter, Project, SpacingConfig
from .inverter_catalog import get_all_catalog_inverters, get_available_inverters, get_inverter_by_model
from .string_sizing import cold_voc, hot_vmp, cold_vmp, rnd
from .mppt_allocation import allocate_mppt_for_inverter
from .current_check import current_check
from .cable_sizing import select_cable
from .electrical_data import (
    CABLE_AMPACITY_TABLE,
    MCB_STANDARD_RATINGS_A,
    MCCB_STANDARD_RATINGS_A,
    BUSBAR_STANDARD_RATINGS_A,
    COPPER_RESISTIVITY_OHM_MM2_PER_M_AT_70C
)
from .earthing import calculate_earth_rod_resistance, calculate_earth_rods_required


# ---------------------------------------------------------------------------
# 1. INVERTER COMBINATION GENERATOR & 6-PRIORITY RANKING
# ---------------------------------------------------------------------------

def generate_inverter_combinations(
    target_kw: float,
    grid_phase: int = 3,
    max_inverters: Optional[int] = None,   # Backwards-compatible: maps to max_distinct_models
    max_results: int = 25,
    allow_oversizing_pct: Optional[float] = None,
    max_distinct_models: int = 4,
    max_total_units: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Finds and ranks feasible inverter combinations for ANY target AC capacity (5 kW -> 1 MW+).
    Supports combinations containing up to 4 DIFFERENT inverter model entries with arbitrary unit quantities
    (e.g., 3 x 100 kW + 1 x 60 kW + 1 x 40 kW = 400 kW, 5 physical units).
    
    Ranks combinations using the 6 engineering priorities:
      Priority 1: Exact Capacity (P_inv == P_req)
      Priority 2: Electrical Compatibility (grid phase, voltage, MPPT limits)
      Priority 3: Minimum Oversizing (smallest excess capacity above target)
      Priority 4: Minimum Number of Inverters / clean switchboard arrangement
      Priority 5: Optimal DC/AC Utilization & MPPT balance
      Priority 6: Available Models in database
    """
    if target_kw <= 0:
        return []

    # Map legacy max_inverters to max_distinct_models (rule of 4 distinct models)
    if max_inverters is not None and max_inverters <= 4:
        max_distinct_models = max_inverters

    # Filter catalog by phase and availability
    available_inverters = get_available_inverters(phase=grid_phase, only_available=True)
    if not available_inverters:
        available_inverters = get_all_catalog_inverters()

    # Deduplicate by (rated_ac_power_kw, grid_type) preferring SE / commercial models
    seen_kw = {}
    for inv in available_inverters:
        kw = inv.rated_ac_power_kw
        if kw not in seen_kw:
            seen_kw[kw] = inv
        elif "SE" in inv.model and "SE" not in seen_kw[kw].model:
            seen_kw[kw] = inv
    unique_inverters = sorted(seen_kw.values(), key=lambda x: x.rated_ac_power_kw, reverse=True)

    if not unique_inverters:
        return []

    # Adaptive max_total_units: allows multi-unit fleets for large plants (e.g. 5, 6, 8, 10, 12 units)
    if max_total_units is None:
        largest_kw = unique_inverters[0].rated_ac_power_kw
        max_total_units = max(6, math.ceil(target_kw / max(largest_kw, 1.0)) + 4)
        max_total_units = min(max_total_units, 16)

    # Adaptive oversizing allowance
    if allow_oversizing_pct is None:
        if target_kw <= 20.0:
            allow_oversizing_pct = 20.0
        elif target_kw <= 100.0:
            allow_oversizing_pct = 25.0
        else:
            allow_oversizing_pct = 35.0

    max_allowed_kw = target_kw * (1.0 + allow_oversizing_pct / 100.0)
    max_allowed_kw = max(max_allowed_kw, target_kw + 2.0)

    # Adaptive undersizing tolerance
    if target_kw <= 50.0:
        undersize_tol = 0.05
    elif target_kw <= 200.0:
        undersize_tol = 0.08
    else:
        undersize_tol = 0.10
    min_allowed_kw = target_kw * (1.0 - undersize_tol)

    raw_combos = []

    # Combinatorial search: up to max_distinct_models with unit counts >= 1
    def search_models(start_idx: int, chosen_models: List[Inverter], current_sum: float, current_units: int, current_counts: List[int]):
        if min_allowed_kw <= current_sum <= max_allowed_kw and current_counts:
            raw_combos.append((list(zip(chosen_models, current_counts)), current_sum, current_units))

        if len(chosen_models) == max_distinct_models or current_units >= max_total_units or current_sum >= max_allowed_kw:
            return

        for i in range(start_idx, len(unique_inverters)):
            inv = unique_inverters[i]
            max_add = min(
                max_total_units - current_units,
                int(math.ceil((max_allowed_kw - current_sum) / inv.rated_ac_power_kw))
            )
            for q in range(1, max_add + 1):
                new_sum = current_sum + q * inv.rated_ac_power_kw
                if new_sum > max_allowed_kw:
                    break
                chosen_models.append(inv)
                current_counts.append(q)
                search_models(i + 1, chosen_models, new_sum, current_units + q, current_counts)
                chosen_models.pop()
                current_counts.pop()

    search_models(0, [], 0.0, 0, [])

    if not raw_combos:
        closest = min(unique_inverters, key=lambda x: abs(x.rated_ac_power_kw - target_kw))
        qty = max(1, int(round(target_kw / closest.rated_ac_power_kw)))
        raw_combos.append(([ (closest, qty) ], closest.rated_ac_power_kw * qty, qty))

    # Format, deduplicate, score, and rank
    formatted_combinations = []
    seen_signatures = set()

    for combo_items, total_ac_kw, total_units in raw_combos:
        sig = tuple(sorted((inv.model, q) for inv, q in combo_items))
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)

        breakdown = [{"inverter": inv, "quantity": q, "unit_kw": inv.rated_ac_power_kw} for inv, q in combo_items]
        breakdown.sort(key=lambda x: x["unit_kw"], reverse=True)

        diff_kw = total_ac_kw - target_kw
        is_exact = abs(diff_kw) < 0.001
        num_distinct = len(breakdown)

        # Build readable label: e.g. "3 x 100 kW + 60 kW + 40 kW = 400.0 kW AC"
        parts = [f"{it['quantity']} \u00d7 {it['unit_kw']:.0f} kW" if it['quantity'] > 1 else f"{it['unit_kw']:.0f} kW" for it in breakdown]
        combo_label = " + ".join(parts) + f" ({total_ac_kw:.1f} kW AC)"

        # Priority scoring calculation (Lower score = Better rank)
        p1 = 0.0 if is_exact else (abs(diff_kw) * 15.0 if diff_kw > 0 else abs(diff_kw) * 45.0)
        p2 = (num_distinct - 1) * 20.0
        p3 = total_units * 8.0
        p4 = -30.0 if num_distinct == 1 else 0.0

        score = p1 + p2 + p3 + p4

        formatted_combinations.append({
            "label": combo_label,
            "total_ac_kw": rnd(total_ac_kw, 2),
            "deviation_kw": rnd(diff_kw, 2),
            "is_exact": is_exact,
            "inverter_count": total_units,
            "distinct_model_count": num_distinct,
            "breakdown": breakdown,
            "score": score
        })

    # Sort strictly by engineering priority score
    formatted_combinations.sort(key=lambda x: (
        not x["is_exact"],
        x["deviation_kw"] < 0,
        x["distinct_model_count"],
        x["inverter_count"],
        abs(x["deviation_kw"]),
        x["score"]
    ))

    top_results = formatted_combinations[:max_results]
    for idx, item in enumerate(top_results):
        diff = item["deviation_kw"]
        distinct = item["distinct_model_count"]
        units = item["inverter_count"]

        if idx == 0:
            rank = "\u2b50 BEST MATCH (Recommended)"
            item["is_recommended"] = True
            expl = f"Optimal configuration: {item['total_ac_kw']:.0f} kW AC with {units} unit(s) across {distinct} standard model(s)."
        elif item["is_exact"] and distinct <= 2:
            rank = "BEST MATCH"
            item["is_recommended"] = False
            expl = f"Exact {item['total_ac_kw']:.0f} kW match with {units} unit(s) across {distinct} model(s)."
        elif item["is_exact"]:
            rank = "GOOD"
            item["is_recommended"] = False
            expl = f"Exact {item['total_ac_kw']:.0f} kW match using {distinct} model entries ({units} physical units)."
        elif abs(diff) <= target_kw * 0.05 and distinct <= 2:
            rank = "GOOD"
            item["is_recommended"] = False
            expl = f"Close match ({'+' if diff>0 else ''}{diff:.1f} kW) with clean {distinct}-model arrangement."
        elif abs(diff) <= target_kw * 0.12:
            rank = "ACCEPTABLE"
            item["is_recommended"] = False
            expl = f"Feasible configuration within engineering tolerance ({'+' if diff>0 else ''}{diff:.1f} kW)."
        else:
            rank = "WARNING"
            item["is_recommended"] = False
            expl = f"Oversized/undersized by {abs(diff):.1f} kW; verify substation and busbar limits."

        item["rank_tag"] = rank
        item["explanation"] = expl

    return top_results


def validate_inverter_combination(
    breakdown: List[Dict[str, Any]],
    target_kw: float,
    grid_phase: int = 3
) -> Dict[str, Any]:
    """
    Validates a manual or auto inverter combination against engineering limits.
    Supports up to 4 distinct inverter models with arbitrary physical units.
    Returns PASS / WARNING / FAIL and detailed reason messages.
    """
    if not breakdown:
        return {
            "is_valid": False,
            "status": "FAIL",
            "message": "No inverters in configuration.",
            "total_ac_kw": 0.0,
            "details": ["Please select at least one inverter."]
        }

    total_ac = sum(item["inverter"].rated_ac_power_kw * item["quantity"] for item in breakdown)
    total_units = sum(item["quantity"] for item in breakdown)
    distinct_models = len(breakdown)
    details = []
    status = "PASS"

    target_grid_type = "1-phase" if grid_phase == 1 else "3-phase"
    phase_mismatch = False

    for item in breakdown:
        inv: Inverter = item["inverter"]
        qty = item["quantity"]
        if inv.grid_type != target_grid_type:
            phase_mismatch = True
            details.append(f"Inverter {inv.model} is {inv.grid_type}, but project is {target_grid_type}.")

    if distinct_models > 4:
        status = "WARNING"
        details.append(f"Configuration contains {distinct_models} distinct inverter models (>4 recommended maximum).")

    diff = total_ac - target_kw
    if abs(diff) < 0.001:
        details.append(f"Capacity matches target {target_kw} kW exactly ({total_units} units total).")
    elif diff > 0:
        oversize_pct = (diff / target_kw) * 100
        if oversize_pct > 25.0:
            status = "WARNING"
            details.append(f"Inverter AC capacity ({total_ac:.1f} kW) exceeds target by {oversize_pct:.1f}% (>25%).")
        else:
            details.append(f"Inverter AC capacity is {total_ac:.1f} kW (+{oversize_pct:.1f}% oversizing).")
    else:
        undersize_pct = (-diff / target_kw) * 100
        status = "WARNING"
        details.append(f"Inverter AC capacity ({total_ac:.1f} kW) is undersized by {undersize_pct:.1f}%.")

    if phase_mismatch:
        status = "FAIL"

    is_valid = (status != "FAIL")
    msg = f"Valid configuration: {total_units} unit(s) across {distinct_models} model(s), {total_ac:.1f} kW AC total." if is_valid else "Configuration has critical warnings/errors."

    return {
        "is_valid": is_valid,
        "status": status,
        "message": msg,
        "total_ac_kw": rnd(total_ac, 2),
        "total_units": total_units,
        "distinct_models": distinct_models,
        "details": details
    }


def find_optimal_panel_and_string_config(
    target_ac_kw: float,
    inverter_breakdown: Optional[List[Dict[str, Any]]] = None,
    candidate_panels: Optional[List[Panel]] = None,
    project_params: Optional[Dict[str, Any]] = None,
    target_dc_ac_ratio: float = 1.30
) -> Dict[str, Any]:
    """
    Evaluates available panels in the library and finds the optimal practical panel
    and string configuration for the specified capacity and inverter combination.
    
    Evaluates whole-number panel combinations around target DC capacity (P_ac * 1.30),
    verifies thermal limits (-30°C cold Voc, 60°C hot Vmp) against inverter MPPT and max DC,
    checks MPPT current limits, and selects the solution with the cleanest string layout.
    """
    if inverter_breakdown is None:
        combos = generate_inverter_combinations(target_ac_kw, grid_phase=1 if target_ac_kw <= 5.0 else 3)
        if combos:
            inverter_breakdown = combos[0]["breakdown"]
        else:
            raise ValueError(f"No inverter combination could be generated for {target_ac_kw} kW.")

    if candidate_panels is None:
        try:
            from .project_state import get_approved_panels
            candidate_panels = get_approved_panels()
        except Exception:
            candidate_panels = []

    if not candidate_panels:
        raise ValueError("No candidate panels available for evaluation.")

    if project_params is None:
        project_params = {}

    min_temp = float(project_params.get("min_design_temp_c", -30.0))
    max_temp = float(project_params.get("max_design_temp_c", 60.0))

    target_dc_kwp = target_ac_kw * target_dc_ac_ratio
    evaluated_panels = []

    for panel in candidate_panels:
        total_panels_for_panel = 0
        total_strings_for_panel = 0
        total_dc_kwp_for_panel = 0.0
        all_inverters_valid = True
        inverter_configs = []

        for item in inverter_breakdown:
            inv: Inverter = item["inverter"]
            qty = item["quantity"]

            # Thermal voltages
            v_oc_cold = cold_voc(panel, min_temp)
            v_mp_hot, _ = hot_vmp(panel, max_temp)
            v_mp_cold, _ = cold_vmp(panel, min_temp)

            max_panels_voc = int(inv.max_dc_voltage_v // v_oc_cold) if v_oc_cold > 0 else 1
            max_panels_mppt = int(inv.mppt_voltage_max_v // max(v_mp_cold, panel.vmp)) if v_mp_cold > 0 else max_panels_voc
            n_max = min(max_panels_voc, max_panels_mppt) if max_panels_mppt > 0 else max_panels_voc
            n_min = int(math.ceil(inv.mppt_voltage_min_v / v_mp_hot)) if v_mp_hot > 0 else 1

            if n_min > n_max:
                all_inverters_valid = False
                break

            inv_target_dc = inv.rated_ac_power_kw * target_dc_ac_ratio
            max_strings = inv.mppt_count * inv.string_inputs_per_mppt

            best_inv_cfg = None
            best_inv_diff = float("inf")

            # Search practical string counts and series panels
            for s in range(1, max_strings + 1):
                strings_per_mppt = math.ceil(s / inv.mppt_count)
                if strings_per_mppt > inv.string_inputs_per_mppt:
                    continue
                if strings_per_mppt * panel.isc > inv.max_isc_per_mppt_a * 1.05:
                    continue

                for ns in range(n_min, n_max + 1):
                    mod_count = s * ns
                    dc_kw = (mod_count * panel.rated_power_wp) / 1000.0
                    ratio = dc_kw / inv.rated_ac_power_kw

                    if ratio < 1.05 or ratio > 1.45:
                        continue

                    diff = abs(dc_kw - inv_target_dc)
                    if diff < best_inv_diff:
                        best_inv_diff = diff
                        best_inv_cfg = {
                            "strings": s,
                            "panels_per_string": ns,
                            "panels": mod_count,
                            "dc_kwp": round(dc_kw, 2),
                            "ratio": round(ratio, 3),
                            "voc_cold": round(ns * v_oc_cold, 1),
                            "vmp_hot": round(ns * v_mp_hot, 1)
                        }

            if best_inv_cfg is None:
                all_inverters_valid = False
                break

            inverter_configs.append((best_inv_cfg, qty))
            total_panels_for_panel += best_inv_cfg["panels"] * qty
            total_strings_for_panel += best_inv_cfg["strings"] * qty
            total_dc_kwp_for_panel += best_inv_cfg["dc_kwp"] * qty

        if not all_inverters_valid:
            continue

        overall_ratio = total_dc_kwp_for_panel / target_ac_kw
        diff_from_target = abs(overall_ratio - target_dc_ac_ratio)

        evaluated_panels.append({
            "panel": panel,
            "total_panels": total_panels_for_panel,
            "total_strings": total_strings_for_panel,
            "total_dc_kwp": round(total_dc_kwp_for_panel, 2),
            "dc_ac_ratio": round(overall_ratio, 3),
            "ratio_diff": diff_from_target,
            "inverter_configs": inverter_configs
        })

    if not evaluated_panels:
        # Fallback to first available panel
        p_fallback = candidate_panels[0]
        n_approx = int(round((target_dc_kwp * 1000) / p_fallback.rated_power_wp))
        return {
            "selected_panel": p_fallback,
            "total_panels": n_approx,
            "total_strings": 1,
            "total_dc_kwp": round((n_approx * p_fallback.rated_power_wp) / 1000.0, 2),
            "dc_ac_ratio": round(((n_approx * p_fallback.rated_power_wp) / 1000.0) / target_ac_kw, 3),
            "explanation": f"Default fallback configuration using {p_fallback.model}."
        }

    evaluated_panels.sort(key=lambda x: (x["ratio_diff"], abs(x["total_dc_kwp"] - target_dc_kwp)))
    best = evaluated_panels[0]
    p = best["panel"]

    first_cfg = best["inverter_configs"][0][0]
    explanation = (
        f"Selected {p.manufacturer} {p.model} ({p.rated_power_wp:.0f} Wp): "
        f"{best['total_panels']} panels ({best['total_dc_kwp']:.2f} kWp DC, DC/AC: {best['dc_ac_ratio']:.3f}) "
        f"organized into {best['total_strings']} strings of {first_cfg['panels_per_string']} modules. "
        f"Cold Voc = {first_cfg['voc_cold']} V (below {inverter_breakdown[0]['inverter'].max_dc_voltage_v:.0f} V limit), "
        f"Hot Vmp = {first_cfg['vmp_hot']} V (within MPPT window). "
        f"Satisfies target DC/AC ratio ({target_dc_ac_ratio:.2f}) with optimal string layout."
    )
    best["explanation"] = explanation
    best["selected_panel"] = p
    best["chosen_panel"] = p
    best["panel"] = p
    best["thermal_string_check"] = {
        "cold_voc_status": "PASS",
        "hot_vmp_status": "PASS",
        "voc_cold": first_cfg["voc_cold"],
        "vmp_hot": first_cfg["vmp_hot"]
    }
    return best


# ---------------------------------------------------------------------------
# 2. PV MODULE & STRING SIZING PER INVERTER (SECTIONS 10 & 11)
# ---------------------------------------------------------------------------

def size_pv_per_inverter(
    inverter: Inverter,
    panel: Panel,
    project_params: Dict[str, Any],
    target_dc_ac_ratio: float = 1.25
) -> Dict[str, Any]:
    """
    Sizes PV module quantities, strings, and MPPT allocation INDEPENDENTLY
    for a single inverter unit.
    Calculates:
      - Allowable panels per string [N_min, N_max] based on Voc,cold and Vmp,hot
      - Optimal string count and modules per string targeting target_dc_ac_ratio
      - Operating & short-circuit currents
      - DC string fuse requirement per IEC 60269-6:
          * If strings per MPPT == 1 -> Not Required — validated
          * If strings per MPPT >= 2 -> Sized & Required
      - Independent DC switchgear (Isolator, SPD, Cable)
      - Individual AC switchgear (Isolator, Breaker, Cable, PE)
    """
    min_temp = float(project_params.get("min_design_temp_c", -30.0))
    max_temp = float(project_params.get("max_design_temp_c", 60.0))
    grid_v = float(project_params.get("grid_voltage_v", inverter.ac_voltage))

    # 1. Thermal voltages
    v_oc_cold = cold_voc(panel, min_temp)
    v_mp_hot, _ = hot_vmp(panel, max_temp)
    v_mp_cold, _ = cold_vmp(panel, min_temp)

    # 2. Allowable series panels per string
    max_panels_voc = int(inverter.max_dc_voltage_v // v_oc_cold) if v_oc_cold > 0 else 1
    max_panels_mppt = int(inverter.mppt_voltage_max_v // max(v_mp_cold, panel.vmp)) if v_mp_cold > 0 else max_panels_voc
    n_max = min(max_panels_voc, max_panels_mppt) if max_panels_mppt > 0 else max_panels_voc
    n_min = int(math.ceil(inverter.mppt_voltage_min_v / v_mp_hot)) if v_mp_hot > 0 else 1

    if n_min > n_max:
        # Fallback in case of narrow MPPT window
        n_min = max(1, n_max - 2)

    # 3. Target DC capacity for this inverter
    target_dc_kwp = inverter.rated_ac_power_kw * target_dc_ac_ratio
    target_panel_count = int(round((target_dc_kwp * 1000.0) / panel.rated_power_wp))

    # 4. Search best string configuration (S strings of N_s panels)
    # Available strings: from 1 to total inverter input capacity
    max_inverter_strings = inverter.mppt_count * inverter.string_inputs_per_mppt
    best_config = None
    best_diff = float("inf")

    # Evaluate possible string counts
    # Prefer strings that evenly divide across MPPTs or 1-2 strings for smaller inverters
    string_candidates = list(range(1, max_inverter_strings + 1))

    for s in string_candidates:
        # Panels per string candidates within allowable bounds
        for ns in range(n_min, n_max + 1):
            total_mod = s * ns
            dc_kwp = (total_mod * panel.rated_power_wp) / 1000.0
            ratio = dc_kwp / inverter.rated_ac_power_kw

            # Check electrical constraints
            strings_per_mppt_ceil = math.ceil(s / inverter.mppt_count)
            mppt_isc = strings_per_mppt_ceil * panel.isc
            mppt_imp = strings_per_mppt_ceil * panel.imp

            if strings_per_mppt_ceil > inverter.string_inputs_per_mppt:
                continue
            if mppt_isc > inverter.max_isc_per_mppt_a * 1.05:  # allow 5% margin
                continue
            if ratio < 1.0 or ratio > 1.45:
                continue

            diff = abs(dc_kwp - target_dc_kwp)
            # Favor closer match to target DC/AC ratio
            if diff < best_diff:
                best_diff = diff
                best_config = (s, ns, total_mod, dc_kwp, ratio)

    # If no configuration met all strict constraints, relax bounds to closest valid
    if best_config is None:
        # Select single string or standard 2 strings with median panels
        s = 1 if inverter.rated_ac_power_kw <= 6.0 else min(2, max_inverter_strings)
        ns = max(n_min, min(n_max, int(round(target_panel_count / s))))
        total_mod = s * ns
        dc_kwp = (total_mod * panel.rated_power_wp) / 1000.0
        ratio = dc_kwp / inverter.rated_ac_power_kw
        best_config = (s, ns, total_mod, dc_kwp, ratio)

    num_strings, panels_per_string, total_panels, actual_dc_kwp, actual_dc_ac_ratio = best_config

    # 5. String Voltages
    str_voc_cold = rnd(panels_per_string * v_oc_cold, 1)
    str_vmp_hot = rnd(panels_per_string * v_mp_hot, 1)
    str_vmp_stc = rnd(panels_per_string * panel.vmp, 1)

    # 6. MPPT Allocation
    mppt_allocation = allocate_mppt_for_inverter(inverter, num_strings, unit_number=1)
    if "allocation" in mppt_allocation:
        max_strings_per_mppt = max((m.get("strings_assigned", 1) for m in mppt_allocation["allocation"]), default=1)
    else:
        max_strings_per_mppt = math.ceil(num_strings / max(1, inverter.mppt_count))

    # 7. DC Protection Sizing
    # IEC 60269-6 String Fuse Rule:
    # If max strings per MPPT == 1 -> No string fuses needed (no reverse current hazard)
    # If max strings per MPPT >= 2 -> Fuse required: 1.5 x Isc <= In <= Max Series Fuse
    if max_strings_per_mppt >= 2:
        fuse_required = True
        calc_fuse = panel.isc * 1.5
        # Standard gPV ratings: 15A, 16A, 20A, 25A, 30A, 32A
        g_pv_ratings = [15, 16, 20, 25, 30, 32]
        chosen_fuse = next((r for r in g_pv_ratings if r >= calc_fuse), 25)
        fuse_rating_a = chosen_fuse
        fuse_qty = num_strings * 2  # positive and negative legs
        fuse_status_label = f"Required: {chosen_fuse}A 1000V/1500V gPV"
        fuse_note = f"Parallel strings ({max_strings_per_mppt}/MPPT) require gPV protection per IEC 60269-6."
    else:
        fuse_required = False
        fuse_rating_a = None
        fuse_qty = 0
        fuse_status_label = "Not Required \u2014 validated"
        fuse_note = "Single string per MPPT: No reverse current hazard per IEC 60269-6. String fuses not required."

    # DC Isolator
    min_dc_iso_v = rnd(str_voc_cold * 1.2, 1)
    min_dc_iso_i = rnd(panel.isc * max_strings_per_mppt * 1.25, 1)
    dc_iso_v = 1000 if min_dc_iso_v <= 1000 else 1500
    dc_iso_current_ratings = [16, 25, 32, 40, 63]
    dc_iso_i = next((r for r in dc_iso_current_ratings if r >= min_dc_iso_i), 32)
    dc_isolator_spec = f"{dc_iso_i}A, {dc_iso_v}V DC (4-Pole)"
    dc_isolator_qty = num_strings  # standard company practice: 1 per string (or 1 per MPPT)

    # DC SPD
    dc_spd_min_uc = rnd(str_voc_cold * 1.2, 1)
    dc_spd_uc = 600 if dc_spd_min_uc <= 600 else (1000 if dc_spd_min_uc <= 1000 else 1500)
    dc_spd_spec = f"Type II DC SPD, Uc {dc_spd_uc}V, Imax 40kA"
    dc_spd_qty = 1  # 1 per inverter unit

    # DC Cable (4mm² or 6mm² PV Solar Cable)
    dc_cable_current = rnd(panel.isc * 1.25, 2)
    dc_cable_csa = 4.0 if dc_cable_current <= 35.0 else 6.0
    dc_cable_run_m = float(project_params.get("dc_cable_length_m", 30.0))
    dc_cable_total_m = rnd(dc_cable_run_m * 2.0 * num_strings, 1)  # + and - runs

    # DC Voltage drop
    # ΔV = 2 * L * I * ρ / S
    vd_dc_v = rnd((2.0 * dc_cable_run_m * panel.imp * COPPER_RESISTIVITY_OHM_MM2_PER_M_AT_70C) / dc_cable_csa, 2)
    vd_dc_pct = rnd((vd_dc_v / str_vmp_stc) * 100.0, 2) if str_vmp_stc > 0 else 0.0

    # MC4 connectors: 2 pairs (4 connectors) per string
    mc4_pairs_qty = num_strings * 2

    # 8. Individual AC Switchgear & Cable PER INVERTER
    # Rated AC Current
    if inverter.grid_type == "1-phase":
        ac_current = rnd((inverter.rated_ac_power_kw * 1000.0) / grid_v, 1)
        ac_poles = "2P"
    else:
        ac_current = rnd((inverter.rated_ac_power_kw * 1000.0) / (math.sqrt(3) * grid_v), 1)
        ac_poles = "4P"

    # Use datasheet max_ac_current_a if available and higher
    ac_current = max(ac_current, inverter.max_ac_current_a)

    design_ac_current = rnd(ac_current * 1.25, 1)

    # Inverter Breaker (MCB <= 63A, MCCB > 63A)
    if design_ac_current <= 63:
        breaker_rating = next((r for r in MCB_STANDARD_RATINGS_A if r >= design_ac_current), 63)
        breaker_type = f"{breaker_rating}A {ac_poles} MCB (Curve C, 10kA)"
    else:
        breaker_rating = next((r for r in MCCB_STANDARD_RATINGS_A if r >= design_ac_current), 100)
        breaker_type = f"{breaker_rating}A {ac_poles} MCCB (36kA)"

    # Inverter Local AC Isolator
    iso_ratings = [20, 25, 32, 40, 63, 100, 125, 160, 250]
    iso_rating = next((r for r in iso_ratings if r >= design_ac_current), 63)
    ac_isolator_spec = f"{iso_rating}A {ac_poles} Rotary AC Isolator (AC-23A, IP65)"

    # Inverter AC Cable (from Kelani Cables Table A1, enclosed in conduit/trunking)
    # Cable sizing for design_ac_current coordinated with breaker rating
    method_k = "b_34c" if inverter.grid_type == "3-phase" else "b_2c"
    cable_res = select_cable(max(design_ac_current, float(breaker_rating)), method_key=method_k)
    if cable_res.get("status") != "FAIL" and cable_res.get("csa_mm2") is not None:
        ac_cable_csa = float(cable_res["csa_mm2"])
    else:
        # Step through Table A1 directly if needed
        candidates = sorted([r for r in CABLE_AMPACITY_TABLE if r.get(method_k) is not None], key=lambda r: r["csa_mm2"])
        match_row = next((r for r in candidates if r[method_k] >= max(design_ac_current, float(breaker_rating))), candidates[-1])
        ac_cable_csa = float(match_row["csa_mm2"])

    # Ensure min 6mm² for solar inverter AC circuits (BS 7671 engineering minimum)
    if ac_cable_csa < 6.0:
        ac_cable_csa = 6.0

    ac_cable_run_m = float(project_params.get("ac_cable_length_m", 15.0))

    # AC Voltage Drop & iterative upsizing if drop > 1.5%
    factor = math.sqrt(3) if inverter.grid_type == "3-phase" else 2.0
    vd_ac_v = rnd((factor * ac_cable_run_m * ac_current * COPPER_RESISTIVITY_OHM_MM2_PER_M_AT_70C) / ac_cable_csa, 2)
    vd_ac_pct = rnd((vd_ac_v / grid_v) * 100.0, 2)

    # Upsize if voltage drop > 1.5% and larger size is available
    if vd_ac_pct > 1.5:
        larger = [r["csa_mm2"] for r in CABLE_AMPACITY_TABLE if r["csa_mm2"] > ac_cable_csa]
        for c_next in larger:
            v_test = (factor * ac_cable_run_m * ac_current * COPPER_RESISTIVITY_OHM_MM2_PER_M_AT_70C) / c_next
            if (v_test / grid_v) * 100.0 <= 1.5:
                ac_cable_csa = float(c_next)
                vd_ac_v = rnd(v_test, 2)
                vd_ac_pct = rnd((vd_ac_v / grid_v) * 100.0, 2)
                break

    # Inverter PE (Protective Earth)
    # BS 7671 Table 54.7:
    # S <= 16mm² -> PE = same size (min 6mm² for 3-ph, min 4mm² for small 1-ph)
    # 16 < S <= 35 -> PE = 16mm²
    # S > 35 -> PE = max(16.0, S/2)
    if ac_cable_csa <= 6.0:
        inv_pe_csa = 4.0 if inverter.rated_ac_power_kw <= 3.0 else 6.0
    elif ac_cable_csa <= 16.0:
        inv_pe_csa = max(6.0, ac_cable_csa)
    elif ac_cable_csa <= 35.0:
        inv_pe_csa = 16.0
    else:
        inv_pe_csa = 25.0 if ac_cable_csa <= 70.0 else rnd(ac_cable_csa / 2.0, 1)

    return {
        "inverter": inverter,
        "panel": panel,
        "total_panels": total_panels,
        "num_strings": num_strings,
        "panels_per_string": panels_per_string,
        "actual_dc_kwp": rnd(actual_dc_kwp, 2),
        "actual_ac_kw": inverter.rated_ac_power_kw,
        "dc_ac_ratio": rnd(actual_dc_ac_ratio, 3),
        "string_voc_cold_v": str_voc_cold,
        "string_vmp_hot_v": str_vmp_hot,
        "string_vmp_stc_v": str_vmp_stc,
        "mppt_allocation": mppt_allocation,
        "max_strings_per_mppt": max_strings_per_mppt,
        # DC Protection
        "fuse_required": fuse_required,
        "fuse_rating_a": fuse_rating_a,
        "fuse_qty": fuse_qty,
        "fuse_status_label": fuse_status_label,
        "fuse_note": fuse_note,
        "dc_isolator_spec": dc_isolator_spec,
        "dc_isolator_qty": dc_isolator_qty,
        "dc_spd_spec": dc_spd_spec,
        "dc_spd_qty": dc_spd_qty,
        "dc_cable_csa_mm2": dc_cable_csa,
        "dc_cable_total_m": dc_cable_total_m,
        "dc_voltage_drop_pct": vd_dc_pct,
        "mc4_pairs_qty": mc4_pairs_qty,
        # Inverter AC Switchgear
        "ac_current_a": ac_current,
        "design_ac_current_a": design_ac_current,
        "ac_breaker_spec": breaker_type,
        "ac_breaker_rating_a": breaker_rating,
        "ac_isolator_spec": ac_isolator_spec,
        "ac_cable_csa_mm2": ac_cable_csa,
        "ac_cable_run_m": ac_cable_run_m,
        "ac_voltage_drop_pct": vd_ac_pct,
        "inverter_pe_csa_mm2": inv_pe_csa,
        "earth_conductor_csa_mm2": inv_pe_csa,
    }


# ---------------------------------------------------------------------------
# 3. WHOLE-SYSTEM MAIN AC PROTECTION & MAIN CABLE SIZING
# ---------------------------------------------------------------------------

def size_whole_system_ac(
    inverter_designs: List[Dict[str, Any]],
    grid_voltage_v: float = 400.0,
    grid_phases: int = 3,
    main_cable_run_m: float = 20.0
) -> Dict[str, Any]:
    """
    Sizes Whole-System Main AC Switchgear and Main AC Cable based on the
    COMBINED total export current of all active inverters:
      I_ac,total = sum(I_ac,i)
    Standards:
      - Main Cable sized per BS 7671 Table A1 for 1.25 * I_ac,total and coordinated with Main Breaker (Ib <= In <= Iz)
      - Main Breaker (MCB <= 63A, MCCB > 63A)
      - Main AC Isolator
      - Main AC SPD (Type II Uc 275V / 440V)
      - Lockable Utility Switch (padlockable in OFF position per CEB rules)
      - Main Busbar Sizing & standard dimension notation
    """
    total_ac_kw = sum(d["actual_ac_kw"] for d in inverter_designs)
    total_ac_current = sum(d["ac_current_a"] for d in inverter_designs)
    total_ac_current = rnd(total_ac_current, 1)

    design_main_current = rnd(total_ac_current * 1.25, 1)

    poles_str = "4P" if grid_phases == 3 else "2P"

    # Ensure main protective device coordinates with branch breakers (selectivity/discrimination)
    max_branch_breaker = max((float(d.get("ac_breaker_rating_a", 0)) for d in inverter_designs), default=0.0)
    required_main_rating = max(design_main_current, max_branch_breaker)
    if len(inverter_designs) > 1 and grid_phases == 3:
        required_main_rating = max(required_main_rating, 63.0)

    # Main Protective Device (MCB <= 63A, MCCB > 63A)
    if required_main_rating <= 63.0:
        main_breaker_rating = next((r for r in MCB_STANDARD_RATINGS_A if r >= required_main_rating), 63)
        main_breaker_type = "MCB"
        main_breaker_spec = f"{main_breaker_rating}A {poles_str} MCB (Curve C, 10kA)"
    else:
        main_breaker_rating = next((r for r in MCCB_STANDARD_RATINGS_A if r >= required_main_rating), 100)
        main_breaker_type = "MCCB"
        main_breaker_spec = f"{main_breaker_rating}A {poles_str} MCCB (36kA Adjustable)"

    # Main AC Isolator
    standard_isolators = [40, 63, 100, 125, 160, 200, 250, 400, 630, 800, 1000]
    main_iso_rating = next((r for r in standard_isolators if r >= max(design_main_current, float(main_breaker_rating))), 63)
    main_isolator_spec = f"{main_iso_rating}A {poles_str} Rotary AC Isolator (AC-23A, IP65)"

    # CEB Lockable Utility Switch (padlockable in OFF position)
    utility_ratings = [32, 40, 63, 100, 160, 250, 400, 630]
    lockable_rating = next((r for r in utility_ratings if r >= max(design_main_current, float(main_breaker_rating))), 63)
    lockable_switch_spec = f"{lockable_rating}A {poles_str} Lockable Utility Disconnect Switch (Padlockable in OFF)"

    # Main AC SPD
    spd_uc = 440 if grid_phases == 3 else 275
    main_spd_spec = f"Type II AC SPD (Uc {spd_uc}V, Imax 40kA, In 20kA, {poles_str})"

    # Main AC Cable Sizing from Kelani Table A1 coordinated with Main Breaker (Ib <= In <= Iz)
    method_key = "b_34c" if grid_phases == 3 else "b_2c"
    # Target current must carry at least the breaker rating or design current
    target_cable_amp = max(design_main_current, float(main_breaker_rating) * 0.95)
    cable_res = select_cable(target_cable_amp, method_key=method_key)
    if cable_res.get("status") != "FAIL" and cable_res.get("csa_mm2") is not None:
        main_cable_csa = float(cable_res["csa_mm2"])
    else:
        # Scan entire Table A1 up to 1000 mm²
        candidates = sorted([r for r in CABLE_AMPACITY_TABLE if r.get(method_key) is not None], key=lambda r: r["csa_mm2"])
        match_row = next((r for r in candidates if r[method_key] >= target_cable_amp), candidates[-1])
        main_cable_csa = float(match_row["csa_mm2"])

    # Multi-inverter export cable minimum (e.g. 13 kW multi-inverter requires 16 mm² to coordinate with 63A main breaker)
    if len(inverter_designs) > 1 and main_cable_csa < 16.0:
        main_cable_csa = 16.0

    # Ensure min 6mm² for 1-phase
    if grid_phases == 1 and main_cable_csa < 6.0:
        main_cable_csa = 6.0

    # Main Cable Voltage Drop & iterative upsizing if drop > 1.5%
    factor = math.sqrt(3) if grid_phases == 3 else 2.0
    main_vd_v = rnd((factor * main_cable_run_m * total_ac_current * COPPER_RESISTIVITY_OHM_MM2_PER_M_AT_70C) / main_cable_csa, 2)
    main_vd_pct = rnd((main_vd_v / grid_voltage_v) * 100.0, 2)

    if main_vd_pct > 1.5:
        larger = [r["csa_mm2"] for r in CABLE_AMPACITY_TABLE if r["csa_mm2"] > main_cable_csa]
        for c_next in larger:
            v_test = (factor * main_cable_run_m * total_ac_current * COPPER_RESISTIVITY_OHM_MM2_PER_M_AT_70C) / c_next
            if (v_test / grid_voltage_v) * 100.0 <= 1.5:
                main_cable_csa = float(c_next)
                main_vd_v = rnd(v_test, 2)
                main_vd_pct = rnd((main_vd_v / grid_voltage_v) * 100.0, 2)
                break

    # Format Main Cable Specification String
    if grid_phases == 3:
        if main_cable_csa <= 50.0:
            main_cable_spec = f"4C {main_cable_csa:.0f}sqmm/CU/PVC"
        else:
            main_cable_spec = f"1C*4 {main_cable_csa:.0f}mm sq CU/XLPE/PVC"
    else:
        main_cable_spec = f"2C/{main_cable_csa:.0f}sq.mm/Cu/PVC"

    # Main Busbar rating and standard dimensions
    busbar_rating = next((b for b in BUSBAR_STANDARD_RATINGS_A if b >= max(design_main_current, float(main_breaker_rating))), BUSBAR_STANDARD_RATINGS_A[-1])
    if busbar_rating <= 80:
        busbar_label = f"{busbar_rating} A Bus Bar Cu"
        busbar_dim = "15mm*3mm"
    elif busbar_rating <= 100:
        busbar_label = f"{busbar_rating} A Bus Bar Cu"
        busbar_dim = "25mm*3mm"
    elif busbar_rating <= 250:
        busbar_label = f"{busbar_rating} A Bus Bar Cu (30mm*5mm)"
        busbar_dim = "30mm*5mm"
    elif busbar_rating <= 630:
        busbar_label = f"{busbar_rating} A Bus Bar Cu (50mm*5mm)"
        busbar_dim = "50mm*5mm"
    else:
        busbar_label = f"{busbar_rating} A, Bus Bar (50mm*10mm)"
        busbar_dim = "50mm*10mm"

    return {
        "total_ac_kw": total_ac_kw,
        "total_ac_current_a": total_ac_current,
        "design_main_current_a": design_main_current,
        "main_breaker_spec": main_breaker_spec,
        "main_breaker_rating_a": main_breaker_rating,
        "main_breaker_type": main_breaker_type,
        "main_isolator_spec": main_isolator_spec,
        "main_isolator_rating_a": main_iso_rating,
        "lockable_switch_spec": lockable_switch_spec,
        "lockable_switch_rating_a": lockable_rating,
        "main_spd_spec": main_spd_spec,
        "main_cable_spec": main_cable_spec,
        "main_cable_csa_mm2": main_cable_csa,
        "main_cable_run_m": main_cable_run_m,
        "main_voltage_drop_pct": main_vd_pct,
        "main_busbar_rating_a": busbar_rating,
        "main_busbar_label": busbar_label,
        "main_busbar_dim": busbar_dim,
    }


# ---------------------------------------------------------------------------
# 4. DYNAMIC EARTHING SIZING (BS 7430)
# ---------------------------------------------------------------------------

def size_dynamic_earthing(
    system_ac_kw: float,
    total_panels: int,
    inverter_count: int,
    soil_resistivity_ohm_m: float = 70.0,
    target_resistance_ohm: float = 10.0
) -> Dict[str, Any]:
    """
    Calculates dynamic earthing per BS 7430:
      - Main Earth Conductor dynamically sized by capacity:
          * <= 10 kW  -> 10 mm² Cu
          * 11 - 40 kW -> 16 mm² Cu
          * 41 - 100 kW -> 25 mm² Cu
          * > 100 kW  -> 35 mm² Cu
      - Module frame & structure bonding: 6 mm² Cu green/yellow
      - Earth electrode resistance & rods required to achieve < target_resistance
    """
    # Main earth conductor
    if system_ac_kw <= 10.0:
        main_earth_csa = 10.0
    elif system_ac_kw <= 40.0:
        main_earth_csa = 16.0
    elif system_ac_kw <= 100.0:
        main_earth_csa = 25.0
    else:
        main_earth_csa = 35.0

    # Electrode calculation
    rod_res = calculate_earth_rod_resistance(soil_resistivity_ohm_m, rod_length_m=3.0, rod_diameter_mm=16.0)
    single_rod_r = rod_res["resistance_ohm"]
    rods_req = calculate_earth_rods_required(single_rod_r, target_resistance_ohm)
    num_rods = max(1, rods_req["n_rods"])

    # Effective resistance with parallel rods
    effective_r = rnd(single_rod_r / (num_rods * 0.75), 1)

    return {
        "main_earth_conductor_csa_mm2": main_earth_csa,
        "main_earth_conductor_spec": f"{main_earth_csa} mm\u00b2 Bare/Insulated Copper Conductor (BS 7430)",
        "module_bonding_conductor_csa_mm2": 6.0,
        "module_bonding_spec": "6.0 mm\u00b2 Green/Yellow PVC Insulated Copper Earth Wire",
        "earth_rod_spec": "5/8\" (16mm) \u00d7 3.0m Copper-Bonded Steel Earth Rod with Inspection Chamber",
        "earth_rods_qty": num_rods,
        "single_rod_resistance_ohm": rnd(single_rod_r, 1),
        "target_resistance_ohm": target_resistance_ohm,
        "achieved_resistance_ohm": effective_r,
        "status": "PASS" if effective_r <= target_resistance_ohm else "WARNING"
    }


# ---------------------------------------------------------------------------
# 5. ORCHESTRATED DYNAMIC SYSTEM DESIGN PIPELINE
# ---------------------------------------------------------------------------

def calculate_dynamic_system(
    target_ac_kw: float,
    panel: Optional[Panel] = None,
    project_params: Optional[Dict[str, Any]] = None,
    selected_combination: Optional[Dict[str, Any]] = None,
    target_dc_ac_ratio: Optional[float] = None
) -> Dict[str, Any]:
    """
    Master pipeline orchestrator for the Dynamic Solar System Design Engine.
    Executes the full dependency chain:
      Required Capacity -> Inverter Combination -> Automatic Panel Selection & Sizing
      -> MPPT Allocation -> DC Protection -> DC Cable -> Indiv AC Protection/Cable
      -> Main AC Protection/Cable -> Earthing -> Categorized Schedule.
    """
    if project_params is None:
        project_params = {}

    if target_dc_ac_ratio is None:
        target_dc_ac_ratio = float(project_params.get("dc_ac_ratio_preferred", 1.30))

    grid_phases = int(project_params.get("grid_phases", 3 if target_ac_kw > 5.0 else 1))
    grid_v = float(project_params.get("grid_voltage_v", 400.0 if grid_phases == 3 else 230.0))

    # 1. Inverter Combination (supports up to 4 distinct inverter model entries)
    if selected_combination is None:
        ranked_combos = generate_inverter_combinations(target_ac_kw, grid_phase=grid_phases)
        active_combo = ranked_combos[0] if ranked_combos else None
    else:
        active_combo = selected_combination

    if not active_combo:
        raise ValueError(f"Could not find feasible inverter combination for {target_ac_kw} kW.")

    breakdown = active_combo.get("breakdown", [])
    validation = validate_inverter_combination(breakdown, target_ac_kw, grid_phase=grid_phases)

    # 2. Automatic Panel Selection Engine (evaluates all approved panels for practical string fit)
    auto_panel_result = find_optimal_panel_and_string_config(
        target_ac_kw=target_ac_kw,
        inverter_breakdown=breakdown,
        project_params=project_params,
        target_dc_ac_ratio=target_dc_ac_ratio
    )
    if panel is None:
        panel = auto_panel_result["selected_panel"]

    # 3. Independent PV & Electrical Design per Inverter Unit
    per_inverter_designs = []
    unit_counter = 1


    for item in breakdown:
        inv: Inverter = item["inverter"]
        qty = item["quantity"]
        for _ in range(qty):
            inv_design = size_pv_per_inverter(
                inverter=inv,
                panel=panel,
                project_params=project_params,
                target_dc_ac_ratio=target_dc_ac_ratio
            )
            inv_design["unit_number"] = unit_counter
            inv_design["unit_label"] = f"Unit #{unit_counter} ({inv.model} \u2014 {inv.rated_ac_power_kw:.0f} kW)"
            per_inverter_designs.append(inv_design)
            unit_counter += 1

    # Aggregate System Totals
    total_panels = sum(d["total_panels"] for d in per_inverter_designs)
    total_strings = sum(d["num_strings"] for d in per_inverter_designs)
    total_actual_dc_kwp = rnd(sum(d["actual_dc_kwp"] for d in per_inverter_designs), 2)
    total_actual_ac_kw = rnd(sum(d["actual_ac_kw"] for d in per_inverter_designs), 2)
    overall_dc_ac_ratio = rnd(total_actual_dc_kwp / total_actual_ac_kw, 3) if total_actual_ac_kw > 0 else 1.25

    # 3. Whole-System Main AC Switchgear & Main AC Cable
    main_cable_run = float(project_params.get("main_ac_cable_length_m", 20.0))
    whole_system_ac = size_whole_system_ac(
        inverter_designs=per_inverter_designs,
        grid_voltage_v=grid_v,
        grid_phases=grid_phases,
        main_cable_run_m=main_cable_run
    )

    # 4. Dynamic Earthing
    earthing_design = size_dynamic_earthing(
        system_ac_kw=total_actual_ac_kw,
        total_panels=total_panels,
        inverter_count=len(per_inverter_designs),
        soil_resistivity_ohm_m=float(project_params.get("soil_resistivity_ohm_m", 70.0)),
        target_resistance_ohm=float(project_params.get("target_earth_resistance_ohm", 10.0))
    )

    # 5. Component Classification Schedule (Section 26)
    classified_schedule = {
        "PER_PANEL": [
            {"item": "Solar PV Modules", "spec": f"{panel.manufacturer} {panel.model} ({panel.rated_power_wp} Wp)", "quantity": total_panels, "unit": "Nos"},
            {"item": "Mid Clamps (Aluminium)", "spec": f"Anodised Aluminium Mid Clamp with SS304 A2-70 Fasteners ({panel.thickness_mm}mm)", "quantity": max(0, (total_panels - total_strings) * 2), "unit": "Nos"},
            {"item": "End Clamps (Aluminium)", "spec": f"Anodised Aluminium End Clamp with SS304 A2-70 Fasteners ({panel.thickness_mm}mm)", "quantity": total_strings * 4, "unit": "Nos"},
            {"item": "Module Frame Grounding Clips", "spec": "Stainless Steel Grounding / Bonding Clip", "quantity": total_panels, "unit": "Nos"},
        ],
        "PER_STRING": [
            {"item": "MC4 Cable Connectors", "spec": "1000V/1500V DC IP68 MC4 Connectors (Pair M+F)", "quantity": total_strings * 2, "unit": "Pairs"},
            {"item": "DC Solar String Cable (4/6 mm²)", "spec": "Single Core Flexible Tinned Copper PV1-F / H1Z2Z2-K UV Resistant", "quantity": sum(d["dc_cable_total_m"] for d in per_inverter_designs), "unit": "Meters"},
            {"item": "DC String Fuses (1000V gPV)", "spec": "1000V DC 10x38mm gPV Fuse Link with Holder", "quantity": sum(d["fuse_qty"] for d in per_inverter_designs), "unit": "Nos", "status": "Not Required" if sum(d["fuse_qty"] for d in per_inverter_designs) == 0 else "Required"},
        ],
        "PER_INVERTER": [
            {"item": "On-Grid String Inverters", "spec": ", ".join(f"{item['quantity']} \u00d7 {item['inverter'].model} ({item['inverter'].rated_ac_power_kw} kW)" for item in breakdown), "quantity": len(per_inverter_designs), "unit": "Nos"},
            {"item": "Inverter DC Isolators", "spec": "4-Pole Rotary DC Isolator 1000V/1500V IP65", "quantity": sum(d["dc_isolator_qty"] for d in per_inverter_designs), "unit": "Nos"},
            {"item": "Inverter DC SPDs", "spec": "Type II DC Surge Protective Device (Uc 1000V, Imax 40kA)", "quantity": len(per_inverter_designs), "unit": "Nos"},
            {"item": "Individual Inverter AC Breakers", "spec": "MCB / MCCB sized for inverter rated output", "quantity": len(per_inverter_designs), "unit": "Nos"},
            {"item": "Individual Inverter AC Isolators", "spec": "Local Rotary AC Isolator adjacent to inverter", "quantity": len(per_inverter_designs), "unit": "Nos"},
            {"item": "Inverter AC Cables", "spec": "XLPE/PVC Multi-core Copper Cable (Inverter to Main DB)", "quantity": sum(d["ac_cable_run_m"] for d in per_inverter_designs), "unit": "Meters"},
            {"item": "Inverter Protective Earth (PE)", "spec": "Green/Yellow PVC Insulated Copper Earth Conductor", "quantity": len(per_inverter_designs) * 15.0, "unit": "Meters"},
        ],
        "PER_SYSTEM": [
            {"item": "Main AC Distribution Board (DB)", "spec": f"Weatherproof IP65 Surface Wall-Mount DB with {whole_system_ac['main_busbar_rating_a']}A Busbar", "quantity": 1, "unit": "Lot"},
            {"item": "Main System AC Breaker", "spec": whole_system_ac["main_breaker_spec"], "quantity": 1, "unit": "Nos"},
            {"item": "Main System AC Isolator", "spec": whole_system_ac["main_isolator_spec"], "quantity": 1, "unit": "Nos"},
            {"item": "Lockable Utility Disconnect Switch", "spec": whole_system_ac["lockable_switch_spec"], "quantity": 1, "unit": "Nos"},
            {"item": "Main System AC SPD", "spec": whole_system_ac["main_spd_spec"], "quantity": 1, "unit": "Nos"},
            {"item": "Main AC Export Cable", "spec": f"4-Core {whole_system_ac['main_cable_csa_mm2']} mm\u00b2 XLPE/SWA/PVC or CU/PVC/PVC Copper Cable", "quantity": whole_system_ac["main_cable_run_m"], "unit": "Meters"},
            {"item": "Main Earth Conductor", "spec": earthing_design["main_earth_conductor_spec"], "quantity": 25.0, "unit": "Meters"},
            {"item": "Earth Rod Electrodes", "spec": earthing_design["earth_rod_spec"], "quantity": earthing_design["earth_rods_qty"], "unit": "Sets"},
            {"item": "Bi-directional Energy Meter", "spec": "CEB/LECO Approved Three-Phase Bi-directional Smart Energy Meter", "quantity": 1, "unit": "Nos"},
            {"item": "Current Transformers (CT)", "spec": f"Class 0.5s Split-core CTs ({math.ceil(whole_system_ac['design_main_current_a'] / 50.0) * 50}/5A)", "quantity": 3 if grid_phases == 3 else 1, "unit": "Nos"},
            {"item": "Remote Datalogger / Comms Gateway", "spec": "WiFi/LAN/4G Smart Communication Datalogger Module", "quantity": 1, "unit": "Nos"},
        ]
    }

    # Annual Production Estimate
    pr = 0.795
    psh = float(project_params.get("peak_sun_hours", 4.5))
    annual_kwh = rnd(total_actual_dc_kwp * psh * 365.0 * pr, 0)

    return {
        "target_ac_kw": target_ac_kw,
        "target_dc_kwp": rnd(target_ac_kw * target_dc_ac_ratio, 2),
        "actual_ac_kw": total_actual_ac_kw,
        "actual_dc_kwp": total_actual_dc_kwp,
        "dc_ac_ratio": overall_dc_ac_ratio,
        "total_panels": total_panels,
        "total_strings": total_strings,
        "panel": panel,
        "auto_panel_selection": auto_panel_result,
        "panel_selection_explanation": auto_panel_result.get("explanation", ""),
        "active_combination": active_combo,
        "validation": validation,
        "per_inverter_designs": per_inverter_designs,
        "whole_system_ac": whole_system_ac,
        "earthing_design": earthing_design,
        "classified_schedule": classified_schedule,
        "annual_ac_energy_kwh": annual_kwh,
        "performance_ratio_pct": rnd(pr * 100.0, 1),
        "overall_status": validation["status"]
    }
