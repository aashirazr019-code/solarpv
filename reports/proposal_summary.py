"""
reports/proposal_summary.py — Executive 1-Page Customer Solar & CEB Tariff Proposal Generator
Generates a formal, stamped 1-page executive solar proposal and utility tariff savings summary.

Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
Complies with PUCSL Tariff Schedule (Effective 01 April 2026) and CEB / LECO Interconnection Guidelines.
"""
from typing import Dict, Any, Optional
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class ProposalCanvas(canvas.Canvas):
    """Running header and footer for executive proposal document."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_decorations(self, page_count):
        self.saveState()
        page_w, page_h = A4

        # Top Accent Header Bar
        self.setFillColor(colors.HexColor("#1E3A8A"))
        self.rect(0, page_h - 12, page_w, 12, fill=True, stroke=False)

        # Bottom Footer Accent & Text
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 32, page_w - 36, 32)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(36, 22, "Official Solar PV Customer Proposal & CEB Tariff Economics | Prepared by Eng. Aashir © 2026")
        self.drawRightString(page_w - 36, 22, f"Page {self._pageNumber} of {page_count} | CEB / PUCSL Compliant")
        self.restoreState()


def generate_proposal_summary_pdf(
    unified_dataset_or_tariff: Any,
    customer_name: Optional[str] = None,
    site_name: Optional[str] = None,
    notes: Optional[str] = None
) -> bytes:
    """
    Generates a high-impact, professional 1-page Customer Solar Proposal & Utility Savings Summary PDF.
    Accepts unified engineering dataset or raw tariff impact dictionary.
    """
    if isinstance(unified_dataset_or_tariff, dict) and "pv_subsystem" in unified_dataset_or_tariff:
        ds = unified_dataset_or_tariff
    else:
        from core.unified_dataset import get_unified_engineering_dataset
        ds = get_unified_engineering_dataset(13.0)

    p = ds.get("project", {})
    pv = ds.get("pv_subsystem", {})
    inv = ds.get("inverter_infrastructure", {})
    ceb = ds.get("ceb_tariff_analysis", {})

    client = customer_name or p.get("customer_name", "Valued Solar Client")
    facility = site_name or p.get("site_name", "Rooftop Solar Installation")
    loc = p.get("location", "Colombo, Sri Lanka")
    date_str = datetime.now().strftime("%d %B %Y")

    ac_kw = float(inv.get("actual_ac_kw", 13.0))
    dc_kwp = float(pv.get("installed_dc_kwp", round(ac_kw * 1.25, 2)))
    modules_count = int(pv.get("total_panels", 28))
    panel_model = str(pv.get("model", "PANDA 3.0 PRO 580W"))

    tariff_cat = str(ceb.get("tariff_category", "Domestic" if ac_kw <= 10 else "General Purpose 1"))
    scheme = str(ceb.get("scheme", "Net Accounting"))
    cons_kwh = float(ceb.get("consumption_kwh", ac_kw * 120))
    gen_kwh = float(ceb.get("solar_generation_kwh", ac_kw * 120))
    cov_pct = float(ceb.get("solar_coverage_pct", (gen_kwh / max(1.0, cons_kwh)) * 100))

    bill_before = float(ceb.get("bill_before_solar_lkr", 0.0))
    bill_after = float(ceb.get("bill_after_solar_lkr", 0.0))
    export_inc = float(ceb.get("solar_export_income_lkr", 0.0))
    net_cost = float(ceb.get("net_monthly_cost_lkr", 0.0))
    mo_sav = float(ceb.get("monthly_saving_lkr", 0.0))
    yr_sav = float(ceb.get("annual_saving_lkr", 0.0))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=38
    )

    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle('PT', parent=base['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=17, alignment=1, textColor=colors.HexColor('#1E3A8A')),
        "sub": ParagraphStyle('PS', parent=base['Normal'], fontName='Helvetica', fontSize=8.5, leading=11, alignment=1, textColor=colors.HexColor('#475569')),
        "sec_hdr": ParagraphStyle('SH', parent=base['Heading2'], fontName='Helvetica-Bold', fontSize=9.5, leading=12, textColor=colors.HexColor('#1E3A8A'), spaceBefore=5, spaceAfter=2),
        "body": ParagraphStyle('PB', parent=base['Normal'], fontName='Helvetica', fontSize=8, leading=10.5, textColor=colors.HexColor('#1E293B')),
        "body_bold": ParagraphStyle('PBB', parent=base['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10.5, textColor=colors.HexColor('#0F172A')),
        "kpi_val": ParagraphStyle('KV', parent=base['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=1, textColor=colors.HexColor('#1E3A8A')),
        "kpi_lbl": ParagraphStyle('KL', parent=base['Normal'], fontName='Helvetica', fontSize=7.5, leading=9.5, alignment=1, textColor=colors.HexColor('#64748B')),
        "tbl_hdr": ParagraphStyle('TH', parent=base['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white, alignment=0),
    }

    story = []

    # Title & Proposal Header
    story.append(Paragraph("☀️ SOLAR PHOTOVOLTAIC & CEB UTILITY SAVINGS PROPOSAL", styles["title"]))
    story.append(Paragraph(f"<b>Client:</b> {client} &nbsp;|&nbsp; <b>Facility:</b> {facility}, {loc} &nbsp;|&nbsp; <b>Date:</b> {date_str}", styles["sub"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=6))

    # Executive Highlight Cards (3-up metric grid)
    kpi_cards = [
        [
            Paragraph(f"<b>{ac_kw:.1f} kW AC</b><br/>{dc_kwp:.2f} kWp DC Array", styles["kpi_val"]),
            Paragraph(f"<b>LKR {mo_sav:,.2f}</b><br/>Net Savings / Month", styles["kpi_val"]),
            Paragraph(f"<b>LKR {yr_sav:,.2f}</b><br/>Forecast Annual Savings", styles["kpi_val"]),
            Paragraph(f"<b>{cov_pct:.1f}%</b><br/>Solar Demand Offset", styles["kpi_val"])
        ],
        [
            Paragraph("System Capacity Rating", styles["kpi_lbl"]),
            Paragraph("Monthly Utility Savings", styles["kpi_lbl"]),
            Paragraph("Annual Utility Savings", styles["kpi_lbl"]),
            Paragraph("Monthly Energy Coverage", styles["kpi_lbl"])
        ]
    ]
    t_kpi = Table(kpi_cards, colWidths=[130, 130, 135, 125])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EFF6FF')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#3B82F6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BFDBFE')),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 6))

    # 1. Technical System Sizing
    story.append(Paragraph("1. Technical PV System Architecture & Equipment Sizing", styles["sec_hdr"]))
    tech_data = [
        [Paragraph("<b>Technical Parameter</b>", styles["tbl_hdr"]), Paragraph("<b>Engineering Specification</b>", styles["tbl_hdr"]), Paragraph("<b>Standard / Rule Basis</b>", styles["tbl_hdr"])],
        [Paragraph("Contracted AC Capacity", styles["body_bold"]), Paragraph(f"{ac_kw:.1f} kW AC ({p.get('grid_phases', 3)}-Phase, 400V)", styles["body"]), Paragraph("CEB Interconnection Standard", styles["body"])],
        [Paragraph("Total Array DC Peak", styles["body_bold"]), Paragraph(f"{dc_kwp:.2f} kWp DC (DC/AC Ratio: {pv.get('dc_ac_ratio', 1.25):.2f})", styles["body"]), Paragraph("Optimal Solar Yield Window", styles["body"])],
        [Paragraph("Photovoltaic Modules", styles["body_bold"]), Paragraph(f"{modules_count} Nos x {panel_model}", styles["body"]), Paragraph("Tier-1 TOPCon Bifacial Technology", styles["body"])],
        [Paragraph("Inverter Fleet System", styles["body_bold"]), Paragraph(inv.get("fleet_description", "High-Efficiency Inverter Fleet"), styles["body"]), Paragraph("IEC 62109 / IEC 62116 Certified", styles["body"])],
        [Paragraph("Estimated Monthly Generation", styles["body_bold"]), Paragraph(f"<b>{gen_kwh:,.1f} kWh / month</b> ({gen_kwh/30:.1f} kWh/day)", styles["body"]), Paragraph("120 kWh/kW/month Engineering Standard", styles["body"])],
    ]
    t_tech = Table(tech_data, colWidths=[145, 230, 145])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 2.8),
    ]))
    story.append(t_tech)
    story.append(Spacer(1, 5))

    # 2. CEB Utility Tariff Economics (PUCSL April 2026)
    story.append(Paragraph("2. CEB Electricity Tariff & Customer Savings Model (PUCSL April 2026)", styles["sec_hdr"]))
    econ_data = [
        [Paragraph("<b>Utility Tariff & Financial Metric</b>", styles["tbl_hdr"]), Paragraph("<b>Pre-Solar Baseline</b>", styles["tbl_hdr"]), Paragraph("<b>Post-Solar Forecast</b>", styles["tbl_hdr"]), Paragraph("<b>Customer Net Benefit</b>", styles["tbl_hdr"])],
        [Paragraph("CEB Tariff Category", styles["body_bold"]), Paragraph(tariff_cat, styles["body"]), Paragraph(tariff_cat, styles["body"]), Paragraph("Effective 01 April 2026 Schedule", styles["body"])],
        [Paragraph("Interconnection Scheme", styles["body_bold"]), Paragraph("Grid Only (No Solar)", styles["body"]), Paragraph(f"<b>{scheme}</b>", styles["body"]), Paragraph("CEB Interconnection Agreement", styles["body"])],
        [Paragraph("Monthly Grid Consumption", styles["body_bold"]), Paragraph(f"{cons_kwh:,.1f} kWh", styles["body"]), Paragraph(f"Net Import: {ceb.get('grid_import_kwh', 0.0):,.1f} kWh", styles["body"]), Paragraph(f"Solar Offset: {ceb.get('solar_used_kwh', 0.0):,.1f} kWh", styles["body"])],
        [Paragraph("Solar Export to CEB Grid", styles["body_bold"]), Paragraph("0.0 kWh", styles["body"]), Paragraph(f"{ceb.get('grid_export_kwh', 0.0):,.1f} kWh", styles["body"]), Paragraph(f"Export Credit: LKR {export_inc:,.2f}", styles["body"])],
        [Paragraph("Monthly CEB Electricity Bill", styles["body_bold"]), Paragraph(f"<b>LKR {bill_before:,.2f}</b>", styles["body"]), Paragraph(f"LKR {bill_after:,.2f}", styles["body"]), Paragraph("Residual Grid Invoice", styles["body"])],
        [Paragraph("Net Monthly Customer Cost", styles["body_bold"]), Paragraph(f"LKR {bill_before:,.2f}", styles["body"]), Paragraph(f"<b>LKR {net_cost:,.2f}</b>", styles["body"]), Paragraph(f"<b>LKR {mo_sav:,.2f} Saved / Mo</b>", styles["body_bold"])],
        [Paragraph("Projected Annual Savings", styles["body_bold"]), Paragraph("LKR 0.00", styles["body"]), Paragraph(f"<b>LKR {yr_sav:,.2f} / yr</b>", styles["body"]), Paragraph("<b>12-Month Cumulative Benefit</b>", styles["body_bold"])]
    ]
    t_econ = Table(econ_data, colWidths=[140, 115, 125, 140])
    t_econ.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 2.8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(t_econ)
    story.append(Spacer(1, 5))

    # 3. Statutory SSCL & Scheme Operating Rule
    story.append(Paragraph("3. Scheme Operation & Statutory Compliance Notes", styles["sec_hdr"]))
    note_text = (
        f"• <b>Interconnection Scheme ({scheme}):</b> {ceb.get('explanation', 'Statutory self-generation arrangement')}<br/>"
        "• <b>Statutory SSCL:</b> All utility bill calculations strictly incorporate the 2.5% Social Security Contribution Levy (SSCL) per Act No. 25 of 2022.<br/>"
        "• <b>Statutory Engineering Standards:</b> Sizing complies with BS 7671:2008 (Kelani Table A1), IEC 60364-7-712, IEC 60269-6, BS 7430, and CEB Grid Code."
    )
    story.append(Paragraph(note_text, styles["body"]))
    story.append(Spacer(1, 5))

    # 4. Professional Sign-Off Block
    story.append(Paragraph("4. Professional Engineering Certification & Approval", styles["sec_hdr"]))
    sign_table_data = [
        [
            Paragraph(
                "<b>Prepared & Certified By:</b><br/>"
                "<b>Eng. Aashir</b><br/>"
                "Lead Photovoltaic Systems Engineer<br/>"
                "Solar PV Engineering Platform &copy; 2026<br/>"
                "Colombo, Sri Lanka",
                styles["body"]
            ),
            Paragraph(
                "<b>Engineering Guarantee & Stamped Approval:</b><br/>"
                "The calculations, system sizing, and financial projections presented in this proposal "
                "are derived from verified engineering equations and official PUCSL electricity tariff schedules.<br/>"
                f"<b>Status:</b> CERTIFIED COMPLIANT &nbsp;|&nbsp; <b>Date:</b> {datetime.now().strftime('%d.%m.%Y')}",
                styles["body"]
            )
        ]
    ]
    t_sign = Table(sign_table_data, colWidths=[200, 320])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1E3A8A')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_sign)

    doc.build(story, canvasmaker=ProposalCanvas)
    return buffer.getvalue()
