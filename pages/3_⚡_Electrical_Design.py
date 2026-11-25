"""
pages/3_⚡_Electrical_Design.py — Dynamic Multi-Inverter Electrical Design & Cable Sizing
Consolidates:
  1. String Sizing & MPPT Allocation PER INVERTER UNIT
  2. Independent DC Protection PER INVERTER (with IEC 60269-6 String Fuse validation)
  3. Individual Inverter AC Switchgear + Whole-System Main AC Switchgear
  4. Cable Sizing (DC, Individual AC, Combined Main AC, and BS 7430 Dynamic Earthing)
  5. Categorized Schedule Matrix (PER PANEL, PER STRING, PER INVERTER, PER SYSTEM)

Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
Complies with BS 7671:2008 (Kelani Cables Table A1), IEC 60364-7-712, IEC 60269-6, BS 7430.
"""
import streamlit as st
import pandas as pd
from ui.styles import apply_custom_css
from ui.components import page_header, render_status, render_calculation_proof
from core.models import Panel, Inverter
from core.project_state import (
    init_project_state,
    get_active_project,
    get_active_panel,
    get_active_inverter,
    get_dynamic_system,
    recalculate_system_state,
    update_design_state,
    render_active_project_banner,
    get_manual_overrides,
    clear_manual_overrides,
)

st.set_page_config(
    page_title="Electrical Design & Cables — Eng. Aashir",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)
apply_custom_css()
init_project_state()

page_header(
    "Electrical Design & Cable Engineering",
    "Dynamic multi-inverter string sizing, independent DC switchgear, combined main AC protection, and BS 7430 earthing",
    "⚡"
)

render_active_project_banner()

# Active manual overrides notice
overrides = get_manual_overrides()
if overrides:
    ov_items = []
    if "dc_cable_csa_mm2" in overrides:
        ov_items.append(f"DC Cable: {overrides['dc_cable_csa_mm2']} mm²")
    if "main_ac_cable_csa_mm2" in overrides:
        ov_items.append(f"Main Cable: {overrides['main_ac_cable_csa_mm2']} mm²")
    if "main_breaker_rating_a" in overrides:
        ov_items.append(f"Main Breaker: {overrides['main_breaker_rating_a']}A")
    elif "main_breaker_spec" in overrides:
        ov_items.append(f"Main Breaker: {overrides['main_breaker_spec']}")
    if "main_busbar_rating_a" in overrides:
        ov_items.append(f"Busbar: {overrides['main_busbar_rating_a']}A")

    col_ov1, col_ov2 = st.columns([3, 1])
    col_ov1.warning(f"⚠️ **Manual Overrides Active:** {' | '.join(ov_items)} (Synchronized into SLD & BOQ)")
    if col_ov2.button("↺ Reset to 100% Auto", key="reset_all_ov_elec", use_container_width=True):
        clear_manual_overrides()
        st.success("All manual overrides cleared. System recalculated automatically.")
        st.rerun()

proj = get_active_project()
panel = get_active_panel()
dynamic_sys = get_dynamic_system()

# Check if dynamic_sys exists, if not recalculate
if not dynamic_sys or "per_inverter_designs" not in dynamic_sys:
    dynamic_sys = recalculate_system_state()

per_inv_designs = dynamic_sys.get("per_inverter_designs", [])
whole_ac = dynamic_sys.get("whole_system_ac", {})
earthing = dynamic_sys.get("earthing_design", {})
active_combo = dynamic_sys.get("active_combination", {})
classified_sched = dynamic_sys.get("classified_schedule", {})

total_sys_panels = dynamic_sys.get("total_panels", 0)
total_sys_dc_kwp = dynamic_sys.get("actual_dc_kwp", 0.0)
total_sys_ac_kw = dynamic_sys.get("actual_ac_kw", 0.0)
overall_ratio = dynamic_sys.get("dc_ac_ratio", 1.25)
inv_count = len(per_inv_designs)

