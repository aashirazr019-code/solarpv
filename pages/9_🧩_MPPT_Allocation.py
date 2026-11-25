import streamlit as st
import pandas as pd
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from ui.equipment_forms import panel_picker, inverter_picker, design_temperature_inputs
from core.models import Project, SpacingConfig
from core.string_sizing import panels_per_string_range, voltage_check, cold_voc, hot_vmp, cold_vmp
from core.mppt_allocation import allocate_mppt_comprehensive, allocate_mppt_for_inverter, allocate_mppt
from core.project_state import get_active_project, get_active_panel, get_active_inverter, set_design_value, render_active_project_banner

try:
    st.set_page_config(page_title="MPPT Allocation Calculator — Eng. Aashir", page_icon="🧩", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()
render_active_project_banner()

page_header("MPPT Allocation & Verification Engine", "Allocate strings per MPPT tracker, compute operating/Isc currents, verify voltage limits, and validate chassis constraints", icon="🧩")

c_eq1, c_eq2 = st.columns(2)
with c_eq1:
    st.markdown("#### 🔋 Module Specification")
    panel = panel_picker("mppt_page_panel")
with c_eq2:
    st.markdown("#### ⚡ Inverter Specification")
    inverter = inverter_picker("mppt_page_inv")

st.markdown("---")
c_param1, c_param2, c_param3 = st.columns(3)
with c_param1:
    st.markdown("#### 🌡️ Site Ambient Temperatures")
    t_min, t_max = design_temperature_inputs("mppt_page_temps")
with c_param2:
    st.markdown("#### 🔢 Inverter Array Scope")
    inverter_qty = st.number_input("Number of Inverter Units", min_value=1, max_value=50, value=1, step=1,
                                   help="Number of identical inverter units installed in this subsystem.")
    total_strings = st.number_input("Total Number of Strings", min_value=1, max_value=200, value=10, step=1,
                                    help="Total strings to distribute across the inverters.")
with c_param3:
    st.markdown("#### 📏 String Length")
    dummy_proj = Project(
        id="mppt-calc-temp", name="MPPT Calc", location="", installation_type="rooftop",
        target_ac_capacity_kw=100.0, min_design_temp_c=t_min, max_design_temp_c=t_max,
        dc_ac_ratio_min=1.05, dc_ac_ratio_preferred=1.20, dc_ac_ratio_max=1.35,
        panel_id=panel.id if panel else "", panel_available_qty=1000,
        area_length_m=100.0, area_width_m=50.0, spacing_config=SpacingConfig()
    )
    rng_res = panels_per_string_range(panel, inverter, dummy_proj)
    default_panels_per_str = min(rng_res["max_panels_per_string"], max(rng_res["min_panels_per_string"], 16))
    
    st.caption(f"Valid Range: **{rng_res['min_panels_per_string']} to {rng_res['max_panels_per_string']} panels/string**")
    panels_per_str = st.number_input("Selected Panels per String", min_value=1, max_value=35, value=default_panels_per_str, step=1)

if st.button("🧩 Execute Full MPPT Allocation & Validation", type="primary", use_container_width=True):
    try:
        alloc_res = allocate_mppt_comprehensive(
            inverter=inverter,
            panel=panel,
            total_strings=int(total_strings),
            panels_per_string=int(panels_per_str),
            t_min_c=t_min,
            t_max_c=t_max,
            num_inverters=int(inverter_qty)
        )

        st.markdown("---")

        # Top level status banner
        if not alloc_res["valid"]:
            st.error(f"❌ **{alloc_res['message']}**")
            for r in alloc_res["failure_reasons"]:
                st.markdown(f"- 🔴 **Violation:** {r}")
        elif alloc_res["status"] == "WARNING":
            st.warning(f"⚠️ **{alloc_res['message']}**")
            for w in alloc_res["warnings"]:
                st.markdown(f"- 🟡 **Notice:** {w}")
        else:
            st.success(f"✅ **{alloc_res['message']}**")

        # Summary KPIs
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Max MPPT Current (Imp)", f"{alloc_res['max_mppt_current_a']:.2f} A", f"Limit: {inverter.max_input_current_per_mppt_a} A")
        m2.metric("Max MPPT Current (Isc)", f"{alloc_res['max_mppt_isc_a']:.2f} A", f"Limit: {inverter.max_isc_per_mppt_a} A")
        m3.metric("Cold Voc String", f"{alloc_res['string_voc_cold_v']:.1f} V", f"Limit <= {inverter.max_dc_voltage_v} V")
        m4.metric("Hot Vmp String", f"{alloc_res['string_vmp_hot_v']:.1f} V", f"MPPT: {inverter.mppt_voltage_min_v}-{inverter.mppt_voltage_max_v} V")

        st.markdown("### 📋 MPPT Allocation Schedule Matrix")
        st.caption("Detailed tracker-by-tracker current, voltage, and hardware input limit verification:")

        df_matrix = pd.DataFrame(alloc_res["allocation_table"])
        st.dataframe(df_matrix, use_container_width=True, hide_index=True)

        # Update session state for downstream calculators
        set_design_value("total_strings", int(total_strings))
        set_design_value("panels_per_string", int(panels_per_str))
        set_design_value("panel_qty", int(total_strings * panels_per_str))
        set_design_value("actual_dc_kwp", round((total_strings * panels_per_str * panel.rated_power_wp) / 1000.0, 2))
        set_design_value("mppt_allocation", alloc_res)
        set_design_value("dc_operating_current_a", alloc_res["max_mppt_current_a"])
        set_design_value("dc_isc_current_a", alloc_res["max_mppt_isc_a"])
        set_design_value("string_voc_cold_v", alloc_res["string_voc_cold_v"])
        set_design_value("string_vmp_hot_v", alloc_res["string_vmp_hot_v"])

        render_calculation_proof(
            "Tracker Voltage & Current Equations",
            [
                {"formula": r"V_{oc,string\_cold} = N_{panels} \times V_{oc,STC} \times [1 + \frac{\gamma_{Voc}}{100} \times (T_{min} - 25)]"},
                {"label": f"Cold String Voc ({panels_per_str} panels)", "value": f"{alloc_res['string_voc_cold_v']} V (Inverter Max: {inverter.max_dc_voltage_v} V)"},
                {"formula": r"V_{mp,string\_hot} = N_{panels} \times V_{mp,STC} \times [1 + \frac{\gamma_{Vmp}}{100} \times (T_{max} - 25)]"},
                {"label": f"Hot String Vmp ({panels_per_str} panels)", "value": f"{alloc_res['string_vmp_hot_v']} V (MPPT Window: {inverter.mppt_voltage_min_v} - {inverter.mppt_voltage_max_v} V)"},
                {"formula": r"I_{MPPT,Imp} = N_{strings\_assigned} \times I_{mp,STC}"},
                {"label": "Maximum MPPT Operating Current", "value": f"{alloc_res['max_mppt_current_a']} A"},
                {"formula": r"I_{MPPT,Isc} = N_{strings\_assigned} \times I_{sc,STC}"},
                {"label": "Maximum MPPT Short-Circuit Current", "value": f"{alloc_res['max_mppt_isc_a']} A (Ceiling: {inverter.max_isc_per_mppt_a} A)"}
            ]
        )

    except Exception as e:
        st.error(f"Error during MPPT allocation: {str(e)}")
