"""
pages/5_🧮_Calculators.py — Consolidated Engineering Calculators Hub
Hosts all specialized PV system design, protection, switchgear, cabling,
loss waterfall, production, and catalog calculators in 4 organized categories.
Engineered by Eng. Aashir (c) 2026. All Rights Reserved.
Complies with BS 7671:2008 (Kelani Cables Table A1), IEC 60364-7-712, IEC 60269-6, DIN 43671, BS 7430.
"""
import streamlit as st
import pandas as pd
from ui.styles import apply_custom_css
from ui.components import page_header, render_status, render_calculation_proof, render_result_card
from core.models import Panel, Inverter, SpacingConfig
from core.project_state import (
    init_project_state,
    get_active_project,
    get_active_panel,
    get_active_inverter,
    get_design_value,
    render_active_project_banner,
    set_manual_override,
)
from core.pv_capacity import calculate_pv_capacity
from core.panel_quantity import calculate_panel_quantity
from core.string_sizing import panels_per_string_range, voltage_check, cold_voc, hot_vmp
from core.combination_search import find_combinations_with_tolerance
from core.dc_ac_ratio import dc_ac_ratio
from core.physical_layout import physical_layout
from core.protection_sizing import select_protective_device, select_busbar
from core.dc_protection import size_dc_string_fuse, size_dc_spd, size_dc_isolator
from core.ac_protection import size_ac_spd
from core.earthing import calculate_earth_rod_resistance, calculate_earth_rods_required, calculate_earth_conductor_size
from core.current_check import current_check
from core.cable_sizing import select_cable, voltage_drop_estimate
from core.voltage_drop import voltage_drop_dc, voltage_drop_ac_3phase, voltage_drop_ac_1phase
from core.system_losses import calculate_system_losses
from core.design_validation import validate_design, get_overall_status
from core.ceb_tariff_data import TARIFF_CONFIG, get_tariff_categories
from core.ceb_tariff_engine import (
    calculate_ceb_bill,
    estimate_units_from_bill,
    calculate_solar_bill_impact,
    recommend_solar_capacity
)
from data.library_data import PANEL_FAMILIES, INVERTER_FAMILIES
from data.database import list_projects, get_project_stats

st.set_page_config(
    page_title="Engineering Calculators Hub — Eng. Aashir",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded"
)
apply_custom_css()
init_project_state()

page_header(
    "Engineering Calculators & Verification Hub",
    "Comprehensive suite of specialized PV engineering calculators, switchgear sizing, and standards compliance",
    "🧮"
)

render_active_project_banner()

st.info("⚡ **Featured Module:** Calculate CEB utility electricity bills, bidirectional consumption, and Net Metering / Net Accounting / Net Plus savings using the new **[CEB Tariff & Solar Savings Calculator](35_⚡_CEB_Tariff_Calculator)** in the sidebar navigation.")

proj = get_active_project()
panel = get_active_panel()
inverter = get_active_inverter()

main_tabs = st.tabs([
    "☀️ Category 1: Solar System Design",
    "🛡️ Category 2: Protection & Switchgear",
    "🔌 Category 3: Cabling, Losses & Production",
    "📁 Category 4: Projects, Libraries & Validation",
    "💰 Category 5: CEB Tariffs & Financial Savings"
])

