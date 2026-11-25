import streamlit as st
from ui.components import page_header, render_result_card, render_calculation_proof
from ui.equipment_forms import panel_picker, inverter_picker, design_temperature_inputs
from core.models import Project, SpacingConfig
from core.string_sizing import voltage_check, panels_per_string_range

try:
    st.set_page_config(page_title="String Voltage", page_icon="🔍", layout="wide")
except Exception:
    pass

page_header("String Voltage Verification", "Verify voltage limits for a specific string length", icon="🔍")

col1, col2 = st.columns(2)
with col1:
    panel = panel_picker("str_volt_panel")
with col2:
    inverter = inverter_picker("str_volt_inv")

min_temp, max_temp = design_temperature_inputs("str_volt_temp")
panels_per_string = st.number_input("Panels per String", min_value=1, max_value=100, value=15, step=1)

if st.button("Verify Voltage limits", type="primary"):
    try:
        project = Project(
            id='calc', name='Calculator', location='', installation_type='rooftop',
            target_ac_capacity_kw=100, min_design_temp_c=min_temp, max_design_temp_c=max_temp,
            dc_ac_ratio_min=1.0, dc_ac_ratio_preferred=1.2, dc_ac_ratio_max=1.5,
            panel_id=panel.id if panel else '', panel_available_qty=9999, 
            area_length_m=100, area_width_m=100, spacing_config=SpacingConfig()
        )
        
        result = voltage_check(panel, inverter, project, panels_per_string)
        
        c1, c2 = st.columns(2)
        with c1:
            render_result_card(
                "Cold Condition (Voc)",
                [
                    {"label": "String Voc", "value": result['cold']['calculated_v'], "unit": "V"},
                    {"label": "Inverter Limit", "value": result['cold']['limit_v'], "unit": "V"}
                ],
                status=result['cold']['status'],
                explanation="Ensures the string open-circuit voltage at cold temperatures does not exceed the inverter absolute maximum."
            )
        with c2:
            render_result_card(
                "Hot Condition (Vmp)",
                [
                    {"label": "String Vmp", "value": result['hot']['calculated_v'], "unit": "V"},
                    {"label": "MPPT Range", "value": f"{result['hot']['min_v']} - {result['hot']['max_v']}", "unit": "V"}
                ],
                status=result['hot']['status'],
                explanation="Ensures the string maximum power point voltage at hot temperatures falls within the inverter MPPT operating range."
            )

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
