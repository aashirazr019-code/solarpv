"""
pages/35_⚡_CEB_Tariff_Calculator.py — CEB Tariff, Solar Generation & Customer Savings Engine
Effective Date: 01 April 2026.
Authored by Eng. Aashir (c) 2026. All Rights Reserved.
"""

import streamlit as st
import datetime
import io
import csv
from ui.styles import apply_custom_css
from ui.components import page_header, render_status, render_calculation_proof
from core.unified_dataset import get_unified_engineering_dataset
from reports.proposal_summary import generate_proposal_summary_pdf
from core.project_state import (
    render_active_project_banner,
    get_active_project,
    get_design_value,
)
from core.ceb_tariff_data import (
    TARIFF_CONFIG,
    get_tariff_categories,
    get_tariff_info,
    get_net_plus_rate,
    get_default_generation_per_kw,
)
from core.ceb_tariff_engine import (
    calculate_vdmc,
    calculate_ceb_bill,
    estimate_units_from_bill,
    calculate_solar_generation,
    calculate_solar_bill_impact,
    recommend_solar_capacity,
)

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
try:
    st.set_page_config(
        page_title="CEB Tariff & Solar Savings — Solar PV Platform",
        page_icon="⚡",
        layout="wide",
    )
except Exception:
    pass

apply_custom_css()
render_active_project_banner()
page_header(
    "CEB Electricity Tariff & Solar Savings Calculator",
    "Calculate electricity bills, bidirectional consumption, solar offset, and Net Metering / Net Accounting / Net Plus savings",
    icon="⚡",
)

# ---------------------------------------------------------------------------
# Retrieve Active Project Context
# ---------------------------------------------------------------------------
proj = get_active_project()
active_ac_kw = float(get_design_value("actual_ac_kw", proj.get("target_ac_capacity_kw", 5.0)))
active_dc_kwp = float(get_design_value("actual_dc_kwp", round(active_ac_kw * 1.30, 2)))
active_phase = str(get_design_value("system_type", proj.get("installation_type", "Three Phase 400V")))

# ---------------------------------------------------------------------------
# SECTION 1: Customer Electricity Usage
# ---------------------------------------------------------------------------
st.markdown("### 🔌 1. Customer Electricity Usage & Utility Tariff")

col_left, col_right = st.columns([3, 2])

with col_left:
    with st.container(border=True):
        st.markdown("#### Tariff Category & Billing Parameters")

        c_tar, c_days = st.columns([3, 2])
        tariff_keys = get_tariff_categories()

        # Default tariff selection based on phase/capacity
        default_tariff_idx = 0  # Domestic
        if "Three" in active_phase and active_ac_kw >= 42.0:
            default_tariff_idx = tariff_keys.index("Industrial-2") if "Industrial-2" in tariff_keys else 0
        elif "Three" in active_phase and active_ac_kw >= 15.0:
            default_tariff_idx = tariff_keys.index("General") if "General" in tariff_keys else 0

        selected_category = c_tar.selectbox(
            "CEB Tariff Category",
            tariff_keys,
            index=default_tariff_idx,
            format_func=lambda k: f"{TARIFF_CONFIG[k]['name']}" + (" [Bulk TOU]" if TARIFF_CONFIG[k].get("is_bulk") else ""),
            help="Select the utility customer tariff classification per CEB / PUCSL Revision 2026.",
            key="ceb_tariff_cat_select",
        )

        tar_info = get_tariff_info(selected_category)

        # Billing Period Options
        period_mode = c_days.radio(
            "Billing Period Mode",
            ["Number of Days", "Reading Dates"],
            horizontal=True,
            key="ceb_period_mode",
        )

        billing_days = 30
        if period_mode == "Number of Days":
            billing_days = c_days.number_input(
                "Billing Period (Days)",
                min_value=1,
                max_value=90,
                value=30,
                step=1,
                key="ceb_billing_days_in",
            )
        else:
            d_col1, d_col2 = c_days.columns(2)
            today = datetime.date.today()
            prev_date = d_col1.date_input("Previous Date", today - datetime.timedelta(days=30), key="ceb_prev_date")
            curr_date = d_col2.date_input("Current Date", today, key="ceb_curr_date")
            delta_days = (curr_date - prev_date).days
            billing_days = max(1, delta_days)
            c_days.caption(f"Calculated billing cycle: **{billing_days} days**")

        st.caption(f"ℹ️ **Category Description:** {tar_info.get('description', '')}")

        # Maximum Demand (kVA) input if required
        max_demand_kva = 0.0
        if tar_info.get("requires_demand", False):
            d_c1, d_c2 = st.columns(2)
            max_demand_kva = d_c1.number_input(
                "Maximum Demand (kVA)",
                min_value=0.0,
                value=max(45.0, round(active_ac_kw * 1.1, 1)),
                step=5.0,
                key="ceb_max_demand_kva_in",
                help="Contract or recorded peak demand in kVA during the billing cycle.",
            )
            d_c2.info(f"⚡ **Demand Charge:** Rs. {tar_info.get('demand_charge_lkr_per_kva', 0.0):,.2f} / kVA/month")

