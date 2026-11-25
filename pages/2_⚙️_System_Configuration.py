"""
pages/2_⚙️_System_Configuration.py — Dynamic Project & System Configuration Hub
Primary engineering input hub enforcing the Dynamic Solar System Design Engine logic:
  - Unrestricted Target Capacity Input (any float / int: 7, 8, 11, 13, 16, 23, 36, 47, 73, 125 kW, etc.)
  - Inverter Combination Engine:
      * AUTO MODE: Evaluates all feasible combinations using the 6 engineering priorities.
        Presents ranked options (⭐ Recommended, Alternative 1, Alternative 2) with full unit breakdown.
      * MANUAL MODE: Choose alternative combinations or configure individual inverters & quantities
        with live engineering validation (✓ Valid Manual Configuration / ✕ Warning).
  - Approved PV Module Selection (580W, 615W, 630W Default) / Manual Entry.
  - Project context, temperature extremes, cable run lengths.
  - Automatic Downstream Recalculation:
      Capacity -> Inverter Combo -> Panel Qty -> Strings -> MPPT -> DC Protection
      -> DC Cable -> Indiv AC Switchgear -> Main AC Cable/Switchgear -> Earthing -> BOQ.

Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
"""
import streamlit as st
from ui.styles import apply_custom_css
from ui.components import page_header, render_status
from core.models import Panel, Inverter, SpacingConfig
from core.project_state import (
    init_project_state,
    get_active_project,
    set_active_project,
    get_active_panel,
    set_active_panel,
    get_active_inverter,
    set_active_inverter,
    get_approved_panels,
    get_approved_panel_by_wattage,
    recalculate_system_state,
    get_dynamic_system,
    get_calculation_mode,
    set_calculation_mode,
    render_active_project_banner,
)
from core.inverter_catalog import (
    get_all_catalog_inverters,
    get_available_inverters,
    get_inverter_by_model
)
from core.dynamic_system_engine import (
    generate_inverter_combinations,
    validate_inverter_combination
)

st.set_page_config(
    page_title="Project & System Configuration — Eng. Aashir",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)
apply_custom_css()
init_project_state()

page_header(
    "Project & System Configuration",
    "Dynamic Solar System Design Engine — Define plant capacity, inverter combinations, PV modules, and site conditions",
    "⚙️"
)

render_active_project_banner()

proj = get_active_project()
active_panel = get_active_panel()
dynamic_sys = get_dynamic_system()

st.markdown("---")

# ---------------------------------------------------------------------------
# SECTION 1: System Capacity & Grid Parameters
# ---------------------------------------------------------------------------
st.markdown("### 1. System Capacity & Grid Interconnection")

col_cap, col_grid1, col_grid2, col_grid3 = st.columns([1.5, 1, 1, 1])

with col_cap:
    current_cap = float(proj.get("target_ac_capacity_kw", 5.0))
    capacity_kw = st.number_input(
        "Required System Capacity (kW AC) *",
        min_value=1.0,
        max_value=2500.0,
        value=current_cap,
        step=1.0,
        format="%.1f",
        help="Enter ANY required system continuous AC export capacity. Not restricted to fixed presets."
    )

with col_grid1:
    phase_options = [1, 3]
    default_phase = 1 if capacity_kw <= 5.0 else 3
    curr_phase = proj.get("grid_phases", default_phase)
    phase_idx = 0 if curr_phase == 1 else 1
    selected_phase = st.selectbox(
        "Grid Phases",
        phase_options,
        index=phase_idx,
        format_func=lambda p: "Single Phase (230V)" if p == 1 else "Three Phase (400V)",
        help="CEB/LECO standard: Single Phase <= 5 kW; Three Phase > 5 kW"
    )

with col_grid2:
    grid_voltage = 230.0 if selected_phase == 1 else 400.0
    st.number_input("Grid AC Voltage (V)", value=grid_voltage, disabled=True)

