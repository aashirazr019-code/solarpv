import streamlit as st
import pandas as pd
import math
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from core.busbar_sizing import size_busbar_engineering

try:
    st.set_page_config(page_title="Busbar Sizing Calculator — Eng. Aashir", page_icon="📊", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("Busbar Sizing & Dimensioning Calculator", "Calculate continuous current, cross-sectional area, dimensions, and parallel laminations per phase", icon="📊")

input_mode = st.radio("Current Calculation Mode", ["Calculate from Total Plant AC Power", "Direct Current Input (A)"], horizontal=True)

c1, c2 = st.columns(2)

if input_mode == "Calculate from Total Plant AC Power":
    with c1:
        st.markdown("#### ⚡ Plant Power & Electrical System")
        plant_kw = st.number_input("Total Aggregated Inverter AC Power (kW)", min_value=5.0, max_value=50000.0, value=300.0, step=25.0)
        phases = 3
        volt = st.number_input("Nominal Line Voltage (V)", min_value=200.0, max_value=1000.0, value=400.0, step=15.0)
        pf = st.number_input("System Power Factor (cos phi)", min_value=0.70, max_value=1.00, value=0.95, step=0.01)
        
        operating_current = (plant_kw * 1000.0) / (math.sqrt(3.0) * volt * pf)
        st.info(f"Calculated Aggregated Operating Current: **{operating_current:.2f} A**")
    with c2:
        st.markdown("#### 🏗️ Busbar Material & Installation Environment")
        material = st.selectbox("Busbar Conductor Material", ["Copper (Cu - Electrolytic E-Cu)", "Aluminium (Al - E-Al)"])
        enclosure = st.selectbox("Enclosure Type", ["Enclosed Switchboard (Derate 0.80)", "Ventilated Compartment (Derate 0.90)", "Open Air / Perforated (Derate 1.00)"])
        enc_code = "enclosed" if "Enclosed" in enclosure else ("ventilated" if "Ventilated" in enclosure else "open_air")
        amb_temp = st.number_input("Ambient Temperature inside Switchboard (°C)", min_value=20.0, max_value=65.0, value=40.0, step=1.0)
        safety_factor = st.number_input("Continuous Duty Safety Factor", min_value=1.00, max_value=1.50, value=1.25, step=0.05)

else:
    with c1:
        st.markdown("#### ⚡ Aggregated Current Input")
        operating_current = st.number_input("Total Continuous Busbar Current (A)", min_value=10.0, max_value=10000.0, value=450.0, step=25.0)
        safety_factor = st.number_input("Continuous Duty Safety Factor", min_value=1.00, max_value=1.50, value=1.25, step=0.05)
    with c2:
        st.markdown("#### 🏗️ Conductor Material & Environmental Conditions")
        material = st.selectbox("Busbar Conductor Material", ["Copper (Cu - Electrolytic E-Cu)", "Aluminium (Al - E-Al)"])
        enclosure = st.selectbox("Enclosure Type", ["Enclosed Switchboard (Derate 0.80)", "Ventilated Compartment (Derate 0.90)", "Open Air / Perforated (Derate 1.00)"])
        enc_code = "enclosed" if "Enclosed" in enclosure else ("ventilated" if "Ventilated" in enclosure else "open_air")
        amb_temp = st.number_input("Ambient Temperature inside Switchboard (°C)", min_value=20.0, max_value=65.0, value=40.0, step=1.0)

mat_str = "copper" if "Copper" in material else "aluminium"
default_density = 1.5 if mat_str == "copper" else 1.0
density_user = st.slider("Target Current Density (A/mm²)", min_value=0.5, max_value=3.0, value=default_density, step=0.1,
                         help="Standard design current density: 1.2 - 1.8 A/mm² for Copper; 0.8 - 1.2 A/mm² for Aluminium.")

if st.button("📊 Size Busbar & Determine Laminations", type="primary", use_container_width=True):
    try:
        res = size_busbar_engineering(
            current_a=operating_current,
            material=mat_str,
            current_density_a_mm2=density_user,
            enclosure_type=enc_code,
            safety_factor=safety_factor,
            ambient_temp_c=amb_temp
        )

        if res["status"] == "FAIL":
            st.error(f"❌ Error during busbar sizing: {res.get('errors')}")
        else:
            rec = res["recommended"]
            st.markdown("---")
            st.subheader(f"✅ Recommended Busbar: {rec['arrangement_str']}")

            c_b1, c_b2, c_b3, c_b4 = st.columns(4)
            c_b1.metric("Recommended Profile", rec["dimension_str"], f"{rec['bars_per_phase']} bar(s) per phase")
            c_b2.metric("Effective Ampacity", f"{rec['effective_ampacity_a']:.1f} A", f"Design Current: {res['design_current_a']:.1f} A")
            c_b3.metric("Total Cross-Section", f"{rec['total_csa_mm2']} mm²", f"Req Min: {res['required_csa_mm2']:.1f} mm²")
            c_b4.metric("Actual Current Density", f"{rec['actual_current_density_a_mm2']:.2f} A/mm²", f"Utilization: {rec['utilization_pct']:.1f}%")

            st.markdown("---")
            st.subheader("📋 Viable Alternative Standard Commercial Profiles")
            st.caption("Standard rectangular bar options satisfying thermal continuous capacity per IEC 61439 & DIN 43671:")

            alt_rows = []
            for alt in res.get("alternative_options", []):
                alt_rows.append({
                    "Physical Arrangement": alt["arrangement_str"],
                    "Single Bar Size": alt["dimension_str"],
                    "Bars / Phase": alt["bars_per_phase"],
                    "Total CSA (mm²)": alt["total_csa_mm2"],
                    "Effective Ampacity (A)": alt["effective_ampacity_a"],
                    "Design Current (A)": alt["design_current_a"],
                    "Capacity Margin": f"{100.0 - alt['utilization_pct']:+.1f}%",
                    "Est Weight (4P kg/m)": f"{alt['est_weight_4p_kg_per_m']:.2f} kg/m"
                })
            st.dataframe(pd.DataFrame(alt_rows), use_container_width=True, hide_index=True)

            render_calculation_proof(
                "Busbar Sizing & Current Density Engineering Derivation",
                [
                    {"formula": r"I_{design} = I_{operating} \times \text{Safety Factor} \quad [\text{A}]"},
                    {"label": "Operating Continuous Current", "value": f"{operating_current:.2f} A"},
                    {"label": f"Design Current with SF={safety_factor}", "value": f"{res['design_current_a']:.2f} A"},
                    {"formula": r"\text{CSA}_{required} = \frac{I_{design}}{J_{target} \times k_{enc} \times k_{temp}} \quad [\text{mm}^2]"},
                    {"label": "Target Current Density (J)", "value": f"{density_user} A/mm²"},
                    {"label": "Enclosure Factor (k_enc)", "value": f"{res['enclosure_factor']}"},
                    {"label": f"Temperature Derating Factor at {amb_temp}°C (k_temp)", "value": f"{res['temp_derating_factor']}"},
                    {"label": "Combined Derating Factor", "value": f"{res['combined_derating_factor']}"},
                    {"label": "Required Minimum Cross-Sectional Area", "value": f"{res['required_csa_mm2']:.1f} mm²"},
                    {"label": f"Selected Arrangement ({res['material']})", "value": f"{rec['arrangement_str']} -> Total CSA = {rec['total_csa_mm2']} mm² (Ampacity: {rec['effective_ampacity_a']} A)"}
                ]
            )

    except Exception as e:
        st.error(f"Error during busbar sizing: {str(e)}")
