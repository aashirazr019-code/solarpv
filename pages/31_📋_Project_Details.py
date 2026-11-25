"""
pages/31_📋_Project_Details.py — Project Details & Engineering Site Criteria
Detailed view and management of active project parameters, site environmental criteria, and constraints.
Authored by Eng. Aashir © 2026.
"""
import streamlit as st
import pandas as pd
from ui.styles import apply_custom_css
from ui.components import page_header, render_status
from data.database import save_project
from core.project_state import get_active_project, set_active_project, render_active_project_banner
from core.models import SpacingConfig

try:
    st.set_page_config(page_title="Project Details — Solar PV Platform", page_icon="📋", layout="wide")
except Exception:
    pass

apply_custom_css()
render_active_project_banner()
page_header("Project Details & Site Criteria", "Inspect and update active photovoltaic project site criteria, grid parameters, and design constraints", icon="📋")

proj = get_active_project()

st.markdown("### 📝 Edit Project Parameters")
with st.form("edit_project_form"):
    c1, c2, c3, c4 = st.columns(4)
    p_name = c1.text_input("Project Name", value=proj.get("name", "Commercial Solar PV System"))
    p_cust = c2.text_input("Client / Customer", value=proj.get("customer_name", "Industrial Client"))
    p_site = c3.text_input("Site / Facility", value=proj.get("site_name", "Main Facility"))
    p_loc = c4.text_input("Geographical Location", value=proj.get("location", "Colombo, Sri Lanka"))

    c5, c6, c7, c8 = st.columns(4)
    install_types = ["Rooftop Commercial", "Ground Mount", "Carport Canopy", "Industrial Metal Deck"]
    curr_install = proj.get("installation_type", "rooftop").title()
    install_idx = 0
    for idx, it in enumerate(install_types):
        if curr_install.lower() in it.lower():
            install_idx = idx
            break
    install_type = c5.selectbox("Installation Architecture", install_types, index=install_idx)
    target_ac = c6.number_input("Target AC Export Capacity (kW)", min_value=1.0, max_value=50000.0, value=float(proj.get("target_ac_capacity_kw", 100.0)), step=5.0)
    grid_v = c7.selectbox("Grid Interconnection Voltage (V)", [400.0, 230.0, 415.0, 480.0, 500.0], index=0 if float(proj.get("grid_voltage_v", 400.0)) == 400.0 else 1)
    grid_phases = c8.selectbox("Grid Phase System", [3, 1], index=0 if int(proj.get("grid_phases", 3)) == 3 else 1)

    st.markdown("#### 🌡️ Site Ambient Temperature Extremes")
    c9, c10, c11, c12 = st.columns(4)
    t_min = c9.number_input("Min Design Ambient Temp (°C)", value=float(proj.get("min_design_temp_c", -30.0)), min_value=-50.0, max_value=35.0, step=1.0, help="Used for cold-day string open-circuit voltage Voc calculation. Default -30 °C.")
    t_max = c10.number_input("Max Design Ambient Temp (°C)", value=float(proj.get("max_design_temp_c", 60.0)), min_value=20.0, max_value=85.0, step=1.0, help="Used for hot-day minimum MPPT operating voltage Vmp calculation. Default 60 °C.")
    dc_ac_pref = c11.number_input("Preferred DC/AC Ratio", value=float(proj.get("dc_ac_ratio_preferred", 1.20)), min_value=0.90, max_value=1.60, step=0.05)
    max_panels = c12.number_input("Max Available Panels (Stock/Area Limit)", value=int(proj.get("panel_available_qty", 1000)), min_value=10, step=50)

    st.markdown("#### 📐 Installation Boundary Dimensions & Clearances")
    c13, c14, c15, c16 = st.columns(4)
    area_len = c13.number_input("Usable Area Length (m)", value=float(proj.get("area_length_m", 80.0)), min_value=5.0, step=5.0)
    area_wid = c14.number_input("Usable Area Width (m)", value=float(proj.get("area_width_m", 35.0)), min_value=5.0, step=5.0)
    edge_clear = c15.number_input("Roof Perimeter Clearance (m)", value=1.0, min_value=0.2, step=0.2)
    walkway_w = c16.number_input("Maintenance Walkway Width (m)", value=1.2, min_value=0.5, step=0.1)

    submitted = st.form_submit_button("💾 Save Project Details to Database", type="primary", use_container_width=True)
    if submitted:
        updated_proj = dict(proj)
        updated_proj.update({
            "name": p_name,
            "customer_name": p_cust,
            "site_name": p_site,
            "location": p_loc,
            "installation_type": install_type.lower(),
            "target_ac_capacity_kw": target_ac,
            "target_ac_kw": target_ac,
            "grid_voltage_v": grid_v,
            "grid_phases": grid_phases,
            "min_design_temp_c": t_min,
            "max_design_temp_c": t_max,
            "dc_ac_ratio_preferred": dc_ac_pref,
            "panel_available_qty": max_panels,
            "area_length_m": area_len,
            "area_width_m": area_wid,
            "spacing_config": SpacingConfig(0.02, 0.5, edge_clear, walkway_w, 2.0)
        })
        set_active_project(updated_proj)
        try:
            save_project(updated_proj)
            st.success("✅ Project parameters successfully updated and saved to SQLite database.")
            st.rerun()
        except Exception as e:
            st.error(f"Error saving to database: {e}")

st.markdown("---")
st.markdown("#### 📊 Project Specification Summary")
summary_data = [
    {"Parameter": "Project Name & Client", "Value": f"{proj.get('name', 'N/A')} ({proj.get('customer_name', 'N/A')})"},
    {"Parameter": "Target AC Capacity", "Value": f"{proj.get('target_ac_capacity_kw', 100.0)} kW AC"},
    {"Parameter": "Nominal Grid Voltage", "Value": f"{proj.get('grid_voltage_v', 400.0)} V, {proj.get('grid_phases', 3)}-Phase"},
    {"Parameter": "Site Temperature Window", "Value": f"{proj.get('min_design_temp_c', -30.0)} °C to {proj.get('max_design_temp_c', 60.0)} °C"},
    {"Parameter": "Target DC/AC Sizing Ratio", "Value": f"{proj.get('dc_ac_ratio_preferred', 1.20):.2f}"},
    {"Parameter": "Site Installation Boundary", "Value": f"{proj.get('area_length_m', 80.0)} m × {proj.get('area_width_m', 35.0)} m ({proj.get('area_length_m', 80.0)*proj.get('area_width_m', 35.0):,.0f} m²)"},
    {"Parameter": "Applicable Engineering Standards", "Value": "BS 7671:2008, IEC 60364-7-712, IEC 60269-6, BS 7430"}
]
st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
