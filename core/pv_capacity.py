"""
PV System Capacity Calculator.
Calculates required DC system size from annual energy target and site conditions.
Formula: P_dc = E_yr / (365 × PSH × PR × (1 - shading/100)) [kWp]
"""
import math
from .string_sizing import rnd


def calculate_pv_capacity(annual_energy_kwh, peak_sun_hours, performance_ratio=0.78,
                          shading_loss_pct=0.0):
    """
    Calculate required DC peak power from annual energy demand.

    Parameters
    ----------
    annual_energy_kwh  : float — target annual AC energy output (kWh/year)
    peak_sun_hours     : float — average daily peak sun hours (h/day) at tilt
    performance_ratio  : float — system performance ratio (0–1), default 0.78
    shading_loss_pct   : float — shading loss percentage (0–100), default 0.0

    Returns
    -------
    dict with dc_capacity_kwp, daily_energy_kwh, status, warnings, show_calculation
    """
    warnings = []

    if peak_sun_hours <= 0:
        return {
            'dc_capacity_kwp': 0.0,
            'daily_energy_kwh': 0.0,
            'performance_ratio': performance_ratio,
            'status': 'FAIL',
            'warnings': ['Peak sun hours must be greater than 0'],
            'show_calculation': {},
        }

    if performance_ratio <= 0 or performance_ratio > 1.0:
        return {
            'dc_capacity_kwp': 0.0,
            'daily_energy_kwh': 0.0,
            'performance_ratio': performance_ratio,
            'status': 'FAIL',
            'warnings': ['Performance ratio must be between 0 and 1'],
            'show_calculation': {},
        }

    if performance_ratio > 0.85:
        warnings.append(f'PR of {performance_ratio:.0%} is very high — verify assumptions. '
                        'Typical range: 0.70–0.82 for ground mount, 0.65–0.78 for rooftop.')

    shading_factor = 1.0 - (shading_loss_pct / 100.0)
    effective_psh = peak_sun_hours * shading_factor
    dc_capacity_kwp = annual_energy_kwh / (365.0 * peak_sun_hours * performance_ratio * shading_factor)
    dc_capacity_kwp = rnd(dc_capacity_kwp, 2)
    daily_energy_kwh = rnd(annual_energy_kwh / 365.0, 1)

    status = 'WARNING' if warnings else 'PASS'

    return {
        'dc_capacity_kwp': dc_capacity_kwp,
        'daily_energy_kwh': daily_energy_kwh,
        'performance_ratio': performance_ratio,
        'status': status,
        'warnings': warnings,
        'show_calculation': {
            'formula': 'P_dc = E_yr / (365 × PSH × PR × (1 - shading%))',
            'annual_energy_kwh': annual_energy_kwh,
            'peak_sun_hours': peak_sun_hours,
            'performance_ratio': performance_ratio,
            'shading_loss_pct': shading_loss_pct,
            'shading_factor': rnd(shading_factor, 4),
            'effective_psh': rnd(effective_psh, 3),
            'dc_capacity_kwp': dc_capacity_kwp,
            'daily_energy_kwh': daily_energy_kwh,
        },
    }
