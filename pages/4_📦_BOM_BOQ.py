"""
pages/4_📦_BOM_BOQ.py — Master BOM / BOQ Engine & Template Generator
Populates dynamic multi-inverter configuration directly into the exact data/BOQ/sample_boq.xlsx template.
Enforces the Blank Field Rule: auto-fills only verified calculated equipment,
leaving uncalculated site hardware and unit prices blank for manual completion.
Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
"""
import os
import io
import datetime
import streamlit as st
import pandas as pd
from ui.styles import apply_custom_css
from ui.components import page_header, render_status
from core.models import Panel, Inverter
from core.project_state import (
    init_project_state,
    get_active_project,
    get_active_panel,
    get_active_inverter,
    get_dynamic_system,
    recalculate_system_state,
    render_active_project_banner,
)
from reports.boq_excel_generator import generate_master_template_boq_excel, generate_boq_excel

st.set_page_config(
    page_title="BOM / BOQ Engine — Eng. Aashir",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)
apply_custom_css()
init_project_state()

page_header(
    "Intelligent BOM / BOQ Generation Engine",
    "Auto-fill verified multi-inverter equipment schedules directly into the exact Master Excel Template (sample_boq.xlsx)",
    "📦"
)

render_active_project_banner()

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
total_strings = int(dynamic_sys.get("total_strings", 0))
inverter_count = len(per_inv_designs)

# Inverter specification label
if inverter_count == 1:
    inv_item = per_inv_designs[0]["inverter"]
    inv_spec = f"{inv_item.rated_ac_power_kw:.0f} kW ({inv_item.model})"
    inv_notes = f"Continuous {inv_item.rated_ac_power_kw:.0f} kW AC export"
else:
    inv_spec = active_combo.get("label", f"{ac_kw:.1f} kW AC Multi-Inverter")
    inv_notes = ", ".join(f"{it['quantity']}× {it['inverter'].model} ({it['inverter'].rated_ac_power_kw:.0f}kW)" for it in active_combo.get("breakdown", []))

# Switchgear and cables aggregated from dynamic system
dc_iso_qty = sum(d.get("dc_isolator_qty", 1) for d in per_inv_designs)
dc_iso_spec = per_inv_designs[0].get("dc_isolator_spec", "1000V 25A 4P DC Isolator") if per_inv_designs else "1000V 32A 4P"

dc_spd_qty = inverter_count
dc_spd_spec = per_inv_designs[0].get("dc_spd_spec", "Type II DC SPD 1000V (20/40kA)") if per_inv_designs else "Type II DC SPD 1000V"

dc_fuse_qty = sum(d.get("fuse_qty", 0) for d in per_inv_designs)
if dc_fuse_qty > 0:
    fuse_r = next((d["fuse_rating_a"] for d in per_inv_designs if d["fuse_rating_a"]), 25)
    dc_fuse_spec = f"1000V gPV {fuse_r}A 10x38mm Fuse Link"
    fuse_holder_spec = "1000V/1500V 10x38mm Finger-Safe DIN Rail Holder"
    fuse_holder_qty = dc_fuse_qty
    fuse_notes = f"IEC 60269-6: Required for parallel strings ({dc_fuse_qty} legs fused)"
else:
    dc_fuse_spec = "Not Required (Single String per MPPT)"
    fuse_holder_spec = "Not Required"
    fuse_holder_qty = 0
    fuse_notes = "IEC 60269-6: No reverse current risk; string fuses not required"

mc4_qty = sum(d.get("mc4_pairs_qty", 2) for d in per_inv_designs)
total_dc_cable_m = sum(d.get("dc_cable_total_m", 60.0) for d in per_inv_designs)
dc_cable_csa = per_inv_designs[0].get("dc_cable_csa_mm2", 4.0) if per_inv_designs else 4.0

ac_breaker_spec = whole_ac.get("main_breaker_spec", "MCB / MCCB")
ac_iso_spec = whole_ac.get("main_isolator_spec", "Rotary AC Isolator IP65")
ac_spd_spec = whole_ac.get("main_spd_spec", "Type II AC SPD")
lockable_spec = whole_ac.get("lockable_switch_spec", "Padlockable Switch IP65")
main_ac_cable_csa = whole_ac.get("main_cable_csa_mm2", 10.0)
main_ac_cable_m = whole_ac.get("main_cable_run_m", 20.0)
main_busbar_rating = whole_ac.get("main_busbar_rating_a", 100)

earth_rod_qty = earthing.get("earth_rods_qty", 1)
main_earth_csa = earthing.get("main_earth_conductor_csa_mm2", 16.0)

