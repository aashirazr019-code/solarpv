import streamlit as st
import pandas as pd
from ui.components import page_header, render_result_card, render_status, nav_sidebar
from ui.styles import apply_custom_css
from ui.equipment_forms import panel_picker
from data.library_data import INVERTER_FAMILIES, build_inverter
from core.models import Project, SpacingConfig, InverterOption, Inverter
from core.pipeline import evaluate_project, evaluate_project_with_tolerance, breakdown_summary

try:
    st.set_page_config(page_title="Inverter Combination Engine — Eng. Aashir", page_icon="🏗️", layout="wide")
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("Inverter Combination Calculator", "Calculate, rank, and recommend optimal multi-inverter plant architectures", icon="🏗️")

c_top1, c_top2 = st.columns([1, 1])
with c_top1:
    st.markdown("#### 🔋 Project PV Module")
    panel = panel_picker("inv_comb_page_panel")

with c_top2:
    st.markdown("#### 🎯 System AC Capacity Target")
    target_ac_kw = st.number_input("Target Plant AC Capacity (kW)", min_value=3.0, max_value=50000.0, value=300.0, step=25.0,
                                   help="Target total AC power to be injected into the utility grid.")
    c_s1, c_s2 = st.columns(2)
    search_mode = c_s1.selectbox("Search Mode", ["Exact Match", "Tolerance (±5%)", "Closest Match", "Oversized Allowed"], index=0)
    target_dc_ac = c_s2.number_input("Preferred DC/AC Ratio", min_value=1.00, max_value=1.50, value=1.20, step=0.02)

st.markdown("---")
st.markdown("#### ⚡ Inverter Pool Configuration")
st.caption("Select the candidate inverter models available for combination search (e.g. 100kW, 80kW, 50kW, 25kW).")

# Build a rich pool of representative inverters from Sunways library
available_inverter_models = []
for fam in INVERTER_FAMILIES:
    for var in fam["variants"]:
        inv_obj = build_inverter(fam, var)
        available_inverter_models.append(inv_obj)

# Sort descending by rated AC power
available_inverter_models.sort(key=lambda x: x.rated_ac_power_kw, reverse=True)

# Selection interface
col_p1, col_p2 = st.columns([2, 1])
with col_p1:
    pool_options_labels = [f"{inv.rated_ac_power_kw:g} kW — {inv.manufacturer} {inv.model}" for inv in available_inverter_models]
    # Default to 100kW, 50kW, 25kW if around 300kW, or appropriate defaults
    default_indices = [i for i, inv in enumerate(available_inverter_models) if inv.rated_ac_power_kw in (100.0, 80.0, 50.0, 25.0)]
    if not default_indices:
        default_indices = [0, 1, 2] if len(available_inverter_models) >= 3 else [0]
    
    selected_labels = st.multiselect(
        "Select Inverter Sizes to Include in Search",
        options=pool_options_labels,
        default=[pool_options_labels[i] for i in default_indices]
    )

with col_p2:
    max_units_per_size = st.number_input("Max Units per Model", min_value=1, max_value=20, value=6, step=1,
                                         help="Maximum number of inverters of any single model to consider.")

# Build InverterOption list
inverter_options = []
for lbl in selected_labels:
    idx = pool_options_labels.index(lbl)
    inv_obj = available_inverter_models[idx]
    inverter_options.append(InverterOption(inverter=inv_obj, available_qty=max_units_per_size))

