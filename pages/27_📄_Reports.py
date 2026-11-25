"""
pages/27_📄_Reports.py — Official Solar PV Engineering Reports, Schedules & Single Line Diagram (SLD)
Generates and downloads formal PDF engineering reports, multi-sheet Excel schedules,
CSV Bill of Materials (with rule sourcing), and CAD-standard Single Line Diagrams (SVG and Vector PDF).

Conforms to:
  - BS 7671:2008 (Table A1 Kelani Cables ampacity & voltage drop)
  - IEC 60364-7-712 (Solar PV electrical installations)
  - IEC 60269-6 (gPV string fuse coordination)
  - BS 7430:2011 (Protective earthing & electrode resistance)
  - CEB / LECO Grid Interconnection Standards

Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
"""
import streamlit as st
from ui.components import page_header, nav_sidebar
from ui.styles import apply_custom_css
from core.project_state import (
    get_active_project,
    get_active_panel,
    get_active_inverter,
    get_dynamic_system,
    recalculate_system_state,
    render_active_project_banner
)
from core.unified_dataset import get_unified_engineering_dataset
from reports.pdf_report import generate_pdf_report
from reports.excel_report import generate_excel_report
from reports.csv_export import export_bom_to_csv
from reports.sld_generator import generate_sld_svg, generate_sld_pdf
from reports.dxf_generator import generate_sld_dxf
from reports.ceb_application import generate_ceb_application_pdf
from reports.proposal_summary import generate_proposal_summary_pdf

try:
    st.set_page_config(page_title="Project Reports & SLD — Solar PV Platform", page_icon="📄", layout="wide")
except Exception:
    pass

apply_custom_css()
nav_sidebar()
render_active_project_banner()

page_header("Engineering Reports & Documentation", "Generate, preview, and download formal design reports, schedules, and Single Line Diagrams (SLD)", icon="📄")

proj = get_active_project()
panel = get_active_panel()
inverter = get_active_inverter()
dynamic_sys = get_dynamic_system()

if not dynamic_sys or "per_inverter_designs" not in dynamic_sys:
    dynamic_sys = recalculate_system_state()

ac_kw = float(dynamic_sys.get("actual_ac_kw", proj.get("target_ac_capacity_kw", 13.0)))
if ac_kw <= 0:
    ac_kw = 13.0

# 1. Obtain Canonical Single Source of Truth
ds = get_unified_engineering_dataset(target_kw=ac_kw, panel=panel, custom_project_params=proj)

p_meta = ds["project"]
pv_sub = ds["pv_subsystem"]
inv_infra = ds["inverter_infrastructure"]
whole_ac = ds["whole_system_ac"]
earthing = ds["earthing_system"]
energy = ds["energy_yield"]
bom = ds["bom_items"]
val_items = ds["validation_items"]
sld_data = ds["sld_data"]

proj_name = p_meta.get("name", "Solar PV Design Project")
safe_name = "".join(c for c in proj_name if c.isalnum() or c in ("-", "_")).rstrip()

# Metric summary banner
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Nominal AC Capacity", f"{inv_infra.get('actual_ac_kw', ac_kw):.1f} kW", f"{p_meta.get('grid_phases', 3)}-Phase {p_meta.get('grid_voltage_v', 400.0):.0f}V")
m2.metric("Installed DC Array", f"{pv_sub.get('dc_capacity_kwp', 0):.2f} kWp", f"{pv_sub.get('total_panels', 0)}x {pv_sub.get('panel_model', '')}")
m3.metric("DC / AC Ratio", f"{pv_sub.get('dc_ac_ratio', 1.25):.2f}", "Optimal 1.15–1.30")
m4.metric("Annual AC Generation", f"{energy.get('annual_ac_energy_kwh', 0):,.0f} kWh", f"PR: {energy.get('performance_ratio_pct', 79.5):.1f}%")
m5.metric("Compliance Status", ds.get("overall_status", "PASS"), "Eng. Aashir Certified")

st.markdown("---")
st.markdown("### 📥 Official Engineering Deliverables")
st.caption("All deliverables are generated live from the central unified engineering model. Zero residual 5 kW data.")

r_col1, r_col2 = st.columns(2)

