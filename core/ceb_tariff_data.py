"""
core/ceb_tariff_data.py — Centralized CEB Electricity Tariff & Solar System Configuration
Effective Date: 01 April 2026 (PUCSL / CEB Tariff Schedule Revision).
Authored by Eng. Aashir (c) 2026. All Rights Reserved.

Defines:
1. tariffConfig: All Retail, Bulk, TOU, and EVCS tariffs.
2. solarConfig: Solar generation rate (120 kWh/kW/month), Net Plus feed-in rate (Rs. 19/kWh), SSCL (2.5%).
"""

from typing import Dict, Any

# ---------------------------------------------------------------------------
# Global Solar & Statutory Parameters
# ---------------------------------------------------------------------------
SOLAR_CONFIG: Dict[str, Any] = {
    # Default benchmark assumption: 5 kW -> 600 kWh/month => 120 kWh/kW/month
    "default_generation_per_kw_month": 120.0,
    # Net Plus Feed-in Tariff configured rate (LKR / kWh)
    # Note: Admin-configurable system rate.
    "net_plus_export_rate_lkr": 19.0,
    # Social Security Contribution Levy (2.5% on bill subtotal)
    "sscl_rate": 0.025,
    # Effective date of tariff revision
    "effective_date": "2026-04-01",
}


