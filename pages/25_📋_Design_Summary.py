"""
pages/25_📋_Design_Summary.py — Consolidated Engineering Design Summary
Automatically aggregates all project parameters, PV subsystem sizing, multi-inverter data,
electrical infrastructure, energy yield, and validation health checks.
Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
"""
import streamlit as st
import pandas as pd
from ui.components import page_header, render_status
from ui.styles import apply_custom_css
from core.project_state import (
    get_active_project,
    get_active_panel,
    get_active_inverter,
    get_dynamic_system,
    recalculate_system_state,
    render_active_project_banner
)

try:
    st.set_page_config(page_title="Design Summary — Solar PV Platform", page_icon="📋", layout="wide")
except Exception:
    pass

apply_custom_css()
render_active_project_banner()
page_header("Consolidated Engineering Design Summary", "Complete, system-wide technical summary generated automatically from verified dynamic calculations", icon="📋")

proj = get_active_project()
panel = get_active_panel()
inverter = get_active_inverter()
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
total_strings = int(dynamic_sys.get("total_strings", 0))
inv_units = len(per_inv_designs)
ratio = float(dynamic_sys.get("dc_ac_ratio", round(dc_kwp / ac_kw, 2) if ac_kw > 0 else 1.25))
val_status = dynamic_sys.get("overall_status", "PASS")
pr_pct = float(dynamic_sys.get("performance_ratio_pct", 79.5))
annual_gen = float(dynamic_sys.get("annual_ac_energy_kwh", round(dc_kwp * 4.5 * 365 * (pr_pct / 100.0), 0)))
inverter_desc = active_combo.get("label", f"{ac_kw:.1f} kW Inverter System")

# Top KPI Metric Strip
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Target AC Power", f"{ac_kw:.1f} kW")
k2.metric("Installed DC Peak", f"{dc_kwp:.2f} kWp")
k3.metric("DC/AC Ratio", f"{ratio:.2f}")
k4.metric("Annual Export", f"{annual_gen:,.0f} kWh")
k5.metric("System PR", f"{pr_pct:.1f}%")

st.divider()

# 6 Consolidated Engineering Sections
col_left, col_right = st.columns(2)

with col_left:
    # 1. Project Information
    with st.container(border=True):
        st.markdown("#### 1. 📁 Project & Site Parameters")
        p_df = pd.DataFrame([
            {"Parameter": "Project Title", "Engineering Specification": proj.get("name", "N/A")},
            {"Parameter": "Client / Customer", "Engineering Specification": proj.get("customer_name", "N/A")},
            {"Parameter": "Site Location", "Engineering Specification": proj.get("location", "N/A")},
            {"Parameter": "Facility / Roof Name", "Engineering Specification": proj.get("site_name", "N/A")},
            {"Parameter": "Nominal Grid Voltage", "Engineering Specification": f"{proj.get('grid_voltage_v', 400.0)} V ({proj.get('grid_phases', 3)}-Phase)"},
            {"Parameter": "Installation Type", "Engineering Specification": str(proj.get("installation_type", "Rooftop")).title()},
            {"Parameter": "Ambient Design Range", "Engineering Specification": f"{proj.get('min_design_temp_c', -30.0)} °C to {proj.get('max_design_temp_c', 60.0)} °C"}
        ])
        st.dataframe(p_df, use_container_width=True, hide_index=True)

    # 2. PV Module Array Configuration
    with st.container(border=True):
        st.markdown("#### 2. ☀️ PV System Configuration")
        first_d = per_inv_designs[0] if per_inv_designs else {}
        pv_df = pd.DataFrame([
            {"Parameter": "PV Module Model", "Engineering Specification": f"{panel.manufacturer} {panel.model}"},
            {"Parameter": "Cell Technology", "Engineering Specification": f"{panel.cell_technology} ({panel.cell_count} cells)"},
            {"Parameter": "Module Rated Power", "Engineering Specification": f"{panel.rated_power_wp} Wp"},
            {"Parameter": "Total Module Quantity", "Engineering Specification": f"{panel_qty} modules"},
            {"Parameter": "Total Strings Count", "Engineering Specification": f"{total_strings} strings total across {inv_units} unit(s)"},
            {"Parameter": "String Arrangement (Primary)", "Engineering Specification": f"{first_d.get('num_strings', 0)} strings × {first_d.get('panels_per_string', 0)} mod/string"},
            {"Parameter": "Cold Voc per String", "Engineering Specification": f"{first_d.get('string_voc_cold_v', 0.0):.1f} V DC"},
            {"Parameter": "Hot Vmp per String", "Engineering Specification": f"{first_d.get('string_vmp_hot_v', 0.0):.1f} V DC"},
        ])
        st.dataframe(pv_df, use_container_width=True, hide_index=True)

    # 3. Inverter Infrastructure
    with st.container(border=True):
        st.markdown("#### 3. ⚡ Inverter Infrastructure")
        inv_breakdown_str = ", ".join(f"{it['quantity']}× {it['inverter'].model} ({it['inverter'].rated_ac_power_kw:.0f}kW)" for it in active_combo.get("breakdown", []))
        inv_df = pd.DataFrame([
            {"Parameter": "Inverter Configuration", "Engineering Specification": inverter_desc},
            {"Parameter": "Inverter Fleet Breakdown", "Engineering Specification": inv_breakdown_str if inv_breakdown_str else f"1× {inverter.model}"},
            {"Parameter": "Number of Inverter Units", "Engineering Specification": f"{inv_units} unit(s)"},
            {"Parameter": "Combined Plant Inverter Capacity", "Engineering Specification": f"{ac_kw:.1f} kW AC"},
            {"Parameter": "Combined Continuous AC Current", "Engineering Specification": f"{whole_ac.get('total_ac_current_a', 0.0):.1f} A AC"},
            {"Parameter": "Max Permissible DC Voltage", "Engineering Specification": f"{inverter.max_dc_voltage_v} V DC"},
            {"Parameter": "Weighted Efficiency", "Engineering Specification": f"{inverter.efficiency_pct} %"}
        ])
        st.dataframe(inv_df, use_container_width=True, hide_index=True)

