"""
reports/sld_generator.py — Parametric Single Line Diagram (SLD) Engine
Generates CAD-standard, professional Single Line Diagrams in SVG and vector PDF format.
Faithfully follows the engineering presentation, CAD title block, and equipment arrangement
of Eng. Aashir's reference blueprints extracted from "single line diagrams":
  - 5KW SINGLE LINE DIiagram 5kw 635wp.pdf / 5kw 580wp.pdf (Vertical Single-Inverter)
  - Mr. TM Irfan- 20kW SINGLE LINE DIAGRAM.pdf (Vertical 20kW Inverter)
  - 13KW azr.pdf / 13 kw.dwg (Horizontal Multi-Inverter Collector Busbar)
  - 260 kw_AutoDWG.pdf / 260 kw.dwg (Large Commercial Multi-Inverter Fleet)

Features:
  - Dual Topologies:
      1. Vertical Single-Inverter Layout for 1-inverter systems (5 kW, 10 kW, 20 kW, 25 kW)
      2. Horizontal Collector-Busbar Layout for multi-inverter systems (13 kW to 1 MW+)
  - Reusable CAD label helpers: draw_component_label(), draw_multiline_label(),
    draw_value_label(), draw_connection_label() with white cutout backgrounds to prevent wire collision.
  - Dynamic Busbar Phase Configuration (1Ph L+N+PE with 2 indicator lamps vs 3Ph L1+L2+L3+N+PE with 3 indicator lamps).
  - Dynamic Busbar Physical Dimensions & Rating (e.g. 40A, 63A, 100A, 250A, 600A Cu with WxT mm).
  - Dynamic instrumentation: AC-SPD, Power Analyzer (kWh), Earth Fault Relay (EFR) scaling with capacity.
  - Complete CAD Title Block (Designed By, Title, Client, Scale, Date, Drawn By, Ref, Location).
  - 100% Single Source of Truth synchronization with unified engineering dataset.

Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
"""
from typing import Dict, Any, Optional, List, Tuple
import html
import io
import math

from reportlab.lib.pagesizes import landscape, A3, A4
from reportlab.lib import colors
from reportlab.graphics.shapes import (
    Drawing, Rect, Line, Circle, String, Group, Polygon
)
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas


# ===========================================================================
# REUSABLE CAD DRAWING & LABEL HELPER FUNCTIONS
# ===========================================================================

def draw_connection_label(x: float, y: float, text: str, font_size: float = 9.5,
                          font_weight: str = "bold", color: str = "#000000",
                          align: str = "middle", background: bool = True,
                          pad_x: float = 5.0, pad_y: float = 2.5) -> str:
    """
    Renders an inline conductor or cable label with an optional white cutout rectangle
    behind the text so electrical lines do not intersect or obscure the text.
    """
    escaped = html.escape(str(text))
    # Approximate character width ~ 0.58 * font_size
    w_est = max(12.0, len(text) * font_size * 0.58 + (pad_x * 2))
    h_est = font_size + (pad_y * 2)

    if align == "middle":
        bx = x - (w_est / 2.0)
    elif align == "end":
        bx = x - w_est
    else:
        bx = x - 2.0

    by = y - font_size + 1.5
    out = []
    if background:
        out.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{w_est:.1f}" height="{h_est:.1f}" '
            f'fill="#ffffff" fill-opacity="0.96" stroke="none"/>'
        )
    out.append(
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{font_size}" font-weight="{font_weight}" '
        f'fill="{color}" text-anchor="{align}">{escaped}</text>'
    )
    return "\n".join(out)


def draw_multiline_label(x: float, y: float, lines: List[str], font_size: float = 10.0,
                         line_height: float = 13.5, color: str = "#000000",
                         font_weight: str = "normal", align: str = "start",
                         background: bool = False, pad: float = 4.0) -> str:
    """
    Renders multiple lines of text with consistent line height and optional background mask.
    """
    valid_lines = [str(l) for l in lines if l]
    if not valid_lines:
        return ""
    out = []
    if background:
        max_len = max(len(l) for l in valid_lines)
        w_est = max_len * font_size * 0.58 + (pad * 2)
        h_est = (len(valid_lines) * line_height) + (pad * 2)
        bx = x - (w_est / 2.0) if align == "middle" else (x - w_est if align == "end" else x - 2.0)
        by = y - font_size + 1.0
        out.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{w_est:.1f}" height="{h_est:.1f}" '
            f'fill="#ffffff" fill-opacity="0.96" stroke="none"/>'
        )
    for i, line in enumerate(valid_lines):
        ly = y + (i * line_height)
        out.append(
            f'<text x="{x:.1f}" y="{ly:.1f}" font-size="{font_size}" font-weight="{font_weight}" '
            f'fill="{color}" text-anchor="{align}">{html.escape(line)}</text>'
        )
    return "\n".join(out)


def draw_component_label(x: float, y: float, name: str, spec: Optional[str] = None,
                         font_size: float = 11.0, spec_size: float = 9.0,
                         color: str = "#000000", align: str = "middle",
                         background: bool = True) -> str:
    """
    Renders component name and subtitle spec with clean vertical stacking and background mask.
    """
    lines = [name]
    if spec:
        lines.append(spec)
    out = []
    w_est = max(len(l) for l in lines) * font_size * 0.58 + 10.0
    h_est = font_size + (spec_size + 4.0 if spec else 0.0) + 4.0
    bx = x - (w_est / 2.0) if align == "middle" else (x - w_est if align == "end" else x - 2.0)
    by = y - font_size + 1.5

    if background:
        out.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{w_est:.1f}" height="{h_est:.1f}" '
            f'fill="#ffffff" fill-opacity="0.96" stroke="none"/>'
        )
    out.append(
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{font_size}" font-weight="bold" '
        f'fill="{color}" text-anchor="{align}">{html.escape(name)}</text>'
    )
    if spec:
        out.append(
            f'<text x="{x:.1f}" y="{y + spec_size + 3.0:.1f}" font-size="{spec_size}" '
            f'fill="#334155" text-anchor="{align}">{html.escape(spec)}</text>'
        )
    return "\n".join(out)


def draw_value_label(x: float, y: float, label: str, value: str, unit: str = "",
                     font_size: float = 10.0, align: str = "start") -> str:
    """
    Renders key-value parameter pair e.g. 'Busbar: 100A Cu'.
    """
    val_str = f"{value} {unit}".strip()
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{font_size}" fill="#334155" text-anchor="{align}">'
        f'<tspan font-weight="bold" fill="#000000">{html.escape(label)}: </tspan>'
        f'{html.escape(val_str)}</text>'
    )


# ===========================================================================
# TOPOLOGY 1: VERTICAL SINGLE-INVERTER SLD GENERATOR
# Conforms to 5KW SINGLE LINE DIiagram 5kw 635wp.pdf & 20kW single line diagram
# ===========================================================================

