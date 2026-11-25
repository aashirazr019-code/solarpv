"""
DC/AC ratio — evaluates array DC capacity vs inverter AC capacity.
Validates within project target range and permissible overload limits.
"""
from .string_sizing import rnd

WARNING_GRACE_PCT = 0.05


def dc_ac_ratio(panel_qty, panel_rated_wp, inverter_breakdown, project):
    """
    Calculates DC/AC ratio and validates against project constraints.
    Guards against zero AC capacity and invalid panel quantities.
    """
    dc_capacity_kwp = rnd((max(0, panel_qty) * max(0, panel_rated_wp)) / 1000, 3)
    ac_capacity_kw = sum(b["inverter"].rated_ac_power_kw * b["quantity"] for b in inverter_breakdown)

    if ac_capacity_kw <= 0:
        return {
            "dc_capacity_kwp": dc_capacity_kwp,
            "ac_capacity_kw": 0.0,
            "ratio": 0.0,
            "dc_ac_ratio_min": project.dc_ac_ratio_min,
            "dc_ac_ratio_preferred": project.dc_ac_ratio_preferred,
            "dc_ac_ratio_max": project.dc_ac_ratio_max,
            "status": "FAIL",
            "message": "Total inverter AC capacity is zero."
        }

    ratio = rnd(dc_capacity_kwp / ac_capacity_kw, 3)

    if project.dc_ac_ratio_min <= ratio <= project.dc_ac_ratio_max:
        status = "PASS"
    else:
        lower_grace = project.dc_ac_ratio_min * (1 - WARNING_GRACE_PCT)
        upper_grace = project.dc_ac_ratio_max * (1 + WARNING_GRACE_PCT)
        status = "WARNING" if lower_grace <= ratio <= upper_grace else "FAIL"

    return {
        "dc_capacity_kwp": dc_capacity_kwp,
        "ac_capacity_kw": ac_capacity_kw,
        "ratio": ratio,
        "dc_ac_ratio_min": project.dc_ac_ratio_min,
        "dc_ac_ratio_preferred": project.dc_ac_ratio_preferred,
        "dc_ac_ratio_max": project.dc_ac_ratio_max,
        "status": status,
        "show_calculation": {
            "panel_qty": panel_qty,
            "panel_rated_wp": panel_rated_wp,
            "dc_capacity_kwp": dc_capacity_kwp,
            "ac_capacity_kw": ac_capacity_kw,
            "ratio": ratio,
            "status": status
        }
    }
