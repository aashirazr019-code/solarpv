"""
Cable sizing — picks the smallest cable CSA whose tabulated ampacity
(Table A1, from the uploaded Kelani Cables chart) meets or exceeds the
derated design current. Also gives an approximate voltage-drop estimate.

This mirrors BS 7671 method: It >= Ib / (Ca x Cg), where Ca = ambient
temperature correction factor, Cg = grouping correction factor. The
chart itself is already at 30°C ambient / 70°C conductor — if your real
site conditions differ, apply Ca/Cg from the cable manufacturer's
correction tables (chart references "Table Y-01", not included here)
and enter the combined factor below.
"""
import math
from .electrical_data import CABLE_AMPACITY_TABLE, COPPER_RESISTIVITY_OHM_MM2_PER_M_AT_70C, resolve_method_key
from .string_sizing import rnd


def select_cable(design_current_a, method_key, derating_factor=1.0):
    """
    design_current_a : the actual load/design current (A), before derating
    method_key       : one of the column keys in electrical_data.INSTALLATION_METHODS or alias
    derating_factor  : combined Ca x Cg correction factor (1.0 = chart's
                        base conditions, no correction needed)
    """
    derating_factor = derating_factor if derating_factor and derating_factor > 0 else 1.0
    required_tabulated_a = rnd(design_current_a / derating_factor, 2)
    resolved_key = resolve_method_key(method_key, default="b_34c")

    candidates = sorted(CABLE_AMPACITY_TABLE, key=lambda r: r["csa_mm2"])
    chosen = None
    for row in candidates:
        amp = row.get(resolved_key)
        if amp is not None and amp >= required_tabulated_a:
            chosen = row
            break

    if chosen is None:
        return {
            "status": "FAIL",
            "message": (
                f"No cable size in this table's data for this method covers "
                f"{required_tabulated_a}A required tabulated current. Use a larger "
                f"installation method rating, parallel cables, or a manufacturer's "
                f"extended table."
            ),
            "required_tabulated_a": required_tabulated_a,
            "csa_mm2": None,
            "tabulated_ampacity_a": None,
            "ampacity_a": None,
        }

    chosen_amp = chosen[resolved_key]
    margin_pct = rnd((required_tabulated_a / chosen_amp) * 100, 1)
    status = "WARNING" if margin_pct >= 90 else "PASS"

    return {
        "status": status,
        "csa_mm2": chosen["csa_mm2"],
        "tabulated_ampacity_a": chosen_amp,
        "ampacity_a": chosen_amp,
        "required_tabulated_a": required_tabulated_a,
        "design_current_a": design_current_a,
        "derating_factor": derating_factor,
        "method_key": resolved_key,
        "margin_pct": margin_pct,
        "show_calculation": {
            "design_current_a": design_current_a,
            "derating_factor": derating_factor,
            "required_tabulated_a": required_tabulated_a,
            "chosen_csa_mm2": chosen["csa_mm2"],
            "chosen_tabulated_ampacity_a": chosen_amp,
        },
    }


def select_cable_and_device(design_current_a, method_key, derating_factor=1.0, safety_factor=1.25, allow_mccb=True):
    """
    Coordinated selection: picks the smallest cable AND the smallest
    protective device such that Ib <= In <= Iz holds together — not just
    a cable sized for Ib alone. Steps the cable up automatically if the
    first-choice cable can't carry the standard device rating above it.
    """
    from .protection_sizing import select_protective_device

    resolved_key = resolve_method_key(method_key, default="b_34c")
    candidates = sorted(CABLE_AMPACITY_TABLE, key=lambda r: r["csa_mm2"])
    required_tabulated_a = rnd(design_current_a / (derating_factor if derating_factor > 0 else 1.0), 2)

    for row in candidates:
        amp = row.get(resolved_key)
        if amp is None or amp < required_tabulated_a:
            continue
        device = select_protective_device(design_current_a, cable_ampacity_a=amp, safety_factor=safety_factor, allow_mccb=allow_mccb)
        if device["status"] == "PASS":
            return {
                "status": "PASS",
                "csa_mm2": row["csa_mm2"],
                "tabulated_ampacity_a": amp,
                "ampacity_a": amp,
                "device_type": device["device_type"],
                "rated_current_a": device["rated_current_a"],
                "design_current_a": design_current_a,
                "derating_factor": derating_factor,
                "method_key": resolved_key,
                "cable_margin_pct": rnd((required_tabulated_a / amp) * 100, 1),
                "rule_note": "Ib \u2264 In \u2264 Iz \u2014 cable upsized as needed so the standard device rating still fits within the cable's ampacity.",
            }

    return {
        "status": "FAIL",
        "message": "No cable/device combination in this table's data satisfies Ib \u2264 In \u2264 Iz for this current and method.",
        "required_tabulated_a": required_tabulated_a,
        "csa_mm2": None,
        "tabulated_ampacity_a": None,
        "ampacity_a": None,
    }