def _generate_vertical_single_inverter_svg(sld: dict) -> str:
    tb = sld.get("title_block", {})
    meta = sld.get("system_meta", {})
    inverters = sld.get("inverters", [])
    busbar = sld.get("busbar", {})
    main_sw = sld.get("main_switchgear", {})
    earthing = sld.get("earthing", {})

    inv = inverters[0] if inverters else {}
    grid_phases = int(meta.get("grid_phases", 1))
    voltage_v = float(meta.get("grid_voltage_v", 230.0))
    cap_kw = float(meta.get("capacity_kw", inv.get("capacity_kw", 5.0)))
    dc_kwp = float(meta.get("dc_kwp", round(cap_kw * 1.25, 2)))
    num_strings = max(int(inv.get("strings_count", 2)), 1)
    panels_per_str = int(inv.get("panels_per_string", 4))
    total_panels = int(meta.get("total_modules", num_strings * panels_per_str))
    mod_wp = float(inv.get("module_wp", 635.0))

    width = 1400
    height = 980
    margin_x = 35
    margin_y = 35
    inner_w = width - (2 * margin_x)
    inner_h = height - (2 * margin_y)
    tb_h = 112
    tb_y = height - margin_y - tb_h

    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" height="100%" style="background-color: #ffffff; font-family: \'Segoe UI\', Arial, Helvetica, sans-serif;">'
    )

    # CAD Watermark
    svg.append(f'''
    <g transform="rotate(-24 {width/2} {height/2})" pointer-events="none">
        <text x="120" y="{height/2}" fill="#0f172a" opacity="0.03" font-size="40" font-weight="bold" letter-spacing="6">
            SOLAR PV ENGINEERING SUITE — ENG. AASHIR © 2026
        </text>
    </g>
    ''')

    # Outer CAD Double Border
    svg.append(f'<rect x="{margin_x}" y="{margin_y}" width="{inner_w}" height="{inner_h}" fill="none" stroke="#000000" stroke-width="2"/>')
    svg.append(f'<rect x="{margin_x+5}" y="{margin_y+5}" width="{inner_w-10}" height="{inner_h-10}" fill="none" stroke="#000000" stroke-width="0.75"/>')

    # -------------------------------------------------------------
    # TOP SECTION: Load, CEB Meter, Bus Bar
    # -------------------------------------------------------------
    # Load Box (Left)
    load_x = 240
    load_y = 70
    svg.append(f'''
    <rect x="{load_x}" y="{load_y}" width="70" height="42" fill="#ffffff" stroke="#000000" stroke-width="1.8"/>
    <text x="{load_x+35}" y="{load_y+26}" font-size="12" font-weight="bold" fill="#000000" text-anchor="middle">Load</text>
    ''')

    # CEB Meter Box (Center)
    meter_x = 480
    meter_y = 65
    svg.append(f'''
    <rect x="{meter_x}" y="{meter_y}" width="90" height="48" fill="#ffffff" stroke="#000000" stroke-width="2"/>
    <text x="{meter_x+45}" y="{meter_y+25}" font-size="12" font-weight="bold" fill="#000000" text-anchor="middle">CEB Meter</text>
    <text x="{meter_x+45}" y="{meter_y+40}" font-size="9" fill="#475569" text-anchor="middle">Bidirectional</text>
    ''')

    # Bus Bar Box (Center)
    bb_x = 425
    bb_y = 150
    bb_w = 200
    bb_h = 32
    bb_rating_label = busbar.get("label", f"{busbar.get('rating_a', 40)} A Bus Bar Cu")
    bb_dim = busbar.get("dimension", "25mm*3mm")
    svg.append(f'''
    <rect x="{bb_x}" y="{bb_y}" width="{bb_w}" height="{bb_h}" fill="#f8fafc" stroke="#000000" stroke-width="2"/>
    <text x="{bb_x + bb_w/2}" y="{bb_y + 15}" font-size="11" font-weight="bold" fill="#000000" text-anchor="middle">Bus Bar — {html.escape(bb_rating_label)}</text>
    <text x="{bb_x + bb_w/2}" y="{bb_y + 27}" font-size="8.5" fill="#475569" text-anchor="middle">Phase Config: {"3Ph (L1, L2, L3, N, PE)" if grid_phases == 3 else "1Ph (L + N + PE)"} | Size: {html.escape(bb_dim)}</text>
    ''')

    # Conductor from Load to Bus Bar
    svg.append(f'<line x1="{load_x+35}" y1="{load_y+42}" x2="{load_x+35}" y2="{bb_y+16}" stroke="#000000" stroke-width="2"/>')
    svg.append(f'<line x1="{load_x+35}" y1="{bb_y+16}" x2="{bb_x}" y2="{bb_y+16}" stroke="#000000" stroke-width="2"/>')
    load_cable = "4C/10sq.mm/Cu/PVC" if grid_phases == 3 else "6sq.mm"
    svg.append(draw_connection_label(load_x + 75, bb_y + 12, load_cable, font_size=8.5))

    # Conductor from CEB Meter to Bus Bar
    svg.append(f'<line x1="{meter_x+45}" y1="{meter_y+48}" x2="{meter_x+45}" y2="{bb_y}" stroke="#000000" stroke-width="2.2"/>')
    main_cbl_str = main_sw.get("main_cable", "4C 2sqmm/CU/PVC")
    svg.append(draw_connection_label(meter_x + 95, (meter_y + 48 + bb_y) / 2 + 2, main_cbl_str, font_size=8.5, align="start"))

    # Central Inverter Axis X
    cx = meter_x + 45  # 525

    # -------------------------------------------------------------
    # CENTER DOWNSTREAM: Busbar -> AC Isolator -> Breaker -> SPD -> Inverter
    # -------------------------------------------------------------
    inv_top_y = 390
    svg.append(f'<line x1="{cx}" y1="{bb_y+bb_h}" x2="{cx}" y2="{inv_top_y}" stroke="#000000" stroke-width="2.2"/>')

    # AC Isolator (y = 215)
    iso_y = 215
    iso_label = main_sw.get("isolator_spec", "40A 2P AC Isolator" if grid_phases == 1 else "40A 4P AC Isolator")
    svg.append(f'''
    <!-- AC Isolator switch symbol -->
    <circle cx="{cx}" cy="{iso_y-10}" r="3" fill="#000000"/>
    <line x1="{cx}" y1="{iso_y-10}" x2="{cx+15}" y2="{iso_y+10}" stroke="#000000" stroke-width="2.2"/>
    <circle cx="{cx}" cy="{iso_y+14}" r="3" fill="#000000"/>
    ''')
    svg.append(draw_component_label(cx + 80, iso_y + 4, iso_label, font_size=10, align="start"))

    # AC Circuit Breaker (y = 265)
    mcb_y = 265
    inv_brk_spec = inv.get("ac_breaker", main_sw.get("breaker_spec", "40 A 2P MCB"))
    svg.append(f'''
    <!-- Breaker cross X symbol -->
    <line x1="{cx-9}" y1="{mcb_y-9}" x2="{cx+9}" y2="{mcb_y+9}" stroke="#000000" stroke-width="2.2"/>
    <line x1="{cx-9}" y1="{mcb_y+9}" x2="{cx+9}" y2="{mcb_y-9}" stroke="#000000" stroke-width="2.2"/>
    ''')
    svg.append(draw_component_label(cx - 20, mcb_y + 4, inv_brk_spec, font_size=10, align="end"))

    # AC SPD branch (y = 315)
    spd_y = 315
    svg.append(f'''
    <!-- AC SPD tap off main AC line -->
    <line x1="{cx}" y1="{spd_y}" x2="{cx+80}" y2="{spd_y}" stroke="#000000" stroke-width="1.8"/>
    <circle cx="{cx}" cy="{spd_y}" r="2.5" fill="#000000"/>
    <!-- AC SPD Box -->
    <rect x="{cx+80}" y="{spd_y-15}" width="65" height="30" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>
    <text x="{cx+112}" y="{spd_y-2}" font-size="9" font-weight="bold" fill="#000000" text-anchor="middle">AC SPD</text>
    <text x="{cx+112}" y="{spd_y+10}" font-size="8" fill="#475569" text-anchor="middle">20kA / 40kA</text>
    <!-- Earth from AC SPD -->
    <line x1="{cx+112}" y1="{spd_y+15}" x2="{cx+112}" y2="{spd_y+32}" stroke="#000000" stroke-width="1.5"/>
    <line x1="{cx+102}" y1="{spd_y+32}" x2="{cx+122}" y2="{spd_y+32}" stroke="#000000" stroke-width="2"/>
    <line x1="{cx+105}" y1="{spd_y+35}" x2="{cx+119}" y2="{spd_y+35}" stroke="#000000" stroke-width="1.5"/>
    <line x1="{cx+108}" y1="{spd_y+38}" x2="{cx+116}" y2="{spd_y+38}" stroke="#000000" stroke-width="1"/>
    ''')

    # Main Inverter AC Cable Callout (y = 360)
    ac_cable_label = inv.get("ac_cable", main_sw.get("main_cable", "2C/6sq.mm/Cu/PVC"))
    svg.append(f'''
    <ellipse cx="{cx}" cy="360" rx="14" ry="7" fill="#ffffff" stroke="#000000" stroke-width="1.2"/>
    <line x1="{cx-8}" y1="368" x2="{cx+8}" y2="352" stroke="#000000" stroke-width="1.5"/>
    ''')
    svg.append(draw_connection_label(cx - 20, 364, ac_cable_label, font_size=9.5, align="end"))

    # Inverter Box (Center)
    inv_w = 80
    inv_h = 75
    inv_box_x = cx - inv_w / 2.0
    inv_box_y = inv_top_y
    inv_label = inv.get("label", f"{cap_kw:.0f}kW Inverter")
    svg.append(f'''
    <!-- Inverter box with diagonal partition -->
    <rect x="{inv_box_x}" y="{inv_box_y}" width="{inv_w}" height="{inv_h}" fill="#ffffff" stroke="#000000" stroke-width="2"/>
    <line x1="{inv_box_x}" y1="{inv_box_y}" x2="{inv_box_x+inv_w}" y2="{inv_box_y+inv_h}" stroke="#000000" stroke-width="1.8"/>
    <text x="{inv_box_x+14}" y="{inv_box_y+32}" font-size="16" font-weight="bold" fill="#000000">~</text>
    <text x="{inv_box_x+inv_w-26}" y="{inv_box_y+inv_h-14}" font-size="16" font-weight="bold" fill="#000000">=</text>
    ''')
    svg.append(draw_component_label(inv_box_x + inv_w + 10, inv_box_y + 35, inv_label, spec=f"{inv.get('model', 'Sunways')}", font_size=12, align="start"))

    # Inverter Chassis Earthing (Right of inverter)
    pe_cable = inv.get("chassis_earth", "6 mm sq Earth")
    svg.append(f'''
    <line x1="{inv_box_x+inv_w}" y1="{inv_box_y+inv_h/2}" x2="{inv_box_x+inv_w+45}" y2="{inv_box_y+inv_h/2}" stroke="#000000" stroke-width="1.5"/>
    <line x1="{inv_box_x+inv_w+45}" y1="{inv_box_y+inv_h/2}" x2="{inv_box_x+inv_w+45}" y2="{inv_box_y+inv_h/2+18}" stroke="#000000" stroke-width="1.5"/>
    <line x1="{inv_box_x+inv_w+35}" y1="{inv_box_y+inv_h/2+18}" x2="{inv_box_x+inv_w+55}" y2="{inv_box_y+inv_h/2+18}" stroke="#000000" stroke-width="2"/>
    <line x1="{inv_box_x+inv_w+38}" y1="{inv_box_y+inv_h/2+21}" x2="{inv_box_x+inv_w+52}" y2="{inv_box_y+inv_h/2+21}" stroke="#000000" stroke-width="1.5"/>
    <line x1="{inv_box_x+inv_w+41}" y1="{inv_box_y+inv_h/2+24}" x2="{inv_box_x+inv_w+49}" y2="{inv_box_y+inv_h/2+24}" stroke="#000000" stroke-width="1"/>
    ''')
    svg.append(draw_connection_label(inv_box_x + inv_w + 60, inv_box_y + inv_h/2 + 22, pe_cable, font_size=8.5, align="start"))

    # -------------------------------------------------------------
    # BOTTOM DC SECTION: Inverter -> Strings -> SPDs -> Modules
    # -------------------------------------------------------------
    inv_bot_y = inv_box_y + inv_h
    dc_bus_y = 500

    # Determine string X positions
    if num_strings == 1:
        str_xs = [cx]
    elif num_strings == 2:
        str_xs = [cx - 160, cx + 160]
    elif num_strings == 3:
        str_xs = [cx - 240, cx, cx + 240]
    else:
        avail_w = 720.0 if num_strings > 4 else 600.0
        start_x = cx - (avail_w / 2.0)
        spacing = avail_w / (num_strings - 1)
        str_xs = [start_x + i * spacing for i in range(num_strings)]

    # Trunk from inverter bottom to horizontal DC branch line
    svg.append(f'<line x1="{cx}" y1="{inv_bot_y}" x2="{cx}" y2="{dc_bus_y}" stroke="#000000" stroke-width="2.2"/>')
    svg.append(f'<line x1="{min(str_xs)}" y1="{dc_bus_y}" x2="{max(str_xs)}" y2="{dc_bus_y}" stroke="#000000" stroke-width="2"/>')

    dc_cable_label = inv.get("dc_cable", "2 x 1C/4sq.mm/Cu/PVC")
    dc_iso_label = inv.get("dc_isolator", "2P 1000V DC Isolator")
    dc_spd_label = inv.get("dc_spd", "DC SPD-40kA")

    is_crowded = (num_strings > 4)
    for s_idx, sx in enumerate(str_xs):
        # Vertical drop from DC bus
        svg.append(f'<line x1="{sx}" y1="{dc_bus_y}" x2="{sx}" y2="{tb_y - 85}" stroke="#000000" stroke-width="2"/>')

        # DC Isolator at y = 540
        sw_y = 540
        svg.append(f'''
        <circle cx="{sx}" cy="{sw_y-8}" r="2.5" fill="#000000"/>
        <line x1="{sx}" y1="{sw_y-8}" x2="{sx+12}" y2="{sw_y+8}" stroke="#000000" stroke-width="2"/>
        <circle cx="{sx}" cy="{sw_y+10}" r="2.5" fill="#000000"/>
        ''')
        if not is_crowded:
            svg.append(draw_component_label(sx + 18, sw_y + 4, dc_iso_label, font_size=8.5, align="start"))
        elif s_idx == 0:
            svg.append(draw_component_label(sx + 16, sw_y + 4, f"{dc_iso_label} (Typ.)", font_size=8.0, align="start"))

        # DC Cable Callout at y = 585
        svg.append(f'''
        <ellipse cx="{sx}" cy="585" rx="12" ry="6" fill="#ffffff" stroke="#000000" stroke-width="1.2"/>
        <line x1="{sx-7}" y1="592" x2="{sx+7}" y2="578" stroke="#000000" stroke-width="1.5"/>
        ''')
        if not is_crowded:
            svg.append(draw_connection_label(sx + 16, 589, dc_cable_label, font_size=8.5, align="start"))
        elif s_idx == 0:
            svg.append(draw_connection_label(sx + 16, 589, f"{dc_cable_label} (Typ.)", font_size=8.0, align="start"))

        # DC SPD Branch at y = 625
        spd_sy = 625
        svg.append(f'''
        <line x1="{sx}" y1="{spd_sy}" x2="{sx+45}" y2="{spd_sy}" stroke="#000000" stroke-width="1.5"/>
        <circle cx="{sx}" cy="{spd_sy}" r="2" fill="#000000"/>
        <rect x="{sx+45}" y="{spd_sy-12}" width="48" height="24" fill="#ffffff" stroke="#000000" stroke-width="1.2"/>
        <text x="{sx+69}" y="{spd_sy+4}" font-size="8" font-weight="bold" fill="#000000" text-anchor="middle">DC-SPD</text>
        <line x1="{sx+69}" y1="{spd_sy+12}" x2="{sx+69}" y2="{spd_sy+24}" stroke="#000000" stroke-width="1.2"/>
        <line x1="{sx+61}" y1="{spd_sy+24}" x2="{sx+77}" y2="{spd_sy+24}" stroke="#000000" stroke-width="1.8"/>
        <line x1="{sx+64}" y1="{spd_sy+27}" x2="{sx+74}" y2="{spd_sy+27}" stroke="#000000" stroke-width="1.2"/>
        <line x1="{sx+66}" y1="{spd_sy+30}" x2="{sx+72}" y2="{spd_sy+30}" stroke="#000000" stroke-width="0.8"/>
        <text x="{sx+82}" y="{spd_sy+26}" font-size="7.5" fill="#475569">40kA</text>
        ''')

        # PV Module Symbol at y = 680
        pv_y = 680
        mod_w = 42
        mod_h = 28
        svg.append(f'''
        <!-- PV Module rectangle with diagonal cross -->
        <rect x="{sx-mod_w/2}" y="{pv_y}" width="{mod_w}" height="{mod_h}" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>
        <line x1="{sx-mod_w/2}" y1="{pv_y}" x2="{sx+mod_w/2}" y2="{pv_y+mod_h}" stroke="#000000" stroke-width="1"/>
        <line x1="{sx-mod_w/2}" y1="{pv_y+mod_h}" x2="{sx+mod_w/2}" y2="{pv_y}" stroke="#000000" stroke-width="1"/>
        ''')
        # Panel count per string
        svg.append(f'<text x="{sx}" y="{pv_y+mod_h+16}" font-size="11" font-weight="bold" fill="#000000" text-anchor="middle">{panels_per_str:02d}</text>')
        # Module symbol lower box
        svg.append(f'''
        <rect x="{sx-mod_w/2}" y="{pv_y+mod_h+22}" width="{mod_w}" height="{mod_h}" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>
        <line x1="{sx-mod_w/2}" y1="{pv_y+mod_h+22}" x2="{sx+mod_w/2}" y2="{pv_y+2*mod_h+22}" stroke="#000000" stroke-width="1"/>
        <line x1="{sx-mod_w/2}" y1="{pv_y+2*mod_h+22}" x2="{sx+mod_w/2}" y2="{pv_y+mod_h+22}" stroke="#000000" stroke-width="1"/>
        ''')
        # Module rating label
        if not is_crowded or s_idx == 0:
            svg.append(f'<text x="{sx}" y="{pv_y+2*mod_h+38}" font-size="9" font-weight="bold" fill="#000000" text-anchor="middle">({mod_wp:.0f}W Solar Panel)</text>')

    if is_crowded:
        arr_mid_x = (str_xs[0] + str_xs[-1]) / 2.0
        svg.append(f'<text x="{arr_mid_x}" y="{pv_y+2*mod_h+54}" font-size="10.5" font-weight="bold" fill="#0f172a" text-anchor="middle">All {num_strings} Strings: {panels_per_str} Panels Each ({mod_wp:.0f}W)</text>')

    # -------------------------------------------------------------
    # RIGHT SIDE: General Details & Eastwestsolar Branding
    # -------------------------------------------------------------
    dt_x = 960
    dt_y = 65
    dt_w = 340
    dt_h = 285
    svg.append(f'''
    <rect x="{dt_x}" y="{dt_y}" width="{dt_w}" height="{dt_h}" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>
    <rect x="{dt_x}" y="{dt_y}" width="{dt_w}" height="28" fill="#f1f5f9" stroke="#000000" stroke-width="1.5"/>
    <text x="{dt_x+15}" y="{dt_y+19}" font-size="13" font-weight="bold" fill="#0f172a">General Details</text>
    ''')

    details_rows = [
        ("Scheme", sld.get("project_scheme", "Net Accounting")),
        ("Total DC kW", f"{dc_kwp:.2f} kWp"),
        ("Total AC kW", f"{cap_kw:.1f} kW"),
        ("Total No. PV Modules", f"{total_panels:02d} Nos. ({mod_wp:.0f} Wp)"),
        ("Strings Configuration", f"{num_strings:02d} Strings, Each 1 x {panels_per_str} modules"),
        ("Inverter Output", f"{cap_kw:.1f} kW ({voltage_v:.0f}V, {grid_phases}-Phase)"),
        ("Main Switchgear Breaker", main_sw.get("breaker_spec", "40A 4P MCB")),
        ("Main Export Cable", main_sw.get("main_cable", "4C 16sqmm/CU/PVC")),
        ("Main Earth Conductor", earthing.get("main_earth_cable", "16 mm sq Earth Cable")),
        ("Utility Interconnection", f"CEB / LECO {voltage_v:.0f}V Grid")
    ]
    r_start_y = dt_y + 46
    for i, (k, v) in enumerate(details_rows):
        ry = r_start_y + (i * 23)
        svg.append(f'<text x="{dt_x+15}" y="{ry}" font-size="10" font-weight="bold" fill="#334155">{k} :</text>')
        svg.append(f'<text x="{dt_x+160}" y="{ry}" font-size="10" fill="#0f172a">{html.escape(v)}</text>')
        if i < len(details_rows) - 1:
            svg.append(f'<line x1="{dt_x+10}" y1="{ry+6}" x2="{dt_x+dt_w-10}" y2="{ry+6}" stroke="#e2e8f0" stroke-width="0.8"/>')

    # Eastwestsolar Corporate Branding (Right Side below table)
    br_x = 1000
    br_y = 480
    svg.append(f'''
    <!-- Eastwestsolar Stylized Branding -->
    <g transform="translate({br_x}, {br_y})">
        <!-- 4-Leaf Logo -->
        <rect x="0" y="0" width="22" height="22" rx="4" fill="#f59e0b"/>
        <rect x="26" y="0" width="22" height="22" rx="4" fill="#10b981"/>
        <rect x="0" y="26" width="22" height="22" rx="4" fill="#0284c7"/>
        <rect x="26" y="26" width="22" height="22" rx="4" fill="#f97316"/>
        <text x="56" y="32" font-size="20" font-weight="bold" fill="#1e3a8a" letter-spacing="1">Eastwestsolar</text>
        <text x="56" y="50" font-size="10.5" fill="#475569">41 Ananda Mawatha, Colombo 01000.</text>
        <text x="56" y="65" font-size="10.5" fill="#475569">03 Main Street, Nintavur.</text>
        <text x="56" y="80" font-size="9" fill="#0284c7" font-weight="bold">www.eastwestsolar.lk</text>
    </g>
    ''')

    # -------------------------------------------------------------
    # BOTTOM CAD TITLE BLOCK (Standard 4-column format)
    # -------------------------------------------------------------
    svg.append(f'<rect x="{margin_x+5}" y="{tb_y}" width="{inner_w-10}" height="{tb_h}" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>')

    col1_w = 280
    col2_w = 340
    col3_w = 280
    col4_w = (inner_w - 10) - col1_w - col2_w - col3_w

    x_c1 = margin_x + 5
    x_c2 = x_c1 + col1_w
    x_c3 = x_c2 + col2_w
    x_c4 = x_c3 + col3_w

    svg.append(f'<line x1="{x_c2}" y1="{tb_y}" x2="{x_c2}" y2="{tb_y+tb_h}" stroke="#000000" stroke-width="1.2"/>')
    svg.append(f'<line x1="{x_c3}" y1="{tb_y}" x2="{x_c3}" y2="{tb_y+tb_h}" stroke="#000000" stroke-width="1.2"/>')
    svg.append(f'<line x1="{x_c4}" y1="{tb_y}" x2="{x_c4}" y2="{tb_y+tb_h}" stroke="#000000" stroke-width="1.2"/>')

    # Col 1: Designed By
    svg.append(f'<text x="{x_c1+12}" y="{tb_y+20}" font-size="10.5" fill="#475569">Designed By :</text>')
    svg.append(f'<text x="{x_c1+16}" y="{tb_y+54}" font-size="15" font-weight="bold" fill="#000000">{html.escape(tb.get("designed_by", "East West Solar PVT (Ltd)"))}</text>')
    svg.append(f'<text x="{x_c1+16}" y="{tb_y+75}" font-size="10.5" fill="#334155">Lead Engineer: {html.escape(tb.get("drawn_by", "Eng. Aashir"))} © 2026</text>')
    svg.append(f'<text x="{x_c1+16}" y="{tb_y+92}" font-size="9" fill="#64748b">Standards: BS 7671 (Kelani) / IEC 60364-7-712</text>')

    # Col 2: Title
    svg.append(f'<text x="{x_c2+12}" y="{tb_y+20}" font-size="10.5" fill="#475569">TiTle :</text>')
    title_text = tb.get("title", f"{cap_kw:.0f} Kw on-Grid Solar System")
    svg.append(f'<text x="{x_c2+16}" y="{tb_y+50}" font-size="14" font-weight="bold" fill="#000000">{html.escape(title_text)}</text>')
    svg.append(f'<text x="{x_c2+16}" y="{tb_y+72}" font-size="10.5" fill="#334155">Grid Interconnection: {voltage_v:.0f}V ({grid_phases}-Phase 50Hz)</text>')
    svg.append(f'<text x="{x_c2+16}" y="{tb_y+90}" font-size="9.5" fill="#64748b">Installed DC: {dc_kwp:.2f} kWp | Oversizing: {meta.get("ratio", 1.25):.2f}</text>')

    # Col 3: Client
    svg.append(f'<text x="{x_c3+12}" y="{tb_y+20}" font-size="10.5" fill="#475569">Clint :</text>')
    svg.append(f'<text x="{x_c3+16}" y="{tb_y+52}" font-size="14" font-weight="bold" fill="#000000">{html.escape(tb.get("client", "Valued Client"))}</text>')
    svg.append(f'<text x="{x_c3+16}" y="{tb_y+74}" font-size="10" fill="#475569">{html.escape(tb.get("location", "Colombo"))}</text>')

    # Col 4: Meta table
    r_h = tb_h / 4.0
    for r in range(1, 4):
        svg.append(f'<line x1="{x_c4}" y1="{tb_y + r*r_h}" x2="{x_c4+col4_w}" y2="{tb_y + r*r_h}" stroke="#000000" stroke-width="0.8"/>')
    mid_x = x_c4 + (col4_w * 0.45)
    svg.append(f'<line x1="{mid_x}" y1="{tb_y}" x2="{mid_x}" y2="{tb_y + 2*r_h}" stroke="#000000" stroke-width="0.8"/>')

    svg.append(f'<text x="{x_c4+8}" y="{tb_y+18}" font-size="9.5" fill="#333333">Scale : {html.escape(tb.get("scale", "1:50"))}</text>')
    svg.append(f'<text x="{mid_x+8}" y="{tb_y+18}" font-size="9.5" font-weight="bold" fill="#000000">Drawn By : {html.escape(tb.get("drawn_by", "Eng. Aashir"))}</text>')
    svg.append(f'<text x="{x_c4+8}" y="{tb_y+r_h+18}" font-size="9.5" fill="#333333">Date : {html.escape(tb.get("date", "19.08.2026"))}</text>')
    svg.append(f'<text x="{mid_x+8}" y="{tb_y+r_h+18}" font-size="9.5" fill="#333333">Ref : {html.escape(tb.get("ref", "EW/SLD/01"))}</text>')
    svg.append(f'<text x="{x_c4+8}" y="{tb_y+2*r_h+18}" font-size="10" font-weight="bold" fill="#000000">Drawing Title : Single Line Diagram</text>')
    svg.append(f'<text x="{x_c4+8}" y="{tb_y+3*r_h+18}" font-size="9.5" fill="#333333">Location : {html.escape(tb.get("location", "Colombo"))}</text>')

    svg.append('</svg>')
    return "\n".join(svg)


