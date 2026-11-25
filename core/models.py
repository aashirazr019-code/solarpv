"""
Data models for the Solar PV Engineering Design Platform.

Enhanced from the original engine/model.py with:
- Input validation on construction
- Additional fields for professional engineering (NOCT, bifaciality, provenance)
- Project management fields (customer, revision, status)
- Cable, Protection, Earthing, BOM data classes
- All original fields preserved for backward compatibility
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def rnd(n: float, dp: int) -> float:
    """Consistent rounding used throughout the engine."""
    f = 10 ** dp
    return round(n * f) / f


def _gen_id() -> str:
    return str(uuid.uuid4())[:8]


# ---------------------------------------------------------------------------
# PV Module (Panel)
# ---------------------------------------------------------------------------

@dataclass
class Panel:
    """
    PV Module electrical and mechanical specification.
    All original fields preserved. New optional fields added for
    professional engineering without breaking existing code.
    """
    id: str
    manufacturer: str
    model: str
    rated_power_wp: float
    voc: float                          # Open-circuit voltage at STC (V)
    vmp: float                          # Max power voltage at STC (V)
    isc: float                          # Short-circuit current at STC (A)
    imp: float                          # Max power current at STC (A)
    max_system_voltage: float           # Maximum system voltage (V)
    max_series_fuse: float              # Maximum series fuse rating (A)
    temp_coeff_voc: float               # %/°C
    temp_coeff_isc: float               # %/°C
    temp_coeff_pmax: float              # %/°C — fallback for temp_coeff_vmp
    length_m: float
    width_m: float
    thickness_mm: float
    weight_kg: float
    cell_technology: str
    cell_count: int
    temp_coeff_vmp: Optional[float] = None   # %/°C, nullable
    # --- New professional fields (all optional for backward compat) ---
    noct_temp_c: Optional[float] = None      # NOCT/NMOT temperature (°C)
    bifaciality_factor: Optional[float] = None  # e.g. 0.80 for 80% rear gain
    module_efficiency_pct: Optional[float] = None
    power_tolerance_pos_pct: float = 3.0
    power_tolerance_neg_pct: float = 0.0
    connector_type: str = "MC4"
    frame_type: str = "Aluminium Alloy"
    ip_rating: str = "IP68"
    # provenance
    notes: str = ""
    source: str = "manual"               # manual | library | datasheet_import
    datasheet_file: str = ""
    verification_status: str = "unverified"  # unverified | pending | verified
    verified_by: str = ""
    verified_at: str = ""

    def area_m2(self) -> float:
        return self.length_m * self.width_m

    def validate(self) -> List[str]:
        """Returns list of validation error messages. Empty = valid."""
        errors = []
        if self.rated_power_wp <= 0:
            errors.append("Rated power must be > 0 Wp")
        if self.voc <= 0:
            errors.append("Voc must be > 0 V")
        if self.vmp <= 0:
            errors.append("Vmp must be > 0 V")
        if self.vmp >= self.voc:
            errors.append(f"Vmp ({self.vmp}V) must be less than Voc ({self.voc}V)")
        if self.isc <= 0:
            errors.append("Isc must be > 0 A")
        if self.imp <= 0:
            errors.append("Imp must be > 0 A")
        if self.imp >= self.isc:
            errors.append(f"Imp ({self.imp}A) must be less than Isc ({self.isc}A)")
        if self.max_system_voltage <= 0:
            errors.append("Max system voltage must be > 0 V")
        if self.length_m <= 0 or self.width_m <= 0:
            errors.append("Panel dimensions must be > 0")
        if self.temp_coeff_voc >= 0:
            errors.append("Temp coeff Voc should be negative for silicon modules")
        return errors


# ---------------------------------------------------------------------------
# Inverter
# ---------------------------------------------------------------------------

@dataclass
class Inverter:
    """
    Inverter / MPPT controller specification.
    All original fields preserved.
    """
    id: str
    manufacturer: str
    model: str
    rated_ac_power_kw: float
    max_dc_input_power_kw: float
    max_dc_voltage_v: float
    mppt_voltage_min_v: float
    mppt_voltage_max_v: float
    mppt_count: int
    string_inputs_per_mppt: int
    max_input_current_per_mppt_a: float
    max_isc_per_mppt_a: float
    max_total_dc_current_a: float
    ac_voltage: float
    rated_ac_current_a: float
    max_ac_current_a: float
    efficiency_pct: float
    recommended_dc_ac_ratio: Optional[float] = None
    max_dc_oversizing_pct: Optional[float] = None
    # --- New professional fields ---
    inverter_type: str = "string"        # string | central | micro | hybrid
    grid_type: str = "3-phase"           # 1-phase | 3-phase
    startup_voltage_v: Optional[float] = None
    nominal_dc_voltage_v: Optional[float] = None
    max_apparent_power_kva: Optional[float] = None
    frequency_hz: float = 50.0
    thd_pct: Optional[float] = None
    dc_switch_integrated: bool = False
    dc_spd_integrated: bool = False
    ip_rating: str = "IP65"
    cooling_method: str = "Natural Convection"
    operating_temp_min_c: float = -25.0
    operating_temp_max_c: float = 60.0
    weight_kg: Optional[float] = None
    dimensions_mm: str = ""
    # provenance
    notes: str = ""
    source: str = "manual"
    datasheet_file: str = ""
    verification_status: str = "unverified"
    verified_by: str = ""
    verified_at: str = ""

    def validate(self) -> List[str]:
        errors = []
        if self.rated_ac_power_kw <= 0:
            errors.append("Rated AC power must be > 0 kW")
        if self.max_dc_voltage_v <= 0:
            errors.append("Max DC voltage must be > 0 V")
        if self.mppt_voltage_min_v >= self.mppt_voltage_max_v:
            errors.append("MPPT min voltage must be < MPPT max voltage")
        if self.mppt_voltage_max_v > self.max_dc_voltage_v:
            errors.append("MPPT max voltage cannot exceed max DC voltage")
        if self.mppt_count < 1:
            errors.append("MPPT count must be >= 1")
        if self.string_inputs_per_mppt < 1:
            errors.append("String inputs per MPPT must be >= 1")
        if self.max_isc_per_mppt_a <= 0:
            errors.append("Max Isc per MPPT must be > 0 A")
        if self.efficiency_pct <= 0 or self.efficiency_pct > 100:
            errors.append("Efficiency must be between 0 and 100%")
        return errors


# ---------------------------------------------------------------------------
# Spacing & Layout Configuration
# ---------------------------------------------------------------------------

@dataclass
class SpacingConfig:
    """Physical spacing parameters for panel array layout."""
    panel_gap_m: float = 0.02
    row_gap_m: float = 0.5
    edge_clearance_m: float = 1.0
    walkway_m: float = 1.2
    inverter_access_m: float = 2.0


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

@dataclass
class Project:
    """
    Engineering project — enhanced with professional management fields.
    All original fields preserved for backward compatibility.
    """
    id: str
    name: str
    location: str
    installation_type: str              # "rooftop" | "ground_mount"
    target_ac_capacity_kw: float
    min_design_temp_c: float
    max_design_temp_c: float
    dc_ac_ratio_min: float
    dc_ac_ratio_preferred: float
    dc_ac_ratio_max: float
    panel_id: str
    panel_available_qty: int
    area_length_m: float
    area_width_m: float
    spacing_config: SpacingConfig
    availability_mode: str = "technical_optimization"
    # --- New professional fields ---
    customer_name: str = ""
    customer_contact: str = ""
    site_name: str = ""
    site_address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_m: Optional[float] = None
    grid_voltage_v: float = 400.0
    grid_frequency_hz: float = 50.0
    grid_type: str = "3-phase"           # 1-phase | 3-phase
    designer_name: str = ""
    reviewer_name: str = ""
    revision: int = 0
    status: str = "draft"               # draft | in_review | approved | archived
    created_at: str = ""
    updated_at: str = ""
    notes: str = ""
    # Design conditions
    peak_sun_hours: Optional[float] = None   # PSH (h/day)
    soiling_loss_pct: float = 2.0
    shading_loss_pct: float = 0.0
    availability_pct: float = 99.0
    annual_degradation_pct: float = 0.5

    def validate(self) -> List[str]:
        errors = []
        if self.target_ac_capacity_kw <= 0:
            errors.append("Target AC capacity must be > 0 kW")
        if self.min_design_temp_c >= self.max_design_temp_c:
            errors.append("Min design temp must be < Max design temp")
        if self.dc_ac_ratio_min >= self.dc_ac_ratio_max:
            errors.append("DC/AC ratio min must be < max")
        if self.dc_ac_ratio_preferred < self.dc_ac_ratio_min or \
           self.dc_ac_ratio_preferred > self.dc_ac_ratio_max:
            errors.append("DC/AC ratio preferred must be between min and max")
        if self.area_length_m <= 0 or self.area_width_m <= 0:
            errors.append("Area dimensions must be > 0")
        if self.panel_available_qty <= 0:
            errors.append("Panel available quantity must be > 0")
        return errors


# ---------------------------------------------------------------------------
# Inverter Option (for combination search)
# ---------------------------------------------------------------------------

@dataclass
class InverterOption:
    """An inverter model paired with its available stock quantity."""
    inverter: Inverter
    available_qty: int


# ---------------------------------------------------------------------------
# Cable Specification
# ---------------------------------------------------------------------------

@dataclass
class CableSpec:
    """Cable specification for sizing and voltage drop calculations."""
    id: str = ""
    name: str = ""
    csa_mm2: float = 0.0
    material: str = "copper"             # copper | aluminium
    insulation: str = "PVC"              # PVC | XLPE | H1Z2Z2-K
    max_temp_c: float = 70.0             # 70 for PVC, 90 for XLPE
    voltage_rating_v: float = 1000.0
    cores: int = 1                       # single-core or multi-core
    ampacity_a: float = 0.0             # tabulated ampacity for selected method
    installation_method: str = ""
    length_m: float = 0.0
    manufacturer: str = ""
    source: str = "manual"


# ---------------------------------------------------------------------------
# Protection Device
# ---------------------------------------------------------------------------

@dataclass
class ProtectionDevice:
    """MCB, MCCB, Fuse, SPD specification."""
    id: str = ""
    device_type: str = ""               # MCB | MCCB | DC_FUSE | SPD_DC | SPD_AC | RCD | ISOLATOR
    manufacturer: str = ""
    model: str = ""
    rated_current_a: float = 0.0
    rated_voltage_v: float = 0.0
    breaking_capacity_ka: float = 0.0
    poles: int = 1
    trip_curve: str = "C"                # B | C | D (MCB) or thermal-magnetic (MCCB)
    notes: str = ""
    source: str = "manual"


# ---------------------------------------------------------------------------
# Earthing Configuration
# ---------------------------------------------------------------------------

@dataclass
class EarthingConfig:
    """Earthing system parameters."""
    soil_resistivity_ohm_m: float = 100.0    # REQUIRES ENGINEERING CONFIRMATION
    electrode_type: str = "copper_bonded_rod"
    electrode_length_m: float = 3.0
    electrode_diameter_mm: float = 16.0
    target_resistance_ohm: float = 5.0
    earth_conductor_csa_mm2: float = 16.0
    earth_conductor_material: str = "copper"


# ---------------------------------------------------------------------------
# BOM Item
# ---------------------------------------------------------------------------

@dataclass
class BOMItem:
    """Single line item in the Bill of Materials."""
    category: str                        # Module | Inverter | Cable | Protection | Mounting | Earthing
    item_name: str
    manufacturer: str = ""
    model: str = ""
    description: str = ""
    quantity: float = 0.0
    unit: str = "nos"                    # nos | m | set | lot
    specification: str = ""
    source: str = ""                     # Where quantity was derived from
    notes: str = ""
    rule_source: str = "ENGINEERING_RULE" # CEB_REQUIRED | ENGINEERING_RULE | COMPANY_STANDARD | INSTALLER_RULE | MANUAL_REVIEW_REQUIRED


# ---------------------------------------------------------------------------
# Design Result (output of the full pipeline)
# ---------------------------------------------------------------------------

@dataclass
class DesignResult:
    """Complete design result from the pipeline — used for reports & validation."""
    project_id: str = ""
    project_name: str = ""
    timestamp: str = ""
    overall_status: str = "PENDING"      # PASS | WARNING | FAIL | PENDING

    # Capacities
    dc_capacity_kwp: float = 0.0
    ac_capacity_kw: float = 0.0
    dc_ac_ratio: float = 0.0
    total_panels: int = 0
    panels_per_string: int = 0
    total_strings: int = 0
    total_inverters: int = 0

    # Detailed results (dicts from individual calculators)
    string_sizing: Dict[str, Any] = field(default_factory=dict)
    voltage_check: Dict[str, Any] = field(default_factory=dict)
    current_check: Dict[str, Any] = field(default_factory=dict)
    mppt_allocation: Dict[str, Any] = field(default_factory=dict)
    dc_ac_result: Dict[str, Any] = field(default_factory=dict)
    layout: Dict[str, Any] = field(default_factory=dict)
    inverter_breakdown: str = ""

    # Electrical sizing
    dc_cable: Dict[str, Any] = field(default_factory=dict)
    ac_cable: Dict[str, Any] = field(default_factory=dict)
    voltage_drop_dc: Dict[str, Any] = field(default_factory=dict)
    voltage_drop_ac: Dict[str, Any] = field(default_factory=dict)
    protection_dc: Dict[str, Any] = field(default_factory=dict)
    protection_ac: Dict[str, Any] = field(default_factory=dict)
    busbar: Dict[str, Any] = field(default_factory=dict)
    earthing: Dict[str, Any] = field(default_factory=dict)
    system_losses: Dict[str, Any] = field(default_factory=dict)

    # Validation
    validation_results: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, str]] = field(default_factory=list)

    # BOM
    bom_items: List[BOMItem] = field(default_factory=list)

    # Scoring
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    rank: int = 0