with col_right:
    with st.container(border=True):
        st.markdown("#### Monthly Consumption vs Electricity Bill")

        entry_mode = st.radio(
            "Consumption Input Mode",
            ["Enter Monthly Units (kWh)", "Enter Monthly Bill (LKR)", "Calculate from Meter Readings"],
            horizontal=True,
            key="ceb_entry_mode",
        )

        cust_units = 500.0
        cust_bill_input = 0.0

        if entry_mode == "Enter Monthly Units (kWh)":
            cust_units = st.number_input(
                "Monthly Electricity Consumption (kWh / Units)",
                min_value=0.0,
                max_value=500000.0,
                value=500.0,
                step=25.0,
                key="ceb_units_direct_in",
                help="Total kilowatt-hours (kWh) consumed in the billing period.",
            )
            est_bill_res = calculate_ceb_bill(selected_category, cust_units, days=billing_days, max_demand_kva=max_demand_kva)
            st.success(f"💰 **Estimated CEB Electricity Bill:** LKR **{est_bill_res['total_bill_lkr']:,.2f}**")
            st.caption(f"Includes SSCL (2.5%) = LKR {est_bill_res['sscl_lkr']:,.2f} | Effective Rate: LKR {est_bill_res['effective_unit_rate_lkr']:.2f}/kWh")

        elif entry_mode == "Enter Monthly Bill (LKR)":
            cust_bill_input = st.number_input(
                "Monthly Electricity Bill Amount (LKR)",
                min_value=0.0,
                max_value=50000000.0,
                value=25000.0,
                step=1000.0,
                key="ceb_bill_direct_in",
                help="Total bill amount in Sri Lankan Rupees including fixed charges and SSCL.",
            )
            cust_units = estimate_units_from_bill(
                cust_bill_input,
                tariff_category=selected_category,
                days=billing_days,
                max_demand_kva=max_demand_kva,
            )
            st.info(f"📊 **Estimated Monthly Consumption:** **{cust_units:,.1f} kWh**")
            st.caption("Bidirectional reverse calculation solving retroactive slabs, fixed charges, and 2.5% SSCL.")

        else:
            # Meter readings
            m_c1, m_c2 = st.columns(2)
            prev_rd = m_c1.number_input("Previous Meter Reading", min_value=0.0, value=12450.0, step=50.0, key="ceb_prev_rd")
            curr_rd = m_c2.number_input("Current Meter Reading", min_value=0.0, value=12950.0, step=50.0, key="ceb_curr_rd")
            cust_units = max(0.0, curr_rd - prev_rd)
            st.markdown(f"**Consumption:** `{curr_rd:,.0f} - {prev_rd:,.0f} = ` **{cust_units:,.1f} kWh**")
            est_bill_res = calculate_ceb_bill(selected_category, cust_units, days=billing_days, max_demand_kva=max_demand_kva)
            st.success(f"💰 **Estimated CEB Electricity Bill:** LKR **{est_bill_res['total_bill_lkr']:,.2f}**")

        # Time of Use Breakdown Expander (if applicable)
        day_units = None
        peak_units = None
        off_peak_units = None
        if tar_info.get("requires_tou", False):
            with st.expander("⏱️ Time of Use (TOU) Energy Distribution", expanded=False):
                st.caption("Specify energy consumed in Day, Peak, and Off-Peak intervals, or use standard utility defaults.")
                t_c1, t_c2, t_c3 = st.columns(3)
                default_dist = tar_info.get("default_distribution", {"day_pct": 0.60, "peak_pct": 0.15, "off_peak_pct": 0.25})
                day_units = t_c1.number_input("Day (05:30–18:30)", min_value=0.0, value=round(cust_units * default_dist["day_pct"], 1), step=10.0, key="ceb_tou_day")
                peak_units = t_c2.number_input("Peak (18:30–22:30)", min_value=0.0, value=round(cust_units * default_dist["peak_pct"], 1), step=10.0, key="ceb_tou_peak")
                off_peak_units = t_c3.number_input("Off-Peak (22:30–05:30)", min_value=0.0, value=round(cust_units * default_dist["off_peak_pct"], 1), step=10.0, key="ceb_tou_offpeak")

