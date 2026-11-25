import streamlit as st
import pandas as pd
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from core.production_calculator import calculate_ac_production, calculate_dc_capacity_from_modules
from core.project_state import (
    get_active_project,
    get_active_panel,
    get_active_inverter,
    get_design_value,
    set_design_value,
    render_active_project_banner
)

try:
    st.set_page_config(page_title="AC Production Calculator — Eng. Aashir", page_icon="⚡", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()
render_active_project_banner()

page_header("AC Grid-Connected Energy Production Calculator", "Calculate net exportable AC energy after inverter conversion, AC line losses, and system availability", icon="⚡")

# State bindings
panel = get_active_panel()
inverter = get_active_inverter()
st_panel_qty = get_design_value("panel_qty", 12)
st_panel_wp = panel.rated_power_wp if panel else 630.0
st_inv_eff = inverter.efficiency_pct if inverter else 98.1
calc_dc_cap = calculate_dc_capacity_from_modules(st_panel_qty, st_panel_wp)

c1, c2 = st.columns(2)

with c1:
    st.markdown("#### 🔋 Plant Size & Solar Resource")
    c_p1, c_p2 = st.columns(2)
    num_panels = c_p1.number_input("Total Panels", min_value=1, value=int(st_panel_qty), step=1)
    module_wp = c_p2.number_input("Module Power (Wp)", min_value=100.0, max_value=800.0, value=float(st_panel_wp), step=5.0)
    derived_dc_cap = calculate_dc_capacity_from_modules(num_panels, module_wp)
    
    st.info(f"⚡ **Array DC Capacity:** $P_{{dc}} = {num_panels} \\times {module_wp}\\text{{ Wp}} / 1000 = \\mathbf{{{derived_dc_cap:.2f}\\text{{ kWp}}}}$")
    
    psh = st.number_input("Peak Sun Hours — PSH (h/day)", min_value=0.0, max_value=10.0, value=4.5, step=0.1,
                          help="Annual average peak sun hours at module tilt. Required solar resource.")
    
    st.markdown("#### ⚡ Inverter & AC Conversion Parameters")
    inv_eff = st.number_input("Inverter Euro/CEC Efficiency (%)", min_value=70.0, max_value=99.8, value=float(st_inv_eff), step=0.1,
                              help="Weighted conversion efficiency of the inverter from DC to AC.")
    ac_cable_loss = st.number_input("AC Cable Voltage Drop & Line Loss (%)", min_value=0.0, max_value=10.0, value=0.8, step=0.1)

with c2:
    st.markdown("#### 📉 System Derating & Operational Losses (%)")
    temp_loss = st.number_input("Temperature Loss (%)", min_value=0.0, max_value=25.0, value=5.0, step=0.5)
    soiling_loss = st.number_input("Soiling Loss (%)", min_value=0.0, max_value=20.0, value=2.0, step=0.5)
    mismatch_loss = st.number_input("Module Mismatch Loss (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)
    dc_cable_loss = st.number_input("DC Cable Loss (%)", min_value=0.0, max_value=10.0, value=1.0, step=0.2)
    trafo_loss = st.number_input("MV Transformer Loss (if applicable) (%)", min_value=0.0, max_value=5.0, value=0.0, step=0.1)
    availability = st.number_input("Plant Grid Availability (%)", min_value=80.0, max_value=100.0, value=99.0, step=0.5,
                                  help="Percentage of time the grid and inverter are operational and available.")

if st.button("⚡ Calculate Net AC Production & PR", type="primary", use_container_width=True):
    try:
        if psh <= 0:
            st.error("❌ Solar resource data required. Please enter a valid Peak Sun Hours (PSH > 0) value.")
        else:
            res = calculate_ac_production(
                dc_capacity_kwp=derived_dc_cap,
                peak_sun_hours=psh,
                inverter_efficiency_pct=inv_eff,
                ac_cable_loss_pct=ac_cable_loss,
                transformer_loss_pct=trafo_loss,
                availability_pct=availability,
                temp_loss_pct=temp_loss,
                soiling_pct=soiling_loss,
                mismatch_pct=mismatch_loss,
                dc_cable_loss_pct=dc_cable_loss
            )

            if res["status"] == "FAIL":
                st.error(f"❌ Error: {res.get('message', res.get('errors'))}")
            else:
                st.markdown("---")
                st.subheader("📊 Net Exportable AC Performance & Yield")

                c_res1, c_res2, c_res3, c_res4 = st.columns(4)
                c_res1.metric("Net Daily AC Generation", f"{res['daily_ac_energy_kwh']:,.1f} kWh", f"Gross DC: {res['daily_dc_energy_kwh']:,.1f} kWh")
                c_res2.metric("Annual AC Generation", f"{res['annual_ac_energy_mwh']:,.2f} MWh", f"{res['annual_ac_energy_kwh']:,.0f} kWh/year")
                c_res3.metric("System Performance Ratio", f"{res['performance_ratio_pct']:.1f}%", f"Overall PR: {res['performance_ratio']:.3f}")
                c_res4.metric("Specific AC Yield", f"{res['specific_yield_ac_kwh_kwp']:,.0f} kWh/kWp", "Net AC yield per DC kWp")

                # Update session state
                set_design_value("annual_ac_energy_kwh", res["annual_ac_energy_kwh"])
                set_design_value("performance_ratio_pct", res["performance_ratio_pct"])

                # Loss Breakdown (Clean Separation: DC, Inverter, AC BOS)
                st.markdown("---")
                st.subheader("⚖️ Three-Stage Energy Balance & Loss Breakdown")
                st.caption("Explicitly separated into DC field losses, Inverter conversion loss, and AC grid connection losses (no double-counting):")

                wf = res["loss_waterfall"]
                loss_df = pd.DataFrame([
                    {"Stage": "1. DC Field Losses", "Component": "Thermal Derate", "Loss (%)": f"{wf['temperature_loss_pct']:.1f}%", "Scope": "DC Array"},
                    {"Stage": "1. DC Field Losses", "Component": "Soiling & Dust", "Loss (%)": f"{wf['soiling_loss_pct']:.1f}%", "Scope": "DC Array"},
                    {"Stage": "1. DC Field Losses", "Component": "Module Mismatch", "Loss (%)": f"{wf['mismatch_loss_pct']:.1f}%", "Scope": "DC Array"},
                    {"Stage": "1. DC Field Losses", "Component": "DC Cable I²R Drop", "Loss (%)": f"{wf['dc_cable_loss_pct']:.1f}%", "Scope": "DC Array"},
                    {"Stage": "2. Inverter Inversion", "Component": "Inverter Thermal Loss", "Loss (%)": f"{wf['inverter_inefficiency_pct']:.1f}%", "Scope": "Power Electronics"},
                    {"Stage": "3. AC BOS & Grid", "Component": "AC Cable I²R Drop", "Loss (%)": f"{wf['ac_cable_loss_pct']:.1f}%", "Scope": "AC Switchboard"},
                    {"Stage": "3. AC BOS & Grid", "Component": "Transformer Loss", "Loss (%)": f"{wf['transformer_loss_pct']:.1f}%", "Scope": "Grid Interface"},
                    {"Stage": "3. AC BOS & Grid", "Component": "Unavailability Outage", "Loss (%)": f"{wf['unavailability_pct']:.1f}%", "Scope": "Grid Reliability"},
                    {"Stage": "★ NET OUTPUT", "Component": "Net Performance Ratio", "Loss (%)": f"PR = {wf['net_performance_ratio_pct']:.1f}%", "Scope": "Whole System"}
                ])
                st.dataframe(loss_df, use_container_width=True, hide_index=True)

                # Monthly Schedule
                st.markdown("---")
                st.subheader("📅 12-Month DC vs AC Projected Production Schedule")
                m_df = pd.DataFrame(res["monthly_breakdown"])
                m_display = m_df.rename(columns={
                    "month": "Month",
                    "days": "Days",
                    "psh": "Effective PSH (h/day)",
                    "dc_kwh": "Gross DC (kWh)",
                    "ac_kwh": "Net AC Export (kWh)",
                    "ac_mwh": "Net AC Export (MWh)",
                    "inverter_loss_kwh": "Inverter Thermal Loss (kWh)"
                })[["Month", "Days", "Effective PSH (h/day)", "Gross DC (kWh)", "Net AC Export (kWh)", "Net AC Export (MWh)", "Inverter Thermal Loss (kWh)"]]
                st.dataframe(m_display, use_container_width=True, hide_index=True)

                chart_data = m_df.set_index("month")[["dc_kwh", "ac_kwh"]].rename(columns={"dc_kwh": "Gross DC kWh", "ac_kwh": "Net AC kWh"})
                st.bar_chart(chart_data)

                render_calculation_proof(
                    "AC Energy Production & PR Engineering Derivation",
                    [
                        {"formula": r"P_{dc} = \frac{N_{panels} \times P_{mp}}{1000}"},
                        {"label": "DC Nameplate Capacity", "value": f"{num_panels} × {module_wp}W = {derived_dc_cap:.2f} kWp"},
                        {"formula": r"\text{PR}_{net} = \text{Derate}_{DC} \times \eta_{inv} \times (1 - L_{AC}) \times (1 - L_{trafo}) \times \text{Availability}"},
                        {"label": "System Performance Ratio", "value": f"{res['performance_ratio_pct']:.2f}% ({res['performance_ratio']:.4f})"},
                        {"formula": r"E_{daily,AC} = E_{daily,DC} \times \text{AC Conversion Factor} \quad [\text{kWh/day}]"},
                        {"label": "Daily AC Energy Export", "value": f"{res['daily_ac_energy_kwh']:,.1f} kWh/day"},
                        {"formula": r"E_{annual,AC} = \sum_{m=1}^{12} E_{monthly,AC} \quad [\text{kWh/year}]"},
                        {"label": "Annual Net AC Energy Export", "value": f"{res['annual_ac_energy_kwh']:,.0f} kWh/year ({res['annual_ac_energy_mwh']:.2f} MWh)"},
                        {"formula": r"\text{Specific Yield}_{AC} = \frac{E_{annual,AC}}{P_{dc}} \quad [\text{kWh/kWp/year}]"},
                        {"label": "Specific AC Yield", "value": f"{res['specific_yield_ac_kwh_kwp']:,.1f} kWh/kWp/year"}
                    ]
                )

    except Exception as e:
        st.error(f"Error during AC production calculation: {str(e)}")