# ---------------------------------------------------------------------------
# SECTION 1: Master BOQ Item Dictionary Construction
# ---------------------------------------------------------------------------
boq_items = [
    # === PV MODULES ===
    {
        "sn": 1,
        "description": "Solar PV Module",
        "brand": panel.manufacturer,
        "capacity": f"{panel.rated_power_wp:.0f} W",
        "unit": "Nos",
        "quantity": panel_qty,
        "status": "AUTO-FILLED",
        "notes": f"{total_strings} strings × {int(panel_qty / total_strings) if total_strings else 0} panels/string"
    },
    # === INVERTER ===
    {
        "sn": 2,
        "description": "Grid-Tie String Inverter",
        "brand": per_inv_designs[0]["inverter"].manufacturer if per_inv_designs else "Sunways",
        "capacity": (f"{per_inv_designs[0]['inverter'].rated_ac_power_kw:.0f} kW"
                     if inverter_count == 1
                     else f"{ac_kw:.0f} kW ({inverter_count} units)"),
        "unit": "Nos",
        "quantity": inverter_count,
        "status": "AUTO-FILLED",
        "notes": inv_notes
    },
    # === DC SIDE ===
    {
        "sn": 3,
        "description": "DC Isolator Switch",
        "brand": "Suntree / Projoy",
        "capacity": f"2P, 1000 V DC",
        "unit": "Nos",
        "quantity": dc_iso_qty,
        "status": "AUTO-FILLED",
        "notes": f"1 per string group ({dc_iso_qty} units)"
    },
    {
        "sn": 4,
        "description": "DC Surge Protection Device (SPD)",
        "brand": "Suntree / Beny",
        "capacity": f"Type 2, 1000 V DC",
        "unit": "Nos",
        "quantity": dc_spd_qty,
        "status": "AUTO-FILLED",
        "notes": f"1 SPD per inverter ({dc_spd_qty} units)"
    },
    {
        "sn": 5,
        "description": "DC String Fuse (gPV)",
        "brand": "Suntree / Schneider",
        "capacity": (f"gPV, {next((d['fuse_rating_a'] for d in per_inv_designs if d.get('fuse_rating_a')), 25)} A, 1000 V"
                     if dc_fuse_qty > 0 else "Not Required"),
        "unit": "Nos",
        "quantity": dc_fuse_qty if dc_fuse_qty > 0 else None,
        "status": "AUTO-FILLED",
        "notes": fuse_notes
    },
    {
        "sn": 6,
        "description": "DC Fuse Holder (DIN Rail)",
        "brand": "Suntree",
        "capacity": "10 × 38 mm, 1000 V" if fuse_holder_qty > 0 else "Not Required",
        "unit": "Nos",
        "quantity": fuse_holder_qty if fuse_holder_qty > 0 else None,
        "status": "AUTO-FILLED",
        "notes": "Matches fuse quantity" if fuse_holder_qty > 0 else "Not Required"
    },
    {
        "sn": 7,
        "description": "MC4 Solar Connectors",
        "brand": "Staubli / QC Solar",
        "capacity": "1000 V, 30 A",
        "unit": "Pairs",
        "quantity": mc4_qty,
        "status": "AUTO-FILLED",
        "notes": f"2 pairs per string ({mc4_qty} pairs total)"
    },
    # === AC SIDE ===
    {
        "sn": 8,
        "description": "AC Isolator Switch",
        "brand": "Suntree / ABB",
        "capacity": (f"{'2P' if proj.get('grid_phases',3)==1 else '4P'}, "
                     f"{int(proj.get('grid_voltage_v', 400))} V AC"),
        "unit": "Nos",
        "quantity": 1,
        "status": "AUTO-FILLED",
        "notes": "Main AC export isolation"
    },
    {
        "sn": 9,
        "description": "AC Surge Protection Device (SPD)",
        "brand": "Suntree / Schneider",
        "capacity": (f"Type 2, "
                     f"{int(proj.get('grid_voltage_v', 400))} V AC"),
        "unit": "Nos",
        "quantity": 1,
        "status": "AUTO-FILLED",
        "notes": "Transient overvoltage protection at Main DB"
    },
    {
        "sn": 10,
        "description": "AC Main Circuit Breaker (MCB/MCCB)",
        "brand": "Schneider / ABB",
        "capacity": (f"{'2P' if proj.get('grid_phases',3)==1 else '4P'}, "
                     f"{whole_ac.get('main_breaker_rating_a', '—')} A"),
        "unit": "Nos",
        "quantity": 1,
        "status": "AUTO-FILLED",
        "notes": f"Sized for {whole_ac.get('design_main_current_a', 0.0):.1f} A combined export"
    },
    {
        "sn": 11,
        "description": "AC Main Busbar / DB",
        "brand": "Standard IP65",
        "capacity": f"Cu Busbar, {main_busbar_rating} A",
        "unit": "Nos",
        "quantity": 1,
        "status": "AUTO-FILLED",
        "notes": f"DIN 43671 — {whole_ac.get('main_busbar_dim', '25mm×3mm')}"
    },
    {
        "sn": 12,
        "description": "Padlockable Utility Disconnector",
        "brand": "Suntree / ABB",
        "capacity": (f"{'2P' if proj.get('grid_phases',3)==1 else '4P'}, "
                     f"{int(proj.get('grid_voltage_v', 400))} V AC"),
        "unit": "Nos",
        "quantity": 1,
        "status": "AUTO-FILLED",
        "notes": "CEB/LECO grid interconnection requirement"
    },
    # === CABLES ===
    {
        "sn": 13,
        "description": "DC Solar Cable",
        "brand": "KBE / Lapp",
        "capacity": f"1C × {dc_cable_csa:.0f} mm² Cu, PV1-F, 1000 V",
        "unit": "m",
        "quantity": total_dc_cable_m,
        "status": "AUTO-FILLED",
        "notes": f"Both +/− runs for {total_strings} strings"
    },
    {
        "sn": 14,
        "description": "AC Main Power Cable",
        "brand": "Kelani / ACL",
        "capacity": (f"{'2C' if proj.get('grid_phases',3)==1 else '4C'} × "
                     f"{main_ac_cable_csa:.0f} mm² Cu/XLPE/PVC"),
        "unit": "m",
        "quantity": main_ac_cable_m,
        "status": "AUTO-FILLED",
        "notes": f"Sized for {whole_ac.get('total_ac_current_a', 0.0):.1f} A, Kelani Table A1"
    },
    {
        "sn": 15,
        "description": "Earthing / PE Cable",
        "brand": "Kelani / ACL",
        "capacity": f"1C × {main_earth_csa:.0f} mm² Cu/PVC, Green/Yellow",
        "unit": "m",
        "quantity": 25.0,
        "status": "AUTO-FILLED",
        "notes": "BS 7430 protective earthing conductor"
    },
    # === EARTHING ===
    {
        "sn": 16,
        "description": "Earth Electrode (Grounding Rod)",
        "brand": "Copper-Bonded",
        "capacity": "16 mm × 3000 mm, Copper-Bonded Steel",
        "unit": "Nos",
        "quantity": earth_rod_qty,
        "status": "AUTO-FILLED",
        "notes": f"BS 7430 — {earth_rod_qty} rod(s) for < 10 Ω resistance"
    },
]


