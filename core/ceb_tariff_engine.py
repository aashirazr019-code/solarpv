"""
core/ceb_tariff_engine.py — Comprehensive CEB Electricity Tariff & Solar Financial Calculation Engine
Effective Date: 01 April 2026.
Authored by Eng. Aashir (c) 2026. All Rights Reserved.

Implements:
1. calculate_vdmc(): Normalized Virtual Days Monthly Consumption for billing period days.
2. calculate_ceb_bill(): Forward solver from units/TOU/demand to exact CEB bill with SSCL (2.5%).
3. estimate_units_from_bill(): Exact reverse solver from LKR bill to equivalent monthly units.
4. calculate_solar_generation(): 1 kW -> 120 kWh/month default.
5. calculate_solar_bill_impact(): None, Net Metering, Net Accounting, Net Plus models.
6. recommend_solar_capacity(): Sizing estimation based on customer consumption.
"""

import math
from typing import Dict, Any, Optional, Tuple, List
from .ceb_tariff_data import (
    TARIFF_CONFIG,
    SOLAR_CONFIG,
    get_tariff_info,
    get_net_plus_rate,
    get_default_generation_per_kw,
)


def calculate_vdmc(units: float, days: int = 30) -> float:
    """
    Calculate Virtual Days Monthly Consumption (VDMC) normalized to a 30-day billing cycle.
    Formula: VDMC = units / (days / 30.0)
    """
    if days <= 0:
        days = 30
    return units / (days / 30.0)


def calculate_sscl(subtotal: float) -> float:
    """Apply Social Security Contribution Levy (2.5% of bill subtotal)."""
    return round(subtotal * SOLAR_CONFIG["sscl_rate"], 2)


# ---------------------------------------------------------------------------
# FORWARD BILL CALCULATION ENGINE
# ---------------------------------------------------------------------------

def calculate_domestic_bill(units: float, days: int = 30) -> Dict[str, Any]:
    """
    Calculate Domestic (D-1) electricity bill.
    Rules:
    - Slabs <= 60 kWh: Incremental block (0-30 @ Rs.5, 31-60 @ Rs.9, fixed Rs.80 or Rs.210).
    - Slabs > 60 kWh: RETROACTIVE pricing (total units determines slab; slab rate applies to ALL units).
    """
    days_ratio = days / 30.0
    vdmc = calculate_vdmc(units, days)

    energy_charge = 0.0
    fixed_charge = 0.0
    applied_rate_description = ""
    slab_name = ""

    if vdmc <= 60.0:
        # Incremental blocks for <= 60
        if vdmc <= 30.0:
            energy_charge = units * 5.0
            fixed_charge = 80.0 * days_ratio
            applied_rate_description = f"{units:.1f} units @ Rs. 5.00/kWh"
            slab_name = "0–30 kWh Block"
        else:
            block1_units = min(units, 30.0 * days_ratio)
            block2_units = max(0.0, units - block1_units)
            energy_charge = (block1_units * 5.0) + (block2_units * 9.0)
            fixed_charge = 210.0 * days_ratio
            applied_rate_description = f"{block1_units:.1f} units @ Rs. 5.00 + {block2_units:.1f} units @ Rs. 9.00"
            slab_name = "31–60 kWh Block"
    else:
        # RETROACTIVE PRICING for > 60 kWh
        # The entire consumption is billed at the slab rate!
        if vdmc <= 90.0:
            rate = 20.0
            fixed = 400.0
            slab_name = "61–90 kWh Slab (Retroactive)"
        elif vdmc <= 120.0:
            rate = 28.0
            fixed = 1000.0
            slab_name = "91–120 kWh Slab (Retroactive)"
        elif vdmc <= 180.0:
            rate = 44.0
            fixed = 1500.0
            slab_name = "121–180 kWh Slab (Retroactive)"
        else:
            rate = 85.0
            fixed = 2100.0
            slab_name = "Above 180 kWh Slab (Retroactive)"

        energy_charge = units * rate
        fixed_charge = fixed * days_ratio
        applied_rate_description = f"{units:.1f} units @ Rs. {rate:.2f}/kWh (all units)"

    subtotal = round(energy_charge + fixed_charge, 2)
    sscl = calculate_sscl(subtotal)
    total_bill = round(subtotal + sscl, 2)

    return {
        "tariff_category": "Domestic",
        "units": units,
        "vdmc": round(vdmc, 2),
        "days": days,
        "slab_name": slab_name,
        "rate_description": applied_rate_description,
        "energy_charge_lkr": round(energy_charge, 2),
        "fixed_charge_lkr": round(fixed_charge, 2),
        "demand_charge_lkr": 0.0,
        "subtotal_lkr": subtotal,
        "sscl_lkr": sscl,
        "total_bill_lkr": total_bill,
        "effective_unit_rate_lkr": round(total_bill / units, 2) if units > 0 else 0.0,
    }


