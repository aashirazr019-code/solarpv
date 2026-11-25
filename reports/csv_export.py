"""
reports/csv_export.py — Sourced Bill of Materials (BOM) CSV Generator
Generates clean, standardized, machine-readable Bill of Materials CSV files.
Fields:
  - Item No.
  - Category
  - Description
  - Specification
  - Manufacturer / Model
  - Rating
  - Unit
  - Quantity
  - Remarks (Engineering Standards & Sourcing Rules)

Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
"""
from typing import List, Dict, Any, Union
import csv
import io
from datetime import datetime


def export_bom_to_csv(bom_items_or_dataset: Union[List[Any], Dict[str, Any]]) -> str:
    """
    Exports a clean, standardized, numbered BOM CSV representing the final engineering design.
    Consumes either the unified dataset or structured BOM list.
    """
    # If unified dataset is passed
    if isinstance(bom_items_or_dataset, dict) and "bom_items" in bom_items_or_dataset:
        bom_items = bom_items_or_dataset["bom_items"]
        proj = bom_items_or_dataset.get("project", {})
        proj_title = proj.get("name", "Solar PV Engineering Design")
        cap_str = f"{bom_items_or_dataset.get('inverter_infrastructure', {}).get('actual_ac_kw', 13.0):.1f} kW AC"
    else:
        bom_items = bom_items_or_dataset if isinstance(bom_items_or_dataset, list) else []
        proj_title = "Solar Photovoltaic Generation Facility"
        cap_str = "Verified Engineering Design"

    output = io.StringIO()
    # Professional Engineering Metadata Header
    output.write(f"# ==============================================================================\n")
    output.write(f"# SOLAR PV ENGINEERING DESIGN PLATFORM — OFFICIAL BILL OF MATERIALS (BOM)\n")
    output.write(f"# Project: {proj_title} | Capacity: {cap_str}\n")
    output.write(f"# Lead Systems Engineer: Eng. Aashir | © {datetime.now().year} All Rights Reserved\n")
    output.write(f"# Standards: BS 7671:2008 / IEC 60364-7-712 / IEC 60269-6 / BS 7430 / CEB Code\n")
    output.write(f"# Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output.write(f"# ==============================================================================\n")

    writer = csv.writer(output, lineterminator="\n")
    headers = [
        "Item No.",
        "Category",
        "Description",
        "Specification",
        "Manufacturer / Model",
        "Rating",
        "Unit",
        "Quantity",
        "Remarks"
    ]
    writer.writerow(headers)

    for idx, item in enumerate(bom_items):
        if isinstance(item, dict):
            i_no = item.get("item_no", idx + 1)
            cat = item.get("category", "General")
            desc = item.get("item_name") or item.get("name") or item.get("description", "")
            spec = item.get("specification", "")
            mfr_model = item.get("model", "")
            rating = item.get("rating", "")
            unit = item.get("unit", "Nos")
            qty = item.get("quantity", 0)
            remarks = item.get("rule_source") or item.get("remarks", "BS 7671 / IEC")
        else:
            i_no = getattr(item, "item_no", idx + 1)
            cat = getattr(item, "category", "General")
            desc = getattr(item, "item_name", None) or getattr(item, "description", None) or getattr(item, "name", str(item))
            spec = getattr(item, "specification", "")
            mfr = getattr(item, "manufacturer", "") or ""
            model = getattr(item, "model", "") or ""
            mfr_model = f"{mfr} {model}".strip()
            rating = getattr(item, "rating", "")
            unit = getattr(item, "unit", "Nos")
            qty = getattr(item, "quantity", 0)
            remarks = getattr(item, "rule_source", None) or getattr(item, "remarks", "BS 7671 / IEC")

        writer.writerow([
            i_no,
            cat,
            desc,
            spec,
            mfr_model,
            rating,
            unit,
            qty,
            remarks
        ])

    return output.getvalue()


def export_design_summary_to_csv(unified_dataset_or_summary: Any) -> str:
    """
    Exports comprehensive design summary key-value pairs to CSV format.
    """
    if isinstance(unified_dataset_or_summary, dict) and "pv_subsystem" in unified_dataset_or_summary:
        ds = unified_dataset_or_summary
    else:
        from core.unified_dataset import get_unified_engineering_dataset
        ds = get_unified_engineering_dataset()

    p = ds["project"]
    pv = ds["pv_subsystem"]
    inv = ds["inverter_infrastructure"]
    ac = ds["whole_system_ac"]
    e = ds["earthing_system"]
    y = ds["energy_yield"]

    output = io.StringIO()
    output.write(f"# Solar PV Design Summary — Eng. Aashir © {datetime.now().year}\n")
    output.write(f"# Project: {p.get('name', 'N/A')} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["Section", "Parameter", "Value", "Unit", "Standards Reference"])

    rows = [
        ["Project", "Project Name", p.get("name", "N/A"), "-", "Contract Record"],
        ["Project", "Client", p.get("customer_name", "N/A"), "-", "Client Information"],
        ["Project", "Site Location", p.get("location", "N/A"), "-", "Site Data"],
        ["Project", "Nominal Grid Voltage", f"{p.get('grid_voltage_v', 400):.0f} V ({p.get('grid_phases', 3)}-Phase)", "-", "CEB Grid Code"],
        ["PV Subsystem", "Module Model", f"{pv['panel'].manufacturer} {pv['panel'].model}", "-", "Tier-1 Photovoltaic Module"],
        ["PV Subsystem", "Total PV Modules", pv.get("total_panels", 0), "Nos", "Dynamic Array Sizing"],
        ["PV Subsystem", "Installed DC Capacity", f"{pv.get('installed_dc_kwp', 0.0):.2f}", "kWp", "Array Peak Power"],
        ["PV Subsystem", "DC/AC Loading Ratio", f"{pv.get('dc_ac_ratio', 1.25):.2f}", "-", "Recommended: 1.10 - 1.35"],
        ["Inverter Fleet", "Nominal AC Capacity", f"{inv.get('actual_ac_kw', 0.0):.1f}", "kW", "Contractual Export Capacity"],
        ["Inverter Fleet", "Inverter Units", inv.get("inverter_units_count", 1), "Units", inv.get("fleet_description", "")],
        ["Inverter Fleet", "Continuous AC Current", f"{ac.get('total_ac_current_a', 0.0):.1f}", "A", "Sum of Inverter Currents"],
        ["AC Switchgear", "Main Circuit Breaker", ac.get("main_breaker_spec", "N/A"), "-", "BS EN 60947-2"],
        ["AC Switchgear", "Main AC Isolator", ac.get("main_isolator_spec", "N/A"), "-", "BS EN 60947-3"],
        ["AC Switchgear", "Utility Lockable Switch", ac.get("lockable_switch_spec", "N/A"), "-", "CEB Clause 6.3 Padlockable"],
        ["AC Cabling", "Main Export Cable", f"4-Core {ac.get('main_cable_csa_mm2', 10):.0f} mm² Cu", "-", "BS 7671 Table A1 (Kelani Cables)"],
        ["Earthing", "Main Protective Earth", f"{e.get('main_earth_conductor_csa_mm2', 16):.0f} mm² Cu", "-", "BS 7430 Earthing Sizing"],
        ["Earthing", "Achieved Earth Resistance", f"{e.get('achieved_resistance_ohm', 4.2):.1f}", "Ω", "BS 7430 limit <= 10.0 Ω"],
        ["Yield Forecast", "Annual Energy Export", f"{y.get('annual_energy_kwh', 0):,.0f}", "kWh/yr", "Loss Waterfall Yield Forecast"],
        ["Yield Forecast", "Performance Ratio (PR)", f"{y.get('pr_pct', 79.5):.1f}", "%", "System Performance Ratio"]
    ]

    for r in rows:
        writer.writerow(r)

    return output.getvalue()
