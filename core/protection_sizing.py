"""
MCB/MCCB and busbar selection.

Rule applied (BS 7671 style, standard PV/continuous-load practice):
    Ib <= In <= Iz
    Ib = design/load current
    In = protective device rated current (chosen here as >= 1.25 x Ib,
         the usual continuous-duty/PV safety factor, rounded UP to the
         next standard device rating)
    Iz = tabulated ampacity of the selected cable (from cable_sizing)

Busbar selection uses the same 1.25x safety-factor logic against the
total current the busbar must carry, rounded up to a standard busbar
current rating.
"""
from .electrical_data import MCB_STANDARD_RATINGS_A, MCCB_STANDARD_RATINGS_A, BUSBAR_STANDARD_RATINGS_A
from .string_sizing import rnd


def select_protective_device(design_current_a, cable_ampacity_a=None, safety_factor=1.25, allow_mccb=True):
    required_in = design_current_a * safety_factor

    device_type = "MCB"
    ratings = MCB_STANDARD_RATINGS_A
    chosen = next((r for r in ratings if r >= required_in), None)

    if chosen is None and allow_mccb:
        device_type = "MCCB"
        ratings = MCCB_STANDARD_RATINGS_A
        chosen = next((r for r in ratings if r >= required_in), None)

    if chosen is None:
        return {
            "status": "FAIL",
            "message": f"Required rating {rnd(required_in, 1)}A exceeds standard MCB/MCCB series in this table — use a larger frame device or split the load.",
            "required_in_a": rnd(required_in, 1),
        }

    checks = {"ib_le_in": design_current_a <= chosen}
    if cable_ampacity_a is not None:
        checks["in_le_iz"] = chosen <= cable_ampacity_a

    all_pass = all(checks.values())
    status = "PASS" if all_pass else "FAIL"

    return {
        "status": status,
        "device_type": device_type,
        "rated_current_a": chosen,
        "rating_a": chosen,
        "required_in_a": rnd(required_in, 1),
        "design_current_a": design_current_a,
        "cable_ampacity_a": cable_ampacity_a,
        "checks": checks,
        "rule_note": "Ib \u2264 In \u2264 Iz",
        "show_calculation": {
            "design_current_ib_a": design_current_a,
            "safety_factor": safety_factor,
            "required_in_a": rnd(required_in, 1),
            "chosen_device_type": device_type,
            "chosen_rated_current_in_a": chosen,
            "cable_ampacity_iz_a": cable_ampacity_a,
        },
    }


def select_busbar(total_current_a, safety_factor=1.25):
    required_a = total_current_a * safety_factor
    chosen = next((r for r in BUSBAR_STANDARD_RATINGS_A if r >= required_a), None)

    if chosen is None:
        return {
            "status": "FAIL",
            "message": f"Required busbar rating {rnd(required_a, 1)}A exceeds this table's standard series — a custom/larger busbar is needed.",
            "required_a": rnd(required_a, 1),
            "rating_a": None,
            "rated_current_a": None,
        }

    margin_pct = rnd((total_current_a / chosen) * 100, 1)
    return {
        "status": "PASS",
        "rated_current_a": chosen,
        "rating_a": chosen,
        "required_a": rnd(required_a, 1),
        "total_current_a": total_current_a,
        "margin_pct": margin_pct,
        "show_calculation": {
            "total_current_a": total_current_a,
            "safety_factor": safety_factor,
            "required_a": rnd(required_a, 1),
            "chosen_busbar_rating_a": chosen,
        },
    }