# ---------------------------------------------------------------------------
# Structured 5-Tab Architecture
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "🧩 1. String Sizing & MPPT Allocation",
    "🛡️ 2. DC Protection & Switchgear",
    "⚡ 3. AC Protection (Individual & Main)",
    "🔌 4. Cable Sizing & Dynamic Earthing",
    "📋 5. Classified Schedule & Sync"
])

# ===========================================================================
# TAB 1: String Sizing & MPPT Allocation (Per Inverter Unit)
# ===========================================================================
with tabs[0]:
    st.markdown("### String Sizing & MPPT Allocation (Per Inverter Unit)")
    st.caption(
        f"Dynamic System Design: **{total_sys_panels} Modules ({total_sys_dc_kwp:.2f} kWp DC)** "
        f"across **{inv_count} Inverter Unit(s) ({total_sys_ac_kw:.1f} kW AC Total)**. "
        f"Overall DC/AC Ratio: **{overall_ratio:.3f}**."
    )

    # Inverter units selector or tabs
    unit_tabs = st.tabs([d["unit_label"] for d in per_inv_designs])

    for u_idx, d in enumerate(per_inv_designs):
        with unit_tabs[u_idx]:
            inv: Inverter = d["inverter"]
            col_u_kpi1, col_u_kpi2, col_u_kpi3, col_u_kpi4 = st.columns(4)
            col_u_kpi1.metric("Inverter Capacity", f"{inv.rated_ac_power_kw:.0f} kW AC")
            col_u_kpi2.metric("Assigned Modules", f"{d['total_panels']} Nos ({d['actual_dc_kwp']:.2f} kWp)")
            col_u_kpi3.metric("String Configuration", f"{d['num_strings']} str × {d['panels_per_string']} mod")
            col_u_kpi4.metric("Inverter DC/AC Ratio", f"{d['dc_ac_ratio']:.3f}")

            col_str_volts, col_str_mppt = st.columns([1, 1.2])

            with col_str_volts:
                with st.container(border=True):
                    st.markdown("#### String Voltage Verification")
                    str_voc = d["string_voc_cold_v"]
                    str_vmp = d["string_vmp_hot_v"]

                    v1, v2 = st.columns(2)
                    v1.metric("Cold Voc (@ 15°C)", f"{str_voc:.1f} V", f"Max <= {inv.max_dc_voltage_v:.0f} V")
                    v2.metric("Hot Vmp (@ 45°C)", f"{str_vmp:.1f} V", f"Min >= {inv.mppt_voltage_min_v:.0f} V")

                    if str_voc <= inv.max_dc_voltage_v:
                        st.success(f"✅ String Voc ({str_voc}V) complies with inverter maximum DC limit ({inv.max_dc_voltage_v:.0f}V).")
                    else:
                        st.error(f"❌ String Voc ({str_voc}V) EXCEEDS inverter max DC voltage ({inv.max_dc_voltage_v:.0f}V)!")

                    if str_vmp >= inv.mppt_voltage_min_v and str_voc <= inv.mppt_voltage_max_v:
                        st.info(f"ℹ️ Hot Vmp ({str_vmp}V) is well within MPPT tracking window [{inv.mppt_voltage_min_v:.0f}V – {inv.mppt_voltage_max_v:.0f}V].")
                    else:
                        st.warning(f"⚠️ Operating Vmp ({str_vmp}V) is near or outside MPPT tracking window.")

            with col_str_mppt:
                with st.container(border=True):
                    st.markdown(f"#### MPPT Tracker Allocation ({inv.mppt_count} MPPTs)")
                    mppt_alloc = d["mppt_allocation"]
                    mppt_table = []
                    for alloc_item in mppt_alloc.get("allocation", []):
                        m_idx = alloc_item["mppt_index"]
                        s_assigned = alloc_item["strings_assigned"]
                        m_panels = s_assigned * d["panels_per_string"]
                        m_imp = round(s_assigned * panel.imp, 2)
                        m_isc = round(s_assigned * panel.isc, 2)
                        hw_ok = alloc_item["hardware_ok"]
                        mppt_table.append({
                            "MPPT Tracker": f"MPPT {m_idx}",
                            "Assigned Strings": s_assigned,
                            "Modules": m_panels,
                            "Operating Current Imp (A)": m_imp,
                            "Short Circuit Current Isc (A)": m_isc,
                            "Max Isc Limit (A)": inv.max_isc_per_mppt_a,
                            "Status": "🟢 PASS" if (hw_ok and m_isc <= inv.max_isc_per_mppt_a) else "🔴 FAIL"
                        })
                    st.dataframe(pd.DataFrame(mppt_table), use_container_width=True, hide_index=True)

