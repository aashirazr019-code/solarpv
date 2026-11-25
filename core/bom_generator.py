"""
core/bom_generator.py — Engineering Bill of Materials (BoQ) Generator
Generates itemized Bill of Materials directly from calculated design parameters and master catalog rules.
Every line item is attributed to an explicit rule source:
- "CEB_REQUIRED"
- "ENGINEERING_RULE"
- "COMPANY_STANDARD"
- "INSTALLER_RULE"
- "MANUAL_REVIEW_REQUIRED"
- "USER_DEFINED"
Authored by Eng. Aashir © 2026.
"""
from typing import Dict, List, Optional, Any
from .models import BOMItem
from .master_data import (
    RULE_SOURCE_CEB,
    RULE_SOURCE_ENGINEERING,
    RULE_SOURCE_COMPANY,
    RULE_SOURCE_INSTALLER,
    RULE_SOURCE_MANUAL_REVIEW,
    RULE_SOURCE_USER
)


def generate_bom(
    panel,
    inverter_breakdown,
    design_result: Dict[str, Any],
    project: Any = None,
    dc_cable_csa: Optional[float] = None,
    ac_cable_csa: Optional[float] = None,
    dc_cable_length_per_string_m: Optional[float] = None,
    ac_cable_length_per_inverter_m: Optional[float] = None,
    mcb_rating: Optional[float] = None,
    mccb_rating: Optional[float] = None,
    busbar_rating: Optional[float] = None,
    earth_rods: Optional[int] = None,
    earth_conductor_csa: Optional[float] = None,
    strings_per_mppt: int = 1,
    dc_isolator_qty: Optional[int] = None,
    meter_info: Optional[Dict[str, Any]] = None,
    lockable_isolator_info: Optional[Dict[str, Any]] = None
) -> List[BOMItem]:
    """
    Generates a complete, standards-compliant Bill of Materials (BoQ).
    inverter_breakdown: list of {"inverter": Inverter, "quantity": int}
    design_result: dict with panel_qty, strings_total, panels_per_string
    """
    items = []

    total_panels = design_result.get('panel_qty', design_result.get('total_panels', 0))
    total_strings = design_result.get('strings_total', design_result.get('total_strings', 0))
    total_inverter_units = sum(b['quantity'] for b in inverter_breakdown)
    
    # 1. PV Modules
    if total_panels > 0:
        items.append(BOMItem(
            category='Module', item_name='Solar PV Module',
            manufacturer=panel.manufacturer, model=panel.model,
            description=f'{panel.rated_power_wp}Wp {panel.cell_technology}',
            quantity=total_panels, unit='nos',
            specification=f'Voc={panel.voc}V, Vmp={panel.vmp}V, Isc={panel.isc}A, Imp={panel.imp}A ({panel.length_m}x{panel.width_m}m)',
            source=f'Array sizing: {total_strings} strings × {design_result.get("panels_per_string", 0)} modules',
            rule_source=RULE_SOURCE_COMPANY,
        ))

    # 2. Inverters
    for b in inverter_breakdown:
        inv = b['inverter']
        qty = b['quantity']
        if qty > 0:
            items.append(BOMItem(
                category='Inverter', item_name='Grid-tie Inverter',
                manufacturer=inv.manufacturer, model=inv.model,
                description=f'{inv.rated_ac_power_kw}kW 3-Phase Inverter',
                quantity=qty, unit='nos',
                specification=f'DC Max: {inv.max_dc_voltage_v}V, MPPT: {inv.mppt_voltage_min_v}-{inv.mppt_voltage_max_v}V ({inv.mppt_count} MPPTs), AC: {inv.ac_voltage}V',
                source='Inverter capacity sizing & combination optimization',
                rule_source=RULE_SOURCE_COMPANY,
            ))

    # 3. DC String Solar Cable (Positive + Negative run per string)
    csa_dc = dc_cable_csa or 6.0
    len_dc = dc_cable_length_per_string_m or 25.0
    if total_strings > 0:
        dc_total_length = round(total_strings * len_dc * 2, 0)
        items.append(BOMItem(
            category='Cable', item_name='DC Solar Cable (1500V DC)',
            manufacturer='Kelani Cables / Equivalent',
            model='H1Z2Z2-K',
            description=f'{csa_dc}mm² Cross-Linked Halogen-Free Solar DC Cable',
            quantity=dc_total_length, unit='m',
            specification=f'{csa_dc}mm² Tinned Copper, 1.5kV DC rated, UV resistant',
            source=f'{total_strings} strings × {len_dc}m per string × 2 (positive + negative)',
            notes='Indicative cable run length. Verify final run length after site cable routing.',
            rule_source=RULE_SOURCE_ENGINEERING,
        ))

    # 4. AC Output Multicore Cable
    csa_ac = ac_cable_csa or (150.0 if sum(b['inverter'].rated_ac_power_kw * b['quantity'] for b in inverter_breakdown) >= 100 else 35.0)
    len_ac = ac_cable_length_per_inverter_m or 15.0
    if total_inverter_units > 0:
        ac_total_length = round(total_inverter_units * len_ac, 0)
        items.append(BOMItem(
            category='Cable', item_name='AC Main Output Cable',
            manufacturer='Kelani Cables',
            model='BS 5467 / BS 6004',
            description=f'{csa_ac}mm² 4-Core Copper XLPE/SWA/PVC Cable',
            quantity=ac_total_length, unit='m',
            specification=f'{csa_ac}mm² 4-Core (3P + N), 600/1000V rated per BS 7671 Table A1',
            source=f'{total_inverter_units} inverters × {len_ac}m run length to AC distribution board',
            notes='Multicore cable ordered by continuous route run length.',
            rule_source=RULE_SOURCE_ENGINEERING,
        ))

    # 5. MC4 Connectors (1 positive + 1 negative pair per string)
    if total_strings > 0:
        items.append(BOMItem(
            category='Connector', item_name='MC4 Solar Connectors',
            manufacturer='Staubli / Compatible',
            model='MC4-Evo2',
            description='Male & Female MC4 Connector Pairs (1000V/1500V DC)',
            quantity=total_strings * 2, unit='pairs',
            specification='IP68, 30A rated, snap-in locking',
            source=f'{total_strings} strings × 2 (1 string-head pair + 1 inverter connection pair)',
            rule_source=RULE_SOURCE_INSTALLER,
        ))

    # 6. DC String Fuses (Per IEC 60269-6: Required when 3 or more strings connect to one MPPT)
    if strings_per_mppt >= 3 and total_strings > 0:
        fuse_rating = round(panel.isc * 1.5, 0)
        items.append(BOMItem(
            category='Protection', item_name='gPV DC String Fuse & Holder',
            manufacturer='Bussmann / Mersen',
            model='10x38mm gPV',
            description=f'{fuse_rating}A 1000V DC gPV Solar String Fuse with Finger-Safe Holder',
            quantity=total_strings * 2, unit='nos',
            specification=f'{fuse_rating}A, 1000V DC, 33kA breaking capacity (IEC 60269-6)',
            source=f'{total_strings} strings × 2 legs (pos + neg) required because strings/MPPT >= 3',
            rule_source=RULE_SOURCE_ENGINEERING,
        ))

    # 7. DC Isolator Switch (Company Policy: 1 per string)
    num_dc_isolators = dc_isolator_qty or total_strings
    if num_dc_isolators > 0:
        items.append(BOMItem(
            category='Protection', item_name='DC Load-Break Isolator Switch',
            manufacturer='Suntree / Projoy',
            model='SISO-2P-1000V-32A',
            description='Rotary DC Disconnect Isolator Switch (DC-PV2)',
            quantity=num_dc_isolators, unit='nos',
            specification='1000V DC, 32A, 2-Pole, lockable handle (IEC 60947-3)',
            source=f'Company Standard: 1 DC Isolator per string ({num_dc_isolators} strings = {num_dc_isolators} units)',
            rule_source=RULE_SOURCE_COMPANY,
        ))

    # 8. DC Surge Protection Device (SPD)
    if total_inverter_units > 0:
        items.append(BOMItem(
            category='Protection', item_name='DC Surge Arrester (SPD Type II)',
            manufacturer='Suntree / CITEL',
            model='MED-3P-1000V',
            description='Pluggable Type II DC Surge Protective Device',
            quantity=total_inverter_units, unit='nos',
            specification='Uc = 1000V DC, Imax = 40kA, Up <= 3.8kV (IEC 61643-31)',
            source='1 per inverter DC section',
            rule_source=RULE_SOURCE_ENGINEERING,
        ))

    # 9. Inverter AC Circuit Breaker (MCB / MCCB)
    if total_inverter_units > 0:
        ac_breaker_rating = mcb_rating or 63
        items.append(BOMItem(
            category='Protection', item_name='Inverter AC Output Breaker',
            manufacturer='Schneider Electric / ABB',
            model='Acti9 / Compact',
            description=f'3-Pole/4-Pole AC Circuit Breaker rated {ac_breaker_rating}A',
            quantity=total_inverter_units, unit='nos',
            specification=f'{ac_breaker_rating}A, 400V AC, coordinated per Ib <= In <= Iz',
            source='1 dedicated AC circuit breaker per inverter unit',
            rule_source=RULE_SOURCE_ENGINEERING,
        ))

    # 10. Main Incomer MCCB
    if mccb_rating:
        items.append(BOMItem(
            category='Protection', item_name='Main Incomer AC MCCB',
            manufacturer='Schneider Electric / ABB',
            model='Compact NSX / Tmax',
            description=f'Molded Case Circuit Breaker (MCCB) rated {mccb_rating}A',
            quantity=1, unit='nos',
            specification=f'{mccb_rating}A, 4-Pole, 36kA/50kA Icu fault breaking capacity',
            source='Main AC distribution board incomer isolation',
            rule_source=RULE_SOURCE_ENGINEERING,
        ))

    # 11. Utility Lockable Isolator Switch (CEB Required)
    lock_model = lockable_isolator_info.get("model", "LK-4P-63A") if lockable_isolator_info else "LK-4P-63A"
    lock_rating = lockable_isolator_info.get("rating", "63A 400V 4P") if lockable_isolator_info else "63A 400V 4P"
    items.append(BOMItem(
        category='Protection', item_name='Utility Lockable AC Isolator',
        manufacturer='Katko / Kraus & Naimer',
        model=lock_model,
        description=f'External Grid Isolation Switch ({lock_rating}) - Padlockable in OFF position',
        quantity=1, unit='nos',
        specification='IEC 60947-3, 4-Pole AC-23A, yellow-red padlockable handle',
        source='Utility point of common coupling grid disconnection requirement',
        rule_source=RULE_SOURCE_CEB,
    ))

    # 12. AC Surge Protection Device (SPD)
    items.append(BOMItem(
        category='Protection', item_name='AC Surge Arrester (SPD Type II)',
        manufacturer='Dehn / CITEL',
        model='Type II AC SPD 3P+N',
        description='Type II AC Surge Protection Device (4-Pole)',
        quantity=1, unit='nos',
        specification='Uc = 385V / 440V AC, Imax = 40kA (IEC 61643-11)',
        source='1 per main AC distribution board',
        rule_source=RULE_SOURCE_ENGINEERING,
    ))

    # 13. Residual Current Device (RCD Type B)
    items.append(BOMItem(
        category='Protection', item_name='Residual Current Device (Type B RCD)',
        manufacturer='Doepke / ABB',
        model='Type B RCD',
        description='Type B 300mA RCD for Fire Protection & DC Residual Detection',
        quantity=1, unit='nos',
        specification='300mA sensitivity, Type B per IEC 62423 for transformerless inverters',
        source='Mandatory for transformerless solar grid connections',
        rule_source=RULE_SOURCE_CEB,
    ))

    # 14. Utility Bi-directional Energy Metering System
    if meter_info:
        meter_src = meter_info.get("rule_source", RULE_SOURCE_COMPANY)
        items.append(BOMItem(
            category='Metering', item_name='Bi-directional Smart Net Meter',
            manufacturer='CEB Approved / Secure / EDMI',
            model=meter_info.get("meter_type", "Bi-directional Meter"),
            description=f'{meter_info.get("rating", "Standard")} Bi-directional Meter with Remote AMR',
            quantity=1, unit='set',
            specification=f'{meter_info.get("connection_type", "Direct")} - CT Ratio: {meter_info.get("ct_ratio", "N/A")}',
            source=f'Assigned under {meter_src}',
            rule_source=meter_src,
        ))

    # 15. Copper Busbar Set
    if busbar_rating:
        items.append(BOMItem(
            category='Distribution', item_name='Electrolytic Copper Busbar Set',
            manufacturer='Standard Switchgear',
            model='Cu-ETP',
            description=f'4-Bar Copper Busbar System rated {busbar_rating}A',
            quantity=1, unit='set',
            specification=f'{busbar_rating}A continuous rating, tinned copper (L1, L2, L3, N)',
            source='Calculated from total AC capacity with 1.25 safety factor',
            rule_source=RULE_SOURCE_ENGINEERING,
        ))

    # 16. Solar Mounting Structure Hardware
    if total_panels > 0:
        rail_length_m = round(total_panels * panel.width_m * 2 * 1.05, 1)
        mid_clamps = max(0, round((total_panels - total_strings) * 2))
        end_clamps = max(4, round(total_strings * 4))
        
        items.append(BOMItem(
            category='Structure', item_name='Anodized Aluminum Mounting Rails',
            manufacturer='Standard Racking',
            model='AL6005-T5',
            description='Extruded aluminum mounting profile with splice kits and roof fixings',
            quantity=rail_length_m, unit='m',
            specification='Alloy AL6005-T5, anodized 10µm+, wind load certified to 140 km/h',
            source=f'2 rails per module row × {total_panels} panels × {panel.width_m}m × 1.05 margin',
            rule_source=RULE_SOURCE_COMPANY,
        ))
        items.append(BOMItem(
            category='Structure', item_name='Module Fastening Clamps (Mid & End)',
            manufacturer='Standard Racking',
            model='SS304 / Aluminum',
            description=f'Module clamps: {mid_clamps} mid-clamps + {end_clamps} end-clamps with SS304 fasteners',
            quantity=mid_clamps + end_clamps, unit='sets',
            specification='SUS304 bolts + spring nuts, pre-assembled, grounding pins included',
            source=f'{mid_clamps} mid-clamps + {end_clamps} end-clamps',
            rule_source=RULE_SOURCE_INSTALLER,
        ))

    # 17. Earthing Materials (BS 7430 & CEB)
    num_rods = earth_rods or max(2, int(round(total_inverter_units * 1.5)))
    csa_earth = earth_conductor_csa or 70.0
    items.append(BOMItem(
        category='Earthing', item_name='Copper-Bonded Earth Rods',
        manufacturer='Furse / Wallis',
        model='ER-16-300',
        description='Copper-bonded steel earth electrodes (3.0m × 16mm)',
        quantity=num_rods, unit='nos',
        specification='3m length, 16mm diameter, 254µm copper coating per BS 7430',
        source=f'Earthing calculation for target ground resistance <= 5 Ohm ({num_rods} rods)',
        rule_source=RULE_SOURCE_CEB,
    ))
    items.append(BOMItem(
        category='Earthing', item_name='Main Earthing Bare Copper Conductor',
        manufacturer='Kelani Cables',
        model='Hard-Drawn Bare Cu',
        description=f'{csa_earth}mm² Bare Stranded Copper Earth Conductor',
        quantity=round(num_rods * 15.0 + 20.0, 0), unit='m',
        specification=f'{csa_earth}mm² stranded bare copper per BS 7430 fault clearing calculations',
        source=f'Electrode interconnection grid ({num_rods} rods × 15m spacing) + equipment bonding',
        rule_source=RULE_SOURCE_ENGINEERING,
    ))

    # 18. AC Distribution Board Enclosure
    items.append(BOMItem(
        category='Enclosure', item_name='AC Distribution Board (ACDB)',
        manufacturer='Hensel / ABB / Schneider',
        model='IP65 Weatherproof',
        description='AC combiner / sub-distribution board enclosure with transparent viewing door',
        quantity=1, unit='nos',
        specification='IP65, IK08 rated, UV stabilized polycarbonate / sheet steel, with gland plates',
        source='1 central AC distribution enclosure',
        rule_source=RULE_SOURCE_INSTALLER,
    ))

    return items
