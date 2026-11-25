"""
core/financial.py — Solar PV Financial Modeling & CEB/LECO ROI Engine
Calculates:
  - Capital Expenditure (CAPEX) breakdowns (Modules, Inverters, BOS, Switchgear, Labor, CEB Connection)
  - CEB Tariff Schemes: Net Metering, Net Accounting, Net Plus
  - Annual Revenue / Utility Bill Savings
  - Simple & Discounted Payback Periods
  - Net Present Value (NPV)
  - Internal Rate of Return (IRR)
  - Levelized Cost of Electricity (LCOE in LKR/kWh and USD/kWh)
  - 25-Year Cumulative Cash Flow Projection with PV Module Degradation

Authored and Designed by Eng. Aashir © 2026. All Rights Reserved.
"""
from typing import Dict, Any, List, Optional
import math


def calculate_capex(
    target_ac_kw: float,
    installed_dc_kwp: float,
    cost_per_watt_lkr: float = 180.0,
    ceb_processing_fee_lkr: float = 35000.0,
    ceb_meter_deposit_lkr: float = 25000.0
) -> Dict[str, Any]:
    """
    Estimates total project CAPEX based on installed DC capacity and standard Sri Lanka market rates.
    Default turnkey benchmark: ~LKR 160-200 / Wp (~USD 0.55-0.65 / Wp).
    """
    pv_watts = installed_dc_kwp * 1000.0
    total_epc_lkr = pv_watts * cost_per_watt_lkr

    # Breakdown distribution based on industry standard proportions:
    modules_lkr = total_epc_lkr * 0.42       # 42% PV Modules
    inverters_lkr = total_epc_lkr * 0.20     # 20% Inverters
    structures_lkr = total_epc_lkr * 0.12    # 12% Aluminium mounting & railings
    switchgear_cables_lkr = total_epc_lkr * 0.14  # 14% DC/AC switchgear, cables, earthing
    installation_labor_lkr = total_epc_lkr * 0.12 # 12% Labor, engineering & transport

    ceb_utility_fees_lkr = ceb_processing_fee_lkr + ceb_meter_deposit_lkr
    total_capex_lkr = total_epc_lkr + ceb_utility_fees_lkr

    return {
        "installed_dc_kwp": installed_dc_kwp,
        "target_ac_kw": target_ac_kw,
        "cost_per_watt_lkr": cost_per_watt_lkr,
        "modules_cost_lkr": round(modules_lkr, 2),
        "inverters_cost_lkr": round(inverters_lkr, 2),
        "mounting_structure_lkr": round(structures_lkr, 2),
        "switchgear_and_cables_lkr": round(switchgear_cables_lkr, 2),
        "installation_labor_lkr": round(installation_labor_lkr, 2),
        "ceb_utility_fees_lkr": round(ceb_utility_fees_lkr, 2),
        "total_epc_lkr": round(total_epc_lkr, 2),
        "total_capex_lkr": round(total_capex_lkr, 2),
        "total_capex_usd": round(total_capex_lkr / 305.0, 2)  # Benchmark USD/LKR rate: 305
    }


