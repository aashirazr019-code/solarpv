"""
pages/34_💰_Financial_ROI.py — Solar PV Financial Modeling & CEB / LECO ROI Engine
Calculates Turnkey CAPEX, Payback Period, Net Present Value (NPV), Internal Rate of Return (IRR),
Levelized Cost of Electricity (LCOE), and 25-Year Cash Flow projections.

Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
"""
import io
import csv
import streamlit as st
import pandas as pd
from ui.components import page_header, nav_sidebar
from ui.styles import apply_custom_css
from core.project_state import (
    get_active_project,
    get_active_panel,
    get_dynamic_system,
    recalculate_system_state,
    render_active_project_banner
)
from core.unified_dataset import get_unified_engineering_dataset
from core.financial import calculate_capex, calculate_solar_roi
from core.ceb_tariff_data import get_net_plus_rate, TARIFF_CONFIG

try:
    st.set_page_config(page_title="Financial Modeling & ROI — Solar PV Platform", page_icon="💰", layout="wide")
except Exception:
    pass

apply_custom_css()
nav_sidebar()
render_active_project_banner()

page_header("Financial Modeling & CEB / LECO ROI Analysis", "Capital expenditure, payback period, NPV, IRR, LCOE, and 25-year bankability cash flows", icon="💰")

proj = get_active_project()
panel = get_active_panel()
dynamic_sys = get_dynamic_system()

if not dynamic_sys or "per_inverter_designs" not in dynamic_sys:
    dynamic_sys = recalculate_system_state()

ac_kw = float(dynamic_sys.get("actual_ac_kw", proj.get("target_ac_capacity_kw", 13.0)))
if ac_kw <= 0:
    ac_kw = 13.0

ds = get_unified_engineering_dataset(target_kw=ac_kw, panel=panel, custom_project_params=proj)
pv_sub = ds["pv_subsystem"]
energy = ds["energy_yield"]

dc_kwp = float(pv_sub.get("dc_capacity_kwp", round(ac_kw * 1.25, 2)))
annual_kwh = float(energy.get("annual_ac_energy_kwh", round(dc_kwp * 4.5 * 365 * 0.795, 0)))

# ---------------------------------------------------------------------------
# SECTION 1: Financial & Commercial Parameters Form
# ---------------------------------------------------------------------------
st.markdown("### 1. Commercial Inputs & Utility Tariff Structure")
st.info("💡 **CEB Tariff Integration:** Feed-in tariffs and retail rates are aligned with official PUCSL / CEB tariffs (effective 01 April 2026). For comprehensive monthly bill modeling, retroactive domestic calculations, and bidirectional bill-to-units conversion, use the **[⚡ CEB Tariff Calculator](35_⚡_CEB_Tariff_Calculator)**.")

col_in1, col_in2, col_in3 = st.columns(3)

with col_in1:
    scheme = st.selectbox(
        "CEB / LECO Interconnection Scheme",
        ["Net Accounting", "Net Metering", "Net Plus"],
        index=0,
        help="Net Accounting: Export paid at fixed Feed-In Tariff (FIT). Net Metering: Offsets utility bill. Net Plus: 100% exported."
    )
    cost_per_watt = st.number_input(
        "Turnkey System Cost (LKR / Wp)",
        min_value=100.0,
        max_value=400.0,
        value=180.0,
        step=5.0,
        help="Sri Lanka market benchmark: LKR 160–200/Wp for tier-1 components."
    )

with col_in2:
    if scheme == "Net Plus":
        default_fit = float(proj.get("ceb_export_tariff_lkr", get_net_plus_rate()))
        tariff_rate = st.number_input(
            "CEB Net Plus Feed-In Tariff (LKR / kWh)",
            min_value=10.0,
            max_value=80.0,
            value=default_fit,
            step=1.0,
            help="Standard CEB export feed-in tariff is LKR 19.00/kWh."
        )
    elif scheme == "Net Accounting":
        default_fit = float(proj.get("ceb_export_tariff_lkr", 19.0))
        tariff_rate = st.number_input(
            "CEB Feed-In Tariff (LKR / kWh)",
            min_value=10.0,
            max_value=80.0,
            value=default_fit,
            step=1.0,
            help="Standard CEB export feed-in tariff is LKR 19.00/kWh."
        )
    else:
        tariff_rate = st.number_input(
            "Retail Grid Electricity Rate (LKR / kWh)",
            min_value=10.0,
            max_value=150.0,
            value=48.0,
            step=2.0,
            help="Avoided utility grid tariff under Net Metering 1:1 offset."
        )

    discount_rate = st.number_input("Discount / Cost of Capital (%)", min_value=4.0, max_value=25.0, value=10.0, step=0.5)

with col_in3:
    degradation = st.number_input("Annual Module Degradation (%)", min_value=0.2, max_value=2.0, value=0.55, step=0.05)
    om_rate = st.number_input("Annual O&M (% of CAPEX)", min_value=0.2, max_value=3.0, value=1.0, step=0.1)

# Execute Financial Calculations
capex_data = calculate_capex(target_ac_kw=ac_kw, installed_dc_kwp=dc_kwp, cost_per_watt_lkr=cost_per_watt)
roi_data = calculate_solar_roi(
    capex_lkr=capex_data["total_capex_lkr"],
    year_1_energy_kwh=annual_kwh,
    scheme=scheme,
    feed_in_tariff_lkr=tariff_rate if scheme != "Net Metering" else 37.0,
    retail_electricity_rate_lkr=tariff_rate if scheme == "Net Metering" else 48.0,
    discount_rate_pct=discount_rate,
    annual_degradation_pct=degradation,
    annual_om_pct_of_capex=om_rate
)

