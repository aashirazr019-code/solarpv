"""
Current check — string Imp and Isc against MPPT hardware current limits.
Validates both maximum operating input current (Imp) and maximum short-circuit current (Isc).
"""
from .string_sizing import rnd


def current_check(panel, inverter, strings_per_mppt):
    """
    Validates array DC current against inverter MPPT hardware ratings:
    1. Short-Circuit Current (Isc): Hard safety constraint. If Isc > max_isc_a -> FAIL.
    2. Operating Current (Imp): Clipping constraint. If Imp > max_operating_current -> WARNING (inverter clamps current).
    """
    operating_current_a = rnd(panel.imp * strings_per_mppt, 2)
    isc_current_a = rnd(panel.isc * strings_per_mppt, 2)

    limit_op_a = inverter.max_input_current_per_mppt_a
    limit_isc_a = inverter.max_isc_per_mppt_a

    op_ratio = operating_current_a / limit_op_a if limit_op_a > 0 else 1.0
    isc_ratio = isc_current_a / limit_isc_a if limit_isc_a > 0 else 1.0

    # Short-circuit check (Hard safety limit)
    if isc_ratio > 1.0:
        isc_status = "FAIL"
    elif isc_ratio >= 0.90:
        isc_status = "WARNING"
    else:
        isc_status = "PASS"

    # Operating current check (Inverter power clipping limit)
    if op_ratio > 1.30:
        op_status = "FAIL"
    elif op_ratio > 1.0:
        op_status = "WARNING"
    elif op_ratio >= 0.90:
        op_status = "WARNING"
    else:
        op_status = "PASS"

    # Overall status: Isc failure is always FAIL.
    if isc_status == "FAIL" or op_status == "FAIL":
        status = "FAIL"
    elif isc_status == "WARNING" or op_status == "WARNING":
        status = "WARNING"
    else:
        status = "PASS"

    return {
        "strings_per_mppt": strings_per_mppt,
        "operating_current_a": operating_current_a,
        "limit_operating_current_a": limit_op_a,
        "operating_margin_pct": rnd(op_ratio * 100, 1),
        "operating_status": op_status,
        "isc_current_a": isc_current_a,
        "limit_isc_a": limit_isc_a,
        "margin_pct": rnd(isc_ratio * 100, 1),
        "isc_status": isc_status,
        "status": status,
        "show_calculation": {
            "panel_imp": panel.imp,
            "panel_isc": panel.isc,
            "strings_per_mppt": strings_per_mppt,
            "operating_current_a": operating_current_a,
            "limit_operating_current_a": limit_op_a,
            "operating_ratio": rnd(op_ratio, 3),
            "isc_current_a": isc_current_a,
            "limit_isc_a": limit_isc_a,
            "isc_ratio": rnd(isc_ratio, 3),
        },
    }