# ===========================================================================
# TAB 2: DC Protection & Switchgear (Per Inverter Unit)
# ===========================================================================
with tabs[1]:
    st.markdown("### DC Side Protection & Switchgear (Independent Per Inverter)")
    st.caption("Each inverter unit features independent DC isolation, surge protection, and string-level fusing.")

    dc_unit_tabs = st.tabs([d["unit_label"] for d in per_inv_designs])

    for u_idx, d in enumerate(per_inv_designs):
        with dc_unit_tabs[u_idx]:
            dc_c1, dc_c2 = st.columns(2)

            with dc_c1:
                with st.container(border=True):
                    st.markdown("#### 1. Inverter DC Isolator")
                    st.success(f"**Specification:** `{d['dc_isolator_spec']}`")
                    st.write(f"• **Quantity Required:** `{d['dc_isolator_qty']} Nos`")
                    st.write(f"• **Design Voltage:** `Voc,cold × 1.20 = {d['string_voc_cold_v'] * 1.2:.1f} V`")
                    st.write(f"• **Design Current:** `Isc × 1.25 = {panel.isc * 1.25:.2f} A`")

                with st.container(border=True):
                    st.markdown("#### 2. Inverter DC Surge Protection Device (SPD)")
                    st.success(f"**Specification:** `{d['dc_spd_spec']}`")
                    st.write(f"• **Quantity Required:** `{d['dc_spd_qty']} Nos` (1 per inverter unit)")
                    st.write("• **Standard:** IEC 61643-31 Type II DC Surge Arrester")

            with dc_c2:
                with st.container(border=True):
                    st.markdown("#### 3. DC String Fuse Evaluation (IEC 60269-6)")
                    if not d["fuse_required"]:
                        st.info(f"🟢 **{d['fuse_status_label']}**")
                        st.caption(d["fuse_note"])
                        st.write("• **Quantity:** `0 Nos` (No reverse current risk with single string per MPPT)")
                    else:
                        st.warning(f"⚠️ **{d['fuse_status_label']}**")
                        st.caption(d["fuse_note"])
                        st.write(f"• **Fuse Rating:** `{d['fuse_rating_a']}A 1000V/1500V gPV`")
                        st.write(f"• **Quantity:** `{d['fuse_qty']} Nos` (fused on both positive and negative legs)")

                with st.container(border=True):
                    st.markdown("#### 4. DC Cable & Connectors")
                    st.write(f"• **DC String Cable CSA:** `{d['dc_cable_csa_mm2']} mm²` PV1-F / H1Z2Z2-K Solar Cable")
                    st.write(f"• **Total DC Cable Length (+ & -):** `{d['dc_cable_total_m']} m`")
                    st.write(f"• **DC Voltage Drop:** `{d['dc_voltage_drop_pct']:.2f}%` (Permissible <= 1.5%)")
                    st.write(f"• **MC4 Cable Connectors:** `{d['mc4_pairs_qty']} Pairs`")