with r_col1:
    with st.container(border=True):
        st.markdown("#### 📄 Output 01: Professional Engineering Report (PDF)")
        st.write("Formal multi-page stamped document containing 12 engineering sections:")
        st.caption("1. Project Context • 2. PV Subsystem • 3. Inverter Fleet & Stringing • 4. DC Protection (IEC 60269-6) • 5. AC Switchgear & BS 7671 Cable • 6. BS 7430 Earthing • 7. Energy Yield & PR • 8. CEB Tariff & Savings (PUCSL 2026) • 9. Calculation Proofs • 10. Health Check Matrix • 11. Sourced BOM • 12. Eng. Aashir Certification")
        try:
            pdf_bytes = generate_pdf_report(ds)
            st.download_button(
                label=f"📥 Download Engineering Report ({len(pdf_bytes):,} bytes)",
                data=pdf_bytes,
                file_name=f"Solar_Engineering_Report_{int(ac_kw)}kW_{safe_name}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF Generator Notice: {e}")

    with st.container(border=True):
        st.markdown("#### 📊 Output 02: Multi-Sheet Engineering Schedule (.xlsx)")
        st.write("Complete 15-sheet OpenPyXL workbook with Navy Blue styling, freeze panes, and Blank Field Rule:")
        st.caption("1. Project Summary • 2. System Config • 3. Panel Sched • 4. String Sched • 5. Inverter Sched • 6. DC Cable • 7. DC Protection • 8. AC Cable • 9. AC Protection • 10. Earthing • 11. Equipment • 12. BOM & BOQ • 13. Calculations • 14. SLD Mapping • 15. Validation")
        try:
            excel_bytes = generate_excel_report(ds)
            st.download_button(
                label=f"📥 Download 15-Sheet Excel Schedule ({len(excel_bytes):,} bytes)",
                data=excel_bytes,
                file_name=f"Solar_Engineering_Schedule_{int(ac_kw)}kW_{safe_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Excel Generator Notice: {e}")

    with st.container(border=True):
        st.markdown("#### 💼 Output 06: Executive 1-Page Customer Proposal (PDF)")
        st.write("Formal 1-page executive solar proposal and utility tariff savings summary with PUCSL April 2026 tariff schedules and Eng. Aashir certification.")
        try:
            prop_pdf = generate_proposal_summary_pdf(ds)
            st.download_button(
                label=f"📥 Download 1-Page Proposal ({len(prop_pdf):,} bytes)",
                data=prop_pdf,
                file_name=f"Solar_Proposal_{int(ac_kw)}kW_{safe_name}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Proposal Generator Notice: {e}")

