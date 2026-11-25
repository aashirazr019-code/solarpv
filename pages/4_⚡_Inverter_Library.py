import streamlit as st
from ui.components import page_header, nav_sidebar
from ui.styles import apply_custom_css
from data.library_data import INVERTER_FAMILIES, build_inverter
from data.database import list_inverters, save_inverter, delete_inverter

try:
    st.set_page_config(page_title='Inverter Library — Solar PV Platform', page_icon='⚡', layout='wide')
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("Inverter Master Library", "Explore manufacturer datasheets, verified Tier-1 brands (Sunways, Huawei, Sungrow), and custom inverters", icon="⚡")

tab_lib, tab_add = st.tabs(["📚 Inverter Catalog", "➕ Add Custom Inverter"])

with tab_lib:
    col_search, col_fam = st.columns([2, 2])
    family_options = ["All Families"] + [f"{f.get('manufacturer', 'Sunways')} — {f['series']}" for f in INVERTER_FAMILIES]
    selected_fam_label = col_fam.selectbox("Filter by Series", family_options)
    search_txt = col_search.text_input("🔍 Search by power (kW), model, or series", "")
    
    # Collect all inverters from library
    all_inverters = []
    for fam in INVERTER_FAMILIES:
        fam_label = f"{fam.get('manufacturer', 'Sunways')} — {fam['series']}"
        if selected_fam_label != "All Families" and fam_label != selected_fam_label:
            continue
        for var in fam["variants"]:
            inv = build_inverter(fam, var)
            all_inverters.append(inv)
            
    # Include saved custom inverters from DB
    try:
        custom_invs = list_inverters()
        for ci in custom_invs:
            from core.models import Inverter
            inv = Inverter(
                id=ci.get("id", ""),
                manufacturer=ci.get("manufacturer", "Custom"),
                model=ci.get("model", ""),
                rated_ac_power_kw=ci.get("rated_ac_power_kw", 50.0),
                max_dc_input_power_kw=ci.get("max_dc_input_power_kw", 65.0),
                max_dc_voltage_v=ci.get("max_dc_voltage_v", 1100.0),
                mppt_voltage_min_v=ci.get("mppt_voltage_min_v", 200.0),
                mppt_voltage_max_v=ci.get("mppt_voltage_max_v", 950.0),
                mppt_count=int(ci.get("mppt_count", 4)),
                string_inputs_per_mppt=int(ci.get("string_inputs_per_mppt", 2)),
                max_input_current_per_mppt_a=ci.get("max_input_current_per_mppt_a", 26.0),
                max_isc_per_mppt_a=ci.get("max_isc_per_mppt_a", 35.0),
                max_total_dc_current_a=ci.get("max_total_dc_current_a", 104.0),
                ac_voltage=ci.get("ac_voltage", 400.0),
                rated_ac_current_a=ci.get("rated_ac_current_a", 72.0),
                max_ac_current_a=ci.get("max_ac_current_a", 80.0),
                efficiency_pct=ci.get("efficiency_pct", 98.6),
                source="custom"
            )
            all_inverters.append(inv)
    except Exception:
        pass

    # Filter
    if search_txt.strip():
        stxt = search_txt.lower()
        all_inverters = [i for i in all_inverters if stxt in i.model.lower() or stxt in str(i.rated_ac_power_kw)]

    st.markdown(f"**Showing {len(all_inverters)} verified Inverter models:**")
    
    for inv in all_inverters:
        with st.container(border=True):
            h1, h2 = st.columns([3, 1])
            h1.markdown(f"### {inv.manufacturer} {inv.model} ({inv.rated_ac_power_kw} kW)")
            h1.caption(f"Grid: **{inv.grid_type}** ({inv.ac_voltage}V) | MPPT Trackers: **{inv.mppt_count}** ({inv.string_inputs_per_mppt} strings/MPPT) | Efficiency: **{inv.efficiency_pct}%**")
            
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Rated AC Power", f"{inv.rated_ac_power_kw} kW")
            c2.metric("Max DC Input", f"{inv.max_dc_voltage_v} V")
            c3.metric("MPPT Range", f"{inv.mppt_voltage_min_v} - {inv.mppt_voltage_max_v} V")
            c4.metric("Max Isc / MPPT", f"{inv.max_isc_per_mppt_a} A")
            c5.metric("Operating I / MPPT", f"{inv.max_input_current_per_mppt_a} A")
            c6.metric("Max AC Output I", f"{inv.max_ac_current_a} A")

