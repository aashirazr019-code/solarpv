"""
Inverter combination search — exact AC match, bounded subset-sum
over available inverter models/quantities, plus tolerance-based match.
"""
from .string_sizing import rnd


def _normalize_options(inverter_options):
    normalized = []
    for o in inverter_options:
        if hasattr(o, "inverter"):
            normalized.append({"inverter": o.inverter, "available_qty": o.available_qty})
        elif isinstance(o, dict):
            normalized.append(o)
        else:
            normalized.append({"inverter": getattr(o, "inverter"), "available_qty": getattr(o, "available_qty", 1)})
    return normalized


def find_exact_combinations(inverter_options, target_ac_kw, max_combinations=200):
    """inverter_options: list of {"inverter": Inverter, "available_qty": int} or InverterOption"""
    normalized_options = _normalize_options(inverter_options)
    results = []
    options = sorted(normalized_options, key=lambda o: -o["inverter"].rated_ac_power_kw)

    def recurse(index, remaining_kw, current_breakdown):
        if len(results) >= max_combinations:
            return
        if rnd(remaining_kw, 3) == 0 and current_breakdown:
            results.append([dict(b) for b in current_breakdown])
            return
        if index >= len(options) or remaining_kw < 0:
            return

        opt = options[index]
        inverter, available_qty = opt["inverter"], opt["available_qty"]
        max_usable = min(available_qty, int(remaining_kw // inverter.rated_ac_power_kw + 1e-9))

        for qty in range(max_usable, -1, -1):
            if len(results) >= max_combinations:
                return
            next_breakdown = (
                current_breakdown + [{"inverter": inverter, "quantity": qty}]
                if qty > 0
                else current_breakdown
            )
            recurse(index + 1, rnd(remaining_kw - qty * inverter.rated_ac_power_kw, 3), next_breakdown)

    recurse(0, target_ac_kw, [])
    return results

def find_combinations_with_tolerance(inverter_options, target_ac_kw, tolerance_pct=5.0, max_combinations=200, mode='closest'):
    """
    Enhanced combination search supporting tolerance-based matching.
    mode: 'exact' | 'closest' | 'oversized' | 'undersized' | 'any_within_tolerance'
    tolerance_pct: allowed deviation from target (e.g. 5.0 means +/-5%)
    Returns list of breakdowns sorted by proximity to target.
    """
    results = []
    normalized_options = _normalize_options(inverter_options)
    options = sorted(normalized_options, key=lambda o: -o["inverter"].rated_ac_power_kw)
    tolerance_kw = target_ac_kw * tolerance_pct / 100.0

    def recurse(index, current_kw, current_breakdown):
        if len(results) >= max_combinations:
            return
        diff = current_kw - target_ac_kw
        if current_breakdown and abs(diff) <= tolerance_kw:
            # Check mode filter
            if mode == 'oversized' and diff < 0:
                pass  # skip undersized
            elif mode == 'undersized' and diff > 0:
                pass  # skip oversized
            else:
                results.append(([dict(b) for b in current_breakdown], rnd(current_kw, 3)))
        if index >= len(options):
            return
        if current_kw > target_ac_kw + tolerance_kw:
            return  # pruning

        opt = options[index]
        inverter, available_qty = opt["inverter"], opt["available_qty"]
        max_usable = min(available_qty, int((target_ac_kw + tolerance_kw - current_kw) // inverter.rated_ac_power_kw + 1))
        max_usable = max(0, max_usable)

        for qty in range(max_usable, -1, -1):
            if len(results) >= max_combinations:
                return
            next_kw = current_kw + qty * inverter.rated_ac_power_kw
            next_breakdown = (
                current_breakdown + [{"inverter": inverter, "quantity": qty}]
                if qty > 0
                else current_breakdown
            )
            recurse(index + 1, next_kw, next_breakdown)

    recurse(0, 0.0, [])

    # Sort by proximity to target
    results.sort(key=lambda r: abs(r[1] - target_ac_kw))
    return [r[0] for r in results]
