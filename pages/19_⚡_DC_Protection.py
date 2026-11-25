import streamlit as st
import pandas as pd
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from ui.equipment_forms import panel_picker
from core.dc_protection import (
    size_dc_string_fuse,
    size_dc_spd_from_master,
    size_dc_isolator_from_master
)
from core.project_state import (
    get_active_project,
    get_active_panel,
    get_design_value,
    set_design_value,
    render_active_project_banner
)

try:
    st.set_page_config(page_title="DC Protection Sizing — Eng. Aashir", page_icon="⚡", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()
render_active_project_banner()

page_header("DC Protection & Switchgear Sizing", "Select string gPV fuses (IEC 60269-6), DC surge protection devices (SPDs), and DC load-break isolators", icon="⚡")

# Retrieve defaults from project state
st_total_strings = get_design_value("total_strings", 14)
st_voc_cold = get_design_value("string_voc_cold_v", 780.0)
st_isc = get_design_value("dc_isc_current_a", 14.0)

c_panel, c_inputs = st.columns([1, 1])
with c_panel:
    st.markdown("#### 🔋 Module Specification")
    panel = panel_picker("dc_prot_panel")

with c_inputs:
    st.markdown("#### ⚡ DC Array Electrical Parameters")
    c1, c2 = st.columns(2)
    strings_total = c1.number_input("Total Strings in System", min_value=1, value=int(st_total_strings), step=1,
                                    help="Total string count. Used to determine total DC isolators (Company Rule: 1 isolator per string).")
    strings_per_mppt = c2.number_input("Parallel Strings per MPPT", min_value=1, value=1, step=1,
                                       help="Fuses are mandatory under IEC 60269-6 if parallel strings >= 3.")
    c3, c4 = st.columns(2)
    max_str_voc_cold = c3.number_input("Cold String Voc (V)", min_value=50.0, max_value=1500.0, value=float(st_voc_cold), step=5.0,
                                       help="Coldest string open-circuit voltage.")
    max_str_isc = c4.number_input("Module Short-Circuit Current Isc (A)", min_value=1.0, max_value=40.0, value=float(panel.isc if panel else st_isc), step=0.1)
    
    c5, c6 = st.columns(2)
    pole_pref = c5.selectbox("DC Isolator Configuration", ["Auto", "2P", "4P"], index=0,
                             help="Select 2P for single-circuit or 4P for double-circuit isolation.")
    strings_per_iso = c6.number_input("Strings per Isolator", min_value=1, max_value=4, value=1, step=1,
                                      help="Company Standard: 1 DC isolator per string.")

if st.button("⚡ Size DC Protection Switchgear", type="primary", use_container_width=True):
    try:
        preferred_poles = None if pole_pref == "Auto" else pole_pref
        
        # 1. DC String Fuse Sizing (IEC 60269-6)
        fuse_res = size_dc_string_fuse(max_str_isc, panel.max_series_fuse if panel else 30.0, strings_per_mppt)
        
        # 2. DC SPD Sizing from Master Catalog
        spd_res = size_dc_spd_from_master(max_str_voc_cold, num_inverters=1)
        
        # 3. DC Isolator Sizing from Master Catalog
        iso_res = size_dc_isolator_from_master(
            max_string_voc_cold=max_str_voc_cold,
            max_string_isc=max_str_isc,
            total_strings=int(strings_total),
            preferred_poles=preferred_poles,
            strings_per_isolator=int(strings_per_iso)
        )
        
        st.markdown("---")
        st.subheader("📋 DC Protection Equipment Takeoff")
        
        # Summary Table
        summary_rows = [
            {
                "Equipment": "DC String Fuse (gPV)",
                "Specification": f"{fuse_res.get('fuse_rating_a', 'Not Required')} A" if fuse_res.get("fuse_required") else "Not Required (Parallel strings < 3)",
                "Quantity": f"{strings_total * 2} pcs (pos & neg)" if fuse_res.get("fuse_required") else "0 pcs",
                "Rule / Standard": "IEC 60269-6",
                "Status": "🟢 PASS" if fuse_res.get("status") == "PASS" else "🔴 FAIL"
            },
            {
                "Equipment": "DC Surge Protection (SPD)",
                "Specification": f"{spd_res.get('model', 'DC SPD')} ({spd_res.get('rating') or ('Uc ' + str(spd_res.get('uc_v', spd_res.get('min_uc_v', 1000))) + 'V')})",
                "Quantity": f"{spd_res.get('quantity', 1)} set",
                "Rule / Standard": spd_res.get("rule_source", "ENGINEERING_RULE"),
                "Status": "🟢 PASS" if spd_res.get("status") == "PASS" else "🔵 MANUAL REVIEW"
            },
            {
                "Equipment": "DC Load-Break Isolator",
                "Specification": f"{iso_res.get('model', 'DC Isolator')} ({iso_res.get('rating', 'Rating Review Req')})",
                "Quantity": f"{iso_res.get('quantity', strings_total)} units",
                "Rule / Standard": iso_res.get("rule_source", "COMPANY_STANDARD"),
                "Status": "🟢 PASS" if iso_res.get("status") == "PASS" else "🔵 MANUAL REVIEW"
            }
        ]
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
        
        # Detailed Cards
        st.markdown("### 🔍 Technical Device Specifications")
        c_f, c_s, c_i = st.columns(3)
        
        with c_f:
            st.markdown("##### 🔌 DC String Fuses")
            if fuse_res.get("fuse_required"):
                st.info(f"**Required:** {fuse_res.get('fuse_rating_a', '30')} A gPV Fuses")
                st.caption(f"Rule: 1.5 × Isc = {max_str_isc * 1.5:.2f}A <= Max Series Fuse ({panel.max_series_fuse if panel else 30.0}A)")
            else:
                st.success("✅ No string fuses required (strings per MPPT < 3). Modules protected against reverse fault current.")
        
        with c_s:
            st.markdown("##### ⚡ DC Surge Protective Device (SPD)")
            if spd_res.get("status") == "PASS":
                st.success(f"**{spd_res.get('model', 'DC SPD')}**")
                st.markdown(f"- Continuous Operating Voltage ($U_c$): **{spd_res.get('uc_v', spd_res.get('min_uc_v', 1000))} VDC**")
                st.markdown(f"- Maximum Discharge Current ($I_{{max}}$): **{spd_res.get('imax_ka', 40)} kA**")
                st.markdown(f"- Voltage Protection Level ($U_p$): **<= {spd_res.get('up_kv', 3.8)} kV**")
                st.caption(f"Rule Source: `{spd_res.get('rule_source', 'ENGINEERING_RULE')}` (Uc >= 1.20 × Voc,cold)")
            else:
                st.error(spd_res.get("message", "Review Required"))
        
        with c_i:
            st.markdown("##### 🔲 DC Load-Break Switch / Isolator")
            if iso_res.get("status") == "PASS":
                st.success(f"**{iso_res.get('model', 'DC Isolator')}**")
                st.markdown(f"- Voltage Rating: **{iso_res.get('voltage_rating_v', 1000)} VDC**")
                st.markdown(f"- Current Rating: **{iso_res.get('current_rating_a', 32)} A (DC-PV2 / DC-21B)**")
                st.markdown(f"- Total Units: **{iso_res.get('quantity', strings_total)} units** ({strings_total} strings @ 1/string)")
                st.caption(f"Rule Source: `{iso_res.get('rule_source', 'COMPANY_STANDARD')}`")
            else:
                st.error(iso_res.get("message", "Review Required"))
        
        # Update project state
        set_design_value("dc_fuse", fuse_res)
        set_design_value("dc_spd", spd_res)
        set_design_value("dc_isolator", iso_res)
        
        proof_steps = [
            {"formula": r"V_{isolator,min} = 1.15 \times V_{oc,cold}"},
            {"label": "DC Isolator Voltage Threshold", "value": f"{max_str_voc_cold} × 1.15 = {max_str_voc_cold * 1.15:.1f} V"},
            {"formula": r"I_{isolator,min} = 1.25 \times I_{sc,module}"},
            {"label": "DC Isolator Current Threshold", "value": f"{max_str_isc} × 1.25 = {max_str_isc * 1.25:.2f} A"},
            {"formula": r"U_{c,SPD} \ge 1.20 \times V_{oc,cold}"},
            {"label": "SPD Minimum Continuous Operating Voltage", "value": f"{max_str_voc_cold} × 1.20 = {max_str_voc_cold * 1.20:.1f} V"},
            {"label": "Company Switchgear Takeoff Standard", "value": f"1 Isolator per String -> {iso_res['quantity']} units ({iso_res['rule_source']})"}
        ]
        render_calculation_proof("DC Protection Engineering Proof", proof_steps)
        
    except Exception as e:
        st.error(f"Error sizing DC protection switchgear: {str(e)}")