# ===========================================================================
# TOPOLOGY 2: HORIZONTAL MULTI-INVERTER COLLECTOR BUSBAR SLD GENERATOR
# Conforms to 13KW azr.pdf & 260 kw_AutoDWG.pdf
# ===========================================================================

def _generate_horizontal_multi_inverter_svg(sld: dict) -> str:
    tb = sld.get("title_block", {})
    meta = sld.get("system_meta", {})
    inverters = sld.get("inverters", [])
    busbar = sld.get("busbar", {})
    main_sw = sld.get("main_switchgear", {})
    earthing = sld.get("earthing", {})

    inv_count = max(len(inverters), 1)
    cap_kw = float(meta.get("capacity_kw", 13.0))
    dc_kwp = float(meta.get("dc_kwp", round(cap_kw * 1.25, 2)))
    grid_phases = int(meta.get("grid_phases", 3))
    voltage_v = float(meta.get("grid_voltage_v", 400.0))

    width = 1680
    height = max(1000, 720 + (inv_count * 220))
    tb_h = 120
    tb_y = height - tb_h - 30

    margin_x = 35
    margin_y = 35
    inner_w = width - (2 * margin_x)
    inner_h = height - (2 * margin_y)

    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" height="100%" style="background-color: #ffffff; font-family: \'Segoe UI\', Arial, Helvetica, sans-serif;">'
    )

    # Watermark
    svg.append(f'''
    <g transform="rotate(-24 {width/2} {height/2})" pointer-events="none">
        <text x="120" y="{height/2}" fill="#0f172a" opacity="0.03" font-size="44" font-weight="bold" letter-spacing="6">
            SOLAR PV ENGINEERING SUITE — ENG. AASHIR © 2026
        </text>
    </g>
    ''')

    # Outer CAD Double Border
    svg.append(f'<rect x="{margin_x}" y="{margin_y}" width="{inner_w}" height="{inner_h}" fill="none" stroke="#000000" stroke-width="2"/>')
    svg.append(f'<rect x="{margin_x+5}" y="{margin_y+5}" width="{inner_w-10}" height="{inner_h-10}" fill="none" stroke="#000000" stroke-width="0.75"/>')

    # -------------------------------------------------------------
    # 1. Earth Pit & Green Conductor Riser (Far Left)
    # -------------------------------------------------------------
    earth_pit_x = margin_x + 35
    earth_pit_y = tb_y - 45
    svg.append(f'''
    <!-- Earth Pit Symbol -->
    <rect x="{earth_pit_x}" y="{earth_pit_y}" width="24" height="24" fill="#ffffff" stroke="#000000" stroke-width="1.8"/>
    <line x1="{earth_pit_x+4}" y1="{earth_pit_y+18}" x2="{earth_pit_x+20}" y2="{earth_pit_y+18}" stroke="#000000" stroke-width="1.5"/>
    <line x1="{earth_pit_x+12}" y1="{earth_pit_y}" x2="{earth_pit_x+12}" y2="{earth_pit_y+18}" stroke="#000000" stroke-width="1.8"/>
    <text x="{earth_pit_x+34}" y="{earth_pit_y+16}" font-size="11" font-weight="bold" fill="#000000">Earth pit</text>
    ''')

    earth_riser_x = earth_pit_x + 12
    top_y = margin_y + 90
    main_earth_str = earthing.get("main_earth_cable", "16 mm sq Earth Cable")
    svg.append(f'<line x1="{earth_riser_x}" y1="{earth_pit_y}" x2="{earth_riser_x}" y2="{top_y}" stroke="#16a34a" stroke-width="2.5"/>')
    svg.append(f'<text x="{earth_riser_x+10}" y="{(top_y + earth_pit_y)/2}" font-size="10.5" font-weight="bold" fill="#16a34a" transform="rotate(-90 {earth_riser_x+10} {(top_y + earth_pit_y)/2})">{html.escape(main_earth_str)}</text>')

    # -------------------------------------------------------------
    # 2. Central AC Collector Busbar
    # -------------------------------------------------------------
    busbar_x = 980
    busbar_top_y = margin_y + 70
    busbar_bottom_y = tb_y - 45

    # Heavy Busbar Conductor Line
    svg.append(f'<line x1="{busbar_x}" y1="{busbar_top_y}" x2="{busbar_x}" y2="{busbar_bottom_y}" stroke="#1e293b" stroke-width="6"/>')

    # Busbar Rating & Dimensions Label
    bb_label = busbar.get("label", f"{busbar.get('rating_a', 100)} A Bus Bar Cu")
    bb_dim = busbar.get("dimension", "30mm*5mm")
    svg.append(f'<text x="{busbar_x + 18}" y="{busbar_top_y + 24}" font-size="15" font-weight="bold" fill="#000000">{html.escape(bb_label)}</text>')
    if bb_dim:
        svg.append(f'<text x="{busbar_x + 18}" y="{busbar_top_y + 42}" font-size="11" fill="#475569">({html.escape(bb_dim)})</text>')

    # Dynamic Busbar Phase Indicator Lamps
    ind_y = busbar_bottom_y - 110
    if grid_phases == 1:
        lamps = [("#dc2626", "L"), ("#2563eb", "N")]
        for i, (col, lbl) in enumerate(lamps):
            cy = ind_y + (i * 24)
            svg.append(f'<circle cx="{busbar_x}" cy="{cy}" r="6.5" fill="{col}" stroke="#000000" stroke-width="1.5"/>')
            svg.append(f'<text x="{busbar_x - 18}" y="{cy + 4}" font-size="8.5" font-weight="bold" fill="#333333">{lbl}</text>')
        svg.append(f'<text x="{busbar_x - 70}" y="{ind_y + 26}" font-size="11" font-weight="bold" fill="#000000">Indicators (L,N)</text>')
    else:
        lamps = [("#dc2626", "L1"), ("#eab308", "L2"), ("#2563eb", "L3")]
        for i, (col, lbl) in enumerate(lamps):
            cy = ind_y + (i * 24)
            svg.append(f'<circle cx="{busbar_x}" cy="{cy}" r="6.5" fill="{col}" stroke="#000000" stroke-width="1.5"/>')
            svg.append(f'<text x="{busbar_x - 22}" y="{cy + 4}" font-size="8.5" font-weight="bold" fill="#333333">{lbl}</text>')
        svg.append(f'<text x="{busbar_x - 70}" y="{ind_y + 36}" font-size="11" font-weight="bold" fill="#000000">Indicators</text>')

    # -------------------------------------------------------------
    # 3. Collector Busbar Protection & Instrumentation
    # -------------------------------------------------------------
    spd_y = (busbar_top_y + busbar_bottom_y) / 2.0 + 30
    if cap_kw >= 40.0:
        # Commercial system: Power Analyzer, EFR, and AC SPD with HRC Fuse
        analyzer_y = spd_y - 120
        svg.append(f'''
        <!-- Power Analyzer & EFR -->
        <line x1="{busbar_x}" y1="{analyzer_y}" x2="{busbar_x + 70}" y2="{analyzer_y}" stroke="#000000" stroke-width="1.8"/>
        <circle cx="{busbar_x + 95}" cy="{analyzer_y}" r="22" fill="#ffffff" stroke="#000000" stroke-width="1.8"/>
        <text x="{busbar_x + 85}" y="{analyzer_y + 5}" font-size="12" font-weight="bold" fill="#000000">kWh</text>
        <text x="{busbar_x + 65}" y="{analyzer_y - 30}" font-size="12" font-weight="bold" fill="#000000">Power Analyzer</text>
        
        <!-- EFR Box -->
        <rect x="{busbar_x + 75}" y="{analyzer_y + 32}" width="45" height="24" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>
        <text x="{busbar_x + 87}" y="{analyzer_y + 48}" font-size="11" font-weight="bold" fill="#000000">EFR</text>
        <text x="{busbar_x + 130}" y="{analyzer_y + 42}" font-size="8.5" fill="#333333">EFR current adjustable</text>
        <text x="{busbar_x + 130}" y="{analyzer_y + 54}" font-size="8.5" fill="#333333">should be less than 0.8</text>
        
        <!-- AC SPD 40kA with HRC Fuse -->
        <line x1="{busbar_x}" y1="{spd_y}" x2="{busbar_x + 110}" y2="{spd_y}" stroke="#000000" stroke-width="1.8"/>
        <rect x="{busbar_x + 110}" y="{spd_y - 12}" width="30" height="24" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>
        <text x="{busbar_x + 114}" y="{spd_y + 4}" font-size="8.5" fill="#000000">HRC</text>
        <line x1="{busbar_x + 140}" y1="{spd_y}" x2="{busbar_x + 180}" y2="{spd_y}" stroke="#000000" stroke-width="1.8"/>
        
        <rect x="{busbar_x + 180}" y="{spd_y - 20}" width="50" height="40" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>
        <text x="{busbar_x + 188}" y="{spd_y - 3}" font-size="10" font-weight="bold" fill="#000000">40 kA</text>
        <text x="{busbar_x + 184}" y="{spd_y + 11}" font-size="9" fill="#000000">AC-SPD</text>
        
        <!-- Earth Conductor from SPD -->
        <line x1="{busbar_x + 205}" y1="{spd_y + 20}" x2="{busbar_x + 205}" y2="{spd_y + 42}" stroke="#000000" stroke-width="1.5"/>
        <line x1="{busbar_x + 195}" y1="{spd_y + 42}" x2="{busbar_x + 215}" y2="{spd_y + 42}" stroke="#000000" stroke-width="2"/>
        <line x1="{busbar_x + 198}" y1="{spd_y + 45}" x2="{busbar_x + 212}" y2="{spd_y + 45}" stroke="#000000" stroke-width="1.5"/>
        <line x1="{busbar_x + 201}" y1="{spd_y + 48}" x2="{busbar_x + 209}" y2="{spd_y + 48}" stroke="#000000" stroke-width="1"/>
        <text x="{busbar_x + 224}" y="{spd_y + 44}" font-size="9" fill="#000000">70 mm sq Earth Cable</text>
        ''')
    else:
        # Standard residential/light-commercial (<40 kW, e.g. 13 kW azr.pdf)
        svg.append(f'''
        <!-- AC SPD Branch (matching 13KW azr.pdf) -->
        <line x1="{busbar_x}" y1="{spd_y}" x2="{busbar_x + 80}" y2="{spd_y}" stroke="#000000" stroke-width="1.8"/>
        <circle cx="{busbar_x + 80}" cy="{spd_y}" r="2.5" fill="#000000"/>
        
        <!-- Disconnect Switch symbol -->
        <line x1="{busbar_x + 80}" y1="{spd_y}" x2="{busbar_x + 105}" y2="{spd_y - 12}" stroke="#000000" stroke-width="2"/>
        <circle cx="{busbar_x + 110}" cy="{spd_y}" r="2.5" fill="#000000"/>
        <line x1="{busbar_x + 110}" y1="{spd_y}" x2="{busbar_x + 140}" y2="{spd_y}" stroke="#000000" stroke-width="1.8"/>
        
        <!-- AC SPD Box -->
        <rect x="{busbar_x + 140}" y="{spd_y - 16}" width="75" height="32" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>
        <text x="{busbar_x + 177}" y="{spd_y + 4}" font-size="10" font-weight="bold" fill="#000000" text-anchor="middle">AC SPD-20KA</text>
        
        <!-- Earth Conductor from SPD -->
        <line x1="{busbar_x + 177}" y1="{spd_y + 16}" x2="{busbar_x + 177}" y2="{spd_y + 36}" stroke="#000000" stroke-width="1.5"/>
        <line x1="{busbar_x + 167}" y1="{spd_y + 36}" x2="{busbar_x + 187}" y2="{spd_y + 36}" stroke="#000000" stroke-width="2"/>
        <line x1="{busbar_x + 170}" y1="{spd_y + 39}" x2="{busbar_x + 184}" y2="{spd_y + 39}" stroke="#000000" stroke-width="1.5"/>
        <line x1="{busbar_x + 173}" y1="{spd_y + 42}" x2="{busbar_x + 181}" y2="{spd_y + 42}" stroke="#000000" stroke-width="1"/>
        <text x="{busbar_x + 195}" y="{spd_y + 38}" font-size="9" fill="#000000">6 mm sq Earth</text>
        ''')

    # -------------------------------------------------------------
    # 4. Inverter Units & String Array Generation (Stacked Left)
    # -------------------------------------------------------------
    avail_h = (tb_y - 60) - (margin_y + 80)
    spacing_inv = avail_h / inv_count

    for idx, inv in enumerate(inverters):
        inv_center_y = (margin_y + 110) + (idx * spacing_inv) + 30
        inv_box_x = 490
        inv_box_w = 65
        inv_box_h = 75
        inv_box_y = inv_center_y - 37.5

        # Horizontal earth tap from main vertical earth line to array frames
        svg.append(f'<line x1="{earth_riser_x}" y1="{inv_center_y - 35}" x2="{margin_x + 85}" y2="{inv_center_y - 35}" stroke="#16a34a" stroke-width="1.8"/>')
        svg.append(f'<line x1="{earth_riser_x}" y1="{inv_center_y + 25}" x2="{margin_x + 85}" y2="{inv_center_y + 25}" stroke="#16a34a" stroke-width="1.8"/>')

        # Array String Symbols (2 rows per inverter)
        str_y1 = inv_center_y - 35
        str_y2 = inv_center_y + 25
        p_x = margin_x + 85

        for sy in [str_y1, str_y2]:
            svg.append(f'''
            <rect x="{p_x}" y="{sy-13}" width="38" height="26" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>
            <line x1="{p_x}" y1="{sy-13}" x2="{p_x+38}" y2="{sy+13}" stroke="#000000" stroke-width="1.2"/>
            <line x1="{p_x}" y1="{sy+13}" x2="{p_x+38}" y2="{sy-13}" stroke="#000000" stroke-width="1.2"/>
            ''')

        # Panel count string text
        str_desc = inv.get("string_desc", "Panels")
        mod_wp_val = inv.get("module_wp", 580.0)
        svg.append(draw_multiline_label(p_x + 48, (str_y1 + str_y2)/2 - 8, [str_desc, f"{mod_wp_val:.0f} Wp"], font_size=9.5, font_weight="bold"))

        # DC Protection Box & Cable
        dc_cable_label = inv.get("dc_cable", "2 x 1C/4sq.mm/Cu/PVC")
        sw_x = p_x + 230
        for s_idx, sy in enumerate([str_y1, str_y2]):
            # DC Line from string to switch
            svg.append(f'<line x1="{p_x+38}" y1="{sy}" x2="{sw_x}" y2="{sy}" stroke="#000000" stroke-width="1.8"/>')

            # DC Switch / Disconnect Symbol
            svg.append(f'''
            <circle cx="{sw_x}" cy="{sy}" r="2.5" fill="#000000"/>
            <line x1="{sw_x}" y1="{sy}" x2="{sw_x+14}" y2="{sy-8}" stroke="#000000" stroke-width="2"/>
            <circle cx="{sw_x+18}" cy="{sy}" r="2.5" fill="#000000"/>
            ''')
            # DC Protection Label cleanly above switch
            svg.append(draw_connection_label(sw_x + 9, sy - 14, "SPD (1100Vdc), Isolator (1100Vdc)", font_size=8.0, font_weight="normal"))

            # Line from switch into inverter
            svg.append(f'<line x1="{sw_x+18}" y1="{sy}" x2="{inv_box_x}" y2="{sy}" stroke="#000000" stroke-width="1.8"/>')

        # DC Cable callout cleanly positioned
        svg.append(draw_connection_label(p_x + 130, str_y1 - 10, dc_cable_label, font_size=8.5))

        # Inverter Block: Diagonal split
        svg.append(f'''
        <rect x="{inv_box_x}" y="{inv_box_y}" width="{inv_box_w}" height="{inv_box_h}" fill="#ffffff" stroke="#000000" stroke-width="2"/>
        <line x1="{inv_box_x}" y1="{inv_box_y}" x2="{inv_box_x+inv_box_w}" y2="{inv_box_y+inv_box_h}" stroke="#000000" stroke-width="1.5"/>
        <text x="{inv_box_x+10}" y="{inv_box_y+26}" font-size="13" font-weight="bold" fill="#000000">DC</text>
        <text x="{inv_box_x+inv_box_w-26}" y="{inv_box_y+inv_box_h-12}" font-size="13" font-weight="bold" fill="#000000">AC</text>
        ''')
        # Inverter Title Label (Cleanly above inverter box)
        inv_title = inv.get("label", f"Inverter {idx+1} - {inv.get('capacity_kw', 10):.0f} Kw")
        svg.append(f'<text x="{inv_box_x - 10}" y="{inv_box_y - 12}" font-size="12" font-weight="bold" fill="#000000">{html.escape(inv_title)}</text>')

        # Inverter Chassis Earthing
        pe_str = inv.get("chassis_earth", "6 mm sq Earth")
        svg.append(f'''
        <line x1="{inv_box_x+20}" y1="{inv_box_y+inv_box_h}" x2="{inv_box_x+20}" y2="{inv_box_y+inv_box_h+16}" stroke="#000000" stroke-width="1.5"/>
        <line x1="{inv_box_x+10}" y1="{inv_box_y+inv_box_h+16}" x2="{inv_box_x+30}" y2="{inv_box_y+inv_box_h+16}" stroke="#000000" stroke-width="2"/>
        <line x1="{inv_box_x+13}" y1="{inv_box_y+inv_box_h+19}" x2="{inv_box_x+27}" y2="{inv_box_y+inv_box_h+19}" stroke="#000000" stroke-width="1.5"/>
        <line x1="{inv_box_x+16}" y1="{inv_box_y+inv_box_h+22}" x2="{inv_box_x+24}" y2="{inv_box_y+inv_box_h+22}" stroke="#000000" stroke-width="1"/>
        <text x="{inv_box_x+34}" y="{inv_box_y+inv_box_h+18}" font-size="9" fill="#000000">{html.escape(pe_str)}</text>
        ''')

        # Inverter AC Output Feed Line to Collector Busbar
        ac_y = inv_center_y
        svg.append(f'<line x1="{inv_box_x+inv_box_w}" y1="{ac_y}" x2="{busbar_x}" y2="{ac_y}" stroke="#000000" stroke-width="2"/>')

        # AC Cable Notation on Feed Line (Centered, with white cutout)
        ac_cable_txt = inv.get("ac_cable", "4C/ 10mm sq CU/PVC")
        svg.append(draw_connection_label(inv_box_x + inv_box_w + 90, ac_y - 12, ac_cable_txt, font_size=10, font_weight="bold"))

        # Circuit Breaker 'X' Symbol on AC Feed
        mcb_x = inv_box_x + inv_box_w + 240
        svg.append(f'''
        <line x1="{mcb_x-12}" y1="{ac_y-12}" x2="{mcb_x+12}" y2="{ac_y+12}" stroke="#000000" stroke-width="2.2"/>
        <line x1="{mcb_x-12}" y1="{ac_y+12}" x2="{mcb_x+12}" y2="{ac_y-12}" stroke="#000000" stroke-width="2.2"/>
        ''')
        # Breaker Rating Label (Cleanly below cross)
        ac_brk_txt = inv.get("ac_breaker", "40 A 4P MCB")
        svg.append(draw_component_label(mcb_x, ac_y + 24, ac_brk_txt, font_size=10, align="middle"))

    # -------------------------------------------------------------
    # 5. Main AC Export Switchgear, Main Breaker, Isolator & Grid
    # -------------------------------------------------------------
    main_feed_y = busbar_top_y + 110
    inter_x = 1440

    svg.append(f'<line x1="{busbar_x}" y1="{main_feed_y}" x2="{inter_x}" y2="{main_feed_y}" stroke="#000000" stroke-width="2.5"/>')

    # Current Transformer / Metering Ring
    ct_x = busbar_x + 65
    svg.append(f'<ellipse cx="{ct_x}" cy="{main_feed_y}" rx="14" ry="8" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>')

    # Main Export Cable Callout (Above line)
    main_cable_str = main_sw.get("main_cable", "4C 16sqmm/CU/PVC")
    svg.append(draw_connection_label(ct_x, main_feed_y - 20, main_cable_str, font_size=9.5, font_weight="bold", align="middle"))

    # Main Breaker Symbol ('X' cross)
    mb_x = busbar_x + 200
    svg.append(f'''
    <line x1="{mb_x-12}" y1="{main_feed_y-12}" x2="{mb_x+12}" y2="{main_feed_y+12}" stroke="#000000" stroke-width="2.2"/>
    <line x1="{mb_x-12}" y1="{main_feed_y+12}" x2="{mb_x+12}" y2="{main_feed_y-12}" stroke="#000000" stroke-width="2.2"/>
    ''')
    # Breaker rating label BELOW line to avoid collision with cable label above
    mb_spec = main_sw.get("breaker_spec", "63 A / 4P MCCB")
    svg.append(draw_component_label(mb_x, main_feed_y + 24, mb_spec, font_size=10, align="middle"))

    # Main AC Isolator Switch (Above line)
    iso_x = busbar_x + 330
    iso_spec = main_sw.get("isolator_spec", "63 A / 4P AC Isolator")
    svg.append(f'''
    <circle cx="{iso_x-8}" cy="{main_feed_y}" r="2.5" fill="#000000"/>
    <line x1="{iso_x-8}" y1="{main_feed_y}" x2="{iso_x+12}" y2="{main_feed_y-10}" stroke="#000000" stroke-width="2"/>
    <circle cx="{iso_x+16}" cy="{main_feed_y}" r="2.5" fill="#000000"/>
    ''')
    svg.append(draw_component_label(iso_x + 4, main_feed_y - 20, iso_spec, font_size=10, align="middle"))

    # Secondary Busbar (`BUS BAR` vertical block)
    svg.append(f'''
    <rect x="{inter_x}" y="{main_feed_y - 45}" width="24" height="110" fill="#f8fafc" stroke="#000000" stroke-width="2"/>
    <text x="{inter_x + 15}" y="{main_feed_y + 22}" font-size="10.5" font-weight="bold" fill="#000000" transform="rotate(90 {inter_x + 15} {main_feed_y + 22})">BUS BAR</text>
    ''')

    # Tap to Load (Top right)
    load_box_x = inter_x + 75
    svg.append(f'''
    <line x1="{inter_x + 24}" y1="{main_feed_y - 25}" x2="{load_box_x}" y2="{main_feed_y - 25}" stroke="#000000" stroke-width="2"/>
    <rect x="{load_box_x}" y="{main_feed_y - 48}" width="65" height="45" fill="#ffffff" stroke="#000000" stroke-width="1.8"/>
    <text x="{load_box_x + 32}" y="{main_feed_y - 21}" font-size="12" font-weight="bold" fill="#000000" text-anchor="middle">Load</text>
    ''')

    # Tap to CEB Meter (Bottom right)
    meter_box_x = inter_x + 75
    svg.append(f'''
    <line x1="{inter_x + 24}" y1="{main_feed_y + 35}" x2="{meter_box_x}" y2="{main_feed_y + 35}" stroke="#000000" stroke-width="2"/>
    <rect x="{meter_box_x}" y="{main_feed_y + 10}" width="75" height="52" fill="#ffffff" stroke="#000000" stroke-width="2"/>
    <text x="{meter_box_x + 37}" y="{main_feed_y + 34}" font-size="12" font-weight="bold" fill="#000000" text-anchor="middle">CEB</text>
    <text x="{meter_box_x + 37}" y="{main_feed_y + 49}" font-size="12" font-weight="bold" fill="#000000" text-anchor="middle">Meter</text>
    ''')

    # Optional Grid Transformer (T/F) for commercial >= 100kW
    if cap_kw >= 100.0:
        tf_x = meter_box_x + 75 + 35
        svg.append(f'''
        <line x1="{meter_box_x + 75}" y1="{main_feed_y + 35}" x2="{tf_x - 18}" y2="{main_feed_y + 35}" stroke="#000000" stroke-width="2"/>
        <circle cx="{tf_x}" cy="{main_feed_y + 35}" r="18" fill="#ffffff" stroke="#000000" stroke-width="1.8"/>
        <text x="{tf_x}" y="{main_feed_y + 40}" font-size="11" font-weight="bold" fill="#000000" text-anchor="middle">T/F</text>
        <text x="{tf_x}" y="{main_feed_y + 66}" font-size="9" fill="#475569" text-anchor="middle">Utility Grid</text>
        ''')

    # -------------------------------------------------------------
    # 6. Bottom Standard 4-Column CAD Title Block
    # -------------------------------------------------------------
    svg.append(f'<rect x="{margin_x+5}" y="{tb_y}" width="{inner_w-10}" height="{tb_h}" fill="#ffffff" stroke="#000000" stroke-width="1.5"/>')

    col1_w = 340
    col2_w = 400
    col3_w = 320
    col4_w = (inner_w - 10) - col1_w - col2_w - col3_w

    x_c1 = margin_x + 5
    x_c2 = x_c1 + col1_w
    x_c3 = x_c2 + col2_w
    x_c4 = x_c3 + col3_w

    svg.append(f'<line x1="{x_c2}" y1="{tb_y}" x2="{x_c2}" y2="{tb_y+tb_h}" stroke="#000000" stroke-width="1.2"/>')
    svg.append(f'<line x1="{x_c3}" y1="{tb_y}" x2="{x_c3}" y2="{tb_y+tb_h}" stroke="#000000" stroke-width="1.2"/>')
    svg.append(f'<line x1="{x_c4}" y1="{tb_y}" x2="{x_c4}" y2="{tb_y+tb_h}" stroke="#000000" stroke-width="1.2"/>')

    # Col 1: Designed By
    svg.append(f'<text x="{x_c1+15}" y="{tb_y+22}" font-size="11" fill="#475569">Designed By :</text>')
    svg.append(f'<text x="{x_c1+20}" y="{tb_y+60}" font-size="17" font-weight="bold" fill="#000000">{html.escape(tb.get("designed_by", "East West Solar PVT (Ltd)"))}</text>')
    svg.append(f'<text x="{x_c1+20}" y="{tb_y+84}" font-size="11" fill="#334155">Lead Engineer: {html.escape(tb.get("drawn_by", "Eng. Aashir"))} © 2026</text>')
    svg.append(f'<text x="{x_c1+20}" y="{tb_y+102}" font-size="9.5" fill="#64748b">Standards: BS 7671 (Kelani) / IEC 60364-7-712 / BS 7430</text>')

    # Col 2: Title
    svg.append(f'<text x="{x_c2+15}" y="{tb_y+22}" font-size="11" fill="#475569">TiTle :</text>')
    title_text = tb.get("title", f"{cap_kw:.0f} Kw on-Grid Solar System")
    svg.append(f'<text x="{x_c2+20}" y="{tb_y+56}" font-size="15" font-weight="bold" fill="#000000">{html.escape(title_text)}</text>')
    svg.append(f'<text x="{x_c2+20}" y="{tb_y+80}" font-size="11" fill="#334155">Grid Connection: {voltage_v:.0f}V ({grid_phases}-Phase 50Hz)</text>')
    svg.append(f'<text x="{x_c2+20}" y="{tb_y+100}" font-size="10" fill="#64748b">Installed DC: {dc_kwp:.2f} kWp | Ratio: {meta.get("ratio", 1.25):.2f}</text>')

    # Col 3: Client
    svg.append(f'<text x="{x_c3+15}" y="{tb_y+22}" font-size="11" fill="#475569">Clint :</text>')
    svg.append(f'<text x="{x_c3+20}" y="{tb_y+58}" font-size="15" font-weight="bold" fill="#000000">{html.escape(tb.get("client", "Valued Client"))}</text>')
    svg.append(f'<text x="{x_c3+20}" y="{tb_y+82}" font-size="11" fill="#475569">{html.escape(tb.get("location", "Facility Rooftop"))}</text>')

    # Col 4: Meta Table
    r_h = tb_h / 4.0
    for r in range(1, 4):
        svg.append(f'<line x1="{x_c4}" y1="{tb_y + r*r_h}" x2="{x_c4+col4_w}" y2="{tb_y + r*r_h}" stroke="#000000" stroke-width="0.8"/>')
    mid_x = x_c4 + (col4_w * 0.45)
    svg.append(f'<line x1="{mid_x}" y1="{tb_y}" x2="{mid_x}" y2="{tb_y + 2*r_h}" stroke="#000000" stroke-width="0.8"/>')

    svg.append(f'<text x="{x_c4+8}" y="{tb_y+20}" font-size="10" fill="#333333">Scale : {html.escape(tb.get("scale", "1:50"))}</text>')
    svg.append(f'<text x="{mid_x+8}" y="{tb_y+20}" font-size="10" font-weight="bold" fill="#000000">Drawn By : {html.escape(tb.get("drawn_by", "Eng. Aashir"))}</text>')
    svg.append(f'<text x="{x_c4+8}" y="{tb_y+r_h+20}" font-size="10" fill="#333333">Date : {html.escape(tb.get("date", "19.08.2026"))}</text>')
    svg.append(f'<text x="{mid_x+8}" y="{tb_y+r_h+20}" font-size="10" fill="#333333">Ref : {html.escape(tb.get("ref", "EW/SLD/01"))}</text>')
    svg.append(f'<text x="{x_c4+8}" y="{tb_y+2*r_h+20}" font-size="10.5" font-weight="bold" fill="#000000">Drawing Title : Single Line Diagram</text>')
    svg.append(f'<text x="{x_c4+8}" y="{tb_y+3*r_h+20}" font-size="10" fill="#333333">Location : {html.escape(tb.get("location", "Colombo"))}</text>')

    svg.append('</svg>')
    return "\n".join(svg)


