import streamlit as st
from core.models import Panel, Inverter
from data.library_data import PANEL_FAMILIES, INVERTER_FAMILIES, build_panel, build_inverter

def panel_picker(key_prefix):
    """
    Controlled modes: Approved Panels (580W, 615W, 630W Default), Full Library, or Custom / Manual entry.
    Returns a Panel dataclass.
    """
    from core.project_state import get_approved_panels
    approved_list = get_approved_panels()

    mode = st.radio(
        'Panel source',
        ['Approved Panels (580W / 615W / 630W)', 'Full Library (Yingli, Jinko, LONGi, JA)', 'Custom Panel / Manual entry'],
        key=f'{key_prefix}_mode',
        horizontal=True
    )
    
    if mode.startswith('Approved Panels'):
        labels = [f"{p.rated_power_wp:.0f} Wp — {p.model}" + (" ⭐ (Default)" if p.rated_power_wp == 630.0 else "") for p in approved_list]
        # 630W is index 2
        default_idx = 2 if len(approved_list) >= 3 else 0
        selected_idx = st.selectbox(
            'Select Approved Panel',
            range(len(approved_list)),
            index=default_idx,
            format_func=lambda i: labels[i],
            key=f'{key_prefix}_appr_idx'
        )
        return approved_list[selected_idx]

    if mode.startswith('Full Library'):
        family_names = [f"{f.get('manufacturer', 'Yingli')} — {f['series']}" for f in PANEL_FAMILIES]
        family_idx = st.selectbox('Panel family', range(len(family_names)), format_func=lambda i: family_names[i], key=f'{key_prefix}_fam', index=3 if len(family_names) > 3 else 0)
        family = PANEL_FAMILIES[family_idx]
        wp_options = [v['wp'] for v in family['variants']]
        wp = st.selectbox('Wattage (Wp)', wp_options, index=len(wp_options)-1, key=f'{key_prefix}_wp')
        variant = next(v for v in family['variants'] if v['wp'] == wp)
        return build_panel(family, variant)
    
    # Custom Panel / Manual entry
    c1, c2 = st.columns(2)
    manufacturer = c1.text_input('Manufacturer', 'Yingli Solar', key=f'{key_prefix}_m_mfr')
    model = c2.text_input('Model', 'PANDA 3.0 Pro 2 CF66-630W', key=f'{key_prefix}_m_model')
    c1, c2, c3, c4 = st.columns(4)
    wp = c1.number_input('Rated Power (Wp)', value=630.0, key=f'{key_prefix}_m_wp')
    voc = c2.number_input('Voc (V)', value=49.44, key=f'{key_prefix}_m_voc')
    vmp = c3.number_input('Vmp (V)', value=41.47, key=f'{key_prefix}_m_vmp')
    isc = c4.number_input('Isc (A)', value=16.18, key=f'{key_prefix}_m_isc')
    c1, c2, c3, c4 = st.columns(4)
    imp = c1.number_input('Imp (A)', value=15.19, key=f'{key_prefix}_m_imp')
    tc_voc = c2.number_input('Temp Coeff Voc (%/°C)', value=-0.24, format='%.3f', key=f'{key_prefix}_m_tcvoc')
    tc_isc = c3.number_input('Temp Coeff Isc (%/°C)', value=0.042, format='%.3f', key=f'{key_prefix}_m_tcisc')
    tc_pmax = c4.number_input('Temp Coeff Pmax (%/°C)', value=-0.29, format='%.3f', key=f'{key_prefix}_m_tcpmax')
    has_tc_vmp = st.checkbox('Datasheet has separate Temp Coeff Vmp?', value=True, key=f'{key_prefix}_m_has_tcvmp')
    tc_vmp = None
    if has_tc_vmp:
        tc_vmp = st.number_input('Temp Coeff Vmp (%/°C)', value=-0.26, format='%.3f', key=f'{key_prefix}_m_tcvmp')
    c1, c2, c3, c4 = st.columns(4)
    length_m = c1.number_input('Length (m)', value=2.382, key=f'{key_prefix}_m_len')
    width_m = c2.number_input('Width (m)', value=1.134, key=f'{key_prefix}_m_wid')
    max_sys_v = c3.number_input('Max System Voltage (V)', value=1500.0, key=f'{key_prefix}_m_maxsys')
    max_fuse = c4.number_input('Max Series Fuse (A)', value=30.0, key=f'{key_prefix}_m_maxfuse')
    
    return Panel(
        id=f'manual-{key_prefix}', manufacturer=manufacturer, model=model,
        rated_power_wp=wp, voc=voc, vmp=vmp, isc=isc, imp=imp,
        max_system_voltage=max_sys_v, max_series_fuse=max_fuse,
        temp_coeff_voc=tc_voc, temp_coeff_vmp=tc_vmp, temp_coeff_isc=tc_isc, temp_coeff_pmax=tc_pmax,
        length_m=length_m, width_m=width_m, thickness_mm=30, weight_kg=33.0,
        cell_technology='user-entered', cell_count=132, source='manual',
    )

