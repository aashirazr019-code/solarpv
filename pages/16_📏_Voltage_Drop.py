import streamlit as st
from ui.components import page_header, render_result_card, render_calculation_proof
from core.voltage_drop import voltage_drop_dc, voltage_drop_ac_3phase, voltage_drop_ac_1phase

try:
    st.set_page_config(page_title="Voltage Drop", page_icon="📏", layout="wide")
except Exception:
    pass

page_header("Detailed Voltage Drop", "Accurate voltage drop calculation for DC and AC circuits", icon="📏")

circuit_type = st.selectbox("Circuit Type", ["DC", "AC 1-Phase", "AC 3-Phase"])

col1, col2 = st.columns(2)
with col1:
    csa_mm2 = st.number_input("Cable Cross Section (mm²)", min_value=1.5, value=6.0)
    current_a = st.number_input("Operating Current (A)", min_value=0.1, value=15.0)
    length_m = st.number_input("Cable Length (m)", min_value=1.0, value=50.0)

with col2:
    nominal_voltage = st.number_input("Nominal Voltage (V)", min_value=12.0, value=400.0)
    cond_temp = st.number_input("Conductor Temp (°C)", min_value=20.0, value=70.0)
    pf = 1.0
    if "AC" in circuit_type:
        pf = st.number_input("Power Factor", min_value=0.1, max_value=1.0, value=1.0)

if st.button("Calculate Voltage Drop", type="primary"):
    try:
        if circuit_type == "DC":
            res = voltage_drop_dc(csa_mm2, current_a, length_m, nominal_voltage, cond_temp)
        elif circuit_type == "AC 1-Phase":
            res = voltage_drop_ac_1phase(csa_mm2, current_a, length_m, nominal_voltage, pf, cond_temp)
        else:
            res = voltage_drop_ac_3phase(csa_mm2, current_a, length_m, nominal_voltage, pf, cond_temp)

        render_result_card(
            f"{circuit_type} Voltage Drop Results",
            [
                {"label": "Voltage Drop", "value": res['drop_v'], "unit": "V"},
                {"label": "Voltage Drop %", "value": res['drop_pct'], "unit": "%"},
                {"label": "Power Loss", "value": res['power_loss_w'], "unit": "W"}
            ],
            status=res['status']
        )
        
        render_calculation_proof("Calculation Details", res["show_calculation"])

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
