"""
reports/boq_excel_generator.py — Professional Excel BOQ Generator
Generates formatted Excel workbooks aligned with the reference BoQ template structure,
supporting openpyxl formatting, category section headers, and strict compliance
with the Blank Field Rule.
Authored by Eng. Aashir © 2026.
"""
import io
import os
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from typing import Dict, List, Any, Optional
from datetime import datetime

MASTER_TEMPLATE_DEFAULT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "BOQ", "sample_boq.xlsx")
)


def generate_master_template_boq_excel(
    boq_items: List[Dict[str, Any]],
    project_metadata: Optional[Dict[str, Any]] = None,
    template_path: Optional[str] = None
) -> bytes:
    """
    Directly fills data into the exact sample_boq.xlsx master template.
    Preserves all merged cells, original rows, column positions, fonts, and borders.
    Adheres strictly to the Blank Field Rule: unknown or uncalculated values remain blank.
    """
    t_path = template_path or MASTER_TEMPLATE_DEFAULT
    if not os.path.exists(t_path):
        return generate_boq_excel(boq_items, project_metadata)

    wb = openpyxl.load_workbook(t_path)
    ws1 = wb["Sheet1"]
    ws2 = wb["Sheet2"] if "Sheet2" in wb.sheetnames else None

    meta = project_metadata or {}
    capacity_kw = meta.get("system_capacity_kw", meta.get("capacity_kw", 5.0))
    customer_name = meta.get("customer_name", "").strip()
    date_str = meta.get("date", "").strip()
    phase_str = meta.get("phase_desc", "Single Phase 230V" if capacity_kw <= 5.0 else "Three Phase 400V")

    # Row 5: Customer and Date
    if customer_name:
        ws1["A5"] = f"Customer           : {customer_name}"
    if date_str:
        ws1["G5"] = f"Date : {date_str}"

    # Row 6: Installation Capacity
    ws1["A6"] = f"Installation Cap : {capacity_kw:.1f} kW ({phase_str})"

    # Map keys to row numbers in Sheet1
    row_map_s1 = {
        "panel": 10,
        "inverter": 11,
        "battery": 12,
        "dc_isolator": 14,
        "dc_spd": 15,
        "dc_fuse": 16,
        "fuse_holder": 17,
        "mc4": 18,
        "earth_rod": 19,
        "ac_isolator": 22,
        "ac_spd": 23,
        "mccb": 24,
        "mcb": 24,
        "bus_bar": 25,
        "abc_box": 26,
        "steel_box": 27,
        "dc_wire": 30,
        "earth_wire": 31,
        "ac_wire": 32,
        "bar": 35,
        "mid_clamp": 36,
        "end_clamp": 37,
        "ceat_clip": 38,
        "angle_clamp": 39,
        "splicer": 40,
        "z_bracket_double": 41,
        "z_bracket_single": 42,
        "tile_hook": 43,
        "nut": 44,
        "bolt": 45,
        "amana_screw": 46
    }

    def classify_item(it):
        name = str(it.get("item_name", "")).lower()
        desc = str(it.get("description", "")).lower()
        cat = str(it.get("category", "")).lower()
        c = f"{name} {desc} {cat}"

        if "fuse holder" in c:
            return "fuse_holder"
        if "dc" in c and "fuse" in c:
            return "dc_fuse"
        if "dc" in c and "isolator" in c:
            return "dc_isolator"
        if "dc" in c and "spd" in c:
            return "dc_spd"
        if "ac" in c and "isolator" in c:
            return "ac_isolator"
        if "ac" in c and "spd" in c:
            return "ac_spd"
        if "lockable" in c or "padlockable" in c:
            return "lockable"
        if "panel" in c or "module" in c:
            return "panel"
        if "inverter" in c:
            return "inverter"
        if "mc4" in c:
            return "mc4"
        if "earth rod" in c or "electrode" in c:
            return "earth_rod"
        if "mccb" in c or "mcb" in c or "breaker" in c:
            return "mccb"
        if "bus bar" in c or "busbar" in c:
            return "bus_bar"
        if "abc" in c:
            return "abc_box"
        if "steel" in c:
            return "steel_box"
        if "dc" in c and ("wire" in c or "cable" in c):
            return "dc_wire"
        if "earth" in c and ("wire" in c or "cable" in c):
            return "earth_wire"
        if "ac" in c and ("wire" in c or "cable" in c):
            return "ac_wire"
        if "mid clamp" in c:
            return "mid_clamp"
        if "end clamp" in c:
            return "end_clamp"
        if "rail" in c or "bar" in c:
            return "bar"
        if "nut" in c:
            return "nut"
        if "bolt" in c:
            return "bolt"
        if "screw" in c:
            return "amana_screw"
        return None

    for it in boq_items:
        key = classify_item(it)
        if not key:
            continue

        brand = it.get("brand", "")
        spec = it.get("specification", it.get("capacity", ""))
        unit = it.get("unit", "")
        qty = it.get("quantity", "")
        u_price = it.get("unit_price", "")

        if key == "lockable" and ws2:
            row = 33
            if brand: ws2.cell(row=row, column=3, value=brand)
            if spec: ws2.cell(row=row, column=4, value=spec)
            if unit: ws2.cell(row=row, column=5, value=unit)
            if qty not in ["", 0, None]: ws2.cell(row=row, column=6, value=qty)
            if u_price not in ["", None]: ws2.cell(row=row, column=7, value=u_price)
        elif key in row_map_s1:
            row = row_map_s1[key]
            if brand: ws1.cell(row=row, column=3, value=brand)
            if spec: ws1.cell(row=row, column=4, value=spec)
            if unit: ws1.cell(row=row, column=5, value=unit)
            if qty not in ["", 0, None]: ws1.cell(row=row, column=6, value=qty)
            if u_price not in ["", None]: ws1.cell(row=row, column=7, value=u_price)

    out_buf = io.BytesIO()
    wb.save(out_buf)
    return out_buf.getvalue()


