"""
pages/26_📦_BOM.py — Intelligent Solar PV Bill of Materials (BOQ) Generator
Automated equipment selection, string-level DC protection, capacity-aware AC switchgear,
structured RF / Production equipment, configurable AC rules table, AUTO/MANUAL dual modes,
reactive capacity switching, interactive editable takeoff, and professional Excel export.
Authored by Eng. Aashir © 2026.
"""
import streamlit as st
import pandas as pd
import math
from ui.components import page_header, nav_sidebar, render_status
from ui.styles import apply_custom_css
from core.bom_engine import BOMEngine, ENGINEERING_DISCLAIMER
from core.bom_generator import generate_bom
from core.models import Panel, Inverter
from core.project_state import (
    get_active_project,
    get_active_panel,
    get_active_inverter,
    get_design_value,
    render_active_project_banner,
    get_approved_panels,
    get_approved_panel_by_wattage,
    get_default_panel,
    get_default_inverter
)
from reports.csv_export import export_bom_to_csv
from reports.boq_excel_generator import generate_boq_excel

try:
    st.set_page_config(page_title="BOM & BOQ Generator — Solar PV Platform", page_icon="📦", layout="wide")
except Exception:
    pass

apply_custom_css()
nav_sidebar()
render_active_project_banner()
page_header(
    "Intelligent Bill of Quantities (BOM / BOQ) Engine",
    "Rule-based automated sizing, string-level switchgear coordination, RF/production equipment, interactive editable takeoff, and professional Excel export",
    icon="📦"
)

# Initialize BOM Engine
bom_engine = BOMEngine()

# Active Project & Equipment Context
proj = get_active_project()

# Initialize session state for capacity and overrides
if "bom_system_cap_kw" not in st.session_state:
    st.session_state["bom_system_cap_kw"] = 5.0

if "bom_last_cap" not in st.session_state:
    st.session_state["bom_last_cap"] = st.session_state["bom_system_cap_kw"]

if "bom_overrides" not in st.session_state:
    st.session_state["bom_overrides"] = {}

# Detect capacity change from user input and reset stale overrides
if st.session_state["bom_system_cap_kw"] != st.session_state["bom_last_cap"]:
    st.session_state["bom_last_cap"] = st.session_state["bom_system_cap_kw"]
    st.session_state["bom_overrides"] = {}

tab_wizard, tab_schedules = st.tabs([
    "🚀 Intelligent BOM / BOQ Generator",
    "📋 Detailed Material Schedules (BOS Takeoff)"
])

