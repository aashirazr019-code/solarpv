"""
pages/30_📊_Meter_Selection.py — Bi-directional Net Metering & Grid Connection
Calculates export current, selects Direct vs CT-operated smart energy meter per Master Data rules:
  - 1–5 kW: Single Phase (COMPANY_STANDARD)
  - 6–20 kW: 3-Phase 30A (COMPANY_STANDARD)
  - 21–40 kW: 3-Phase 60A (COMPANY_STANDARD)
  - >40 kW: CEB / Utility Assessment Required (MANUAL_REVIEW_REQUIRED)
Authored by Eng. Aashir © 2026.
"""
import streamlit as st
import pandas as pd
from ui.styles import apply_custom_css
from ui.components import page_header, render_status, render_result_card, render_calculation_proof, nav_sidebar
from core.project_state import get_active_project, get_design_value, set_design_value, render_active_project_banner
from core.meter_selection import select_meter_system

try:
    st.set_page_config(page_title="Meter Selection — Solar PV Platform", page_icon="📊", layout="wide")
except Exception:
    pass

apply_custom_css()
nav_sidebar()
render_active_project_banner()
page_header("Meter & Grid Interconnection Selection", "Bi-directional Net Metering, CT sizing, and grid interface specifications with rule sourcing", icon="📊")

proj = get_active_project()
default_ac_kw = float(get_design_value("actual_ac_kw", proj.get("target_ac_capacity_kw", 100.0)))
default_voltage = float(proj.get("grid_voltage_v", 400.0))
default_phases = int(proj.get("grid_phases", 3))

st.markdown("### 🔌 Grid Connection & Inverter Output Parameters")
c1, c2, c3, c4 = st.columns(4)
ac_power_kw = c1.number_input("Inverter AC Export Capacity (kW)", min_value=1.0, max_value=50000.0, value=default_ac_kw, step=5.0)
grid_v = c2.selectbox("Nominal Grid Line Voltage (V)", [400.0, 230.0, 415.0, 480.0, 500.0], index=0 if default_voltage == 400.0 else 1)
phases = c3.selectbox("Number of Phases", [3, 1], index=0 if default_phases == 3 else 1)
pf = c4.number_input("Design Power Factor (cos φ)", min_value=0.80, max_value=1.00, value=0.95, step=0.01)

c5, c6 = st.columns(2)
scheme = c5.selectbox("Interconnection Billing Scheme", ["Net Metering (Export-Import)", "Net Accounting", "Net Plus (Gross Metering)", "Zero Export (Self-Consumption)"])
safety_factor = c6.slider("Continuous Current Safety Factor", min_value=1.00, max_value=1.50, value=1.25, step=0.05)

if st.button("📊 Calculate & Select Metering System", type="primary", use_container_width=True):
    try:
        res = select_meter_system(
            ac_power_kw=ac_power_kw,
            grid_voltage_v=grid_v,
            phases=phases,
            power_factor=pf,
            safety_factor=safety_factor,
            scheme_type=scheme
        )

        set_design_value("meter_selection_result", res)

        st.markdown("---")
        
        # Explicit status notification
        if res["status"] == "MANUAL_REVIEW":
            st.info(f"🔵 **MANUAL REVIEW REQUIRED:** {res['message']}")
            st.markdown(f"> **Rule Sourcing:** `{res['rule_source']}` — Because system capacity exceeds 40 kW, local utility regulations (e.g. CEB / LECO) mandate specialized engineering review and transformer/substation feeder assessment. Automated assumption of meter parameters is prohibited.")
        else:
            st.success(f"✅ **{res['message']}** (Rule Sourcing: `{res['rule_source']}`)")

        # Result Card
        render_result_card(
            title=f"Metering Type: {res['meter_type']}",
            metrics=[
                {"label": "Rated AC Current", "value": f"{res['rated_current_a']} A"},
                {"label": "Design Export Current", "value": f"{res['design_current_a']} A"},
                {"label": "Rating / Bracket", "value": res.get("rating", "Standard")},
                {"label": "Rule Sourcing", "value": res["rule_source"]}
            ],
            status=res["status"],
            explanation=f"Scheme: **{scheme}** | Connection: **{res['connection_type']}** | Protocol: **{res['communication_protocol']}**",
            calculation_steps=[
                {"label": "Rated Current Formula", "formula": r"I_{rated} = \frac{P_{ac} \times 1000}{\sqrt{3} \cdot V_{grid} \cdot \cos\varphi}" if phases == 3 else r"I_{rated} = \frac{P_{ac} \times 1000}{V_{grid} \cdot \cos\varphi}"},
                {"label": "Rated Operating Current", "value": f"{res['rated_current_a']} A"},
                {"label": "Design Current Formula", "formula": r"I_{design} = I_{rated} \times 1.25"},
                {"label": "Design Export Current", "value": f"{res['design_current_a']} A"},
                {"label": "Master Data Rule Allocation", "value": f"Policy Source: {res['rule_source']} (Threshold: 1-5kW 1P, 6-20kW 3P 30A, 21-40kW 3P 60A, >40kW Manual Review)"}
            ]
        )

        # Technical Specification Table
        st.markdown("#### 📋 Metering Equipment Technical Schedule")
        spec_df = pd.DataFrame([
            {"Parameter": "Meter Specification", "Engineering Schedule": res["meter_type"]},
            {"Parameter": "Nominal Rating", "Engineering Schedule": res.get("rating", res["rated_meter_current"])},
            {"Parameter": "Connection Topology", "Engineering Schedule": res["connection_type"]},
            {"Parameter": "Rule Sourcing Tag", "Engineering Schedule": res["rule_source"]},
            {"Parameter": "Current Transformer (CT)", "Engineering Schedule": res["ct_ratio"]},
            {"Parameter": "CT Accuracy & Burden", "Engineering Schedule": res["ct_accuracy_class"]},
            {"Parameter": "Meter Accuracy Class", "Engineering Schedule": res["meter_accuracy_class"]},
            {"Parameter": "Telemetry / AMR Protocol", "Engineering Schedule": res["communication_protocol"]},
            {"Parameter": "Interconnection Scheme", "Engineering Schedule": scheme},
            {"Parameter": "Compliance Standards", "Engineering Schedule": res["applicable_standards"]}
        ])
        st.dataframe(spec_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error calculating meter selection: {e}")