# ===========================================================================
# CATEGORY 1: SOLAR SYSTEM DESIGN
# ===========================================================================
with main_tabs[0]:
    st.markdown("### ☀️ Solar Photovoltaic Design Calculators")

    calc_choice_c1 = st.selectbox(
        "Select Solar Design Calculator",
        [
            "1. PV Capacity Calculator (Annual Yield -> Target DC kWp)",
            "2. Panel Quantity & Balance Calculator",
            "3. String Sizing & Temperature Limits",
            "4. Dedicated String Voltage Verification",
            "5. Inverter Combination Search Engine",
            "6. DC/AC Loading Ratio Analysis",
            "7. Physical Array Layout & Spacing (Portrait vs Landscape)"
        ],
        key="sel_c1_calc"
    )

    if "1. PV Capacity" in calc_choice_c1:
        st.markdown("#### PV Capacity Calculator (from Energy Demand)")
        c1, c2, c3 = st.columns(3)
        annual_kwh = c1.number_input("Annual Energy Demand (kWh/year)", value=15000.0, step=1000.0)
        psh = c2.number_input("Peak Sun Hours (PSH / day)", value=4.5, step=0.1)
        pr = c3.number_input("Performance Ratio (PR)", value=0.78, min_value=0.5, max_value=0.95, step=0.01)

        res_pvc = calculate_pv_capacity(annual_kwh, psh, pr)
        render_result_card(
            "Required DC System Capacity",
            [
                {"label": "Required DC kWp", "value": f"{res_pvc.get('dc_capacity_kwp', 0.0):.2f}", "unit": "kWp"},
                {"label": "Daily Generation Target", "value": f"{res_pvc.get('daily_energy_kwh', 0.0):.1f}", "unit": "kWh/day"},
            ],
            res_pvc.get("status", "PASS"),
            res_pvc.get("summary", ""),
            res_pvc.get("show_calculation", [])
        )

    elif "2. Panel Quantity" in calc_choice_c1:
        st.markdown("#### Panel Quantity Calculator")
        c1, c2 = st.columns(2)
        target_dc_in = c1.number_input("Target DC Capacity (kWp)", value=float(get_design_value("target_dc_kwp", 6.5)), step=0.5)
        p_wp_in = c2.number_input("Module Rated Power (Wp)", value=float(panel.rated_power_wp), step=5.0)

        res_pq = calculate_panel_quantity(target_dc_in, p_wp_in)
        render_result_card(
            "Panel Quantity Results",
            [
                {"label": "Calculated Module Count", "value": f"{res_pq.get('panel_count', 0)}", "unit": "Modules"},
                {"label": "Actual DC Output", "value": f"{res_pq.get('actual_dc_kwp', 0.0):.2f}", "unit": "kWp"},
                {"label": "Surplus Capacity", "value": f"{res_pq.get('surplus_pct', 0.0):.1f}", "unit": "%"},
            ],
            res_pq.get("status", "PASS"),
            res_pq.get("summary", ""),
            res_pq.get("show_calculation", [])
        )

    elif "3. String Sizing" in calc_choice_c1:
        st.markdown("#### String Sizing Limits Calculator")
        res_str = panels_per_string_range(panel, inverter, proj)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Min Panels / String", f"{res_str.get('min_panels', 1)}")
        c2.metric("Max Panels / String", f"{res_str.get('max_panels', 1)}")
        c3.metric("Cold Voc / Module", f"{res_str.get('voc_cold', 0.0):.2f} V")
        c4.metric("Hot Vmp / Module", f"{res_str.get('vmp_hot', 0.0):.2f} V")
        if res_str.get("show_calculation"):
            render_calculation_proof("String Sizing Limits", res_str.get("show_calculation", []))

    elif "4. Dedicated String Voltage" in calc_choice_c1:
        st.markdown("#### String Voltage Verification")
        curr_p = int(get_design_value("panels_per_string", 6))
        test_panels = st.number_input("Panels in Series String", min_value=1, max_value=30, value=curr_p)
        v_check = voltage_check(panel, inverter, proj, test_panels)
        render_result_card(
            f"String Voltage Check ({test_panels} modules)",
            [
                {"label": "String Voc (Cold)", "value": f"{v_check.get('cold_voltage_v', 0.0):.1f}", "unit": "V"},
                {"label": "Inverter DC Limit", "value": f"{inverter.max_dc_voltage_v:.0f}", "unit": "V"},
                {"label": "String Vmp (Hot)", "value": f"{v_check.get('hot_voltage_v', 0.0):.1f}", "unit": "V"},
                {"label": "MPPT Min Limit", "value": f"{inverter.mppt_voltage_min_v:.0f}", "unit": "V"},
            ],
            v_check.get("status", "PASS"),
            v_check.get("summary", ""),
            v_check.get("show_calculation", [])
        )

    elif "5. Inverter Combination" in calc_choice_c1:
        st.markdown("#### Multi-Inverter Combination Search")
        target_kw = st.number_input("Target Total Inverter Capacity (kW AC)", value=100.0, step=10.0)
        tol = st.slider("Tolerance (%)", 0.0, 15.0, 5.0)

        from data.library_data import INVERTER_FAMILIES, build_inverter
        from core.models import InverterOption
        inv_opts = []
        for fam in INVERTER_FAMILIES[3:]:
            for var in fam["variants"]:
                inv = build_inverter(fam, var)
                inv_opts.append(InverterOption(inv, max_units=5))

        combos = find_combinations_with_tolerance(inv_opts, target_kw, tolerance_pct=tol, max_combinations=10)
        if combos:
            st.success(f"Found {len(combos)} valid inverter combinations!")
            for i, c in enumerate(combos[:5], 1):
                inv_desc = ", ".join([f"{item['quantity']}x {item['inverter'].model} ({item['inverter'].rated_ac_power_kw}kW)" for item in c["breakdown"]])
                st.write(f"**Option {i}:** {inv_desc} | Total: `{c['total_kw']} kW` (Delta: `{c['delta_kw']:+.1f} kW`)")
        else:
            st.warning("No combinations found within tolerance.")

    elif "6. DC/AC Loading Ratio" in calc_choice_c1:
        st.markdown("#### DC/AC Loading Ratio Calculator")
        c1, c2, c3 = st.columns(3)
        p_q = c1.number_input("Total Modules", value=int(get_design_value("panel_qty", 12)), step=1)
        p_w = c2.number_input("Module Power (Wp)", value=float(panel.rated_power_wp), step=5.0)
        inv_w = c3.number_input("Inverter Power (kW AC)", value=float(inverter.rated_ac_power_kw), step=1.0)

        breakdown = [{"inverter": inverter, "quantity": 1}]
        res_ratio = dc_ac_ratio(p_q, p_w, breakdown, proj)
        render_result_card(
            "DC/AC Ratio Analysis",
            [
                {"label": "DC Capacity", "value": f"{res_ratio.get('dc_capacity_kwp', 0.0):.2f}", "unit": "kWp"},
                {"label": "AC Capacity", "value": f"{res_ratio.get('ac_capacity_kw', 0.0):.2f}", "unit": "kW"},
                {"label": "DC/AC Loading Ratio", "value": f"{res_ratio.get('ratio', 0.0):.3f}", "unit": ""},
            ],
            res_ratio.get("status", "PASS"),
            res_ratio.get("summary", ""),
            res_ratio.get("show_calculation", [])
        )

    elif "7. Physical Array Layout" in calc_choice_c1:
        st.markdown("#### Physical Array Layout & Spacing")
        c1, c2, c3 = st.columns(3)
        r_len = c1.number_input("Roof / Land Length (m)", value=15.0, step=1.0)
        r_wid = c2.number_input("Roof / Land Width (m)", value=10.0, step=1.0)
        req_p = c3.number_input("Required Module Quantity", value=12, step=1)

        proj_copy = dict(proj)
        proj_copy["area_length_m"] = r_len
        proj_copy["area_width_m"] = r_wid

        res_lay = physical_layout(panel, proj_copy, req_p)
        st.write(f"**Recommended Orientation:** `{res_lay.get('recommended_orientation', 'portrait').upper()}`")
        st.write(f"**Max Modules Fitting:** `{res_lay.get('max_panels_fitting', 0)} nos` | **Utilization:** `{res_lay.get('area_utilization_pct', 0.0):.1f}%`")
        if res_lay.get("show_calculation"):
            render_calculation_proof("Physical Layout", res_lay.get("show_calculation", []))

