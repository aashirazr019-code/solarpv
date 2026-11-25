"""
Solar PV DC & AC Energy Production Engine.
Calculates daily, monthly, and annual energy yields for DC generation
and net grid-connected AC export after conversion and balance-of-system losses.
"""
import math
from typing import Dict, List, Optional
from .string_sizing import rnd

# Default monthly distribution weights based on typical tropical/sub-tropical solar profiles
# If monthly irradiance is not provided, uses standard 12-month variation profile normalized to annual PSH.
MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DEFAULT_MONTH_WEIGHTS = [0.98, 1.05, 1.08, 1.04, 0.95, 0.92, 0.94, 0.96, 1.00, 1.02, 1.03, 1.03]


def calculate_dc_capacity_from_modules(num_panels: int, panel_power_wp: float) -> float:
    """
    Computes nameplate DC capacity: P_dc = N_panels × P_mp / 1000 [kWp]
    """
    return rnd((num_panels * panel_power_wp) / 1000.0, 3)


def calculate_dc_production(
    dc_capacity_kwp: float,
    peak_sun_hours: Optional[float],
    temp_loss_pct: float = 5.0,
    soiling_pct: float = 2.0,
    mismatch_pct: float = 2.0,
    dc_cable_loss_pct: float = 1.0,
    shading_loss_pct: float = 0.0,
    monthly_psh_profile: Optional[List[float]] = None
) -> Dict:
    """
    Calculates expected DC photovoltaic energy generation.
    Formula:
        P_dc = N_panels × P_mp / 1000
        DC Derating Factor = (1 - temp/100) * (1 - soil/100) * (1 - mismatch/100) * (1 - dc_cable/100) * (1 - shade/100)
        E_daily_dc = P_dc * PSH * DC_derate [kWh/day]
        E_annual_dc = sum(E_monthly_dc) [kWh/year]
    """
    errors = []
    if dc_capacity_kwp is None or dc_capacity_kwp <= 0:
        errors.append("DC capacity must be greater than 0 kWp.")
    if peak_sun_hours is None or peak_sun_hours <= 0:
        errors.append("Solar resource data required.")
    for name, val in [
        ("Temperature loss", temp_loss_pct),
        ("Soiling loss", soiling_pct),
        ("Mismatch loss", mismatch_pct),
        ("DC cable loss", dc_cable_loss_pct),
        ("Shading loss", shading_loss_pct)
    ]:
        if val is None or val < 0 or val > 50:
            errors.append(f"{name} must be between 0% and 50%.")

    if errors:
        return {
            "status": "FAIL",
            "message": "Solar resource data required." if "Solar resource data required." in errors else errors[0],
            "errors": errors,
            "annual_dc_energy_kwh": 0.0,
            "annual_dc_energy_mwh": 0.0,
            "daily_dc_energy_kwh": 0.0,
            "specific_yield_dc_kwh_kwp": 0.0,
            "dc_derating_factor": 0.0,
            "monthly_breakdown": [],
            "show_calculation": {}
        }

    # Compound DC derating factor
    dc_derate = (
        (1.0 - temp_loss_pct / 100.0) *
        (1.0 - soiling_pct / 100.0) *
        (1.0 - mismatch_pct / 100.0) *
        (1.0 - dc_cable_loss_pct / 100.0) *
        (1.0 - shading_loss_pct / 100.0)
    )

    daily_dc_kwh = dc_capacity_kwp * peak_sun_hours * dc_derate

    # Monthly calculation
    monthly_breakdown = []
    annual_dc_kwh = 0.0

    for i in range(12):
        days = MONTH_DAYS[i]
        if monthly_psh_profile and len(monthly_psh_profile) == 12:
            m_psh = monthly_psh_profile[i]
        else:
            m_psh = peak_sun_hours * DEFAULT_MONTH_WEIGHTS[i]
        
        m_daily = dc_capacity_kwp * m_psh * dc_derate
        m_total = m_daily * days
        annual_dc_kwh += m_total
        
        monthly_breakdown.append({
            "month_num": i + 1,
            "month": MONTH_NAMES[i],
            "days": days,
            "psh": rnd(m_psh, 2),
            "daily_dc_kwh": rnd(m_daily, 2),
            "monthly_dc_kwh": rnd(m_total, 1),
            "monthly_dc_mwh": rnd(m_total / 1000.0, 3)
        })

    specific_yield = annual_dc_kwh / dc_capacity_kwp if dc_capacity_kwp > 0 else 0.0

    return {
        "status": "PASS",
        "errors": [],
        "dc_capacity_kwp": rnd(dc_capacity_kwp, 2),
        "peak_sun_hours": rnd(peak_sun_hours, 2),
        "dc_derating_factor": rnd(dc_derate, 4),
        "dc_derating_pct": rnd(dc_derate * 100.0, 2),
        "total_dc_losses_pct": rnd((1.0 - dc_derate) * 100.0, 2),
        "daily_dc_energy_kwh": rnd(daily_dc_kwh, 2),
        "annual_dc_energy_kwh": rnd(annual_dc_kwh, 1),
        "annual_dc_energy_mwh": rnd(annual_dc_kwh / 1000.0, 2),
        "specific_yield_dc_kwh_kwp": rnd(specific_yield, 1),
        "monthly_breakdown": monthly_breakdown,
        "show_calculation": {
            "dc_derating_formula": "(1 - temp) * (1 - soil) * (1 - mismatch) * (1 - dc_cable) * (1 - shade)",
            "daily_energy_formula": "P_dc * PSH * DC_derate",
            "annual_energy_formula": "sum(monthly_dc_kwh)"
        }
    }