# ---------------------------------------------------------------------------
# Centralized CEB Tariff Configuration (tariffConfig)
# ---------------------------------------------------------------------------
TARIFF_CONFIG: Dict[str, Dict[str, Any]] = {
    # -----------------------------------------------------------------------
    # 1. RETAIL CATEGORIES
    # -----------------------------------------------------------------------
    "Domestic": {
        "name": "Domestic (D-1)",
        "type": "domestic_slab",
        "description": "Private residential premises. Slabs <=60 kWh are incremental; slabs >60 kWh use retroactive pricing.",
        "is_bulk": False,
        "requires_demand": False,
        "requires_tou": False,
        # Incremental blocks for consumption <= 60 kWh/month
        "blocks_le_60": [
            {"min_kwh": 0, "max_kwh": 30, "rate_lkr": 5.0, "fixed_charge_lkr": 80.0},
            {"min_kwh": 31, "max_kwh": 60, "rate_lkr": 9.0, "fixed_charge_lkr": 210.0},
        ],
        # Retroactive slabs for consumption > 60 kWh/month
        # The total consumption determines the slab, and that slab's rate applies to ALL units!
        "slabs_gt_60": [
            {"min_kwh": 61, "max_kwh": 90, "retroactive_rate_lkr": 20.0, "fixed_charge_lkr": 400.0},
            {"min_kwh": 91, "max_kwh": 120, "retroactive_rate_lkr": 28.0, "fixed_charge_lkr": 1000.0},
            {"min_kwh": 121, "max_kwh": 180, "retroactive_rate_lkr": 44.0, "fixed_charge_lkr": 1500.0},
            {"min_kwh": 181, "max_kwh": 999999, "retroactive_rate_lkr": 85.0, "fixed_charge_lkr": 2100.0},
        ],
    },

    "Domestic TOU": {
        "name": "Domestic Time of Use (D-TOU)",
        "type": "tou",
        "description": "Optional residential Time of Use metering with dedicated Day, Peak, and Off-Peak intervals.",
        "is_bulk": False,
        "requires_demand": False,
        "requires_tou": True,
        "day_rate_lkr": 40.0,         # 05:30 - 18:30
        "peak_rate_lkr": 90.0,        # 18:30 - 22:30
        "off_peak_rate_lkr": 28.0,    # 22:30 - 05:30
        "fixed_charge_lkr": 2100.0,
        "default_distribution": {"day_pct": 0.60, "peak_pct": 0.15, "off_peak_pct": 0.25},
    },

    "Religious": {
        "name": "Religious & Charitable (R-1)",
        "type": "incremental_block",
        "description": "Places of public religious worship, approved charities and social welfare institutions.",
        "is_bulk": False,
        "requires_demand": False,
        "requires_tou": False,
        "slabs": [
            {"min_kwh": 0, "max_kwh": 30, "rate_lkr": 4.50, "fixed_charge_lkr": 80.0},
            {"min_kwh": 31, "max_kwh": 90, "rate_lkr": 4.50, "fixed_charge_lkr": 150.0},
            {"min_kwh": 91, "max_kwh": 120, "rate_lkr": 8.00, "fixed_charge_lkr": 400.0},
            {"min_kwh": 121, "max_kwh": 180, "rate_lkr": 19.00, "fixed_charge_lkr": 1000.0},
            {"min_kwh": 181, "max_kwh": 999999, "rate_lkr": 30.00, "fixed_charge_lkr": 1500.0},
        ],
    },

    "Industrial": {
        "name": "Industrial Rate 1 (I-1)",
        "type": "volume_differentiated",
        "description": "Manufacturing, mining, agriculture, cold storage (400/230V, contract demand <= 42 kVA).",
        "is_bulk": False,
        "requires_demand": False,
        "requires_tou": False,
        "threshold_kwh": 300,
        "tier_1": {"rate_lkr": 9.00, "fixed_charge_lkr": 300.0},     # <= 300 units
        "tier_2": {"rate_lkr": 18.00, "fixed_charge_lkr": 800.0},   # > 300 units
    },

    "General": {
        "name": "General Purpose Rate 1 (GP-1)",
        "type": "volume_differentiated",
        "description": "Commercial premises, retail shops, offices, banks, clinics (400/230V, contract demand <= 42 kVA).",
        "is_bulk": False,
        "requires_demand": False,
        "requires_tou": False,
        "threshold_kwh": 180,
        "tier_1": {"rate_lkr": 27.00, "fixed_charge_lkr": 500.0},   # <= 180 units
        "tier_2": {"rate_lkr": 36.00, "fixed_charge_lkr": 1600.0},  # > 180 units
    },

    "Government": {
        "name": "Government Rate 1 (GV-1)",
        "type": "flat_rate",
        "description": "Government-owned hospitals, schools, and non-commercial public institutions (<= 42 kVA).",
        "is_bulk": False,
        "requires_demand": False,
        "requires_tou": False,
        "rate_lkr": 24.00,
        "fixed_charge_lkr": 600.0,
    },

    "Hotel": {
        "name": "Hotel Rate 1 (H-1)",
        "type": "volume_differentiated",
        "description": "Hotels & tourist guest houses registered with SLTDA (400/230V, contract demand <= 42 kVA).",
        "is_bulk": False,
        "requires_demand": False,
        "requires_tou": False,
        "threshold_kwh": 300,
        "tier_1": {"rate_lkr": 9.00, "fixed_charge_lkr": 300.0},
        "tier_2": {"rate_lkr": 18.00, "fixed_charge_lkr": 800.0},
    },

    "Agriculture": {
        "name": "Agriculture Supply",
        "type": "volume_differentiated",
        "description": "Agricultural pumping, greenhouse cultivation, and irrigation systems (<= 42 kVA).",
        "is_bulk": False,
        "requires_demand": False,
        "requires_tou": False,
        "threshold_kwh": 300,
        "tier_1": {"rate_lkr": 9.00, "fixed_charge_lkr": 300.0},
        "tier_2": {"rate_lkr": 18.00, "fixed_charge_lkr": 800.0},
    },

    # -----------------------------------------------------------------------
    # 2. BULK & MAXIMUM DEMAND CATEGORIES (Rate 2 & Rate 3)
    # -----------------------------------------------------------------------
    "Industrial-2": {
        "name": "Industrial Bulk Low Voltage (I-2)",
        "type": "bulk_tou",
        "description": "Industrial bulk supply metered at 400/230V, contract demand > 42 kVA.",
        "is_bulk": True,
        "requires_demand": True,
        "requires_tou": True,
        "day_rate_lkr": 16.0,
        "peak_rate_lkr": 33.0,
        "off_peak_rate_lkr": 14.0,
        "fixed_charge_lkr": 5000.0,
        "demand_charge_lkr_per_kva": 1400.0,
        "default_distribution": {"day_pct": 0.65, "peak_pct": 0.15, "off_peak_pct": 0.20},
    },

    "Industrial-3": {
        "name": "Industrial Bulk Medium Voltage (I-3)",
        "type": "bulk_tou",
        "description": "Industrial bulk supply metered at 11 kV / 33 kV medium voltage.",
        "is_bulk": True,
        "requires_demand": True,
        "requires_tou": True,
        "day_rate_lkr": 15.0,
        "peak_rate_lkr": 32.0,
        "off_peak_rate_lkr": 13.0,
        "fixed_charge_lkr": 5000.0,
        "demand_charge_lkr_per_kva": 1350.0,
        "default_distribution": {"day_pct": 0.65, "peak_pct": 0.15, "off_peak_pct": 0.20},
    },

    "General-2": {
        "name": "General Purpose Bulk Low Voltage (GP-2)",
        "type": "bulk_tou",
        "description": "Commercial bulk supply metered at 400/230V, contract demand > 42 kVA.",
        "is_bulk": True,
        "requires_demand": True,
        "requires_tou": True,
        "day_rate_lkr": 25.0,
        "peak_rate_lkr": 45.0,
        "off_peak_rate_lkr": 18.0,
        "fixed_charge_lkr": 5000.0,
        "demand_charge_lkr_per_kva": 1400.0,
        "default_distribution": {"day_pct": 0.70, "peak_pct": 0.15, "off_peak_pct": 0.15},
    },

    "General-3": {
        "name": "General Purpose Bulk Medium Voltage (GP-3)",
        "type": "bulk_tou",
        "description": "Commercial bulk supply metered at 11 kV / 33 kV medium voltage.",
        "is_bulk": True,
        "requires_demand": True,
        "requires_tou": True,
        "day_rate_lkr": 24.0,
        "peak_rate_lkr": 43.0,
        "off_peak_rate_lkr": 17.0,
        "fixed_charge_lkr": 5000.0,
        "demand_charge_lkr_per_kva": 1350.0,
        "default_distribution": {"day_pct": 0.70, "peak_pct": 0.15, "off_peak_pct": 0.15},
    },

    "Hotel-2": {
        "name": "Hotel Bulk Low Voltage (H-2)",
        "type": "bulk_tou",
        "description": "Hotel bulk supply metered at 400/230V, contract demand > 42 kVA.",
        "is_bulk": True,
        "requires_demand": True,
        "requires_tou": True,
        "day_rate_lkr": 18.0,
        "peak_rate_lkr": 35.0,
        "off_peak_rate_lkr": 15.0,
        "fixed_charge_lkr": 5000.0,
        "demand_charge_lkr_per_kva": 1400.0,
        "default_distribution": {"day_pct": 0.60, "peak_pct": 0.20, "off_peak_pct": 0.20},
    },

    "Hotel-3": {
        "name": "Hotel Bulk Medium Voltage (H-3)",
        "type": "bulk_tou",
        "description": "Hotel bulk supply metered at 11 kV / 33 kV medium voltage.",
        "is_bulk": True,
        "requires_demand": True,
        "requires_tou": True,
        "day_rate_lkr": 17.0,
        "peak_rate_lkr": 34.0,
        "off_peak_rate_lkr": 14.0,
        "fixed_charge_lkr": 5000.0,
        "demand_charge_lkr_per_kva": 1350.0,
        "default_distribution": {"day_pct": 0.60, "peak_pct": 0.20, "off_peak_pct": 0.20},
    },

    "Government-2": {
        "name": "Government Bulk Low Voltage (GV-2)",
        "type": "bulk_tou",
        "description": "Government bulk supply metered at 400/230V, contract demand > 42 kVA.",
        "is_bulk": True,
        "requires_demand": True,
        "requires_tou": True,
        "day_rate_lkr": 22.0,
        "peak_rate_lkr": 40.0,
        "off_peak_rate_lkr": 16.0,
        "fixed_charge_lkr": 5000.0,
        "demand_charge_lkr_per_kva": 1400.0,
        "default_distribution": {"day_pct": 0.70, "peak_pct": 0.15, "off_peak_pct": 0.15},
    },

    "Government-3": {
        "name": "Government Bulk Medium Voltage (GV-3)",
        "type": "bulk_tou",
        "description": "Government bulk supply metered at 11 kV / 33 kV medium voltage.",
        "is_bulk": True,
        "requires_demand": True,
        "requires_tou": True,
        "day_rate_lkr": 21.0,
        "peak_rate_lkr": 38.0,
        "off_peak_rate_lkr": 15.0,
        "fixed_charge_lkr": 5000.0,
        "demand_charge_lkr_per_kva": 1350.0,
        "default_distribution": {"day_pct": 0.70, "peak_pct": 0.15, "off_peak_pct": 0.15},
    },

    # -----------------------------------------------------------------------
    # 3. ELECTRIC VEHICLE CHARGING STATIONS (EVCS)
    # -----------------------------------------------------------------------
    "EVCS-1": {
        "name": "EV Charging Station Retail (EVCS-1)",
        "type": "tou",
        "description": "Dedicated EV charging supply (400/230V, contract demand <= 42 kVA). Level 2 AC.",
        "is_bulk": False,
        "requires_demand": False,
        "requires_tou": True,
        "day_rate_lkr": 70.0,
        "peak_rate_lkr": 90.0,
        "off_peak_rate_lkr": 40.0,
        "fixed_charge_lkr": 2000.0,
        "default_distribution": {"day_pct": 0.40, "peak_pct": 0.10, "off_peak_pct": 0.50},
    },

    "EVCS-2": {
        "name": "EV Charging Station Bulk (EVCS-2)",
        "type": "bulk_tou",
        "description": "Dedicated EV charging bulk supply (> 42 kVA) for DC Fast Charging.",
        "is_bulk": True,
        "requires_demand": True,
        "requires_tou": True,
        "day_rate_lkr": 85.0,
        "peak_rate_lkr": 108.0,
        "off_peak_rate_lkr": 50.0,
        "fixed_charge_lkr": 5000.0,
        "demand_charge_lkr_per_kva": 1400.0,
        "default_distribution": {"day_pct": 0.40, "peak_pct": 0.10, "off_peak_pct": 0.50},
    }
}


def get_tariff_categories() -> list:
    """Return ordered list of tariff category keys."""
    return list(TARIFF_CONFIG.keys())


def get_tariff_info(category_key: str) -> Dict[str, Any]:
    """Retrieve full configuration dictionary for a given tariff category."""
    return TARIFF_CONFIG.get(category_key, TARIFF_CONFIG["Domestic"])


def get_net_plus_rate() -> float:
    """Return configured Net Plus feed-in export tariff rate."""
    return float(SOLAR_CONFIG.get("net_plus_export_rate_lkr", 19.0))


def set_net_plus_rate(new_rate: float) -> None:
    """Admin-only: update Net Plus export rate dynamically."""
    if new_rate > 0:
        SOLAR_CONFIG["net_plus_export_rate_lkr"] = float(new_rate)


def get_default_generation_per_kw() -> float:
    """Return project benchmark monthly generation per kW (default 120 kWh/kW/month)."""
    return float(SOLAR_CONFIG.get("default_generation_per_kw_month", 120.0))