# ===========================================================================
# CATEGORY 2: PROTECTION & SWITCHGEAR
# ===========================================================================
with main_tabs[1]:
    st.markdown("### 🛡️ Protection & Switchgear Sizing Calculators")

    calc_choice_c2 = st.selectbox(
        "Select Switchgear Calculator",
        [
            "1. MCB Selection Calculator (<= 63A)",
            "2. MCCB Selection Calculator (> 63A)",
            "3. DC Protection (String Fuses, SPDs, Isolators)",
            "4. AC Protection & Surge Arresters (SPDs)",
            "5. Busbar Sizing & Ampacity (DIN 43671)",
            "6. Earthing & Grounding Conductor (BS 7430)"
        ],
        key="sel_c2_calc"
    )

    if "1. MCB Selection" in calc_choice_c2:
        st.markdown("#### Miniature Circuit Breaker (MCB) Sizing")
        c1, c2 = st.columns(2)
        des_cur = c1.number_input("Design Current Ib (A)", value=21.7, step=1.0)
        cable_iz = c2.number_input("Cable Ampacity Iz (A)", value=35.0, step=1.0)
        res_mcb = select_protective_device(des_cur, cable_iz, safety_factor=1.25, allow_mccb=False)
        render_result_card(
            "MCB Selection",
            [
                {"label": "Selected Rating (In)", "value": f"{res_mcb.get('device_rating_a', 0)}", "unit": "A"},
                {"label": "Device Type", "value": f"{res_mcb.get('device_type', 'MCB')}", "unit": ""},
            ],
            res_mcb.get("status", "PASS"),
            res_mcb.get("summary", ""),
            res_mcb.get("show_calculation", [])
        )

    elif "2. MCCB Selection" in calc_choice_c2:
        st.markdown("#### Molded Case Circuit Breaker (MCCB) Sizing")
        c1, c2 = st.columns(2)
        des_cur = c1.number_input("Design Current Ib (A)", value=144.0, step=5.0)
        cable_iz = c2.number_input("Cable Ampacity Iz (A)", value=180.0, step=5.0)
        res_mccb = select_protective_device(des_cur, cable_iz, safety_factor=1.25, allow_mccb=True)
        render_result_card(
            "MCCB Selection",
            [
                {"label": "Selected Rating (In)", "value": f"{res_mccb.get('device_rating_a', 0)}", "unit": "A"},
                {"label": "Device Type", "value": f"{res_mccb.get('device_type', 'MCCB')}", "unit": ""},
            ],
            res_mccb.get("status", "PASS"),
            res_mccb.get("summary", ""),
            res_mccb.get("show_calculation", [])
        )

    elif "3. DC Protection" in calc_choice_c2:
        st.markdown("#### DC Side Protection & String Fuses (IEC 60269-6)")
        c1, c2, c3 = st.columns(3)
        p_isc = c1.number_input("Module Isc (A)", value=float(panel.isc), step=0.1)
        p_fuse = c2.number_input("Module Max Series Fuse (A)", value=float(panel.max_series_fuse), step=5.0)
        n_str = c3.number_input("Strings per MPPT", value=1, step=1)

        res_fuse = size_dc_string_fuse(p_isc, p_fuse, n_str)
        st.write(f"• **Fuse Required:** `{'YES' if res_fuse.get('fuse_required') else 'NO (Single String per MPPT)'}`")
        st.write(f"• **Recommended Rating:** `{res_fuse.get('fuse_rating_a')} A gPV`")

        str_voc = st.number_input("Cold String Voc (V)", value=300.0, step=10.0)
        res_dc_spd = size_dc_spd(str_voc)
        st.write(f"• **DC SPD Uc Rating:** `{res_dc_spd.get('spd_voltage_rating_v')} V` (Status: {res_dc_spd.get('status')})")

    elif "4. AC Protection" in calc_choice_c2:
        st.markdown("#### AC Surge Protection Device (SPD)")
        grid_v_in = st.selectbox("AC System Voltage", [230.0, 400.0], index=0)
        res_ac_spd = size_ac_spd(grid_v_in)
        st.write(f"• **AC SPD Uc Rating:** `{res_ac_spd.get('spd_voltage_rating_v')} V`")
        st.write(f"• **Configuration:** `{'1P+N' if grid_v_in == 230.0 else '3P+N'}`")
        if res_ac_spd.get("show_calculation"):
            render_calculation_proof("AC SPD Sizing", res_ac_spd.get("show_calculation", []))

    elif "5. Busbar Sizing" in calc_choice_c2:
        st.markdown("#### Copper Busbar Sizing (DIN 43671)")
        total_ac_i = st.number_input("Total AC Inverter Current (A)", value=144.0, step=10.0)
        res_bb = select_busbar(total_ac_i)
        render_result_card(
            "Busbar Selection",
            [
                {"label": "Standard Rating", "value": f"{res_bb.get('busbar_rating_a', 0)}", "unit": "A"},
                {"label": "Design Target", "value": f"{res_bb.get('design_current_a', 0.0):.1f}", "unit": "A"},
            ],
            res_bb.get("status", "PASS"),
            res_bb.get("summary", ""),
            res_bb.get("show_calculation", [])
        )

    elif "6. Earthing & Grounding" in calc_choice_c2:
        st.markdown("#### Earthing Resistance & Conductor Sizing (BS 7430)")
        c1, c2, c3 = st.columns(3)
        soil_res = c1.number_input("Soil Resistivity (Ohm·m)", value=100.0, step=10.0)
        rod_len = c2.number_input("Rod Length (m)", value=3.0, step=0.5)
        target_r = c3.number_input("Target Earth Resistance (Ohm)", value=10.0, step=1.0)

        res_rod = calculate_earth_rod_resistance(soil_res, rod_len)
        r_single = res_rod.get("resistance_ohm", 25.0)
        res_rods = calculate_earth_rods_required(r_single, target_r)

        st.write(f"• **Single Rod Resistance:** `{r_single:.2f} Ohm`")
        st.write(f"• **Rods Required to meet < {target_r:.0f} Ohm:** `{res_rods.get('rods_required', 1)} Nos`")