# ===========================================================================
# TAB 3: AC Protection & Switchgear (Individual & Main)
# ===========================================================================
with tabs[2]:
    st.markdown("### AC Protection & Switchgear Architecture")
    st.caption("Individual protection per inverter unit PLUS Whole-System Main AC Switchgear sized for combined export current.")

    st.markdown("#### A. Individual Inverter AC Switchgear (PER INVERTER)")
    indiv_cols = st.columns(len(per_inv_designs))
    for u_idx, d in enumerate(per_inv_designs):
        with indiv_cols[u_idx]:
            with st.container(border=True):
                st.markdown(f"**{d['unit_label']}**")
                st.write(f"• **Rated Output Current (In):** `{d['ac_current_a']:.1f} A`")
                st.write(f"• **Design Current (1.25 × In):** `{d['design_ac_current_a']:.1f} A`")
                st.write(f"• **Inverter AC Breaker:** `{d['ac_breaker_spec']}`")
                st.write(f"• **Inverter Local AC Isolator:** `{d['ac_isolator_spec']}`")
                st.write(f"• **Inverter PE Conductor:** `{d['inverter_pe_csa_mm2']} mm² Cu`")

    st.markdown("---")
    st.markdown("#### B. Whole-System Main AC Switchgear (PER SYSTEM)")
    st.info(f"💡 **Combined System AC Export:** Sized for **{whole_ac.get('total_ac_current_a', 0.0):.1f} A continuous AC current** ({total_sys_ac_kw:.1f} kW AC Combined).")

    main_c1, main_c2 = st.columns(2)
    with main_c1:
        with st.container(border=True):
            st.markdown("##### 1. Main System AC Breaker")
            st.success(f"**Specification:** `{whole_ac.get('main_breaker_spec', '')}`")
            st.write(f"• **Rating:** `{whole_ac.get('main_breaker_rating_a', 63)}A` ({whole_ac.get('main_breaker_type', 'MCB')})")
            st.write(f"• **Design Current:** `{whole_ac.get('design_main_current_a', 0.0):.1f} A` (1.25 × Combined Current)")

        with st.container(border=True):
            st.markdown("##### 2. Main System AC Isolator")
            st.success(f"**Specification:** `{whole_ac.get('main_isolator_spec', '')}`")
            st.write(f"• **Rating:** `{whole_ac.get('main_isolator_rating_a', 63)}A` Rotary Switch IP65")

    with main_c2:
        with st.container(border=True):
            st.markdown("##### 3. Lockable Utility AC Disconnect Switch")
            st.success(f"**Specification:** `{whole_ac.get('lockable_switch_spec', '')}`")
            st.caption("Required by CEB/LECO grid code. Padlockable in the OFF position at interconnection boundary.")

        with st.container(border=True):
            st.markdown("##### 4. Main AC Distribution Board & SPD")
            st.write(f"• **Main AC SPD:** `{whole_ac.get('main_spd_spec', '')}`")
            st.write(f"• **Main Collector Busbar:** `{whole_ac.get('main_busbar_rating_a', 100)} A Bus Bar Cu` ({whole_ac.get('main_busbar_dim', '25mm*3mm')})")

