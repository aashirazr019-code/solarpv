"""
pages/0_🚀_Design_Studio.py — Guided 8-Step Solar BoQ & Design Studio Pipeline
Authored by Eng. Aashir (c) 2026.
"""
import streamlit as st
import pandas as pd
import math
from ui.styles import apply_custom_css
from ui.components import render_status, render_calculation_proof, render_result_card, render_validation_table
from data.database import save_project
from data.library_data import PANEL_FAMILIES, INVERTER_FAMILIES, build_panel, build_inverter
from core.models import Panel, Inverter, Project, SpacingConfig
from core.string_sizing import panels_per_string_range, voltage_check, cold_voc, hot_vmp, cold_vmp
from core.current_check import current_check
from core.dc_ac_ratio import dc_ac_ratio
from core.mppt_allocation import allocate_mppt_for_inverter
from core.panel_quantity import calculate_panel_quantity, calculate_string_and_panel_balance
from core.bom_generator import generate_bom
from core.project_state import render_active_project_banner, set_active_project, update_design_state, get_active_project
from reports.pdf_report import generate_pdf_report
from reports.excel_report import generate_excel_report
from reports.csv_export import export_bom_to_csv
from reports.sld_generator import generate_sld_svg

try:
    st.set_page_config(page_title="Design Studio — Solar PV Platform", page_icon="🚀", layout="wide")
except Exception:
    pass

apply_custom_css()
render_active_project_banner()
st.markdown("## 🚀 Guided 8-Step Solar BoQ & Design Studio")
st.caption("Step through the unified engineering workflow from initial site criteria to one-click formal report generation.")
st.markdown("### ⚡ Guided Photovoltaic System Design & BoQ Generator")
st.caption("Step through the unified engineering workflow from initial site criteria to one-click formal report generation.")

proj = get_active_project()

