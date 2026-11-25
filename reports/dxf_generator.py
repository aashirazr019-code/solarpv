"""
reports/dxf_generator.py — Parametric AutoCAD DXF Single Line Diagram (SLD) Generator
Generates native AutoCAD (.dxf) vector engineering drawings conforming to:
  - Eng. Aashir's CAD blueprint visual standard (from single line diagrams.rar)
  - BS 7671:2008 (Table A1 Kelani Cables)
  - IEC 60364-7-712 / IEC 60269-6
  - BS 7430:2011 (Earthing)
  - CEB / LECO Interconnection Guidelines

Layer Standards:
  - BORDER: Outer double CAD border
  - TITLE_BLOCK: 4-compartment standard title block
  - ELEC_DC: DC string wiring & polarity symbols
  - ELEC_AC: 3-phase/1-phase AC conductors & collector busbar
  - ELEC_EARTHING: Green protective conductor & earth pit
  - EQUIPMENT: Module frames, inverters, switchgear, meters, transformer
  - TEXT: Engineering notations, equipment labels, and ratings

Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
"""
from typing import Dict, Any, Union
import io
import ezdxf
from ezdxf import colors


def generate_sld_dxf(unified_dataset_or_summary: Any) -> str:
    """
    Generates a full-scale CAD engineering Single Line Diagram (SLD) in AutoCAD DXF format.
    Accepts either the unified engineering dataset or a design summary dictionary.
    Returns the DXF file content as a string.
    """
    # 1. Resolve dataset
    if isinstance(unified_dataset_or_summary, dict) and "sld_data" in unified_dataset_or_summary:
        sld = unified_dataset_or_summary["sld_data"]
    elif isinstance(unified_dataset_or_summary, dict) and "inverters" in unified_dataset_or_summary:
        sld = unified_dataset_or_summary
    else:
        from core.unified_dataset import get_unified_engineering_dataset
        ds = get_unified_engineering_dataset(13.0)
        sld = ds["sld_data"]

    tb = sld.get("title_block", {})
    meta = sld.get("system_meta", {})
    inverters = sld.get("inverters", [])
    busbar = sld.get("busbar", {})
    main_sw = sld.get("main_switchgear", {})
    grid = sld.get("grid", {})
    earthing = sld.get("earthing", {})

    # 2. Create DXF document (AutoCAD R2010 format for universal compatibility)
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # 3. Setup CAD Layers
    layers = [
        ("BORDER", colors.WHITE, 0.50),
        ("TITLE_BLOCK", colors.CYAN, 0.35),
        ("ELEC_DC", colors.RED, 0.35),
        ("ELEC_AC", colors.YELLOW, 0.35),
        ("ELEC_EARTHING", colors.GREEN, 0.35),
        ("EQUIPMENT", colors.WHITE, 0.35),
        ("TEXT", colors.WHITE, 0.25),
        ("ANNOTATIONS", colors.CYAN, 0.20),
    ]
    for name, color, lw in layers:
        if name not in doc.layers:
            layer = doc.layers.add(name)
            layer.color = color

    # Coordinate system: A3 Landscape (420mm x 297mm in CAD units)
    w = 420.0
    h = 297.0
    margin = 8.0

    # 4. Outer CAD Double Border
    msp.add_lwpolyline([(margin, margin), (w - margin, margin), (w - margin, h - margin), (margin, h - margin), (margin, margin)], dxfattribs={"layer": "BORDER"})
    msp.add_lwpolyline([(margin + 2.0, margin + 2.0), (w - margin - 2.0, margin + 2.0), (w - margin - 2.0, h - margin - 2.0), (margin + 2.0, h - margin - 2.0), (margin + 2.0, margin + 2.0)], dxfattribs={"layer": "BORDER"})

    # 5. Drawing Title Block (Bottom Right CAD Table per Eng. Aashir format)
    tb_w = 180.0
    tb_h = 42.0
    tb_x = w - margin - 2.0 - tb_w
    tb_y = margin + 2.0

    msp.add_lwpolyline([(tb_x, tb_y), (tb_x + tb_w, tb_y), (tb_x + tb_w, tb_y + tb_h), (tb_x, tb_y + tb_h), (tb_x, tb_y)], dxfattribs={"layer": "TITLE_BLOCK"})
    msp.add_line((tb_x, tb_y + 28.0), (tb_x + tb_w, tb_y + 28.0), dxfattribs={"layer": "TITLE_BLOCK"})
    msp.add_line((tb_x, tb_y + 14.0), (tb_x + tb_w, tb_y + 14.0), dxfattribs={"layer": "TITLE_BLOCK"})
    msp.add_line((tb_x + 90.0, tb_y), (tb_x + 90.0, tb_y + tb_h), dxfattribs={"layer": "TITLE_BLOCK"})

    # Title block texts
    msp.add_text(f"DESIGNED BY: {tb.get('designed_by', 'East West Solar')}", dxfattribs={"layer": "TEXT", "height": 3.0}).set_placement((tb_x + 3.0, tb_y + 34.0))
    msp.add_text(f"DRAWN BY: {tb.get('drawn_by', 'Eng. Aashir')} (c) 2026", dxfattribs={"layer": "TEXT", "height": 2.2}).set_placement((tb_x + 3.0, tb_y + 30.0))

    
    msp.add_text(f"CLIENT: {tb.get('client', 'Commercial Client')}", dxfattribs={"layer": "TEXT", "height": 3.0}).set_placement((tb_x + 93.0, tb_y + 34.0))
    msp.add_text(f"LOCATION: {tb.get('location', 'Colombo, Sri Lanka')}", dxfattribs={"layer": "TEXT", "height": 2.2}).set_placement((tb_x + 93.0, tb_y + 30.0))

    msp.add_text(f"DRAWING: {tb.get('drawing_title', 'SINGLE LINE DIAGRAM')}", dxfattribs={"layer": "TEXT", "height": 3.2}).set_placement((tb_x + 3.0, tb_y + 20.0))
    msp.add_text(f"CAPACITY: {meta.get('ac_capacity_kw', 13.0):.1f} kW AC / {meta.get('dc_capacity_kwp', 16.2):.2f} kWp DC", dxfattribs={"layer": "TEXT", "height": 2.5}).set_placement((tb_x + 3.0, tb_y + 16.0))

    msp.add_text(f"SCALE: {tb.get('scale', 'NTS')}", dxfattribs={"layer": "TEXT", "height": 2.5}).set_placement((tb_x + 93.0, tb_y + 20.0))
    msp.add_text(f"DATE: {tb.get('date', '2026-09-07')} | REV: 01", dxfattribs={"layer": "TEXT", "height": 2.5}).set_placement((tb_x + 93.0, tb_y + 16.0))
    msp.add_text(f"STANDARDS: BS 7671 (Kelani) / IEC 60364-7-712 / BS 7430", dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((tb_x + 3.0, tb_y + 5.0))
    msp.add_text(f"STATUS: APPROVED FOR CONSTRUCTION", dxfattribs={"layer": "TEXT", "height": 2.5}).set_placement((tb_x + 93.0, tb_y + 5.0))

    # 6. Earth Pit & Grounding System (Bottom-Left per Eng. Aashir standard)
    earth_x = margin + 20.0
    earth_y = margin + 25.0
    msp.add_circle((earth_x, earth_y), 5.0, dxfattribs={"layer": "ELEC_EARTHING"})
    msp.add_line((earth_x - 7.0, earth_y - 7.0), (earth_x + 7.0, earth_y - 7.0), dxfattribs={"layer": "ELEC_EARTHING"})
    msp.add_line((earth_x - 5.0, earth_y - 9.0), (earth_x + 5.0, earth_y - 9.0), dxfattribs={"layer": "ELEC_EARTHING"})
    msp.add_line((earth_x - 3.0, earth_y - 11.0), (earth_x + 3.0, earth_y - 11.0), dxfattribs={"layer": "ELEC_EARTHING"})
    msp.add_text("EARTH PIT", dxfattribs={"layer": "TEXT", "height": 2.5}).set_placement((earth_x - 8.0, earth_y + 8.0))
    msp.add_text(f"R < 10.0 OHM (BS 7430)", dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((earth_x - 14.0, earth_y - 15.0))

    # Vertical Green Earth Riser to Arrays
    msp.add_line((earth_x, earth_y + 5.0), (earth_x, h - margin - 35.0), dxfattribs={"layer": "ELEC_EARTHING"})
    earth_txt = earthing.get("main_earth_cable", f"1C x {earthing.get('conductor_csa', 16):.0f}mm² Cu PE Main Conductor")
    msp.add_text(earth_txt, dxfattribs={"layer": "TEXT", "height": 2.0, "rotation": 90.0}).set_placement((earth_x - 2.0, earth_y + 35.0))

    # 7. Stacked Inverters & PV Array Subsystems
    n_inv = max(len(inverters), 1)
    slot_h = (h - margin - 50.0 - 55.0) / n_inv

    # Busbar X Position
    bb_x = margin + 210.0
    bb_y_top = h - margin - 40.0
    bb_y_bot = margin + 60.0

    # Draw Heavy Central Collector Busbar
    msp.add_lwpolyline([(bb_x - 2.0, bb_y_bot), (bb_x + 2.0, bb_y_bot), (bb_x + 2.0, bb_y_top), (bb_x - 2.0, bb_y_top), (bb_x - 2.0, bb_y_bot)], dxfattribs={"layer": "ELEC_AC"})
    bb_label = busbar.get("label", f"CENTRAL AC COLLECTOR BUSBAR ({busbar.get('rating_a', 100)}A Cu)")
    dxf_bb_text = f"{bb_label} BUSBAR" if "BUSBAR" not in bb_label.upper() else bb_label
    msp.add_text(dxf_bb_text, dxfattribs={"layer": "TEXT", "height": 2.6, "rotation": 90.0}).set_placement((bb_x - 4.0, bb_y_bot + 15.0))

    # Busbar Instruments (R-Y-B indicator lamps, AC SPD, Power Analyzer, Meter)
    inst_x = bb_x + 8.0
    msp.add_circle((inst_x, bb_y_top - 5.0), 2.5, dxfattribs={"layer": "EQUIPMENT"})
    msp.add_circle((inst_x, bb_y_top - 12.0), 2.5, dxfattribs={"layer": "EQUIPMENT"})
    msp.add_circle((inst_x, bb_y_top - 19.0), 2.5, dxfattribs={"layer": "EQUIPMENT"})
    msp.add_text("R", dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((inst_x - 0.8, bb_y_top - 6.0))
    msp.add_text("Y", dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((inst_x - 0.8, bb_y_top - 13.0))
    msp.add_text("B", dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((inst_x - 0.8, bb_y_top - 20.0))
    msp.add_text("Indicator Lamps", dxfattribs={"layer": "TEXT", "height": 1.8}).set_placement((inst_x + 5.0, bb_y_top - 13.0))

    # AC SPD with Fuse on Busbar
    msp.add_line((bb_x, bb_y_top - 30.0), (inst_x + 12.0, bb_y_top - 30.0), dxfattribs={"layer": "ELEC_AC"})
    msp.add_lwpolyline([(inst_x + 12.0, bb_y_top - 34.0), (inst_x + 24.0, bb_y_top - 34.0), (inst_x + 24.0, bb_y_top - 26.0), (inst_x + 12.0, bb_y_top - 26.0), (inst_x + 12.0, bb_y_top - 34.0)], dxfattribs={"layer": "EQUIPMENT"})
    msp.add_text("AC SPD", dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((inst_x + 14.0, bb_y_top - 29.0))
    spd_txt = busbar.get("spd", {}).get("rating", "40 kA AC-SPD")
    msp.add_text(spd_txt, dxfattribs={"layer": "TEXT", "height": 1.6}).set_placement((inst_x + 12.0, bb_y_top - 37.0))

    # Render each Inverter Branch
    for i, inv in enumerate(inverters):
        center_y = h - margin - 50.0 - (i + 0.5) * slot_h
        
        # 1. PV Array Block
        arr_x = margin + 35.0
        arr_w = 32.0
        arr_h = 24.0
        msp.add_lwpolyline([(arr_x, center_y - arr_h/2), (arr_x + arr_w, center_y - arr_h/2), (arr_x + arr_w, center_y + arr_h/2), (arr_x, center_y + arr_h/2), (arr_x, center_y - arr_h/2)], dxfattribs={"layer": "EQUIPMENT"})
        # Grid lines on PV module
        msp.add_line((arr_x + arr_w/2, center_y - arr_h/2), (arr_x + arr_w/2, center_y + arr_h/2), dxfattribs={"layer": "EQUIPMENT"})
        msp.add_line((arr_x, center_y), (arr_x + arr_w, center_y), dxfattribs={"layer": "EQUIPMENT"})

        mod_count = inv.get("modules_count", inv.get("panels_count", 14))
        mod_model = meta.get("module_model", meta.get("panel_model", "PV Module"))
        msp.add_text("PV ARRAY", dxfattribs={"layer": "TEXT", "height": 2.2}).set_placement((arr_x + 3.0, center_y + 8.0))
        msp.add_text(f"{mod_count}x {mod_model}", dxfattribs={"layer": "TEXT", "height": 1.8}).set_placement((arr_x + 2.0, center_y - 8.0))
        voc_c = inv.get("voc_cold", 0.0)
        vmp_h = inv.get("vmp_hot", 0.0)
        msp.add_text(f"Voc={voc_c:.0f}V Vmp={vmp_h:.0f}V", dxfattribs={"layer": "TEXT", "height": 1.6}).set_placement((arr_x + 2.0, center_y - 11.0))

        # Earth bond from array to earth riser
        msp.add_line((arr_x, center_y), (earth_x, center_y), dxfattribs={"layer": "ELEC_EARTHING"})

        # DC Lines to DC Switchgear
        dc_sw_x = arr_x + arr_w + 14.0
        msp.add_line((arr_x + arr_w, center_y + 4.0), (dc_sw_x, center_y + 4.0), dxfattribs={"layer": "ELEC_DC"})
        msp.add_line((arr_x + arr_w, center_y - 4.0), (dc_sw_x, center_y - 4.0), dxfattribs={"layer": "ELEC_DC"})
        dc_cable_txt = inv.get("dc_cable", "2 x 1C/4sq.mm/Cu/PVC")
        msp.add_text(dc_cable_txt, dxfattribs={"layer": "TEXT", "height": 1.6}).set_placement((arr_x + arr_w + 1.0, center_y + 5.5))

        # DC Isolator & DC SPD Box
        msp.add_lwpolyline([(dc_sw_x, center_y - 10.0), (dc_sw_x + 18.0, center_y - 10.0), (dc_sw_x + 18.0, center_y + 10.0), (dc_sw_x, center_y + 10.0), (dc_sw_x, center_y - 10.0)], dxfattribs={"layer": "EQUIPMENT"})
        dc_iso_txt = inv.get("dc_isolator", "2P 1000V DC Isolator")
        dc_spd_txt = inv.get("dc_spd", "DC SPD-40kA")
        msp.add_text(dc_iso_txt, dxfattribs={"layer": "TEXT", "height": 1.5}).set_placement((dc_sw_x + 1.0, center_y + 4.0))
        msp.add_text(dc_spd_txt, dxfattribs={"layer": "TEXT", "height": 1.5}).set_placement((dc_sw_x + 1.0, center_y - 5.0))

        # Line from DC box to Inverter
        inv_box_x = dc_sw_x + 18.0 + 12.0
        msp.add_line((dc_sw_x + 18.0, center_y), (inv_box_x, center_y), dxfattribs={"layer": "ELEC_DC"})

        # Inverter Box (with diagonal DC/AC division line)
        inv_w = 34.0
        inv_h = 24.0
        msp.add_lwpolyline([(inv_box_x, center_y - inv_h/2), (inv_box_x + inv_w, center_y - inv_h/2), (inv_box_x + inv_w, center_y + inv_h/2), (inv_box_x, center_y + inv_h/2), (inv_box_x, center_y - inv_h/2)], dxfattribs={"layer": "EQUIPMENT"})
        msp.add_line((inv_box_x, center_y + inv_h/2), (inv_box_x + inv_w, center_y - inv_h/2), dxfattribs={"layer": "EQUIPMENT"})

        msp.add_text("DC", dxfattribs={"layer": "TEXT", "height": 2.2}).set_placement((inv_box_x + 4.0, center_y + 4.0))
        msp.add_text("AC", dxfattribs={"layer": "TEXT", "height": 2.2}).set_placement((inv_box_x + inv_w - 9.0, center_y - 7.0))
        inv_label = inv.get("label", f"INV #{i+1}: {inv.get('capacity_kw', 10):.0f} kW")
        msp.add_text(inv_label, dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((inv_box_x + 2.0, center_y + inv_h/2 + 2.0))
        msp.add_text(f"{inv.get('model', 'Inverter')}", dxfattribs={"layer": "TEXT", "height": 1.8}).set_placement((inv_box_x + 2.0, center_y - inv_h/2 - 4.0))

        # AC Output line to Individual MCB
        mcb_x = inv_box_x + inv_w + 14.0
        msp.add_line((inv_box_x + inv_w, center_y), (mcb_x, center_y), dxfattribs={"layer": "ELEC_AC"})
        ac_cable_txt = inv.get("ac_cable", "4C/10mm sq CU/PVC")
        msp.add_text(ac_cable_txt, dxfattribs={"layer": "TEXT", "height": 1.6}).set_placement((inv_box_x + inv_w + 1.0, center_y + 4.0))

        # Individual MCB Box
        msp.add_lwpolyline([(mcb_x, center_y - 6.0), (mcb_x + 14.0, center_y - 6.0), (mcb_x + 14.0, center_y + 6.0), (mcb_x, center_y + 6.0), (mcb_x, center_y - 6.0)], dxfattribs={"layer": "EQUIPMENT"})
        ac_brk_txt = inv.get("ac_breaker", "40A 4P MCB")
        msp.add_text(ac_brk_txt, dxfattribs={"layer": "TEXT", "height": 1.6}).set_placement((mcb_x + 1.0, center_y - 2.0))

        # Feeder to Central Busbar
        msp.add_line((mcb_x + 14.0, center_y), (bb_x, center_y), dxfattribs={"layer": "ELEC_AC"})

    # 8. Main Plant Outgoing Section (Right of Busbar)
    main_tap_y = bb_y_bot + 45.0
    msp.add_line((bb_x, main_tap_y), (bb_x + 25.0, main_tap_y), dxfattribs={"layer": "ELEC_AC"})

    # Main Breaker (MCB / MCCB)
    mb_x = bb_x + 25.0
    msp.add_lwpolyline([(mb_x, main_tap_y - 8.0), (mb_x + 20.0, main_tap_y - 8.0), (mb_x + 20.0, main_tap_y + 8.0), (mb_x, main_tap_y + 8.0), (mb_x, main_tap_y - 8.0)], dxfattribs={"layer": "EQUIPMENT"})
    msp.add_text("MAIN BREAKER", dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((mb_x + 1.5, main_tap_y + 3.0))
    main_brk_txt = main_sw.get("breaker_spec", "63A 4P MCB")
    msp.add_text(main_brk_txt, dxfattribs={"layer": "TEXT", "height": 1.6}).set_placement((mb_x + 1.5, main_tap_y - 4.0))

    # Lockable Utility Disconnect Switch
    iso_x = mb_x + 20.0 + 10.0
    msp.add_line((mb_x + 20.0, main_tap_y), (iso_x, main_tap_y), dxfattribs={"layer": "ELEC_AC"})
    msp.add_lwpolyline([(iso_x, main_tap_y - 8.0), (iso_x + 22.0, main_tap_y - 8.0), (iso_x + 22.0, main_tap_y + 8.0), (iso_x, main_tap_y + 8.0), (iso_x, main_tap_y - 8.0)], dxfattribs={"layer": "EQUIPMENT"})
    msp.add_text("CEB ISOLATOR", dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((iso_x + 2.0, main_tap_y + 3.0))
    main_iso_txt = main_sw.get("isolator_spec", "63A / 4P AC Isolator")
    msp.add_text(main_iso_txt, dxfattribs={"layer": "TEXT", "height": 1.5}).set_placement((iso_x + 2.0, main_tap_y - 4.0))

    # Main AC Export Cable run
    feed_x = iso_x + 22.0 + 12.0
    msp.add_line((iso_x + 22.0, main_tap_y), (feed_x, main_tap_y), dxfattribs={"layer": "ELEC_AC"})
    main_cab_txt = main_sw.get("main_cable", "4C 16sqmm/CU/PVC")
    msp.add_text(f"Main Cable: {main_cab_txt}", dxfattribs={"layer": "TEXT", "height": 1.8}).set_placement((iso_x + 23.0, main_tap_y + 2.0))
    msp.add_text(f"BS 7671 Table A1 (Kelani Cables)", dxfattribs={"layer": "TEXT", "height": 1.5}).set_placement((iso_x + 23.0, main_tap_y - 3.0))

    # Secondary DB & Interconnection Busbar
    msp.add_lwpolyline([(feed_x, main_tap_y - 25.0), (feed_x + 3.0, main_tap_y - 25.0), (feed_x + 3.0, main_tap_y + 25.0), (feed_x, main_tap_y + 25.0), (feed_x, main_tap_y - 25.0)], dxfattribs={"layer": "ELEC_AC"})
    msp.add_text("SECONDARY DB", dxfattribs={"layer": "TEXT", "height": 2.0, "rotation": 90.0}).set_placement((feed_x - 2.0, main_tap_y - 12.0))

    # Facility Load (Top Branch)
    msp.add_line((feed_x + 3.0, main_tap_y + 15.0), (feed_x + 25.0, main_tap_y + 15.0), dxfattribs={"layer": "ELEC_AC"})
    msp.add_lwpolyline([(feed_x + 25.0, main_tap_y + 8.0), (feed_x + 45.0, main_tap_y + 8.0), (feed_x + 45.0, main_tap_y + 22.0), (feed_x + 25.0, main_tap_y + 22.0), (feed_x + 25.0, main_tap_y + 8.0)], dxfattribs={"layer": "EQUIPMENT"})
    msp.add_text("FACILITY LOAD", dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((feed_x + 27.0, main_tap_y + 14.0))

    # CEB Net Meter (Bottom Branch)
    meter_y = main_tap_y - 15.0
    msp.add_line((feed_x + 3.0, meter_y), (feed_x + 25.0, meter_y), dxfattribs={"layer": "ELEC_AC"})
    msp.add_lwpolyline([(feed_x + 25.0, meter_y - 10.0), (feed_x + 48.0, meter_y - 10.0), (feed_x + 48.0, meter_y + 10.0), (feed_x + 25.0, meter_y + 10.0), (feed_x + 25.0, meter_y - 10.0)], dxfattribs={"layer": "EQUIPMENT"})
    msp.add_text("CEB / LECO", dxfattribs={"layer": "TEXT", "height": 2.2}).set_placement((feed_x + 28.0, meter_y + 3.0))
    msp.add_text("NET METER", dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((feed_x + 28.0, meter_y - 4.0))

    # Grid Transformer (T/F)
    tf_x = feed_x + 48.0 + 15.0
    msp.add_line((feed_x + 48.0, meter_y), (tf_x - 6.0, meter_y), dxfattribs={"layer": "ELEC_AC"})
    msp.add_circle((tf_x, meter_y), 6.0, dxfattribs={"layer": "EQUIPMENT"})
    msp.add_text("T/F", dxfattribs={"layer": "TEXT", "height": 2.5}).set_placement((tf_x - 2.5, meter_y - 1.0))
    msp.add_text("Utility Grid", dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((tf_x - 6.0, meter_y - 11.0))

    # Export to DXF stream
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue()
