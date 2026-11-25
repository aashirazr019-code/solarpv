"""
Input & Compatibility Validation Module for Solar PV Systems.
Provides deterministic engineering checks against physical constraints and manufacturer ratings.
"""
from typing import List, Optional


def validate_positive(value, name: str, allow_zero: bool = False) -> Optional[str]:
    """Check that numeric value is positive."""
    if value is None:
        return f"{name} cannot be None."
    if allow_zero and value < 0:
        return f"{name} cannot be negative (got {value})."
    if not allow_zero and value <= 0:
        return f"{name} must be greater than zero (got {value})."
    return None


def validate_range(value, min_val, max_val, name: str) -> Optional[str]:
    """Check that value lies within [min_val, max_val]."""
    if value is None:
        return f"{name} cannot be None."
    if not (min_val <= value <= max_val):
        return f"{name} ({value}) must be within range [{min_val}, {max_val}]."
    return None


def validate_panel(panel) -> List[str]:
    """
    Validates physical feasibility of PV Module specifications.
    Enforces basic semiconductor physics: Vmp < Voc and Imp < Isc.
    """
    errors = []
    if panel.rated_power_wp <= 0:
        errors.append(f"Rated power must be positive (got {panel.rated_power_wp}Wp).")
    if panel.voc <= 0:
        errors.append(f"Open-circuit voltage Voc must be positive (got {panel.voc}V).")
    if panel.vmp <= 0:
        errors.append(f"Max power voltage Vmp must be positive (got {panel.vmp}V).")
    if panel.vmp >= panel.voc:
        errors.append(f"Physics violation: Vmp ({panel.vmp}V) must be less than Voc ({panel.voc}V).")
    if panel.isc <= 0:
        errors.append(f"Short-circuit current Isc must be positive (got {panel.isc}A).")
    if panel.imp <= 0:
        errors.append(f"Max power current Imp must be positive (got {panel.imp}A).")
    if panel.imp >= panel.isc:
        errors.append(f"Physics violation: Imp ({panel.imp}A) must be less than Isc ({panel.isc}A).")
    if panel.max_system_voltage <= 0:
        errors.append("Max system voltage must be positive.")
    if panel.temp_coeff_voc >= 0:
        errors.append("Voc temperature coefficient must be negative for silicon cells (%/°C).")
    return errors


def validate_inverter(inverter) -> List[str]:
    """
    Validates Inverter specifications against operating constraints.
    """
    errors = []
    if inverter.rated_ac_power_kw <= 0:
        errors.append("Inverter rated AC power must be positive.")
    if inverter.max_dc_voltage_v <= 0:
        errors.append("Max DC voltage must be positive.")
    if inverter.mppt_voltage_min_v >= inverter.mppt_voltage_max_v:
        errors.append(f"MPPT min voltage ({inverter.mppt_voltage_min_v}V) must be less than MPPT max voltage ({inverter.mppt_voltage_max_v}V).")
    if inverter.mppt_voltage_max_v > inverter.max_dc_voltage_v:
        errors.append("MPPT max voltage cannot exceed inverter absolute maximum DC voltage.")
    if inverter.mppt_count <= 0:
        errors.append("MPPT tracker count must be at least 1.")
    if inverter.efficiency_pct <= 0 or inverter.efficiency_pct > 100:
        errors.append(f"Efficiency must be between 0 and 100% (got {inverter.efficiency_pct}%).")
    return errors


def validate_project(project) -> List[str]:
    """
    Validates design parameters of a Project.
    """
    errors = []
    if project.target_ac_capacity_kw <= 0:
        errors.append("Target AC capacity must be positive.")
    if project.min_design_temp_c >= project.max_design_temp_c:
        errors.append(f"Min design temp ({project.min_design_temp_c}°C) must be less than max design temp ({project.max_design_temp_c}°C).")
    if not (project.dc_ac_ratio_min <= project.dc_ac_ratio_preferred <= project.dc_ac_ratio_max):
        errors.append(f"DC/AC ratio configuration must satisfy min <= preferred <= max.")
    return errors


def validate_panel_inverter_compatibility(panel, inverter, project) -> List[str]:
    """
    Performs preliminary compatibility check between panel and inverter.
    """
    errors = []
    from .string_sizing import cold_voc, hot_vmp
    
    voc_c = cold_voc(panel, project.min_design_temp_c)
    if voc_c > inverter.max_dc_voltage_v:
        errors.append(f"Single module cold Voc ({voc_c}V) exceeds inverter max DC limit ({inverter.max_dc_voltage_v}V).")
        
    vmp_h, _ = hot_vmp(panel, project.max_design_temp_c)
    if vmp_h > inverter.mppt_voltage_max_v:
        errors.append(f"Single module hot Vmp ({vmp_h}V) exceeds inverter MPPT max voltage ({inverter.mppt_voltage_max_v}V).")
        
    if panel.isc > inverter.max_isc_per_mppt_a:
        errors.append(f"Single string Isc ({panel.isc}A) exceeds MPPT max short-circuit current ({inverter.max_isc_per_mppt_a}A).")
        
    return errors
