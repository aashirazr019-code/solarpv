"""
pages/32_💾_Saved_Designs.py — Saved Designs & Revisions Manager
Inspects, compares, and restores saved engineering design revisions and SQLite project snapshots.
Authored by Eng. Aashir © 2026.
"""
import streamlit as st
import json
import pandas as pd
from ui.styles import apply_custom_css
from ui.components import page_header, render_status
from data.database import list_projects, save_project_revision, get_project_revisions
from core.project_state import get_active_project, set_active_project, get_design_value, render_active_project_banner

try:
    st.set_page_config(page_title="Saved Designs — Solar PV Platform", page_icon="💾", layout="wide")
except Exception:
    pass

apply_custom_css()
render_active_project_banner()
page_header("Saved Designs & Revision History", "Manage version-controlled engineering snapshots and SQLite project revisions", icon="💾")

proj = get_active_project()
p_id = proj.get("id", "default")
p_name = proj.get("name", "Active Project")

st.markdown(f"### 📂 Revisions for: **{p_name}**")

c_rev1, c_rev2 = st.columns([2, 1])

with c_rev1:
    st.markdown("#### 🔖 Create Design Revision Snapshot")
    with st.form("create_revision_form"):
        r_notes = st.text_area("Revision Notes / Change Description", placeholder="e.g. Optimized string arrangement for cold morning Voc compliance and upsized AC cable to 95mm².")
        r_engineer = st.text_input("Lead Approving Engineer", value="Eng. Aashir")
        r_submit = st.form_submit_button("💾 Save Snapshot Revision", type="primary", use_container_width=True)

        if r_submit:
            if not r_notes:
                st.warning("Please provide revision change notes.")
            else:
                snapshot_data = {
                    "project": proj,
                    "design_state": st.session_state.get("design_state", {}),
                    "active_panel": st.session_state.active_panel.__dict__ if hasattr(st.session_state.active_panel, "__dict__") else st.session_state.active_panel,
                    "active_inverter": st.session_state.active_inverter.__dict__ if hasattr(st.session_state.active_inverter, "__dict__") else st.session_state.active_inverter,
                }
                try:
                    save_project_revision(p_id, snapshot_data, notes=r_notes, created_by=r_engineer)
                    st.success("✅ Revision snapshot successfully committed to database.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving revision: {e}")

with c_rev2:
    st.markdown("#### ⚡ Active Snapshot Status")
    with st.container(border=True):
        st.markdown(f"**Project ID:** `{p_id}`")
        st.markdown(f"**Current Revision:** `Rev {proj.get('revision', 1)}`")
        st.markdown(f"**Status:** `{proj.get('status', 'draft').upper()}`")
        st.markdown(f"**Target AC:** `{proj.get('target_ac_capacity_kw', 100.0)} kW`")
        st.markdown(f"**Calculated DC:** `{get_design_value('actual_dc_kwp', 120.0)} kWp`")

st.markdown("---")
st.markdown("### 📜 Revision History Table")

try:
    revs = get_project_revisions(p_id)
    if not revs:
        st.info("No revision history logged yet for this project. Save your first snapshot above.")
    else:
        rev_rows = []
        for r in revs:
            rev_rows.append({
                "Rev #": f"Rev {r.get('revision_number', 1)}",
                "Created Date": r.get("created_at", "N/A"),
                "Engineer": r.get("created_by", "Eng. Aashir"),
                "Change Notes": r.get("notes", ""),
            })
        st.dataframe(pd.DataFrame(rev_rows), use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"Error reading revisions: {e}")
