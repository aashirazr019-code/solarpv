import streamlit as st
from ui.components import page_header, render_result_card
from ui.equipment_forms import panel_picker, inverter_picker
from core.current_check import current_check

try:
    st.set_page_config(page_title="DC Current Validation", page_icon="⚡", layout="wide")
except Exception:
    pass

page_header("DC Current Validation", "Verify maximum string currents against MPPT limits", icon="⚡")

col1, col2 = st.columns(2)
with col1:
    panel = panel_picker("dc_curr_panel")
with col2:
    inverter = inverter_picker("dc_curr_inv")

strings_per_mppt = st.number_input("Strings per MPPT", min_value=1, max_value=10, value=2, step=1)

if st.button("Validate Current limits", type="primary"):
    try:
        result = current_check(panel, inverter, strings_per_mppt)
        
        render_result_card(
            "Short Circuit Current Check",
            [
                {"label": "Total Isc", "value": result['isc_current_a'], "unit": "A"},
                {"label": "Inverter Max Isc per MPPT", "value": result['limit_isc_a'], "unit": "A"}
            ],
            status=result['status'],
            explanation=f"Checks if the combined short circuit current of {strings_per_mppt} strings exceeds the inverter's MPPT limit."
        )

        st.info(f"Operating Current (Imp): {result['operating_current_a']} A")
        st.info(f"Margin: {result['margin_pct']}%")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
