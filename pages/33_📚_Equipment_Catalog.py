"""
pages/33_📚_Equipment_Catalog.py — Unified Master Equipment & Electrical Component Catalog
Tabulated engineering data for Cables (BS 7671 Table A1), Breakers (MCB/MCCB), SPDs, Busbars, and Earthing.
Authored by Eng. Aashir © 2026.
"""
import streamlit as st
import pandas as pd
from ui.styles import apply_custom_css
from ui.components import page_header
from core.electrical_data import CABLE_AMPACITY_TABLE, MCB_STANDARD_RATINGS_A, MCCB_STANDARD_RATINGS_A, BUSBAR_STANDARD_RATINGS_A
from core.project_state import render_active_project_banner

from core.inverter_catalog import INVERTER_CATALOG_DATA, get_catalog_summary
from core.project_state import APPROVED_PANELS_SPECS

try:
    st.set_page_config(page_title="Equipment Catalog — Solar PV Platform", page_icon="📚", layout="wide")
except Exception:
    pass

apply_custom_css()
render_active_project_banner()
page_header("Master Equipment & Component Catalog", "Comprehensive technical database for solar panels, string inverters, cables, circuit breakers, surge arresters, busbars, and grounding materials", icon="📚")

tab_inverters, tab_panels, tab_cables, tab_breakers, tab_spds, tab_busbars, tab_earthing = st.tabs([
    "⚡ Inverters Database (Sunways & KACO)",
    "☀️ Solar PV Modules",
    "🔌 Cable Ampacity Library (BS 7671)",
    "🛡️ Circuit Breakers (MCB & MCCB)",
    "⚡ SPDs, Fuses & Isolators",
    "📊 Busbar Profiles (DIN 43671)",
    "🌍 Earthing & Grounding Materials"
])