# STEP 1: Project Information & Design Criteria
with st.expander("📍 Step 1: Project Information & Site Design Criteria", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    proj_name = c1.text_input("Project Name", value=proj.get("name", "100 kW Commercial Solar PV Plant"), key="studio_proj_name")
    client_name = c2.text_input("Client / Customer", value=proj.get("customer_name", "Commercial Client"), key="studio_client")
    site_loc = c3.text_input("Site Location", value=proj.get("location", "Colombo, Sri Lanka"), key="studio_loc")
    install_type = c4.selectbox("Installation Type", ["Rooftop Commercial", "Rooftop Residential", "Ground Mount", "Carport Canopy"], key="studio_install_type")

    c5, c6, c7, c8 = st.columns(4)
    target_ac_kw = c5.number_input("Target AC Capacity (kW)", min_value=1.0, max_value=50000.0, value=float(proj.get("target_ac_capacity_kw", 100.0)), step=1.0, key="studio_target_ac")
    default_grid_idx = 0 if float(proj.get("grid_voltage_v", 400.0)) == 230.0 else 1
    grid_v = c6.selectbox("AC Grid Voltage", [230.0, 400.0, 415.0, 480.0, 500.0], index=default_grid_idx, key="studio_grid_v")
    t_min = c7.number_input("Min Design Ambient Temp (°C)", value=float(proj.get("min_design_temp_c", -30.0)), min_value=-50.0, max_value=35.0, step=1.0, help="Record minimum ambient temperature at site. Used for cold Voc calculation. Default -30 °C.", key="studio_tmin")
    t_max = c8.number_input("Max Design Ambient Temp (°C)", value=float(proj.get("max_design_temp_c", 60.0)), min_value=20.0, max_value=85.0, step=1.0, help="Record maximum ambient temperature at site. Used for hot Vmp calculation. Default 60 °C.", key="studio_tmax")

    c9, c10, c11, c12 = st.columns(4)
    dc_ac_min = c9.number_input("DC/AC Ratio Min", value=float(proj.get("dc_ac_ratio_min", 1.05)), min_value=0.80, max_value=1.50, step=0.05, key="studio_dcac_min")
    dc_ac_target = c10.number_input("DC/AC Ratio Target", value=float(proj.get("dc_ac_ratio_preferred", 1.30)), min_value=0.90, max_value=1.60, step=0.05, key="studio_dcac_target")
    dc_ac_max = c11.number_input("DC/AC Ratio Max", value=float(proj.get("dc_ac_ratio_max", 1.45)), min_value=1.00, max_value=1.80, step=0.05, key="studio_dcac_max")
    avail_panels_limit = c12.number_input("Max Available Panels (Stock/Space)", value=int(proj.get("panel_available_qty", 500)), min_value=1, step=50, key="studio_max_panels")

# STEP 2: Solar PV Module Configuration
with st.expander("🔋 Step 2: Solar PV Module Selection & Parameters", expanded=True):
    p_mode = st.radio("Module Source", ["Library (Tier-1: Yingli, Jinko, LONGi, JA)", "Custom / Datasheet Entry"], horizontal=True, key="studio_p_mode")
    
    if p_mode.startswith("Library"):
        c_pfam, c_pvar = st.columns(2)
        fam_names = [f"{f.get('manufacturer', 'Yingli')} — {f['series']}" for f in PANEL_FAMILIES]
        fam_idx = c_pfam.selectbox("Module Family", range(len(fam_names)), index=3 if len(fam_names) > 3 else 0, format_func=lambda i: fam_names[i], key="studio_pfam_idx")
        p_family = PANEL_FAMILIES[fam_idx]
        var_wp_opts = [v["wp"] for v in p_family["variants"]]
        p_wp = c_pvar.selectbox("Rated Wattage (Wp)", var_wp_opts, index=len(var_wp_opts)-1, key="studio_p_wp")
        p_variant = next(v for v in p_family["variants"] if v["wp"] == p_wp)
        panel = build_panel(p_family, p_variant)
    else:
        c1, c2, c3, c4 = st.columns(4)
        p_mfr = c1.text_input("Manufacturer", "Yingli Solar", key="studio_pmfr")
        p_mod = c2.text_input("Model", "PANDA 3.0 Pro 2 CF66-630W", key="studio_pmod")
        p_wp_val = c3.number_input("Rated Power (Wp)", value=630.0, step=5.0, key="studio_pwp_c")
        p_voc = c4.number_input("Voc at STC (V)", value=49.44, step=0.1, key="studio_pvoc_c")

        c5, c6, c7, c8 = st.columns(4)
        p_vmp = c5.number_input("Vmp at STC (V)", value=41.47, step=0.1, key="studio_pvmp_c")
        p_isc = c6.number_input("Isc at STC (A)", value=16.18, step=0.1, key="studio_pisc_c")
        p_imp = c7.number_input("Imp at STC (A)", value=15.19, step=0.1, key="studio_pimp_c")
        p_tcvoc = c8.number_input("Temp Coeff Voc (%/°C)", value=-0.24, format="%.3f", key="studio_ptcvoc_c")

        c9, c10, c11, c12 = st.columns(4)
        p_tcpmax = c9.number_input("Temp Coeff Pmax (%/°C)", value=-0.29, format="%.3f", key="studio_ptcpmax_c")
        p_len = c10.number_input("Length (m)", value=2.382, format="%.3f", key="studio_plen_c")
        p_wid = c11.number_input("Width (m)", value=1.134, format="%.3f", key="studio_pwid_c")
        p_maxsys = c12.number_input("Max System Voltage (V)", value=1500.0, step=100.0, key="studio_pmaxsys_c")

        panel = Panel(
            id="custom-panel-studio", manufacturer=p_mfr, model=p_mod,
            rated_power_wp=p_wp_val, voc=p_voc, vmp=p_vmp, isc=p_isc, imp=p_imp,
            max_system_voltage=p_maxsys, max_series_fuse=30.0,
            temp_coeff_voc=p_tcvoc, temp_coeff_vmp=-0.26, temp_coeff_isc=0.042, temp_coeff_pmax=p_tcpmax,
            length_m=p_len, width_m=p_wid, thickness_mm=30.0, weight_kg=33.0,
            cell_technology="N-type TOPCon Bifacial", cell_count=132, source="manual"
        )

    # Module Specs Quick Summary Card
    m_c1, m_c2, m_c3, m_c4, m_c5 = st.columns(5)
    m_c1.metric("Rated Power", f"{panel.rated_power_wp} Wp")
    m_c2.metric("Voc / Vmp", f"{panel.voc}V / {panel.vmp}V")
    m_c3.metric("Isc / Imp", f"{panel.isc}A / {panel.imp}A")
    m_c4.metric("Temp Coeff Voc", f"{panel.temp_coeff_voc} %/°C")
    m_c5.metric("Dimensions", f"{panel.length_m}m × {panel.width_m}m")

# STEP 3: Inverter Selection & Capacity Sizing
with st.expander("⚡ Step 3: Inverter Selection & Plant Architecture", expanded=True):
    i_mode = st.radio("Inverter Source", ["Library (Sunways, Huawei, Sungrow)", "Custom / Datasheet Entry"], horizontal=True, key="studio_i_mode")

    if i_mode.startswith("Library"):
        c_ifam, c_ivar = st.columns(2)
        i_fam_names = [f"{f.get('manufacturer', 'Sunways')} — {f['series']}" for f in INVERTER_FAMILIES]
        default_fam_idx = 4 if target_ac_kw >= 80 else (3 if target_ac_kw >= 15 else 2)
        i_fam_idx = c_ifam.selectbox("Inverter Family", range(len(i_fam_names)), index=min(default_fam_idx, len(i_fam_names)-1), format_func=lambda i: i_fam_names[i], key="studio_ifam_idx")
        i_family = INVERTER_FAMILIES[i_fam_idx]
        i_mod_names = [v["model"] for v in i_family["variants"]]
        default_var_idx = 4 if i_family.get("series") == "sunways-sts-3-6ktl-p" and len(i_mod_names) > 4 else 0
        i_var_idx = c_ivar.selectbox("Inverter Model", range(len(i_mod_names)), index=default_var_idx, format_func=lambda i: i_mod_names[i], key="studio_ivar_idx")
        inverter = build_inverter(i_family, i_family["variants"][i_var_idx])
    else:
        c1, c2, c3, c4 = st.columns(4)
        i_mfr = c1.text_input("Manufacturer", "Sunways", key="studio_imfr")
        i_mod = c2.text_input("Model", "STS-5KTL-P", key="studio_imod")
        i_kw = c3.number_input("Rated AC Power (kW)", value=float(min(target_ac_kw, 5.0)), step=1.0, key="studio_ikw_c")
        i_maxdc = c4.number_input("Max DC Voltage (V)", value=600.0 if grid_v <= 240.0 else 1100.0, step=50.0, key="studio_imaxdc_c")

        c5, c6, c7, c8 = st.columns(4)
        i_mpptmin = c5.number_input("MPPT Min Voltage (V)", value=100.0 if grid_v <= 240.0 else 160.0, step=10.0, key="studio_impptmin_c")
        i_mpptmax = c6.number_input("MPPT Max Voltage (V)", value=550.0 if grid_v <= 240.0 else 1000.0, step=10.0, key="studio_impptmax_c")
        i_mppt_cnt = c7.number_input("MPPT Trackers Count", value=2, min_value=1, step=1, key="studio_imppt_cnt_c")
        i_inputs_per_mppt = c8.number_input("String Inputs per MPPT", value=1, min_value=1, step=1, key="studio_inputs_per_mppt_c")

        c9, c10, c11, c12 = st.columns(4)
        i_maxcur = c9.number_input("Max Operating Current/MPPT (A)", value=15.0 if grid_v <= 240.0 else 26.0, step=1.0, key="studio_imaxcur_c")
        i_maxisc = c10.number_input("Max Isc/MPPT (A)", value=20.0 if grid_v <= 240.0 else 40.0, step=1.0, key="studio_imaxisc_c")
        i_eff = c11.number_input("Max Efficiency (%)", value=98.1, step=0.1, key="studio_ieff_c")
        i_ac_v = c12.number_input("AC Voltage (V)", value=grid_v, key="studio_iacv_c")

        inverter = Inverter(
            id="custom-inverter-studio", manufacturer=i_mfr, model=i_mod,
            rated_ac_power_kw=i_kw, max_dc_input_power_kw=i_kw * 1.30,
            max_dc_voltage_v=i_maxdc, mppt_voltage_min_v=i_mpptmin, mppt_voltage_max_v=i_mpptmax,
            mppt_count=int(i_mppt_cnt), string_inputs_per_mppt=int(i_inputs_per_mppt),
            max_input_current_per_mppt_a=i_maxcur, max_isc_per_mppt_a=i_maxisc,
            max_total_dc_current_a=i_maxcur * int(i_mppt_cnt), ac_voltage=i_ac_v,
            rated_ac_current_a=round(i_kw * 1000 / (1.732 * i_ac_v), 1),
            max_ac_current_a=round(i_kw * 1000 / (1.732 * i_ac_v) * 1.1, 1),
            efficiency_pct=i_eff, source="manual"
        )

    # Inverter Quantity Calculation
    inv_units = max(1, int(math.ceil(target_ac_kw / inverter.rated_ac_power_kw))) if inverter.rated_ac_power_kw > 0 else 1
    actual_plant_ac_kw = inv_units * inverter.rated_ac_power_kw

    inv_c1, inv_c2, inv_c3, inv_c4, inv_c5 = st.columns(5)
    inv_c1.metric("Unit Inverter Rating", f"{inverter.rated_ac_power_kw} kW")
    inv_c2.metric("Inverter Units Required", f"{inv_units} units")
    inv_c3.metric("Total Plant AC Capacity", f"{actual_plant_ac_kw:.1f} kW")
    inv_c4.metric("MPPT Voltage Range", f"{inverter.mppt_voltage_min_v} – {inverter.mppt_voltage_max_v} V")
    inv_c5.metric("MPPT Trackers / Inputs", f"{inverter.mppt_count} MPPTs ({inverter.string_inputs_per_mppt} str/ea)")

# Build Project Object for Core Engines
current_proj = Project(
    id="studio-active-project",
    name=proj_name,
    location=site_loc,
    installation_type=install_type,
    target_ac_capacity_kw=actual_plant_ac_kw,
    min_design_temp_c=t_min,
    max_design_temp_c=t_max,
    dc_ac_ratio_min=dc_ac_min,
    dc_ac_ratio_preferred=dc_ac_target,
    dc_ac_ratio_max=dc_ac_max,
    panel_id=panel.id,
    panel_available_qty=avail_panels_limit,
    area_length_m=100.0,
    area_width_m=50.0,
    spacing_config=SpacingConfig(),
    customer_name=client_name
)

# STEP 4: String Sizing & MPPT Voltage Window
with st.expander("🔌 Step 4: String Sizing & MPPT Voltage Window Optimization", expanded=True):
    str_range = panels_per_string_range(panel, inverter, current_proj)
    
    col_rng_info, col_sel = st.columns([2, 1])
    with col_rng_info:
        st.markdown(
            f"**Allowable String Configuration Range:** "
            f"<span style='font-size: 18px; color: #1e3a8a; font-weight: bold;'>"
            f"{str_range['min_panels_per_string']} to {str_range['max_panels_per_string']} panels per string"
            f"</span>",
            unsafe_allow_html=True
        )
        st.caption(
            f"Based on Cold Voc ({str_range['voc_cold_v']} V/panel @ {t_min}°C) and "
            f"Hot Vmp ({str_range['vmp_hot_v']} V/panel @ {t_max}°C) vs Inverter Limits."
        )

    with col_sel:
        default_panels_per_str = min(str_range["max_panels_per_string"], max(str_range["min_panels_per_string"], 16))
        panels_per_str = st.number_input(
            "Selected Panels per String",
            min_value=1,
            max_value=max(35, str_range["max_panels_per_string"] + 2),
            value=default_panels_per_str,
            step=1,
            key="studio_sel_panels_per_str"
        )

    # Voltage Check Evaluation
    v_check = voltage_check(panel, inverter, current_proj, panels_per_str)
    v_c1, v_c2, v_c3 = st.columns(3)
    with v_c1:
        cold_status = v_check["cold"]["status"]
        render_status(cold_status, f"Cold String Voc: {v_check['cold']['string_voc_cold_v']} V (Max: {inverter.max_dc_voltage_v} V)")
    with v_c2:
        hot_status = v_check["hot"]["status"]
        render_status(hot_status, f"Hot String Vmp: {v_check['hot']['string_vmp_hot_v']} V (Min: {inverter.mppt_voltage_min_v} V)")
    with v_c3:
        cold_vmp_status = v_check.get("cold_vmp", {}).get("status", "PASS")
        cold_vmp_val = v_check.get("cold_vmp", {}).get("string_vmp_cold_v", round(panels_per_str * panel.vmp, 1))
        render_status(cold_vmp_status, f"Cold String Vmp: {cold_vmp_val} V (Max MPPT: {inverter.mppt_voltage_max_v} V)")

    render_calculation_proof(
        "String Voltage Sizing Formulas (Cold Voc & Hot Vmp)",
        [
            {"formula": r"V_{oc,cold} = V_{oc,STC} \times [1 + \frac{\gamma_{Voc}}{100} \times (T_{min} - 25)]"},
            {"label": "Cold Voc per Module", "value": f"{str_range['voc_cold_v']} V"},
            {"formula": r"V_{mp,hot} = V_{mp,STC} \times [1 + \frac{\gamma_{Vmp}}{100} \times (T_{max} - 25)]"},
            {"label": "Hot Vmp per Module", "value": f"{str_range['vmp_hot_v']} V"},
            {"formula": r"N_{max} = \lfloor \frac{V_{max,inv}}{V_{oc,cold}} \rfloor, \quad N_{min} = \lceil \frac{V_{mppt,min}}{V_{mp,hot}} \rceil"},
            {"label": f"Evaluated String ({panels_per_str} panels)", "value": f"Voc Cold = {v_check['cold']['string_voc_cold_v']} V, Vmp Hot = {v_check['hot']['string_vmp_hot_v']} V"}
        ]
    )

# STEP 5: Module & String Quantity Balancing
with st.expander("🔢 Step 5: Module & String Quantity Balancing (Divisibility Engine)", expanded=True):
    target_dc_kwp = actual_plant_ac_kw * dc_ac_target
    raw_qty_res = calculate_panel_quantity(target_dc_kwp, panel.rated_power_wp, avail_panels_limit)
    raw_panel_count = raw_qty_res["panel_count"]

    bal_res = calculate_string_and_panel_balance(raw_panel_count, panels_per_str)

    if bal_res["is_divisible"]:
        st.success(f"✅ Perfectly Divisible: {raw_panel_count} modules form exactly {bal_res['strings_count']} strings of {panels_per_str} panels.")
        chosen_panels = raw_panel_count
        chosen_strings = bal_res["strings_count"]
    else:
        st.warning(f"⚠️ Non-Divisible Module Requirement: {raw_panel_count} modules cannot be divided into uniform strings of {panels_per_str} modules.")
        st.markdown(f"*{bal_res['warning']}*")

        bal_choice = st.radio(
            "Select Engineering Resolution for String Balancing:",
            [
                f"Option A (Round Down): {bal_res['round_down']['panels']} modules ({bal_res['round_down']['strings']} strings of {panels_per_str})",
                f"Option B (Round Up): {bal_res['round_up']['panels']} modules ({bal_res['round_up']['strings']} strings of {panels_per_str})",
                f"Option C (Custom Input): Exact specified strings"
            ],
            index=0 if bal_res["remainder_panels"] < (panels_per_str / 2) else 1,
            key="studio_bal_choice"
        )

        if "Option A" in bal_choice:
            chosen_panels = bal_res["round_down"]["panels"]
            chosen_strings = bal_res["round_down"]["strings"]
        elif "Option B" in bal_choice:
            chosen_panels = bal_res["round_up"]["panels"]
            chosen_strings = bal_res["round_up"]["strings"]
        else:
            chosen_strings = st.number_input("Custom Number of Strings", min_value=1, value=bal_res["strings_count"], step=1, key="studio_cust_str")
            chosen_panels = chosen_strings * panels_per_str

    actual_dc_kwp = (chosen_panels * panel.rated_power_wp) / 1000.0
    actual_dc_ac = actual_dc_kwp / actual_plant_ac_kw if actual_plant_ac_kw > 0 else 0.0

    b_c1, b_c2, b_c3, b_c4 = st.columns(4)
    b_c1.metric("Final Module Count", f"{chosen_panels} panels")
    b_c2.metric("Total Strings", f"{chosen_strings} strings")
    b_c3.metric("Plant DC Capacity", f"{actual_dc_kwp:.2f} kWp")
    dcac_delta = round(actual_dc_ac - dc_ac_target, 3)
    b_c4.metric("Actual DC/AC Sizing Ratio", f"{actual_dc_ac:.2f}", delta=f"{dcac_delta:+.2f}")

# STEP 6: MPPT Allocation & Dual Current Check
with st.expander("🧩 Step 6: MPPT Tracker Allocation & Dual Current Safety", expanded=True):
    strings_per_inverter = chosen_strings // inv_units
    remainder_strings = chosen_strings % inv_units
    
    mppt_alloc = allocate_mppt_for_inverter(inverter, strings_per_inverter + (1 if remainder_strings > 0 else 0), unit_number=1)
    max_str_per_mppt = max(a["strings_assigned"] for a in mppt_alloc["allocation"]) if mppt_alloc["allocation"] else 1

    cur_eval = current_check(panel, inverter, max_str_per_mppt)

    c_cur1, c_cur2 = st.columns(2)
    with c_cur1:
        render_status(cur_eval["status"], f"Max Strings per MPPT Tracker: {max_str_per_mppt} strings")
        st.markdown(
            f"- **Operating Current (Imp):** {cur_eval['operating_current_a']} A "
            f"(Inverter Rated Imp: {inverter.max_input_current_per_mppt_a} A)\n"
            f"- **Short-Circuit Current (Isc):** {cur_eval['isc_current_a']} A "
            f"(Inverter Safety Limit Isc: {inverter.max_isc_per_mppt_a} A)\n"
            f"- **Tracker Balance:** {'Balanced across trackers' if mppt_alloc['balanced'] else 'Uneven distribution across trackers'}"
        )
        if cur_eval.get("power_clipping_warning"):
            st.info("ℹ️ Note: Operating current Imp slightly exceeds inverter nominal tracking rating; inverter will safely clip peak power without tripping safety circuits.")

    with c_cur2:
        render_status("PASS" if not mppt_alloc["exceeded_hardware_limit"] else "FAIL", 
                      f"Hardware String Inputs Limit: {inverter.string_inputs_per_mppt} inputs/MPPT")
        if mppt_alloc["exceeded_hardware_limit"]:
            st.error("❌ Physical string input channels exceeded on inverter! Combiner box or lower string count required.")

    # Tracker Table
    mppt_rows = []
    for m in mppt_alloc["allocation"]:
        mppt_rows.append({
            "MPPT Tracker": f"MPPT {m['mppt_index']}",
            "Assigned Strings": m["strings_assigned"],
            "Max Allowed Inputs": m["max_inputs"],
            "Status": "🟢 OK" if m["hardware_ok"] else "🔴 Exceeded"
        })
    st.dataframe(pd.DataFrame(mppt_rows), use_container_width=True, hide_index=True)

# STEP 7: Engineering Health Check & Validation Matrix
with st.expander("🛡️ Step 7: Engineering Health Check & Compliance Matrix", expanded=True):
    validation_items = [
        {
            "parameter": "String Cold Voc",
            "actual_value": f"{v_check['cold']['string_voc_cold_v']} V",
            "allowed_value": f"<= {inverter.max_dc_voltage_v} V",
            "deviation": f"{round(v_check['cold']['string_voc_cold_v'] - inverter.max_dc_voltage_v, 1)} V",
            "status": v_check["cold"]["status"],
            "reason": "String Voc at minimum site temperature must not exceed inverter maximum DC voltage rating.",
            "recommended_action": "Reduce panels per string if FAIL."
        },
        {
            "parameter": "String Hot Vmp",
            "actual_value": f"{v_check['hot']['string_vmp_hot_v']} V",
            "allowed_value": f">= {inverter.mppt_voltage_min_v} V",
            "deviation": f"{round(v_check['hot']['string_vmp_hot_v'] - inverter.mppt_voltage_min_v, 1)} V",
            "status": v_check["hot"]["status"],
            "reason": "String Vmp at maximum site temperature must stay above MPPT lower tracking voltage floor.",
            "recommended_action": "Increase panels per string if FAIL."
        },
        {
            "parameter": "String Cold Vmp",
            "actual_value": f"{cold_vmp_val} V",
            "allowed_value": f"<= {inverter.mppt_voltage_max_v} V",
            "deviation": f"{round(cold_vmp_val - inverter.mppt_voltage_max_v, 1)} V",
            "status": cold_vmp_status,
            "reason": "String Vmp at cold condition must remain within inverter MPPT upper tracking boundary.",
            "recommended_action": "Reduce panels per string if FAIL."
        },
        {
            "parameter": "MPPT Short-Circuit Current (Isc)",
            "actual_value": f"{cur_eval['isc_current_a']} A",
            "allowed_value": f"<= {inverter.max_isc_per_mppt_a} A",
            "deviation": f"{round(cur_eval['isc_current_a'] - inverter.max_isc_per_mppt_a, 1)} A",
            "status": cur_eval["status"] if cur_eval["status"] == "FAIL" else "PASS",
            "reason": "Total string short-circuit current must not exceed inverter hard hardware limit.",
            "recommended_action": "Reduce strings paralleled per MPPT if FAIL."
        },
        {
            "parameter": "Plant DC/AC Ratio",
            "actual_value": f"{actual_dc_ac:.2f}",
            "allowed_value": f"{dc_ac_min} – {dc_ac_max}",
            "deviation": f"{round(actual_dc_ac - dc_ac_target, 2)}",
            "status": "PASS" if (dc_ac_min <= actual_dc_ac <= dc_ac_max) else "WARNING",
            "reason": "Plant sizing ratio should be optimized to prevent excessive clipping or inverter under-utilization.",
            "recommended_action": "Adjust target capacity or string count if outside preferred range."
        },
        {
            "parameter": "MPPT String Input Channels",
            "actual_value": f"{max_str_per_mppt} strings",
            "allowed_value": f"<= {inverter.string_inputs_per_mppt} per MPPT",
            "deviation": f"{max_str_per_mppt - inverter.string_inputs_per_mppt}",
            "status": "PASS" if not mppt_alloc["exceeded_hardware_limit"] else "FAIL",
            "reason": "Direct DC connector inputs physically provided on the inverter terminal board.",
            "recommended_action": "Install external DC combiner box if strings exceed direct inverter terminals."
        }
    ]

    render_validation_table(validation_items)

# STEP 8: Bill of Materials & Export Studio
with st.expander("📦 Step 8: Bill of Materials (BOM) & One-Click Export Studio", expanded=True):
    st.subheader("📋 Engineering Bill of Materials (Deterministic Takeoff)")
    
    c_cable1, c_cable2 = st.columns(2)
    dc_cable_run = c_cable1.number_input("Est. DC Cable Run per String (m)", value=25.0, step=5.0, key="studio_dc_run")
    ac_cable_run = c_cable2.number_input("Est. AC Cable Run per Inverter (m)", value=15.0, step=5.0, key="studio_ac_run")

    breakdown = [{"inverter": inverter, "quantity": inv_units}]
    design_metrics = {
        "panel_qty": chosen_panels,
        "strings_total": chosen_strings,
        "dc_capacity_kwp": actual_dc_kwp,
        "ac_capacity_kw": actual_plant_ac_kw,
        "dc_ac_ratio": actual_dc_ac
    }

    # Generate BOM
    try:
        bom_items = generate_bom(
            panel=panel,
            inverter_breakdown=breakdown,
            design_result=design_metrics,
            dc_cable_csa=6.0,
            ac_cable_csa=150.0 if actual_plant_ac_kw >= 80 else 35.0,
            dc_cable_length_per_string_m=dc_cable_run,
            ac_cable_length_per_inverter_m=ac_cable_run,
            mcb_rating=63 if actual_plant_ac_kw <= 40 else None,
            mccb_rating=round(actual_plant_ac_kw * 1.8),
            busbar_rating=round(actual_plant_ac_kw * 2.2),
            earth_rods=max(2, int(actual_plant_ac_kw / 25)),
            earth_conductor_csa=70.0 if actual_plant_ac_kw >= 100 else 35.0,
            dc_isolator_qty=chosen_strings
        )

        bom_table_rows = []
        for item in bom_items:
            bom_table_rows.append({
                "Category": item.category,
                "Item Name": item.item_name,
                "Manufacturer": item.manufacturer or "-",
                "Model / Spec": item.model or item.specification or "-",
                "Description": item.description,
                "Qty": item.quantity,
                "Unit": item.unit,
                "Rule Source": getattr(item, "rule_source", "ENGINEERING_RULE"),
                "Source": item.source,
                "Notes": item.notes or ""
            })
        st.dataframe(pd.DataFrame(bom_table_rows), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error generating BOM: {str(e)}")
        bom_items = []

    st.markdown("---")
    st.subheader("📑 One-Click Formal Deliverables & Exports")
    st.caption("All generated documentation includes official Eng. Aashir engineer stamp, watermarks, and full standards citations.")

    # Summary dictionaries for report generators
    project_meta_dict = {
        "Project Name": proj_name,
        "Customer": client_name,
        "Site Location": site_loc,
        "Design Standard": "BS 7671:2008 / IEC 60364-7-712 / IEC 60269-6 / BS 7430",
        "Target AC Capacity": f"{actual_plant_ac_kw:.1f} kW",
        "Installation Type": install_type,
        "DC/AC Sizing Ratio": f"{actual_dc_ac:.2f}"
    }

    design_summary_dict = {
        "DC Capacity (kWp)": f"{actual_dc_kwp:.2f} kWp",
        "AC Output (kW)": f"{actual_plant_ac_kw:.1f} kW",
        "DC/AC Sizing Ratio": f"{actual_dc_ac:.2f}",
        "Module Model": f"{panel.manufacturer} {panel.model} ({panel.rated_power_wp}Wp)",
        "Module Count": f"{chosen_panels} Modules",
        "String Configuration": f"{chosen_strings} Strings ({panels_per_str} modules/string)",
        "Inverter Model": f"{inverter.manufacturer} {inverter.model} ({inverter.rated_ac_power_kw}kW)",
        "Inverter Units": f"{inv_units} units",
        "Est. Annual Yield": f"{actual_dc_kwp * 4.5 * 365 * 0.78:,.0f} kWh/year",
        "Performance Ratio": "78.0%"
    }

    exp_col1, exp_col2, exp_col3, exp_col4 = st.columns(4)

    with exp_col1:
        try:
            pdf_bytes = generate_pdf_report(
                project_name=proj_name,
                project_meta=project_meta_dict,
                design_results=design_summary_dict,
                bom_items=[b.__dict__ for b in bom_items],
                validation_items=validation_items
            )
            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_bytes,
                file_name=f"{proj_name.replace(' ', '_')}_Engineering_Report.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as ex:
            st.error(f"PDF Error: {str(ex)}")

    with exp_col2:
        try:
            excel_bytes = generate_excel_report(
                project_data=design_summary_dict,
                bom_items=[b.__dict__ for b in bom_items],
                validation_items=validation_items
            )
            st.download_button(
                label="📊 Download Excel Schedules",
                data=excel_bytes,
                file_name=f"{proj_name.replace(' ', '_')}_Design_Schedules.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as ex:
            st.error(f"Excel Error: {str(ex)}")

    with exp_col3:
        try:
            csv_bytes = export_bom_to_csv(bom_items)
            st.download_button(
                label="📋 Download BOM CSV",
                data=csv_bytes,
                file_name=f"{proj_name.replace(' ', '_')}_BOM.csv",
                mime="text/csv",
                use_container_width=True
            )
        except Exception as ex:
            st.error(f"CSV Error: {str(ex)}")

    with exp_col4:
        try:
            svg_markup = generate_sld_svg(
                project_name=proj_name,
                total_dc_kwp=actual_dc_kwp,
                total_ac_kw=actual_plant_ac_kw,
                panel_model=f"{panel.rated_power_wp}Wp {panel.manufacturer}",
                inverter_model=f"{inverter.rated_ac_power_kw}kW {inverter.manufacturer} {inverter.model}",
                strings_count=chosen_strings,
                mppt_count=inverter.mppt_count,
                ac_voltage=grid_v
            )
            st.download_button(
                label="📐 Download SLD (SVG)",
                data=svg_markup,
                file_name=f"{proj_name.replace(' ', '_')}_SLD.svg",
                mime="image/svg+xml",
                use_container_width=True
            )
        except Exception as ex:
            st.error(f"SLD Error: {str(ex)}")
            svg_markup = ""

    # Single Line Diagram Visual Preview
    if svg_markup:
        with st.expander("⚡ Single Line Diagram (SLD) Live Visual Preview", expanded=False):
            st.markdown(svg_markup, unsafe_allow_html=True)

    # Sync with Session State
    st.session_state.active_project = {
        "name": proj_name,
        "customer_name": client_name,
        "site_name": proj_name,
        "location": site_loc,
        "target_ac_kw": actual_plant_ac_kw,
        "target_ac_capacity_kw": actual_plant_ac_kw,
        "min_design_temp_c": t_min,
        "max_design_temp_c": t_max,
        "status": "approved",
        "revision": 1
    }
    st.session_state.last_design_result = {
        "panel": panel,
        "inverter": inverter,
        "panels_per_string": panels_per_str,
        "total_panels": chosen_panels,
        "total_strings": chosen_strings,
        "dc_capacity_kwp": actual_dc_kwp,
        "ac_capacity_kw": actual_plant_ac_kw,
        "validation_items": validation_items,
        "bom_items": bom_items
    }

