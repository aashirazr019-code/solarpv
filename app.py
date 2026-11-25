"""
app.py — Solar PV Engineering Design & BoQ Platform
Master application entrypoint with clean 5-step engineering workflow navigation (st.navigation).
Engineered and authored by Eng. Aashir (c) 2026. All Rights Reserved.
Complies with BS 7671:2008 (Kelani Cables Table A1), IEC 60364-7-712, IEC 60269-6, DIN 43671, BS 7430.
"""
import streamlit as st
from ui.styles import apply_custom_css
from data.database import init_db
from core.project_state import init_project_state, get_active_project, get_design_value

# ---------------------------------------------------------------------------
# 1. Main Page Configuration & Initialization
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Solar PV Engineering Platform — Eng. Aashir",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)
apply_custom_css()
init_db()
init_project_state()

# ---------------------------------------------------------------------------
# 2. Sidebar Branding & Lead Engineer Watermark
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1e3a8a, #0f172a); color: white; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #3b82f6; margin-bottom: 12px;">
            <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 1.2px; color: #93c5fd; font-weight: 600;">Solar PV Engineering Suite</div>
            <div style="font-size: 18px; font-weight: 700; margin-top: 2px; color: #ffffff;">Eng. Aashir</div>
            <div style="font-size: 10px; color: #cbd5e1; margin-top: 2px;">Lead PV Systems Engineer &copy; 2026</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    proj = get_active_project()
    ac_kw = float(get_design_value("actual_ac_kw", proj.get("target_ac_capacity_kw", 5.0)))
    dc_kwp = float(get_design_value("actual_dc_kwp", round(ac_kw * 1.30, 2)))
    st.markdown(
        f"""
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 10px; font-size: 11px; margin-bottom: 10px;">
            <b>Active:</b> {proj.get('name', 'Active Project')[:24]}<br/>
            <b>Client:</b> {proj.get('customer_name', 'N/A')[:24]}<br/>
            <b>Plant:</b> {ac_kw:.1f} kW AC / {dc_kwp:.1f} kWp DC
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------------------------
# 3. Dynamic Capacity-Driven 7-Step Engineering Workflow Navigation
# ---------------------------------------------------------------------------
navigation_pages = {
    "01 – PROJECT": [
        st.Page("pages/1_📊_Dashboard.py", title="Executive Dashboard", icon="📊", default=True),
        st.Page("pages/2_⚙️_System_Configuration.py", title="System Configuration", icon="⚙️"),
        st.Page("pages/2_📁_Projects.py", title="Project Manager", icon="📁"),
        st.Page("pages/31_📋_Project_Details.py", title="Project Details", icon="📋"),
    ],
    "02 – EQUIPMENT LIBRARY": [
        st.Page("pages/3_🔋_Panel_Library.py", title="Panel Library", icon="🔋"),
        st.Page("pages/4_⚡_Inverter_Library.py", title="Inverter Library", icon="⚡"),
        st.Page("pages/33_📚_Equipment_Catalog.py", title="Equipment Catalog", icon="📚"),
        st.Page("pages/32_💾_Saved_Designs.py", title="Saved Designs", icon="💾"),
    ],
    "03 – PV ARRAY DESIGN": [
        st.Page("pages/0_🚀_Design_Studio.py", title="Guided Design Studio", icon="🚀"),
        st.Page("pages/5_📊_PV_Capacity.py", title="PV Capacity", icon="📊"),
        st.Page("pages/6_🔢_Panel_Quantity.py", title="Panel Quantity", icon="🔢"),
        st.Page("pages/7_🔌_String_Sizing.py", title="String Sizing", icon="🔌"),
        st.Page("pages/8_🔍_String_Voltage.py", title="String Voltage Check", icon="🔍"),
        st.Page("pages/10_⚡_DC_Current.py", title="DC Current Check", icon="⚡"),
        st.Page("pages/9_🧩_MPPT_Allocation.py", title="MPPT Allocation", icon="🧩"),
        st.Page("pages/12_📐_PV_Layout.py", title="PV Layout & Spacing", icon="📐"),
    ],
    "04 – INVERTER DESIGN": [
        st.Page("pages/13_🏗️_Inverter_Combination.py", title="Inverter Combinations", icon="🏗️"),
        st.Page("pages/11_📊_DC_AC_Ratio.py", title="DC/AC Ratio Analysis", icon="📊"),
    ],
    "05 – ELECTRICAL DESIGN": [
        st.Page("pages/3_⚡_Electrical_Design.py", title="Electrical Design Summary", icon="⚡"),
        st.Page("pages/14_🔌_DC_Cable.py", title="DC Cable Sizing", icon="🔌"),
        st.Page("pages/15_🔌_AC_Cable.py", title="AC Cable Sizing", icon="🔌"),
        st.Page("pages/16_📏_Voltage_Drop.py", title="Voltage Drop", icon="📏"),
        st.Page("pages/17_🛡️_MCB_Selection.py", title="MCB Selection", icon="🛡️"),
        st.Page("pages/18_🛡️_MCCB_Selection.py", title="MCCB Selection", icon="🛡️"),
        st.Page("pages/19_⚡_DC_Protection.py", title="DC Protection", icon="⚡"),
        st.Page("pages/20_⚡_AC_Protection.py", title="AC Protection", icon="⚡"),
        st.Page("pages/21_📊_Busbar.py", title="Busbar Sizing", icon="📊"),
        st.Page("pages/22_🌍_Earthing.py", title="Earthing System", icon="🌍"),
    ],
    "06 – SYSTEM OUTPUT": [
        st.Page("pages/24_✅_Design_Validation.py", title="Design Validation", icon="✅"),
        st.Page("pages/25_📋_Design_Summary.py", title="Design Summary", icon="📋"),
        st.Page("pages/4_📦_BOM_BOQ.py", title="BOQ Schedule", icon="📦"),
        st.Page("pages/26_📦_BOM.py", title="BOM Generator", icon="📦"),
        st.Page("pages/35_⚡_CEB_Tariff_Calculator.py", title="CEB Tariff Calculator", icon="⚡"),
        st.Page("pages/34_💰_Financial_ROI.py", title="Financial ROI", icon="💰"),
    ],
    "07 – REPORTS": [
        st.Page("pages/27_📄_Reports.py", title="Reports & SLD", icon="📄"),
        st.Page("pages/28_☀️_DC_Production.py", title="DC Production", icon="☀️"),
        st.Page("pages/29_⚡_AC_Production.py", title="AC Production", icon="⚡"),
        st.Page("pages/23_📉_System_Losses.py", title="System Losses", icon="📉"),
        st.Page("pages/30_📊_Meter_Selection.py", title="Meter Selection", icon="📊"),
        st.Page("pages/5_🧮_Calculators.py", title="Calculators Hub", icon="🧮"),
    ],
}

# Run the selected page via Streamlit navigation
nav = st.navigation(navigation_pages)
nav.run()

# ---------------------------------------------------------------------------
# 4. Global Engineering Watermark Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div style="text-align: center; color: #64748b; font-size: 12px; margin-top: 35px; border-top: 1px solid #e2e8f0; padding-top: 12px;">
        <b>Solar PV Engineering Design & BoQ Platform v2.0</b><br/>
        Authored & Engineered by <b>Eng. Aashir</b> — Lead PV Systems Engineer | &copy; 2026 All Rights Reserved<br/>
        Standards: <b>BS 7671:2008 (Kelani Cables Table A1)</b>, <b>IEC 60364-7-712</b>, <b>IEC 60269-6</b>, <b>DIN 43671</b>, <b>BS 7430</b>
    </div>
    """,
    unsafe_allow_html=True
)