def inverter_picker(key_prefix):
    """
    Two modes: Library or Manual entry. Returns an Inverter dataclass.
    Defaults to 5 kW STS-5KTL-P (1-Phase, 230V, 2 MPPT).
    """
    mode = st.radio('Inverter source', ['Library (Sunways, Huawei, Sungrow)', 'Manual entry'], key=f'{key_prefix}_mode', horizontal=True)
    
    if mode.startswith('Library'):
        family_names = [f"{f.get('manufacturer', 'Sunways')} — {f['series']}" for f in INVERTER_FAMILIES]
        # Default to STS-3~6KTL-P (index 2)
        default_fam = 2 if len(family_names) > 2 else 0
        family_idx = st.selectbox('Inverter family', range(len(family_names)), format_func=lambda i: family_names[i], key=f'{key_prefix}_fam', index=default_fam)
        family = INVERTER_FAMILIES[family_idx]
        model_names = [v['model'] for v in family['variants']]
        # If STS series selected, default to STS-5KTL-P (index 4)
        default_model = 4 if len(model_names) > 4 and family.get('series') == 'sunways-sts-3-6ktl-p' else 0
        model_idx = st.selectbox('Model', range(len(model_names)), format_func=lambda i: model_names[i], key=f'{key_prefix}_model', index=default_model)
        variant = family['variants'][model_idx]
        return build_inverter(family, variant)
    
    # Manual entry - default to 5 kW 1-Phase
    c1, c2 = st.columns(2)
    manufacturer = c1.text_input('Manufacturer', 'Sunways', key=f'{key_prefix}_m_mfr')
    model = c2.text_input('Model', 'STS-5KTL-P', key=f'{key_prefix}_m_model')
    c1, c2, c3, c4 = st.columns(4)
    rated_ac_kw = c1.number_input('Rated AC Power (kW)', value=5.0, key=f'{key_prefix}_m_rac')
    max_dc_v = c2.number_input('Max DC Voltage (V)', value=600.0, key=f'{key_prefix}_m_maxdc')
    mppt_min = c3.number_input('MPPT Min Voltage (V)', value=100.0, key=f'{key_prefix}_m_mpptmin')
    mppt_max = c4.number_input('MPPT Max Voltage (V)', value=550.0, key=f'{key_prefix}_m_mpptmax')
    c1, c2, c3, c4 = st.columns(4)
    mppt_count = c1.number_input('MPPT Count', min_value=1, value=2, step=1, key=f'{key_prefix}_m_mpptcount')
    strings_per_mppt = c2.number_input('String Inputs per MPPT', min_value=1, value=1, step=1, key=f'{key_prefix}_m_strperm')
    max_current = c3.number_input('Max Input Current/MPPT (A)', value=15.0, key=f'{key_prefix}_m_maxcur')
    max_isc = c4.number_input('Max Isc/MPPT (A)', value=20.0, key=f'{key_prefix}_m_maxisc')
    c1, c2, c3 = st.columns(3)
    ac_voltage = c1.number_input('AC Voltage (V)', value=230.0, key=f'{key_prefix}_m_acv')
    efficiency = c2.number_input('Efficiency (%)', value=98.1, key=f'{key_prefix}_m_eff')
    max_dc_input_kw = c3.number_input('Max DC Input Power (kW)', value=6.5, key=f'{key_prefix}_m_maxdcin')
    default_ac_current = 22.0
    max_ac_current = st.number_input('Max AC Output Current (A)', value=default_ac_current, key=f'{key_prefix}_m_maxac',
        help='From datasheet Max Output Current row. Defaults to 22A for 5kW 230V.')
    
    return Inverter(
        id=f'manual-{key_prefix}', manufacturer=manufacturer, model=model,
        rated_ac_power_kw=rated_ac_kw, max_dc_input_power_kw=max_dc_input_kw,
        max_dc_voltage_v=max_dc_v, mppt_voltage_min_v=mppt_min, mppt_voltage_max_v=mppt_max,
        mppt_count=int(mppt_count), string_inputs_per_mppt=int(strings_per_mppt),
        max_input_current_per_mppt_a=max_current, max_isc_per_mppt_a=max_isc,
        max_total_dc_current_a=max_current*mppt_count, ac_voltage=ac_voltage,
        rated_ac_current_a=max_ac_current, max_ac_current_a=max_ac_current, efficiency_pct=efficiency,
        source='manual',
    )

