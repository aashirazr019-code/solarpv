def calculate_system_losses(dc_capacity_kwp, peak_sun_hours, soiling_pct=2.0, temperature_loss_pct=5.0, dc_cable_loss_pct=1.0, inverter_efficiency_pct=98.0, ac_cable_loss_pct=0.5, availability_pct=99.0, shading_loss_pct=0.0, mismatch_loss_pct=2.0):
    """
    PR = (1-soil)×(1-temp)×(1-dc_cable)×(η_inv)×(1-ac_cable)×(1-avail_loss)×(1-shade)×(1-mismatch)
    E_annual = P_dc × PSH × 365 × PR [kWh/year]
    Specific Yield = E_annual / P_dc [kWh/kWp/year]
    """
    pr = (1 - soiling_pct/100) * (1 - temperature_loss_pct/100) * (1 - dc_cable_loss_pct/100) * \
         (inverter_efficiency_pct/100) * (1 - ac_cable_loss_pct/100) * (availability_pct/100) * \
         (1 - shading_loss_pct/100) * (1 - mismatch_loss_pct/100)
         
    annual_energy_kwh = dc_capacity_kwp * peak_sun_hours * 365 * pr
    specific_yield = annual_energy_kwh / dc_capacity_kwp if dc_capacity_kwp > 0 else 0
    
    return {
        "performance_ratio": round(pr, 4),
        "performance_ratio_pct": round(pr * 100.0, 2),
        "annual_energy_kwh": round(annual_energy_kwh, 1),
        "annual_energy_mwh": round(annual_energy_kwh / 1000.0, 2),
        "specific_yield": round(specific_yield, 1),
        "specific_yield_kwh_kwp": round(specific_yield, 1),
        "total_losses_pct": round((1.0 - pr) * 100.0, 2),
        "loss_breakdown": {
            "soiling": soiling_pct,
            "temperature": temperature_loss_pct,
            "dc_cable": dc_cable_loss_pct,
            "inverter": inverter_efficiency_pct,
            "ac_cable": ac_cable_loss_pct,
            "availability": availability_pct,
            "shading": shading_loss_pct,
            "mismatch": mismatch_loss_pct
        },
        "status": "PASS",
        "show_calculation": {
            "pr_formula": "Product of all (1 - loss) factors",
            "annual_energy_formula": "P_dc * PSH * 365 * PR",
            "specific_yield_formula": "Annual_Energy / P_dc"
        }
    }