with col_grid3:
    install_type_opts = ["rooftop", "ground_mounted"]
    curr_inst = proj.get("installation_type", "rooftop")
    inst_idx = 0 if curr_inst == "rooftop" else 1
    installation_type = st.selectbox(
        "Installation Type",
        install_type_opts,
        index=inst_idx,
        format_func=lambda x: "Rooftop Mounted" if x == "rooftop" else "Ground Mounted"
    )

# Quick Presets for User Convenience
st.caption("Quick capacity benchmarks (click to apply):")
pre_cols = st.columns(7)
benchmarks = [
    (5.0, "5 kW (1P)"),
    (20.0, "20 kW (3P)"),
    (50.0, "50 kW (3P)"),
    (100.0, "100 kW (3P)"),
    (200.0, "200 kW (3P)"),
    (300.0, "300 kW (3P)"),
    (400.0, "400 kW (3P)")
]
for i, (b_val, b_lbl) in enumerate(benchmarks):
    if pre_cols[i].button(b_lbl, key=f"quick_bm_{int(b_val)}", use_container_width=True):
        proj["target_ac_capacity_kw"] = b_val
        proj["target_ac_kw"] = b_val
        proj["grid_phases"] = 1 if b_val <= 5.0 else 3
        proj["grid_voltage_v"] = 230.0 if b_val <= 5.0 else 400.0
        recalculate_system_state(target_kw=b_val, calculation_mode="AUTO")
        st.rerun()

st.markdown("---")

# ---------------------------------------------------------------------------
# SECTION 2: Dynamic Inverter Combination Engine (AUTO vs MANUAL MODE)
# ---------------------------------------------------------------------------
st.markdown("### 2. Dynamic Inverter Combination Engine")

calc_mode = st.radio(
    "Inverter Selection Operating Mode",
    ["AUTO MODE (Ranked Engineering Optimization)", "MANUAL MODE (Custom Inverter Selection & Unit Customizer)"],
    index=0 if get_calculation_mode() == "AUTO" else 1,
    horizontal=True,
    help="AUTO MODE generates all feasible combinations and ranks them using 6 engineering priorities. MANUAL MODE lets you choose alternatives or specify custom inverters with instant validation."
)

# Fetch all ranked combinations for this capacity & phase (up to 4 distinct models)
ranked_combos = generate_inverter_combinations(
    target_kw=capacity_kw,
    grid_phase=selected_phase,
    max_distinct_models=4
)

chosen_combination = None

if "AUTO" in calc_mode:
    set_calculation_mode("AUTO")
    st.info(f"⚡ **AUTO MODE ACTIVE:** Analyzing catalog inverters for **{capacity_kw:.1f} kW AC** ({'Single Phase' if selected_phase == 1 else 'Three Phase'}).")

    if not ranked_combos:
        st.error("No valid inverter combination found in catalog for this target capacity and phase.")
    else:
        # Display ranked options
        combo_labels = [f"{c['rank_tag']}: {c['label']}" for c in ranked_combos]
        selected_combo_idx = st.selectbox(
            "Ranked Inverter Combinations (Ranked by P1 Exact, P2 Compatibility, P3 Min Oversizing, P4 Min Units):",
            range(len(combo_labels)),
            format_func=lambda idx: combo_labels[idx],
            index=0
        )
        chosen_combination = ranked_combos[selected_combo_idx]

        # Combination KPI summary
        top_kpi1, top_kpi2, top_kpi3, top_kpi4 = st.columns(4)
        top_kpi1.metric("Total Inverter AC Rating", f"{chosen_combination['total_ac_kw']:.1f} kW AC")
        top_kpi2.metric("Inverter Unit Count", f"{chosen_combination['inverter_count']} Unit(s)")
        dev = chosen_combination['deviation_kw']
        dev_label = "Exact Match (0.0 kW)" if abs(dev) < 0.001 else (f"+{dev:.1f} kW (Oversized)" if dev > 0 else f"{dev:.1f} kW (Undersized)")
        top_kpi3.metric("Capacity Deviation", dev_label)
        top_kpi4.metric("Engineering Rank", chosen_combination['rank_tag'])

        # Detailed breakdown of units in selected combination
        st.markdown("**Combination Units Breakdown:**")
        unit_cols = st.columns(min(4, len(chosen_combination["breakdown"])))
        for u_idx, item in enumerate(chosen_combination["breakdown"]):
            inv_unit: Inverter = item["inverter"]
            unit_qty = item["quantity"]
            with unit_cols[u_idx % len(unit_cols)]:
                with st.container(border=True):
                    st.markdown(f"**{unit_qty} × {inv_unit.model}**")
                    st.caption(f"Rated AC: **{inv_unit.rated_ac_power_kw:.0f} kW** ({inv_unit.grid_type})")
                    st.write(f"• MPPTs: **{inv_unit.mppt_count}** ({inv_unit.string_inputs_per_mppt} str/MPPT)")
                    st.write(f"• MPPT Range: **{inv_unit.mppt_voltage_min_v:.0f} - {inv_unit.mppt_voltage_max_v:.0f} V**")
                    st.write(f"• Max DC: **{inv_unit.max_dc_voltage_v:.0f} V**")
                    st.write(f"• Max AC Current: **{inv_unit.max_ac_current_a:.1f} A**")

