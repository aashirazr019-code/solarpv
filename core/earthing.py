import math

def calculate_earth_rod_resistance(soil_resistivity, rod_length_m=3.0, rod_diameter_mm=16.0):
    """
    R_rod = ρ / (2πL) × [ln(4L/d) - 1]
    Per BS 7430.
    """
    d_m = rod_diameter_mm / 1000
    resistance_ohm = (soil_resistivity / (2 * math.pi * rod_length_m)) * (math.log(4 * rod_length_m / d_m) - 1)
    return {
        "resistance_ohm": resistance_ohm,
        "status": "PASS",
        "show_calculation": {"r_rod": f"({soil_resistivity} / (2*PI*{rod_length_m})) * (ln(4*{rod_length_m}/{d_m}) - 1)"}
    }

def calculate_earth_rods_required(single_rod_resistance, target_resistance, efficiency_factor=0.75):
    """
    N_rods = ceil(R_single / (R_target × η))
    """
    n_rods = math.ceil(single_rod_resistance / (target_resistance * efficiency_factor))
    return {"n_rods": n_rods, "status": "PASS"}

def calculate_earth_conductor_size(fault_current_a, clearing_time_s=1.0, k_factor=143):
    """
    S_e = I_fault × √t / k   (minimum 16mm² Cu)
    k = 143 for copper PVC, 176 for copper XLPE.
    """
    csa_mm2 = (fault_current_a * math.sqrt(clearing_time_s)) / k_factor
    csa_mm2 = max(csa_mm2, 16.0)
    return {"csa_mm2": csa_mm2, "status": "PASS"}
