import streamlit as st
from ui.styles import status_badge

def render_status(status, text=None):
    """Render PASS/WARNING/FAIL/MANUAL_REVIEW with emoji AND text. Never color-only."""
    if status == 'PASS':
        st.success(f'✅ PASS — {text}' if text else '✅ PASS')
    elif status == 'WARNING':
        st.warning(f'⚠️ WARNING — {text}' if text else '⚠️ WARNING')
    elif status in ('FAIL', 'NOT_FITTING'):
        st.error(f'❌ FAIL — {text}' if text else '❌ FAIL')
    elif status in ('MANUAL_REVIEW', 'MANUAL REVIEW'):
        st.info(f'🔵 MANUAL REVIEW — {text}' if text else '🔵 MANUAL REVIEW')
    else:
        st.info(f'⏳ {status} — {text}' if text else f'⏳ {status}')

def render_calculation_proof(title, steps):
    """
    Renders an expandable engineering calculation proof panel.
    steps: list of dicts with 'label'+'value', or 'formula', or 'note'.
           Also accepts a flat dict {key: value} for convenience.
    """
    # Accept a plain dict and convert it to list format
    if isinstance(steps, dict):
        steps = [{"label": k.replace("_", " ").title(), "value": v}
                 for k, v in steps.items() if v is not None]
    with st.expander(f'📝 {title} — Engineering Calculation Proof', expanded=False):
        if not steps:
            st.caption("No calculation details available.")
            return
        for step in steps:
            if 'formula' in step:
                try:
                    st.latex(step['formula'])
                except Exception:
                    st.code(step['formula'])
            if 'label' in step and 'value' in step:
                st.markdown(f"**{step['label']}**: `{step['value']}`")
            if 'note' in step:
                st.caption(step['note'])

def render_result_card(title, metrics, status, explanation='', calculation_steps=None):
    """
    Professional result card with value, unit, status, and optional calculation proof.
    metrics: list of dicts with keys: label, value, unit (optional), delta (optional)
    """
    with st.container(border=True):
        col_title, col_status = st.columns([3, 1])
        with col_title:
            st.markdown(f'### {title}')
        with col_status:
            render_status(status)
        
        cols = st.columns(len(metrics))
        for i, m in enumerate(metrics):
            label = m.get('label', '')
            value = m.get('value', '')
            unit = m.get('unit', '')
            display = f"{value} {unit}".strip()
            delta = m.get('delta', None)
            cols[i].metric(label, display, delta)
        
        if explanation:
            st.caption(explanation)
        
        if calculation_steps:
            render_calculation_proof(title, calculation_steps)

def render_validation_table(validation_items):
    """
    Renders the design validation health check matrix.
    validation_items: list of dicts with parameter, actual_value, allowed_value, deviation, status, reason, recommended_action
    """
    import pandas as pd
    if not validation_items:
        st.info('No validation items to display.')
        return
    
    rows = []
    for item in validation_items:
        icon = {"PASS": "🟢", "WARNING": "🟡", "FAIL": "🔴", "MANUAL_REVIEW": "🔵", "MANUAL REVIEW": "🔵"}.get(item['status'], '❓')
        rows.append({
            'Status': f"{icon} {item['status']}",
            'Parameter': item['parameter'],
            'Actual': item.get('actual_value', ''),
            'Allowed': item.get('allowed_value', ''),
            'Deviation': item.get('deviation', ''),
            'Reason': item.get('reason', ''),
            'Action': item.get('recommended_action', ''),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

def page_header(title, subtitle='', icon=''):
    """Standard page header for all calculator pages."""
    col_t, col_auth = st.columns([3, 1])
    with col_t:
        st.markdown(f'# {icon} {title}')
        if subtitle:
            st.caption(subtitle)
    with col_auth:
        st.markdown(
            '<div style="text-align: right; font-size: 11px; color: #64748b; padding-top: 10px;">'
            '<b>Designed by:</b> Eng. Aashir<br/>'
            '© 2026 All Rights Reserved'
            '</div>',
            unsafe_allow_html=True
        )
    st.divider()

def nav_sidebar():
    """Show project context in sidebar with engineering watermark."""
    with st.sidebar:
        st.markdown('## ☀️ Solar PV Platform')
        st.caption('Lead Engineer: **Eng. Aashir**')
        st.divider()
        # Active project display
        if 'active_project' in st.session_state and st.session_state.active_project:
            proj = st.session_state.active_project
            st.markdown(f"**Active Project:** {proj.get('name', 'Untitled')}")
            st.caption(f"Status: {proj.get('status', 'draft')} | Rev: {proj.get('revision', 0)}")
            st.divider()
        else:
            st.info('No active project. Go to Projects to create or open one.')
            st.divider()
            
        st.markdown(
            '<div style="font-size: 11px; color: #94a3b8; text-align: center; margin-top: 40px;">'
            'Solar PV Engineering Design Platform<br/>'
            '<b>© 2026 Eng. Aashir</b><br/>'
            'All Rights Reserved'
            '</div>',
            unsafe_allow_html=True
        )
