import streamlit as st
from ui.components import page_header, render_result_card, render_calculation_proof
from core.earthing import calculate_earth_rod_resistance, calculate_earth_rods_required, calculate_earth_conductor_size

try:
    st.set_page_config(page_title="Earthing Design", page_icon="🌍", layout="wide")
except Exception:
    pass

page_header("Earthing Design", "Calculate rod resistance, quantity, and conductor size", icon="🌍")

col1, col2 = st.columns(2)
with col1:
    soil_res = st.number_input("Soil Resistivity (Ohm.m)", min_value=1.0, value=100.0)
    rod_length = st.number_input("Rod Length (m)", min_value=1.0, value=3.0)
    rod_diameter = st.number_input("Rod Diameter (mm)", min_value=10.0, value=16.0)
with col2:
    target_res = st.number_input("Target Resistance (Ohm)", min_value=0.1, value=5.0)
    fault_current = st.number_input("Max Fault Current (A)", min_value=100.0, value=1000.0)
    clear_time = st.number_input("Clearing Time (s)", min_value=0.1, value=1.0)

if st.button("Calculate Earthing", type="primary"):
    try:
        rod_res = calculate_earth_rod_resistance(soil_res, rod_length, rod_diameter)
        render_result_card(
            "Single Rod Resistance",
            [{"label": "Resistance", "value": rod_res['resistance_ohm'], "unit": "Ω"}],
            status=rod_res['status']
        )
        render_calculation_proof("Rod Calc", rod_res["show_calculation"])
        
        qty_res = calculate_earth_rods_required(rod_res['resistance_ohm'], target_res)
        render_result_card(
            "Required Rods",
            [{"label": "Quantity", "value": qty_res['rods_required'], "unit": "rods"}],
            status=qty_res['status']
        )
        
        cond_res = calculate_earth_conductor_size(fault_current, clear_time)
        render_result_card(
            "Earth Conductor Sizing",
            [{"label": "Min CSA", "value": cond_res['min_csa_mm2'], "unit": "mm²"}],
            status=cond_res['status']
        )
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