# ===========================================================================
# TAB 1: INTELLIGENT BOM / BOQ GENERATOR
# ===========================================================================
with tab_wizard:
    st.markdown("### ⚙️ Step 1: Project & Capacity Configuration")

    # Quick Preset Capacity Buttons
    st.markdown("##### ⚡ Quick System Capacity Presets")
    q_col1, q_col2, q_col3, q_col4, q_col5 = st.columns(5)
    with q_col1:
        if st.button("🟢 5 kW (Default)", use_container_width=True, type="primary" if st.session_state["bom_system_cap_kw"] == 5.0 else "secondary"):
            st.session_state["bom_system_cap_kw"] = 5.0
            st.session_state["bom_last_cap"] = 5.0
            st.session_state["bom_overrides"] = {}
            st.rerun()
    with q_col2:
        if st.button("⚡ 10 kW", use_container_width=True, type="primary" if st.session_state["bom_system_cap_kw"] == 10.0 else "secondary"):
            st.session_state["bom_system_cap_kw"] = 10.0
            st.session_state["bom_last_cap"] = 10.0
            st.session_state["bom_overrides"] = {}
            st.rerun()
    with q_col3:
        if st.button("⚡ 20 kW", use_container_width=True, type="primary" if st.session_state["bom_system_cap_kw"] == 20.0 else "secondary"):
            st.session_state["bom_system_cap_kw"] = 20.0
            st.session_state["bom_last_cap"] = 20.0
            st.session_state["bom_overrides"] = {}
            st.rerun()
    with q_col4:
        if st.button("⚡ 50 kW", use_container_width=True, type="primary" if st.session_state["bom_system_cap_kw"] == 50.0 else "secondary"):
            st.session_state["bom_system_cap_kw"] = 50.0
            st.session_state["bom_last_cap"] = 50.0
            st.session_state["bom_overrides"] = {}
            st.rerun()
    with q_col5:
        if st.button("⚡ 100 kW", use_container_width=True, type="primary" if st.session_state["bom_system_cap_kw"] == 100.0 else "secondary"):
            st.session_state["bom_system_cap_kw"] = 100.0
            st.session_state["bom_last_cap"] = 100.0
            st.session_state["bom_overrides"] = {}
            st.rerun()

    col_cap, col_ph, col_type, col_over = st.columns(4)
    with col_cap:
        system_cap_kw = st.number_input(
            "System / Inverter Capacity (kW)",
            min_value=1.0,
            max_value=500.0,
            value=float(st.session_state["bom_system_cap_kw"]),
            step=1.0,
            key="bom_system_cap_kw_input",
            help="Rated AC capacity of the photovoltaic inverter or plant. Loads 5 kW by default."
        )
        if system_cap_kw != st.session_state["bom_system_cap_kw"]:
            st.session_state["bom_system_cap_kw"] = system_cap_kw
            st.session_state["bom_last_cap"] = system_cap_kw
            st.session_state["bom_overrides"] = {}
            st.rerun()

    # Automatic phase suggestion based on centralized rules
    phase_rule = bom_engine.select_phase(system_cap_kw)
    suggested_phase = phase_rule["phase"]
    phase_label = f"{suggested_phase} Phase ({phase_rule['category']})"

    with col_ph:
        phase_options = ["Auto (From Rule Engine)", "Single Phase (1P 230V)", "Three Phase (3P 400V)"]
        default_ph_idx = 0
        selected_phase_str = st.selectbox(
            "Grid Phase Category",
            phase_options,
            index=default_ph_idx,
            key=f"bom_phase_{system_cap_kw}",
            help=f"Rule Engine suggests: {phase_label} for {system_cap_kw} kW per CEB / Company standards."
        )
        if "Single" in selected_phase_str:
            evaluated_phase = 1
        elif "Three" in selected_phase_str:
            evaluated_phase = 3
        else:
            evaluated_phase = suggested_phase

    with col_type:
        install_type = st.selectbox(
            "Installation Type",
            ["Rooftop (Metal Sheet)", "Rooftop (Tile Roof)", "Ground Mount"],
            index=0,
            key=f"bom_instype_{system_cap_kw}"
        )

    with col_over:
        default_oversize = 1.30 if "Rooftop" in install_type else 1.20
        dc_oversize_factor = st.number_input(
            "DC Oversizing Factor",
            min_value=1.00,
            max_value=1.60,
            value=float(default_oversize),
            step=0.05,
            key=f"bom_oversize_{system_cap_kw}",
            help="DC/AC ratio multiplier (Default 1.30 = 30% rooftop oversizing)."
        )

    dc_target_info = bom_engine.calculate_dc_target(system_cap_kw, install_type, dc_oversize_factor)
    target_dc_kwp = dc_target_info["target_dc_kwp"]

    st.info(
        f"🎯 **Target DC Sizing:** {system_cap_kw:.1f} kW AC × {dc_oversize_factor:.2f} = **{target_dc_kwp:.2f} kWp DC** | "
        f"Grid Category: **{phase_rule['category']}** ({phase_rule['rule_source']})"
    )

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Step 2: Inverter & Controlled Approved Panel Selection
    # -----------------------------------------------------------------------
    st.markdown("### 🔌 Step 2: Equipment Selection & Controlled Approved Panels")

    col_inv_sel, col_pnl_sel = st.columns([1, 1])

    # Available inverters matching phase
    inverter_candidates = [
        inv for inv in bom_engine.master_data.get("inverters", [])
        if inv.get("is_active", True) and inv.get("phases", 3 if evaluated_phase == 3 else 1) == evaluated_phase
    ]
    if not inverter_candidates:
        inverter_candidates = bom_engine.master_data.get("inverters", [])

    inv_display_names = [f"{inv['model']} ({inv['rated_ac_power_kw']} kW, {inv['phases']}P, {inv['mppt_count']} MPPT)" for inv in inverter_candidates]
    default_inv_idx = 0
    for idx, inv in enumerate(inverter_candidates):
        if abs(inv["rated_ac_power_kw"] - system_cap_kw) < 0.1:
            default_inv_idx = idx
            break

    with col_inv_sel:
        inv_idx = st.selectbox(
            "Selected Solar Inverter",
            range(len(inverter_candidates)),
            format_func=lambda i: inv_display_names[i],
            index=default_inv_idx,
            key=f"bom_inv_select_{system_cap_kw}"
        )
        raw_inv = inverter_candidates[inv_idx]
        current_inverter = Inverter(
            id=raw_inv.get("id", "inv-selected"),
            manufacturer=raw_inv.get("manufacturer", "Sunways"),
            model=raw_inv.get("model", f"{system_cap_kw}kW Inverter"),
            rated_ac_power_kw=float(raw_inv.get("rated_ac_power_kw", system_cap_kw)),
            max_dc_input_power_kw=float(raw_inv.get("max_dc_power_kw", system_cap_kw * 1.35)),
            max_dc_voltage_v=float(raw_inv.get("max_dc_voltage_v", 600.0 if evaluated_phase == 1 else 1100.0)),
            mppt_voltage_min_v=float(raw_inv.get("mppt_voltage_min_v", 100.0 if evaluated_phase == 1 else 160.0)),
            mppt_voltage_max_v=float(raw_inv.get("mppt_voltage_max_v", 550.0 if evaluated_phase == 1 else 1000.0)),
            mppt_count=int(raw_inv.get("mppt_count", 2)),
            string_inputs_per_mppt=int(raw_inv.get("string_inputs_per_mppt", 1)),
            max_input_current_per_mppt_a=float(raw_inv.get("max_input_current_per_mppt_a", 15.0 if evaluated_phase == 1 else 26.0)),
            max_isc_per_mppt_a=float(raw_inv.get("max_isc_per_mppt_a", 20.0 if evaluated_phase == 1 else 40.0)),
            max_total_dc_current_a=float(raw_inv.get("max_input_current_per_mppt_a", 15.0) * raw_inv.get("mppt_count", 2)),
            ac_voltage=float(raw_inv.get("ac_voltage", 230.0 if evaluated_phase == 1 else 400.0)),
            rated_ac_current_a=float(raw_inv.get("max_ac_current_a", 22.8 if evaluated_phase == 1 else 15.2)),
            max_ac_current_a=float(raw_inv.get("max_ac_current_a", 22.8 if evaluated_phase == 1 else 15.2)),
            efficiency_pct=float(raw_inv.get("efficiency_pct", 98.1 if evaluated_phase == 1 else 98.6)),
            source="master_data"
        )

    # Approved Panel Selection Mode
    approved_panels = get_approved_panels()
    min_temp = float(proj.get("min_design_temp_c", -30.0))
    max_temp = float(proj.get("max_design_temp_c", 60.0))

    with col_pnl_sel:
        panel_mode = st.radio(
            "Module Selection Mode",
            ["Approved List (580W / 615W / 630W)", "Custom Panel / Manual Entry"],
            horizontal=True,
            key=f"bom_panel_mode_{system_cap_kw}"
        )

        if panel_mode == "Approved List (580W / 615W / 630W)":
            pnl_labels = [f"{p.rated_power_wp:.0f} Wp — {p.model}" + (" ⭐ (Default)" if p.rated_power_wp == 630.0 else "") for p in approved_panels]
            default_pnl_idx = 2  # 630W is index 2
            selected_pnl_idx = st.selectbox(
                "Select Approved PV Module",
                range(len(approved_panels)),
                index=default_pnl_idx,
                format_func=lambda i: pnl_labels[i],
                key=f"bom_appr_pnl_idx_{system_cap_kw}"
            )
            selected_panel = approved_panels[selected_pnl_idx]
        else:
            with st.container(border=True):
                c_m1, c_m2 = st.columns(2)
                custom_mfr = c_m1.text_input("Manufacturer", "Custom Solar", key=f"bom_cmfr_{system_cap_kw}")
                custom_model = c_m2.text_input("Model", "Custom-630W", key=f"bom_cmod_{system_cap_kw}")
                c_m3, c_m4, c_m5 = st.columns(3)
                custom_wp = c_m3.number_input("Rated Wp", value=630.0, step=5.0, key=f"bom_cwp_{system_cap_kw}")
                custom_voc = c_m4.number_input("Voc (V)", value=49.44, step=0.1, key=f"bom_cvoc_{system_cap_kw}")
                custom_vmp = c_m5.number_input("Vmp (V)", value=41.47, step=0.1, key=f"bom_cvmp_{system_cap_kw}")
                c_m6, c_m7, c_m8 = st.columns(3)
                custom_isc = c_m6.number_input("Isc (A)", value=16.18, step=0.1, key=f"bom_cisc_{system_cap_kw}")
                custom_imp = c_m7.number_input("Imp (A)", value=15.19, step=0.1, key=f"bom_cimp_{system_cap_kw}")
                custom_fuse = c_m8.number_input("Max Fuse (A)", value=30.0, step=5.0, key=f"bom_cfuse_{system_cap_kw}")
                selected_panel = Panel(
                    id="custom-panel-bom",
                    manufacturer=custom_mfr,
                    model=custom_model,
                    rated_power_wp=custom_wp,
                    voc=custom_voc,
                    vmp=custom_vmp,
                    isc=custom_isc,
                    imp=custom_imp,
                    max_system_voltage=1500.0,
                    max_series_fuse=custom_fuse,
                    temp_coeff_voc=-0.24,
                    temp_coeff_vmp=-0.26,
                    temp_coeff_isc=0.042,
                    temp_coeff_pmax=-0.29,
                    length_m=2.382,
                    width_m=1.134,
                    thickness_mm=30.0,
                    weight_kg=33.0,
                    cell_technology="N-type TOPCon Bifacial",
                    cell_count=132,
                    source="manual"
                )

    # Multi-Panel Optimization Matrix
    opt_results = bom_engine.optimize_panel_selection(target_dc_kwp, current_inverter, min_temp, max_temp, approved_panels)
    with st.expander("🔍 Approved Panels Comparison Matrix (580W, 615W, 630W)", expanded=False):
        opt_rows = []
        for r in opt_results:
            p = r["panel"]
            opt_rows.append({
                "Status": r.get("badge", "❓"),
                "Panel Model": p.model,
                "Power": f"{p.rated_power_wp:.0f} Wp",
                "Panels": r.get("panel_count", 0),
                "String Architecture": f"{r.get('strings_count', 0)} str × {r.get('panels_per_string', 0)} mod",
                "Actual DC (kWp)": f"{r.get('actual_dc_kwp', 0.0):.2f}",
                "DC/AC Ratio": f"{r.get('dc_ac_ratio', 0.0):.2f}",
                "Deviation from Target": f"{r.get('deviation_kwp', 0.0):+.2f} kWp",
                "Engineering Rationale": r.get("reason", "")
            })
        st.dataframe(pd.DataFrame(opt_rows), use_container_width=True, hide_index=True)

    # Panel count derivation
    rec_count = 12
    for r in opt_results:
        if r["panel"].id == selected_panel.id and r.get("panel_count", 0) > 0:
            rec_count = r["panel_count"]
            break

    # If user has an active override for panel_count, apply it
    user_panel_override = st.session_state["bom_overrides"].get("panel_count", None)
    count_to_show = int(user_panel_override if user_panel_override is not None else rec_count)

    col_cnt_info, col_cnt_ovr = st.columns([2, 1])
    with col_cnt_info:
        st.caption(f"Theoretical Panel Requirement: `CEILING({target_dc_kwp:.2f} kWp / {selected_panel.rated_power_wp/1000:.3f} kW) = {math.ceil(target_dc_kwp/(selected_panel.rated_power_wp/1000))}` modules")
    with col_cnt_ovr:
        final_panel_count = st.number_input(
            "Final Validated Panel Quantity",
            min_value=1,
            max_value=2000,
            value=count_to_show,
            step=1,
            key=f"bom_final_pnl_cnt_{system_cap_kw}",
            help="Sized to satisfy string divisibility and inverter MPPT symmetry."
        )
        if final_panel_count != rec_count:
            st.session_state["bom_overrides"]["panel_count"] = final_panel_count

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Step 3: String Architecture & MPPT Distribution
    # -----------------------------------------------------------------------
    st.markdown("### 🔢 Step 3: PV Design Summary & MPPT Distribution")

    str_info = bom_engine.calculate_string_and_mppt(selected_panel, current_inverter, final_panel_count, min_temp, max_temp)
    actual_dc_kwp = round(final_panel_count * selected_panel.rated_power_wp / 1000.0, 2)
    dc_ac_ratio = round(actual_dc_kwp / current_inverter.rated_ac_power_kw, 2)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Target DC", f"{target_dc_kwp:.2f} kWp")
    m2.metric("Selected Panel", f"{selected_panel.rated_power_wp:.0f} Wp")
    m3.metric("Total Panels", f"{final_panel_count} pcs")
    m4.metric("Actual DC", f"{actual_dc_kwp:.2f} kWp")
    m5.metric("DC/AC Ratio", f"{dc_ac_ratio:.2f}")
    m6.metric("String Config", f"{str_info['total_strings']} str × {str_info['panels_per_string']} mod")

    # Voltage & Current Check Row
    st.caption("⚡ Electrical Validation Bounds:")
    c_v1, c_v2, c_v3 = st.columns(3)
    with c_v1:
        voc_pass = str_info["string_voc_cold_v"] <= current_inverter.max_dc_voltage_v
        render_status("PASS" if voc_pass else "FAIL", f"Cold String Voc: {str_info['string_voc_cold_v']} V (Max: {current_inverter.max_dc_voltage_v} V)")
    with c_v2:
        vmp_pass = str_info["string_vmp_hot_v"] >= current_inverter.mppt_voltage_min_v
        render_status("PASS" if vmp_pass else "FAIL", f"Hot String Vmp: {str_info['string_vmp_hot_v']} V (Min MPPT: {current_inverter.mppt_voltage_min_v} V)")
    with c_v3:
        render_status("PASS", f"String Current: Imp={str_info['string_imp_a']} A, Isc={str_info['string_isc_a']} A")

    # MPPT Distribution display
    with st.expander("🧩 MPPT String Allocation Details", expanded=False):
        mppt_cols = st.columns(len(str_info["mppt_distribution"]))
        for i, m_data in enumerate(str_info["mppt_distribution"]):
            with mppt_cols[i]:
                st.markdown(f"**MPPT {m_data['mppt_number']}**")
                st.markdown(f"- Strings: `{m_data['strings_count']}`")
                st.markdown(f"- Modules: `{m_data['strings_count'] * m_data['panels_per_string']}`")
                st.markdown(f"- Operating I: `{m_data['operating_current_a']} A`")
                render_status(m_data["status"])

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Step 4: Coordinated Protection Switchgear (String-Level DC & Capacity-Aware AC)
    # -----------------------------------------------------------------------
    st.markdown("### 🛡️ Step 4: Coordinated Protection Switchgear")

    dc_prot = bom_engine.select_dc_protection(
        string_voc_cold=str_info["string_voc_cold_v"],
        string_isc=selected_panel.isc,
        total_strings=str_info["total_strings"],
        strings_per_mppt=max(1, math.ceil(str_info["total_strings"] / current_inverter.mppt_count)),
        phase=evaluated_phase,
        panel_max_fuse=selected_panel.max_series_fuse
    )

    ac_prot = bom_engine.select_ac_protection(
        inverter=current_inverter,
        system_capacity_kw=system_cap_kw,
        phase=evaluated_phase,
        ac_voltage=current_inverter.ac_voltage,
        pf=getattr(current_inverter, "pf", 0.95)
    )

    # String-Level DC Architecture Banner
    st.success(
        f"📐 **String-Level DC Protection Architecture:** {str_info['total_strings']} DC Strings → "
        f"**{dc_prot['dc_isolator']['quantity']} × DC Isolators** (1 per string) + "
        f"**{dc_prot['dc_spd']['quantity']} × DC SPDs** (Uc >= 1.20 × Voc,cold = {dc_prot['dc_spd']['voltage_rating']:.0f}V) + "
        f"{'Required' if dc_prot['dc_fuse']['required'] else 'Optional'} DC String Fuses."
    )

    col_dc_prot, col_ac_prot = st.columns(2)
    with col_dc_prot:
        st.subheader("⚡ DC Side Protection (String-Level)")
        with st.container(border=True):
            # Check for DC overrides
            dc_iso_ovr = st.session_state["bom_overrides"].get("dc_isolator", None)
            dc_spd_ovr = st.session_state["bom_overrides"].get("dc_spd", None)

            iso_mode = "🛠️ MANUAL" if dc_iso_ovr else "🤖 AUTO"
            spd_mode = "🛠️ MANUAL" if dc_spd_ovr else "🤖 AUTO"

            iso = dc_iso_ovr or dc_prot["dc_isolator"]
            st.markdown(f"**DC Isolator:** {iso['brand']} {iso['model']} `{iso_mode}`")
            st.caption(f"Rating: {iso['voltage_rating']}V, {iso['current_rating']}A ({iso['pole']}) | Qty: {iso['quantity']} nos (1 per string)")
            render_status(iso.get("status", "PASS"), iso.get("reason", ""))

            spd = dc_spd_ovr or dc_prot["dc_spd"]
            st.markdown(f"**DC SPD:** {spd['brand']} {spd['model']} `{spd_mode}`")
            st.caption(f"Rating: {spd['voltage_rating']}V, {spd.get('ka_rating', 40)}kA ({spd['pole']}) | Qty: {spd['quantity']} nos | Uc >= 1.20×Voc")
            render_status(spd.get("status", "PASS"), spd.get("reason", ""))

            fuse = dc_prot["dc_fuse"]
            st.markdown(f"**DC String Fuse:** {fuse['brand']} {fuse['model']} `🤖 AUTO`")
            st.caption(f"Rating: {fuse['current_rating']}A gPV 1000V DC | Required: {'Yes' if fuse['required'] else 'No (Optional for <= 2 parallel strings)'} | Qty: {fuse['quantity']} nos")
            render_status(fuse.get("status", "PASS"), fuse.get("reason", ""))

    with col_ac_prot:
        st.subheader("⚡ AC Side Protection (Capacity-Aware)")
        with st.container(border=True):
            ac_iso_ovr = st.session_state["bom_overrides"].get("ac_isolator", None)
            ac_spd_ovr = st.session_state["bom_overrides"].get("ac_spd", None)
            ac_brk_ovr = st.session_state["bom_overrides"].get("ac_breaker", None)
            ac_lck_ovr = st.session_state["bom_overrides"].get("lockable_isolator", None)

            ac_iso_mode = "🛠️ MANUAL" if ac_iso_ovr else "🤖 AUTO"
            ac_spd_mode = "🛠️ MANUAL" if ac_spd_ovr else "🤖 AUTO"
            ac_brk_mode = "🛠️ MANUAL" if ac_brk_ovr else "🤖 AUTO"
            ac_lck_mode = "🛠️ MANUAL" if ac_lck_ovr else "🤖 AUTO"

            ac_iso = ac_iso_ovr or ac_prot["ac_isolator"]
            st.markdown(f"**AC Isolator:** {ac_iso['brand']} {ac_iso['model']} `{ac_iso_mode}`")
            st.caption(f"Rating: {ac_iso['voltage_rating']}V, {ac_iso['current_rating']}A ({ac_iso['pole']}) | Qty: 1 nos")
            render_status(ac_iso.get("status", "PASS"), ac_iso.get("reason", ""))

            ac_spd = ac_spd_ovr or ac_prot["ac_spd"]
            st.markdown(f"**AC SPD:** {ac_spd['brand']} {ac_spd['model']} `{ac_spd_mode}`")
            st.caption(f"Rating: {ac_spd['voltage_rating']}V, {ac_spd.get('ka_rating', 40)}kA ({ac_spd['pole']}) | Qty: 1 nos")
            render_status(ac_spd.get("status", "PASS"), ac_spd.get("reason", ""))

            brk = ac_brk_ovr or ac_prot["ac_breaker"]
            st.markdown(f"**{brk.get('breaker_type', 'MCB/MCCB')} Breaker:** {brk['brand']} {brk['model']} `{ac_brk_mode}`")
            st.caption(f"Rating: {brk['current_rating']}A ({brk['pole']}) | Rated AC Current: {ac_prot['rated_ac_current_a']:.1f}A | Qty: 1 nos")
            render_status(brk.get("status", "PASS"), brk.get("reason", ""))

            lock = ac_lck_ovr or ac_prot["lockable_isolator"]
            st.markdown(f"**Utility Lockable Switch:** {lock['brand']} {lock['model']} `{ac_lck_mode}`")
            st.caption(f"Rating: {lock['voltage_rating']}V, {lock['current_rating']}A ({lock['pole']}) Padlockable (CEB requirement) | Qty: 1 nos")
            render_status(lock.get("status", "PASS"), lock.get("reason", ""))

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Step 5: Structured RF / Production Equipment & Validation
    # -----------------------------------------------------------------------
    st.markdown("### 📡 Step 5: Structured RF / Production & Monitoring Equipment")

    rf_items = bom_engine.select_rf_production_equipment(
        system_capacity_kw=system_cap_kw,
        phase=evaluated_phase,
        inverter=current_inverter
    )

    with st.container(border=True):
        rf_c1, rf_c2, rf_c3, rf_c4 = st.columns(4)
        for i, item in enumerate(rf_items):
            target_col = [rf_c1, rf_c2, rf_c3, rf_c4][i % 4]
            with target_col:
                st.markdown(f"**{item['item_name']}** `🤖 AUTO`")
                st.markdown(f"*{item['model']}* ({item['brand']})")
                st.caption(f"Spec: {item['specification']} | Qty: {item['quantity']} {item['unit']}")
                st.caption(f"Note: {item.get('remarks', '')}")

    # Design & Compatibility Health Check Validation Banner
    validation_warnings = bom_engine.validate_system_configuration(
        panel=selected_panel,
        inverter=current_inverter,
        string_info=str_info,
        dc_prot=dc_prot,
        ac_prot=ac_prot
    )
    if system_cap_kw > 5.0 and evaluated_phase == 1:
        validation_warnings.append({
            "severity": "WARNING",
            "parameter": "Grid Phase Standard",
            "message": f"Single-phase connection is restricted to maximum 5 kW per CEB / LECO interconnection code. For {system_cap_kw:.1f} kW, Three-Phase 400V is required."
        })
    if system_cap_kw <= 5.0 and evaluated_phase == 3:
        validation_warnings.append({
            "severity": "WARNING",
            "parameter": "Grid Phase Standard",
            "message": f"Three-phase connection for a {system_cap_kw:.1f} kW system increases tariff and balance-of-system cost. Single-phase 230V is recommended."
        })

    if validation_warnings:
        st.markdown("#### ⚠️ System Design & Compatibility Health Check")
        for w in validation_warnings:
            if w["severity"] == "FAIL":
                st.error(f"❌ **Configuration not recommended ({w['parameter']}):** {w['message']}")
            else:
                st.warning(f"⚠️ **Configuration not recommended ({w['parameter']}):** {w['message']}")

    # Expandable Configurable AC Protection Rules Table
    with st.expander("⚙️ Configurable AC Protection Selection Table (Administrator / Engineering Rules)", expanded=False):
        st.info("Centralized AC protection rule matrix. Modifying breakpoints updates automatic sizing rules across all capacities.")
        current_ac_table = bom_engine.get_ac_protection_table()
        df_ac_table = pd.DataFrame(current_ac_table)
        edited_ac_table = st.data_editor(
            df_ac_table,
            use_container_width=True,
            num_rows="dynamic",
            key=f"ac_rule_editor_{system_cap_kw}"
        )
        if st.button("💾 Save AC Protection Rules", type="secondary", key=f"btn_save_ac_{system_cap_kw}"):
            if bom_engine.save_ac_protection_table(edited_ac_table.to_dict(orient="records")):
                st.success("✅ AC Protection rules updated and saved successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to save AC protection rules.")

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Step 6: Complete Interactive Editable BOQ Table
    # -----------------------------------------------------------------------
    st.markdown("### 📋 Step 6: Interactive Bill of Quantities (Editable Before Download)")
    st.caption("You can directly edit item descriptions, brands, ratings, quantities, unit prices, remarks, or supplier names in the table below before exporting.")

    # Generate complete BOQ payload
    project_payload = {
        "system_capacity_kw": system_cap_kw,
        "phase": evaluated_phase,
        "installation_type": install_type,
        "inverter": current_inverter,
        "panel": selected_panel,
        "dc_oversizing_factor": dc_oversize_factor,
        "customer_name": proj.get("customer_name", ""),
        "min_design_temp_c": min_temp,
        "max_design_temp_c": max_temp
    }
    user_overrides = {"panel_count": final_panel_count, **st.session_state["bom_overrides"]}
    raw_boq = bom_engine.generate_boq(project_payload, user_overrides)
    raw_items = raw_boq["boq_items"]

    # Convert to DataFrame for st.data_editor
    df_raw = pd.DataFrame(raw_items)

    # Organize columns
    col_order = ["sn", "category", "item_name", "description", "brand", "specification", "unit", "quantity", "mode", "unit_price", "total_price", "remarks", "supplier"]
    existing_cols = [c for c in col_order if c in df_raw.columns] + [c for c in df_raw.columns if c not in col_order and c != "rule_source"]
    df_editor = df_raw[existing_cols].copy()

    # Rename columns for presentation
    df_editor.rename(columns={
        "sn": "S/N",
        "category": "Category",
        "item_name": "Item",
        "description": "Description",
        "brand": "Brand",
        "specification": "Capacity / Spec",
        "unit": "Unit",
        "quantity": "QTY",
        "mode": "Mode",
        "unit_price": "Unit Price (Rs)",
        "total_price": "Total Price (Rs)",
        "remarks": "Remarks",
        "supplier": "Supplier"
    }, inplace=True)

    edited_df = st.data_editor(
        df_editor,
        use_container_width=True,
        num_rows="dynamic",
        key=f"editable_boq_table_{system_cap_kw}",
        hide_index=True
    )

    # -----------------------------------------------------------------------
    # Step 7: Professional Excel Export & Blank Field Rule
    # -----------------------------------------------------------------------
    st.markdown("### 📥 Step 7: Professional Excel Export")

    with st.expander("📝 Project & Quotation Metadata (Optional - Blank Field Rule Active)", expanded=False):
        st.info("ℹ️ Per engineering guidelines, unknown fields will remain completely blank in the generated Excel unless filled below.")
        meta_c1, meta_c2, meta_c3 = st.columns(3)
        cust_input = meta_c1.text_input("Customer Name", value=proj.get("customer_name", ""), key=f"meta_cust_{system_cap_kw}")
        site_input = meta_c2.text_input("Site / Project Location", value=proj.get("site_name", ""), key=f"meta_site_{system_cap_kw}")
        date_input = meta_c3.text_input("Quotation Date", value="", key=f"meta_date_{system_cap_kw}")

    # Prepare export items from edited dataframe
    export_items = []
    for _, row in edited_df.iterrows():
        export_items.append({
            "sn": row.get("S/N", ""),
            "category": row.get("Category", ""),
            "item_name": row.get("Item", ""),
            "description": row.get("Description", ""),
            "brand": row.get("Brand", ""),
            "capacity": row.get("Capacity / Spec", ""),
            "specification": row.get("Capacity / Spec", ""),
            "unit": row.get("Unit", "nos"),
            "quantity": row.get("QTY", 0),
            "unit_price": row.get("Unit Price (Rs)", ""),
            "total_price": row.get("Total Price (Rs)", ""),
            "remarks": row.get("Remarks", ""),
            "supplier": row.get("Supplier", ""),
            "mode": row.get("Mode", "AUTO")
        })

    excel_metadata = {
        "system_capacity_kw": system_cap_kw,
        "phase_desc": phase_rule["category"],
        "customer_name": cust_input,
        "site_name": site_input,
        "date": date_input,
        "disclaimer": ENGINEERING_DISCLAIMER
    }

    try:
        excel_bytes = generate_boq_excel(export_items, excel_metadata)
        excel_filename = f"Solar_BOQ_{int(system_cap_kw)}kW.xlsx"

        st.download_button(
            label=f"📥 Download Formatted BOQ Excel ({excel_filename})",
            data=excel_bytes,
            file_name=excel_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_excel_{system_cap_kw}"
        )
    except Exception as e:
        st.error(f"Error preparing Excel download: {e}")

    st.caption(f"🛡️ **Engineering Disclaimer:** {ENGINEERING_DISCLAIMER}")