def voltage_drop_estimate(csa_mm2, current_a, length_m, system="dc", nominal_voltage=None):
    """
    Rough indicative voltage-drop estimate using copper resistivity —
    NOT a substitute for the manufacturer's Table A2 (mV/A/m) figures.
    system: "dc" or "ac_single" -> round-trip (2 x length).
            "ac_three" -> single-way with sqrt(3) factor, simplified (cos phi = 1).
    """
    r_per_m = COPPER_RESISTIVITY_OHM_MM2_PER_M_AT_70C / csa_mm2  # ohm/m, single conductor

    if system == "ac_three":
        drop_v = rnd(1.732 * current_a * r_per_m * length_m, 2)
    else:  # dc or single-phase ac: current flows out and back
        drop_v = rnd(2 * current_a * r_per_m * length_m, 2)

    result = {
        "estimated_drop_v": drop_v,
        "note": "Indicative only (copper resistivity @70°C) — check manufacturer's Table A2 for a precise figure.",
    }
    if nominal_voltage:
        result["drop_pct"] = rnd((drop_v / nominal_voltage) * 100, 2)
        result["within_3pct"] = result["drop_pct"] <= 3.0
    return result


def select_dc_cable_comprehensive(
    design_current_a: float,
    length_m: float,
    nominal_voltage_v: float,
    num_parallel_strings: int = 1,
    max_vd_pct: float = 1.5,
    method_key: str = "c_2c",
    derating_factor: float = 1.0,
    material: str = "copper",
    safety_factor: float = 1.25
):
    """
    Comprehensive DC solar cable sizing complying with IEC 60364-7-712.
    Evaluates thermal ampacity AND iterative voltage drop, automatically upsizing
    the conductor until both criteria are completely satisfied.
    """
    is_copper = material.lower().strip() in ("copper", "cu")
    # Resistivity at 70°C in ohm·mm²/m: Copper 0.02135, Aluminium 0.0350
    rho = COPPER_RESISTIVITY_OHM_MM2_PER_M_AT_70C if is_copper else 0.0350

    valid_keys = set(CABLE_AMPACITY_TABLE[0].keys()) - {"csa_mm2"}
    if method_key not in valid_keys:
        method_key = "c_2c"

    total_operating_current = design_current_a * max(1, num_parallel_strings)
    derated_divisor = derating_factor if derating_factor > 0 else 1.0
    required_tabulated_a = rnd((total_operating_current * safety_factor) / derated_divisor, 2)

    candidates = sorted(CABLE_AMPACITY_TABLE, key=lambda r: r["csa_mm2"])
    
    # 1. Thermal ampacity selection
    thermal_choice = None
    for row in candidates:
        amp = row.get(method_key)
        if amp is not None:
            effective_amp = amp if is_copper else amp * 0.78
            if effective_amp >= required_tabulated_a:
                thermal_choice = {
                    "csa_mm2": row["csa_mm2"],
                    "tabulated_amp": effective_amp
                }
                break

    if thermal_choice is None:
        return {
            "status": "FAIL",
            "message": f"Operating current {total_operating_current}A requires {required_tabulated_a}A tabulated ampacity, exceeding available cable sizes.",
            "operating_current_a": total_operating_current,
            "required_tabulated_a": required_tabulated_a
        }

    # 2. Voltage drop evaluation and iterative upsizing
    upsized_for_vd = False
    chosen_row = None
    chosen_drop_v = 0.0
    chosen_drop_pct = 0.0
    chosen_amp = 0.0

    start_csa = thermal_choice["csa_mm2"]
    eligible_candidates = [r for r in candidates if r["csa_mm2"] >= start_csa]

    for row in eligible_candidates:
        csa = row["csa_mm2"]
        amp = row.get(method_key)
        if amp is None:
            continue
        effective_amp = amp if is_copper else amp * 0.78

        # DC two-way voltage drop: Delta V = 2 * L * I * rho / CSA
        drop_v = (2.0 * length_m * total_operating_current * rho) / csa
        drop_pct = (drop_v / nominal_voltage_v) * 100.0 if nominal_voltage_v > 0 else 0.0

        if drop_pct <= max_vd_pct:
            chosen_row = row
            chosen_drop_v = rnd(drop_v, 2)
            chosen_drop_pct = rnd(drop_pct, 2)
            chosen_amp = effective_amp
            if csa > start_csa:
                upsized_for_vd = True
            break

    # If even largest cable exceeds max_vd_pct, pick largest available
    if chosen_row is None:
        chosen_row = eligible_candidates[-1]
        csa = chosen_row["csa_mm2"]
        amp = chosen_row.get(method_key, 0)
        chosen_amp = amp if is_copper else amp * 0.78
        chosen_drop_v = rnd((2.0 * length_m * total_operating_current * rho) / csa, 2)
        chosen_drop_pct = rnd((chosen_drop_v / nominal_voltage_v) * 100.0, 2) if nominal_voltage_v > 0 else 0.0
        upsized_for_vd = True

    power_loss_w = rnd(chosen_drop_v * total_operating_current, 1)
    status = "PASS" if chosen_drop_pct <= max_vd_pct else ("WARNING" if chosen_drop_pct <= 3.0 else "FAIL")

    return {
        "status": status,
        "material": "Copper" if is_copper else "Aluminium",
        "csa_mm2": chosen_row["csa_mm2"],
        "thermal_csa_mm2": start_csa,
        "upsized_for_voltage_drop": upsized_for_vd,
        "operating_current_a": rnd(total_operating_current, 2),
        "tabulated_ampacity_a": rnd(chosen_amp, 1),
        "required_tabulated_a": required_tabulated_a,
        "cable_ampacity_utilization_pct": rnd((required_tabulated_a / chosen_amp) * 100.0, 1) if chosen_amp > 0 else 100.0,
        "voltage_drop_v": chosen_drop_v,
        "voltage_drop_pct": chosen_drop_pct,
        "max_allowed_vd_pct": max_vd_pct,
        "power_loss_w": power_loss_w,
        "length_m": length_m,
        "nominal_voltage_v": nominal_voltage_v,
        "num_parallel_strings": num_parallel_strings,
        "show_calculation": {
            "operating_current_formula": "I_b = I_string * N_parallel_strings",
            "voltage_drop_formula": "Delta_V = (2 * L * I_b * rho) / CSA",
            "voltage_drop_pct_formula": "Delta_V% = (Delta_V / V_nominal) * 100%",
            "power_loss_formula": "P_loss = Delta_V * I_b"
        }
    }