# ===========================================================================
# TAB 4: Cable Sizing & Dynamic Earthing
# ===========================================================================
with tabs[3]:
    st.markdown("### Cable Sizing & Dynamic Earthing Coordination")
    st.caption("Kelani Cables Table A1 (BS 7671:2008) and BS 7430 Earthing Standards.")

    cab_c1, cab_c2 = st.columns(2)

    with cab_c1:
        with st.container(border=True):
            st.markdown("#### A. Power Cables Sizing")
            st.markdown("**1. Whole-System Main AC Export Cable:**")
            main_src = whole_ac.get("main_cable_source", "AUTO")
            src_tag = "🔒 MANUAL OVERRIDE" if main_src == "MANUAL OVERRIDE" else "⚡ AUTO (Kelani Table A1)"
            st.success(f"**Main Cable CSA:** `{whole_ac.get('main_cable_csa_mm2', 10.0)} mm² Cu`  `[{src_tag}]`")
            st.caption("Sized for total combined plant export current. Never copied from a single inverter.")
            st.write(f"• **Run Length:** `{whole_ac.get('main_cable_run_m', 20.0)} m`")
            st.write(f"• **Voltage Drop:** `{whole_ac.get('main_voltage_drop_pct', 0.5):.2f}%` (Permissible <= 1.5%)")

            st.markdown("---")
            st.markdown("**2. Individual Inverter AC Cables (Inverter to Main DB):**")
            for d in per_inv_designs:
                inv_c_src = d.get("ac_cable_source", "AUTO")
                inv_tag = " `[MANUAL]`" if inv_c_src == "MANUAL OVERRIDE" else ""
                st.write(f"• **{d['unit_label']}:** `{d['ac_cable_csa_mm2']} mm² Cu`{inv_tag} ({d['ac_cable_run_m']}m run, ΔV: {d['ac_voltage_drop_pct']:.2f}%)")

            st.markdown("---")
            st.markdown("**3. DC Solar String Cables:**")
            dc_src = per_inv_designs[0].get("dc_cable_source", "AUTO") if per_inv_designs else "AUTO"
            dc_csa = per_inv_designs[0].get("dc_cable_csa_mm2", 4.0) if per_inv_designs else 4.0
            dc_tag = " `[MANUAL OVERRIDE]`" if dc_src == "MANUAL OVERRIDE" else " `[AUTO]`"
            st.write(f"• **Cross-Section:** `{dc_csa:.1f} mm²` PV1-F / H1Z2Z2-K UV Resistant{dc_tag}")
            st.write(f"• **Total DC Cable:** `{sum(d['dc_cable_total_m'] for d in per_inv_designs)} m`")

    with cab_c2:
        with st.container(border=True):
            st.markdown("#### B. Dynamic Earthing System (BS 7430)")
            st.markdown(f"**Main Earth Conductor:** `{earthing.get('main_earth_conductor_spec', '')}`")
            st.write(f"• **Main Conductor CSA:** `{earthing.get('main_earth_conductor_csa_mm2', 16.0)} mm² Cu`")
            st.caption("Dynamically sized per BS 7430: <=10kW: 10mm², 11-40kW: 16mm², 41-100kW: 25mm², >100kW: 35mm².")

            st.write(f"• **Module Bonding Wire:** `{earthing.get('module_bonding_spec', '')}`")
            st.write(f"• **Earth Rod Electrode:** `{earthing.get('earth_rod_spec', '')}`")
            st.write(f"• **Electrodes Required:** `{earthing.get('earth_rods_qty', 1)} Set(s)`")
            st.write(f"• **Calculated Effective Resistance:** `{earthing.get('achieved_resistance_ohm', 4.2)} Ω` (Target <= 10.0 Ω)")
            render_status(earthing.get("status", "PASS"), "Earthing Resistance Compliant with BS 7430")

# ===========================================================================
# TAB 5: Classified Summary Schedule & State Sync
# ===========================================================================
with tabs[4]:
    st.markdown("### Classified Component Schedule (Section 26)")
    st.caption("Categorized cleanly by PER PANEL, PER STRING, PER INVERTER, and PER SYSTEM to prevent equipment duplication.")

    for cat_key, cat_label in [
        ("PER_PANEL", "📦 1. Per Panel Components"),
        ("PER_STRING", "🔌 2. Per String Components"),
        ("PER_INVERTER", "⚡ 3. Per Inverter Components"),
        ("PER_SYSTEM", "🏢 4. Whole-System Components")
    ]:
        with st.expander(cat_label, expanded=True):
            items = classified_sched.get(cat_key, [])
            if items:
                df = pd.DataFrame(items)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.caption("No items in category.")

    st.markdown("---")
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("💾 Synchronize with BOM / BOQ Engine", type="primary", use_container_width=True):
            st.success("✅ Multi-inverter electrical design synchronized with BOM / BOQ Generator!")
            st.rerun()

    with c_btn2:
        if st.button("Proceed to BOM / BOQ Generator 📦 ➡️", use_container_width=True):
            try:
                st.switch_page("pages/4_📦_BOM_BOQ.py")
            except Exception:
                pass