def calculate_tou_bill(
    category_key: str,
    units: float,
    days: int = 30,
    day_units: Optional[float] = None,
    peak_units: Optional[float] = None,
    off_peak_units: Optional[float] = None,
    max_demand_kva: float = 0.0,
) -> Dict[str, Any]:
    """Calculate Time-of-Use bill for Domestic TOU, Bulk (Rate 2/3), or EVCS."""
    info = get_tariff_info(category_key)
    days_ratio = days / 30.0

    # Handle TOU allocation if not explicitly specified
    if day_units is None or peak_units is None or off_peak_units is None:
        dist = info.get("default_distribution", {"day_pct": 0.60, "peak_pct": 0.15, "off_peak_pct": 0.25})
        day_units = units * dist["day_pct"]
        peak_units = units * dist["peak_pct"]
        off_peak_units = units * dist["off_peak_pct"]

    day_rate = info.get("day_rate_lkr", 40.0)
    peak_rate = info.get("peak_rate_lkr", 90.0)
    off_peak_rate = info.get("off_peak_rate_lkr", 28.0)
    fixed_charge = info.get("fixed_charge_lkr", 2100.0) * days_ratio

    day_cost = day_units * day_rate
    peak_cost = peak_units * peak_rate
    off_peak_cost = off_peak_units * off_peak_rate
    energy_charge = round(day_cost + peak_cost + off_peak_cost, 2)

    # Demand charge (if applicable)
    demand_rate = info.get("demand_charge_lkr_per_kva", 0.0)
    demand_charge = round(max_demand_kva * demand_rate * days_ratio, 2)

    subtotal = round(energy_charge + fixed_charge + demand_charge, 2)
    sscl = calculate_sscl(subtotal)
    total_bill = round(subtotal + sscl, 2)

    desc = f"Day: {day_units:.1f}u @ Rs.{day_rate} | Peak: {peak_units:.1f}u @ Rs.{peak_rate} | Off-Peak: {off_peak_units:.1f}u @ Rs.{off_peak_rate}"
    if demand_charge > 0:
        desc += f" | Demand: {max_demand_kva:.1f} kVA @ Rs.{demand_rate}/kVA"

    return {
        "tariff_category": category_key,
        "units": units,
        "vdmc": round(calculate_vdmc(units, days), 2),
        "days": days,
        "slab_name": "Time of Use (TOU)",
        "rate_description": desc,
        "day_units": round(day_units, 2),
        "peak_units": round(peak_units, 2),
        "off_peak_units": round(off_peak_units, 2),
        "energy_charge_lkr": energy_charge,
        "fixed_charge_lkr": round(fixed_charge, 2),
        "demand_charge_lkr": demand_charge,
        "subtotal_lkr": subtotal,
        "sscl_lkr": sscl,
        "total_bill_lkr": total_bill,
        "effective_unit_rate_lkr": round(total_bill / units, 2) if units > 0 else 0.0,
    }


def calculate_volume_differentiated_bill(category_key: str, units: float, days: int = 30) -> Dict[str, Any]:
    """Calculate bill for Industrial-1, General-1, Hotel-1, Agriculture."""
    info = get_tariff_info(category_key)
    days_ratio = days / 30.0
    vdmc = calculate_vdmc(units, days)
    threshold = info.get("threshold_kwh", 300)

    if vdmc <= threshold:
        tier = info["tier_1"]
        slab_name = f"<= {threshold} kWh Tier"
    else:
        tier = info["tier_2"]
        slab_name = f"> {threshold} kWh Tier"

    rate = tier["rate_lkr"]
    fixed = tier["fixed_charge_lkr"] * days_ratio
    energy_charge = round(units * rate, 2)
    subtotal = round(energy_charge + fixed, 2)
    sscl = calculate_sscl(subtotal)
    total_bill = round(subtotal + sscl, 2)

    return {
        "tariff_category": category_key,
        "units": units,
        "vdmc": round(vdmc, 2),
        "days": days,
        "slab_name": slab_name,
        "rate_description": f"{units:.1f} units @ Rs. {rate:.2f}/kWh (all units)",
        "energy_charge_lkr": energy_charge,
        "fixed_charge_lkr": round(fixed, 2),
        "demand_charge_lkr": 0.0,
        "subtotal_lkr": subtotal,
        "sscl_lkr": sscl,
        "total_bill_lkr": total_bill,
        "effective_unit_rate_lkr": round(total_bill / units, 2) if units > 0 else 0.0,
    }