def design_temperature_inputs(key_prefix, default_min=-30.0, default_max=60.0):
    """Standard temperature inputs used across multiple calculators with central defaults (-30 °C to 60 °C)."""
    if "active_project" in st.session_state and st.session_state.active_project:
        p = st.session_state.active_project
        default_min = float(p.get("min_design_temp_c", default_min))
        default_max = float(p.get("max_design_temp_c", default_max))
    c1, c2 = st.columns(2)
    min_temp = c1.number_input('Min Design Temp (°C)', value=default_min, key=f'{key_prefix}_min_temp',
        help='Record minimum ambient temperature at site. Used for cold Voc calculation. Default -30 °C.')
    max_temp = c2.number_input('Max Design Temp (°C)', value=default_max, key=f'{key_prefix}_max_temp',
        help='Record maximum ambient temperature at site. Used for hot Vmp calculation. Default 60 °C.')
    return min_temp, max_temp

def dc_ac_ratio_inputs(key_prefix):
    """Standard DC/AC ratio range inputs."""
    c1, c2, c3 = st.columns(3)
    dc_ac_min = c1.number_input('DC/AC Ratio Min', value=1.05, key=f'{key_prefix}_dcac_min')
    dc_ac_pref = c2.number_input('DC/AC Ratio Preferred', value=1.20, key=f'{key_prefix}_dcac_pref')
    dc_ac_max = c3.number_input('DC/AC Ratio Max', value=1.35, key=f'{key_prefix}_dcac_max')
    return dc_ac_min, dc_ac_pref, dc_ac_max

def spacing_inputs(key_prefix):
    """Standard spacing configuration inputs."""
    from core.models import SpacingConfig
    with st.expander('Spacing Configuration (Advanced)', expanded=False):
        c1, c2, c3, c4, c5 = st.columns(5)
        panel_gap = c1.number_input('Panel gap (m)', value=0.02, key=f'{key_prefix}_pgap')
        row_gap = c2.number_input('Row gap (m)', value=0.5, key=f'{key_prefix}_rgap')
        edge_clearance = c3.number_input('Edge clearance (m)', value=1.0, key=f'{key_prefix}_edge')
        walkway = c4.number_input('Walkway (m)', value=1.2, key=f'{key_prefix}_walk')
        inverter_access = c5.number_input('Inverter access (m)', value=2.0, key=f'{key_prefix}_invacc')
    return SpacingConfig(panel_gap, row_gap, edge_clearance, walkway, inverter_access)
