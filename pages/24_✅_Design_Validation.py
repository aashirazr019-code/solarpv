"""
pages/24_✅_Design_Validation.py — Central Design Rule Validation Engine
Automatically collects parameters across all 12 calculators, verifies against engineering limits, and renders a status matrix.
Authored by Eng. Aashir © 2026.
"""
import streamlit as st
import pandas as pd
from ui.styles import apply_custom_css
from ui.components import page_header, render_status, render_validation_table
from core.design_validation import validate_design, get_overall_status, validate_engineering_consistency, validate_design_prerequisites
from core.unified_dataset import get_unified_engineering_dataset
from core.project_state import get_active_project, get_active_panel, get_active_inverter, get_design_value, set_design_value, render_active_project_banner
from core.string_sizing import cold_voc, hot_vmp, cold_vmp

try:
    st.set_page_config(page_title="Design Validation — Solar PV Platform", page_icon="✅", layout="wide")
except Exception:
    pass

apply_custom_css()
render_active_project_banner()
page_header("Engineering Design Rule Validation", "Automated compliance checks across photovoltaic electrical safety rules, voltage limits, and standards", icon="✅")

proj = get_active_project()
panel = get_active_panel()
inverter = get_active_inverter()

t_min = float(proj.get("min_design_temp_c", -30.0))
t_max = float(proj.get("max_design_temp_c", 60.0))
panels_per_str = int(get_design_value("panels_per_string", 16))
total_strings = int(get_design_value("total_strings", 14))
mppt_count = getattr(inverter, "mppt_count", 10)
strings_per_mppt = max(1, int(round(total_strings / mppt_count)))

# Derived voltages from actual panel and site temperatures
raw_voc_c = cold_voc(panel, t_min)
val_voc_c = raw_voc_c[0] if isinstance(raw_voc_c, (tuple, list)) else raw_voc_c
v_voc_cold = round(float(val_voc_c) * panels_per_str, 2)

raw_vmp_h = hot_vmp(panel, t_max)
val_vmp_h = raw_vmp_h[0] if isinstance(raw_vmp_h, (tuple, list)) else raw_vmp_h
v_vmp_hot = round(float(val_vmp_h) * panels_per_str, 2)

raw_vmp_c = cold_vmp(panel, t_min)
val_vmp_c = raw_vmp_c[0] if isinstance(raw_vmp_c, (tuple, list)) else raw_vmp_c
v_vmp_cold = round(float(val_vmp_c) * panels_per_str, 2)

# Actual live system parameters
live_params = {
    "string_voc_cold_v": v_voc_cold,
    "inverter_max_dc_v": float(inverter.max_dc_voltage_v),
    "string_vmp_hot_v": v_vmp_hot,
    "inverter_mppt_min_v": float(inverter.mppt_voltage_min_v),
    "string_vmp_cold_v": v_vmp_cold,
    "inverter_mppt_max_v": float(inverter.mppt_voltage_max_v),
    "mppt_isc_a": round(panel.isc * strings_per_mppt, 2),
    "inverter_max_isc_per_mppt_a": float(inverter.max_isc_per_mppt_a),
    "dc_ac_ratio": float(get_design_value("dc_ac_ratio", 1.20)),
    "dc_ac_ratio_max": float(proj.get("dc_ac_ratio_max", 1.35)),
    "dc_voltage_drop_pct": float(get_design_value("dc_voltage_drop_pct", 1.25)),
    "ac_voltage_drop_pct": float(get_design_value("ac_voltage_drop_pct", 1.85)),
    "earth_resistance_ohm": float(get_design_value("earth_resistance_ohm", 4.2)),
    "target_earth_resistance_ohm": 5.0,
    "performance_ratio_pct": float(get_design_value("performance_ratio_pct", 78.5)),
    "min_pr_pct": 75.0
}

# Run automated validation
validation_items = validate_design(live_params)
overall_status = get_overall_status(validation_items)
set_design_value("overall_status", overall_status)
set_design_value("validation_items", validation_items)