st.markdown("---")

# ---------------------------------------------------------------------------
# SECTION 2: Executive Financial Metrics Row
# ---------------------------------------------------------------------------
st.markdown("### 2. Investment & Payback Summary")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Turnkey CAPEX", f"LKR {capex_data['total_capex_lkr']:,.0f}", f"~${capex_data['total_capex_usd']:,.0f} USD")
k2.metric("Simple Payback", f"{roi_data['simple_payback_years']:.1f} Years", "Target: < 5 Yrs")
k3.metric("Discounted Payback", f"{roi_data['discounted_payback_years']:.1f} Years", f"At {discount_rate:.1f}% rate")
k4.metric("Net Present Value (NPV)", f"LKR {roi_data['npv_lkr']:,.0f}", "25-Yr Net Gain")
k5.metric("Internal Rate (IRR)", f"{roi_data['irr_pct']:.1f}%", f"ROI: {roi_data['roi_multiple']:.1f}x")
k6.metric("Solar LCOE", f"LKR {roi_data['lcoe_lkr_per_kwh']:.2f} / kWh", f"Grid: LKR {tariff_rate:.0f}")

# ---------------------------------------------------------------------------
# SECTION 3: Detailed CAPEX Breakdown
# ---------------------------------------------------------------------------
with st.expander("💼 Detailed Turnkey Capital Expenditure (CAPEX) Breakdown", expanded=False):
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        st.write(f"• **PV Modules (42%):** LKR {capex_data['modules_cost_lkr']:,.2f}")
        st.write(f"• **Inverters (20%):** LKR {capex_data['inverters_cost_lkr']:,.2f}")
        st.write(f"• **Mounting Hardware (12%):** LKR {capex_data['mounting_structure_lkr']:,.2f}")
    with c_b2:
        st.write(f"• **DC/AC Switchgear & Cables (14%):** LKR {capex_data['switchgear_and_cables_lkr']:,.2f}")
        st.write(f"• **Installation, Labor & Engineering (12%):** LKR {capex_data['installation_labor_lkr']:,.2f}")
        st.write(f"• **CEB Processing & Meter Deposit:** LKR {capex_data['ceb_utility_fees_lkr']:,.2f}")

# ---------------------------------------------------------------------------
# SECTION 4: 25-Year Cumulative Cash Flow Chart
# ---------------------------------------------------------------------------
st.markdown("### 3. 25-Year Cumulative Cash Flow Projection")
st.caption("Illustrates the capital recovery curve and long-term net positive cash generation over a 25-year asset lifecycle.")

cf_df = pd.DataFrame(roi_data["yearly_cash_flows"])
chart_df = cf_df[["year", "cumulative_cash_flow_lkr", "cumulative_discounted_cf_lkr"]].copy()
chart_df.columns = ["Year", "Nominal Cumulative (LKR)", "Discounted Cumulative (LKR)"]
chart_df.set_index("Year", inplace=True)

st.line_chart(chart_df)

# ---------------------------------------------------------------------------
# SECTION 5: Cash Flow Data Table & CSV Download
# ---------------------------------------------------------------------------
st.markdown("### 4. 25-Year Annual Cash Flow Statement")

tab_tbl, tab_csv = st.tabs(["📊 Financial Statement Table", "📥 Export Schedule"])

with tab_tbl:
    display_tbl = cf_df.copy()
    display_tbl.rename(columns={
        "year": "Year",
        "energy_kwh": "Generation (kWh)",
        "tariff_lkr": "Tariff (LKR)",
        "revenue_lkr": "Revenue / Savings (LKR)",
        "om_cost_lkr": "O&M (LKR)",
        "net_cash_flow_lkr": "Net Cash Flow (LKR)",
        "cumulative_cash_flow_lkr": "Cumulative Cash Flow (LKR)",
        "discounted_cash_flow_lkr": "Discounted CF (LKR)",
        "cumulative_discounted_cf_lkr": "Cumulative Discounted CF (LKR)"
    }, inplace=True)
    st.dataframe(display_tbl, use_container_width=True, hide_index=True)

with tab_csv:
    # Build clean CSV
    output_io = io.StringIO()
    output_io.write(f"# Solar PV Financial Analysis & 25-Year Cash Flow Projection\n")
    output_io.write(f"# Project: {proj.get('name', 'Solar Plant')} | Capacity: {ac_kw:.1f} kW AC / {dc_kwp:.2f} kWp DC\n")
    output_io.write(f"# Scheme: {scheme} | Payback: {roi_data['simple_payback_years']:.1f} Years | IRR: {roi_data['irr_pct']:.1f}% | NPV: LKR {roi_data['npv_lkr']:,.0f}\n")
    output_io.write(f"# Author: Eng. Aashir © 2026 All Rights Reserved\n")
    cf_df.to_csv(output_io, index=False)
    csv_bytes = output_io.getvalue()

    st.download_button(
        label="📥 Download 25-Year Cash Flow Projection (CSV)",
        data=csv_bytes,
        file_name=f"Solar_Financial_Projection_{int(ac_kw)}kW.csv",
        mime="text/csv",
        type="primary",
        use_container_width=True
    )