# ===========================================================================
# PUBLIC EXPORT FUNCTIONS
# ===========================================================================

def generate_sld_svg(unified_dataset_or_summary: Any, layout_style: str = "auto") -> str:
    """
    Generates a full-scale CAD engineering Single Line Diagram (SLD) in SVG format.
    Accepts either the unified engineering dataset or a design summary dictionary.

    Parameters
    ----------
    unified_dataset_or_summary : dict or Any
        Unified engineering dataset containing 'sld_data' or design state dictionary.
    layout_style : str
        'auto' : Uses vertical blueprint for 1 inverter, horizontal for multi-inverter fleet.
        'vertical' : Forces clean vertical layout (matches 5KW & 20kW blueprints).
        'horizontal' : Forces horizontal collector-busbar layout (matches 13KW & 260kW blueprints).
    """
    if isinstance(unified_dataset_or_summary, dict) and "sld_data" in unified_dataset_or_summary:
        sld = unified_dataset_or_summary["sld_data"]
    elif isinstance(unified_dataset_or_summary, dict) and "inverters" in unified_dataset_or_summary:
        sld = unified_dataset_or_summary
    else:
        from core.unified_dataset import get_unified_engineering_dataset
        ds = get_unified_engineering_dataset()
        sld = ds["sld_data"]

    inverters = sld.get("inverters", [])
    inv_count = len(inverters)

    if layout_style == "vertical" or (layout_style == "auto" and inv_count <= 1):
        return _generate_vertical_single_inverter_svg(sld)
    else:
        return _generate_horizontal_multi_inverter_svg(sld)