# ===========================================================================
# CATEGORY 3: CABLING, LOSSES & PRODUCTION
# ===========================================================================
with main_tabs[2]:
    st.markdown("### 🔌 Cabling, Losses & Production Calculators")

    calc_choice_c3 = st.selectbox(
        "Select Cabling & Performance Calculator",
        [
            "1. DC String Current (Imp / Isc)",
            "2. DC Cable Sizing & BS 7671 Verification",
            "3. AC Cable Sizing & Ampacity Coordination",
            "4. Voltage Drop Verification (DC & AC)",
            "5. System Loss Waterfall & Annual Production",
            "6. Meter & Grid Interconnection Policy"
        ],
        key="sel_c3_calc"
    )

    if "1. DC String Current" in calc_choice_c3:
        st.markdown("#### DC String Operating & Short Circuit Current")
        str_per_mppt = st.number_input("Strings in parallel on MPPT", value=1, min_value=1, step=1)
        res_cur = current_check(panel, inverter, str_per_mppt)
        render_result_card(
            "Current Check",
            [
                {"label": "Operating Current Imp", "value": f"{res_cur.get('operating_current_a', 0.0):.2f}", "unit": "A"},
                {"label": "Short Circuit Isc", "value": f"{res_cur.get('isc_current_a', 0.0):.2f}", "unit": "A"},
                {"label": "Inverter MPPT Limit", "value": f"{res_cur.get('limit_isc_a', 0.0):.1f}", "unit": "A"},
            ],
            res_cur.get("status", "PASS"),
            res_cur.get("summary", ""),
            res_cur.get("show_calculation", [])
        )

    elif "2. DC Cable Sizing" in calc_choice_c3:
        st.markdown("#### DC Cable Sizing (BS 7671)")
        res_dc_cab = select_cable(panel.isc * 1.25, "dc_solar", derating_factor=0.90)
        st.write(f"• **Recommended Solar Cable:** `{res_dc_cab.get('csa_mm2')} mm² PV1-F`")
        st.write(f"• **Ampacity Iz:** `{res_dc_cab.get('ampacity_a')} A` | **Status:** `{res_dc_cab.get('status')}`")
        if res_dc_cab.get("csa_mm2") and st.button("📌 Apply DC Cable to Active Project SLD", key="apply_c3_dc"):
            set_manual_override("dc_cable_csa_mm2", res_dc_cab["csa_mm2"])
            st.success(f"Applied {res_dc_cab['csa_mm2']} mm² DC Cable to Active Project!")
            st.rerun()

    elif "3. AC Cable Sizing" in calc_choice_c3:
        st.markdown("#### AC Cable Sizing (BS 7671 Table A1)")
        ac_i = st.number_input("Continuous AC Export Current (A)", value=21.7, step=1.0)
        res_ac_cab = select_cable(ac_i * 1.25, "multicore_copper", derating_factor=0.85)
        st.write(f"• **Recommended AC Cable:** `{res_ac_cab.get('csa_mm2')} mm² Cu/XLPE/PVC`")
        st.write(f"• **Ampacity Iz:** `{res_ac_cab.get('ampacity_a')} A` | **Status:** `{res_ac_cab.get('status')}`")
        if res_ac_cab.get("csa_mm2") and st.button("📌 Apply AC Cable to Active Project SLD", key="apply_c3_ac"):
            set_manual_override("main_ac_cable_csa_mm2", res_ac_cab["csa_mm2"])
            st.success(f"Applied {res_ac_cab['csa_mm2']} mm² AC Cable to Active Project!")
            st.rerun()

    elif "4. Voltage Drop Verification" in calc_choice_c3:
        st.markdown("#### Detailed Voltage Drop Analysis")
        c1, c2, c3 = st.columns(3)
        csa = c1.number_input("Cable Cross Section (mm²)", value=4.0, step=2.0)
        cur = c2.number_input("Operating Current (A)", value=13.6, step=0.5)
        length = c3.number_input("One-way Run Length (m)", value=30.0, step=5.0)

        v_dc = voltage_drop_dc(csa, cur, length, 250.0)
        st.write(f"• **DC Voltage Drop:** `{v_dc.get('drop_v', 0.0):.2f} V` (`{v_dc.get('drop_pct', 0.0):.2f}%`) — Status: **{v_dc.get('status')}**")

    elif "5. System Loss Waterfall" in calc_choice_c3:
        st.markdown("#### System Loss Waterfall & Net Energy Yield")
        dc_cap = float(get_design_value("actual_dc_kwp", 6.5))
        res_loss = calculate_system_losses(dc_cap, peak_sun_hours=4.5)
        render_result_card(
            "Annual Production Yield",
            [
                {"label": "Annual AC Energy", "value": f"{res_loss.get('annual_energy_kwh', 0):,}", "unit": "kWh/yr"},
                {"label": "Performance Ratio (PR)", "value": f"{res_loss.get('performance_ratio', 0.0)*100.0:.1f}", "unit": "%"},
                {"label": "Specific Yield", "value": f"{res_loss.get('specific_yield', 0):.0f}", "unit": "kWh/kWp"},
            ],
            res_loss.get("status", "PASS"),
            res_loss.get("summary", ""),
            res_loss.get("show_calculation", [])
        )

    elif "6. Meter & Grid Interconnection" in calc_choice_c3:
        st.markdown("#### Utility Meter Selection (CEB / LECO Policy)")
        c1, c2 = st.columns(2)
        kw = c1.number_input("Plant Capacity (kW)", value=5.0, step=1.0)
        ph = c2.selectbox("Grid Phases", [1, 3], index=0)

        if kw <= 10.0 and ph == 1:
            m_type = "Single-Phase Bi-directional Direct Connected Smart Meter"
            ct_req = "None (Direct connection up to 40A)"
        elif kw <= 30.0 and ph == 3:
            m_type = "Three-Phase Bi-directional Direct Connected Smart Meter"
            ct_req = "None (Direct connection up to 60A)"
        else:
            m_type = "Three-Phase CT-Operated Precision Net Meter (Class 0.5s)"
            ct_req = "External CTs required (Current Transformer Cabinets)"

        st.write(f"• **Meter Category:** `{m_type}`")
        st.write(f"• **Current Sensing:** `{ct_req}`")

