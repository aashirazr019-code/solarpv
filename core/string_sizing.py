"""
String sizing — temperature-adjusted voltage and panels-per-string range.
Conforms to BS 7671, IEC 60364-7-712, and inverter MPPT window bounds.
"""

STC_TEMP_C = 25


def rnd(n, dp):
    f = 10 ** dp
    return round(n * f) / f


def cold_voc(panel, min_design_temp_c):
    """Calculates maximum open-circuit voltage at site minimum design temperature."""
    coeff = panel.temp_coeff_voc
    voc = panel.voc * (1 + (coeff / 100) * (min_design_temp_c - STC_TEMP_C))
    return rnd(voc, 3)


def hot_vmp(panel, max_design_temp_c):
    """Calculates minimum operating voltage Vmp at site maximum design temperature."""
    coeff = panel.temp_coeff_vmp
    used_fallback = False
    if coeff is None:
        coeff = panel.temp_coeff_pmax
        used_fallback = True
    vmp = panel.vmp * (1 + (coeff / 100) * (max_design_temp_c - STC_TEMP_C))
    return rnd(vmp, 3), used_fallback


def cold_vmp(panel, min_design_temp_c):
    """Calculates maximum operating voltage Vmp at site minimum design temperature."""
    coeff = panel.temp_coeff_vmp
    used_fallback = False
    if coeff is None:
        coeff = panel.temp_coeff_pmax
        used_fallback = True
    vmp = panel.vmp * (1 + (coeff / 100) * (min_design_temp_c - STC_TEMP_C))
    return rnd(vmp, 3), used_fallback


def status_from_ratio(ratio):
    if ratio > 1.0:
        return "FAIL"
    if ratio >= 0.90:
        return "WARNING"
    return "PASS"


