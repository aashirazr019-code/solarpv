import uuid
from datetime import datetime
import streamlit as st
from ui.components import page_header, nav_sidebar, render_status
from ui.styles import apply_custom_css
from data.database import (
    list_projects,
    save_project,
    get_project,
    delete_project,
    duplicate_project,
    archive_project,
    save_project_revision,
    get_project_revisions
)

try:
    st.set_page_config(page_title='Projects — Solar PV Platform', page_icon='📁', layout='wide')
except Exception:
    pass
apply_custom_css()
nav_sidebar()

page_header("Project Management", "Create, open, revise, duplicate, and archive engineering projects", icon="📁")

tab_list, tab_new, tab_rev = st.tabs(["📁 Project Portfolio", "➕ New Project", "📝 Revisions & History"])

# -------------------------------------------------------------
# TAB 1: PROJECT LIST & MANAGEMENT
# -------------------------------------------------------------
with tab_list:
    search_col, filter_col = st.columns([3, 1])
    search_query = search_col.text_input("🔍 Search projects by name, customer, or site", "")
    status_filter = filter_col.selectbox("Status Filter", ["All", "draft", "in_review", "approved", "archived"])
    
    try:
        raw_projects = list_projects(status_filter=None if status_filter == "All" else status_filter)
        if search_query.strip():
            q = search_query.lower()
            projects = [
                p for p in raw_projects
                if q in p.get("name", "").lower()
                or q in p.get("customer_name", "").lower()
                or q in p.get("site_name", "").lower()
                or q in p.get("location", "").lower()
            ]
        else:
            projects = raw_projects
            
        if not projects:
            st.info("No matching projects found.")
        else:
            for p in projects:
                p_id = p.get("id", "")
                p_name = p.get("name", "Untitled")
                p_cust = p.get("customer_name", "N/A")
                p_site = p.get("site_name", "N/A")
                p_loc = p.get("location", "N/A")
                p_stat = p.get("status", "draft")
                p_type = p.get("installation_type", "rooftop")
                p_kw = p.get("target_ac_capacity_kw", p.get("target_ac_kw", 0.0))
                p_rev = p.get("revision", 0)
                
                is_active = (st.session_state.get("active_project", {}).get("id") == p_id)
                
                with st.container(border=True):
                    h_col, stat_col = st.columns([3, 1])
                    with h_col:
                        st.markdown(f"### {p_name} {'⭐ (Active)' if is_active else ''}")
                        st.caption(f"Customer: **{p_cust}** | Site: **{p_site}** ({p_loc}) | Type: **{p_type.capitalize()}** | Rev: **{p_rev}**")
                    with stat_col:
                        badge_color = "PASS" if p_stat == "approved" else ("WARNING" if p_stat == "draft" else "INFO")
                        render_status(badge_color, p_stat.upper())
                        
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Target AC", f"{p_kw} kW")
                    m2.metric("DC/AC Ratio", f"{p.get('dc_ac_ratio_preferred', 1.20):.2f}")
                    m3.metric("Min Temp", f"{p.get('min_design_temp_c', -30.0)} °C")
                    m4.metric("Max Temp", f"{p.get('max_design_temp_c', 60.0)} °C")
                    
                    b1, b2, b3, b4 = st.columns(4)
                    if b1.button("📂 Open as Active", key=f"open_btn_{p_id}", use_container_width=True, disabled=is_active):
                        st.session_state.active_project = p
                        st.success(f"Project **{p_name}** is now active.")
                        st.rerun()
                        
                    if b2.button("📑 Duplicate", key=f"dup_btn_{p_id}", use_container_width=True):
                        new_id = duplicate_project(p_id, f"{p_name} (Copy)")
                        st.success(f"Duplicated as new project.")
                        st.rerun()
                        
                    if b3.button("📦 Archive", key=f"arch_btn_{p_id}", use_container_width=True, disabled=(p_stat == "archived")):
                        archive_project(p_id)
                        st.info(f"Archived project.")
                        st.rerun()
                        
                    if b4.button("🗑️ Delete", key=f"del_btn_{p_id}", use_container_width=True):
                        delete_project(p_id)
                        if is_active:
                            st.session_state.active_project = None
                        st.warning(f"Deleted project.")
                        st.rerun()
    except Exception as e:
        st.error(f"Error accessing project records: {e}")

