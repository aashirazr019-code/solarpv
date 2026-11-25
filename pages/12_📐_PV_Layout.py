import streamlit as st
import pandas as pd
import math
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from ui.equipment_forms import panel_picker, inverter_picker, spacing_inputs
from core.models import Project, SpacingConfig
from core.physical_layout import physical_layout
from core.mppt_allocation import allocate_mppt

try:
    st.set_page_config(page_title="PV Layout Calculator — Eng. Aashir", page_icon="📐", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("PV Layout & String Arrangement Calculator", "Calculate physical panel fitting, string arrangements, and inverter-wise BoQ allocations", icon="📐")

c_p1, c_p2 = st.columns(2)
with c_p1:
    st.markdown("#### 🔋 Module & Inverter Selection")
    panel = panel_picker("layout_page_panel")
    inverter = inverter_picker("layout_page_inv")

with c_p2:
    st.markdown("#### 🏗️ Rooftop / Site Dimensions (m)")
    c_dim1, c_dim2 = st.columns(2)
    area_len = c_dim1.number_input("Available Area Length (m)", min_value=2.0, max_value=2000.0, value=50.0, step=5.0)
    area_wid = c_dim2.number_input("Available Area Width (m)", min_value=2.0, max_value=2000.0, value=30.0, step=5.0)

    st.markdown("#### 🔌 Stringing & Plant Sizing")
    c_str1, c_str2, c_str3 = st.columns(3)
    panels_per_str = c_str1.number_input("Panels per String", min_value=1, max_value=35, value=16, step=1)
    inverter_units = c_str2.number_input("Inverter Units", min_value=1, max_value=50, value=1, step=1)
    target_strings = c_str3.number_input("Planned Strings Count", min_value=1, max_value=200, value=12, step=1)

spacing_cfg = spacing_inputs("layout_page_spacing")

if st.button("📐 Generate Engineering PV Layout & Allocation Table", type="primary", use_container_width=True):
    try:
        total_panels_req = target_strings * panels_per_str
        panel_wp = panel.rated_power_wp if panel else 630.0
        total_dc_kwp = (total_panels_req * panel_wp) / 1000.0

        project = Project(
            id="layout-proj", name="Layout Design", location="", installation_type="rooftop",
            target_ac_capacity_kw=inverter.rated_ac_power_kw * inverter_units,
            min_design_temp_c=-30.0, max_design_temp_c=60.0,
            dc_ac_ratio_min=1.0, dc_ac_ratio_preferred=1.2, dc_ac_ratio_max=1.5,
            panel_id=panel.id, panel_available_qty=9999,
            area_length_m=area_len, area_width_m=area_wid, spacing_config=spacing_cfg
        )

        # 1. Physical layout geometry
        layout_res = physical_layout(panel, project, total_panels_req)
        p_fit = layout_res["portrait"]["total_panels"]
        l_fit = layout_res["landscape"]["total_panels"]
        rec_orient = layout_res["recommended_orientation"]
        max_fit = layout_res["total_fitting"]
        fits_site = max_fit >= total_panels_req

        st.markdown("---")
        st.subheader("📐 Physical Array Geometric Fitting")

        c_fit1, c_fit2, c_fit3 = st.columns(3)
        with c_fit1:
            st.metric("Portrait Orientation", f"{p_fit} panels", f"{layout_res['portrait']['rows']} rows × {layout_res['portrait']['cols']} cols")
        with c_fit2:
            st.metric("Landscape Orientation", f"{l_fit} panels", f"{layout_res['landscape']['rows']} rows × {layout_res['landscape']['cols']} cols")
        with c_fit3:
            st.metric("Recommended Orientation", rec_orient.capitalize(), f"Area Utilization: {layout_res['area_utilization_pct']}%")

        if fits_site:
            st.success(f"✅ Planned array of {total_panels_req} modules ({target_strings} strings × {panels_per_str} panels) fits comfortably within available roof space (max {max_fit} modules).")
        else:
            st.error(f"❌ Area Deficit: Planned array requires {total_panels_req} modules, but roof area only accommodates a maximum of {max_fit} modules.")

        st.markdown("---")
        st.subheader("📋 Inverter & MPPT-Wise Engineering Takeoff Table")
        st.caption("Detailed schedule of strings, modules, and DC kWp capacity allocated per inverter and MPPT tracker.")

        # 2. Inverter-wise allocation
        breakdown = [{"inverter": inverter, "quantity": inverter_units}]
        alloc_res = allocate_mppt(breakdown, target_strings)

        boq_layout_rows = []
        cumulative_panels = 0
        cumulative_kwp = 0.0

        for u_idx, unit_res in enumerate(alloc_res["per_inverter_unit"]):
            for m in unit_res["allocation"]:
                if m["strings_assigned"] > 0:
                    str_on_mppt = m["strings_assigned"]
                    panels_on_mppt = str_on_mppt * panels_per_str
                    kwp_on_mppt = (panels_on_mppt * panel_wp) / 1000.0
                    cumulative_panels += panels_on_mppt
                    cumulative_kwp += kwp_on_mppt

                    boq_layout_rows.append({
                        "Inverter Unit": f"INV #{u_idx + 1} ({inverter.model})",
                        "MPPT Tracker": f"MPPT #{m['mppt_index']}",
                        "Assigned Strings": str_on_mppt,
                        "Panels / String": panels_per_str,
                        "Total Modules": panels_on_mppt,
                        "DC Power (kWp)": round(kwp_on_mppt, 2),
                        "Cumulative Panels": cumulative_panels,
                        "Cumulative kWp": round(cumulative_kwp, 2),
                        "Hardware Limit": f"<= {m['max_inputs']} inputs ({'OK' if m['hardware_ok'] else 'EXCEEDED'})"
                    })

        df_layout = pd.DataFrame(boq_layout_rows)
        st.dataframe(df_layout, use_container_width=True, hide_index=True)

        # Download button for engineering schedule
        csv_data = df_layout.to_csv(index=False)
        st.download_button(
            label="💾 Download Engineering Layout Schedule (.csv)",
            data=csv_data,
            file_name=f"PV_Layout_Schedule_{inverter.model}.csv",
            mime="text/csv"
        )

        render_calculation_proof(
            "Array Physical Spacing & Dimensions Formula",
            [
                {"formula": r"\text{Row Pitch} = \text{Module Length/Width} + \text{Inter-Row Gap}"},
                {"label": "Effective Usable Length", "value": f"{area_len - 2 * spacing_cfg.edge_clearance_m:.2f} m (after {spacing_cfg.edge_clearance_m}m edge clearance)"},
                {"label": "Effective Usable Width", "value": f"{area_wid - 2 * spacing_cfg.edge_clearance_m:.2f} m"},
                {"label": "Total Required Modules", "value": f"{total_panels_req} modules ({target_strings} strings of {panels_per_str})"},
                {"label": "Total Connected DC Capacity", "value": f"{total_dc_kwp:.2f} kWp"}
            ]
        )

    except Exception as e:
        st.error(f"Error generating PV layout: {str(e)}")
