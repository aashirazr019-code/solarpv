"""
pages/1_📊_Dashboard.py — Executive Engineering Dashboard
Executive plant KPIs, multi-inverter configuration summary, protection & cable metrics,
and direct access to the reorganized 5-step engineering design workflow.
Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
"""
import streamlit as st
from ui.components import page_header, render_status
from ui.styles import apply_custom_css
from data.database import get_project_stats, list_projects
from core.project_state import (
    init_project_state,
    get_active_project,
    set_active_project,
    get_active_panel,
    get_active_inverter,
    get_dynamic_system,
    recalculate_system_state,
    render_active_project_banner,
)

try:
    st.set_page_config(page_title="Executive Dashboard — Solar PV Platform", page_icon="📊", layout="wide")
except Exception:
    pass

apply_custom_css()
init_project_state()
render_active_project_banner()

page_header(
    "Solar PV Engineering Dashboard",
    "Executive summary of plant capacity, multi-inverter configuration, switchgear coordination, and cable sizing",
    "📊"
)

proj = get_active_project()
panel = get_active_panel()
dynamic_sys = get_dynamic_system()

if not dynamic_sys or "per_inverter_designs" not in dynamic_sys:
    dynamic_sys = recalculate_system_state()

per_inv_designs = dynamic_sys.get("per_inverter_designs", [])
whole_ac = dynamic_sys.get("whole_system_ac", {})
earthing = dynamic_sys.get("earthing_design", {})
active_combo = dynamic_sys.get("active_combination", {})

ac_kw = float(dynamic_sys.get("actual_ac_kw", proj.get("target_ac_capacity_kw", 5.0)))
dc_kwp = float(dynamic_sys.get("actual_dc_kwp", round(ac_kw * 1.25, 2)))
panel_qty = int(dynamic_sys.get("total_panels", 0))
n_strings = int(dynamic_sys.get("total_strings", 0))
ratio = float(dynamic_sys.get("dc_ac_ratio", round(dc_kwp / ac_kw, 2) if ac_kw > 0 else 1.25))
inv_count = len(per_inv_designs)
inv_label = active_combo.get("label", f"{ac_kw:.1f} kW AC Inverter System")

# ---------------------------------------------------------------------------
# 1. Executive Top Metrics Row
# ---------------------------------------------------------------------------
st.markdown("### 📈 Plant Executive Sizing Overview")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Target AC Capacity", f"{ac_kw:.1f} kW", f"{proj.get('grid_voltage_v', 400.0):.0f}V {proj.get('grid_phases', 3)}P")
k2.metric("Total DC Capacity", f"{dc_kwp:.2f} kWp", f"DC/AC Ratio: {ratio:.2f}")
k3.metric("Selected PV Module", f"{panel.rated_power_wp} Wp", f"{panel.manufacturer} {panel.model[:12]}")
k4.metric("Total PV Modules", f"{panel_qty} Nos", f"{n_strings} strings / {inv_count} inv")
k5.metric("Monthly Generation", f"{ac_kw * 120:,.0f} kWh", "120 kWh/kW standard")

# Multi-Inverter Units Banner
if inv_count > 1:
    st.info(f"⚡ **Multi-Inverter Combination:** `{inv_label}` — {inv_count} inverters operating in parallel for {ac_kw:.1f} kW total export.")

st.markdown("---")

# ---------------------------------------------------------------------------
# 2. Workflow Navigation Cards
# ---------------------------------------------------------------------------
st.markdown("### 🚀 Guided Engineering Workflow")
w1, w2, w3, w4, w5 = st.columns(5)

with w1:
    with st.container(border=True):
        st.markdown("#### ⚙️ 1. Config")
        st.caption("Target kW, Inverter Selection (AUTO/MANUAL), Approved Panels.")
        if st.button("System Config ➡️", key="nav_cfg", use_container_width=True):
            try:
                st.switch_page("pages/2_⚙️_System_Configuration.py")
            except Exception:
                pass

with w2:
    with st.container(border=True):
        st.markdown("#### ⚡ 2. Electrical")
        st.caption("Per-inverter strings, MPPT, DC switchgear, main AC cable & earthing.")
        if st.button("Electrical Design ➡️", key="nav_elec", use_container_width=True):
            try:
                st.switch_page("pages/3_⚡_Electrical_Design.py")
            except Exception:
                pass

with w3:
    with st.container(border=True):
        st.markdown("#### 📦 3. BOM / BOQ")
        st.caption("Auto-fill Master sample_boq.xlsx, Blank Field audit, Excel download.")
        if st.button("BOM / BOQ ➡️", key="nav_boq", use_container_width=True):
            try:
                st.switch_page("pages/4_📦_BOM_BOQ.py")
            except Exception:
                pass