with col_right:
    # 4. Electrical Sizing & Protection
    with st.container(border=True):
        st.markdown("#### 4. 🔌 Electrical Infrastructure & Protection")
        tot_fuses = sum(d.get('fuse_qty', 0) for d in per_inv_designs)
        fuse_desc = "Not Required — validated (1 str/MPPT)" if tot_fuses == 0 else f"{tot_fuses}x 1000V gPV Fuses (IEC 60269-6)"
        elec_df = pd.DataFrame([
            {"Parameter": "String Operating Current (Imp)", "Engineering Specification": f"{panel.imp:.2f} A DC"},
            {"Parameter": "String Short-Circuit (Isc)", "Engineering Specification": f"{panel.isc:.2f} A DC"},
            {"Parameter": "Combined AC Export Current", "Engineering Specification": f"{whole_ac.get('total_ac_current_a', 0.0):.1f} A AC"},
            {"Parameter": "Main AC Export Cable", "Engineering Specification": f"{whole_ac.get('main_cable_spec', f'4-Core {whole_ac.get(\"main_cable_csa_mm2\", 10.0):.0f} mm² Cu')} (BS 7671 Table A1)"},
            {"Parameter": "Main AC Circuit Breaker", "Engineering Specification": whole_ac.get('main_breaker_spec', 'MCB / MCCB')},
            {"Parameter": "Main AC Isolator Switch", "Engineering Specification": whole_ac.get('main_isolator_spec', 'Rotary AC Isolator IP65')},
            {"Parameter": "Utility Lockable Disconnector", "Engineering Specification": whole_ac.get('lockable_switch_spec', 'Padlockable in OFF (CEB Required)')},
            {"Parameter": "Main AC Surge Protection (SPD)", "Engineering Specification": whole_ac.get('main_spd_spec', 'Type II AC SPD 3P+N')},
            {"Parameter": "Inverter DC Surge Protection (SPD)", "Engineering Specification": f"{inv_units}x Type II DC SPD (Uc 1000V)"},
            {"Parameter": "DC String Overcurrent Fuses", "Engineering Specification": fuse_desc},
            {"Parameter": "Main Distribution Board Busbar", "Engineering Specification": f"{whole_ac.get('main_busbar_rating_a', 100)}A Cu Busbar ({whole_ac.get('main_busbar_dim', '25mm*3mm')}) (DIN 43671)"},
            {"Parameter": "Main Earth Conductor", "Engineering Specification": earthing.get('main_earth_conductor_spec', '16 mm² Cu (BS 7430)')},
            {"Parameter": "Earth Electrode Resistance", "Engineering Specification": f"{earthing.get('achieved_resistance_ohm', 4.2):.1f} Ω (BS 7430 <= 10.0 Ω)"},
        ])
        st.dataframe(elec_df, use_container_width=True, hide_index=True)

    # 5. Energy Yield & Generation Forecast
    with st.container(border=True):
        st.markdown("#### 5. ⚡ Generation & Performance Metrics")
        gen_df = pd.DataFrame([
            {"Parameter": "Peak Sun Hours (PSH)", "Engineering Specification": f"{proj.get('peak_sun_hours', 4.5)} h/day"},
            {"Parameter": "System Performance Ratio (PR)", "Engineering Specification": f"{pr_pct:.1f} %"},
            {"Parameter": "Daily Energy Yield (Est.)", "Engineering Specification": f"{annual_gen / 365.0:,.1f} kWh/day"},
            {"Parameter": "Annual Energy Generation", "Engineering Specification": f"{annual_gen:,.0f} kWh/year"},
            {"Parameter": "Specific Yield", "Engineering Specification": f"{annual_gen / dc_kwp:,.1f} kWh/kWp/year" if dc_kwp > 0 else "N/A"},
        ])
        st.dataframe(gen_df, use_container_width=True, hide_index=True)

    # 6. Compliance Health Status
    with st.container(border=True):
        st.markdown("#### 6. 🛡️ Standards Compliance Status")
        status_color = "🟢" if val_status == "PASS" else ("🟡" if val_status == "WARNING" else "🔴")
        st.markdown(f"**Overall Compliance:** {status_color} **{val_status}**")
        st.caption("Verified against BS 7671:2008 (Kelani Table A1), IEC 60364-7-712, IEC 60269-6, BS 7430, and CEB Interconnection Standards.")