# ===========================================================================
# TAB 2: DETAILED MATERIAL SCHEDULES (PRESERVED WORKFLOW)
# ===========================================================================
with tab_schedules:
    st.markdown("### ⚙️ Cable Run Length Estimates & Equipment Context")
    c_str, c_ac, c_ea = st.columns(3)
    dc_cable_len = c_str.number_input("Average DC Cable Run per String (m)", value=float(get_design_value("dc_cable_length_m", 30.0)), step=5.0)
    ac_cable_len = c_ac.number_input("Average Inverter AC Run to Panelboard (m)", value=float(get_design_value("ac_cable_length_m", 20.0)), step=5.0)
    earth_cable_len = c_ea.number_input("Estimated Main Earth Conductor Run (m)", value=35.0, step=5.0)

    # Pull switchgear and metering state
    dc_iso_state = get_design_value("dc_isolator", {})
    lock_iso_state = get_design_value("lockable_isolator", {})
    meter_state = get_design_value("meter_selection_result", {})

    total_p = int(get_design_value("panel_qty", 12))
    panels_per_s = int(get_design_value("panels_per_string", 6))
    total_s = int(get_design_value("total_strings", 2))
    inv_u = max(1, int(round(system_cap_kw / current_inverter.rated_ac_power_kw))) if current_inverter.rated_ac_power_kw > 0 else 1

    breakdown = [{"inverter": current_inverter, "quantity": inv_u}]
    design_result = {
        "panel_qty": total_p,
        "total_panels": total_p,
        "panels_per_string": panels_per_s,
        "total_strings": total_s,
        "dc_string_cable_length_m": dc_cable_len,
        "ac_cable_length_m": ac_cable_len,
        "earth_conductor_length_m": earth_cable_len,
        "earth_rod_count": 2 if system_cap_kw <= 5.0 else 3
    }

    bom_items = generate_bom(
        panel=selected_panel,
        inverter_breakdown=breakdown,
        design_result=design_result,
        project=proj,
        dc_isolator_qty=total_s,
        meter_info=meter_state,
        lockable_isolator_info=lock_iso_state
    )

    bom_rows = []
    for idx, item in enumerate(bom_items, 1):
        bom_rows.append({
            "Item #": idx,
            "Category": item.category,
            "Item Name": item.item_name,
            "Description": item.description,
            "Manufacturer / Model": f"{item.manufacturer} {item.model}".strip() if item.manufacturer else "Approved Equivalent",
            "Technical Specification": item.specification,
            "Quantity": item.quantity,
            "Unit": item.unit,
            "Rule Source": getattr(item, "rule_source", "ENGINEERING_RULE"),
            "Engineering Derivation Basis": item.source or "Standard Engineering Takeoff"
        })

    df_bom = pd.DataFrame(bom_rows)

    sub_all, sub_mat, sub_cables, sub_prot, sub_equip = st.tabs([
        "📦 Complete Material Takeoff",
        "🏗️ Material & Mounting Schedule",
        "🔌 Cable & Routing Schedule",
        "🛡️ Electrical Protection Schedule",
        "⚡ Core PV Equipment Schedule"
    ])

    with sub_all:
        st.markdown(f"#### Complete Material Takeoff ({len(df_bom)} Line Items)")
        st.dataframe(df_bom, use_container_width=True, hide_index=True)
        csv_data = export_bom_to_csv(bom_items)
        st.download_button(
            label="📥 Download Complete BOM as CSV (with Rule Sourcing)",
            data=csv_data,
            file_name=f"Solar_PV_BOM_{proj.get('name', 'Project').replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with sub_mat:
        st.markdown("#### 🏗️ Mounting Structure & Structural Materials Schedule")
        mat_df = df_bom[df_bom["Category"].isin(["Structure", "Enclosure", "Connector"])]
        st.dataframe(mat_df if not mat_df.empty else df_bom, use_container_width=True, hide_index=True)

    with sub_cables:
        st.markdown("#### 🔌 Cabling & Interconnection Schedule")
        cable_df = df_bom[df_bom["Category"].isin(["Cable", "Earthing"])]
        st.dataframe(cable_df if not cable_df.empty else df_bom, use_container_width=True, hide_index=True)

    with sub_prot:
        st.markdown("#### 🛡️ Switchgear, Protection & Metering Schedule")
        prot_df = df_bom[df_bom["Category"].isin(["Protection", "Metering", "Distribution"])]
        st.dataframe(prot_df if not prot_df.empty else df_bom, use_container_width=True, hide_index=True)

    with sub_equip:
        st.markdown("#### ⚡ Core Photovoltaic Equipment Schedule")
        equip_df = df_bom[df_bom["Category"].isin(["Module", "Inverter"])]
        st.dataframe(equip_df, use_container_width=True, hide_index=True)