def generate_sld_pdf(unified_dataset_or_summary: Any, layout_style: str = "auto") -> bytes:
    """
    Generates a high-resolution vector PDF drawing of the Single Line Diagram (SLD)
    formatted in CAD landscape with border, title block, and engineering stamp.
    """
    svg_str = generate_sld_svg(unified_dataset_or_summary, layout_style=layout_style)

    # Use PyMuPDF vector SVG->PDF conversion for pristine vector fidelity
    try:
        import pymupdf as fitz
        svg_doc = fitz.open(stream=svg_str.encode("utf-8"), filetype="svg")
        pdf_bytes = svg_doc.convert_to_pdf()
        if pdf_bytes and len(pdf_bytes) > 1000:
            return pdf_bytes
    except Exception:
        pass

    # Fallback: ReportLab Drawing
    page_w, page_h = landscape(A3)
    buffer = io.BytesIO()
    margin = 15
    dw = page_w - (2 * margin)
    dh = page_h - (2 * margin)
    d = Drawing(dw, dh)

    if isinstance(unified_dataset_or_summary, dict) and "sld_data" in unified_dataset_or_summary:
        sld = unified_dataset_or_summary["sld_data"]
    else:
        from core.unified_dataset import get_unified_engineering_dataset
        ds = get_unified_engineering_dataset()
        sld = ds["sld_data"]

    tb = sld.get("title_block", {})

    d.add(Rect(0, 0, dw, dh, fillColor=None, strokeColor=colors.black, strokeWidth=2))
    d.add(Rect(4, 4, dw - 8, dh - 8, fillColor=None, strokeColor=colors.black, strokeWidth=0.5))

    tb_h = 95
    d.add(Rect(4, 4, dw - 8, tb_h, fillColor=colors.white, strokeColor=colors.black, strokeWidth=1.5))
    d.add(String(20, tb_h - 20, str(tb.get("designed_by", "East West Solar PVT (Ltd)")), fontName="Helvetica-Bold", fontSize=14))
    d.add(String(20, tb_h - 40, f"Drawn By: {tb.get('drawn_by', 'Eng. Aashir')} © 2026", fontName="Helvetica", fontSize=9))
    d.add(String(20, tb_h - 60, f"Title: {tb.get('title', 'Solar PV System')}", fontName="Helvetica-Bold", fontSize=12))

    c = canvas.Canvas(buffer, pagesize=landscape(A3))
    renderPDF.draw(d, c, margin, margin)
    c.showPage()
    c.save()
    return buffer.getvalue()