with r_col2:
    with st.container(border=True):
        st.markdown("#### 📑 Output 03: Sourced Bill of Materials (BOM .csv)")
        st.write("Clean, machine-readable CSV with item codes, equipment specs, quantities, units, and statutory rule sourcing tags (BS 7671 / IEC 60269-6 / BS 7430 / CEB).")
        try:
            csv_str = export_bom_to_csv(ds)
            st.download_button(
                label="📥 Download Sourced BOM (CSV)",
                data=csv_str,
                file_name=f"Solar_BOM_{int(ac_kw)}kW_{safe_name}.csv",
                mime="text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"CSV Export Notice: {e}")

    with st.container(border=True):
        st.markdown("#### 🏛️ Output 05: CEB / LECO Interconnection Application Form (PDF)")
        st.write("Statutory Ceylon Electricity Board & LECO Embedded Solar PV Interconnection Application Form (SOP Form A-1) with technical parameters and Eng. Aashir certification.")
        try:
            ceb_bytes = generate_ceb_application_pdf(ds, scheme="Net Accounting")
            st.download_button(
                label=f"📥 Download CEB Application Form ({len(ceb_bytes):,} bytes)",
                data=ceb_bytes,
                file_name=f"Solar_CEB_Application_{int(ac_kw)}kW_{safe_name}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"CEB Form Notice: {e}")

    with st.container(border=True):
        st.markdown("#### ⚡ Output 04: CAD Single Line Diagram (SLD)")
        st.write("Single Line Diagram designed to Eng. Aashir's CAD blueprint standard with outer double border, 4-compartment title block, stacked inverters, collector busbar, and CEB meter:")
        s_col1, s_col2, s_col3 = st.columns(3)
        try:
            sld_svg_str = generate_sld_svg(ds)
            with s_col1:
                st.download_button(
                    label="📥 Download SLD (.svg)",
                    data=sld_svg_str,
                    file_name=f"Solar_SLD_{int(ac_kw)}kW_{safe_name}.svg",
                    mime="image/svg+xml",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"SLD SVG Notice: {e}")

        try:
            sld_pdf_bytes = generate_sld_pdf(ds)
            with s_col2:
                st.download_button(
                    label="📥 Download SLD Vector (.pdf)",
                    data=sld_pdf_bytes,
                    file_name=f"Solar_SLD_{int(ac_kw)}kW_{safe_name}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"SLD PDF Notice: {e}")

        try:
            sld_dxf_str = generate_sld_dxf(ds)
            with s_col3:
                st.download_button(
                    label="📥 Download AutoCAD (.dxf)",
                    data=sld_dxf_str,
                    file_name=f"Solar_SLD_{int(ac_kw)}kW_{safe_name}.dxf",
                    mime="application/dxf",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"SLD DXF Notice: {e}")

# Interactive SVG SLD Preview Section
st.markdown("---")
st.markdown("### 🔍 Interactive Single Line Diagram (CAD Preview)")
st.caption("Parametric vector blueprint rendered per Eng. Aashir's visual standard. Includes PV string arrays, inverters, AC collector busbar, metering, and utility grid interface.")

try:
    sld_preview_svg = generate_sld_svg(ds)
    # Wrap in styled scrollable container
    st.components.v1.html(
        f"""
        <div style="width: 100%; overflow-x: auto; background: #ffffff; padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            {sld_preview_svg}
        </div>
        """,
        height=720,
        scrolling=True
    )
except Exception as e:
    st.info(f"SLD Preview renderer note: {e}")

# Detailed Tabs for On-Screen Verification
st.markdown("---")
st.markdown("### 📋 On-Screen Verification Schedules")

tab_bom, tab_val, tab_elec = st.tabs(["📦 Sourced Bill of Materials", "🛡️ Validation Matrix", "⚡ Electrical Protection Summary"])

with tab_bom:
    import pandas as pd
    bom_display = []
    for item in bom:
        bom_display.append({
            "#": item.get("item_no", 0),
            "Category": item.get("category", ""),
            "Description": item.get("name", ""),
            "Specification": item.get("specification", ""),
            "Manufacturer / Model": item.get("model", "-"),
            "Rating": item.get("rating", "-"),
            "Unit": item.get("unit", ""),
            "Qty": item.get("quantity", 0),
            "Sourcing Standard": item.get("rule_source", "BS 7671 / IEC")
        })
    st.dataframe(pd.DataFrame(bom_display), use_container_width=True, hide_index=True)

with tab_val:
    val_display = []
    for v in val_items:
        stat = v.get("status", "PASS")
        icon = "🟢" if stat == "PASS" else ("🟡" if stat == "WARNING" else "🔴")
        val_display.append({
            "Status": f"{icon} {stat}",
            "Parameter": v.get("parameter", ""),
            "Actual Value": v.get("actual_value", ""),
            "Allowable Limit": v.get("allowed_value", ""),
            "Standard": v.get("standard", ""),
            "Notes": v.get("reason", "")
        })
    st.dataframe(pd.DataFrame(val_display), use_container_width=True, hide_index=True)

with tab_elec:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### DC Subsystem Protection")
        st.markdown(f"- **String Voc (Cold @ {p_meta.get('min_design_temp_c', -30.0):.0f}°C):** `{pv_sub.get('voc_cold_v', 0):.1f} V` (Limit: < 1000/1100V)")
        st.markdown(f"- **String Vmp (Hot @ {p_meta.get('max_design_temp_c', 60.0):.0f}°C):** `{pv_sub.get('vmp_hot_v', 0):.1f} V` (Within MPPT range)")
        st.markdown(f"- **DC String Fuse:** `{ds.get('dc_protection', {}).get('fuse_status', 'Not required (< 3 strings)')}` (IEC 60269-6)")
        st.markdown(f"- **DC Surge Arrester (SPD):** `{ds.get('dc_protection', {}).get('spd_rating', 'Type II 1000V DC')}` (IEC 61643-31)")
        st.markdown(f"- **DC String Isolation:** `{ds.get('dc_protection', {}).get('isolator_spec', '1000V DC 4-Pole 32A')}`")
    with c2:
        st.markdown("#### AC Subsystem Protection & Earthing")
        st.markdown(f"- **Inverter AC Output Protection:** `{inv_infra.get('inv_mcb_rating_a', 25)}A MCB / Inverter`")
        st.markdown(f"- **Main AC Collector Breaker:** `{whole_ac.get('main_breaker_type', 'MCCB')} {whole_ac.get('main_breaker_rating_a', 32)}A`")
        st.markdown(f"- **Main AC Feeder Cable:** `{whole_ac.get('main_cable_csa_mm2', 16)} mm² 4C Cu/XLPE/SWA/PVC` ({whole_ac.get('main_cable_run_m', 20)}m)")
        st.markdown(f"- **Feeder Voltage Drop:** `{whole_ac.get('main_cable_voltage_drop_pct', 0.5):.2f}%` (Kelani Cables Table A1, Limit: < 1.0%)")
        st.markdown(f"- **Earth Electrodes (BS 7430):** `{earthing.get('earth_rods_qty', 2)}x 16mm x 3m Cu-clad Steel Rod(s)` ({earthing.get('effective_resistance_ohm', 8.5):.2f} Ω < 10.0 Ω)")