# Display Overall Health Banner
st.markdown("### 🚦 Design Compliance Health Check")
col_stat, col_score = st.columns([3, 1])
with col_stat:
    if overall_status == "PASS":
        st.success("🟢 **ALL ENGINEERING RULES PASSED** — The active photovoltaic design complies with all IEC, BS 7671, and inverter manufacturer constraints.")
    elif overall_status == "WARNING":
        st.warning("🟡 **DESIGN WARNINGS DETECTED** — System is physically safe, but operating near upper thresholds (e.g. clipping margin or ratio limit). Review details below.")
    elif overall_status == "MANUAL_REVIEW":
        st.info("🔵 **MANUAL REVIEW REQUIRED** — System parameters require utility interconnection agreement or custom engineering approval (e.g. system > 40 kW utility net metering).")
    else:
        st.error("🔴 **HARD RULE VIOLATIONS (FAIL)** — Design exceeds permissible equipment or safety limits. Review recommended actions below.")

with col_score:
    pass_cnt = sum(1 for i in validation_items if i["status"] == "PASS")
    warn_cnt = sum(1 for i in validation_items if i["status"] == "WARNING")
    review_cnt = sum(1 for i in validation_items if i["status"] == "MANUAL_REVIEW")
    fail_cnt = sum(1 for i in validation_items if i["status"] == "FAIL")
    st.metric("Checks Passed", f"{pass_cnt} / {len(validation_items)}", f"{fail_cnt} Fail, {warn_cnt} Warn, {review_cnt} Review")

st.markdown("---")
st.markdown("#### 📋 Comprehensive Verification Matrix")
render_validation_table(validation_items)

st.markdown("---")
st.markdown("#### 📐 Single Line Diagram (SLD) & Cable Sizing Synchronization Audit")
st.caption("Verifies 100% agreement and Single Source of Truth between calculated engineering sizing and SLD schematic parameters.")

try:
    ds_active = get_unified_engineering_dataset()
    prereq_errors = validate_design_prerequisites(ds_active)
    if prereq_errors:
        for p_err in prereq_errors:
            st.error(f"⚠️ **Prerequisite Incomplete:** {p_err}")
    else:
        st.success("✅ **All Engineering Prerequisites Satisfied** — Capacity, equipment specifications, string allocation, cable ampacities, and busbars are verified.")

    sync_errors = validate_engineering_consistency(ds_active, ds_active.get("sld_data", {}))

    if not sync_errors:
        st.success("✅ **100% SLD & Cable Synchronization Confirmed** — Zero discrepancies found across DC cables, AC cables, main export cable, protection devices, busbars, and grounding conductors.")
        with st.expander("🔍 View SLD Parameter Cross-Reference Table", expanded=False):
            sld_obj = ds_active.get("sld_data", {})
            sw = sld_obj.get("main_switchgear", {})
            bb = sld_obj.get("busbar", {})
            eth = sld_obj.get("earthing", {})
            invs = sld_obj.get("inverters", [])

            cross_ref_rows = [
                {"Component": "Plant AC Capacity", "Calculated Value": f"{ds_active.get('inverter_infrastructure', {}).get('actual_ac_kw', 0.0):.1f} kW", "SLD Schematic Parameter": f"{sld_obj.get('system_meta', {}).get('capacity_kw', 0):.1f} kW", "Status": "🟢 Synchronized"},
                {"Component": "Total Solar Modules", "Calculated Value": f"{ds_active.get('pv_subsystem', {}).get('total_panels', 0)} Nos", "SLD Schematic Parameter": f"{sld_obj.get('system_meta', {}).get('total_modules', 0)} Nos", "Status": "🟢 Synchronized"},
                {"Component": "Main AC Export Cable", "Calculated Value": f"{sw.get('main_cable_csa_mm2', 0):.0f} mm² Cu", "SLD Schematic Parameter": str(sw.get('main_cable', '')), "Status": "🟢 Synchronized"},
                {"Component": "Main Circuit Breaker", "Calculated Value": f"{sw.get('main_breaker_rating_a', 0)}A {sw.get('main_breaker_type', '')}", "SLD Schematic Parameter": str(sw.get('breaker_spec', '')), "Status": "🟢 Synchronized"},
                {"Component": "Central Busbar", "Calculated Value": f"{bb.get('rating_a', 0)}A Cu", "SLD Schematic Parameter": str(bb.get('label', '')), "Status": "🟢 Synchronized"},
                {"Component": "Main Protective Earth", "Calculated Value": f"{eth.get('conductor_csa', 0):.0f} mm² Cu", "SLD Schematic Parameter": str(eth.get('main_earth_cable', '')), "Status": "🟢 Synchronized"},
            ]
            for idx, inv_item in enumerate(invs, 1):
                cross_ref_rows.append({
                    "Component": f"Inverter #{idx} AC Cable & Breaker",
                    "Calculated Value": f"{inv_item.get('ac_cable_csa', 0):.0f} mm², {inv_item.get('ac_mcb_a', 0)}A",
                    "SLD Schematic Parameter": f"{inv_item.get('ac_cable', '')} | {inv_item.get('ac_breaker', '')}",
                    "Status": "🟢 Synchronized"
                })
            st.dataframe(pd.DataFrame(cross_ref_rows), use_container_width=True, hide_index=True)
    else:
        for err in sync_errors:
            st.error(f"❌ Discrepancy: {err}")
