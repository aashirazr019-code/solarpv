import streamlit as st
from ui.components import page_header, nav_sidebar
from ui.styles import apply_custom_css
from data.library_data import PANEL_FAMILIES, build_panel
from data.database import list_panels, save_panel, delete_panel

try:
    st.set_page_config(page_title='Panel Library — Solar PV Platform', page_icon='🔋', layout='wide')
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("PV Module Master Library", "Explore manufacturer datasheets, verified Tier-1 brands (Jinko, LONGi, JA Solar, Yingli), and custom modules", icon="🔋")

tab_lib, tab_add = st.tabs(["📚 Module Catalog", "➕ Add Custom Module"])

with tab_lib:
    col_search, col_fam = st.columns([2, 2])
    family_options = ["All Families"] + [f"{f.get('manufacturer', 'Yingli')} — {f['series']}" for f in PANEL_FAMILIES]
    selected_fam_label = col_fam.selectbox("Filter by Series", family_options)
    search_txt = col_search.text_input("🔍 Search by wattage, cell tech, or model", "")
    
    # Collect all modules from library
    all_modules = []
    for fam in PANEL_FAMILIES:
        fam_label = f"{fam.get('manufacturer', 'Yingli')} — {fam['series']}"
        if selected_fam_label != "All Families" and fam_label != selected_fam_label:
            continue
        for var in fam["variants"]:
            p = build_panel(fam, var)
            all_modules.append(p)
            
    # Include saved custom panels from DB
    try:
        custom_panels = list_panels()
        for cp in custom_panels:
            # cp is a dict from db
            from core.models import Panel
            p = Panel(
                id=cp.get("id", ""),
                manufacturer=cp.get("manufacturer", "Custom"),
                model=cp.get("model", ""),
                rated_power_wp=cp.get("rated_power_wp", 500.0),
                voc=cp.get("voc", 45.0),
                vmp=cp.get("vmp", 38.0),
                isc=cp.get("isc", 13.0),
                imp=cp.get("imp", 12.0),
                max_system_voltage=cp.get("max_system_voltage", 1500.0),
                max_series_fuse=cp.get("max_series_fuse", 25.0),
                temp_coeff_voc=cp.get("temp_coeff_voc", -0.25),
                temp_coeff_vmp=cp.get("temp_coeff_vmp", None),
                temp_coeff_isc=cp.get("temp_coeff_isc", 0.045),
                temp_coeff_pmax=cp.get("temp_coeff_pmax", -0.34),
                length_m=cp.get("length_m", 2.2),
                width_m=cp.get("width_m", 1.1),
                thickness_mm=cp.get("thickness_mm", 30.0),
                weight_kg=cp.get("weight_kg", 28.0),
                cell_technology=cp.get("cell_technology", "Mono"),
                cell_count=cp.get("cell_count", 144),
                source="custom"
            )
            all_modules.append(p)
    except Exception:
        pass

    # Filter
    if search_txt.strip():
        stxt = search_txt.lower()
        all_modules = [m for m in all_modules if stxt in m.model.lower() or stxt in str(m.rated_power_wp) or stxt in m.cell_technology.lower()]

    st.markdown(f"**Showing {len(all_modules)} verified PV modules:**")
    
    for m in all_modules:
        with st.container(border=True):
            h1, h2 = st.columns([3, 1])
            h1.markdown(f"### {m.manufacturer} {m.model} ({m.rated_power_wp} Wp)")
            h1.caption(f"Cell Tech: **{m.cell_technology}** ({m.cell_count} cells) | Source: **{m.source.upper()}** | Max System Voltage: **{m.max_system_voltage}V**")
            
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Voc (STC)", f"{m.voc} V")
            c2.metric("Vmp (STC)", f"{m.vmp} V")
            c3.metric("Isc (STC)", f"{m.isc} A")
            c4.metric("Imp (STC)", f"{m.imp} A")
            c5.metric("Dimensions", f"{m.length_m} x {m.width_m} m")
            c6.metric("Max Fuse", f"{m.max_series_fuse} A")
            
            with st.expander("🔬 Temperature Coefficients & Mechanical Details", expanded=False):
                tc1, tc2, tc3 = st.columns(3)
                tc1.write(f"**γ (Pmax):** `{m.temp_coeff_pmax} %/°C`")
                tc2.write(f"**β (Voc):** `{m.temp_coeff_voc} %/°C`")
                tc3.write(f"**α (Isc):** `{m.temp_coeff_isc} %/°C`")
                st.caption(f"Weight: {m.weight_kg} kg | Frame Thickness: {m.thickness_mm} mm")