else:
    # MANUAL MODE
    set_calculation_mode("MANUAL")
    st.info("🛠️ **MANUAL MODE ACTIVE:** Select from generated alternative combinations or customize individual inverter models and quantities.")

    manual_tabs = st.tabs(["Select from Alternative Combinations", "Build Custom Inverter Units"])

    with manual_tabs[0]:
        if ranked_combos:
            man_combo_labels = [f"{c['rank_tag']}: {c['label']}" for c in ranked_combos]
            man_idx = st.selectbox(
                "Select Any Available Combination:",
                range(len(man_combo_labels)),
                format_func=lambda i: man_combo_labels[i],
                key="man_combo_select"
            )
            chosen_combination = ranked_combos[man_idx]
            st.success(f"Selected manual combination: **{chosen_combination['label']}**")
        else:
            st.warning("No preset combinations available.")

    with manual_tabs[1]:
        st.markdown("**Build Custom Inverter Allocation:**")
        available_invs = get_available_inverters(phase=selected_phase)
        inv_model_names = [f"{inv.model} ({inv.rated_ac_power_kw:.0f} kW AC, {inv.grid_type})" for inv in available_invs]

        man_col1, man_col2 = st.columns([3, 1])
        with man_col1:
            sel_inv1_idx = st.selectbox("Primary Inverter Model", range(len(inv_model_names)), format_func=lambda i: inv_model_names[i], key="man_inv1")
        with man_col2:
            sel_inv1_qty = st.number_input("Primary Inverter Qty", min_value=1, max_value=6, value=1, key="man_inv1_qty")

        add_second = st.checkbox("Add Secondary Inverter Model?", value=(capacity_kw not in [inv.rated_ac_power_kw for inv in available_invs]))

        custom_breakdown = [
            {"inverter": available_invs[sel_inv1_idx], "quantity": int(sel_inv1_qty), "unit_kw": available_invs[sel_inv1_idx].rated_ac_power_kw}
        ]

        if add_second:
            man_col3, man_col4 = st.columns([3, 1])
            with man_col3:
                sel_inv2_idx = st.selectbox("Secondary Inverter Model", range(len(inv_model_names)), format_func=lambda i: inv_model_names[i], index=min(2, len(available_invs)-1), key="man_inv2")
            with man_col4:
                sel_inv2_qty = st.number_input("Secondary Inverter Qty", min_value=1, max_value=4, value=1, key="man_inv2_qty")
            custom_breakdown.append(
                {"inverter": available_invs[sel_inv2_idx], "quantity": int(sel_inv2_qty), "unit_kw": available_invs[sel_inv2_idx].rated_ac_power_kw}
            )

        # Validate custom combination live
        val_res = validate_inverter_combination(custom_breakdown, capacity_kw, grid_phase=selected_phase)

        if val_res["is_valid"]:
            st.success(f"✓ **Valid Manual Configuration:** {val_res['message']}")
            # Format custom combination object
            tot_ac = val_res["total_ac_kw"]
            parts = [f"{item['quantity']} × {item['unit_kw']:.0f} kW" if item['quantity'] > 1 else f"{item['unit_kw']:.0f} kW" for item in custom_breakdown]
            lbl = " + ".join(parts) + f" ({tot_ac:.1f} kW AC)"
            chosen_combination = {
                "label": lbl,
                "total_ac_kw": tot_ac,
                "deviation_kw": tot_ac - capacity_kw,
                "is_exact": abs(tot_ac - capacity_kw) < 0.001,
                "inverter_count": sum(item["quantity"] for item in custom_breakdown),
                "breakdown": custom_breakdown,
                "score": 0.0,
                "rank_tag": "Manual Custom"
            }
        else:
            st.error(f"✕ **Invalid Configuration:** {val_res['message']}")
            for d in val_res["details"]:
                st.caption(f"• {d}")