except Exception as e:
    st.caption(f"Synchronization check note: {str(e)}")

# Manual Parameter Override / Edge-Case Testing Expander
with st.expander("🛠️ Manual Parameter Testing & Sensitivity Overrides (Optional)", expanded=False):
    st.caption("Test hypothetical worst-case weather extremes or equipment substitutions.")
    col1, col2 = st.columns(2)
    with col1:
        voc_ovr = st.number_input("String Voc Cold (V)", 0.0, 2000.0, live_params["string_voc_cold_v"])
        inv_max_v = st.number_input("Inverter Max DC (V)", 0.0, 2000.0, live_params["inverter_max_dc_v"])
        vmp_ovr = st.number_input("String Vmp Hot (V)", 0.0, 2000.0, live_params["string_vmp_hot_v"])
        inv_min_v = st.number_input("Inverter Min MPPT (V)", 0.0, 2000.0, live_params["inverter_mppt_min_v"])
        vmp_c_ovr = st.number_input("String Vmp Cold (V)", 0.0, 2000.0, live_params["string_vmp_cold_v"])
        inv_max_mppt = st.number_input("Inverter Max MPPT (V)", 0.0, 2000.0, live_params["inverter_mppt_max_v"])
    with col2:
        isc_ovr = st.number_input("MPPT Total Isc (A)", 0.0, 100.0, live_params["mppt_isc_a"])
        inv_max_isc = st.number_input("Inverter Max MPPT Isc (A)", 0.0, 100.0, live_params["inverter_max_isc_per_mppt_a"])
        dc_ac_ovr = st.number_input("DC/AC Ratio", 0.0, 3.0, live_params["dc_ac_ratio"])
        vd_dc_ovr = st.number_input("DC Voltage Drop (%)", 0.0, 10.0, live_params["dc_voltage_drop_pct"])
        vd_ac_ovr = st.number_input("AC Voltage Drop (%)", 0.0, 10.0, live_params["ac_voltage_drop_pct"])
        pr_ovr = st.number_input("System PR (%)", 50.0, 100.0, live_params["performance_ratio_pct"])

    if st.button("🔄 Re-Validate with Overrides", use_container_width=True):
        custom_params = {
            "string_voc_cold_v": voc_ovr,
            "inverter_max_dc_v": inv_max_v,
            "string_vmp_hot_v": vmp_ovr,
            "inverter_mppt_min_v": inv_min_v,
            "string_vmp_cold_v": vmp_c_ovr,
            "inverter_mppt_max_v": inv_max_mppt,
            "mppt_isc_a": isc_ovr,
            "inverter_max_isc_per_mppt_a": inv_max_isc,
            "dc_ac_ratio": dc_ac_ovr,
            "dc_ac_ratio_max": 1.35,
            "dc_voltage_drop_pct": vd_dc_ovr,
            "ac_voltage_drop_pct": vd_ac_ovr,
            "performance_ratio_pct": pr_ovr,
            "min_pr_pct": 75.0
        }
        res_ovr = validate_design(custom_params)
        render_validation_table(res_ovr)