def panels_per_string_range(panel, inverter, project):
    """
    Calculates the allowable range of series-connected panels per string.
    Upper bound: Limited by Inverter Max DC Voltage AND Inverter Max MPPT Voltage.
    Lower bound: Limited by Inverter Min MPPT Voltage under maximum hot temperature.
    """
    voc_c = cold_voc(panel, project.min_design_temp_c)
    vmp_h, used_fallback = hot_vmp(panel, project.max_design_temp_c)
    vmp_c, _ = cold_vmp(panel, project.min_design_temp_c)

    # Upper limit from inverter max DC voltage
    max_panels_voc = int(inverter.max_dc_voltage_v // voc_c) if voc_c > 0 else 0
    # Upper limit from inverter max MPPT voltage
    max_panels_mppt = int(inverter.mppt_voltage_max_v // max(vmp_c, panel.vmp)) if vmp_c > 0 else max_panels_voc
    
    max_panels = min(max_panels_voc, max_panels_mppt) if max_panels_mppt > 0 else max_panels_voc
    # Lower limit from inverter min MPPT voltage (ceiling division)
    min_panels = int(-(-inverter.mppt_voltage_min_v // vmp_h)) if vmp_h > 0 else 1

    valid = (min_panels <= max_panels and max_panels > 0)

    return {
        "voc_cold": voc_c,
        "voc_cold_v": voc_c,
        "vmp_hot": vmp_h,
        "vmp_hot_v": vmp_h,
        "vmp_cold": vmp_c,
        "vmp_cold_v": vmp_c,
        "vmp_hot_used_pmax_fallback": used_fallback,
        "min_panels_per_string": min_panels,
        "max_panels_per_string": max_panels,
        "max_panels_voc_limit": max_panels_voc,
        "max_panels_mppt_limit": max_panels_mppt,
        "valid": valid,
        "show_calculation": {
            "panel_voc_stc": panel.voc,
            "panel_vmp_stc": panel.vmp,
            "temp_coeff_voc": panel.temp_coeff_voc,
            "temp_coeff_vmp_used": panel.temp_coeff_pmax if used_fallback else panel.temp_coeff_vmp,
            "temp_coeff_vmp_fallback_note": (
                "temp_coeff_vmp not available on datasheet — used temp_coeff_pmax as approximation"
                if used_fallback else None
            ),
            "min_design_temp_c": project.min_design_temp_c,
            "max_design_temp_c": project.max_design_temp_c,
            "voc_cold_v": voc_c,
            "vmp_hot_v": vmp_h,
            "vmp_cold_v": vmp_c,
            "inverter_max_dc_voltage_v": inverter.max_dc_voltage_v,
            "inverter_mppt_min_v": inverter.mppt_voltage_min_v,
            "inverter_mppt_max_v": inverter.mppt_voltage_max_v,
            "max_panels_by_voc": max_panels_voc,
            "max_panels_by_mppt": max_panels_mppt,
            "selected_max_panels": max_panels,
            "selected_min_panels": min_panels,
        },
    }


def voltage_check(panel, inverter, project, panels_per_string):
    """
    Performs deterministic electrical voltage verification for a selected panels-per-string count.
    Checks:
    1. Cold Voc <= Inverter Max DC Voltage (hard safety limit)
    2. Hot Vmp >= Inverter Min MPPT Voltage (under-voltage tracking limit)
    3. Cold Vmp <= Inverter Max MPPT Voltage (over-voltage tracking limit)
    """
    voc_c = cold_voc(panel, project.min_design_temp_c)
    vmp_h, _ = hot_vmp(panel, project.max_design_temp_c)
    vmp_c, _ = cold_vmp(panel, project.min_design_temp_c)

    string_voc_cold = rnd(voc_c * panels_per_string, 2)
    string_vmp_hot = rnd(vmp_h * panels_per_string, 2)
    string_vmp_cold = rnd(vmp_c * panels_per_string, 2)

    cold_ratio = string_voc_cold / inverter.max_dc_voltage_v if inverter.max_dc_voltage_v > 0 else 1.0
    cold_status = status_from_ratio(cold_ratio)

    mppt_min_pass = string_vmp_hot >= inverter.mppt_voltage_min_v
    mppt_max_pass = string_vmp_cold <= inverter.mppt_voltage_max_v
    within_mppt_range = mppt_min_pass and mppt_max_pass
    
    if within_mppt_range:
        hot_status = "PASS"
    elif not mppt_min_pass and mppt_max_pass:
        hot_status = "FAIL"  # Drops below MPPT min
    elif mppt_min_pass and not mppt_max_pass:
        hot_status = "WARNING" if string_vmp_hot <= inverter.mppt_voltage_max_v else "FAIL"
    else:
        hot_status = "FAIL"

    return {
        "cold": {
            "calculated_v": string_voc_cold,
            "string_voc_cold_v": string_voc_cold,
            "limit_v": inverter.max_dc_voltage_v,
            "margin_pct": rnd(cold_ratio * 100, 1),
            "status": cold_status,
        },
        "hot": {
            "calculated_v": string_vmp_hot,
            "string_vmp_hot_v": string_vmp_hot,
            "calculated_vmp_cold_v": string_vmp_cold,
            "min_v": inverter.mppt_voltage_min_v,
            "max_v": inverter.mppt_voltage_max_v,
            "status": hot_status,
        },
        "cold_vmp": {
            "calculated_v": string_vmp_cold,
            "string_vmp_cold_v": string_vmp_cold,
            "limit_v": inverter.mppt_voltage_max_v,
            "status": "PASS" if mppt_max_pass else "FAIL",
        },
        "show_calculation": {
            "string_voc_cold_v": string_voc_cold,
            "max_dc_voltage_limit_v": inverter.max_dc_voltage_v,
            "string_vmp_hot_v": string_vmp_hot,
            "string_vmp_cold_v": string_vmp_cold,
            "mppt_min_v": inverter.mppt_voltage_min_v,
            "mppt_max_v": inverter.mppt_voltage_max_v,
            "panels_per_string": panels_per_string,
        }
    }
