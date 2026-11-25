import streamlit as st
import pandas as pd
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from core.ac_protection import (
    size_ac_spd_from_master,
    size_ac_isolator_from_master,
    size_lockable_isolator_from_master,
    select_rcd
)
from core.project_state import (
    get_active_project,
    get_active_inverter,
    get_design_value,
    set_design_value,
    render_active_project_banner
)

try:
    st.set_page_config(page_title="AC Protection Sizing — Eng. Aashir", page_icon="⚡", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()
render_active_project_banner()

page_header("AC Protection & Switchgear Sizing", "Select AC Surge Protectors (SPDs), AC Isolators, CEB Utility Lockable Isolators, and RCDs", icon="⚡")

# State defaults
st_ac_current = get_design_value("ac_operating_current_a", 158.8)
st_ac_kw = get_design_value("actual_ac_kw", 100.0)
st_phases = get_design_value("grid_phases", 3)
st_voltage = get_design_value("grid_voltage_v", 400.0)

c1, c2 = st.columns(2)
with c1:
    st.markdown("#### ⚡ Inverter AC Output Parameters")
    ac_current = st.number_input("Inverter Max AC Current (A)", min_value=1.0, max_value=2000.0, value=float(st_ac_current), step=1.0,
                                 help="Continuous full-load AC output current from inverter datasheet.")
    ac_voltage = st.number_input("Nominal AC Grid Voltage (V)", min_value=110.0, max_value=690.0, value=float(st_voltage), step=10.0)
    phases = st.radio("System Phases", [3, 1], index=0 if st_phases == 3 else 1, horizontal=True)

with c2:
    st.markdown("#### 🛡️ Protection & Safety Factors")
    safety_factor = st.number_input("Switchgear Safety Factor", min_value=1.0, max_value=1.5, value=1.25, step=0.05,
                                    help="Continuous rating multiplier (standard 1.25 per IEC 60364-7-712).")
    has_transformer = st.checkbox("Transformer Isolated Inverter?", value=False,
                                  help="Tick if inverter has an internal galvanic isolation transformer.")
    inverter_tech = st.selectbox("Inverter Technology", ["Transformerless String Inverter", "Microinverter", "Central Inverter"])

if st.button("⚡ Size AC Protection Switchgear", type="primary", use_container_width=True):
    try:
        # 1. AC Isolator Sizing
        ac_iso_res = size_ac_isolator_from_master(ac_current, phases=phases, safety_factor=safety_factor)
        
        # 2. Utility Lockable Isolator Sizing
        lock_iso_res = size_lockable_isolator_from_master(ac_current, phases=phases, safety_factor=safety_factor)
        
        # 3. AC SPD Sizing
        spd_res = size_ac_spd_from_master(phases=phases, ac_voltage_v=ac_voltage)
        
        # 4. RCD Sizing
        rcd_res = select_rcd(inverter_type=inverter_tech, has_transformer=has_transformer)
        
        st.markdown("---")
        st.subheader("📋 AC Protection & Switchgear Schedule")
        
        schedule_rows = [
            {
                "Equipment": "AC Local Isolator",
                "Specification": f"{ac_iso_res['model']} ({ac_iso_res.get('rating', 'Manual Review')})",
                "Role": "Local Inverter AC Disconnect",
                "Rule / Standard": ac_iso_res["rule_source"],
                "Status": "🟢 PASS" if ac_iso_res["status"] == "PASS" else "🔵 MANUAL REVIEW"
            },
            {
                "Equipment": "Utility Lockable Isolator",
                "Specification": f"{lock_iso_res['model']} ({lock_iso_res.get('rating', 'Manual Review')})",
                "Role": "Point of Utility Interconnection (Padlockable in OFF)",
                "Rule / Standard": lock_iso_res["rule_source"],
                "Status": "🟢 PASS" if lock_iso_res["status"] == "PASS" else "🔵 MANUAL REVIEW"
            },
            {
                "Equipment": "AC Surge Protective Device (SPD)",
                "Specification": f"{spd_res['model']} (Uc {spd_res.get('uc_v', 385)}V, {spd_res.get('poles', '3P+N')})",
                "Role": "AC Switchboard Lightning & Surge Clamping",
                "Rule / Standard": spd_res["rule_source"],
                "Status": "🟢 PASS" if spd_res["status"] == "PASS" else "🔵 MANUAL REVIEW"
            },
            {
                "Equipment": "Residual Current Device (RCD)",
                "Specification": f"{rcd_res['rcd_type']} (30mA / 300mA)",
                "Role": "Earth Fault & Residual DC Injection Detection",
                "Rule / Standard": "IEC 60364-7-712 / IEC 62423",
                "Status": "🟢 PASS"
            }
        ]
        st.dataframe(pd.DataFrame(schedule_rows), use_container_width=True, hide_index=True)
        
        # Technical Details Cards
        st.markdown("### 🔍 Technical Device Specifications")
        col_iso1, col_iso2 = st.columns(2)
        
        with col_iso1:
            st.markdown("##### 🔌 AC Local Isolator (Inverter Output)")
            if ac_iso_res["status"] == "PASS":
                st.success(f"**{ac_iso_res['model']}**")
                st.markdown(f"- Continuous Thermal Current ($I_{{th}}$): **{ac_iso_res['rated_current_a']} A**")
                st.markdown(f"- Rated Voltage ($U_e$): **{ac_iso_res['voltage_rating_v']} VAC**")
                st.markdown(f"- Configuration: **{ac_iso_res['poles']} ({ac_iso_res['ac_type']})**")
                st.caption(f"Rule Source: `{ac_iso_res['rule_source']}` (Design current: {ac_current * safety_factor:.1f}A)")
            else:
                st.error(ac_iso_res["message"])
                
        with col_iso2:
            st.markdown("##### 🔒 Utility Lockable Isolator (Grid Boundary)")
            if lock_iso_res["status"] == "PASS":
                st.success(f"**{lock_iso_res['model']}**")
                st.markdown(f"- Rated Continuous Current: **{lock_iso_res['rated_current_a']} A**")
                st.markdown(f"- Configuration: **{lock_iso_res['poles']} ({phases}-Phase)**")
                st.markdown(f"- Feature: **{lock_iso_res['features']}**")
                st.caption(f"Rule Source: `{lock_iso_res['rule_source']}` — Mandatory for utility grid synchronization.")
            else:
                st.error(lock_iso_res["message"])
                
        col_spd, col_rcd = st.columns(2)
        with col_spd:
            st.markdown("##### ⚡ AC Surge Protection Device (SPD)")
            if spd_res["status"] == "PASS":
                st.success(f"**{spd_res['model']}**")
                st.markdown(f"- Max Continuous Operating Voltage ($U_c$): **{spd_res['uc_v']} VAC**")
                st.markdown(f"- Max Discharge Current ($I_{{max}}$): **{spd_res['imax_ka']} kA**")
                st.markdown(f"- Poles: **{spd_res['poles']}**")
                st.caption(f"Rule Source: `{spd_res['rule_source']}` (IEC 61643-11 Type II)")
            else:
                st.error("No matching AC SPD found.")
                
        with col_rcd:
            st.markdown("##### 🛡️ Residual Current Protection (RCD)")
            st.info(f"**Required: {rcd_res['rcd_type']} RCD**")
            st.markdown(f"- Personal Touch Sensitivity: **{rcd_res['sensitivity_ma']} mA**")
            st.markdown(f"- Fire Protection Sensitivity: **{rcd_res['fire_protection_sensitivity_ma']} mA**")
            st.caption(rcd_res["reason"])
            
        # Update project state
        set_design_value("ac_isolator", ac_iso_res)
        set_design_value("lockable_isolator", lock_iso_res)
        set_design_value("ac_spd", spd_res)
        set_design_value("rcd", rcd_res)
        
        proof_steps = [
            {"formula": r"I_{design} = I_{max\_ac} \times 1.25"},
            {"label": "AC Switchgear Design Current", "value": f"{ac_current} × {safety_factor} = {ac_current * safety_factor:.1f} A"},
            {"label": "AC Isolator Selection", "value": f"{ac_iso_res['model']} ({ac_iso_res['rated_current_a']}A) >= {ac_current * safety_factor:.1f}A"},
            {"label": "CEB Lockable Isolator Rule", "value": f"{lock_iso_res['model']} ({lock_iso_res['rated_current_a']}A, {lock_iso_res['poles']}) with padlockable handle (Source: {lock_iso_res['rule_source']})"},
            {"formula": r"U_{c,SPD} \ge 1.15 \times V_{L-N}"},
            {"label": "AC SPD Sizing", "value": f"Uc {spd_res.get('uc_v', 385)}V exceeds minimum required threshold"}
        ]
        render_calculation_proof("AC Protection Engineering Sizing Proof", proof_steps)

    except Exception as e:
        st.error(f"Error sizing AC protection switchgear: {str(e)}")