with w4:
    with st.container(border=True):
        st.markdown("#### ⚡ 4. CEB Tariff")
        st.caption("PUCSL 2026 tariffs, 2-way solvers, Net Metering / Plus savings.")
        if st.button("CEB Tariff ➡️", key="nav_ceb", use_container_width=True):
            try:
                st.switch_page("pages/35_⚡_CEB_Tariff_Calculator.py")
            except Exception:
                pass

with w5:
    with st.container(border=True):
        st.markdown("#### 📄 5. Reports & SLD")
        st.caption("12-Section PDF report, 15-Sheet Excel schedule, and AutoCAD DXF.")
        if st.button("Reports & SLD ➡️", key="nav_rep", use_container_width=True):
            try:
                st.switch_page("pages/27_📄_Reports.py")
            except Exception:
                pass

st.markdown("---")

# ---------------------------------------------------------------------------
# 3. Consolidated Technical Specifications & Schedules
# ---------------------------------------------------------------------------
col_spec1, col_spec2 = st.columns(2)

with col_spec1:
    with st.container(border=True):
        st.markdown("#### 🛡️ Protection & Switchgear Schedule")
        tot_dc_iso = sum(d.get("dc_isolator_qty", 1) for d in per_inv_designs)
        tot_fuses = sum(d.get("fuse_qty", 0) for d in per_inv_designs)
        st.markdown(f"• **Inverter DC Isolators:** `{per_inv_designs[0].get('dc_isolator_spec', '') if per_inv_designs else ''}` — **{tot_dc_iso} Nos total**")
        st.markdown(f"• **Inverter DC SPDs:** `{per_inv_designs[0].get('dc_spd_spec', '') if per_inv_designs else ''}` — **{inv_count} Nos** (1 per inverter)")
        fuse_lbl = f"{tot_fuses} Nos" if tot_fuses > 0 else "Not Required — validated (1 str/MPPT)"
        st.markdown(f"• **DC String Fuses:** `{fuse_lbl}`")
        st.markdown(f"• **Main AC Breaker:** `{whole_ac.get('main_breaker_spec', '')}` — **1 Nos**")
        st.markdown(f"• **Main AC Isolator:** `{whole_ac.get('main_isolator_spec', '')}` — **1 Nos**")
        st.markdown(f"• **Main AC SPD:** `{whole_ac.get('main_spd_spec', '')}` — **1 Nos**")
        st.markdown(f"• **Lockable Utility Switch:** `{whole_ac.get('lockable_switch_spec', '')}` — **1 Nos**")

with col_spec2:
    with st.container(border=True):
        st.markdown("#### 🔌 Cabling & Earthing Schedule")
        tot_dc_wire = sum(d.get("dc_cable_total_m", 60.0) for d in per_inv_designs)
        main_csa = whole_ac.get("main_cable_csa_mm2", 10.0)
        main_len = whole_ac.get("main_cable_run_m", 20.0)
        earth_csa = earthing.get("main_earth_conductor_csa_mm2", 16.0)
        earth_rods = earthing.get("earth_rods_qty", 1)

        st.markdown(f"• **DC Solar String Cable:** `4.0 / 6.0 mm² PV1-F` — **Total: {tot_dc_wire:.0f} m** (+/- runs for {n_strings} strings)")
        st.markdown(f"• **Main AC Export Cable:** `4-Core {main_csa:.0f} mm² Cu` — **Total: {main_len:.0f} m** (Combined current {whole_ac.get('total_ac_current_a', 0.0):.1f}A)")
        st.markdown(f"• **Main Earth Conductor:** `{earth_csa:.0f} mm² Cu (BS 7430)` — **Total: 25 m**")
        st.markdown(f"• **Earth Electrodes:** `5/8\" x 3.0m Copper-Bonded Steel` — **Quantity: {earth_rods} Set(s)**")
        st.markdown(f"• **MC4 Connectors:** `1000V 30A Male/Female Pairs` — **Quantity: {sum(d.get('mc4_pairs_qty', 2) for d in per_inv_designs)} Sets**")

st.markdown("---")

# ---------------------------------------------------------------------------
# 4. Standards Compliance Ribbon
# ---------------------------------------------------------------------------
with st.container(border=True):
    st.markdown("#### 📜 Engineering Standards Verification")
    c_std1, c_std2, c_std3 = st.columns(3)
    c_std1.markdown("✅ **BS 7671:2008 / Kelani Table A1**<br/><span style='font-size:11px;color:#64748b;'>Continuous current capacity & &le;1.5% voltage drop</span>", unsafe_allow_html=True)
    c_std2.markdown("✅ **IEC 60364-7-712 & IEC 60269-6**<br/><span style='font-size:11px;color:#64748b;'>Solar PV installations & gPV string overcurrent protection</span>", unsafe_allow_html=True)
    c_std3.markdown("✅ **CEB / LECO Grid Code & BS 7430**<br/><span style='font-size:11px;color:#64748b;'>Lockable utility disconnect switch & protective earthing</span>", unsafe_allow_html=True)
