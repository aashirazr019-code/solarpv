PAGE_CONFIG = dict(page_title='Solar PV Design Platform — Eng. Aashir', page_icon='☀️', layout='wide')

def apply_custom_css():
    import streamlit as st
    st.markdown('''
    <style>
    .main-header { font-size: 28px; font-weight: bold; color: #1e3a5f; }
    .sub-header { font-size: 18px; color: #4a6fa5; }
    .status-pass { background-color: #d4edda; color: #155724; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
    .status-warning { background-color: #fff3cd; color: #856404; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
    .status-fail { background-color: #f8d7da; color: #721c24; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
    .calc-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin: 8px 0; }
    .metric-label { font-size: 12px; color: #666; text-transform: uppercase; }
    .metric-value { font-size: 24px; font-weight: bold; color: #1e3a5f; }
    div[data-testid="stMetric"] { background-color: #f8f9fa; border-radius: 8px; padding: 12px; border: 1px solid #e9ecef; }
    
    /* Engineer Watermark & Copyright Styling */
    .watermark-banner {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(90deg, #0f172a 0%, #1e3a8a 100%);
        color: #f8fafc;
        padding: 6px 14px;
        border-radius: 6px;
        font-size: 12px;
        margin-bottom: 12px;
        letter-spacing: 0.5px;
    }
    .watermark-banner span { font-weight: 600; color: #38bdf8; }
    
    .floating-watermark {
        position: fixed;
        bottom: 10px;
        right: 18px;
        opacity: 0.70;
        font-size: 11px;
        color: #475569;
        z-index: 99999;
        pointer-events: none;
        background: rgba(255, 255, 255, 0.85);
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid #e2e8f0;
        font-family: sans-serif;
    }
    </style>
    <div class="floating-watermark">© 2026 <b>Eng. Aashir</b> | Solar PV Platform</div>
    ''', unsafe_allow_html=True)

def status_badge(status, label=None):
    """Returns emoji + text status badge string."""
    if label is None:
        label = status
    icons = {'PASS': '🟢', 'WARNING': '🟡', 'FAIL': '🔴', 'NOT_FITTING': '🔴', 'PENDING': '⏳'}
    return f"{icons.get(status, '❓')} **{label}**"