st.markdown("---")

# ---------------------------------------------------------------------------
# SECTION 3: DC Solar PV Panel Selection
# ---------------------------------------------------------------------------
st.markdown("### 3. DC Solar PV Panel Selection")

approved_panels = get_approved_panels()
panel_mode = st.radio(
    "Panel Selection Mode",
    ["Approved Default Panels (Recommended)", "Manual Custom Panel Entry"],
    index=0,
    horizontal=True,
    help="Select from factory-approved Tier-1 modules (580W, 615W, 630W Default) or input manual datasheet specs"
)

selected_panel = active_panel

if panel_mode == "Approved Default Panels (Recommended)":
    current_wp = active_panel.rated_power_wp
    default_panel_idx = 0  # 580W
    for idx, ap in enumerate(approved_panels):
        if abs(ap.rated_power_wp - current_wp) < 2.0:
            default_panel_idx = idx
            break

    panel_choice_idx = st.selectbox(
        "Approved Module Wattage & Model *",
        range(len(approved_panels)),
        index=default_panel_idx,
        format_func=lambda i: f"⭐ {approved_panels[i].rated_power_wp} Wp — {approved_panels[i].manufacturer} {approved_panels[i].model} ({approved_panels[i].cell_technology})"
        if approved_panels[i].rated_power_wp == 580.0
        else f"{approved_panels[i].rated_power_wp} Wp — {approved_panels[i].manufacturer} {approved_panels[i].model} ({approved_panels[i].cell_technology})"
    )
    selected_panel = approved_panels[panel_choice_idx]

    c_p1, c_p2, c_p3, c_p4, c_p5 = st.columns(5)
    c_p1.metric("Rated Power", f"{selected_panel.rated_power_wp} Wp")
    c_p2.metric("Voc (Open Circuit)", f"{selected_panel.voc:.2f} V")
    c_p3.metric("Vmp (Max Power)", f"{selected_panel.vmp:.2f} V")
    c_p4.metric("Isc (Short Circuit)", f"{selected_panel.isc:.2f} A")
    c_p5.metric("Imp (Max Current)", f"{selected_panel.imp:.2f} A")

    with st.expander("🔍 Detailed Module Electrical & Mechanical Parameters", expanded=False):
        ec1, ec2, ec3, ec4 = st.columns(4)
        ec1.write(f"**Dimensions:** {selected_panel.length_m} m × {selected_panel.width_m} m × {selected_panel.thickness_mm} mm")
        ec1.write(f"**Weight:** {selected_panel.weight_kg} kg")
        ec2.write(f"**Temp Coeff Voc:** {selected_panel.temp_coeff_voc} %/°C")
        ec2.write(f"**Temp Coeff Vmp:** {selected_panel.temp_coeff_vmp} %/°C")
        ec3.write(f"**Temp Coeff Isc:** {selected_panel.temp_coeff_isc} %/°C")
        ec3.write(f"**Temp Coeff Pmax:** {selected_panel.temp_coeff_pmax} %/°C")
        ec4.write(f"**Max System Voltage:** {selected_panel.max_system_voltage} V")
        ec4.write(f"**Max Series Fuse:** {selected_panel.max_series_fuse} A")