if st.button("🏗️ Search & Evaluate Inverter Combinations", type="primary", use_container_width=True):
    if not inverter_options:
        st.error("Please select at least one inverter model in the pool.")
    else:
        try:
            project = Project(
                id="inv-comb-project", name="Inverter Combination", location="", installation_type="rooftop",
                target_ac_capacity_kw=target_ac_kw, min_design_temp_c=-30.0, max_design_temp_c=60.0,
                dc_ac_ratio_min=1.05, dc_ac_ratio_preferred=target_dc_ac, dc_ac_ratio_max=1.35,
                panel_id=panel.id, panel_available_qty=9999,
                area_length_m=200.0, area_width_m=200.0, spacing_config=SpacingConfig()
            )

            # Perform combination evaluation based on search mode
            if search_mode == "Exact Match":
                results = evaluate_project(panel, project, inverter_options, max_combinations=200, top_n=6)
            else:
                mode_code = "closest" if search_mode == "Closest Match" else ("oversized" if search_mode == "Oversized Allowed" else "closest")
                results = evaluate_project_with_tolerance(
                    panel, project, inverter_options, tolerance_pct=5.0, mode=mode_code, max_combinations=200, top_n=6
                )

            valid_configs = results.get("valid", [])
            rejected_configs = results.get("rejected", [])
            total_found = results.get("total_combos_found", 0)

            st.markdown("---")
            st.subheader(f"📊 Evaluation Results (Found {total_found} Combinations)")

            if not valid_configs:
                st.warning(f"No valid inverter combinations could be formed matching {target_ac_kw} kW AC. Try expanding the inverter pool or selecting 'Tolerance (±5%)' or 'Closest Match'.")
            else:
                for idx, cfg in enumerate(valid_configs):
                    rank_badge = "🥇 Rank #1 (Recommended)" if idx == 0 else (f"🥈 Rank #{idx + 1}" if idx == 1 else f"Option #{idx + 1}")
                    
                    with st.container(border=True):
                        c_title, c_score = st.columns([3, 1])
                        with c_title:
                            st.markdown(f"### {rank_badge}: {cfg['breakdown_summary']}")
                        with c_score:
                            st.metric("Composite Score", f"{cfg['score']:.3f}", help="Higher score indicates optimal unit count, minimal clipping, and better MPPT utilization.")

                        # Summary Metrics
                        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                        c_m1.metric("Plant AC Output", f"{cfg['ac_capacity_kw']:.1f} kW")
                        c_m2.metric("Connected DC Array", f"{cfg['dc_capacity_kwp']:.2f} kWp")
                        c_m3.metric("DC/AC Ratio", f"{cfg['actual_dc_ac_ratio']:.2f}")
                        c_m4.metric("Inverter Units", f"{cfg['unit_count']} units")

                        # Breakdown by Inverter Model
                        st.markdown("##### 🔌 Connected Capacity per Inverter Unit")
                        inv_detail_rows = []
                        for b in cfg["inverter_breakdown"]:
                            inv_unit = b["inverter"]
                            qty = b["quantity"]
                            unit_ac = inv_unit.rated_ac_power_kw
                            unit_dc = (cfg["dc_capacity_kwp"] / cfg["ac_capacity_kw"]) * unit_ac if cfg["ac_capacity_kw"] > 0 else 0.0
                            inv_detail_rows.append({
                                "Model": f"{inv_unit.manufacturer} {inv_unit.model}",
                                "Quantity": f"{qty} units",
                                "Unit AC Rating": f"{unit_ac:.1f} kW",
                                "Subtotal AC": f"{unit_ac * qty:.1f} kW",
                                "DC Connected / Unit": f"{unit_dc:.2f} kWp",
                                "MPPT Trackers / Unit": f"{inv_unit.mppt_count} MPPTs",
                                "Max DC Voltage": f"{inv_unit.max_dc_voltage_v} V"
                            })
                        st.dataframe(pd.DataFrame(inv_detail_rows), use_container_width=True, hide_index=True)

            # Rejected Combinations Expander
            if rejected_configs:
                with st.expander(f"⚠️ View {len(rejected_configs)} Non-Viable / Rejected Combinations", expanded=False):
                    st.caption("These combinations matched the target power but failed voltage window or current safety checks:")
                    rej_table = []
                    for r in rejected_configs[:15]:
                        rej_table.append({
                            "Combination": r.get("breakdown", "Unknown"),
                            "Rejection Reason": r.get("reason", "Failed electrical check")
                        })
                    st.dataframe(pd.DataFrame(rej_table), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error during inverter combination search: {str(e)}")
