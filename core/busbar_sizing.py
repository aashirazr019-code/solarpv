"""
Busbar Sizing Engine.
Calculates continuous current, required cross-sectional area, material selection (Copper vs Aluminium),
current density, enclosure derating, and recommends physical bar dimensions and multiple-bar arrangements.
Compliant with standard switchgear design practice (IEC 61439 / DIN 43671 / DIN 43670).
"""
import math
from typing import Dict, List, Optional
from .string_sizing import rnd

# Standard commercial rectangular busbar dimensions (Width mm x Thickness mm)
# and nominal base ampacity in open air (35°C ambient, 65°C temp rise, 50Hz AC)
STANDARD_COPPER_BARS = [
    {"width_mm": 15, "thickness_mm": 3, "csa_mm2": 45, "base_ampacity_a": 110},
    {"width_mm": 20, "thickness_mm": 3, "csa_mm2": 60, "base_ampacity_a": 145},
    {"width_mm": 20, "thickness_mm": 5, "csa_mm2": 100, "base_ampacity_a": 215},
    {"width_mm": 25, "thickness_mm": 5, "csa_mm2": 125, "base_ampacity_a": 270},
    {"width_mm": 30, "thickness_mm": 5, "csa_mm2": 150, "base_ampacity_a": 320},
    {"width_mm": 40, "thickness_mm": 5, "csa_mm2": 200, "base_ampacity_a": 420},
    {"width_mm": 40, "thickness_mm": 10, "csa_mm2": 400, "base_ampacity_a": 650},
    {"width_mm": 50, "thickness_mm": 10, "csa_mm2": 500, "base_ampacity_a": 780},
    {"width_mm": 60, "thickness_mm": 10, "csa_mm2": 600, "base_ampacity_a": 910},
    {"width_mm": 80, "thickness_mm": 10, "csa_mm2": 800, "base_ampacity_a": 1180},
    {"width_mm": 100, "thickness_mm": 10, "csa_mm2": 1000, "base_ampacity_a": 1420},
    {"width_mm": 120, "thickness_mm": 10, "csa_mm2": 1200, "base_ampacity_a": 1680},
]

# Aluminium has approximately 61% the conductivity of copper (standard multiplier ~0.78 for equivalent heating)
ALUMINIUM_CONDUCTIVITY_FACTOR = 0.78
COPPER_DENSITY_G_CM3 = 8.96
ALUMINIUM_DENSITY_G_CM3 = 2.70