else:
    st.info("Enter custom module parameters from manufacturer datasheet:")
    m_c1, m_c2 = st.columns(2)
    m_mfr = m_c1.text_input("Manufacturer", value="Custom Solar", key="man_p_mfr")
    m_model = m_c2.text_input("Model Name", value="CS-550M", key="man_p_model")

    m_c3, m_c4, m_c5, m_c6 = st.columns(4)
    m_wp = m_c3.number_input("Rated Power (Wp)", value=550.0, step=5.0, key="man_p_wp")
    m_voc = m_c4.number_input("Voc (V)", value=49.80, step=0.1, key="man_p_voc")
    m_vmp = m_c5.number_input("Vmp (V)", value=41.90, step=0.1, key="man_p_vmp")
    m_isc = m_c6.number_input("Isc (A)", value=14.00, step=0.1, key="man_p_isc")

    m_c7, m_c8, m_c9, m_c10 = st.columns(4)
    m_imp = m_c7.number_input("Imp (A)", value=13.13, step=0.1, key="man_p_imp")
    m_tc_voc = m_c8.number_input("Temp Coeff Voc (%/°C)", value=-0.26, step=0.01, format="%.3f", key="man_p_tcvoc")
    m_tc_pmax = m_c9.number_input("Temp Coeff Pmax (%/°C)", value=-0.34, step=0.01, format="%.3f", key="man_p_tcpmax")
    m_fuse = m_c10.number_input("Max Series Fuse (A)", value=25.0, step=5.0, key="man_p_fuse")

    m_c11, m_c12, m_c13, m_c14 = st.columns(4)
    m_len = m_c11.number_input("Length (m)", value=2.278, step=0.01, key="man_p_len")
    m_wid = m_c12.number_input("Width (m)", value=1.134, step=0.01, key="man_p_wid")
    m_thick = m_c13.number_input("Thickness (mm)", value=30.0, step=5.0, key="man_p_thick")
    m_weight = m_c14.number_input("Weight (kg)", value=28.0, step=1.0, key="man_p_wt")

    selected_panel = Panel(
        id="panel-manual-custom",
        manufacturer=m_mfr,
        model=m_model,
        rated_power_wp=m_wp,
        voc=m_voc,
        vmp=m_vmp,
        isc=m_isc,
        imp=m_imp,
        max_system_voltage=1500.0,
        max_series_fuse=m_fuse,
        temp_coeff_voc=m_tc_voc,
        temp_coeff_vmp=m_tc_voc,
        temp_coeff_isc=0.045,
        temp_coeff_pmax=m_tc_pmax,
        length_m=m_len,
        width_m=m_wid,
        thickness_mm=m_thick,
        weight_kg=m_weight,
        cell_technology="Monocrystalline",
        cell_count=144,
        source="manual"
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# SECTION 4: Project Context, Ambient Temperatures, and Cable Lengths
# ---------------------------------------------------------------------------
st.markdown("### 4. Project Context & Site Design Parameters")

site_col1, site_col2 = st.columns(2)
with site_col1:
    customer_name = st.text_input("Customer / Client Name *", value=proj.get("customer_name", "Solar Client"))
    site_name = st.text_input("Project / Site Name *", value=proj.get("site_name", "Rooftop PV System"))
    location = st.text_input("Site Location (City / Province)", value=proj.get("location", "Colombo, Sri Lanka"))

with site_col2:
    temp_c1, temp_c2 = st.columns(2)
    min_temp = temp_c1.number_input(
        "Min Ambient Design Temp (°C) *",
        value=float(proj.get("min_design_temp_c", -30.0)),
        step=1.0,
        help="Record lowest ambient temp at site. Used to calculate highest string Voc (Cold). Default -30 °C."
    )
    max_temp = temp_c2.number_input(
        "Max Ambient Design Temp (°C) *",
        value=float(proj.get("max_design_temp_c", 60.0)),
        step=1.0,
        help="Record highest ambient temp at site. Used to calculate lowest string Vmp (Hot). Default 60 °C."
    )

    ratio_c1, ratio_c2 = st.columns(2)
    dc_ac_target = ratio_c1.number_input(
        "Target DC/AC Oversizing Ratio",
        value=float(proj.get("dc_ac_ratio_preferred", 1.25)),
        min_value=1.0,
        max_value=1.60,
        step=0.05,
        help="Standard engineering oversizing is 1.20 to 1.30."
    )
    p_available = ratio_c2.number_input(
        "Max Module Space Available (Nos)",
        value=int(proj.get("panel_available_qty", 100)),
        min_value=1,
        step=1
    )

    ceb_export_tariff = st.number_input(
        "CEB Export Tariff (LKR/kWh) *",
        value=float(proj.get("ceb_export_tariff_lkr", 19.00)),
        min_value=0.0,
        step=0.50,
        format="%.2f",
        help="CEB standard feed-in tariff for Net Plus and export calculations. Default 19.00 LKR/kWh."
    )

# Cable Run Lengths
st.markdown("**Cable Run Estimates:**")
c_run1, c_run2, c_run3 = st.columns(3)
dc_run_m = c_run1.number_input("DC String Cable Run (m per string)", value=float(proj.get("dc_cable_length_m", 30.0)), step=5.0)
inv_ac_run_m = c_run2.number_input("Inverter-to-Main-DB Cable Run (m)", value=float(proj.get("ac_cable_length_m", 15.0)), step=5.0)
main_ac_run_m = c_run3.number_input("Main AC Export Cable Run (m)", value=float(proj.get("main_ac_cable_length_m", 20.0)), step=5.0)

# ---------------------------------------------------------------------------
# SECTION 5: Save, Recalculate & State Synchronization
# ---------------------------------------------------------------------------
st.markdown("---")

col_save, col_next = st.columns([1, 1])

with col_save:
    if st.button("💾 Apply & Recalculate System Engineering", type="primary", use_container_width=True):
        # Update project dict
        proj["target_ac_capacity_kw"] = capacity_kw
        proj["target_ac_kw"] = capacity_kw
        proj["grid_phases"] = selected_phase
        proj["grid_voltage_v"] = grid_voltage
        proj["installation_type"] = installation_type
        proj["customer_name"] = customer_name
        proj["site_name"] = site_name
        proj["location"] = location
        proj["min_design_temp_c"] = min_temp
        proj["max_design_temp_c"] = max_temp
        proj["dc_ac_ratio_preferred"] = dc_ac_target
        proj["panel_available_qty"] = p_available
        proj["ceb_export_tariff_lkr"] = ceb_export_tariff
        proj["dc_cable_length_m"] = dc_run_m
        proj["ac_cable_length_m"] = inv_ac_run_m
        proj["main_ac_cable_length_m"] = main_ac_run_m

        set_active_project(proj)
        set_active_panel(selected_panel)

        # Trigger full downstream recalculation
        new_sys = recalculate_system_state(
            target_kw=capacity_kw,
            panel=selected_panel,
            selected_combination=chosen_combination,
            calculation_mode="MANUAL" if "MANUAL" in calc_mode else "AUTO"
        )

        st.success(
            f"✅ Dynamic Recalculation Complete! Sized {new_sys['total_panels']} panels ({new_sys['actual_dc_kwp']:.2f} kWp) "
            f"across {len(new_sys['per_inverter_designs'])} inverter unit(s) for {new_sys['actual_ac_kw']:.1f} kW AC export."
        )
        st.rerun()

with col_next:
    if st.button("Proceed to Electrical Design ⚡ ➡️", use_container_width=True):
        try:
            st.switch_page("pages/3_⚡_Electrical_Design.py")
        except Exception:
            pass
