import streamlit as st
import pandas as pd
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from core.cable_sizing import select_ac_cable_comprehensive
from core.electrical_data import INSTALLATION_METHODS
from core.project_state import (
    get_manual_overrides,
    set_manual_override,
    clear_manual_overrides,
    recalculate_system_state,
    render_active_project_banner
)

try:
    st.set_page_config(page_title="AC Cable Sizing — Eng. Aashir", page_icon="🔌", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("Inverter AC Cable Sizing Calculator", "Size AC output cables complying with BS 7671 & Kelani Cables Table A1 with coordinated breaker sizing", icon="🔌")
render_active_project_banner()

# Check manual overrides banner
overrides = get_manual_overrides()
active_ac_ov = []
if "main_ac_cable_csa_mm2" in overrides:
    active_ac_ov.append(f"Main Cable: {overrides['main_ac_cable_csa_mm2']} mm²")
if "main_breaker_rating_a" in overrides:
    active_ac_ov.append(f"Breaker: {overrides['main_breaker_rating_a']} A")
elif "main_breaker_spec" in overrides:
    active_ac_ov.append(f"Breaker: {overrides['main_breaker_spec']}")

if active_ac_ov:
    col_ov1, col_ov2 = st.columns([3, 1])
    col_ov1.warning(f"⚠️ **Manual Override Active:** {' | '.join(active_ac_ov)} in Active Project SLD & BOQ.")
    if col_ov2.button("↺ Reset to Auto Sizing", key="reset_ac_override", use_container_width=True):
        overrides.pop("main_ac_cable_csa_mm2", None)
        overrides.pop("main_breaker_rating_a", None)
        overrides.pop("main_breaker_spec", None)
        recalculate_system_state()
        st.success("Reset AC cable and breaker to automatic engineering sizing.")
        st.rerun()

c_in1, c_in2 = st.columns(2)

with c_in1:
    st.markdown("#### ⚡ Inverter Power & Electrical Characteristics")
    power_kw = st.number_input("Inverter AC Output Power (kW)", min_value=1.0, max_value=50000.0, value=100.0, step=5.0)
    phase_option = st.selectbox("System Phase Configuration", ["3-Phase (400V / 415V)", "1-Phase (230V)"])
    phases = 3 if "3-Phase" in phase_option else 1
    default_v = 400.0 if phases == 3 else 230.0
    sys_voltage = st.number_input("Nominal Line Voltage (V)", min_value=100.0, max_value=1000.0, value=default_v, step=10.0)
    pf = st.number_input("Power Factor (cos phi)", min_value=0.70, max_value=1.00, value=0.95, step=0.01)

with c_in2:
    st.markdown("#### 📏 Cable Route & Installation Parameters")
    length = st.number_input("One-Way Cable Route Length (m)", min_value=1.0, max_value=1000.0, value=25.0, step=5.0)
    max_vd = st.number_input("Max Allowable Voltage Drop (%)", min_value=0.5, max_value=5.0, value=3.0, step=0.1,
                             help="BS 7671 standard recommendation is <= 3% for AC power distribution circuits.")
    material = st.selectbox("Conductor Material", ["Copper (Cu)", "Aluminium (Al)"])
    default_method_idx = 4 if phases == 3 else 1
    method_label = st.selectbox("Installation Method (BS 7671 / Kelani Table A1)", options=[m[0] for m in INSTALLATION_METHODS], index=default_method_idx)
    method_key = next((m[1] for m in INSTALLATION_METHODS if m[0] == method_label), "e_3c")
    derating = st.number_input("Environmental Derating Factor (Temp + Grouping)", min_value=0.10, max_value=1.00, value=0.85, step=0.05)

mat_str = "copper" if "Copper" in material else "aluminium"

if st.button("🔌 Size AC Cable & Protection Device", type="primary", use_container_width=True):
    try:
        res = select_ac_cable_comprehensive(
            ac_power_kw=power_kw,
            nominal_voltage_v=sys_voltage,
            length_m=length,
            phases=phases,
            power_factor=pf,
            max_vd_pct=max_vd,
            method_key=method_key,
            derating_factor=derating,
            material=mat_str,
            safety_factor=1.25
        )

        if res["status"] == "FAIL":
            st.error(f"❌ Sizing Failure: {res.get('message', 'Current exceeds cable capacity.')}")
        else:
            st.markdown("---")
            st.subheader(f"✅ Sizing Takeoff: {res['csa_mm2']} mm² {res['material']} ({phases}-Phase AC)")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Operating Current (Ib)", f"{res['operating_current_a']:.2f} A", f"Power: {power_kw} kW @ PF={pf}")
            c1_sub = f"Thermal Base: {res['thermal_csa_mm2']} mm²" if res["upsized_for_voltage_drop"] else "Ampacity Governed"
            c2.metric("Recommended Cable", f"{res['csa_mm2']} mm²", c1_sub)
            c3.metric("Voltage Drop", f"{res['voltage_drop_pct']:.2f}%", f"{res['voltage_drop_v']:.2f} V (Limit: {max_vd}%)")
            c4.metric("Coordinated Breaker", f"{res['protection_device'].get('rated_current_a', 'N/A')} A", f"Type: {res['protection_device'].get('device_type', 'MCCB')}")

            if res["upsized_for_voltage_drop"]:
                st.info(f"ℹ️ **Conductor Upsized for Voltage Drop:** Conductor was upsized from **{res['thermal_csa_mm2']} mm²** to **{res['csa_mm2']} mm²** to satisfy the {max_vd}% voltage drop ceiling over {length}m.")

            prot = res["protection_device"]
            st.markdown(
                f"##### 🛡️ Circuit Breaker Coordination Check:\n"
                f"• **Continuous Load Current ($I_b$):** {res['operating_current_a']:.2f} A\n"
                f"• **Breaker Nominal Rating ($I_n$):** {prot.get('rated_current_a', '-')} A ({prot.get('device_type', 'MCCB')})\n"
                f"• **Cable Derated Ampacity ($I_z$):** {res['tabulated_ampacity_a']:.1f} A\n"
                f"• **Compliance:** {'✅ $I_b \\le I_n \\le I_z$ Satisfied' if prot.get('status') == 'PASS' else '⚠️ Protection coordination warning'}"
            )

            c_app1, c_app2 = st.columns([3, 1])
            with c_app1:
                brk_lbl = f"{prot.get('rated_current_a', 'N/A')} A {prot.get('device_type', 'MCCB')}"
                st.caption(f"Synchronize this sizing (Cable: **{res['csa_mm2']} mm²**, Breaker: **{brk_lbl}**) into the Active Project SLD diagram and Bill of Quantities.")
            with c_app2:
                if st.button("📌 Apply to Active Project", key="apply_ac_to_project", type="primary", use_container_width=True):
                    set_manual_override("main_ac_cable_csa_mm2", res["csa_mm2"])
                    if prot.get("rated_current_a"):
                        set_manual_override("main_breaker_rating_a", prot["rated_current_a"])
                    st.success(f"✅ Applied {res['csa_mm2']} mm² AC Cable & {brk_lbl} to Active Project SLD & BOQ!")
                    st.rerun()

            render_calculation_proof(
                "AC Sizing & Voltage Drop Engineering Derivation",
                [
                    {"formula": r"I_b = \frac{P_{ac} \times 1000}{\sqrt{3} \times V_{ac} \times \cos\phi} \quad (3\text{-Phase})" if phases == 3 else r"I_b = \frac{P_{ac} \times 1000}{V_{ac} \times \cos\phi} \quad (1\text{-Phase})"},
                    {"label": "Calculated Operating Current (I_b)", "value": f"{res['operating_current_a']} A"},
                    {"label": "Required Tabulated Ampacity (I_req)", "value": f"{res['required_tabulated_a']} A"},
                    {"label": "Cable Tabulated Ampacity (I_z)", "value": f"{res['tabulated_ampacity_a']} A"},
                    {"formula": r"\Delta V_{3\Phi} = \frac{\sqrt{3} \cdot L \cdot I_b \cdot (R \cos\phi + X \sin\phi)}{1000} \quad [\text{V}]" if phases == 3 else r"\Delta V_{1\Phi} = \frac{2 \cdot L \cdot I_b \cdot (R \cos\phi + X \sin\phi)}{1000} \quad [\text{V}]"},
                    {"label": "Calculated AC Voltage Drop", "value": f"{res['voltage_drop_v']} V ({res['voltage_drop_pct']}%)"},
                    {"label": "Circuit Power Loss (P_loss)", "value": f"{res['power_loss_w']} W"}
                ]
            )

    except Exception as e:
        st.error(f"Error during AC cable sizing: {str(e)}")