with tab_add:
    st.subheader("Add Custom PV Module to Platform")
    
    with st.form("custom_panel_form"):
        r1_1, r1_2 = st.columns(2)
        mfr = r1_1.text_input("Manufacturer *", value="Tier-1 Solar")
        model = r1_2.text_input("Model Designation *", value="TS-600W-TOPCon")
        
        r2_1, r2_2, r2_3 = st.columns(3)
        wp = r2_1.number_input("Rated Power (Wp) *", value=600.0, step=5.0)
        cell_tech = r2_2.selectbox("Cell Technology", ["N-type TOPCon", "Mono PERC", "HJT", "Bifacial TOPCon"])
        cell_count = r2_3.number_input("Cell Count", value=144, step=6)
        
        st.markdown("#### Electrical Ratings at STC (1000 W/m², 25°C)")
        e1, e2, e3, e4 = st.columns(4)
        voc = e1.number_input("Open-Circuit Voltage Voc (V) *", value=51.2, step=0.1)
        vmp = e2.number_input("Max Power Voltage Vmp (V) *", value=42.5, step=0.1)
        isc = e3.number_input("Short-Circuit Current Isc (A) *", value=14.8, step=0.1)
        imp = e4.number_input("Max Power Current Imp (A) *", value=14.1, step=0.1)
        
        st.markdown("#### Temperature Coefficients (% / °C)")
        tc1, tc2, tc3 = st.columns(3)
        tc_pmax = tc1.number_input("Temp Coeff Pmax (%/°C)", value=-0.30, format="%.3f")
        tc_voc = tc2.number_input("Temp Coeff Voc (%/°C)", value=-0.25, format="%.3f")
        tc_isc = tc3.number_input("Temp Coeff Isc (%/°C)", value=0.046, format="%.3f")
        
        st.markdown("#### Physical & Protection Specs")
        p1, p2, p3, p4 = st.columns(4)
        len_m = p1.number_input("Length (m)", value=2.278, step=0.01)
        wid_m = p2.number_input("Width (m)", value=1.134, step=0.01)
        max_sys = p3.number_input("Max System Voltage (V)", value=1500.0, step=100.0)
        max_fuse = p4.number_input("Max Series Fuse (A)", value=30.0, step=5.0)
        
        save_btn = st.form_submit_button("💾 Save Module to Master Library", type="primary")
        if save_btn:
            if vmp >= voc:
                st.error("Physics Error: Vmp must be strictly less than Voc.")
            elif imp >= isc:
                st.error("Physics Error: Imp must be strictly less than Isc.")
            else:
                import uuid
                panel_id = f"custom-{uuid.uuid4().hex[:8]}"
                p_dict = {
                    "id": panel_id,
                    "manufacturer": mfr.strip(),
                    "model": model.strip(),
                    "rated_power_wp": float(wp),
                    "voc": float(voc),
                    "vmp": float(vmp),
                    "isc": float(isc),
                    "imp": float(imp),
                    "max_system_voltage": float(max_sys),
                    "max_series_fuse": float(max_fuse),
                    "temp_coeff_voc": float(tc_voc),
                    "temp_coeff_vmp": None,
                    "temp_coeff_isc": float(tc_isc),
                    "temp_coeff_pmax": float(tc_pmax),
                    "length_m": float(len_m),
                    "width_m": float(wid_m),
                    "thickness_mm": 30.0,
                    "weight_kg": 32.0,
                    "cell_technology": cell_tech,
                    "cell_count": int(cell_count),
                    "source": "custom"
                }
                save_panel(p_dict)
                st.success(f"✅ Module **{mfr} {model}** saved to library!")
                st.rerun()