def calculate_religious_bill(units: float, days: int = 30) -> Dict[str, Any]:
    """Calculate Religious & Charitable (R-1) incremental block bill."""
    days_ratio = days / 30.0
    vdmc = calculate_vdmc(units, days)
    info = get_tariff_info("Religious")
    slabs = info["slabs"]

    # Determine fixed charge from overall VDMC slab
    fixed_charge = 80.0
    for s in slabs:
        if vdmc <= s["max_kwh"]:
            fixed_charge = s["fixed_charge_lkr"] * days_ratio
            break

    # Incremental energy charge
    energy_charge = 0.0
    rem = units
    bounds = [
        (30.0 * days_ratio, 4.50),
        (60.0 * days_ratio, 4.50),
        (30.0 * days_ratio, 8.00),
        (60.0 * days_ratio, 19.00),
        (float("inf"), 30.00),
    ]

    for block_size, rate in bounds:
        if rem <= 0:
            break
        take = min(rem, block_size)
        energy_charge += take * rate
        rem -= take

    subtotal = round(energy_charge + fixed_charge, 2)
    sscl = calculate_sscl(subtotal)
    total_bill = round(subtotal + sscl, 2)

    return {
        "tariff_category": "Religious",
        "units": units,
        "vdmc": round(vdmc, 2),
        "days": days,
        "slab_name": "Religious Incremental Block",
        "rate_description": "Incremental slabs (Rs. 4.50 / 8.00 / 19.00 / 30.00)",
        "energy_charge_lkr": round(energy_charge, 2),
        "fixed_charge_lkr": round(fixed_charge, 2),
        "demand_charge_lkr": 0.0,
        "subtotal_lkr": subtotal,
        "sscl_lkr": sscl,
        "total_bill_lkr": total_bill,
        "effective_unit_rate_lkr": round(total_bill / units, 2) if units > 0 else 0.0,
    }


def calculate_flat_rate_bill(category_key: str, units: float, days: int = 30) -> Dict[str, Any]:
    """Calculate flat rate bill for Government-1."""
    info = get_tariff_info(category_key)
    days_ratio = days / 30.0
    rate = info.get("rate_lkr", 24.0)
    fixed = info.get("fixed_charge_lkr", 600.0) * days_ratio

    energy_charge = round(units * rate, 2)
    subtotal = round(energy_charge + fixed, 2)
    sscl = calculate_sscl(subtotal)
    total_bill = round(subtotal + sscl, 2)

    return {
        "tariff_category": category_key,
        "units": units,
        "vdmc": round(calculate_vdmc(units, days), 2),
        "days": days,
        "slab_name": "Flat Rate Supply",
        "rate_description": f"{units:.1f} units @ Rs. {rate:.2f}/kWh",
        "energy_charge_lkr": energy_charge,
        "fixed_charge_lkr": round(fixed, 2),
        "demand_charge_lkr": 0.0,
        "subtotal_lkr": subtotal,
        "sscl_lkr": sscl,
        "total_bill_lkr": total_bill,
        "effective_unit_rate_lkr": round(total_bill / units, 2) if units > 0 else 0.0,
    }


