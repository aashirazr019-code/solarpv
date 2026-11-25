import streamlit as st
import pandas as pd
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from core.production_calculator import calculate_dc_production, calculate_dc_capacity_from_modules
from core.project_state import (
    get_active_project,
    get_active_panel,
    get_design_value,
    set_design_value,
    render_active_project_banner
)

try:
    st.set_page_config(page_title="DC Production Calculator — Eng. Aashir", page_icon="☀️", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()
render_active_project_banner()

page_header("DC Photovoltaic Energy Production Calculator", "Estimate gross DC generation, daily yield, monthly generation curves, and specific DC yield from site irradiance", icon="☀️")

# Retrieve state defaults
panel = get_active_panel()
st_panel_qty = get_design_value("panel_qty", 12)
st_panel_wp = panel.rated_power_wp if panel else 630.0
calc_dc_cap = calculate_dc_capacity_from_modules(st_panel_qty, st_panel_wp)

c1, c2 = st.columns(2)

with c1:
    st.markdown("#### 🔋 PV Array & Solar Resource")
    c_p1, c_p2 = st.columns(2)
    num_panels = c_p1.number_input("Total Panels", min_value=1, value=int(st_panel_qty), step=1,
                                  help="Total number of modules in the array.")
    module_wp = c_p2.number_input("Module Power (Wp)", min_value=100.0, max_value=800.0, value=float(st_panel_wp), step=5.0)
    
    # Calculate nameplate Pdc strictly: N_panels * P_mp / 1000
    derived_dc_cap = calculate_dc_capacity_from_modules(num_panels, module_wp)
    st.info(f"⚡ **Array DC Capacity:** $P_{{dc}} = {num_panels} \\times {module_wp}\\text{{ Wp}} / 1000 = \\mathbf{{{derived_dc_cap:.2f}\\text{{ kWp}}}}$")
    
    psh = st.number_input("Peak Sun Hours — PSH (h/day)", min_value=0.0, max_value=10.0, value=4.5, step=0.1,
                          help="Annual average peak sun hours at module tilt. Required solar resource.")

with c2:
    st.markdown("#### 📉 DC Array Loss Factors (%)")
    temp_loss = st.number_input("Thermal Derating Loss (%)", min_value=0.0, max_value=30.0, value=5.0, step=0.5,
                                help="Loss due to cell temperature operating above 25°C STC.")
    soiling_loss = st.number_input("Soiling / Dust Deposition Loss (%)", min_value=0.0, max_value=25.0, value=2.0, step=0.5)
    mismatch_loss = st.number_input("Module Mismatch & Manufacturing Tolerance (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)
    dc_cable_loss = st.number_input("DC String Cable Resistive Loss (%)", min_value=0.0, max_value=10.0, value=1.0, step=0.2)
    shading_loss = st.number_input("Near / Far Horizon Shading Loss (%)", min_value=0.0, max_value=30.0, value=0.0, step=0.5)

if st.button("☀️ Calculate Expected DC Generation", type="primary", use_container_width=True):
    try:
        if psh <= 0:
            st.error("❌ Solar resource data required. Please enter a valid Peak Sun Hours (PSH > 0) value.")
        else:
            res = calculate_dc_production(
                dc_capacity_kwp=derived_dc_cap,
                peak_sun_hours=psh,
                temp_loss_pct=temp_loss,
                soiling_pct=soiling_loss,
                mismatch_pct=mismatch_loss,
                dc_cable_loss_pct=dc_cable_loss,
                shading_loss_pct=shading_loss
            )

            if res["status"] == "FAIL":
                st.error(f"❌ Calculation Error: {res.get('message', res.get('errors'))}")
            else:
                st.markdown("---")
                st.subheader("📊 Expected DC Production Performance")

                c_res1, c_res2, c_res3, c_res4 = st.columns(4)
                c_res1.metric("Daily DC Production", f"{res['daily_dc_energy_kwh']:,.1f} kWh", f"PSH: {psh} h/day")
                c_res2.metric("Annual DC Generation", f"{res['annual_dc_energy_mwh']:,.2f} MWh", f"{res['annual_dc_energy_kwh']:,.0f} kWh")
                c_res3.metric("Specific DC Yield", f"{res['specific_yield_dc_kwh_kwp']:,.0f} kWh/kWp", "Yearly yield per installed kWp")
                c_res4.metric("Compound DC Derate", f"{res['dc_derating_pct']:.1f}%", f"Total Loss: {res['total_dc_losses_pct']:.1f}%")

                # Update session state
                set_design_value("actual_dc_kwp", derived_dc_cap)
                set_design_value("daily_dc_energy_kwh", res["daily_dc_energy_kwh"])
                set_design_value("annual_dc_energy_kwh", res["annual_dc_energy_kwh"])

                st.markdown("---")
                st.subheader("📅 12-Month Projected DC Generation Schedule")
                
                m_df = pd.DataFrame(res["monthly_breakdown"])
                m_display = m_df.rename(columns={
                    "month": "Month",
                    "days": "Days in Month",
                    "psh": "Effective PSH (h/day)",
                    "daily_dc_kwh": "Avg Daily DC (kWh)",
                    "monthly_dc_kwh": "Monthly Energy (kWh)",
                    "monthly_dc_mwh": "Monthly Energy (MWh)"
                })[["Month", "Days in Month", "Effective PSH (h/day)", "Avg Daily DC (kWh)", "Monthly Energy (kWh)", "Monthly Energy (MWh)"]]
                st.dataframe(m_display, use_container_width=True, hide_index=True)

                st.bar_chart(m_df.set_index("month")["monthly_dc_kwh"])

                render_calculation_proof(
                    "DC Energy Generation Engineering Derivation",
                    [
                        {"formula": r"P_{dc} = \frac{N_{panels} \times P_{mp}}{1000}"},
                        {"label": "Installed DC Peak Capacity", "value": f"{num_panels} × {module_wp}W / 1000 = {derived_dc_cap:.2f} kWp"},
                        {"formula": r"\text{DC Derate} = (1 - L_{temp}) \times (1 - L_{soil}) \times (1 - L_{mismatch}) \times (1 - L_{cable}) \times (1 - L_{shade})"},
                        {"label": "Effective DC Derating Factor", "value": f"{res['dc_derating_factor']:.4f} ({res['dc_derating_pct']}%)"},
                        {"formula": r"E_{daily,DC} = P_{dc} \times \text{PSH} \times \text{DC Derate} \quad [\text{kWh/day}]"},
                        {"label": "Daily DC Energy Output", "value": f"{res['daily_dc_energy_kwh']:,.2f} kWh/day"},
                        {"formula": r"E_{annual,DC} = \sum_{m=1}^{12} E_{monthly,DC} \quad [\text{kWh/year}]"},
                        {"label": "Annual DC Total Energy Output", "value": f"{res['annual_dc_energy_kwh']:,.1f} kWh/year ({res['annual_dc_energy_mwh']:.2f} MWh)"},
                        {"formula": r"\text{Specific Yield}_{DC} = \frac{E_{annual,DC}}{P_{dc}} \quad [\text{kWh/kWp/year}]"},
                        {"label": "Specific DC Yield", "value": f"{res['specific_yield_dc_kwh_kwp']:,.1f} kWh/kWp/year"}
                    ]
                )

    except Exception as e:
        st.error(f"Error during DC production calculation: {str(e)}")