# Blank Field Rule audit summary
st.markdown("### 1. Template Compliance & Blank Field Audit")
st.info(
    "🛡️ **Blank Field Rule Enforcement:** In strict compliance with engineering specifications, the engine auto-fills ONLY "
    "the components reliably calculated from dynamic rules. Unit prices, total sums, and field-measured accessories "
    "(e.g. conduits, trunking, brackets, tile screws) are strictly left **BLANK** for site engineer estimation."
)

col_audit1, col_audit2 = st.columns(2)

with col_audit1:
    with st.container(border=True):
        st.markdown("#### 🟢 Automatically Filled Fields (Sheet1 & Sheet2)")
        st.write(f"• **Metadata:** Customer Name, Plant Capacity ({ac_kw:.1f} kW AC), Generation Date")
        st.write(f"• **PV Modules:** {panel.manufacturer} {panel.model} ({panel_qty} Nos, {dc_kwp:.2f} kWp)")
        st.write(f"• **Inverters:** {inv_spec} ({inverter_count} unit(s) total)")
        st.write(f"• **DC Switchgear:** DC Isolators ({dc_iso_qty} Nos), DC SPDs ({dc_spd_qty} Nos), DC Fuses ({dc_fuse_qty if dc_fuse_qty > 0 else 'Not Required'})")
        st.write(f"• **AC Switchgear:** Main Breaker ({ac_breaker_spec}), Main Isolator ({ac_iso_spec}), Main SPD ({ac_spd_spec})")
        st.write(f"• **Utility Switch:** Lockable Switch ({lockable_spec} — Sheet2 Row 33)")
        st.write(f"• **Cables:** DC Cable ({total_dc_cable_m:.0f}m), Main AC Cable ({main_ac_cable_csa:.0f}mm², {main_ac_cable_m:.0f}m), Earth Wire ({main_earth_csa:.0f}mm²)")