def calculate_ceb_bill(
    tariff_category: str,
    units: float,
    days: int = 30,
    max_demand_kva: float = 0.0,
    day_units: Optional[float] = None,
    peak_units: Optional[float] = None,
    off_peak_units: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Central dispatcher function for calculating CEB electricity bills across all categories.
    """
    if units < 0:
        units = 0.0
    if days <= 0:
        days = 30

    info = get_tariff_info(tariff_category)
    ttype = info.get("type", "domestic_slab")

    if ttype == "domestic_slab":
        return calculate_domestic_bill(units, days)
    elif ttype in ("tou", "bulk_tou"):
        return calculate_tou_bill(
            tariff_category, units, days, day_units, peak_units, off_peak_units, max_demand_kva
        )
    elif ttype == "volume_differentiated":
        return calculate_volume_differentiated_bill(tariff_category, units, days)
    elif ttype == "incremental_block":
        return calculate_religious_bill(units, days)
    elif ttype == "flat_rate":
        return calculate_flat_rate_bill(tariff_category, units, days)
    else:
        return calculate_domestic_bill(units, days)


# ---------------------------------------------------------------------------
# REVERSE BILL -> UNITS ESTIMATION ENGINE (Bidirectional live solver)
# ---------------------------------------------------------------------------

def estimate_units_from_bill(
    target_bill_lkr: float,
    tariff_category: str = "Domestic",
    days: int = 30,
    max_demand_kva: float = 0.0,
    tou_distribution: Optional[Dict[str, float]] = None,
) -> float:
    """
    Solve for equivalent monthly consumption units (kWh) from a given CEB electricity bill in LKR.
    Accounts for SSCL (2.5%), fixed charge, demand charge, and nonlinear / retroactive slab boundaries.
    """
    if target_bill_lkr <= 0:
        return 0.0
    if days <= 0:
        days = 30

    days_ratio = days / 30.0
    # Step 1: Remove SSCL
    subtotal = target_bill_lkr / (1.0 + SOLAR_CONFIG["sscl_rate"])

    info = get_tariff_info(tariff_category)
    ttype = info.get("type", "domestic_slab")

    # CASE A: Domestic (Incremental <=60, Retroactive >60)
    if ttype == "domestic_slab":
        # 1. Test 0-30 block: fixed = 80, rate = 5
        sub_30 = (30.0 * days_ratio * 5.0) + (80.0 * days_ratio)
        if subtotal <= sub_30:
            fixed = 80.0 * days_ratio
            if subtotal <= fixed:
                return round(max(0.0, subtotal / 5.0), 2)
            return round((subtotal - fixed) / 5.0, 2)

        # 2. Test 31-60 block: fixed = 210, 30u @ 5, rest @ 9
        sub_60 = (30.0 * days_ratio * 5.0) + (30.0 * days_ratio * 9.0) + (210.0 * days_ratio)
        if subtotal <= sub_60:
            fixed = 210.0 * days_ratio
            energy_rem = subtotal - fixed - (30.0 * days_ratio * 5.0)
            u_b2 = max(0.0, energy_rem / 9.0)
            return round((30.0 * days_ratio) + u_b2, 2)

        # 3. Retroactive slabs > 60 kWh
        # Candidate 1: 61-90 (rate 20, fixed 400)
        c1_sub_min = (60.0 * days_ratio * 20.0) + (400.0 * days_ratio)
        c1_sub_max = (90.0 * days_ratio * 20.0) + (400.0 * days_ratio)
        if c1_sub_min <= subtotal <= c1_sub_max:
            return round((subtotal - (400.0 * days_ratio)) / 20.0, 2)

        # Candidate 2: 91-120 (rate 28, fixed 1000)
        c2_sub_min = (90.0 * days_ratio * 28.0) + (1000.0 * days_ratio)
        c2_sub_max = (120.0 * days_ratio * 28.0) + (1000.0 * days_ratio)
        if c2_sub_min <= subtotal <= c2_sub_max:
            return round((subtotal - (1000.0 * days_ratio)) / 28.0, 2)

        # Candidate 3: 121-180 (rate 44, fixed 1500)
        c3_sub_min = (120.0 * days_ratio * 44.0) + (1500.0 * days_ratio)
        c3_sub_max = (180.0 * days_ratio * 44.0) + (1500.0 * days_ratio)
        if c3_sub_min <= subtotal <= c3_sub_max:
            return round((subtotal - (1500.0 * days_ratio)) / 44.0, 2)

        # Candidate 4: >180 (rate 85, fixed 2100)
        c4_sub_min = (180.0 * days_ratio * 85.0) + (2100.0 * days_ratio)
        if subtotal >= c4_sub_min:
            return round((subtotal - (2100.0 * days_ratio)) / 85.0, 2)

        # Handling Retroactive Boundary Gaps:
        # If subtotal falls in gap between sub_60 and c1_sub_min (e.g. 630 to 1600):
        if subtotal < c1_sub_min:
            # Interpolate smoothly between 60 and 61
            frac = max(0.0, min(1.0, (subtotal - sub_60) / max(1.0, c1_sub_min - sub_60)))
            return round((60.0 + frac) * days_ratio, 2)
        elif subtotal < c2_sub_min:
            frac = max(0.0, min(1.0, (subtotal - c1_sub_max) / max(1.0, c2_sub_min - c1_sub_max)))
            return round((90.0 + frac) * days_ratio, 2)
        elif subtotal < c3_sub_min:
            frac = max(0.0, min(1.0, (subtotal - c2_sub_max) / max(1.0, c3_sub_min - c2_sub_max)))
            return round((120.0 + frac) * days_ratio, 2)
        else:
            frac = max(0.0, min(1.0, (subtotal - c3_sub_max) / max(1.0, c4_sub_min - c3_sub_max)))
            return round((180.0 + frac) * days_ratio, 2)

    # CASE B: Volume Differentiated (Industrial-1, General-1, Hotel-1, Agriculture)
    elif ttype == "volume_differentiated":
        thresh = info["threshold_kwh"] * days_ratio
        t1_rate = info["tier_1"]["rate_lkr"]
        t1_fixed = info["tier_1"]["fixed_charge_lkr"] * days_ratio
        t2_rate = info["tier_2"]["rate_lkr"]
        t2_fixed = info["tier_2"]["fixed_charge_lkr"] * days_ratio

        max_t1_sub = (thresh * t1_rate) + t1_fixed
        min_t2_sub = (thresh * t2_rate) + t2_fixed

        if subtotal <= max_t1_sub:
            return round(max(0.0, (subtotal - t1_fixed) / t1_rate), 2)
        elif subtotal >= min_t2_sub:
            return round((subtotal - t2_fixed) / t2_rate, 2)
        else:
            # Between threshold steps
            return round(thresh, 2)

    # CASE C: Flat Rate (Government-1)
    elif ttype == "flat_rate":
        fixed = info.get("fixed_charge_lkr", 600.0) * days_ratio
        rate = info.get("rate_lkr", 24.0)
        return round(max(0.0, (subtotal - fixed) / rate), 2)

    # CASE D: TOU and Bulk Categories
    elif ttype in ("tou", "bulk_tou"):
        fixed = info.get("fixed_charge_lkr", 2100.0) * days_ratio
        demand_charge = max_demand_kva * info.get("demand_charge_lkr_per_kva", 0.0) * days_ratio

        net_sub = max(0.0, subtotal - fixed - demand_charge)
        dist = tou_distribution or info.get("default_distribution", {"day_pct": 0.60, "peak_pct": 0.15, "off_peak_pct": 0.25})

        avg_rate = (
            dist.get("day_pct", 0.60) * info.get("day_rate_lkr", 40.0)
            + dist.get("peak_pct", 0.15) * info.get("peak_rate_lkr", 90.0)
            + dist.get("off_peak_pct", 0.25) * info.get("off_peak_rate_lkr", 28.0)
        )
        return round(net_sub / avg_rate, 2) if avg_rate > 0 else 0.0

    # CASE E: Religious
    elif ttype == "incremental_block":
        # Binary search / root-finding approximation for monotonic incremental block
        low, high = 0.0, 5000.0
        best_u = 0.0
        for _ in range(30):
            mid = (low + high) / 2.0
            calc = calculate_religious_bill(mid, days)
            if abs(calc["total_bill_lkr"] - target_bill_lkr) < 1.0:
                best_u = mid
                break
            elif calc["total_bill_lkr"] < target_bill_lkr:
                low = mid
                best_u = mid
            else:
                high = mid
                best_u = mid
        return round(best_u, 2)

    return 0.0


# ---------------------------------------------------------------------------
# SOLAR SYSTEM GENERATION & SAVINGS / REVENUE CALCULATOR
# ---------------------------------------------------------------------------

def calculate_solar_generation(solar_capacity_kw: float, gen_per_kw_month: Optional[float] = None) -> float:
    """
    Calculate estimated monthly solar PV generation.
    Default benchmark: 5 kW -> 600 kWh/month => 120 kWh/kW/month.
    """
    rate = gen_per_kw_month if gen_per_kw_month is not None else get_default_generation_per_kw()
    return round(max(0.0, solar_capacity_kw) * rate, 2)


def calculate_solar_bill_impact(
    consumption_kwh: float,
    solar_capacity_kw: float,
    scheme: str = "Net Accounting",
    tariff_category: str = "Domestic",
    days: int = 30,
    brought_forward_kwh: float = 0.0,
    max_demand_kva: float = 0.0,
    gen_per_kw_month: Optional[float] = None,
    export_tariff_lkr: float = 19.0,
    net_accounting_export_rate_lkr: float = 37.0,
) -> Dict[str, Any]:
    """
    Complete calculation of Customer Monthly Bill After Solar across:
    - None (No Solar offset)
    - Net Metering (1:1 offset + unit credit rollover)
    - Net Accounting (Separate CEB import billing + solar export credit)
    - Net Plus (100% grid import billing + 100% solar feed-in income @ export_tariff_lkr/kWh)

    Parameters
    ----------
    export_tariff_lkr : float
        Net Plus CEB feed-in tariff (LKR/kWh). Default 19.00 LKR/kWh (PUCSL Net Plus rate).
        User-configurable — change in CEB Tariff Calculator page.
    net_accounting_export_rate_lkr : float
        Net Accounting excess export credit rate (LKR/kWh). Default 37.00 LKR/kWh
        (CEB standard Feed-in Tariff for Net Accounting excess generation).
    """
    solar_gen_kwh = calculate_solar_generation(solar_capacity_kw, gen_per_kw_month)
    bill_before = calculate_ceb_bill(tariff_category, consumption_kwh, days, max_demand_kva)

    coverage_pct = round((solar_gen_kwh / consumption_kwh * 100.0), 1) if consumption_kwh > 0 else 0.0

    # Output metrics
    grid_import_kwh = 0.0
    grid_export_kwh = 0.0
    carry_forward_kwh = 0.0
    solar_used_kwh = 0.0
    bill_after_solar_lkr = 0.0
    solar_export_income_lkr = 0.0
    scheme_explanation = ""

    # 1. NONE
    if scheme == "None" or solar_capacity_kw <= 0:
        grid_import_kwh = consumption_kwh
        grid_export_kwh = 0.0
        solar_used_kwh = 0.0
        bill_after_solar_lkr = bill_before["total_bill_lkr"]
        solar_export_income_lkr = 0.0
        scheme_explanation = "Standard utility supply without solar self-generation adjustment."

    # 2. NET METERING
    elif scheme == "Net Metering":
        total_available_kwh = solar_gen_kwh + brought_forward_kwh
        if total_available_kwh >= consumption_kwh:
            grid_import_kwh = 0.0
            carry_forward_kwh = round(total_available_kwh - consumption_kwh, 2)
            grid_export_kwh = carry_forward_kwh
            solar_used_kwh = consumption_kwh
            # Zero energy bill, but standard fixed charge + SSCL applies
            zero_energy_calc = calculate_ceb_bill(tariff_category, 0.0, days, max_demand_kva)
            bill_after_solar_lkr = zero_energy_calc["total_bill_lkr"]
            solar_export_income_lkr = 0.0
            scheme_explanation = f"Solar completely offset consumption. {carry_forward_kwh:.1f} kWh banked as unit credit for next month."
        else:
            grid_import_kwh = round(consumption_kwh - total_available_kwh, 2)
            carry_forward_kwh = 0.0
            grid_export_kwh = 0.0
            solar_used_kwh = total_available_kwh
            net_import_calc = calculate_ceb_bill(tariff_category, grid_import_kwh, days, max_demand_kva)
            bill_after_solar_lkr = net_import_calc["total_bill_lkr"]
            solar_export_income_lkr = 0.0
            scheme_explanation = f"Solar offset {total_available_kwh:.1f} kWh. Remaining {grid_import_kwh:.1f} kWh billed at applicable tariff."

    # 3. NET ACCOUNTING
    elif scheme == "Net Accounting":
        # Customer first self-consumes onsite solar
        solar_used_kwh = min(consumption_kwh, solar_gen_kwh)
        grid_import_kwh = max(0.0, round(consumption_kwh - solar_used_kwh, 2))
        grid_export_kwh = max(0.0, round(solar_gen_kwh - consumption_kwh, 2))

        # Import electricity is billed using normal CEB tariff
        import_calc = calculate_ceb_bill(tariff_category, grid_import_kwh, days, max_demand_kva)
        bill_after_solar_lkr = import_calc["total_bill_lkr"]

        # Export electricity is credited at the Net Accounting CEB FIT (default LKR 37.00/kWh)
        # Caller may pass a custom net_accounting_export_rate_lkr to override
        net_acc_export_rate = max(net_accounting_export_rate_lkr, 0.0)
        solar_export_income_lkr = round(grid_export_kwh * net_acc_export_rate, 2)

        scheme_explanation = (
            f"Onsite offset: {solar_used_kwh:.1f} kWh. Grid import ({grid_import_kwh:.1f} kWh) billed at Rs.{bill_after_solar_lkr:,.2f}. "
            f"Excess export ({grid_export_kwh:.1f} kWh) credited at Rs.{net_acc_export_rate:.2f}/kWh (Rs.{solar_export_income_lkr:,.2f})."
        )

    # 4. NET PLUS
    elif scheme == "Net Plus":
        # 100% of customer consumption is imported from grid
        grid_import_kwh = consumption_kwh
        solar_used_kwh = 0.0
        bill_after_solar_lkr = bill_before["total_bill_lkr"]

        # 100% of solar generation is exported to CEB grid at the configurable export tariff
        grid_export_kwh = solar_gen_kwh
        net_plus_rate = max(export_tariff_lkr, 0.0)  # User-configurable, default 19.00 LKR/kWh
        solar_export_income_lkr = round(grid_export_kwh * net_plus_rate, 2)

        scheme_explanation = (
            f"100% solar generation ({solar_gen_kwh:.1f} kWh) exported at Rs.{net_plus_rate:.2f}/kWh "
            f"earning Rs.{solar_export_income_lkr:,.2f}/month. Customer consumption is fully billed from grid."
        )

    # Net monthly cost to customer
    net_monthly_cost = round(bill_after_solar_lkr - solar_export_income_lkr, 2)
    monthly_saving = round(bill_before["total_bill_lkr"] - net_monthly_cost, 2)
    annual_saving = round(monthly_saving * 12.0, 2)

    return {
        "scheme": scheme,
        "tariff_category": tariff_category,
        "consumption_kwh": consumption_kwh,
        "solar_capacity_kw": solar_capacity_kw,
        "solar_generation_kwh": solar_gen_kwh,
        "solar_coverage_pct": coverage_pct,
        "solar_used_kwh": round(solar_used_kwh, 2),
        "grid_import_kwh": round(grid_import_kwh, 2),
        "grid_export_kwh": round(grid_export_kwh, 2),
        "carry_forward_kwh": round(carry_forward_kwh, 2),
        "brought_forward_kwh": round(brought_forward_kwh, 2),
        "bill_before_solar_lkr": bill_before["total_bill_lkr"],
        "bill_after_solar_lkr": bill_after_solar_lkr,
        "solar_export_income_lkr": solar_export_income_lkr,
        "net_monthly_cost_lkr": net_monthly_cost,
        "monthly_saving_lkr": monthly_saving,
        "annual_saving_lkr": annual_saving,
        "explanation": scheme_explanation,
    }


def recommend_solar_capacity(monthly_consumption_kwh: float, gen_per_kw_month: Optional[float] = None) -> float:
    """
    Recommend practical Solar PV system capacity (kW) based on customer monthly electricity consumption.
    Formula: capacity = consumption / (120 kWh/kW/month) rounded to standard commercial ratings.
    """
    if monthly_consumption_kwh <= 0:
        return 5.0

    rate = gen_per_kw_month if gen_per_kw_month is not None else get_default_generation_per_kw()
    raw_kw = monthly_consumption_kwh / rate

    # Practical sizing grid
    standard_sizes = [
        1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0,
        12.0, 13.0, 15.0, 17.5, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0,
        80.0, 100.0, 110.0, 125.0, 150.0, 200.0, 250.0, 260.0, 300.0, 500.0
    ]

    # Select closest size >= raw_kw (or closest size)
    best_size = standard_sizes[0]
    min_diff = float("inf")
    for s in standard_sizes:
        diff = abs(s - raw_kw)
        if diff < min_diff:
            min_diff = diff
            best_size = s

    return best_size
