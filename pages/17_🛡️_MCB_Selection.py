import streamlit as st
import math
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from core.protection_sizing import select_protective_device

try:
    st.set_page_config(page_title="MCB Selection Calculator — Eng. Aashir", page_icon="🛡️", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("Miniature Circuit Breaker (MCB) Selection", "Size standard MCBs (<= 63A/125A) for residential & commercial branch circuits", icon="🛡️")

st.info("💡 **Engineering Note:** MCBs are DIN-rail mounted protection devices typically rated from 6A to 63A (extended up to 125A) with breaking capacities of 6kA - 10kA. For currents exceeding 63A/125A, use the **MCCB Selection Calculator**.")

input_mode = st.radio("Current Derivation Method", ["Calculate from Load Power (kW)", "Direct Current Input (A)"], horizontal=True)

c1, c2 = st.columns(2)

if input_mode == "Calculate from Load Power (kW)":
    with c1:
        st.markdown("#### ⚡ System Power Parameters")
        power_kw = st.number_input("Circuit AC Power (kW)", min_value=0.5, max_value=80.0, value=10.0, step=1.0)
        phase_opt = st.selectbox("Phase System", ["3-Phase (400V)", "1-Phase (230V)"])
        phases = 3 if "3-Phase" in phase_opt else 1
        volt = st.number_input("Nominal Voltage (V)", min_value=100.0, max_value=500.0, value=400.0 if phases == 3 else 230.0)
        pf = st.number_input("Power Factor (cos phi)", min_value=0.70, max_value=1.00, value=0.95, step=0.01)
        
        # Current calculation
        if phases == 3:
            operating_current = (power_kw * 1000.0) / (math.sqrt(3.0) * volt * pf)
        else:
            operating_current = (power_kw * 1000.0) / (volt * pf)
        st.info(f"Calculated Continuous Current ($I_b$): **{operating_current:.2f} A**")
    with c2:
        st.markdown("#### 🛡️ Coordination & Protection")
        safety_factor = st.number_input("Continuous Duty Safety Factor", min_value=1.00, max_value=1.50, value=1.25, step=0.05,
                                        help="Standard factor is 1.25 for solar PV continuous duty circuits (IEC 60364-7-712).")
        cable_ampacity = st.number_input("Selected Conductor Ampacity Iz (A) [Optional]", min_value=0.0, value=25.0, step=1.0)
        cable_ampacity = cable_ampacity if cable_ampacity > 0 else None

else:
    with c1:
        st.markdown("#### ⚡ Operating Current Input")
        operating_current = st.number_input("Continuous Design Current Ib (A)", min_value=1.0, max_value=150.0, value=20.0, step=1.0)
    with c2:
        st.markdown("#### 🛡️ Coordination & Protection")
        safety_factor = st.number_input("Continuous Duty Safety Factor", min_value=1.00, max_value=1.50, value=1.25, step=0.05)
        cable_ampacity = st.number_input("Selected Conductor Ampacity Iz (A) [Optional]", min_value=0.0, value=32.0, step=1.0)
        cable_ampacity = cable_ampacity if cable_ampacity > 0 else None

if st.button("🛡️ Select Coordinated MCB", type="primary", use_container_width=True):
    try:
        res = select_protective_device(
            design_current_a=operating_current,
            cable_ampacity_a=cable_ampacity,
            safety_factor=safety_factor,
            allow_mccb=False
        )

        if res["status"] == "FAIL":
            if operating_current * safety_factor > 63:
                st.warning(f"⚠️ Current requirement ({operating_current * safety_factor:.1f} A) exceeds standard MCB range (63A). An **MCCB** is recommended for this circuit.")
            else:
                st.error(f"❌ Selection Error: {res.get('message', 'Protection coordination failed.')}")
        else:
            st.markdown("---")
            st.subheader(f"✅ Recommended Protection: {res['rated_current_a']} A {res['device_type']}")

            m1, m2, m3 = st.columns(3)
            m1.metric("Load Current (Ib)", f"{operating_current:.2f} A")
            m2.metric("Breaker Rating (In)", f"{res['rated_current_a']} A", f"Min Req: {res['required_in_a']:.1f} A")
            if cable_ampacity:
                m3.metric("Cable Ampacity (Iz)", f"{cable_ampacity:.1f} A", f"Coordination: Ib <= In <= Iz")
            else:
                m3.metric("Type", res["device_type"], "DIN-Rail MCB")

            render_calculation_proof(
                "MCB Sizing Coordination Derivation",
                [
                    {"formula": r"I_n \ge I_b \times 1.25 \quad (\text{Continuous PV Factor})"},
                    {"label": "Design Operating Current (I_b)", "value": f"{operating_current:.2f} A"},
                    {"label": "Minimum Required Rating", "value": f"{res['required_in_a']:.2f} A"},
                    {"label": "Selected Standard Rating (I_n)", "value": f"{res['rated_current_a']} A"},
                    {"formula": r"I_b \le I_n \le I_z \quad (\text{BS 7671 Coordination Requirement})"}
                ]
            )

    except Exception as e:
        st.error(f"Error selecting MCB: {str(e)}")