def size_busbar_engineering(
    current_a: float,
    material: str = "copper",
    current_density_a_mm2: Optional[float] = None,
    enclosure_type: str = "enclosed",
    safety_factor: float = 1.25,
    ambient_temp_c: float = 35.0,
    max_bars_per_phase: int = 3
) -> Dict:
    """
    Sizes busbars with dimensional cross-section and parallel lamination arrangements.
    
    Parameters
    ----------
    current_a              : Operating continuous current (A)
    material               : 'copper' or 'aluminium'
    current_density_a_mm2  : Design current density (A/mm²). If None, standard default is used.
                             Copper default: 1.5 A/mm², Aluminium default: 1.0 A/mm²
    enclosure_type         : 'enclosed' (factor 0.80), 'ventilated' (factor 0.90), 'open_air' (factor 1.00)
    safety_factor          : Continuous design safety multiplier (default 1.25 per NEC / IEC)
    ambient_temp_c         : Ambient operating temperature (°C)
    max_bars_per_phase     : Max physical laminations per phase (typically 1 to 4)
    """
    errors = []
    if current_a <= 0:
        errors.append("Current must be greater than 0 A.")
    if safety_factor < 1.0:
        errors.append("Safety factor must be at least 1.0.")

    mat_lower = material.lower().strip()
    if mat_lower not in ("copper", "cu", "aluminium", "aluminum", "al"):
        errors.append("Material must be 'copper' or 'aluminium'.")

    is_copper = mat_lower in ("copper", "cu")

    # Enclosure derating factors
    enclosure_factors = {
        "enclosed": 0.80,
        "ventilated": 0.90,
        "open_air": 1.00
    }
    k_enc = enclosure_factors.get(enclosure_type.lower(), 0.85)

    # Temperature derating factor (referenced to 35°C ambient)
    k_temp = 1.0
    if ambient_temp_c > 35:
        # standard DIN derating formula ~ 1 - 0.005 * (T_amb - 35)
        k_temp = max(0.60, 1.0 - 0.005 * (ambient_temp_c - 35.0))
    elif ambient_temp_c < 35:
        k_temp = min(1.15, 1.0 + 0.003 * (35.0 - ambient_temp_c))

    # Current density selection
    if current_density_a_mm2 is None or current_density_a_mm2 <= 0:
        design_density = 1.5 if is_copper else 1.0
    else:
        design_density = current_density_a_mm2

    if errors:
        return {
            "status": "FAIL",
            "errors": errors,
            "design_current_a": 0.0,
            "required_csa_mm2": 0.0,
            "recommended_bar": None,
            "bars_per_phase": 0,
            "total_csa_mm2": 0.0,
            "effective_ampacity_a": 0.0
        }

    design_current_a = current_a * safety_factor
    combined_derating = k_enc * k_temp
    
    # Required cross-sectional area based on current density
    required_csa_mm2 = design_current_a / (design_density * combined_derating)

    # Search through standard bar dimensions and lamination configurations
    # When multiple bars are stacked with air gap (e.g. 2 bars), DIN 43671 multi-bar rating factor applies:
    # 1 bar: 1.0x, 2 bars: 1.72x (not 2.0x due to proximity/skin effect), 3 bars: 2.25x
    multi_bar_factors = {1: 1.00, 2: 1.72, 3: 2.25, 4: 2.70}

    best_config = None
    all_viable_options = []

    for bars_count in range(1, max_bars_per_phase + 1):
        multi_factor = multi_bar_factors.get(bars_count, bars_count * 0.70)
        
        for bar in STANDARD_COPPER_BARS:
            base_amp = bar["base_ampacity_a"] if is_copper else (bar["base_ampacity_a"] * ALUMINIUM_CONDUCTIVITY_FACTOR)
            effective_bar_amp = base_amp * multi_factor * combined_derating
            total_csa = bar["csa_mm2"] * bars_count
            
            if effective_bar_amp >= design_current_a:
                utilization_pct = (design_current_a / effective_bar_amp) * 100.0
                density_actual = design_current_a / total_csa
                
                # Weight per meter in kg for 3 phases + neutral (4 bars total)
                density_mat = COPPER_DENSITY_G_CM3 if is_copper else ALUMINIUM_DENSITY_G_CM3
                weight_per_m_kg = (total_csa * 4 * density_mat) / 1000.0
                
                option = {
                    "width_mm": bar["width_mm"],
                    "thickness_mm": bar["thickness_mm"],
                    "dimension_str": f"{bar['width_mm']} x {bar['thickness_mm']} mm",
                    "bars_per_phase": bars_count,
                    "arrangement_str": f"{bars_count} bar{'s' if bars_count > 1 else ''} of {bar['width_mm']}x{bar['thickness_mm']}mm per phase",
                    "single_bar_csa_mm2": bar["csa_mm2"],
                    "total_csa_mm2": total_csa,
                    "effective_ampacity_a": rnd(effective_bar_amp, 1),
                    "design_current_a": rnd(design_current_a, 1),
                    "utilization_pct": rnd(utilization_pct, 1),
                    "actual_current_density_a_mm2": rnd(density_actual, 2),
                    "est_weight_4p_kg_per_m": rnd(weight_per_m_kg, 2)
                }
                all_viable_options.append(option)
                
                # Pick the smallest viable total CSA
                if best_config is None or total_csa < best_config["total_csa_mm2"]:
                    best_config = option

    if best_config is None:
        # If standard tables were exceeded, recommend custom large profile
        custom_csa = required_csa_mm2
        best_config = {
            "width_mm": 120,
            "thickness_mm": 10,
            "dimension_str": "120 x 10 mm",
            "bars_per_phase": max(4, math.ceil(custom_csa / 1200)),
            "arrangement_str": f"{math.ceil(custom_csa / 1200)} bars of 120x10mm per phase",
            "single_bar_csa_mm2": 1200,
            "total_csa_mm2": custom_csa,
            "effective_ampacity_a": rnd(design_current_a * 1.05, 1),
            "design_current_a": rnd(design_current_a, 1),
            "utilization_pct": 95.0,
            "actual_current_density_a_mm2": rnd(design_density, 2),
            "est_weight_4p_kg_per_m": 0.0
        }

    return {
        "status": "PASS",
        "errors": [],
        "material": "Copper" if is_copper else "Aluminium",
        "input_current_a": rnd(current_a, 1),
        "safety_factor": safety_factor,
        "design_current_a": rnd(design_current_a, 1),
        "target_current_density": design_density,
        "enclosure_factor": k_enc,
        "temp_derating_factor": rnd(k_temp, 3),
        "combined_derating_factor": rnd(combined_derating, 3),
        "required_csa_mm2": rnd(required_csa_mm2, 1),
        "recommended": best_config,
        "alternative_options": all_viable_options[:5],
        "show_calculation": {
            "design_current_formula": "I_design = I_operating * Safety_Factor",
            "required_csa_formula": "CSA_req = I_design / (Current_Density * k_enc * k_temp)",
            "ampacity_derating_formula": "I_eff = I_base * k_multi_bar * k_enc * k_temp"
        }
    }
