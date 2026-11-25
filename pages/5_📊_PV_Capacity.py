import streamlit as st
import math
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from ui.equipment_forms import panel_picker
from core.pv_capacity import calculate_pv_capacity
from core.panel_quantity import calculate_panel_quantity

try:
    st.set_page_config(page_title="PV Capacity Calculator — Eng. Aashir", page_icon="📊", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("PV Capacity Calculator", "Determine required DC system size, module quantity, and sizing ratios", icon="📊")

# Calculation Mode Selection
calc_mode = st.radio(
    "Calculation Basis",
    ["Annual Energy Demand (kWh/year)", "Inverter AC Capacity & Target DC/AC Sizing Ratio"],
    horizontal=True
)

st.markdown("---")
c_in1, c_in2 = st.columns([1, 1])

if calc_mode == "Annual Energy Demand (kWh/year)":
    with c_in1:
        st.markdown("#### ☀️ Energy & Solar Resource Parameters")
        annual_demand = st.number_input("Annual Energy Demand (kWh/year)", min_value=100.0, value=150000.0, step=5000.0,
                                        help="Target total energy yield expected from the PV system over one full year.")
        psh = st.number_input("Peak Sun Hours — PSH (h/day)", min_value=0.5, max_value=12.0, value=4.5, step=0.1,
                              help="Average daily equivalent solar irradiance at module tilt angle (kWh/m²/day).")
        pr = st.number_input("Performance Ratio (PR)", min_value=0.50, max_value=0.95, value=0.78, step=0.01,
                             help="Typical PR range is 0.75 - 0.82 for well-designed grid-tie systems.")
        shading_loss = st.number_input("Estimated Shading Loss (%)", min_value=0.0, max_value=50.0, value=2.0, step=0.5)

    with c_in2:
        st.markdown("#### 🔋 Module & Sizing Constraints")
        panel = panel_picker("pv_cap_panel")
        target_ac = st.number_input("Installed / Planned Inverter AC Capacity (kW) [Optional]", min_value=0.0, value=5.0, step=1.0)

    if st.button("⚡ Calculate Required PV Capacity", type="primary", use_container_width=True):
        try:
            res = calculate_pv_capacity(annual_demand, psh, performance_ratio=pr, shading_loss_pct=shading_loss)
            req_dc_kwp = res["dc_capacity_kwp"]
            
            panel_wp = panel.rated_power_wp if panel else 630.0
            p_res = calculate_panel_quantity(req_dc_kwp, panel_wp)
            module_count = p_res["panel_count"]
            actual_dc_kwp = p_res["actual_dc_kwp"]
            
            dc_ac_ratio_val = round(actual_dc_kwp / target_ac, 2) if target_ac > 0 else None

            st.markdown("---")
            st.subheader("📊 Engineering Capacity Sizing Results")

            metrics = [
                {"label": "Required DC Power", "value": f"{req_dc_kwp:.2f}", "unit": "kWp"},
                {"label": "Module Count", "value": f"{module_count:,}", "unit": f"modules ({panel_wp}Wp)"},
                {"label": "Actual Installed DC", "value": f"{actual_dc_kwp:.2f}", "unit": "kWp"},
                {"label": "Daily Generation", "value": f"{res['daily_energy_kwh']:,.1f}", "unit": "kWh/day"},
            ]
            if dc_ac_ratio_val:
                metrics.append({"label": "DC/AC Ratio", "value": f"{dc_ac_ratio_val:.2f}", "unit": ""})

            render_result_card(
                "PV Array Capacity Takeoff",
                metrics,
                status=res["status"],
                explanation=f"Based on {annual_demand:,.0f} kWh/year demand with {psh} PSH and PR={pr:.2f}."
            )

            # Calculation Proof
            render_calculation_proof(
                "PV Capacity Sizing Formula & Derivation",
                [
                    {"formula": r"P_{dc,req} = \frac{E_{annual}}{365 \times \text{PSH} \times \text{PR} \times (1 - \text{Shading}/100)} \quad [\text{kWp}]"},
                    {"label": "Annual Demand (E_annual)", "value": f"{annual_demand:,.1f} kWh"},
                    {"label": "Peak Sun Hours (PSH)", "value": f"{psh} h/day"},
                    {"label": "Performance Ratio (PR)", "value": f"{pr:.2%}"},
                    {"label": "Effective Daily Solar Energy", "value": f"{psh * pr * (1 - shading_loss/100):.3f} kWh/kWp/day"},
                    {"label": "Required Minimum DC Capacity", "value": f"{req_dc_kwp:.2f} kWp"},
                    {"formula": r"N_{modules} = \left\lceil \frac{P_{dc,req} \times 1000}{P_{mp}} \right\rceil"},
                    {"label": f"Module Count ({panel_wp} Wp)", "value": f"{module_count} units -> {actual_dc_kwp:.2f} kWp actual"}
                ]
            )

            # Save to active project session state
            if "active_project" in st.session_state and st.session_state.active_project:
                st.session_state.active_project["target_dc_kwp"] = actual_dc_kwp
                st.session_state.active_project["panel_qty"] = module_count
                st.success("✅ Synced capacity parameters to active session.")

        except Exception as e:
            st.error(f"Error during capacity calculation: {str(e)}")

else:
    with c_in1:
        st.markdown("#### ⚡ Inverter Plant Capacity")
        target_ac_kw = st.number_input("Inverter Plant Rated AC Capacity (kW)", min_value=1.0, value=5.0, step=1.0)
        target_dc_ac = st.number_input("Target DC/AC Sizing Ratio (ILR)", min_value=0.80, max_value=1.80, value=1.20, step=0.05,
                                       help="Typical recommended DC/AC ratio is 1.15 - 1.30 depending on inverter oversizing limits.")
        psh_est = st.number_input("Site Peak Sun Hours (h/day)", min_value=1.0, max_value=10.0, value=4.5, step=0.1)
        pr_est = st.number_input("Expected Performance Ratio (PR)", min_value=0.5, max_value=0.95, value=0.78, step=0.01)

    with c_in2:
        st.markdown("#### 🔋 Module Selection")
        panel = panel_picker("pv_cap_inv_panel")

    if st.button("⚡ Calculate Array & Energy Output", type="primary", use_container_width=True):
        try:
            panel_wp = panel.rated_power_wp if panel else 630.0
            target_dc_kwp = target_ac_kw * target_dc_ac
            
            p_res = calculate_panel_quantity(target_dc_kwp, panel_wp)
            module_count = p_res["panel_count"]
            actual_dc_kwp = p_res["actual_dc_kwp"]
            actual_dc_ac = actual_dc_kwp / target_ac_kw
            
            est_annual_kwh = actual_dc_kwp * psh_est * 365.0 * pr_est
            est_daily_kwh = est_annual_kwh / 365.0

            st.markdown("---")
            st.subheader("📊 System Sizing Summary")

            metrics = [
                {"label": "Target AC Capacity", "value": f"{target_ac_kw:.1f}", "unit": "kW"},
                {"label": "Connected DC Capacity", "value": f"{actual_dc_kwp:.2f}", "unit": "kWp"},
                {"label": "Actual DC/AC Ratio", "value": f"{actual_dc_ac:.2f}", "unit": ""},
                {"label": "Module Quantity", "value": f"{module_count:,}", "unit": f"modules ({panel_wp}Wp)"},
                {"label": "Est. Annual Yield", "value": f"{est_annual_kwh:,.0f}", "unit": "kWh/year"}
            ]

            status = "PASS" if (1.05 <= actual_dc_ac <= 1.35) else "WARNING"
            render_result_card(
                "DC/AC Sizing & Plant Output",
                metrics,
                status=status,
                explanation=f"Plant rated at {target_ac_kw:.1f} kW AC with {actual_dc_kwp:.2f} kWp DC array."
            )

            render_calculation_proof(
                "Inverter Oversizing & Output Formulas",
                [
                    {"formula": r"P_{dc,target} = P_{ac} \times \text{DC/AC Ratio}"},
                    {"label": "Target DC Capacity", "value": f"{target_dc_kwp:.2f} kWp"},
                    {"formula": r"N_{panels} = \left\lceil \frac{P_{dc,target} \times 1000}{P_{mp}} \right\rceil"},
                    {"label": f"Modules ({panel_wp} Wp)", "value": f"{module_count} units -> {actual_dc_kwp:.2f} kWp installed"},
                    {"formula": r"E_{annual} = P_{dc,actual} \times \text{PSH} \times 365 \times \text{PR}"},
                    {"label": "Estimated Annual Generation", "value": f"{est_annual_kwh:,.1f} kWh/year ({est_annual_kwh/1000:,.2f} MWh)"}
                ]
            )

        except Exception as e:
            st.error(f"Error during calculation: {str(e)}")