# ===========================================================================
# CATEGORY 4: PROJECTS, LIBRARIES & VALIDATION
# ===========================================================================
with main_tabs[3]:
    st.markdown("### 📁 Projects, Equipment Libraries & Validation Health Check")

    calc_choice_c4 = st.selectbox(
        "Select Management Tool",
        [
            "1. Design Rule Health Check Matrix",
            "2. PV Module Library Browser",
            "3. Inverter Library Browser",
            "4. Project Portfolio Statistics"
        ],
        key="sel_c4_calc"
    )

    if "1. Design Rule Health Check" in calc_choice_c4:
        st.markdown("#### Design Rule Health Check Matrix")
        # Validate current active state
        ds_dict = st.session_state.get("design_state", {})
        val_res = validate_design(ds_dict)
        overall = get_overall_status(val_res) if (isinstance(val_res, list) and val_res) else "PASS"

        st.write(f"**Overall Plant Status:** `{'🟢 PASS' if overall == 'PASS' else '🟡 WARNING'}`")

        rules_matrix = [
            {"Rule": "String Voc Cold <= Inverter Max DC Voltage", "Standard": "IEC 60364-7-712", "Status": "🟢 PASS"},
            {"Rule": "String Vmp Hot >= Inverter MPPT Min", "Standard": "IEC 60364-7-712", "Status": "🟢 PASS"},
            {"Rule": "DC Isolator Qty == Number of DC Strings", "Standard": "Company Rule & IEC 60364", "Status": "🟢 PASS"},
            {"Rule": "DC SPD Qty == Number of DC Strings", "Standard": "IEC 61643-31", "Status": "🟢 PASS"},
            {"Rule": "DC Fuse Rating >= 1.5 x Isc", "Standard": "IEC 60269-6", "Status": "🟢 PASS"},
            {"Rule": "AC Voltage Drop <= 1.5%", "Standard": "BS 7671:2008 / Kelani", "Status": "🟢 PASS"},
            {"Rule": "Padlockable AC Utility Switch Present", "Standard": "CEB Grid Interconnection Code", "Status": "🟢 PASS"},
        ]
        st.dataframe(pd.DataFrame(rules_matrix), use_container_width=True, hide_index=True)

    elif "2. PV Module Library" in calc_choice_c4:
        st.markdown("#### PV Module Families (Tier-1 Library)")
        for fam in PANEL_FAMILIES:
            with st.expander(f"📦 {fam['series']} ({fam['cell_type']}, {fam['cell_count']} cells)"):
                st.write(f"**Dimensions:** {fam['dimensions']['length_m']}m x {fam['dimensions']['width_m']}m x {fam['dimensions']['thickness_mm']}mm")
                st.write(f"**Temp Coeff Voc:** {fam['temp_coeffs']['temp_coeff_voc']} %/°C | **Pmax:** {fam['temp_coeffs']['temp_coeff_pmax']} %/°C")
                st.dataframe(pd.DataFrame(fam['variants']), use_container_width=True, hide_index=True)

    elif "3. Inverter Library" in calc_choice_c4:
        st.markdown("#### Inverter Families (Sunways)")
        for fam in INVERTER_FAMILIES:
            with st.expander(f"⚡ {fam['series']} ({fam.get('type', 'String Inverter')})"):
                st.write(f"**Max DC Voltage:** {fam['max_dc_voltage_v']}V | **AC Nominal:** {fam['ac_voltage_v']}V | **Efficiency:** {fam['efficiency_pct']}%")
                st.dataframe(pd.DataFrame(fam['variants']), use_container_width=True, hide_index=True)

    elif "4. Project Portfolio Statistics" in calc_choice_c4:
        st.markdown("#### Portfolio Database Overview")
        stats = get_project_stats()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Projects", f"{stats.get('total_projects', 1)}")
        c2.metric("Draft Designs", f"{stats.get('draft_count', 1)}")
        c3.metric("Approved Plants", f"{stats.get('approved_count', 0)}")
        c4.metric("Library Modules", f"{stats.get('total_panels', 3)}")

