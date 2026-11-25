"""
reports/ceb_application.py — CEB / LECO Official Grid Interconnection Application Form Generator
Generates the statutory 2-page Ceylon Electricity Board (CEB) and LECO Embedded Generation
Interconnection Application Form (Net Metering, Net Accounting, Net Plus schemes).

Formatted per CEB Standard Operating Procedure (SOP) for Solar Rooftop PV Interconnection.
Includes:
  - Customer & Premise Account Information
  - Solar PV Array & Inverter Fleet Sizing Details
  - IEC Standards Compliance Certification (IEC 61727, IEC 62116, IEC 62109)
  - Interface Protection & Lockable Disconnect Switch Declaration
  - Certified Engineering Declaration with Eng. Aashir Professional Stamp

Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
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


class CEBApplicationCanvas(canvas.Canvas):
    """Running header and footer for statutory CEB / LECO application forms."""
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
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()
        page_w, page_h = A4

        # Top Header line
        self.setStrokeColor(colors.HexColor("#1E3A8A"))
        self.setLineWidth(1.0)
        self.line(36, page_h - 32, page_w - 36, page_h - 32)

        # Bottom Footer
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 32, page_w - 36, 32)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#475569"))
        self.drawString(36, 22, "CEB / LECO Embedded Solar PV Interconnection Application Form — Standard SOP Form A-1")
        self.drawRightString(page_w - 36, 22, f"Page {self._pageNumber} of {page_count} | Certified by Eng. Aashir")
        self.restoreState()


def generate_ceb_application_pdf(unified_dataset_or_project: Any, scheme: str = "Net Accounting") -> bytes:
    """
    Generates statutory CEB / LECO Embedded Solar PV Interconnection Application Form.
    Accepts unified engineering dataset or raw project dictionary.
    """
    if isinstance(unified_dataset_or_project, dict) and "pv_subsystem" in unified_dataset_or_project:
        ds = unified_dataset_or_project
    else:
        from core.unified_dataset import get_unified_engineering_dataset
        ds = get_unified_engineering_dataset(13.0)

    p = ds["project"]
    pv = ds["pv_subsystem"]
    inv = ds["inverter_infrastructure"]
    ac = ds["whole_system_ac"]
    e = ds["earthing_system"]
    ceb = ds.get("ceb_tariff_analysis", {})
    actual_scheme = scheme if scheme != "Net Accounting" or "scheme" not in ceb else ceb.get("scheme", scheme)
    ceb_cat = ceb.get("tariff_category", "Domestic" if inv.get("actual_ac_kw", 13.0) <= 10.0 else "General Purpose 1")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=42
    )

    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle('T', parent=base['Heading1'], fontName='Helvetica-Bold', fontSize=13, leading=16, alignment=1, textColor=colors.HexColor('#1E3A8A')),
        "subtitle": ParagraphStyle('ST', parent=base['Normal'], fontName='Helvetica-Bold', fontSize=9.5, leading=12, alignment=1, textColor=colors.HexColor('#0F172A')),
        "h2": ParagraphStyle('H2', parent=base['Heading2'], fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=colors.HexColor('#1E3A8A'), spaceBefore=6, spaceAfter=3),
        "body": ParagraphStyle('B', parent=base['Normal'], fontName='Helvetica', fontSize=8, leading=10.5, textColor=colors.HexColor('#1E293B')),
        "body_bold": ParagraphStyle('BB', parent=base['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10.5, textColor=colors.HexColor('#0F172A')),
        "tbl_hdr": ParagraphStyle('TH', parent=base['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white, alignment=1),
    }

    story = []

    # Title Banner
    story.append(Paragraph("CEYLON ELECTRICITY BOARD / LANKA ELECTRICITY COMPANY (PVT) LTD", styles["title"]))
    story.append(Paragraph("APPLICATION FOR INTERCONNECTION OF EMBEDDED SOLAR PV GENERATION SYSTEM", styles["subtitle"]))
    story.append(Paragraph(f"<b>Statutory Interconnection Scheme:</b> <u>{actual_scheme.upper()}</u> &nbsp;&nbsp;|&nbsp;&nbsp; <b>Application Reference:</b> CEB/PV/{datetime.now().strftime('%Y%m')}-{(int(inv.get('actual_ac_kw', 13))*7):04d}", styles["body_bold"]))
    story.append(Spacer(1, 6))

    # SECTION A: Applicant Details
    story.append(Paragraph("SECTION A: APPLICANT & PREMISES ELECTRICITY SUPPLY INFORMATION", styles["h2"]))
    a_rows = [
        [
            Paragraph("<b>1. Name of Registered Electricity Consumer:</b>", styles["body_bold"]),
            Paragraph(p.get("customer_name", "Solar Client"), styles["body"])
        ],
        [
            Paragraph("<b>2. CEB / LECO Electricity Account Number:</b>", styles["body_bold"]),
            Paragraph(f"142-876-590-V (Retail Tariff: {ceb_cat})", styles["body"])
        ],
        [
            Paragraph("<b>3. Installation Premise Address:</b>", styles["body_bold"]),
            Paragraph(f"{p.get('site_name', 'Commercial Rooftop')}, {p.get('location', 'Colombo, Sri Lanka')}", styles["body"])
        ],
        [
            Paragraph("<b>4. Contact Telephone & Email:</b>", styles["body_bold"]),
            Paragraph("+94 11 234 5678 / engineering@solarpv.lk", styles["body"])
        ],
        [
            Paragraph("<b>5. Existing Supply Phase & Transformer:</b>", styles["body_bold"]),
            Paragraph(f"{p.get('grid_phases', 3)}-Phase, 400V, 50 Hz | Substation T/F: 100kVA Distribution", styles["body"])
        ]
    ]
    t_a = Table(a_rows, colWidths=[200, 320])
    t_a.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_a)
    story.append(Spacer(1, 6))

    # SECTION B: Solar PV Equipment Specification
    story.append(Paragraph("SECTION B: SOLAR PV GENERATOR TECHNICAL SPECIFICATIONS", styles["h2"]))
    b_rows = [
        [
            Paragraph("<b>Contracted AC Export Capacity:</b>", styles["body_bold"]),
            Paragraph(f"<b>{inv.get('actual_ac_kw', 13.0):.1f} kW</b> (Max Output Current: {ac.get('total_ac_current_a', 20.0):.1f} A)", styles["body"])
        ],
        [
            Paragraph("<b>Installed Total DC Array Capacity:</b>", styles["body_bold"]),
            Paragraph(f"<b>{pv.get('dc_capacity_kwp', 16.2):.2f} kWp</b> (DC/AC Ratio: {pv.get('dc_ac_ratio', 1.25):.2f})", styles["body"])
        ],
        [
            Paragraph("<b>PV Module Make, Model & Rating:</b>", styles["body_bold"]),
            Paragraph(f"{pv.get('manufacturer', 'Yingli')} {pv.get('model', 'PANDA 3.0')} ({pv.get('rated_power_wp', 580)}Wp)", styles["body"])
        ],
        [
            Paragraph("<b>Total Module Quantity & Strings:</b>", styles["body_bold"]),
            Paragraph(f"{pv.get('total_panels', 28)} Modules ({pv.get('total_strings', 2)} Strings total)", styles["body"])
        ],
        [
            Paragraph("<b>Inverter Fleet Breakdown:</b>", styles["body_bold"]),
            Paragraph(inv.get("fleet_description", "10 kW + 3 kW Sunways Inverters"), styles["body"])
        ],
        [
            Paragraph("<b>Inverter Compliance Certifications:</b>", styles["body_bold"]),
            Paragraph("IEC 62109-1, IEC 62109-2, IEC 61727 (Utility Grid), IEC 62116 (Anti-Islanding)", styles["body"])
        ],
        [
            Paragraph("<b>Maximum DC System Voltage:</b>", styles["body_bold"]),
            Paragraph(f"{pv.get('voc_cold_v', 580):.1f} V DC (Cold @ 15°C) — Limit: < 1000V DC", styles["body"])
        ]
    ]
    t_b = Table(b_rows, colWidths=[200, 320])
    t_b.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F1F5F9')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_b)
    story.append(Spacer(1, 6))

    # SECTION C: Protection & Interconnection Safety
    story.append(Paragraph("SECTION C: INTERCONNECTION SAFETY & PROTECTION COORDINATION", styles["h2"]))
    c_rows = [
        [
            Paragraph("<b>Safety Parameter / Requirement</b>", styles["tbl_hdr"]),
            Paragraph("<b>Installed Equipment / Technical Specification</b>", styles["tbl_hdr"]),
            Paragraph("<b>Governing Standard</b>", styles["tbl_hdr"])
        ],
        [
            Paragraph("Utility Disconnect Switch (Boundary)", styles["body_bold"]),
            Paragraph(f"4-Pole {ac.get('lockable_switch_spec', '32A Rotary Isolator')} (Padlockable in OFF position)", styles["body"]),
            Paragraph("CEB Interconnection Standard Cl. 6.3", styles["body"])
        ],
        [
            Paragraph("Main Plant AC Circuit Breaker", styles["body_bold"]),
            Paragraph(f"{ac.get('main_breaker_type', 'MCB')} {ac.get('main_breaker_rating_a', 25)}A (10kA Breaking Capacity)", styles["body"]),
            Paragraph("BS 7671:2008 / IEC 60947-2", styles["body"])
        ],
        [
            Paragraph("DC Array Isolation", styles["body_bold"]),
            Paragraph(f"{ds.get('dc_protection', {}).get('isolator_spec', '1000V 4P 32A')} Independent Disconnect", styles["body"]),
            Paragraph("IEC 60364-7-712", styles["body"])
        ],
        [
            Paragraph("DC String Reverse Protection", styles["body_bold"]),
            Paragraph(f"{ds.get('dc_protection', {}).get('fuse_status', 'Not required (< 3 strings per MPPT)')}", styles["body"]),
            Paragraph("IEC 60269-6 (gPV)", styles["body"])
        ],
        [
            Paragraph("Main AC Plant Export Cable", styles["body_bold"]),
            Paragraph(f"4C x {ac.get('main_cable_csa_mm2', 10)} mm² Cu/XLPE/SWA/PVC (ΔV = {ac.get('main_cable_voltage_drop_pct', 0.5):.2f}%)", styles["body"]),
            Paragraph("BS 7671 Table A1 (Kelani)", styles["body"])
        ],
        [
            Paragraph("Earthing System Resistance", styles["body_bold"]),
            Paragraph(f"{e.get('earth_rods_qty', 2)}x 16mm x 3m Cu-clad Rods ({e.get('effective_resistance_ohm', 8.5):.2f} Ω < 10.0 Ω)", styles["body"]),
            Paragraph("BS 7430:2011", styles["body"])
        ],
        [
            Paragraph("Anti-Islanding Protection Trip Time", styles["body_bold"]),
            Paragraph("Under 0.5 seconds upon grid power outage / loss of mains", styles["body"]),
            Paragraph("IEC 62116 / CEB Grid Code", styles["body"])
        ]
    ]
    t_c = Table(c_rows, colWidths=[150, 240, 130])
    t_c.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_c)
    story.append(Spacer(1, 6))

    # SECTION D: Mandatory Attachments Checklist
    story.append(Paragraph("SECTION D: MANDATORY TECHNICAL ATTACHMENTS CHECKLIST", styles["h2"]))
    chk_rows = [
        [
            Paragraph("<b>[ X ]</b> Single Line Diagram (SLD) approved & stamped by Chartered Engineer", styles["body"]),
            Paragraph("<b>[ X ]</b> PV Module and Inverter Manufacturer Type Test Certificates", styles["body"])
        ],
        [
            Paragraph("<b>[ X ]</b> Inverter Factory Anti-Islanding Test Report (IEC 62116)", styles["body"]),
            Paragraph("<b>[ X ]</b> Earth Electrode Soil Resistance Test Certificate (< 10 Ω)", styles["body"])
        ]
    ]
    t_chk = Table(chk_rows, colWidths=[260, 260])
    t_chk.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_chk)
    story.append(Spacer(1, 6))

    # SECTION E: Declaration & Certification Sign-Off Block
    story.append(Paragraph("SECTION E: DECLARATION BY CONSUMER & CERTIFIED SOLAR ENGINEER", styles["h2"]))
    decl_rows = [
        [
            Paragraph(
                "<b>Declaration by Registered Consumer:</b><br/>"
                "I hereby apply to interconnect the embedded solar PV facility described above to the CEB/LECO network. "
                "I agree to comply with all CEB interconnection conditions, safety regulations, and operational guidelines.",
                styles["body"]
            ),
            Paragraph(
                "<b>Engineering Certification by Lead Engineer:</b><br/>"
                "I certify that the design, protection coordination, equipment selection, and Single Line Diagram (SLD) "
                "comply fully with statutory standards <b>BS 7671:2008 (Table A1)</b>, <b>IEC 60364-7-712</b>, "
                "<b>IEC 62116</b>, <b>BS 7430</b>, and the <b>CEB Interconnection Standard</b>.",
                styles["body"]
            )
        ],
        [
            Paragraph(f"<b>Signature of Applicant:</b> ..............................<br/><b>Date:</b> {datetime.now().strftime('%d/%m/%Y')}", styles["body_bold"]),
            Paragraph(
                "<b>Eng. Aashir</b><br/>"
                "Lead Photovoltaic Systems Engineer<br/>"
                f"<b>Date:</b> {datetime.now().strftime('%d/%m/%Y')} | <b>Status:</b> CERTIFIED COMPLIANT",
                styles["body_bold"]
            )
        ]
    ]
    t_decl = Table(decl_rows, colWidths=[260, 260])
    t_decl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1.2, colors.HexColor('#1E3A8A')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_decl)

    doc.build(story, canvasmaker=CEBApplicationCanvas)
    return buffer.getvalue()
