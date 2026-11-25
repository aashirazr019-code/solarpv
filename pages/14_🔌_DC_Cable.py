import streamlit as st
import pandas as pd
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from ui.equipment_forms import panel_picker
from core.cable_sizing import select_dc_cable_comprehensive
from core.electrical_data import INSTALLATION_METHODS
from core.project_state import (
    get_manual_overrides,
    set_manual_override,
    clear_manual_overrides,
    recalculate_system_state,
    render_active_project_banner
)

try:
    st.set_page_config(page_title="DC Cable Sizing — Eng. Aashir", page_icon="🔌", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("Solar DC Cable Sizing Calculator", "Size solar DC string & main cables based on continuous ampacity and voltage drop limits", icon="🔌")
render_active_project_banner()

# Check manual overrides banner
overrides = get_manual_overrides()
if "dc_cable_csa_mm2" in overrides:
    col_ov1, col_ov2 = st.columns([3, 1])
    col_ov1.warning(f"⚠️ **Manual Override Active:** DC Solar String Cable is locked to **{overrides['dc_cable_csa_mm2']} mm²** in Active Project SLD & BOQ.")
    if col_ov2.button("↺ Reset to Auto Sizing", key="reset_dc_override", use_container_width=True):
        overrides.pop("dc_cable_csa_mm2", None)
        recalculate_system_state()
        st.success("Reset DC cable to automatic engineering sizing.")
        st.rerun()

calc_source = st.radio("Current Calculation Source", ["Manual Current Entry", "From Solar Module Parameters"], horizontal=True)

c1, c2 = st.columns(2)

if calc_source == "From Solar Module Parameters":
    with c1:
        st.markdown("#### 🔋 Module & Paralleling")
        panel = panel_picker("dc_cable_panel")
        num_parallel = st.number_input("Number of Parallel Strings on this Cable Run", min_value=1, max_value=20, value=1, step=1,
                                       help="1 for direct string cables from array to inverter/combiner; >1 for combiner-to-inverter DC homeruns.")
        panels_per_str = st.number_input("Number of Modules per String", min_value=1, max_value=35, value=16, step=1)
        base_current = panel.imp if panel else 13.10
        string_vmp = (panel.vmp if panel else 42.0) * panels_per_str
        st.info(f"Calculated Module Imp = **{base_current:.2f} A** | String Operating Voltage = **{string_vmp:.1f} V**")
    with c2:
        st.markdown("#### 📏 Cable Route & Installation")
        length = st.number_input("One-Way Cable Route Length (m)", min_value=1.0, max_value=500.0, value=35.0, step=5.0)
        sys_voltage = st.number_input("Circuit Operating DC Voltage (V)", min_value=12.0, max_value=1500.0, value=float(string_vmp), step=10.0)
        max_vd_pct = st.number_input("Max Allowable Voltage Drop (%)", min_value=0.5, max_value=5.0, value=1.5, step=0.1,
                                     help="Standard industry benchmark is <= 1.5% for DC solar circuits (IEC 60364-7-712).")
        material = st.selectbox("Conductor Material", ["Copper (Cu)", "Aluminium (Al)"])
        method_label = st.selectbox("Installation Method (Kelani / BS 7671)", options=[m[0] for m in INSTALLATION_METHODS], index=1)
        method_key = next((m[1] for m in INSTALLATION_METHODS if m[0] == method_label), "c_2c")
        derating_factor = st.number_input("Combined Derating Factor (Temp + Grouping)", min_value=0.10, max_value=1.00, value=0.90, step=0.05)

else:
    with c1:
        st.markdown("#### ⚡ Operating Current Parameters")
        base_current = st.number_input("Single String Operating Current (A)", min_value=0.5, max_value=200.0, value=13.5, step=0.5)
        num_parallel = st.number_input("Number of Parallel Strings", min_value=1, max_value=20, value=1, step=1)
        st.info(f"Total Circuit Current: **{base_current * num_parallel:.2f} A**")
    with c2:
        st.markdown("#### 📏 Cable Route & Environmental Conditions")
        length = st.number_input("One-Way Cable Route Length (m)", min_value=1.0, max_value=500.0, value=35.0, step=5.0)
        sys_voltage = st.number_input("Circuit Operating DC Voltage (V)", min_value=12.0, max_value=1500.0, value=650.0, step=50.0)
        max_vd_pct = st.number_input("Max Allowable Voltage Drop (%)", min_value=0.5, max_value=5.0, value=1.5, step=0.1)
        material = st.selectbox("Conductor Material", ["Copper (Cu)", "Aluminium (Al)"])
        method_label = st.selectbox("Installation Method (Kelani / BS 7671)", options=[m[0] for m in INSTALLATION_METHODS], index=1)
        method_key = next((m[1] for m in INSTALLATION_METHODS if m[0] == method_label), "c_2c")
        derating_factor = st.number_input("Combined Derating Factor (Temp + Grouping)", min_value=0.10, max_value=1.00, value=0.90, step=0.05)

mat_str = "copper" if "Copper" in material else "aluminium"

if st.button("🔌 Size DC Solar Cable", type="primary", use_container_width=True):
    try:
        res = select_dc_cable_comprehensive(
            design_current_a=base_current,
            length_m=length,
            nominal_voltage_v=sys_voltage,
            num_parallel_strings=num_parallel,
            max_vd_pct=max_vd_pct,
            method_key=method_key,
            derating_factor=derating_factor,
            material=mat_str,
            safety_factor=1.25
        )

        if res["status"] == "FAIL":
            st.error(f"❌ Sizing Failure: {res.get('message', 'Current exceeds cable capacity.')}")
        else:
            st.markdown("---")
            st.subheader(f"✅ Recommended Conductor: {res['csa_mm2']} mm² {res['material']}")

            c_res1, c_res2, c_res3, c_res4 = st.columns(4)
            c_res1.metric("Cable Size", f"{res['csa_mm2']} mm²", f"Thermal Base: {res['thermal_csa_mm2']} mm²")
            c_res2.metric("Voltage Drop", f"{res['voltage_drop_pct']:.2f}%", f"{res['voltage_drop_v']:.2f} V (Limit: {max_vd_pct}%)")
            c_res3.metric("Operating Current", f"{res['operating_current_a']:.2f} A", f"Ampacity: {res['tabulated_ampacity_a']:.1f} A")
            c_res4.metric("Conductor Power Loss", f"{res['power_loss_w']:.1f} W", f"Length: {length * 2:.0f}m loop")

            if res["upsized_for_voltage_drop"]:
                st.info(f"ℹ️ **Conductor Upsized for Voltage Drop:** Thermal ampacity required **{res['thermal_csa_mm2']} mm²**, but conductor was automatically upsized to **{res['csa_mm2']} mm²** to satisfy the {max_vd_pct}% voltage drop limit over {length}m.")

            c_app1, c_app2 = st.columns([3, 1])
            with c_app1:
                st.caption(f"Synchronize this sizing ({res['csa_mm2']} mm²) into the Active Project SLD diagram, schematic exports, and Bill of Quantities.")
            with c_app2:
                if st.button("📌 Apply to Active Project", key="apply_dc_csa_btn", type="primary", use_container_width=True):
                    set_manual_override("dc_cable_csa_mm2", res["csa_mm2"])
                    st.success(f"✅ Applied {res['csa_mm2']} mm² DC Cable to Active Project SLD & BOQ!")
                    st.rerun()

            render_calculation_proof(
                "DC Cable Ampacity & Voltage Drop Engineering Derivation",
                [
                    {"formula": r"I_b = N_{parallel} \times I_{string}, \quad I_{tab,req} = \frac{I_b \times 1.25}{C_a \times C_g}"},
                    {"label": "Total Operating Current (I_b)", "value": f"{res['operating_current_a']} A"},
                    {"label": "Required Derated Ampacity", "value": f"{res['required_tabulated_a']} A"},
                    {"label": "Selected Cable Ampacity (I_z)", "value": f"{res['tabulated_ampacity_a']} A"},
                    {"formula": r"\Delta V = \frac{2 \times L \times I_b \times \rho_{70}}{S_{csa}} \quad [\text{V}]"},
                    {"label": f"Resistivity (rho @ 70°C for {res['material']})", "value": "0.02135 ohm·mm²/m" if mat_str == "copper" else "0.0350 ohm·mm²/m"},
                    {"label": "Calculated Voltage Drop", "value": f"{res['voltage_drop_v']} V ({res['voltage_drop_pct']}%)"},
                    {"formula": r"P_{loss} = \Delta V \times I_b \quad [\text{W}]"},
                    {"label": "Conductor I²R Power Loss", "value": f"{res['power_loss_w']} W"}
                ]
            )

    except Exception as e:
        st.error(f"Error during DC cable sizing: {str(e)}")