# ---------------------------------------------------------------------------
# TAB 0A: INVERTERS DATABASE
# ---------------------------------------------------------------------------
with tab_inverters:
    st.markdown("### ⚡ Central Inverter Database (Sunways & KACO)")
    st.caption("Extracted directly from manufacturer technical datasheets across Single Phase (230V) and Three Phase (400V) models.")

    summary = get_catalog_summary()
    sm1, sm2, sm3, sm4 = st.columns(4)
    sm1.metric("Total Inverter Models", f"{summary['total_models']}")
    sm2.metric("Manufacturers", f"{', '.join(summary['manufacturers'])}")
    sm3.metric("Capacity Range", f"{summary['min_rated_kw']:.0f} kW – {summary['max_rated_kw']:.0f} kW")
    sm4.metric("3-Phase Models", f"{summary['three_phase_count']} units")

    inv_display = []
    for d in INVERTER_CATALOG_DATA:
        inv_display.append({
            "Manufacturer": d["manufacturer"],
            "Model": d["model"],
            "Rated AC (kW)": d["rated_ac_power_kw"],
            "Grid Type": d.get("grid_type", "3-phase"),
            "AC Voltage (V)": d["ac_voltage"],
            "Max DC (V)": d["max_dc_voltage_v"],
            "MPPT Range (V)": f"{d['mppt_voltage_min_v']:.0f} – {d['mppt_voltage_max_v']:.0f}",
            "MPPTs": d["mppt_count"],
            "Inputs/MPPT": d["string_inputs_per_mppt"],
            "Max Isc/MPPT (A)": d["max_isc_per_mppt_a"],
            "Max AC Current (A)": d["max_ac_current_a"],
            "Efficiency (%)": d["efficiency_pct"],
            "Datasheet": d.get("datasheet", "")
        })
    inv_df = pd.DataFrame(inv_display)
    st.dataframe(inv_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# TAB 0B: SOLAR PV MODULES
# ---------------------------------------------------------------------------
with tab_panels:
    st.markdown("### ☀️ Central Solar PV Module Database (Tier-1 TOPCon Bifacial)")
    st.caption("Extracted directly from Yingli PANDA 3.0 Pro datasheets (144-cell, 132-cell, and 156-cell series).")

    panel_display = []
    for p in APPROVED_PANELS_SPECS:
        panel_display.append({
            "Manufacturer": p["manufacturer"],
            "Model": p["model"],
            "Rated Power (Wp)": p["rated_power_wp"],
            "Cell Tech": p["cell_technology"],
            "Cells": p["cell_count"],
            "Voc (V)": p["voc"],
            "Vmp (V)": p["vmp"],
            "Isc (A)": p["isc"],
            "Imp (A)": p["imp"],
            "Max System (V)": p["max_system_voltage"],
            "Series Fuse (A)": p["max_series_fuse"],
            "Temp Coeff Voc (%/°C)": p["temp_coeff_voc"],
            "Dimensions (m)": f"{p['length_m']} × {p['width_m']}",
            "Weight (kg)": p["weight_kg"]
        })
    st.dataframe(pd.DataFrame(panel_display), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# TAB 1: CABLE AMPACITY LIBRARY
# ---------------------------------------------------------------------------
with tab_cables:
    st.markdown("### 🔌 BS 7671 Single-Core PVC Insulated Cable Ampacity Table")
    st.caption("Transcribed from Kelani Cables Table A1 / BS 7671 (30°C ambient, 70°C conductor operating temp).")

    cable_df = pd.DataFrame(CABLE_AMPACITY_TABLE)
    st.dataframe(cable_df, use_container_width=True, hide_index=True)
    st.info("💡 **Method Key Legend:** `c_2c` = 2 cables single-phase/DC clipped direct | `c_34c` = 3/4 cables 3-phase clipped direct | `f_touch_3flat` = 3 cables 3-phase flat touching on tray | `a_*` = enclosed in conduit in insulated wall | `b_*` = enclosed in conduit on wall / in trunking.")

# ---------------------------------------------------------------------------
# TAB 2: CIRCUIT BREAKERS
# ---------------------------------------------------------------------------
with tab_breakers:
    st.markdown("### 🛡️ Standard Low-Voltage Overcurrent Protective Devices")
    c_mcb, c_mccb = st.columns(2)
    with c_mcb:
        st.markdown("#### Miniature Circuit Breakers (MCB — IEC 60898)")
        mcb_df = pd.DataFrame([
            {"Rated Current (In)": f"{r} A", "Standard Poles": "1P, 2P, 3P, 4P", "Curve Types": "B, C, D", "Typical Breaking Capacity": "6 kA / 10 kA"}
            for r in MCB_STANDARD_RATINGS_A
        ])
        st.dataframe(mcb_df, use_container_width=True, hide_index=True)

    with c_mccb:
        st.markdown("#### Moulded Case Circuit Breakers (MCCB — IEC 60947-2)")
        mccb_df = pd.DataFrame([
            {"Frame Rating (In)": f"{r} A", "Standard Poles": "3P, 4P", "Trip Unit": "Thermal-Magnetic / Electronic", "Typical Breaking Capacity (Icu)": "25 kA / 36 kA / 50 kA"}
            for r in MCCB_STANDARD_RATINGS_A
        ])
        st.dataframe(mccb_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# TAB 3: SPDS, FUSES & ISOLATORS
# ---------------------------------------------------------------------------
with tab_spds:
    st.markdown("### ⚡ Surge Protective Devices (SPD), gPV Fuses & DC Isolators")
    c_dc_p, c_ac_p = st.columns(2)
    with c_dc_p:
        st.markdown("#### DC Array Protection (IEC 60269-6 & IEC 61643-31)")
        dc_prot_df = pd.DataFrame([
            {"Component": "DC String Fuse", "Standard Ratings": "15A, 20A, 25A, 30A, 32A gPV (1000V/1500V DC)", "Standard": "IEC 60269-6"},
            {"Component": "DC Surge Arrester (SPD)", "Standard Ratings": "600V, 1000V, 1200V, 1500V DC Type II (In=20kA, Imax=40kA)", "Standard": "IEC 61643-31"},
            {"Component": "DC Rotary Isolator Switch", "Standard Ratings": "16A, 25A, 32A, 50A, 63A @ 1000V/1500V DC (DC-PV2)", "Standard": "IEC 60947-3"}
        ])
        st.dataframe(dc_dc_p := dc_prot_df, use_container_width=True, hide_index=True)

    with c_ac_p:
        st.markdown("#### AC Protection & Residual Current Devices")
        ac_prot_df = pd.DataFrame([
            {"Component": "AC Surge Arrester (SPD)", "Standard Ratings": "275V, 320V, 440V AC Type II (Uc >= 1.15*Vph)", "Standard": "IEC 61643-11"},
            {"Component": "Type B RCD (DC Sensitive)", "Standard Ratings": "30mA (Personnel) / 300mA (Fire Protection), 40A to 125A", "Standard": "IEC 62423"},
            {"Component": "AC Isolator Switch", "Standard Ratings": "32A, 63A, 100A, 125A, 160A, 250A, 400A AC-23A", "Standard": "IEC 60947-3"}
        ])
        st.dataframe(ac_prot_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# TAB 4: BUSBAR PROFILES
# ---------------------------------------------------------------------------
with tab_busbars:
    st.markdown("### 📊 Standard Rectangular Busbars (DIN 43671 / IEC 61439)")
    st.caption("Current carrying capacities for indoor switchboards (35°C ambient air, 65°C temp rise).")
    busbar_df = pd.DataFrame([
        {"Dimensions (W × T mm)": "15 × 3", "Cross-Section (mm²)": 45, "Copper Ampacity (A)": 115, "Aluminium Ampacity (A)": 88},
        {"Dimensions (W × T mm)": "20 × 3", "Cross-Section (mm²)": 60, "Copper Ampacity (A)": 150, "Aluminium Ampacity (A)": 115},
        {"Dimensions (W × T mm)": "25 × 3", "Cross-Section (mm²)": 75, "Copper Ampacity (A)": 180, "Aluminium Ampacity (A)": 140},
        {"Dimensions (W × T mm)": "30 × 5", "Cross-Section (mm²)": 150, "Copper Ampacity (A)": 315, "Aluminium Ampacity (A)": 245},
        {"Dimensions (W × T mm)": "40 × 5", "Cross-Section (mm²)": 200, "Copper Ampacity (A)": 405, "Aluminium Ampacity (A)": 315},
        {"Dimensions (W × T mm)": "50 × 5", "Cross-Section (mm²)": 250, "Copper Ampacity (A)": 500, "Aluminium Ampacity (A)": 390},
        {"Dimensions (W × T mm)": "60 × 6", "Cross-Section (mm²)": 360, "Copper Ampacity (A)": 675, "Aluminium Ampacity (A)": 525},
        {"Dimensions (W × T mm)": "80 × 8", "Cross-Section (mm²)": 640, "Copper Ampacity (A)": 1050, "Aluminium Ampacity (A)": 820},
        {"Dimensions (W × T mm)": "100 × 10", "Cross-Section (mm²)": 1000, "Copper Ampacity (A)": 1490, "Aluminium Ampacity (A)": 1160},
        {"Dimensions (W × T mm)": "120 × 10", "Cross-Section (mm²)": 1200, "Copper Ampacity (A)": 1740, "Aluminium Ampacity (A)": 1350}
    ])
    st.dataframe(busbar_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# TAB 5: EARTHING & GROUNDING MATERIALS
# ---------------------------------------------------------------------------
with tab_earthing:
    st.markdown("### 🌍 Grounding Electrodes & Earth Conductors (BS 7430)")
    earth_df = pd.DataFrame([
        {"Material / Item": "Copper-Bonded Earth Rod", "Standard Dimensions": "5/8\" (16mm) dia × 3.0 m length (254 micron Cu coating)", "Typical Resistance": "10 - 25 Ω in clay/loam"},
        {"Material / Item": "Bare Hard-Drawn Copper Tape", "Standard Dimensions": "25 mm × 3 mm (75 mm²)", "Application": "Substation earth grid / ring conductor"},
        {"Material / Item": "PVC Insulated Earth Conductor", "Standard Dimensions": "16 mm², 25 mm², 35 mm², 50 mm², 70 mm² (Green/Yellow)", "Application": "Inverter/Panel frame bonding to main earth bar"},
        {"Material / Item": "Earth Inspection Pit", "Standard Dimensions": "300 × 300 mm Concrete / Heavy-Duty Polymer Pit", "Application": "Rod disconnection test point"},
        {"Material / Item": "Exothermic Weld / Earth Clamp", "Standard Dimensions": "High-strength phosphor bronze / Cadweld connection", "Application": "Corrosion-resistant grounding joint"}
    ])
    st.dataframe(earth_df, use_container_width=True, hide_index=True)