# -------------------------------------------------------------
# TAB 2: CREATE NEW PROJECT
# -------------------------------------------------------------
with tab_new:
    st.subheader("Create New Solar PV Design Project")
    
    with st.form("new_project_full_form"):
        f1, f2 = st.columns(2)
        proj_name = f1.text_input("Project Name *", value="Commercial Rooftop PV")
        customer_name = f2.text_input("Customer / Client Name", value="Industrial Corp")
        
        f3, f4 = st.columns(2)
        site_name = f3.text_input("Site Name", value="Factory Unit A")
        location = f4.text_input("Location / City", value="Colombo, Sri Lanka")
        
        c_inst, c_target = st.columns(2)
        installation_type = c_inst.selectbox("Installation Type", ["rooftop", "ground_mount", "carport"])
        target_ac_kw = c_target.number_input("Target AC Power Capacity (kW) *", min_value=1.0, value=5.0, step=1.0)
        
        st.markdown("#### Environmental Design Limits")
        t1, t2 = st.columns(2)
        min_temp = t1.number_input("Min Design Ambient Temp (°C)", value=-30.0, help="Used for Cold Voc string sizing calculation. Default -30 °C.")
        max_temp = t2.number_input("Max Design Ambient Temp (°C)", value=60.0, help="Used for Hot Vmp string sizing calculation. Default 60 °C.")
        
        st.markdown("#### DC/AC Sizing Constraints")
        r1, r2, r3 = st.columns(3)
        dc_ac_min = r1.number_input("DC/AC Ratio Min", value=1.05, step=0.05)
        dc_ac_pref = r2.number_input("DC/AC Ratio Preferred", value=1.20, step=0.05)
        dc_ac_max = r3.number_input("DC/AC Ratio Max", value=1.35, step=0.05)
        
        st.markdown("#### Available Physical Space")
        a1, a2, a3 = st.columns(3)
        area_len = a1.number_input("Available Length (m)", value=80.0, step=5.0)
        area_wid = a2.number_input("Available Width (m)", value=50.0, step=5.0)
        panel_avail = a3.number_input("Max Available Panels (Qty)", value=1000, step=50)
        
        create_btn = st.form_submit_button("🚀 Save & Initialize Project", type="primary")
        
        if create_btn:
            if not proj_name.strip():
                st.error("Project Name is required.")
            elif min_temp >= max_temp:
                st.error("Min design temp must be lower than Max design temp.")
            elif not (dc_ac_min <= dc_ac_pref <= dc_ac_max):
                st.error("DC/AC ratio constraints must satisfy Min <= Preferred <= Max.")
            else:
                new_project_data = {
                    "id": str(uuid.uuid4()),
                    "name": proj_name.strip(),
                    "customer_name": customer_name.strip(),
                    "site_name": site_name.strip(),
                    "location": location.strip(),
                    "status": "draft",
                    "installation_type": installation_type,
                    "target_ac_capacity_kw": float(target_ac_kw),
                    "target_ac_kw": float(target_ac_kw),
                    "min_design_temp_c": float(min_temp),
                    "max_design_temp_c": float(max_temp),
                    "dc_ac_ratio_min": float(dc_ac_min),
                    "dc_ac_ratio_preferred": float(dc_ac_pref),
                    "dc_ac_ratio_max": float(dc_ac_max),
                    "area_length_m": float(area_len),
                    "area_width_m": float(area_wid),
                    "panel_available_qty": int(panel_avail),
                    "revision": 0,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
                save_project(new_project_data)
                st.session_state.active_project = new_project_data
                st.success(f"✅ Project **{proj_name}** created and set as active!")
                st.rerun()

# -------------------------------------------------------------
# TAB 3: REVISIONS & AUDIT LOG
# -------------------------------------------------------------
with tab_rev:
    st.subheader("Project Revision Tracking")
    active = st.session_state.get("active_project", None)
    if not active:
        st.info("No active project loaded. Open a project to inspect and create design revisions.")
    else:
        st.markdown(f"Active Project: **{active.get('name', 'Untitled')}** (ID: `{active.get('id')}`)")
        
        with st.expander("➕ Snapshot Current Design as New Revision", expanded=False):
            with st.form("save_rev_form"):
                rev_notes = st.text_area("Revision Notes / Change Description", placeholder="e.g., Updated inverter selection to 100KTL models after site survey.")
                author = st.text_input("Engineer / Created By", value="Lead PV Engineer")
                if st.form_submit_button("Commit Revision"):
                    save_project_revision(active.get("id"), active, notes=rev_notes, created_by=author)
                    st.success("Design revision snapshot recorded.")
                    st.rerun()
                    
        st.markdown("#### Revision History")
        revs = get_project_revisions(active.get("id"))
        if not revs:
            st.caption("No revisions committed yet for this project.")
        else:
            for r in revs:
                with st.container(border=True):
                    st.markdown(f"**Revision #{r.get('revision_number')}** — *{r.get('created_at')[:16].replace('T', ' ')}*")
                    st.caption(f"Author: {r.get('created_by', 'N/A')} | Notes: {r.get('notes', 'None')}")
