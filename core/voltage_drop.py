import math
from .electrical_data import COPPER_RESISTIVITY
from .string_sizing import rnd


def voltage_drop_dc(csa_mm2, current_a, length_m, nominal_voltage_v, conductor_temp_c=70):
    """
    DC Voltage Drop:
    ΔV = 2 × L × I × ρ(T) / S
    ρ(T) = ρ_20 × [1 + α × (T - 20)]
    alpha for copper = 0.00393 / °C
    """
    alpha = 0.00393
    rho_t = COPPER_RESISTIVITY * (1 + alpha * (conductor_temp_c - 20))
    drop_v = (2 * length_m * current_a * rho_t) / csa_mm2
    drop_pct = (drop_v / nominal_voltage_v) * 100 if nominal_voltage_v > 0 else 0
    power_loss_w = drop_v * current_a

    drop_v = rnd(drop_v, 2)
    drop_pct = rnd(drop_pct, 2)
    power_loss_w = rnd(power_loss_w, 2)

    status = "PASS" if drop_pct <= 1.5 else ("WARNING" if drop_pct <= 3.0 else "FAIL")
    return {
        "drop_v": drop_v,
        "drop_pct": drop_pct,
        "power_loss_w": power_loss_w,
        "status": status,
        "show_calculation": {
            "formula": r"\Delta V = \frac{2 \times L \times I \times \rho(T)}{S}",
            "csa_mm2": csa_mm2,
            "current_a": current_a,
            "length_m": length_m,
            "nominal_voltage_v": nominal_voltage_v,
            "conductor_temp_c": conductor_temp_c,
            "rho_t": rnd(rho_t, 6),
            "drop_v": drop_v,
            "drop_pct": drop_pct,
            "power_loss_w": power_loss_w,
        }
    }


def voltage_drop_ac_3phase(csa_mm2, current_a, length_m, nominal_voltage_v, power_factor=1.0, conductor_temp_c=70, reactance_ohm_per_km=0.08):
    """
    3-phase AC Voltage Drop:
    ΔV = √3 × (L / 1000) × I × (R·cosφ + X·sinφ)
    R in Ω/km = (ρ(T) / S) × 1000
    """
    alpha = 0.00393
    rho_t = COPPER_RESISTIVITY * (1 + alpha * (conductor_temp_c - 20))
    r_ohm_per_km = (rho_t / csa_mm2) * 1000

    # Ensure power_factor within [-1, 1]
    pf = max(0.0, min(1.0, power_factor))
    sin_phi = math.sin(math.acos(pf))
    drop_v = math.sqrt(3) * (length_m / 1000) * current_a * (r_ohm_per_km * pf + reactance_ohm_per_km * sin_phi)
    drop_pct = (drop_v / nominal_voltage_v) * 100 if nominal_voltage_v > 0 else 0
    power_loss_w = math.sqrt(3) * drop_v * current_a * pf

    drop_v = rnd(drop_v, 2)
    drop_pct = rnd(drop_pct, 2)
    power_loss_w = rnd(power_loss_w, 2)

    status = "PASS" if drop_pct <= 1.5 else ("WARNING" if drop_pct <= 3.0 else "FAIL")
    return {
        "drop_v": drop_v,
        "drop_pct": drop_pct,
        "power_loss_w": power_loss_w,
        "status": status,
        "show_calculation": {
            "formula": r"\Delta V = \sqrt{3} \times \frac{L}{1000} \times I \times (R \cos\phi + X \sin\phi)",
            "csa_mm2": csa_mm2,
            "current_a": current_a,
            "length_m": length_m,
            "nominal_voltage_v": nominal_voltage_v,
            "power_factor": pf,
            "conductor_temp_c": conductor_temp_c,
            "r_ohm_per_km": rnd(r_ohm_per_km, 4),
            "reactance_ohm_per_km": reactance_ohm_per_km,
            "drop_v": drop_v,
            "drop_pct": drop_pct,
            "power_loss_w": power_loss_w,
        }
    }


def voltage_drop_ac_1phase(csa_mm2, current_a, length_m, nominal_voltage_v, power_factor=1.0, conductor_temp_c=70, reactance_ohm_per_km=0.08):
    """
    Single-phase AC Voltage Drop:
    ΔV = 2 × (L / 1000) × I × (R·cosφ + X·sinφ)
    """
    alpha = 0.00393
    rho_t = COPPER_RESISTIVITY * (1 + alpha * (conductor_temp_c - 20))
    r_ohm_per_km = (rho_t / csa_mm2) * 1000

    pf = max(0.0, min(1.0, power_factor))
    sin_phi = math.sin(math.acos(pf))
    drop_v = 2 * (length_m / 1000) * current_a * (r_ohm_per_km * pf + reactance_ohm_per_km * sin_phi)
    drop_pct = (drop_v / nominal_voltage_v) * 100 if nominal_voltage_v > 0 else 0
    power_loss_w = drop_v * current_a * pf

    drop_v = rnd(drop_v, 2)
    drop_pct = rnd(drop_pct, 2)
    power_loss_w = rnd(power_loss_w, 2)

    status = "PASS" if drop_pct <= 1.5 else ("WARNING" if drop_pct <= 3.0 else "FAIL")
    return {
        "drop_v": drop_v,
        "drop_pct": drop_pct,
        "power_loss_w": power_loss_w,
        "status": status,
        "show_calculation": {
            "formula": r"\Delta V = 2 \times \frac{L}{1000} \times I \times (R \cos\phi + X \sin\phi)",
            "csa_mm2": csa_mm2,
            "current_a": current_a,
            "length_m": length_m,
            "nominal_voltage_v": nominal_voltage_v,
            "power_factor": pf,
            "conductor_temp_c": conductor_temp_c,
            "r_ohm_per_km": rnd(r_ohm_per_km, 4),
            "reactance_ohm_per_km": reactance_ohm_per_km,
            "drop_v": drop_v,
            "drop_pct": drop_pct,
            "power_loss_w": power_loss_w,
        }
    }
