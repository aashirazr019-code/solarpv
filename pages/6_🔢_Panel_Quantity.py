import streamlit as st
import math
import pandas as pd
from ui.components import page_header, render_result_card, render_calculation_proof, render_status, nav_sidebar
from ui.styles import apply_custom_css
from ui.equipment_forms import panel_picker
from core.panel_quantity import calculate_panel_quantity, calculate_string_and_panel_balance

try:
    st.set_page_config(page_title="Panel Quantity Calculator — Eng. Aashir", page_icon="🔢", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("Panel Quantity Calculator", "Calculate required module counts, actual DC output, and string divisibility", icon="🔢")

c1, c2 = st.columns([1, 1])
with c1:
    st.markdown("#### 🎯 Sizing Target")
    target_dc = st.number_input("Target DC Capacity (kWp)", min_value=0.1, max_value=50000.0, value=6.5, step=0.5,
                                help="Desired total peak solar array capacity in kilowatt-peak.")
    max_panels = st.number_input("Maximum Available Panels / Space Limit (optional)", min_value=0, value=0, step=10,
                                 help="Set to 0 if unlimited. Enter available stock or maximum rooftop physical capacity.")
    panels_per_str = st.number_input("Assumed Panels per String (for divisibility check)", min_value=1, max_value=40, value=6, step=1,
                                     help="Number of modules connected in series per string (typically 6 to 22).")

with c2:
    st.markdown("#### 🔋 Module Specification")
    panel = panel_picker("panel_qty_calc")

if st.button("🔢 Calculate Module Quantity", type="primary", use_container_width=True):
    try:
        panel_wp = panel.rated_power_wp if panel else 630.0
        max_p = max_panels if max_panels > 0 else None
        
        # Core calculation with numeric wattage
        result = calculate_panel_quantity(target_dc, panel_wp, max_p)
        count = result["panel_count"]
        actual_dc = result["actual_dc_kwp"]
        surplus = result["surplus_pct"]

        # String divisibility balance
        bal = calculate_string_and_panel_balance(count, panels_per_str)

        st.markdown("---")
        st.subheader("📊 Module Quantity & Capacity Results")

        metrics = [
            {"label": "Required Panel Count", "value": f"{count:,}", "unit": "modules"},
            {"label": "Module Rating", "value": f"{panel_wp:.0f}", "unit": "Wp"},
            {"label": "Actual Installed DC", "value": f"{actual_dc:.2f}", "unit": "kWp"},
            {"label": "Capacity Surplus", "value": f"{surplus:+.2f}", "unit": "%", "delta": f"{surplus:+.2f}%"}
        ]

        render_result_card(
            "Array Sizing Summary",
            metrics,
            status=result["status"],
            explanation=f"Generated from {target_dc} kWp target with {panel_wp} Wp modules."
        )

        # Divisibility Status Card
        if bal["is_divisible"]:
            st.success(f"✅ **Perfect Divisibility**: {count} modules form exactly **{bal['strings_count']} strings** of {panels_per_str} modules.")
        else:
            st.warning(f"⚠️ **Non-Divisible Quantity**: {count} modules divided by {panels_per_str} modules/string leaves **{bal['remainder_panels']} spare module(s)**.")
            div_c1, div_c2 = st.columns(2)
            with div_c1:
                st.info(
                    f"**Option A (Round Down):**\n\n"
                    f"• **{bal['round_down']['panels']} modules** ({bal['round_down']['strings']} strings of {panels_per_str})\n"
                    f"• Output: **{(bal['round_down']['panels'] * panel_wp)/1000.0:.2f} kWp**"
                )
            with div_c2:
                st.info(
                    f"**Option B (Round Up):**\n\n"
                    f"• **{bal['round_up']['panels']} modules** ({bal['round_up']['strings']} strings of {panels_per_str})\n"
                    f"• Output: **{(bal['round_up']['panels'] * panel_wp)/1000.0:.2f} kWp**"
                )

        # String Options Sensitivity Table
        st.markdown("#### 📋 Common String Length Comparison Table")
        table_rows = []
        for s_len in range(12, 23):
            s_count = count // s_len
            rem = count % s_len
            clean_panels = (s_count + (1 if rem > s_len/2 else 0)) * s_len
            clean_kwp = (clean_panels * panel_wp) / 1000.0
            table_rows.append({
                "Panels / String": s_len,
                "Strings Count": clean_panels // s_len,
                "Balanced Module Count": clean_panels,
                "Installed DC (kWp)": f"{clean_kwp:.2f}",
                "Divisible Exactly": "✅ Yes" if rem == 0 else f"⚠️ ({rem} spare)"
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        # Step-by-step calculation proof
        render_calculation_proof(
            "Panel Quantity Engineering Formula",
            [
                {"formula": r"N_{panels} = \left\lceil \frac{P_{dc,target} \times 1000}{P_{mp}} \right\rceil"},
                {"label": "Target DC Capacity (P_dc)", "value": f"{target_dc:.2f} kWp ({target_dc * 1000:,.0f} W)"},
                {"label": "Module STC Peak Power (P_mp)", "value": f"{panel_wp:.1f} Wp"},
                {"label": "Calculated Module Count (N)", "value": f"{count} modules"},
                {"formula": r"P_{dc,actual} = \frac{N_{panels} \times P_{mp}}{1000} \quad [\text{kWp}]"},
                {"label": "Actual Installed Capacity", "value": f"{actual_dc:.3f} kWp"},
                {"formula": r"\text{Surplus \%} = \frac{P_{dc,actual} - P_{dc,target}}{P_{dc,target}} \times 100\%"},
                {"label": "Capacity Surplus", "value": f"{surplus:+.2f}%"}
            ]
        )

        # Save to active session state
        if "active_project" in st.session_state and st.session_state.active_project:
            st.session_state.active_project["panel_qty"] = count
            st.session_state.active_project["actual_dc_kwp"] = actual_dc

    except Exception as e:
        st.error(f"Error during panel quantity calculation: {str(e)}")