with col_audit2:
    with st.container(border=True):
        st.markdown("#### 📝 Fields Left Blank for Manual Entry")
        st.write("• **Pricing Columns:** `Unit Price` & `Total Price` left 100% blank")
        st.write("• **Mounting Hardware:** Mid clamps, end clamps, tile roof hooks, L-feet (site measured)")
        st.write("• **Cable Management:** PVC conduits, bends, couplers, cable trunking, saddles")
        st.write("• **Enclosure Hardware:** Steel distribution box, ABC box (site-specific)")
        st.write("• **Supplier Selection:** Supplier names & procurement quotes")

st.markdown("---")

# ---------------------------------------------------------------------------
# SECTION 2: Interactive BOQ Preview
# ---------------------------------------------------------------------------
st.markdown("### 2. Interactive Schedule Preview & Quantity Review")
st.caption("Review quantities derived from the dynamic engineering design before exporting to Master Excel.")

df_preview = pd.DataFrame(boq_items)
# Coerce quantity to numeric float64 so Streamlit's NumberColumn is compatible.
# None/NaN values (fuses not required) display as empty cells.
df_preview["quantity"] = pd.to_numeric(df_preview["quantity"], errors="coerce")

edited_df = st.data_editor(
    df_preview[["sn", "description", "brand", "capacity", "unit", "quantity", "notes"]],
    column_config={
        "sn": st.column_config.NumberColumn("S/N", disabled=True, width="small"),
        "description": st.column_config.TextColumn("Description", width="medium"),
        "brand": st.column_config.TextColumn("Brand / Manufacturer", width="medium"),
        "capacity": st.column_config.TextColumn("Capacity / Model Specification", width="large"),
        "unit": st.column_config.TextColumn("Unit", width="small"),
        "quantity": st.column_config.NumberColumn(
            "Quantity",
            min_value=0.0,
            step=1.0,
            format="%g",
            width="small",
            help="Engineering-calculated quantity. Edit to override before export.",
        ),
        "notes": st.column_config.TextColumn("Engineering Notes", disabled=True, width="large"),
    },
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")

# ---------------------------------------------------------------------------
# SECTION 3: One-Click Excel Generation & Download
# ---------------------------------------------------------------------------
st.markdown("### 3. Generate & Download Official Master Excel BOQ")


# Apply user-edited quantities back to boq_items for Excel export
for i, item in enumerate(boq_items):
    if i < len(edited_df):
        edited_qty = edited_df.iloc[i]["quantity"]
        if pd.notna(edited_qty):
            item["quantity"] = edited_qty

project_meta = {
    "customer_name": proj.get("customer_name", "Solar Client"),
    "system_capacity_kw": ac_kw,
    "capacity_kw": ac_kw,
    "date": datetime.datetime.now().strftime("%d/%m/%Y"),
    "phase_desc": "Single Phase 230V" if proj.get("grid_phases", 1) == 1 else "Three Phase 400V",
}

col_d1, col_d2 = st.columns(2)

with col_d1:
    with st.container(border=True):
        st.markdown("#### 📑 Exact Master Template (sample_boq.xlsx)")
        st.caption("Injects data directly into `data/BOQ/sample_boq.xlsx` preserving exact merged rows, layout, and Sheet2 utility switch.")

        try:
            excel_bytes = generate_master_template_boq_excel(
                boq_items=boq_items,
                project_metadata=project_meta
            )
            file_name = f"Solar_BOQ_{int(ac_kw)}kW_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx"
            st.download_button(
                label="📥 Download Master Template BOQ (Excel)",
                data=excel_bytes,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
            st.success("✅ Master Template Excel prepared successfully!")
        except Exception as e:
            st.error(f"Error generating template: {e}")

with col_d2:
    with st.container(border=True):
        st.markdown("#### 📊 Clean Structured Excel Schedule")
        st.caption("Alternative clean tabular workbook with categorized tables and engineering proofs.")

        try:
            clean_excel = generate_boq_excel(
                boq_items=boq_items,
                project_metadata=project_meta
            )
            st.download_button(
                label="📥 Download Clean Structured BOQ (Excel)",
                data=clean_excel,
                file_name=f"Solar_Schedule_{int(ac_kw)}kW_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error generating clean excel: {e}")
