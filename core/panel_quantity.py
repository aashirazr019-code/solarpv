"""
Panel Quantity & String Divisibility Engine.
Calculates required module count and resolves non-divisible panel/string scenarios.
"""
import math


def calculate_panel_quantity(target_dc_kwp, panel_rated_wp, max_available=None):
    """
    Calculates number of panels required to satisfy target DC capacity.
    Formula: N = ceil(P_dc * 1000 / P_mp)
    """
    if target_dc_kwp <= 0 or panel_rated_wp <= 0:
        return {
            "panel_count": 0,
            "actual_dc_kwp": 0.0,
            "surplus_pct": 0.0,
            "status": "FAIL",
            "message": "Target DC power and panel wattage must both be positive.",
            "show_calculation": {}
        }

    panel_count = math.ceil(target_dc_kwp * 1000 / panel_rated_wp)
    actual_dc_kwp = round((panel_count * panel_rated_wp) / 1000, 3)
    surplus_pct = round(((actual_dc_kwp - target_dc_kwp) / target_dc_kwp) * 100, 2) if target_dc_kwp else 0.0
    
    status = "PASS"
    warning = None
    if max_available is not None and panel_count > max_available:
        status = "FAIL"
        warning = f"Required panel count ({panel_count}) exceeds maximum available space/stock ({max_available})."

    return {
        "panel_count": panel_count,
        "actual_dc_kwp": actual_dc_kwp,
        "surplus_pct": surplus_pct,
        "status": status,
        "warning": warning,
        "show_calculation": {
            "target_dc_kwp": target_dc_kwp,
            "panel_rated_wp": panel_rated_wp,
            "formula": "ceil(target_dc_kwp * 1000 / panel_rated_wp)",
            "panel_count": panel_count,
            "actual_dc_kwp": actual_dc_kwp,
            "surplus_pct": surplus_pct
        }
    }


def calculate_string_and_panel_balance(total_panels, panels_per_string):
    """
    Resolves non-divisible panel quantities against panels per string.
    Example: 103 panels @ 20/string ->
      is_divisible = False,
      remainder = 3,
      round_down = 100 panels (5 strings of 20),
      round_up = 120 panels (6 strings of 20).
    Never generates a fractional string (e.g. 5.15 strings).
    """
    if total_panels <= 0 or panels_per_string <= 0:
        return {
            "is_divisible": False,
            "total_panels": total_panels,
            "panels_per_string": panels_per_string,
            "strings_count": 0,
            "remainder_panels": 0,
            "status": "FAIL",
            "message": "Panel quantity and panels per string must be greater than zero."
        }

    strings_count = total_panels // panels_per_string
    remainder_panels = total_panels % panels_per_string
    is_divisible = (remainder_panels == 0)

    round_down_panels = strings_count * panels_per_string
    round_down_strings = strings_count

    round_up_panels = (strings_count + 1) * panels_per_string
    round_up_strings = strings_count + 1

    warning = None
    if not is_divisible:
        warning = (
            f"Non-divisible panel count: {total_panels} panels cannot be divided into uniform strings of {panels_per_string}. "
            f"Result: {strings_count} complete strings with {remainder_panels} spare panels. "
            f"Option A: Use {round_down_panels} panels ({round_down_strings} strings). "
            f"Option B: Use {round_up_panels} panels ({round_up_strings} strings)."
        )

    return {
        "is_divisible": is_divisible,
        "total_panels_input": total_panels,
        "panels_per_string": panels_per_string,
        "strings_count": strings_count,
        "remainder_panels": remainder_panels,
        "recommended_panels": round_down_panels if remainder_panels < (panels_per_string / 2) else round_up_panels,
        "recommended_strings": round_down_strings if remainder_panels < (panels_per_string / 2) else round_up_strings,
        "round_down": {
            "panels": round_down_panels,
            "strings": round_down_strings,
            "unused_panels": remainder_panels
        },
        "round_up": {
            "panels": round_up_panels,
            "strings": round_up_strings,
            "additional_panels_needed": panels_per_string - remainder_panels
        },
        "status": "PASS" if is_divisible else "WARNING",
        "warning": warning
    }