def select_ac_cable_comprehensive(
    ac_power_kw: float,
    nominal_voltage_v: float,
    length_m: float,
    phases: int = 3,
    power_factor: float = 0.95,
    max_vd_pct: float = 3.0,
    method_key: str = "c_34c",
    derating_factor: float = 0.9,
    material: str = "copper",
    safety_factor: float = 1.25
):
    """
    Comprehensive AC cable sizing complying with BS 7671.
    Calculates design operating current from power and power factor, selects candidate
    cable by thermal ampacity, iteratively verifies AC voltage drop, and coordinates with breaker.
    """
    from .protection_sizing import select_protective_device

    valid_keys = set(CABLE_AMPACITY_TABLE[0].keys()) - {"csa_mm2"}
    if method_key not in valid_keys:
        method_key = "c_34c" if phases == 3 else "c_2c"

    is_copper = material.lower().strip() in ("copper", "cu")
    rho = COPPER_RESISTIVITY_OHM_MM2_PER_M_AT_70C if is_copper else 0.0350

    pf = min(1.0, max(0.70, power_factor))
    v_nom = max(100.0, nominal_voltage_v)

    # 1. Operating current calculation
    if phases == 3:
        operating_current_a = (ac_power_kw * 1000.0) / (math.sqrt(3.0) * v_nom * pf)
    else:
        operating_current_a = (ac_power_kw * 1000.0) / (v_nom * pf)

    operating_current_a = rnd(operating_current_a, 2)
    derated_divisor = derating_factor if derating_factor > 0 else 1.0
    required_tabulated_a = rnd((operating_current_a * safety_factor) / derated_divisor, 2)

    candidates = sorted(CABLE_AMPACITY_TABLE, key=lambda r: r["csa_mm2"])

    # 2. Thermal ampacity selection
    thermal_choice = None
    for row in candidates:
        amp = row.get(method_key)
        if amp is not None:
            effective_amp = amp if is_copper else amp * 0.78
            if effective_amp >= required_tabulated_a:
                thermal_choice = {
                    "csa_mm2": row["csa_mm2"],
                    "tabulated_amp": effective_amp
                }
                break

    if thermal_choice is None:
        return {
            "status": "FAIL",
            "message": f"AC load current {operating_current_a}A exceeds standard cable ampacities for installation method {method_key}.",
            "operating_current_a": operating_current_a,
            "required_tabulated_a": required_tabulated_a
        }

    # 3. Iterative voltage drop check
    start_csa = thermal_choice["csa_mm2"]
    eligible_candidates = [r for r in candidates if r["csa_mm2"] >= start_csa]

    chosen_row = None
    chosen_drop_v = 0.0
    chosen_drop_pct = 0.0
    chosen_amp = 0.0
    upsized_for_vd = False

    reactance_per_m = 0.00008  # 0.08 ohm/km typical 50Hz cable reactance
    sin_phi = math.sqrt(max(0.0, 1.0 - pf**2))

    for row in eligible_candidates:
        csa = row["csa_mm2"]
        amp = row.get(method_key)
        if amp is None:
            continue
        effective_amp = amp if is_copper else amp * 0.78
        r_per_m = rho / csa

        # AC voltage drop:
        # 3-phase: sqrt(3) * L * I * (R*cos_phi + X*sin_phi)
        # 1-phase: 2 * L * I * (R*cos_phi + X*sin_phi)
        factor = math.sqrt(3.0) if phases == 3 else 2.0
        drop_v = factor * length_m * operating_current_a * (r_per_m * pf + reactance_per_m * sin_phi)
        drop_pct = (drop_v / v_nom) * 100.0

        if drop_pct <= max_vd_pct:
            chosen_row = row
            chosen_drop_v = rnd(drop_v, 2)
            chosen_drop_pct = rnd(drop_pct, 2)
            chosen_amp = effective_amp
            if csa > start_csa:
                upsized_for_vd = True
            break

    if chosen_row is None:
        chosen_row = eligible_candidates[-1]
        csa = chosen_row["csa_mm2"]
        amp = chosen_row.get(method_key, 0)
        chosen_amp = amp if is_copper else amp * 0.78
        r_per_m = rho / csa
        factor = math.sqrt(3.0) if phases == 3 else 2.0
        chosen_drop_v = rnd(factor * length_m * operating_current_a * (r_per_m * pf + reactance_per_m * sin_phi), 2)
        chosen_drop_pct = rnd((chosen_drop_v / v_nom) * 100.0, 2)
        upsized_for_vd = True

    power_loss_w = rnd(factor * chosen_drop_v * operating_current_a * pf, 1)

    # 4. Protection Breaker Coordination
    protection_res = select_protective_device(
        design_current_a=operating_current_a,
        cable_ampacity_a=chosen_amp,
        safety_factor=safety_factor,
        allow_mccb=True
    )

    status = "PASS" if (chosen_drop_pct <= max_vd_pct and protection_res["status"] == "PASS") else (
        "WARNING" if chosen_drop_pct <= (max_vd_pct + 1.0) else "FAIL"
    )

    return {
        "status": status,
        "material": "Copper" if is_copper else "Aluminium",
        "phases": phases,
        "ac_power_kw": ac_power_kw,
        "nominal_voltage_v": v_nom,
        "power_factor": pf,
        "length_m": length_m,
        "operating_current_a": operating_current_a,
        "csa_mm2": chosen_row["csa_mm2"],
        "thermal_csa_mm2": start_csa,
        "upsized_for_voltage_drop": upsized_for_vd,
        "tabulated_ampacity_a": rnd(chosen_amp, 1),
        "required_tabulated_a": required_tabulated_a,
        "cable_ampacity_utilization_pct": rnd((required_tabulated_a / chosen_amp) * 100.0, 1) if chosen_amp > 0 else 100.0,
        "voltage_drop_v": chosen_drop_v,
        "voltage_drop_pct": chosen_drop_pct,
        "max_allowed_vd_pct": max_vd_pct,
        "power_loss_w": power_loss_w,
        "protection_device": protection_res,
        "show_calculation": {
            "operating_current_formula": "I_b = P_ac / (sqrt(3) * V_ac * cos_phi)" if phases == 3 else "I_b = P_ac / (V_ac * cos_phi)",
            "voltage_drop_formula": "Delta_V = sqrt(3) * L * I * (R*cos_phi + X*sin_phi)" if phases == 3 else "Delta_V = 2 * L * I * (R*cos_phi + X*sin_phi)",
            "rule_coordination": "I_b <= I_n <= I_z (BS 7671 compliant)"
        }
    }

