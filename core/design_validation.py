"""
core/design_validation.py — Central Multi-Disciplinary Design Validation Engine
Evaluates complete PV plant design against engineering limits, safety codes, and utility standards.
Produces 4-status health check matrix:
  - 🟢 PASS: Fully compliant with safety margins
  - 🟡 WARNING: Within limits but near threshold or power clipping active
  - 🔴 FAIL: Exceeds electrical, thermal, or physical safety ceilings
  - 🔵 MANUAL REVIEW: Requires utility discretion or custom engineering approval (>40kW metering, non-standard switchgear)
Authored by Eng. Aashir © 2026.
"""
from typing import Dict, List, Any
from .string_sizing import rnd


def validate_design(design_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validates a complete PV design against engineering limits and utility rules.
    Returns list of validation items with 4 distinct statuses: PASS, WARNING, FAIL, MANUAL_REVIEW.
    """
    if not design_params or not isinstance(design_params, dict):
        return []
    items = []
    
    # 1. Standard Numerical Safety Checks
    checks = [
        ('String Cold Voc', 'string_voc_cold_v', 'inverter_max_dc_v', '<=', 'V', 'Cold string voltage exceeds inverter maximum DC input voltage.', 'Reduce panels per string or select higher voltage inverter chassis.'),
        ('String Hot Vmp (min)', 'string_vmp_hot_v', 'inverter_mppt_min_v', '>=', 'V', 'Hot string voltage is below MPPT lower tracking boundary.', 'Add more panels per string or select inverter with lower MPPT start voltage.'),
        ('String Cold Vmp (max)', 'string_vmp_cold_v', 'inverter_mppt_max_v', '<=', 'V', 'Cold string tracking voltage exceeds MPPT upper limit.', 'Reduce panels per string.'),
        ('MPPT Isc Current', 'mppt_isc_a', 'inverter_max_isc_per_mppt_a', '<=', 'A', 'Array short-circuit current exceeds MPPT hardware damage limit.', 'Reduce paralleled strings per MPPT tracker.'),
        ('MPPT Operating Imp', 'dc_operating_current_a', 'inverter_max_input_current_a', '<=', 'A', 'Operating Imp exceeds inverter nominal current rating; clipping will occur.', 'Check inverter datasheet power clipping limits.'),
        ('DC/AC Ratio', 'dc_ac_ratio', 'dc_ac_ratio_max', '<=', '', 'DC/AC ratio exceeds maximum allowable inverter overload ratio.', 'Increase inverter AC capacity or reduce DC array size.'),
        ('DC Cable Voltage Drop', 'dc_voltage_drop_pct', None, '<=3.0', '%', 'DC voltage drop exceeds 3.0% maximum allowable loss.', 'Upsize DC solar cable CSA or relocate inverter closer to array.'),
        ('AC Cable Voltage Drop', 'ac_voltage_drop_pct', None, '<=3.0', '%', 'AC voltage drop exceeds 3.0% maximum allowable loss.', 'Upsize AC XLPE/PVC cable CSA or shorten run length to switchboard.'),
        ('Earthing Resistance', 'earth_resistance_ohm', 'target_earth_resistance_ohm', '<=', 'Ω', 'Grounding resistance exceeds allowable maximum limit.', 'Add additional earth rods or treat soil.'),
        ('Performance Ratio (PR)', 'performance_ratio_pct', 'min_pr_pct', '>=', '%', 'System Performance Ratio is below recommended 75% benchmark.', 'Investigate excessive thermal, shading, or cable resistance losses.'),
    ]

    for check_name, actual_key, limit_key, operator, unit, fail_reason, action in checks:
        actual = design_params.get(actual_key)
        if actual is None:
            continue
        if isinstance(actual, (tuple, list)):
            actual = actual[0]
        try:
            actual = float(actual)
        except (ValueError, TypeError):
            continue

        if limit_key:
            limit = design_params.get(limit_key)
            if limit is None:
                continue
            if isinstance(limit, (tuple, list)):
                limit = limit[0]
            try:
                limit = float(limit)
            except (ValueError, TypeError):
                continue
        else:
            limit = float(operator.replace('<=', '').replace('>=', ''))
            operator = '<=' if '<=' in operator else '>='

        if operator == '<=':
            if actual <= limit:
                ratio = actual / limit if limit != 0 else 0
                if ratio >= 0.90:
                    status = 'WARNING'
                    reason = f'{check_name} at {rnd(ratio*100, 1)}% of limit — close to threshold.'
                else:
                    status = 'PASS'
                    reason = f'{check_name} within safe engineering limit.'
            else:
                status = 'FAIL'
                reason = fail_reason
        elif operator == '>=':
            if actual >= limit:
                status = 'PASS'
                reason = f'{check_name} satisfies minimum engineering criterion.'
            else:
                status = 'FAIL'
                reason = fail_reason
        else:
            status = 'PASS'
            reason = ''

        deviation = rnd(actual - limit, 3) if limit else ''
        items.append({
            'parameter': check_name,
            'actual_value': f'{actual} {unit}'.strip(),
            'allowed_value': f'{operator} {limit} {unit}'.strip(),
            'deviation': f'{deviation} {unit}'.strip() if deviation != '' else '',
            'status': status,
            'reason': reason,
            'recommended_action': action if status in ('FAIL', 'WARNING') else '',
        })

    # 2. Utility Net Metering Rule Check (>40 kW requires MANUAL_REVIEW)
    actual_ac = design_params.get('actual_ac_kw') or design_params.get('target_ac_kw')
    if actual_ac is not None:
        if actual_ac > 40.0:
            items.append({
                'parameter': 'Utility Net Metering Policy',
                'actual_value': f'{actual_ac:.1f} kW',
                'allowed_value': '<= 40.0 kW (Standard Metering)',
                'deviation': f'+{actual_ac - 40.0:.1f} kW',
                'status': 'MANUAL_REVIEW',
                'reason': 'System capacity exceeds 40 kW threshold — formal CEB / Utility interconnection assessment and custom meter allocation required.',
                'recommended_action': 'Submit formal application to utility transmission/distribution engineers. Do not assume automated meter sizing.'
            })
        else:
            items.append({
                'parameter': 'Utility Net Metering Policy',
                'actual_value': f'{actual_ac:.1f} kW',
                'allowed_value': '<= 40.0 kW (Standard Metering)',
                'deviation': '',
                'status': 'PASS',
                'reason': 'Standard installer net metering scheme applies (COMPANY_STANDARD).',
                'recommended_action': ''
            })

    # 3. DC Switchgear Availability Check
    dc_iso_status = design_params.get('dc_isolator_status')
    if dc_iso_status == 'MANUAL_REVIEW':
        items.append({
            'parameter': 'DC Isolator Equipment Availability',
            'actual_value': 'Custom / High Voltage',
            'allowed_value': 'Master Catalog Match',
            'deviation': 'Non-catalog',
            'status': 'MANUAL_REVIEW',
            'reason': 'No suitable DC isolator found in master catalog for string voltage/amperage.',
            'recommended_action': 'Perform engineering review to source custom DC switchgear.'
        })

    # 4. Utility Lockable Isolator Check
    lock_iso_status = design_params.get('lockable_isolator_status')
    if lock_iso_status == 'MANUAL_REVIEW':
        items.append({
            'parameter': 'Utility Lockable Isolator Availability',
            'actual_value': 'Custom High Amperage',
            'allowed_value': 'Master Catalog Match',
            'deviation': 'Non-catalog',
            'status': 'MANUAL_REVIEW',
            'reason': 'No standard padlockable utility disconnect found for this current rating.',
            'recommended_action': 'Consult utility interconnection engineer for MCCB with padlock attachment.'
        })

    return items


def get_overall_status(validation_items: List[Dict[str, Any]]) -> str:
    """
    Computes overall design validation health:
    Priority: FAIL > MANUAL_REVIEW > WARNING > PASS
    """
    if any(item['status'] == 'FAIL' for item in validation_items):
        return 'FAIL'
    if any(item['status'] == 'MANUAL_REVIEW' for item in validation_items):
        return 'MANUAL_REVIEW'
    if any(item['status'] == 'WARNING' for item in validation_items):
        return 'WARNING'
    return 'PASS'


def validate_engineering_consistency(
    calculated_data: Dict[str, Any],
    sld_data: Dict[str, Any]
) -> List[str]:
    """
    Validates 100% consistency and Single Source of Truth between calculated engineering data
    and Single Line Diagram (SLD) data structure.
    Checks:
      - System AC Capacity & DC Capacity
      - Total Modules and Total Strings
      - Inverter fleet count, capacities, and models
      - Per-inverter AC cable cross-section (CSA)
      - Per-inverter AC breaker specification and rating
      - Inverter DC solar cable CSA
      - Inverter chassis earthing conductor CSA
      - Main plant AC export cable CSA and specification
      - Main system circuit breaker specification and rating
      - Central AC busbar current rating
      - Main protective earthing conductor CSA
    Returns:
      List of discrepancy error messages. An empty list [] indicates 100% consistency.
    """
    errors = []

    # Handle unified dataset vs dynamic_system structure
    if "per_inverter_designs" in calculated_data:
        per_inv = calculated_data.get("per_inverter_designs", [])
        whole_ac = calculated_data.get("whole_system_ac", {})
        earthing = calculated_data.get("earthing_design", {})
        total_ac = float(calculated_data.get("actual_ac_kw", 0.0))
        total_dc = float(calculated_data.get("actual_dc_kwp", 0.0))
        total_panels = int(calculated_data.get("total_panels", 0))
        total_strings = int(calculated_data.get("total_strings", 0))
    elif "inverter_infrastructure" in calculated_data:
        per_inv = calculated_data.get("inverter_infrastructure", {}).get("per_inverter_designs", [])
        whole_ac = calculated_data.get("whole_system_ac", {})
        earthing = calculated_data.get("earthing_system", {})
        total_ac = float(calculated_data.get("inverter_infrastructure", {}).get("actual_ac_kw", 0.0))
        total_dc = float(calculated_data.get("pv_subsystem", {}).get("installed_dc_kwp", 0.0))
        total_panels = int(calculated_data.get("pv_subsystem", {}).get("total_panels", 0))
        total_strings = int(calculated_data.get("pv_subsystem", {}).get("total_strings", 0))
    else:
        per_inv = []
        whole_ac = calculated_data.get("whole_system_ac", {})
        earthing = calculated_data.get("earthing", {})
        total_ac = float(calculated_data.get("actual_ac_kw", 0.0))
        total_dc = float(calculated_data.get("actual_dc_kwp", 0.0))
        total_panels = int(calculated_data.get("panel_qty", calculated_data.get("total_panels", 0)))
        total_strings = int(calculated_data.get("total_strings", 0))

    sld_meta = sld_data.get("system_meta", {})
    sld_inverters = sld_data.get("inverters", [])
    sld_main_sw = sld_data.get("main_switchgear", {})
    sld_busbar = sld_data.get("busbar", {})
    sld_earthing = sld_data.get("earthing", {})

    # 1. Capacity & Array Consistency
    if sld_meta:
        sld_cap = float(sld_meta.get("capacity_kw", 0.0))
        if total_ac > 0 and abs(sld_cap - total_ac) > 0.01:
            errors.append(f"Capacity mismatch: calculated {total_ac:.1f} kW AC != SLD {sld_cap:.1f} kW AC")

        sld_panels = int(sld_meta.get("total_modules", 0))
        if total_panels > 0 and sld_panels != total_panels:
            errors.append(f"Module count mismatch: calculated {total_panels} != SLD {sld_panels}")

        sld_strings = int(sld_meta.get("total_strings", 0))
        if total_strings > 0 and sld_strings != total_strings:
            errors.append(f"String count mismatch: calculated {total_strings} != SLD {sld_strings}")

    # 2. Inverter Count & Sizing Consistency
    if len(per_inv) != len(sld_inverters):
        errors.append(f"Inverter count mismatch: calculated {len(per_inv)} unit(s) != SLD {len(sld_inverters)} unit(s)")
    else:
        for idx, (calc_d, sld_inv) in enumerate(zip(per_inv, sld_inverters)):
            inv_num = idx + 1
            calc_inv = calc_d["inverter"]
            sld_kw = float(sld_inv.get("capacity_kw", sld_inv.get("rated_kw", 0.0)))
            if abs(calc_inv.rated_ac_power_kw - sld_kw) > 0.01:
                errors.append(f"Inverter #{inv_num} capacity mismatch: calculated {calc_inv.rated_ac_power_kw:.1f}kW != SLD {sld_kw:.1f}kW")

            # AC Cable
            calc_ac_csa = float(calc_d.get("ac_cable_csa_mm2", 0.0))
            sld_ac_csa = float(sld_inv.get("ac_cable_csa", 0.0))
            if calc_ac_csa > 0 and sld_ac_csa > 0 and abs(calc_ac_csa - sld_ac_csa) > 0.01:
                errors.append(f"Inverter #{inv_num} AC cable CSA mismatch: calculated {calc_ac_csa}mm² != SLD {sld_ac_csa}mm²")

            # AC Breaker
            calc_brk_a = calc_d.get("ac_breaker_rating_a")
            sld_brk_a = sld_inv.get("ac_mcb_a")
            if calc_brk_a and sld_brk_a and int(calc_brk_a) != int(sld_brk_a):
                errors.append(f"Inverter #{inv_num} AC breaker rating mismatch: calculated {calc_brk_a}A != SLD {sld_brk_a}A")

            # DC Cable
            calc_dc_csa = float(calc_d.get("dc_cable_csa_mm2", 0.0))
            sld_dc_csa = float(sld_inv.get("dc_cable_csa", 0.0))
            if calc_dc_csa > 0 and sld_dc_csa > 0 and abs(calc_dc_csa - sld_dc_csa) > 0.01:
                errors.append(f"Inverter #{inv_num} DC cable CSA mismatch: calculated {calc_dc_csa}mm² != SLD {sld_dc_csa}mm²")

            # Chassis Earth
            calc_pe = float(calc_d.get("inverter_pe_csa_mm2", calc_d.get("earth_conductor_csa_mm2", 0.0)))
            sld_pe = float(sld_inv.get("chassis_earth_csa", 0.0))
            if calc_pe > 0 and sld_pe > 0 and abs(calc_pe - sld_pe) > 0.01:
                errors.append(f"Inverter #{inv_num} Chassis earth CSA mismatch: calculated {calc_pe}mm² != SLD {sld_pe}mm²")

    # 3. Main Switchgear & Cable Consistency
    calc_main_csa = float(whole_ac.get("main_cable_csa_mm2", 0.0))
    sld_main_csa = float(sld_main_sw.get("main_cable_csa_mm2", sld_main_sw.get("main_cable_csa", 0.0)))
    if calc_main_csa > 0 and sld_main_csa > 0 and abs(calc_main_csa - sld_main_csa) > 0.01:
        errors.append(f"Main AC export cable CSA mismatch: calculated {calc_main_csa}mm² != SLD {sld_main_csa}mm²")

    calc_main_brk_a = whole_ac.get("main_breaker_rating_a")
    sld_main_brk_a = sld_main_sw.get("main_breaker_rating_a")
    if calc_main_brk_a and sld_main_brk_a and int(calc_main_brk_a) != int(sld_main_brk_a):
        errors.append(f"Main AC breaker rating mismatch: calculated {calc_main_brk_a}A != SLD {sld_main_brk_a}A")

    # 4. Busbar Consistency
    calc_bb_rating = whole_ac.get("main_busbar_rating_a")
    sld_bb_rating = sld_busbar.get("rating_a")
    if calc_bb_rating and sld_bb_rating and int(calc_bb_rating) != int(sld_bb_rating):
        errors.append(f"Busbar rating mismatch: calculated {calc_bb_rating}A != SLD {sld_bb_rating}A")

    # 5. Main Earthing Conductor Consistency
    calc_main_earth = float(earthing.get("main_earth_conductor_csa_mm2", 0.0))
    sld_main_earth = float(sld_earthing.get("conductor_csa", 0.0))
    if calc_main_earth > 0 and sld_main_earth > 0 and abs(calc_main_earth - sld_main_earth) > 0.01:
        errors.append(f"Main earth conductor CSA mismatch: calculated {calc_main_earth}mm² != SLD {sld_main_earth}mm²")

    return errors


def validate_design_prerequisites(dataset: Dict[str, Any]) -> List[str]:
    """
    Validates design prerequisites before SLD, BOM, or Proposal generation.
    Enforces that all engineering dependencies are resolved and non-empty.
    Returns:
      List of missing prerequisite error messages. Empty list [] means all prerequisites are met.
    """
    errors = []
    if not dataset or not isinstance(dataset, dict):
        return ["Project design dataset is not initialized."]

    # 1. Capacity
    pv = dataset.get("pv_subsystem", {})
    ac_kw = float(dataset.get("inverter_infrastructure", {}).get("actual_ac_kw", pv.get("installed_dc_kwp", 0.0)))
    if ac_kw <= 0:
        errors.append("System capacity is missing or <= 0 kW.")

    # 2. Panel Data
    panel = pv.get("panel")
    if not panel:
        errors.append("PV module specifications are missing.")
    elif getattr(panel, "rated_power_wp", 0) <= 0:
        errors.append("PV module rated power is zero or invalid.")

    # 3. Inverter Data
    inv_infra = dataset.get("inverter_infrastructure", {})
    per_inv = inv_infra.get("per_inverter_designs", [])
    if not per_inv:
        errors.append("Inverter fleet configuration is missing.")
    else:
        for idx, d in enumerate(per_inv):
            inv = d.get("inverter")
            if not inv or getattr(inv, "rated_ac_power_kw", 0) <= 0:
                errors.append(f"Inverter #{idx+1} model or AC capacity is invalid.")

    # 4. String Configuration
    total_panels = int(pv.get("total_panels", 0))
    total_strings = int(pv.get("total_strings", 0))
    if total_panels <= 0:
        errors.append("Total PV module quantity is zero.")
    if total_strings <= 0:
        errors.append("Array string count is zero.")

    # 5. Cable Sizing Completed
    whole_ac = dataset.get("whole_system_ac", {})
    main_cbl = whole_ac.get("main_cable_csa_mm2", 0.0)
    if not main_cbl or float(main_cbl) <= 0:
        errors.append("Main AC export cable sizing has not been completed.")

    for idx, d in enumerate(per_inv):
        if not d.get("dc_cable_csa_mm2") or float(d["dc_cable_csa_mm2"]) <= 0:
            errors.append(f"Inverter #{idx+1} DC string cable sizing has not been completed.")
        if not d.get("ac_cable_csa_mm2") or float(d["ac_cable_csa_mm2"]) <= 0:
            errors.append(f"Inverter #{idx+1} AC cable sizing has not been completed.")

    # 6. Protection Selection Completed
    main_brk = whole_ac.get("main_breaker_rating_a")
    if not main_brk or int(main_brk) <= 0:
        errors.append("Main AC circuit breaker selection has not been completed.")

    for idx, d in enumerate(per_inv):
        if not d.get("ac_breaker_rating_a") or int(d["ac_breaker_rating_a"]) <= 0:
            errors.append(f"Inverter #{idx+1} AC breaker selection has not been completed.")

    # 7. Busbar Selection Completed
    bb_rating = whole_ac.get("main_busbar_rating_a")
    if not bb_rating or int(bb_rating) <= 0:
        errors.append("Busbar selection cannot be completed because AC design current has not been calculated.")

    return errors


