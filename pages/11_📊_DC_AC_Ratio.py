import streamlit as st
from ui.components import page_header, render_result_card, render_calculation_proof
from ui.equipment_forms import inverter_picker, dc_ac_ratio_inputs
from core.models import Project, SpacingConfig
from core.dc_ac_ratio import dc_ac_ratio

try:
    st.set_page_config(page_title="DC/AC Ratio", page_icon="📊", layout="wide")
except Exception:
    pass

page_header("DC/AC Ratio Calculator", "Calculate the oversizing factor of the PV array relative to the inverter AC capacity", icon="📊")

col1, col2 = st.columns(2)
with col1:
    panel_qty = st.number_input("Total Panel Quantity", min_value=1, value=12, step=1)
    panel_rated_wp = st.number_input("Panel Rated Power (Wp)", min_value=100.0, value=630.0, step=5.0)

with col2:
    inverter = inverter_picker("dc_ac_inv")
    inverter_qty = st.number_input("Number of Inverter Units", min_value=1, value=1, step=1)

min_ratio, pref_ratio, max_ratio = dc_ac_ratio_inputs("dc_ac_ratio")

if st.button("Calculate DC/AC Ratio", type="primary"):
    try:
        project = Project(
            id='calc', name='Calculator', location='', installation_type='rooftop',
            target_ac_capacity_kw=inverter.rated_ac_power_kw * inverter_qty, min_design_temp_c=-30.0, max_design_temp_c=60.0,
            dc_ac_ratio_min=min_ratio, dc_ac_ratio_preferred=pref_ratio, dc_ac_ratio_max=max_ratio,
            panel_id='', panel_available_qty=9999, 
            area_length_m=100, area_width_m=100, spacing_config=SpacingConfig()
        )
        
        breakdown = [{"inverter": inverter, "quantity": inverter_qty}]
        result = dc_ac_ratio(panel_qty, panel_rated_wp, breakdown, project)
        
        render_result_card(
            "DC/AC Ratio Check",
            [
                {"label": "DC Capacity", "value": result['dc_capacity_kwp'], "unit": "kWp"},
                {"label": "AC Capacity", "value": result['ac_capacity_kw'], "unit": "kW"},
                {"label": "DC/AC Ratio", "value": result['ratio'], "unit": ""}
            ],
            status=result['status'],
            explanation=f"Compares installed DC capacity against total inverter nominal AC output. Recommended range is {min_ratio} - {max_ratio}."
        )
        
        render_calculation_proof("Calculation Details", result["show_calculation"])

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
