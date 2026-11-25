import streamlit as st
import math
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from core.protection_sizing import select_protective_device

try:
    st.set_page_config(page_title="MCCB Selection Calculator — Eng. Aashir", page_icon="🛡️", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("Molded Case Circuit Breaker (MCCB) Selection", "Size heavy-duty industrial MCCBs (100A to 1600A+) for plant incomers & main switchboards", icon="🛡️")

st.info("💡 **Engineering Note:** MCCBs are molded-case circuit breakers designed for higher continuous load currents (> 63A up to 1600A+), high short-circuit withstand levels (16kA to 100kA), and adjustable trip thresholds (thermal & magnetic/electronic).")

input_mode = st.radio("Current Derivation Method", ["Calculate from Load Power (kW)", "Direct Current Input (A)"], horizontal=True)

c1, c2 = st.columns(2)

if input_mode == "Calculate from Load Power (kW)":
    with c1:
        st.markdown("#### ⚡ Plant / Inverter AC Power")
        power_kw = st.number_input("Inverter / Main AC Power (kW)", min_value=10.0, max_value=50000.0, value=100.0, step=10.0)
        phases = 3
        volt = st.number_input("Nominal 3-Phase Voltage (V)", min_value=200.0, max_value=1000.0, value=400.0, step=15.0)
        pf = st.number_input("Power Factor (cos phi)", min_value=0.70, max_value=1.00, value=0.95, step=0.01)
        
        operating_current = (power_kw * 1000.0) / (math.sqrt(3.0) * volt * pf)
        st.info(f"Calculated 3-Phase Continuous Current ($I_b$): **{operating_current:.2f} A**")
    with c2:
        st.markdown("#### 🛡️ Protection & Coordination")
        safety_factor = st.number_input("Continuous Duty Multiplier", min_value=1.00, max_value=1.50, value=1.25, step=0.05)
        cable_ampacity = st.number_input("Total Conductor Group Ampacity Iz (A) [Optional]", min_value=0.0, value=250.0, step=10.0)
        cable_ampacity = cable_ampacity if cable_ampacity > 0 else None

else:
    with c1:
        st.markdown("#### ⚡ Operating Current Input")
        operating_current = st.number_input("Continuous Design Current Ib (A)", min_value=10.0, max_value=4000.0, value=180.0, step=10.0)
    with c2:
        st.markdown("#### 🛡️ Protection & Coordination")
        safety_factor = st.number_input("Continuous Duty Multiplier", min_value=1.00, max_value=1.50, value=1.25, step=0.05)
        cable_ampacity = st.number_input("Total Conductor Group Ampacity Iz (A) [Optional]", min_value=0.0, value=250.0, step=10.0)
        cable_ampacity = cable_ampacity if cable_ampacity > 0 else None

if st.button("🛡️ Size & Select MCCB", type="primary", use_container_width=True):
    try:
        res = select_protective_device(
            design_current_a=operating_current,
            cable_ampacity_a=cable_ampacity,
            safety_factor=safety_factor,
            allow_mccb=True
        )

        if res["status"] == "FAIL":
            st.error(f"❌ Selection Error: {res.get('message', 'No suitable standard breaker found.')}")
        else:
            st.markdown("---")
            st.subheader(f"✅ Recommended Protection: {res['rated_current_a']} A {res['device_type']}")

            m1, m2, m3 = st.columns(3)
            m1.metric("Load Current (Ib)", f"{operating_current:.2f} A")
            m2.metric("Breaker Rating (In)", f"{res['rated_current_a']} A", f"Min Req: {res['required_in_a']:.1f} A")
            if cable_ampacity:
                m3.metric("Cable Ampacity (Iz)", f"{cable_ampacity:.1f} A", "Ib <= In <= Iz Satisfied")
            else:
                m3.metric("Device Frame", "MCCB Frame", "IEC 60947-2 Standard")

            render_calculation_proof(
                "MCCB Sizing & Protection Coordination",
                [
                    {"formula": r"I_b = \frac{P_{ac} \times 1000}{\sqrt{3} \times V_{ac} \times \cos\phi} \quad [\text{A}]"},
                    {"label": "Continuous Load Current (I_b)", "value": f"{operating_current:.2f} A"},
                    {"formula": r"I_{req} = I_b \times 1.25 \quad (\text{Continuous Duty Factor})"},
                    {"label": "Minimum Required Trip Threshold", "value": f"{res['required_in_a']:.2f} A"},
                    {"label": "Selected Standard MCCB Frame/Trip", "value": f"{res['rated_current_a']} A"},
                    {"formula": r"I_b \le I_n \le I_z \quad (\text{BS 7671 Rule})"}
                ]
            )

    except Exception as e:
        st.error(f"Error selecting MCCB: {str(e)}")
