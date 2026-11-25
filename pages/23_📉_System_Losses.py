import streamlit as st
import pandas as pd
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from core.system_losses import calculate_system_losses

try:
    st.set_page_config(page_title="System Loss Calculator — Eng. Aashir", page_icon="📉", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("PV System Losses & Performance Ratio Calculator", "Calculate individual subsystem deratings, compound PR, and annual energy waterfall without double counting", icon="📉")

c1, c2 = st.columns(2)

with c1:
    st.markdown("#### 🔋 Plant Capacity & Solar Resource")
    dc_capacity = st.number_input("Total Installed DC Array Capacity (kWp)", min_value=1.0, max_value=50000.0, value=100.0, step=5.0)
    psh = st.number_input("Peak Sun Hours — PSH (h/day)", min_value=1.0, max_value=10.0, value=4.5, step=0.1)

    st.markdown("#### ☀️ DC Pre-Inversion Loss Factors (%)")
    temp_loss = st.number_input("Cell Operating Temperature Loss (%)", min_value=0.0, max_value=25.0, value=5.0, step=0.5,
                                help="Calculated from NOCT, ambient temperature, and module temp coeff of Pmax.")
    soiling = st.number_input("Soiling / Dust Deposition Loss (%)", min_value=0.0, max_value=20.0, value=2.0, step=0.5)
    mismatch = st.number_input("Module Mismatch & Manufacturing Tolerance (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)
    shading = st.number_input("Near Horizon Shading Loss (%)", min_value=0.0, max_value=30.0, value=1.0, step=0.5)
    dc_cable = st.number_input("DC String Cable I²R Resistive Loss (%)", min_value=0.0, max_value=10.0, value=1.0, step=0.2)

with c2:
    st.markdown("#### ⚡ Conversion & AC Balance-of-System Losses (%)")
    inv_eff = st.number_input("Inverter Weighted Conversion Efficiency (%)", min_value=80.0, max_value=99.5, value=98.5, step=0.1,
                              help="Conversion efficiency at nominal load (typically 98.0% - 98.8% for modern string inverters).")
    ac_cable = st.number_input("AC Cable Voltage Drop Loss (%)", min_value=0.0, max_value=10.0, value=0.8, step=0.1)
    availability = st.number_input("System Grid & Inverter Availability (%)", min_value=80.0, max_value=100.0, value=99.0, step=0.5,
                                  help="Percentage of annual operational hours without grid curtailment or inverter maintenance outages.")
    other_losses = st.number_input("Other Unspecified Losses (LID, Soiling, Aux) (%)", min_value=0.0, max_value=10.0, value=0.5, step=0.1)

if st.button("📉 Calculate Overall System Losses & Performance Ratio", type="primary", use_container_width=True):
    try:
        # Multiplicative compound calculation (prevents double counting)
        # Factor for each loss: (1 - L_i / 100)
        f_temp = 1.0 - temp_loss / 100.0
        f_soil = 1.0 - soiling / 100.0
        f_mis = 1.0 - mismatch / 100.0
        f_shade = 1.0 - shading / 100.0
        f_dccable = 1.0 - dc_cable / 100.0
        f_inv = inv_eff / 100.0
        f_accable = 1.0 - ac_cable / 100.0
        f_avail = availability / 100.0
        f_other = 1.0 - other_losses / 100.0

        overall_pr = f_temp * f_soil * f_mis * f_shade * f_dccable * f_inv * f_accable * f_avail * f_other
        overall_loss_pct = (1.0 - overall_pr) * 100.0

        ideal_annual_kwh = dc_capacity * psh * 365.0
        net_annual_kwh = ideal_annual_kwh * overall_pr
        specific_yield = net_annual_kwh / dc_capacity

        st.markdown("---")
        st.subheader("📊 System Yield & Loss Performance Summary")

        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        c_m1.metric("Performance Ratio (PR)", f"{overall_pr * 100.0:.2f}%", f"Derate: {overall_pr:.4f}")
        c_m2.metric("Total Cumulative Losses", f"{overall_loss_pct:.2f}%", "Compound Product")
        c_m3.metric("Net Annual Generation", f"{net_annual_kwh / 1000.0:,.2f} MWh", f"{net_annual_kwh:,.0f} kWh/year")
        c_m4.metric("Specific Yield", f"{specific_yield:,.0f} kWh/kWp", "Yearly yield per installed kWp")

        st.markdown("---")
        st.subheader("📉 Subsystem Loss Waterfall Breakdown")
        st.caption("Energy remaining step-by-step from nominal irradiation to net exportable generation:")

        waterfall_stages = [
            {"Stage": "1. Ideal Nominal Energy (100% PR)", "Loss Factor": "-", "Stage Efficiency": "100.0%", "Remaining Energy (kWh)": round(ideal_annual_kwh, 0)},
            {"Stage": "2. After Horizon Shading Loss", "Loss Factor": f"-{shading:.1f}%", "Stage Efficiency": f"{f_shade*100:.1f}%", "Remaining Energy (kWh)": round(ideal_annual_kwh * f_shade, 0)},
            {"Stage": "3. After Soiling / Dust Loss", "Loss Factor": f"-{soiling:.1f}%", "Stage Efficiency": f"{f_soil*100:.1f}%", "Remaining Energy (kWh)": round(ideal_annual_kwh * f_shade * f_soil, 0)},
            {"Stage": "4. After Temperature Derating", "Loss Factor": f"-{temp_loss:.1f}%", "Stage Efficiency": f"{f_temp*100:.1f}%", "Remaining Energy (kWh)": round(ideal_annual_kwh * f_shade * f_soil * f_temp, 0)},
            {"Stage": "5. After Module Mismatch", "Loss Factor": f"-{mismatch:.1f}%", "Stage Efficiency": f"{f_mis*100:.1f}%", "Remaining Energy (kWh)": round(ideal_annual_kwh * f_shade * f_soil * f_temp * f_mis, 0)},
            {"Stage": "6. After DC String Cable Resistance", "Loss Factor": f"-{dc_cable:.1f}%", "Stage Efficiency": f"{f_dccable*100:.1f}%", "Remaining Energy (kWh)": round(ideal_annual_kwh * f_shade * f_soil * f_temp * f_mis * f_dccable, 0)},
            {"Stage": "7. After Inverter Conversion (DC to AC)", "Loss Factor": f"-{100.0 - inv_eff:.1f}%", "Stage Efficiency": f"{f_inv*100:.1f}%", "Remaining Energy (kWh)": round(ideal_annual_kwh * f_shade * f_soil * f_temp * f_mis * f_dccable * f_inv, 0)},
            {"Stage": "8. After AC Cable Losses", "Loss Factor": f"-{ac_cable:.1f}%", "Stage Efficiency": f"{f_accable*100:.1f}%", "Remaining Energy (kWh)": round(ideal_annual_kwh * f_shade * f_soil * f_temp * f_mis * f_dccable * f_inv * f_accable, 0)},
            {"Stage": "9. After System Availability & Other Losses", "Loss Factor": f"-{(1.0 - f_avail*f_other)*100:.1f}%", "Stage Efficiency": f"{f_avail*f_other*100:.1f}%", "Remaining Energy (kWh)": round(net_annual_kwh, 0)},
        ]

        df_waterfall = pd.DataFrame(waterfall_stages)
        st.dataframe(df_waterfall, use_container_width=True, hide_index=True)

        render_calculation_proof(
            "Compound Performance Ratio (No Double Counting)",
            [
                {"formula": r"\text{PR} = \prod_{i=1}^{n} (1 - L_i) = (1 - L_{temp}) \times (1 - L_{soil}) \times (1 - L_{mis}) \times (1 - L_{shade}) \times (1 - L_{dc}) \times \eta_{inv} \times (1 - L_{ac}) \times \text{Avail}"},
                {"label": "Calculated Compound PR", "value": f"{overall_pr * 100.0:.2f}% ({overall_pr:.4f})"},
                {"formula": r"E_{net,annual} = P_{dc} \times \text{PSH} \times 365 \times \text{PR} \quad [\text{kWh/year}]"},
                {"label": "Net Annual Exported Energy", "value": f"{net_annual_kwh:,.1f} kWh ({net_annual_kwh / 1000.0:,.2f} MWh)"},
                {"formula": r"\text{Specific Yield} = \frac{E_{net,annual}}{P_{dc}} \quad [\text{kWh/kWp/year}]"},
                {"label": "Specific Energy Yield", "value": f"{specific_yield:,.1f} kWh/kWp/year"}
            ]
        )

    except Exception as e:
        st.error(f"Error during system losses calculation: {str(e)}")