with tab_add:
    st.subheader("Add Custom Inverter to Platform")
    
    with st.form("custom_inv_form"):
        r1_1, r1_2 = st.columns(2)
        mfr = r1_1.text_input("Manufacturer *", value="Tier-1 Inverters")
        model = r1_2.text_input("Model Designation *", value="TI-120KTL")
        
        r2_1, r2_2, r2_3 = st.columns(3)
        rated_ac = r2_1.number_input("Rated AC Power (kW) *", value=120.0, step=5.0)
        ac_voltage = r2_2.selectbox("Nominal AC Voltage (V)", [400.0, 230.0, 480.0, 500.0, 690.0])
        efficiency = r2_3.number_input("Peak Efficiency (%)", value=98.8, step=0.1)
        
        st.markdown("#### DC Operating Parameters")
        d1, d2, d3 = st.columns(3)
        max_dc_v = d1.number_input("Max DC Voltage (V) *", value=1100.0, step=50.0)
        mppt_min = d2.number_input("MPPT Min Tracking Voltage (V) *", value=200.0, step=10.0)
        mppt_max = d3.number_input("MPPT Max Tracking Voltage (V) *", value=1000.0, step=10.0)
        
        st.markdown("#### MPPT & Input Current Limits")
        i1, i2, i3, i4 = st.columns(4)
        mppt_count = i1.number_input("MPPT Trackers (Count)", value=10, min_value=1, step=1)
        strings_per_mppt = i2.number_input("String Inputs per MPPT", value=2, min_value=1, step=1)
        max_i_mppt = i3.number_input("Max Operating Current / MPPT (A)", value=30.0, step=1.0)
        max_isc_mppt = i4.number_input("Max Isc / MPPT (A)", value=40.0, step=1.0)
        
        save_btn = st.form_submit_button("💾 Save Inverter to Master Library", type="primary")
        if save_btn:
            if mppt_min >= mppt_max:
                st.error("MPPT Min Voltage must be less than MPPT Max Voltage.")
            elif mppt_max > max_dc_v:
                st.error("MPPT Max Voltage cannot exceed Inverter Max DC Voltage.")
            else:
                import uuid, math
                inv_id = f"custom-{uuid.uuid4().hex[:8]}"
                calc_ac_current = round((rated_ac * 1000) / (math.sqrt(3) * ac_voltage), 1)
                inv_dict = {
                    "id": inv_id,
                    "manufacturer": mfr.strip(),
                    "model": model.strip(),
                    "rated_ac_power_kw": float(rated_ac),
                    "max_dc_input_power_kw": float(rated_ac * 1.35),
                    "max_dc_voltage_v": float(max_dc_v),
                    "mppt_voltage_min_v": float(mppt_min),
                    "mppt_voltage_max_v": float(mppt_max),
                    "mppt_count": int(mppt_count),
                    "string_inputs_per_mppt": int(strings_per_mppt),
                    "max_input_current_per_mppt_a": float(max_i_mppt),
                    "max_isc_per_mppt_a": float(max_isc_mppt),
                    "max_total_dc_current_a": float(max_i_mppt * mppt_count),
                    "ac_voltage": float(ac_voltage),
                    "rated_ac_current_a": calc_ac_current,
                    "max_ac_current_a": round(calc_ac_current * 1.1, 1),
                    "efficiency_pct": float(efficiency),
                    "source": "custom"
                }
                save_inverter(inv_dict)
                st.success(f"✅ Inverter **{mfr} {model}** saved to library!")
                st.rerun()
