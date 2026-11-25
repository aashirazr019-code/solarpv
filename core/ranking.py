"""
Composite ranking — ranks valid inverter configurations based on multi-criteria scoring:
1. Inverter unit count (simplicity / lower O&M)
2. DC/AC ratio proximity to preferred target
3. Combined MPPT and physical area utilization
"""
from .string_sizing import rnd

DEFAULT_WEIGHTS = {"unit_count": 0.3, "dc_ac_fit": 0.4, "utilization": 0.3}


def rank_configs(configs, dc_ac_preferred, weights=None):
    """
    Ranks evaluated configuration dictionaries by weighted engineering score.
    Safely handles empty configuration lists.
    """
    if not configs:
        return []

    if weights is None:
        weights = DEFAULT_WEIGHTS

    def get_ratio(c):
        if "dc_ac_ratio" in c:
            return c["dc_ac_ratio"]
        if isinstance(c.get("dc_ac"), dict):
            return c["dc_ac"].get("ratio", dc_ac_preferred)
        return dc_ac_preferred

    def get_mppt_util(c):
        if "mppt_utilization_pct" in c:
            return c["mppt_utilization_pct"]
        return c.get("avg_mppt_utilization_pct", 0.0)

    min_units = min(c["unit_count"] for c in configs)
    max_units = max(c["unit_count"] for c in configs)
    max_dc_ac_deviation = max(abs(get_ratio(c) - dc_ac_preferred) for c in configs)

    scored = []
    for c in configs:
        unit_count_score = (
            1.0 if max_units == min_units
            else 1.0 - (c["unit_count"] - min_units) / (max_units - min_units)
        )

        deviation = abs(get_ratio(c) - dc_ac_preferred)
        dc_ac_fit_score = 1.0 if max_dc_ac_deviation == 0 else 1.0 - deviation / max_dc_ac_deviation

        avg_util = (get_mppt_util(c) + c.get("area_utilization_pct", 0)) / 2 / 100
        utilization_score = max(0.0, min(1.0, avg_util))

        total_score = rnd(
            weights["unit_count"] * unit_count_score
            + weights["dc_ac_fit"] * dc_ac_fit_score
            + weights["utilization"] * utilization_score,
            4,
        )

        entry = dict(c)
        entry["score_breakdown"] = {
            "unit_count_score": rnd(unit_count_score, 3),
            "dc_ac_fit_score": rnd(dc_ac_fit_score, 3),
            "utilization_score": rnd(utilization_score, 3),
            "total_score": total_score,
        }
        scored.append(entry)

    scored.sort(key=lambda c: -c["score_breakdown"]["total_score"])
    for i, c in enumerate(scored):
        c["rank"] = i + 1
    return scored