def calculate_solar_roi(
    capex_lkr: float,
    year_1_energy_kwh: float,
    scheme: str = "Net Accounting",
    feed_in_tariff_lkr: float = 37.0,
    retail_electricity_rate_lkr: float = 48.0,
    discount_rate_pct: float = 10.0,
    annual_degradation_pct: float = 0.55,
    annual_om_pct_of_capex: float = 1.0,
    om_escalation_pct: float = 4.0,
    tariff_escalation_pct: float = 2.0,
    project_life_years: int = 25
) -> Dict[str, Any]:
    """
    Computes 25-year financial performance, cash flows, NPV, IRR, LCOE, and payback period.
    Supported schemes:
      - "Net Accounting": Export paid at fixed Feed-In Tariff (default LKR 37.00/kWh).
      - "Net Metering": 100% offset of grid import at retail tariff (e.g. LKR 48.00/kWh).
      - "Net Plus": 100% generation exported to CEB grid at Feed-In Tariff.
    """
    discount_rate = discount_rate_pct / 100.0
    degradation = annual_degradation_pct / 100.0
    om_rate = annual_om_pct_of_capex / 100.0
    om_esc = om_escalation_pct / 100.0
    tariff_esc = tariff_escalation_pct / 100.0

    # Base initial rate per kWh
    if scheme in ("Net Accounting", "Net Plus"):
        base_tariff = feed_in_tariff_lkr
    else:  # Net Metering
        base_tariff = retail_electricity_rate_lkr

    yearly_data = []
    cumulative_cash_flow = -capex_lkr
    cumulative_discounted_cash_flow = -capex_lkr
    simple_payback_year = None
    discounted_payback_year = None

    total_generation_kwh = 0.0
    total_revenue_lkr = 0.0
    total_om_lkr = 0.0
    discounted_costs_sum = capex_lkr
    discounted_energy_sum = 0.0

    # Year 0 initial outlay
    yearly_data.append({
        "year": 0,
        "energy_kwh": 0.0,
        "tariff_lkr": round(base_tariff, 2),
        "revenue_lkr": 0.0,
        "om_cost_lkr": 0.0,
        "net_cash_flow_lkr": round(-capex_lkr, 2),
        "cumulative_cash_flow_lkr": round(cumulative_cash_flow, 2),
        "discounted_cash_flow_lkr": round(-capex_lkr, 2),
        "cumulative_discounted_cf_lkr": round(cumulative_discounted_cash_flow, 2)
    })

    prev_cum = cumulative_cash_flow
    prev_cum_disc = cumulative_discounted_cash_flow

    for y in range(1, project_life_years + 1):
        # Degraded generation
        gen_y = year_1_energy_kwh * ((1.0 - degradation) ** (y - 1))
        total_generation_kwh += gen_y

        # Tariff evolution (for Net Metering retail escalation; Net Accounting is fixed for 20 yrs per CEB code)
        if scheme == "Net Accounting":
            curr_tariff = base_tariff if y <= 20 else base_tariff * 0.60
        else:
            curr_tariff = base_tariff * ((1.0 + tariff_esc) ** (y - 1))

        rev_y = gen_y * curr_tariff
        total_revenue_lkr += rev_y

        # O&M Cost
        om_y = (capex_lkr * om_rate) * ((1.0 + om_esc) ** (y - 1))
        total_om_lkr += om_y

        # Net Cash Flow
        net_cf_y = rev_y - om_y

        # Discount factor
        df_y = (1.0 + discount_rate) ** y
        disc_cf_y = net_cf_y / df_y
        discounted_costs_sum += om_y / df_y
        discounted_energy_sum += gen_y / df_y

        cumulative_cash_flow += net_cf_y
        cumulative_discounted_cash_flow += disc_cf_y

        # Calculate Simple Payback
        if simple_payback_year is None and cumulative_cash_flow >= 0:
            fraction = abs(prev_cum) / net_cf_y if net_cf_y > 0 else 0
            simple_payback_year = round((y - 1) + fraction, 2)

        # Calculate Discounted Payback
        if discounted_payback_year is None and cumulative_discounted_cash_flow >= 0:
            fraction_d = abs(prev_cum_disc) / disc_cf_y if disc_cf_y > 0 else 0
            discounted_payback_year = round((y - 1) + fraction_d, 2)

        prev_cum = cumulative_cash_flow
        prev_cum_disc = cumulative_discounted_cash_flow

        yearly_data.append({
            "year": y,
            "energy_kwh": round(gen_y, 1),
            "tariff_lkr": round(curr_tariff, 2),
            "revenue_lkr": round(rev_y, 2),
            "om_cost_lkr": round(om_y, 2),
            "net_cash_flow_lkr": round(net_cf_y, 2),
            "cumulative_cash_flow_lkr": round(cumulative_cash_flow, 2),
            "discounted_cash_flow_lkr": round(disc_cf_y, 2),
            "cumulative_discounted_cf_lkr": round(cumulative_discounted_cash_flow, 2)
        })

    # Net Present Value (NPV)
    npv_lkr = cumulative_discounted_cash_flow

    # Internal Rate of Return (IRR) via binary search
    irr_pct = _calculate_irr([d["net_cash_flow_lkr"] for d in yearly_data])

    # Levelized Cost of Electricity (LCOE)
    # LCOE = Total Discounted Lifetime Costs / Total Discounted Lifetime Energy
    lcoe_lkr_per_kwh = (discounted_costs_sum / discounted_energy_sum) if discounted_energy_sum > 0 else 0.0

    return {
        "scheme": scheme,
        "initial_capex_lkr": round(capex_lkr, 2),
        "year_1_energy_kwh": round(year_1_energy_kwh, 1),
        "lifetime_generation_kwh": round(total_generation_kwh, 1),
        "lifetime_revenue_lkr": round(total_revenue_lkr, 2),
        "lifetime_om_cost_lkr": round(total_om_lkr, 2),
        "net_lifetime_benefit_lkr": round(total_revenue_lkr - total_om_lkr - capex_lkr, 2),
        "simple_payback_years": simple_payback_year or (project_life_years + 1),
        "discounted_payback_years": discounted_payback_year or (project_life_years + 1),
        "npv_lkr": round(npv_lkr, 2),
        "irr_pct": round(irr_pct, 2) if irr_pct is not None else 0.0,
        "lcoe_lkr_per_kwh": round(lcoe_lkr_per_kwh, 2),
        "lcoe_usd_per_kwh": round(lcoe_lkr_per_kwh / 305.0, 4),
        "roi_multiple": round((total_revenue_lkr - total_om_lkr) / capex_lkr, 2) if capex_lkr > 0 else 0.0,
        "yearly_cash_flows": yearly_data
    }


def _calculate_irr(cash_flows: List[float], max_iterations: int = 200, tolerance: float = 1e-5) -> Optional[float]:
    """
    Computes Internal Rate of Return (IRR) using bisection / secant search.
    """
    if not cash_flows or cash_flows[0] >= 0:
        return None

    def npv_at_rate(rate):
        val = 0.0
        for t, cf in enumerate(cash_flows):
            val += cf / ((1.0 + rate) ** t)
        return val

    low = -0.50
    high = 2.00

    npv_low = npv_at_rate(low)
    npv_high = npv_at_rate(high)

    if npv_low * npv_high > 0:
        # Check higher bound
        high = 5.0
        npv_high = npv_at_rate(high)
        if npv_low * npv_high > 0:
            return None

    for _ in range(max_iterations):
        mid = (low + high) / 2.0
        val_mid = npv_at_rate(mid)
        if abs(val_mid) < tolerance:
            return mid * 100.0
        if val_mid * npv_low < 0:
            high = mid
        else:
            low = mid
            npv_low = val_mid

    return ((low + high) / 2.0) * 100.0