def calculate_ac_production(
    dc_capacity_kwp: float,
    peak_sun_hours: float,
    inverter_efficiency_pct: float = 98.5,
    ac_cable_loss_pct: float = 0.8,
    transformer_loss_pct: float = 0.0,
    availability_pct: float = 99.0,
    temp_loss_pct: float = 5.0,
    soiling_pct: float = 2.0,
    mismatch_pct: float = 2.0,
    dc_cable_loss_pct: float = 1.0,
    shading_loss_pct: float = 0.0,
    monthly_psh_profile: Optional[List[float]] = None
) -> Dict:
    """
    Calculates expected net AC electricity generation fed to load/grid.
    
    Distinguishes gross DC generation from net exportable AC generation.
    Accounts for inverter inversion losses, AC line loss, transformer loss, and grid availability.
    """
    # 1. First calculate DC production
    dc_result = calculate_dc_production(
        dc_capacity_kwp=dc_capacity_kwp,
        peak_sun_hours=peak_sun_hours,
        temp_loss_pct=temp_loss_pct,
        soiling_pct=soiling_pct,
        mismatch_pct=mismatch_pct,
        dc_cable_loss_pct=dc_cable_loss_pct,
        shading_loss_pct=shading_loss_pct,
        monthly_psh_profile=monthly_psh_profile
    )

    if dc_result["status"] == "FAIL":
        return {
            "status": "FAIL",
            "errors": dc_result["errors"],
            "annual_ac_energy_kwh": 0.0,
            "annual_ac_energy_mwh": 0.0,
            "daily_ac_energy_kwh": 0.0,
            "performance_ratio": 0.0,
            "monthly_breakdown": []
        }

    errors = []
    if inverter_efficiency_pct <= 50 or inverter_efficiency_pct > 100:
        errors.append("Inverter efficiency must be between 50% and 100%.")
    if ac_cable_loss_pct < 0 or ac_cable_loss_pct > 20:
        errors.append("AC cable loss must be between 0% and 20%.")
    if transformer_loss_pct < 0 or transformer_loss_pct > 20:
        errors.append("Transformer loss must be between 0% and 20%.")
    if availability_pct <= 50 or availability_pct > 100:
        errors.append("Availability must be between 50% and 100%.")

    if errors:
        return {
            "status": "FAIL",
            "errors": errors,
            "annual_ac_energy_kwh": 0.0,
            "annual_ac_energy_mwh": 0.0,
            "daily_ac_energy_kwh": 0.0,
            "performance_ratio": 0.0,
            "monthly_breakdown": []
        }

    # AC conversion factor
    ac_conversion_factor = (
        (inverter_efficiency_pct / 100.0) *
        (1.0 - ac_cable_loss_pct / 100.0) *
        (1.0 - transformer_loss_pct / 100.0) *
        (availability_pct / 100.0)
    )

    # Total compound Performance Ratio (PR)
    overall_pr = dc_result["dc_derating_factor"] * ac_conversion_factor
    daily_ac_kwh = dc_result["daily_dc_energy_kwh"] * ac_conversion_factor
    annual_ac_kwh = dc_result["annual_dc_energy_kwh"] * ac_conversion_factor

    # Monthly breakdown with both DC and AC
    monthly_breakdown = []
    for m in dc_result["monthly_breakdown"]:
        m_ac_kwh = m["monthly_dc_kwh"] * ac_conversion_factor
        m_daily_ac = m["daily_dc_kwh"] * ac_conversion_factor
        monthly_breakdown.append({
            "month": m["month"],
            "days": m["days"],
            "psh": m["psh"],
            "dc_kwh": m["monthly_dc_kwh"],
            "ac_kwh": rnd(m_ac_kwh, 1),
            "ac_mwh": rnd(m_ac_kwh / 1000.0, 3),
            "daily_ac_kwh": rnd(m_daily_ac, 2),
            "inverter_loss_kwh": rnd(m["monthly_dc_kwh"] * (1.0 - inverter_efficiency_pct / 100.0), 1)
        })

    specific_yield_ac = annual_ac_kwh / dc_capacity_kwp if dc_capacity_kwp > 0 else 0.0

    return {
        "status": "PASS",
        "errors": [],
        "dc_capacity_kwp": rnd(dc_capacity_kwp, 2),
        "peak_sun_hours": rnd(peak_sun_hours, 2),
        "daily_dc_energy_kwh": dc_result["daily_dc_energy_kwh"],
        "annual_dc_energy_kwh": dc_result["annual_dc_energy_kwh"],
        "annual_dc_energy_mwh": dc_result["annual_dc_energy_mwh"],
        "daily_ac_energy_kwh": rnd(daily_ac_kwh, 2),
        "annual_ac_energy_kwh": rnd(annual_ac_kwh, 1),
        "annual_ac_energy_mwh": rnd(annual_ac_kwh / 1000.0, 2),
        "performance_ratio": rnd(overall_pr, 4),
        "performance_ratio_pct": rnd(overall_pr * 100.0, 2),
        "specific_yield_ac_kwh_kwp": rnd(specific_yield_ac, 1),
        "ac_conversion_factor": rnd(ac_conversion_factor, 4),
        "dc_to_ac_loss_pct": rnd((1.0 - ac_conversion_factor) * 100.0, 2),
        "monthly_breakdown": monthly_breakdown,
        "loss_waterfall": {
            "temperature_loss_pct": temp_loss_pct,
            "soiling_loss_pct": soiling_pct,
            "mismatch_loss_pct": mismatch_pct,
            "dc_cable_loss_pct": dc_cable_loss_pct,
            "shading_loss_pct": shading_loss_pct,
            "inverter_inefficiency_pct": rnd(100.0 - inverter_efficiency_pct, 2),
            "ac_cable_loss_pct": ac_cable_loss_pct,
            "transformer_loss_pct": transformer_loss_pct,
            "unavailability_pct": rnd(100.0 - availability_pct, 2),
            "net_performance_ratio_pct": rnd(overall_pr * 100.0, 2)
        },
        "show_calculation": {
            "overall_pr_formula": "DC_derate * (eta_inv) * (1 - ac_cable) * (1 - trafo) * (availability)",
            "annual_ac_formula": "Annual_DC_kWh * AC_conversion_factor",
            "specific_yield_formula": "Annual_AC_kWh / DC_capacity_kWp"
        }
    }
