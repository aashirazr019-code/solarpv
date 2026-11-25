import streamlit as st
from ui.components import page_header, render_result_card, render_calculation_proof
from ui.equipment_forms import panel_picker, inverter_picker, design_temperature_inputs
from core.models import Project, SpacingConfig
from core.string_sizing import panels_per_string_range, voltage_check

try:
    st.set_page_config(page_title="String Sizing", page_icon="🔌", layout="wide")
except Exception:
    pass

page_header("String Sizing Calculator", "Calculate the minimum and maximum number of panels per string", icon="🔌")

col1, col2 = st.columns(2)
with col1:
    panel = panel_picker("str_sizing_panel")
with col2:
    inverter = inverter_picker("str_sizing_inv")

st.markdown("### Design Temperatures")
min_temp, max_temp = design_temperature_inputs("str_sizing_temp")

if st.button("Calculate Valid Range", type="primary"):
    try:
        project = Project(
            id='calc', name='Calculator', location='', installation_type='rooftop',
            target_ac_capacity_kw=100, min_design_temp_c=min_temp, max_design_temp_c=max_temp,
            dc_ac_ratio_min=1.0, dc_ac_ratio_preferred=1.2, dc_ac_ratio_max=1.5,
            panel_id=panel.id if panel else '', panel_available_qty=9999, 
            area_length_m=100, area_width_m=100, spacing_config=SpacingConfig()
        )
        
        result = panels_per_string_range(panel, inverter, project)
        
        if not result["valid"]:
            st.error("No valid string lengths found for this combination.")
        else:
            st.success(f"Valid range: {result['min_panels_per_string']} to {result['max_panels_per_string']} panels per string.")
            
            st.markdown("### Detailed Voltage Checks")
            v_check_min = voltage_check(panel, inverter, project, result['min_panels_per_string'])
            v_check_max = voltage_check(panel, inverter, project, result['max_panels_per_string'])
            
            c1, c2 = st.columns(2)
            with c1:
                render_result_card(
                    "Cold Voc Check (Max Panels)",
                    [
                        {"label": "Calculated Max Voc", "value": v_check_max['cold']['calculated_v'], "unit": "V"},
                        {"label": "Inverter Max DC Input", "value": v_check_max['cold']['limit_v'], "unit": "V"}
                    ],
                    status=v_check_max['cold']['status'],
                    explanation="Checking maximum string voltage against inverter absolute max at lowest design temperature."
                )
            with c2:
                render_result_card(
                    "Hot Vmp Check (Min Panels)",
                    [
                        {"label": "Calculated Min Vmp", "value": v_check_min['hot']['calculated_v'], "unit": "V"},
                        {"label": "Inverter MPPT Min", "value": v_check_min['hot']['min_v'], "unit": "V"}
                    ],
                    status=v_check_min['hot']['status'],
                    explanation="Checking minimum string operating voltage against MPPT voltage range at highest design temperature."
                )
            
            # Convert show_calculation dict to list of step dicts for the proof renderer
            calc = result["show_calculation"]
            steps = [{"label": k.replace("_", " ").title(), "value": v}
                     for k, v in calc.items() if v is not None]
            render_calculation_proof("String Sizing Calculation", steps)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