# ---------------------------------------------------------------------------
# SECTION 2: Solar PV System & Self-Generation Scheme
# ---------------------------------------------------------------------------
st.divider()
st.markdown("### ☀️ 2. Solar PV System Capacity & Self-Generation Scheme")

rec_capacity_kw = recommend_solar_capacity(cust_units)

# Handle apply button click safely BEFORE widget instantiation
if "ceb_solar_cap_in" not in st.session_state:
    st.session_state["ceb_solar_cap_in"] = active_ac_kw

if st.session_state.get("ceb_apply_rec_flag", False):
    st.session_state["ceb_solar_cap_in"] = rec_capacity_kw
    st.session_state["ceb_apply_rec_flag"] = False

s_col1, s_col2, s_col3 = st.columns([2, 2, 2])

with s_col1:
    with st.container(border=True):
        st.markdown("#### Solar System Sizing")
        st.caption(f"Active Project Capacity: **{active_ac_kw:.1f} kW AC** ({active_dc_kwp:.1f} kWp DC)")

        solar_cap_kw = st.number_input(
            "Proposed Solar System Capacity (kW)",
            min_value=0.0,
            max_value=5000.0,
            step=1.0,
            key="ceb_solar_cap_in",
            help="Rated AC output capacity of the solar PV system.",
        )

        # Recommendation Helper
        st.markdown(
            f"""
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 8px 12px; margin-top: 6px; font-size: 12px;">
                💡 <b>Recommended Capacity:</b> <span style="font-size: 14px; font-weight: bold; color: #166534;">{rec_capacity_kw:.1f} kW</span><br/>
                <span style="color: #4b5563;">Based on 120 kWh/kW/month to cover 100% of consumption.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("⭐ Apply Recommended Capacity", key="apply_rec_cap_btn"):
            st.session_state["ceb_apply_rec_flag"] = True
            st.rerun()

with s_col2:
    with st.container(border=True):
        st.markdown("#### Solar Energy Generation")
        est_monthly_gen = calculate_solar_generation(solar_cap_kw)
        coverage_pct = round((est_monthly_gen / cust_units * 100.0), 1) if cust_units > 0 else 0.0

        st.metric("Estimated Monthly Generation", f"{est_monthly_gen:,.1f} kWh/mo", f"Rate: 120 kWh/kW")
        st.metric("Solar Coverage of Consumption", f"{coverage_pct:.1f} %", "Target: 100%")

        if est_monthly_gen >= cust_units:
            potential_export = est_monthly_gen - cust_units
            st.success(f"🟢 **Potential Monthly Export:** **{potential_export:,.1f} kWh**")
        else:
            remaining_import = cust_units - est_monthly_gen
            st.warning(f"🟡 **Remaining Grid Import:** **{remaining_import:,.1f} kWh**")

with s_col3:
    with st.container(border=True):
        st.markdown("#### Interconnection Scheme")

        selected_scheme = st.selectbox(
            "Self-Generation Scheme",
            ["Net Accounting", "Net Metering", "Net Plus", "None"],
            index=0,
            help="Official CEB / LECO Grid Interconnection Scheme.",
            key="ceb_scheme_select",
        )

        brought_forward_units = 0.0
        if selected_scheme in ("Net Metering", "Net Accounting"):
            brought_forward_units = st.number_input(
                "Brought Forward Energy Credit (kWh)",
                min_value=0.0,
                value=0.0,
                step=50.0,
                key="ceb_bf_units_in",
                help="Unused energy credit banked from previous billing periods.",
            )

        # --- User-configurable CEB Export / Feed-in Tariff ---
        export_tariff_lkr = st.number_input(
            "CEB Export / Feed-in Tariff (LKR/kWh)",
            min_value=0.0,
            max_value=500.0,
            value=float(proj.get("ceb_export_tariff_lkr", 19.0)),
            step=0.50,
            format="%.2f",
            key="ceb_export_tariff_in",
            help=(
                "PUCSL Net Plus feed-in rate or Net Accounting export credit rate. "
                "Default: **19.00 LKR/kWh** (PUCSL effective 01 April 2026). "
                "Change this value to recalculate all savings, income, and proposals."
            ),
        )
        # Persist to project state so downstream pages use the same tariff
        if "active_project" in st.session_state and st.session_state.active_project:
            st.session_state.active_project["ceb_export_tariff_lkr"] = export_tariff_lkr

        if selected_scheme == "Net Plus":
            st.markdown(
                f"""
                <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 10px; font-size: 12px;">
                    <b>Net Plus Export Rate:</b> <span style="font-size: 16px; font-weight: bold; color: #1e40af;">Rs. {export_tariff_lkr:.2f} / kWh</span><br/>
                    <span style="color: #6b7280;">User-configured feed-in rate (PUCSL / CEB authority).</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif selected_scheme == "Net Accounting":
            st.caption(f"ℹ️ **Net Accounting:** Onsite usage offsets consumption. Excess generation exported at Rs. {export_tariff_lkr:.2f}/kWh.")
        elif selected_scheme == "Net Metering":
            st.caption("ℹ️ **Net Metering:** 1:1 unit offset. Excess units banked for future months. Billed only on net import units.")
        else:
            st.caption("ℹ️ **None:** No solar adjustment. Full grid consumption billed at utility tariff.")

# ---------------------------------------------------------------------------
# SECTION 3: Live Engineering Calculation Execution
# ---------------------------------------------------------------------------
impact_results = calculate_solar_bill_impact(
    consumption_kwh=cust_units,
    solar_capacity_kw=solar_cap_kw,
    scheme=selected_scheme,
    tariff_category=selected_category,
    days=billing_days,
    brought_forward_kwh=brought_forward_units,
    max_demand_kva=max_demand_kva,
    export_tariff_lkr=export_tariff_lkr,
)

bill_before = impact_results["bill_before_solar_lkr"]
bill_after = impact_results["bill_after_solar_lkr"]
export_income = impact_results["solar_export_income_lkr"]
net_cost = impact_results["net_monthly_cost_lkr"]
monthly_saving = impact_results["monthly_saving_lkr"]
annual_saving = impact_results["annual_saving_lkr"]

# ---------------------------------------------------------------------------
# SECTION 4: Results Dashboard (Visual KPI Cards)
# ---------------------------------------------------------------------------
st.divider()
st.markdown("### 📊 3. Performance & Financial Results Dashboard")

kpi_c1, kpi_c2, kpi_c3, kpi_c4, kpi_c5 = st.columns(5)
kpi_c1.metric("Monthly Consumption", f"{cust_units:,.1f} kWh", f"VDMC: {calculate_vdmc(cust_units, billing_days):.1f}u")
kpi_c2.metric("Current CEB Bill", f"LKR {bill_before:,.2f}", f"Category: {selected_category}")
kpi_c3.metric("Solar System Capacity", f"{solar_cap_kw:.1f} kW", f"{active_dc_kwp:.1f} kWp DC")
kpi_c4.metric("Solar Generation", f"{est_monthly_gen:,.1f} kWh/mo", f"Rate: 120 kWh/kW")
kpi_c5.metric("Solar Coverage", f"{coverage_pct:.1f} %", "of Consumption")

kpi_c6, kpi_c7, kpi_c8, kpi_c9, kpi_c10 = st.columns(5)
kpi_c6.metric("Grid Import", f"{impact_results['grid_import_kwh']:,.1f} kWh", "Import from CEB")
kpi_c7.metric("Grid Export", f"{impact_results['grid_export_kwh']:,.1f} kWh", "Export to CEB")
kpi_c8.metric("CEB Bill After Solar", f"LKR {bill_after:,.2f}", f"Import Bill")
kpi_c9.metric("Export Income / Credit", f"LKR {export_income:,.2f}", f"Scheme: {selected_scheme}")
kpi_c10.metric("Net Monthly Cost", f"LKR {net_cost:,.2f}", f"Bill - Income")

# Highlight Banner for Savings
st.markdown(
    f"""
    <div style="background: linear-gradient(135deg, #1e3a8a, #065f46); color: white; padding: 18px 24px; border-radius: 8px; margin: 16px 0; display: flex; justify-content: space-around; align-items: center; border: 1px solid #10b981;">
        <div style="text-align: center;">
            <div style="font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #a7f3d0; font-weight: 600;">Net Monthly Saving / Revenue</div>
            <div style="font-size: 28px; font-weight: 800; margin-top: 4px; color: #ffffff;">LKR {monthly_saving:,.2f} / month</div>
        </div>
        <div style="border-left: 2px solid rgba(255,255,255,0.2); height: 50px;"></div>
        <div style="text-align: center;">
            <div style="font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #a7f3d0; font-weight: 600;">Annual Customer Benefit</div>
            <div style="font-size: 28px; font-weight: 800; margin-top: 4px; color: #ffffff;">LKR {annual_saving:,.2f} / year</div>
        </div>
        <div style="border-left: 2px solid rgba(255,255,255,0.2); height: 50px;"></div>
        <div style="text-align: center;">
            <div style="font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #a7f3d0; font-weight: 600;">25-Year Cumulative Savings</div>
            <div style="font-size: 28px; font-weight: 800; margin-top: 4px; color: #34d399;">LKR {(annual_saving * 25.0):,.2f}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# SECTION 5: BEFORE vs AFTER SOLAR COMPARISON
# ---------------------------------------------------------------------------
st.divider()
st.markdown("### ⚖️ 4. Detailed Before vs After Solar Comparison")

col_before, col_after = st.columns(2)

with col_before:
    with st.container(border=True):
        st.markdown("#### 🔴 WITHOUT SOLAR (Utility Supply Only)")
        st.write(f"**Tariff Classification:** `{selected_category}` ({tar_info.get('name', '')})")
        st.write(f"**Monthly Consumption:** `{cust_units:,.1f} kWh` ({billing_days} days)")
        st.write(f"**CEB Electricity Bill:** **LKR {bill_before:,.2f} / month**")
        st.write(f"**Annual Utility Expense:** **LKR {(bill_before * 12.0):,.2f} / year**")
        st.write(f"**Effective Electricity Cost:** `LKR {bill_before / cust_units:.2f} / kWh`" if cust_units > 0 else "")
        st.caption("100% of customer consumption is imported and billed at standard tariff rates including SSCL (2.5%).")

with col_after:
    with st.container(border=True):
        st.markdown(f"#### 🟢 WITH SOLAR ({selected_scheme.upper()})")
        st.write(f"**Solar Generation:** `{est_monthly_gen:,.1f} kWh/month` ({solar_cap_kw:.1f} kW)")
        st.write(f"**Solar Energy Utilized / Offset:** `{impact_results['solar_used_kwh']:,.1f} kWh`")
        st.write(f"**Net Grid Import:** `{impact_results['grid_import_kwh']:,.1f} kWh`")
        st.write(f"**Net Grid Export:** `{impact_results['grid_export_kwh']:,.1f} kWh`" + (f" ({impact_results['carry_forward_kwh']:,.1f} kWh banked)" if selected_scheme == 'Net Metering' else ""))
        st.write(f"**CEB Utility Bill After Solar:** `LKR {bill_after:,.2f}`")
        if export_income > 0:
            st.write(f"**Export Income / Credit:** `LKR {export_income:,.2f}`")
        st.markdown(f"**Net Monthly Electricity Cost:** <span style='font-size: 18px; font-weight: bold; color: #166534;'>LKR {net_cost:,.2f} / month</span>", unsafe_allow_html=True)
        st.caption(f"💡 {impact_results['explanation']}")

# ---------------------------------------------------------------------------
# TRANSPARENT EXPORT FORMULA PANEL (always visible when export > 0)
# ---------------------------------------------------------------------------
if impact_results.get("grid_export_kwh", 0) > 0 or selected_scheme in ("Net Plus", "Net Accounting"):
    st.divider()
    st.markdown("### 💡 Export Revenue Formula — Transparent Calculation")
    exported_kwh = float(impact_results.get("grid_export_kwh", 0.0))
    export_rev = float(impact_results.get("solar_export_income_lkr", 0.0))
    gross_bill = float(bill_after)
    net_bill = max(0.0, gross_bill - export_rev)

    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        with st.container(border=True):
            st.markdown("**Step 1 — Export Revenue**")
            st.markdown(
                f"""
                <div style="font-family: monospace; font-size: 13px; background: #f8fafc; padding: 10px; border-radius: 6px;">
                Monthly Exported Energy &nbsp; = <b>{exported_kwh:,.2f} kWh</b><br/>
                Export Unit Price &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = <b>LKR {export_tariff_lkr:.2f} / kWh</b><br/>
                <hr style="margin:6px 0; border-color:#e2e8f0"/>
                Monthly Export Revenue &nbsp; = {exported_kwh:,.2f} × {export_tariff_lkr:.2f}<br/>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>= LKR {export_rev:,.2f}</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with fcol2:
        with st.container(border=True):
            st.markdown("**Step 2 — Net Bill Calculation**")
            st.markdown(
                f"""
                <div style="font-family: monospace; font-size: 13px; background: #f8fafc; padding: 10px; border-radius: 6px;">
                Gross Electricity Bill &nbsp;= <b>LKR {bill_before:,.2f}</b><br/>
                Bill After Solar Import  = <b>LKR {gross_bill:,.2f}</b><br/>
                Export Credit &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; = <b>LKR {export_rev:,.2f}</b><br/>
                <hr style="margin:6px 0; border-color:#e2e8f0"/>
                Net Bill &nbsp;&nbsp; = {gross_bill:,.2f} − {export_rev:,.2f}<br/>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>= LKR {net_bill:,.2f}</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with fcol3:
        with st.container(border=True):
            st.markdown("**Step 3 — Total Monthly Saving**")
            st.markdown(
                f"""
                <div style="font-family: monospace; font-size: 13px; background: #f8fafc; padding: 10px; border-radius: 6px;">
                Bill Without Solar &nbsp;= <b>LKR {bill_before:,.2f}</b><br/>
                Net Bill With Solar &nbsp;= <b>LKR {net_cost:,.2f}</b><br/>
                <hr style="margin:6px 0; border-color:#e2e8f0"/>
                Monthly Saving &nbsp;= {bill_before:,.2f} − {net_cost:,.2f}<br/>
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>= LKR {monthly_saving:,.2f} / month</b><br/>
                Annual Saving &nbsp;&nbsp; = <b>LKR {annual_saving:,.2f} / year</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.caption(
        f"ℹ️ Export Unit Price = **LKR {export_tariff_lkr:.2f}/kWh** (PUCSL {selected_scheme} rate). "
        "Change the tariff in the 'Interconnection Scheme' box above — all calculations update automatically."
    )


# ---------------------------------------------------------------------------
# SECTION 6: Step-by-Step Engineering & Tariff Proof
# ---------------------------------------------------------------------------
with st.expander("📝 Step-by-Step Mathematical Calculation Proof & Tariff Breakdown", expanded=False):
    st.markdown("#### Tariff Sizing & Calculation Proof")

    full_bill_data = calculate_ceb_bill(selected_category, cust_units, days=billing_days, max_demand_kva=max_demand_kva)

    proof_steps = [
        {"label": "Tariff Category", "value": f"{full_bill_data['tariff_category']} — {tar_info.get('name', '')}"},
        {"label": "Billing Period Days", "value": f"{billing_days} days (Days Ratio: {billing_days/30.0:.3f})"},
        {"label": "Virtual Days Monthly Consumption (VDMC)", "value": f"{full_bill_data['vdmc']} kWh/30-day equivalent"},
        {"label": "Slab Designation", "value": full_bill_data["slab_name"]},
        {"label": "Energy Charge Basis", "value": full_bill_data["rate_description"]},
        {"label": "Energy Charge (LKR)", "value": f"LKR {full_bill_data['energy_charge_lkr']:,.2f}"},
        {"label": "Monthly Fixed Charge (LKR)", "value": f"LKR {full_bill_data['fixed_charge_lkr']:,.2f}"},
    ]

    if full_bill_data.get("demand_charge_lkr", 0.0) > 0:
        proof_steps.append({"label": "Maximum Demand Charge (LKR)", "value": f"LKR {full_bill_data['demand_charge_lkr']:,.2f}"})

    proof_steps.extend([
        {"label": "Bill Subtotal (LKR)", "value": f"LKR {full_bill_data['subtotal_lkr']:,.2f}"},
        {"label": "Social Security Contribution Levy (SSCL @ 2.5%)", "value": f"LKR {full_bill_data['sscl_lkr']:,.2f}"},
        {"label": "Total Current Monthly CEB Bill (LKR)", "value": f"LKR {full_bill_data['total_bill_lkr']:,.2f}"},
        {"label": "Effective Cost per Unit", "value": f"LKR {full_bill_data['effective_unit_rate_lkr']:.2f} / kWh"},
    ])

    render_calculation_proof("CEB Electricity Bill Proof", proof_steps)

    st.markdown(
        """
        ---
        **Statutory & Engineering Citations:**
        - Public Utilities Commission of Sri Lanka (PUCSL) Electricity Tariff Schedule (Effective 01 April 2026).
        - Social Security Contribution Levy (SSCL) Act No. 25 of 2022 (2.5% statutory levy applied on subtotal).
        - Ceylon Electricity Board (CEB) Rooftop Solar PV (RTSPV) Interconnection Schemes (Net Metering, Net Accounting, Net Plus).
        - Lead Systems Engineer & Designer: **Eng. Aashir** © 2026. All Rights Reserved.
        """
    )

# ---------------------------------------------------------------------------
# SECTION 7: Customer Proposal & Project Integration
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 📥 Customer Proposal & Project Integration")
st.caption("Generate executive 1-page proposals for clients, export detailed calculation data, or sync parameters to active project state.")

prop_c1, prop_c2, prop_c3 = st.columns(3)

with prop_c1:
    with st.container(border=True):
        st.markdown("#### 📄 1-Page Customer Proposal (PDF)")
        st.write("Executive stamped proposal comparing baseline grid bill vs post-solar savings.")
        try:
            custom_params = {
                "tariff_category": selected_category,
                "ceb_scheme": selected_scheme,
                "monthly_consumption_kwh": cust_units,
                "billing_days": billing_days,
                "max_demand_kva": max_demand_kva,
                "ceb_export_tariff_lkr": export_tariff_lkr,
            }
            ds_prop = get_unified_engineering_dataset(target_kw=solar_cap_kw, custom_project_params=custom_params)
            prop_pdf = generate_proposal_summary_pdf(ds_prop)
            st.download_button(
                label=f"📥 Download Proposal PDF ({len(prop_pdf):,} bytes)",
                data=prop_pdf,
                file_name=f"Solar_Savings_Proposal_{int(solar_cap_kw)}kW_{selected_category.replace(' ', '_')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Proposal generation error: {e}")

with prop_c2:
    with st.container(border=True):
        st.markdown("#### 📊 Export Calculation Breakdown (CSV)")
        st.write("Complete spreadsheet of pre-solar bill, post-solar bill, and monthly savings.")
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["Parameter", "Calculated Value", "Unit / Statutory Basis"])
        writer.writerow(["Tariff Category", selected_category, "PUCSL Schedule (Eff. 01 Apr 2026)"])
        writer.writerow(["Interconnection Scheme", selected_scheme, "CEB Self-Generation Agreement"])
        writer.writerow(["Billing Days", billing_days, "Days"])
        writer.writerow(["Monthly Consumption", cust_units, "kWh / month"])
        writer.writerow(["Virtual Days Monthly Consumption (VDMC)", round(impact_results.get("vdmc", cust_units), 2), "kWh / 30-day equivalent"])
        writer.writerow(["Solar System Capacity", solar_cap_kw, "kW AC"])
        writer.writerow(["CEB Export / Feed-in Tariff", f"LKR {export_tariff_lkr:.2f}", "LKR / kWh (User-configured)"])
        writer.writerow(["Monthly Solar Generation", impact_results["solar_generation_kwh"], "kWh / month"])
        writer.writerow(["Solar Demand Offset", f"{impact_results['solar_coverage_pct']:.1f}%", "Percentage of consumption offset"])
        writer.writerow(["Baseline Utility Bill (Pre-Solar)", f"LKR {impact_results['bill_before_solar_lkr']:,.2f}", "Includes 2.5% SSCL"])
        writer.writerow(["Grid Electricity Bill (Post-Solar)", f"LKR {impact_results['bill_after_solar_lkr']:,.2f}", "Residual utility import"])
        writer.writerow(["Solar Export Revenue / Credit", f"LKR {impact_results['solar_export_income_lkr']:,.2f}", "Export feed-in income"])
        writer.writerow(["Net Monthly Customer Cost", f"LKR {impact_results['net_monthly_cost_lkr']:,.2f}", "Bill After Solar - Export Income"])
        writer.writerow(["Net Monthly Customer Savings", f"LKR {impact_results['monthly_saving_lkr']:,.2f}", "Direct utility bill reduction"])
        writer.writerow(["Forecast Annual Savings", f"LKR {impact_results['annual_saving_lkr']:,.2f}", "12-month cumulative savings"])
        csv_data = csv_buffer.getvalue().encode("utf-8")
        st.download_button(
            label=f"📊 Download Breakdown CSV ({len(csv_data):,} bytes)",
            data=csv_data,
            file_name=f"CEB_Tariff_Analysis_{int(solar_cap_kw)}kW.csv",
            mime="text/csv",
            use_container_width=True
        )

with prop_c3:
    with st.container(border=True):
        st.markdown("#### 💾 Apply to Active Project")
        st.write("Save these tariff parameters to your active project session state.")
        if st.button("💾 Save Settings to Active Project", use_container_width=True):
            if "active_project" in st.session_state and st.session_state.active_project:
                st.session_state.active_project["tariff_category"] = selected_category
                st.session_state.active_project["ceb_scheme"] = selected_scheme
                st.session_state.active_project["monthly_consumption_kwh"] = cust_units
                st.session_state.active_project["billing_days"] = billing_days
                st.session_state.active_project["max_demand_kva"] = max_demand_kva
                st.session_state.active_project["ceb_export_tariff_lkr"] = export_tariff_lkr
                st.success("✅ Saved! Downstream reports and schedules will use these tariff settings.")
            else:
                st.info("No active project loaded in session state.")