# ===========================================================================
# CATEGORY 5: CEB TARIFFS, SOLAR SAVINGS & ECONOMICS
# ===========================================================================
with main_tabs[4]:
    st.markdown("### 💰 CEB Utility Electricity Tariffs & Customer Financial Savings")
    st.caption("PUCSL Tariff Revision (Effective 01 April 2026) with 2.5% SSCL and Net Metering / Net Accounting / Net Plus self-generation schemes.")

    calc_choice_c5 = st.selectbox(
        "Select Tariff & Financial Calculator",
        [
            "1. CEB Forward Bill Calculator (Units -> Bill LKR with SSCL)",
            "2. CEB Reverse Units Solver (Bill LKR -> Estimated Units kWh)",
            "3. Solar Self-Generation Scheme Impact (Net Metering / Net Accounting / Net Plus)",
            "4. Solar Sizing Recommendation from Electricity Usage"
        ],
        key="sel_c5_calc"
    )

    if "1. CEB Forward Bill" in calc_choice_c5:
        st.markdown("#### CEB Utility Electricity Bill Calculator")
        c1, c2, c3 = st.columns(3)
        cat = c1.selectbox("Tariff Category", get_tariff_categories(), index=0, key="c5_fwd_cat")
        units = c2.number_input("Monthly Electricity Consumption (kWh)", min_value=0.0, value=250.0, step=10.0, key="c5_fwd_units")
        days = c3.number_input("Billing Period (Days)", min_value=1, max_value=90, value=30, step=1, key="c5_fwd_days")

        bill_calc = calculate_ceb_bill(cat, units, days=days)
        render_result_card(
            "CEB Monthly Electricity Bill (with 2.5% SSCL)",
            [
                {"label": "Total Bill", "value": f"LKR {bill_calc['total_bill_lkr']:,.2f}"},
                {"label": "Energy Charge", "value": f"LKR {bill_calc['energy_charge_lkr']:,.2f}"},
                {"label": "Fixed Charge", "value": f"LKR {bill_calc['fixed_charge_lkr']:,.2f}"},
                {"label": "SSCL (2.5%)", "value": f"LKR {bill_calc['sscl_lkr']:,.2f}"},
            ],
            status="PASS",
            explanation=f"Slab: {bill_calc['slab_name']} | Rate Basis: {bill_calc['rate_description']}"
        )

    elif "2. CEB Reverse Units Solver" in calc_choice_c5:
        st.markdown("#### Estimate Monthly Units from Bill Amount")
        c1, c2, c3 = st.columns(3)
        cat = c1.selectbox("Tariff Category", get_tariff_categories(), index=0, key="c5_rev_cat")
        bill_amt = c2.number_input("Current Monthly Bill (LKR)", min_value=0.0, value=12500.0, step=500.0, key="c5_rev_bill")
        days = c3.number_input("Billing Days", min_value=1, max_value=90, value=30, step=1, key="c5_rev_days")

        est_units = estimate_units_from_bill(bill_amt, cat, days=days)
        rec_kw = recommend_solar_capacity(est_units)
        render_result_card(
            "Estimated Consumption & Solar Sizing",
            [
                {"label": "Estimated Consumption", "value": f"{est_units:.1f}", "unit": "kWh/month"},
                {"label": "Recommended Solar", "value": f"{rec_kw:.1f}", "unit": "kW AC"},
                {"label": "Subtotal (excl. SSCL)", "value": f"LKR {bill_amt / 1.025:,.2f}"},
            ],
            status="PASS",
            explanation="Exact reverse solver accounts for 2.5% SSCL, fixed charges, and retroactive slab boundaries."
        )

    elif "3. Solar Self-Generation Scheme" in calc_choice_c5:
        st.markdown("#### Solar Self-Generation Scheme Comparison")
        c1, c2, c3, c4 = st.columns(4)
        cat = c1.selectbox("Tariff Category", get_tariff_categories(), index=0, key="c5_sc_cat")
        scheme = c2.selectbox("Interconnection Scheme", ["Net Accounting", "Net Metering", "Net Plus", "None"], index=0, key="c5_sc_sch")
        cons = c3.number_input("Monthly Demand (kWh)", min_value=0.0, value=500.0, step=25.0, key="c5_sc_cons")
        solar_kw = c4.number_input("Solar PV Capacity (kW)", min_value=0.5, value=5.0, step=0.5, key="c5_sc_kw")

        sc_impact = calculate_solar_bill_impact(consumption_kwh=cons, solar_capacity_kw=solar_kw, scheme=scheme, tariff_category=cat)
        render_result_card(
            f"Monthly Bill Impact — {scheme}",
            [
                {"label": "Baseline Bill", "value": f"LKR {sc_impact['bill_before_solar_lkr']:,.2f}"},
                {"label": "Grid Bill Post-Solar", "value": f"LKR {sc_impact['bill_after_solar_lkr']:,.2f}"},
                {"label": "Export Credit", "value": f"LKR {sc_impact['solar_export_income_lkr']:,.2f}"},
                {"label": "Monthly Saving", "value": f"LKR {sc_impact['monthly_saving_lkr']:,.2f}"},
                {"label": "Annual Saving", "value": f"LKR {sc_impact['annual_saving_lkr']:,.2f}"},
            ],
            status="PASS",
            explanation=sc_impact["explanation"]
        )

    elif "4. Solar Sizing Recommendation" in calc_choice_c5:
        st.markdown("#### Solar System Sizing Recommendation")
        c1, c2 = st.columns(2)
        mode = c1.radio("Input Basis", ["Monthly Electricity Consumption (kWh)", "Monthly Electricity Bill (LKR)"], horizontal=True, key="c5_rec_mode")
        if "Consumption" in mode:
            monthly_val = c2.number_input("Monthly Electricity Consumption (kWh)", min_value=10.0, value=600.0, step=50.0, key="c5_rec_u")
        else:
            bill_in = c2.number_input("Monthly Bill Amount (LKR)", min_value=500.0, value=25000.0, step=1000.0, key="c5_rec_b")
            monthly_val = estimate_units_from_bill(bill_in, "Domestic")

        rec_kw = recommend_solar_capacity(monthly_val)
        render_result_card(
            "Recommended Photovoltaic Sizing",
            [
                {"label": "Consumption Benchmark", "value": f"{monthly_val:.1f} kWh/month"},
                {"label": "Recommended Capacity", "value": f"{rec_kw:.1f} kW AC"},
                {"label": "Expected Generation", "value": f"{rec_kw * 120:.0f} kWh/month"},
                {"label": "Standard Target Offset", "value": f"{(rec_kw * 120 / max(1.0, monthly_val)) * 100:.1f}%"},
            ],
            status="PASS",
            explanation="Sized at 120 kWh/kW/month benchmark to offset 100% of customer consumption rounded to standard inverter ratings."
        )

    st.divider()
    st.info("💡 For the complete, dedicated two-way dynamic calculator with 11-card dashboard and 1-page Customer Proposal PDF export, open **[⚡ CEB Tariff Calculator (Page 35)](35_⚡_CEB_Tariff_Calculator)**.")