def generate_boq_excel(
    boq_items: List[Dict[str, Any]],
    project_metadata: Optional[Dict[str, Any]] = None,
    template_path: Optional[str] = None
) -> bytes:
    """
    Generates a professionally styled Solar PV Bill of Quantities Excel spreadsheet.
    Adheres strictly to the Blank Field Rule: customer details, unit prices, and
    suppliers are left blank unless explicitly provided by the engineer.
    """
    meta = project_metadata or {}
    capacity_kw = meta.get("system_capacity_kw", meta.get("capacity_kw", 5.0))
    customer_name = meta.get("customer_name", "").strip()
    date_str = meta.get("date", "").strip()
    if not date_str and meta.get("auto_date", False):
        date_str = datetime.now().strftime("%Y-%m-%d")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bill of Quantity"

    # Ensure grid lines are visible
    ws.views.sheetView[0].showGridLines = True

    # ---------------------------------------------------------------------------
    # Style Definitions
    # ---------------------------------------------------------------------------
    title_font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
    subtitle_font = Font(name="Calibri", size=12, bold=True, color="334155")
    meta_label_font = Font(name="Calibri", size=11, bold=True, color="0F172A")
    meta_val_font = Font(name="Calibri", size=11, bold=False, color="1E293B")
    
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    category_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    category_font = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
    
    data_font = Font(name="Calibri", size=10, color="0F172A")
    data_bold = Font(name="Calibri", size=10, bold=True, color="0F172A")
    
    thin_border_side = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=thin_border_side
    )
    
    header_border = Border(
        left=Side(border_style="medium", color="1E3A8A"),
        right=Side(border_style="medium", color="1E3A8A"),
        top=Side(border_style="medium", color="1E3A8A"),
        bottom=Side(border_style="medium", color="1E3A8A")
    )

    # ---------------------------------------------------------------------------
    # Document Header Block
    # ---------------------------------------------------------------------------
    company_name = meta.get("company_name", "East West Solar Pvt Ltd")
    doc_title = meta.get("doc_title", "Bill of Quantity - 2026")
    
    ws.merge_cells("B2:G2")
    ws["B2"] = company_name
    ws["B2"].font = title_font
    ws["B2"].alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells("B3:G3")
    ws["B3"] = doc_title
    ws["B3"].font = subtitle_font
    ws["B3"].alignment = Alignment(horizontal="left", vertical="center")

    # Metadata Block (Strict Blank Field Rule Compliance)
    # Row 5: Customer Name and Date
    ws["A5"] = "Customer           :"
    ws["A5"].font = meta_label_font
    ws["B5"] = customer_name if customer_name else ""
    ws["B5"].font = meta_val_font

    ws["F5"] = "Date :"
    ws["F5"].font = meta_label_font
    ws["G5"] = date_str if date_str else ""
    ws["G5"].font = meta_val_font

    # Row 6: Installation Capacity
    ws["A6"] = "Installation Cap :"
    ws["A6"].font = meta_label_font
    ws["B6"] = f"{capacity_kw:.1f} kW ({meta.get('phase_desc', 'Solar PV System')})"
    ws["B6"].font = meta_val_font

    # ---------------------------------------------------------------------------
    # Table Column Headers
    # ---------------------------------------------------------------------------
    headers = [
        "S/N",
        "Description",
        "Brand",
        "Capacity / Specification",
        "Unit",
        "QTY",
        "Unit Price",
        "Total Price",
        "Remarks"
    ]
    
    header_row = 8
    ws.row_dimensions[header_row].height = 25

    for col_idx, h_text in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=h_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = header_border

    # ---------------------------------------------------------------------------
    # Itemized Table Population
    # ---------------------------------------------------------------------------
    curr_row = 9
    current_category = None
    item_rows = []

    # Map categories to clean display names
    for item in boq_items:
        category = item.get("category", "General")

        # Category separator row
        if category != current_category:
            current_category = category
            ws.row_dimensions[curr_row].height = 22
            cat_cell = ws.cell(row=curr_row, column=2, value=f"— {category.upper()} —")
            cat_cell.font = category_font
            cat_cell.fill = category_fill
            cat_cell.alignment = Alignment(horizontal="left", vertical="center")
            
            # Fill across row for category banner
            for c in range(1, len(headers) + 1):
                cell_c = ws.cell(row=curr_row, column=c)
                cell_c.fill = category_fill
                cell_c.border = cell_border
            curr_row += 1

        ws.row_dimensions[curr_row].height = 20
        item_rows.append(curr_row)

        # S/N
        sn_val = item.get("sn", "")
        cell_sn = ws.cell(row=curr_row, column=1, value=sn_val)
        cell_sn.alignment = Alignment(horizontal="center", vertical="center")
        cell_sn.font = data_font
        cell_sn.border = cell_border

        # Description
        desc_val = item.get("description", item.get("item_name", ""))
        cell_desc = ws.cell(row=curr_row, column=2, value=desc_val)
        cell_desc.alignment = Alignment(horizontal="left", vertical="center")
        cell_desc.font = data_bold if category in ["Solar PV Modules", "Inverter"] else data_font
        cell_desc.border = cell_border

        # Brand
        brand_val = item.get("brand", "")
        cell_brand = ws.cell(row=curr_row, column=3, value=brand_val)
        cell_brand.alignment = Alignment(horizontal="left", vertical="center")
        cell_brand.font = data_font
        cell_brand.border = cell_border

        # Specification / Capacity
        spec_val = item.get("capacity", item.get("specification", item.get("rating", "")))
        cell_spec = ws.cell(row=curr_row, column=4, value=spec_val)
        cell_spec.alignment = Alignment(horizontal="left", vertical="center")
        cell_spec.font = data_font
        cell_spec.border = cell_border

        # Unit
        unit_val = item.get("unit", "nos")
        cell_unit = ws.cell(row=curr_row, column=5, value=unit_val)
        cell_unit.alignment = Alignment(horizontal="center", vertical="center")
        cell_unit.font = data_font
        cell_unit.border = cell_border

        # QTY
        qty_val = item.get("quantity", 0)
        try:
            qty_num = int(qty_val) if float(qty_val).is_integer() else round(float(qty_val), 1)
        except Exception:
            qty_num = qty_val
        cell_qty = ws.cell(row=curr_row, column=6, value=qty_num)
        cell_qty.alignment = Alignment(horizontal="right", vertical="center")
        cell_qty.font = data_bold
        cell_qty.border = cell_border

        # Unit Price (Blank Field Rule: Blank unless explicitly provided)
        u_price = item.get("unit_price", "")
        cell_up = ws.cell(row=curr_row, column=7, value=u_price if u_price != "" else None)
        cell_up.alignment = Alignment(horizontal="right", vertical="center")
        cell_up.font = data_font
        cell_up.border = cell_border
        if u_price != "" and isinstance(u_price, (int, float)):
            cell_up.number_format = "#,##0.00"

        # Total Price (Formula = QTY * Unit Price)
        cell_tp = ws.cell(row=curr_row, column=8)
        cell_tp.value = f"=IF(ISNUMBER(G{curr_row}), F{curr_row}*G{curr_row}, \"\")"
        cell_tp.alignment = Alignment(horizontal="right", vertical="center")
        cell_tp.font = data_bold
        cell_tp.border = cell_border
        cell_tp.number_format = "#,##0.00"

        # Remarks
        rem_val = item.get("remarks", "")
        cell_rem = ws.cell(row=curr_row, column=9, value=rem_val)
        cell_rem.alignment = Alignment(horizontal="left", vertical="center")
        cell_rem.font = data_font
        cell_rem.border = cell_border

        curr_row += 1

    # ---------------------------------------------------------------------------
    # Total Summary Row
    # ---------------------------------------------------------------------------
    ws.row_dimensions[curr_row].height = 24
    ws.cell(row=curr_row, column=1).border = cell_border
    total_lbl = ws.cell(row=curr_row, column=2, value="TOTAL ESTIMATED AMOUNT")
    total_lbl.font = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
    total_lbl.alignment = Alignment(horizontal="left", vertical="center")
    total_lbl.border = cell_border

    for c in range(3, 8):
        cell_fill_tot = ws.cell(row=curr_row, column=c)
        cell_fill_tot.border = cell_border

    if item_rows:
        total_cell = ws.cell(row=curr_row, column=8)
        first_r = item_rows[0]
        last_r = item_rows[-1]
        total_cell.value = f"=SUM(H{first_r}:H{last_r})"
        total_cell.font = Font(name="Calibri", size=11, bold=True, color="1E3A8A")
        total_cell.alignment = Alignment(horizontal="right", vertical="center")
        total_cell.border = cell_border
        total_cell.number_format = "#,##0.00"

    ws.cell(row=curr_row, column=9).border = cell_border
    curr_row += 2

    # ---------------------------------------------------------------------------
    # Footer & Engineering Disclaimer
    # ---------------------------------------------------------------------------
    ws.cell(row=curr_row, column=1, value="Note / Engineering Disclaimer:").font = Font(name="Calibri", size=9, bold=True, color="64748B")
    curr_row += 1
    disc_text = meta.get(
        "disclaimer",
        "Automatic BOM selection is based on the configured engineering rules, component database, "
        "and available equipment data. Final equipment selection must be verified against the latest "
        "manufacturer datasheets, applicable Sri Lankan utility requirements, and project/site conditions."
    )
    ws.cell(row=curr_row, column=1, value=disc_text).font = Font(name="Calibri", size=9, italic=True, color="64748B")
    curr_row += 1
    ws.cell(row=curr_row, column=1, value="Prepared & Engineered by Eng. Aashir © 2026. All Rights Reserved.").font = Font(name="Calibri", size=9, bold=True, color="64748B")

    # ---------------------------------------------------------------------------
    # Column Widths Optimization (Auto-fit matching sample template)
    # ---------------------------------------------------------------------------
    col_widths = {
        "A": 7.0,   # S/N
        "B": 36.0,  # Description
        "C": 20.0,  # Brand
        "D": 32.0,  # Capacity / Spec
        "E": 8.0,   # Unit
        "F": 10.0,  # QTY
        "G": 14.0,  # Unit Price
        "H": 16.0,  # Total Price
        "I": 40.0   # Remarks
    }

    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    # Save to byte buffer
    out_buf = io.BytesIO()
    wb.save(out_buf)
    return out_buf.getvalue()
