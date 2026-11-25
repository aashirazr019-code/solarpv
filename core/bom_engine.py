"""
core/bom_engine.py — Intelligent Rule-Based BOM / BOQ Generation Engine
Engineered for automated equipment selection, string-aware protection coordination,
multi-panel optimization, and complete BoS material takeoff.
Authored by Eng. Aashir © 2026.
"""
import os
import json
import math
from typing import Dict, List, Optional, Any
from .models import Panel, Inverter
from .string_sizing import cold_voc, hot_vmp, cold_vmp, panels_per_string_range, voltage_check
from .master_data import (
    RULE_SOURCE_CEB,
    RULE_SOURCE_ENGINEERING,
    RULE_SOURCE_COMPANY,
    RULE_SOURCE_INSTALLER,
    RULE_SOURCE_MANUAL_REVIEW
)

RULES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "solar_rules.json")
COMPONENTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "components.json")
MASTER_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "master_data.json")

ENGINEERING_DISCLAIMER = (
    "Automatic BOM selection is based on the configured engineering rules, "
    "component database, and available equipment data. Final equipment "
    "selection must be verified against the latest manufacturer datasheets, "
    "applicable Sri Lankan utility requirements, and project/site conditions."
)


class BOMEngine:
    """
    Intelligent, modular Solar PV Bill of Materials (BoQ) generation engine.
    Applies configurable engineering rules and priority-based component selection.
    """

    def __init__(self):
        self.rules: Dict[str, Any] = {}
        self.components: Dict[str, Any] = {}
        self.master_data: Dict[str, Any] = {}
        self.load_rules_and_components()

    def load_rules_and_components(self) -> None:
        """Loads or reloads centralized rules and component databases from JSON."""
        if os.path.exists(RULES_FILE):
            try:
                with open(RULES_FILE, "r", encoding="utf-8") as f:
                    self.rules = json.load(f)
            except Exception:
                self.rules = {}

        if os.path.exists(COMPONENTS_FILE):
            try:
                with open(COMPONENTS_FILE, "r", encoding="utf-8") as f:
                    self.components = json.load(f)
            except Exception:
                self.components = {}

        if os.path.exists(MASTER_DATA_FILE):
            try:
                with open(MASTER_DATA_FILE, "r", encoding="utf-8") as f:
                    self.master_data = json.load(f)
            except Exception:
                self.master_data = {}

    # ---------------------------------------------------------------------------
    # 1. Phase Selection
    # ---------------------------------------------------------------------------
    def select_phase(self, system_capacity_kw: float) -> Dict[str, Any]:
        """
        Determines standard grid phase and category based on centralized capacity rules.
        Default Rules:
          1 - 5 kW:   Single Phase
          6 - 20 kW:  3 Phase / 30 A category
          21 - 40 kW: 3 Phase / 60 A category
          > 40 kW:    Utility Interconnection Assessment Required
        """
        phase_rules = self.rules.get("phase_rules", [
            {"min_kw": 1.0, "max_kw": 5.0, "phase": 1, "category": "Single Phase", "description": "Single Phase (1 kW – 5 kW)", "rule_source": RULE_SOURCE_COMPANY},
            {"min_kw": 5.01, "max_kw": 20.0, "phase": 3, "category": "3 Phase 30 A", "description": "Three Phase — 30 A category (6 kW – 20 kW)", "rule_source": RULE_SOURCE_COMPANY},
            {"min_kw": 20.01, "max_kw": 40.0, "phase": 3, "category": "3 Phase 60 A", "description": "Three Phase — 60 A category (21 kW – 40 kW)", "rule_source": RULE_SOURCE_COMPANY},
            {"min_kw": 40.01, "max_kw": 999999.0, "phase": 3, "category": "Utility Assessment Required", "description": "Utility Assessment Required (> 40 kW)", "rule_source": RULE_SOURCE_MANUAL_REVIEW}
        ])

        for rule in phase_rules:
            if rule["min_kw"] <= system_capacity_kw <= rule["max_kw"]:
                return {
                    "phase": rule["phase"],
                    "category": rule.get("category", "Single Phase" if rule["phase"] == 1 else "Three Phase"),
                    "description": rule.get("description", ""),
                    "max_ac_current_category_a": rule.get("max_ac_current_category_a", 32.0 if rule["phase"] == 1 else 60.0),
                    "rule_source": rule.get("rule_source", RULE_SOURCE_COMPANY)
                }

        return {
            "phase": 3,
            "category": "Utility Assessment Required",
            "description": "Commercial / Utility Interconnection Review Required (> 40 kW)",
            "max_ac_current_category_a": 999.0,
            "rule_source": RULE_SOURCE_MANUAL_REVIEW
        }

    # ---------------------------------------------------------------------------
    # 2. DC Sizing & Oversizing
    # ---------------------------------------------------------------------------
    def calculate_dc_target(
        self,
        inverter_capacity_kw: float,
        installation_type: str = "rooftop",
        oversizing_factor: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates target DC capacity:
        DC Design Capacity = Inverter Capacity × DC Oversizing Factor (default 1.30 for rooftop)
        """
        if oversizing_factor is None:
            dc_rules = self.rules.get("dc_oversizing", {})
            if "ground" in installation_type.lower():
                factor = float(dc_rules.get("ground_default", 1.20))
            else:
                factor = float(dc_rules.get("rooftop_default", 1.30))
        else:
            factor = float(oversizing_factor)

        target_dc_kwp = round(inverter_capacity_kw * factor, 3)
        return {
            "inverter_capacity_kw": inverter_capacity_kw,
            "oversizing_factor": factor,
            "target_dc_kwp": target_dc_kwp,
            "installation_type": installation_type,
            "formula": f"{inverter_capacity_kw} kW × {factor:.2f} = {target_dc_kwp:.2f} kWp"
        }

    # ---------------------------------------------------------------------------
    # 3. Multi-Panel Selection & Optimization
    # ---------------------------------------------------------------------------
    def get_available_panels(self) -> List[Panel]:
        """Returns list of approved active panels from rules or master data (580W, 615W, 630W)."""
        approved_rules = self.rules.get("approved_panels", [])
        if approved_rules:
            panels = []
            for p in approved_rules:
                panels.append(Panel(
                    id=f"approved-panel-{int(p.get('rated_power_wp', 630))}",
                    manufacturer=p.get("manufacturer", "Yingli Solar"),
                    model=p.get("model", f"{p.get('rated_power_wp')}W Module"),
                    rated_power_wp=float(p.get("rated_power_wp", 630.0)),
                    voc=float(p.get("voc", 49.44)),
                    vmp=float(p.get("vmp", 41.47)),
                    isc=float(p.get("isc", 16.18)),
                    imp=float(p.get("imp", 15.19)),
                    max_system_voltage=float(p.get("max_system_voltage", 1500.0)),
                    max_series_fuse=float(p.get("max_series_fuse", 30.0)),
                    temp_coeff_voc=float(p.get("temp_coeff_voc", -0.24)),
                    temp_coeff_vmp=float(p.get("temp_coeff_vmp", -0.26)),
                    temp_coeff_isc=float(p.get("temp_coeff_isc", 0.042)),
                    temp_coeff_pmax=float(p.get("temp_coeff_pmax", -0.29)),
                    length_m=float(p.get("length_m", 2.382)),
                    width_m=float(p.get("width_m", 1.134)),
                    thickness_mm=float(p.get("thickness_mm", 30.0)),
                    weight_kg=float(p.get("weight_kg", 33.0)),
                    cell_technology=p.get("cell_technology", "N-type TOPCon Bifacial"),
                    cell_count=int(p.get("cell_count", 132)),
                    source="approved_list"
                ))
            return panels

        panels_raw = self.master_data.get("panels", [])
        panels = []
        for p in panels_raw:
            if not p.get("is_active", True):
                continue
            panels.append(Panel(
                id=p.get("id", f"panel-{p.get('rated_power_wp', 630)}"),
                manufacturer=p.get("manufacturer", "Yingli Solar"),
                model=p.get("model", f"{p.get('rated_power_wp', 630)}W Module"),
                rated_power_wp=float(p.get("rated_power_wp", 630.0)),
                voc=float(p.get("voc", 49.44)),
                vmp=float(p.get("vmp", 41.47)),
                isc=float(p.get("isc", 16.18)),
                imp=float(p.get("imp", 15.19)),
                max_system_voltage=float(p.get("max_system_voltage", 1500.0)),
                max_series_fuse=float(p.get("max_series_fuse", 30.0)),
                temp_coeff_voc=float(p.get("temp_coeff_voc", -0.24)),
                temp_coeff_vmp=float(p.get("temp_coeff_vmp", -0.26)),
                temp_coeff_isc=float(p.get("temp_coeff_isc", 0.042)),
                temp_coeff_pmax=float(p.get("temp_coeff_pmax", -0.29)),
                length_m=float(p.get("length_m", 2.382)),
                width_m=float(p.get("width_m", 1.134)),
                thickness_mm=float(p.get("thickness_mm", 30.0)),
                weight_kg=float(p.get("weight_kg", 33.0)),
                cell_technology=p.get("cell_technology", "N-type TOPCon Bifacial"),
                cell_count=int(p.get("cell_count", 132)),
                source="master_data"
            ))
        return panels

    def optimize_panel_selection(
        self,
        target_dc_kwp: float,
        inverter: Inverter,
        min_temp_c: float = -30.0,
        max_temp_c: float = 60.0,
        candidate_panels: Optional[List[Panel]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluates and ranks available panels (580W, 585W, 615W, 630W).
        Adjusts panel count to the next valid count (>= ceiling) matching string architecture.
        """
        if candidate_panels is None:
            candidate_panels = self.get_available_panels()

        results = []

        class TempProject:
            min_design_temp_c = min_temp_c
            max_design_temp_c = max_temp_c

        proj = TempProject()

        for panel in candidate_panels:
            p_wp = panel.rated_power_wp
            p_kw = p_wp / 1000.0

            # Ceiling calculation
            raw_count = math.ceil(target_dc_kwp / p_kw) if p_kw > 0 else 0

            # String bounds check
            s_range = panels_per_string_range(panel, inverter, proj)
            min_str_len = s_range["min_panels_per_string"]
            max_str_len = s_range["max_panels_per_string"]

            if not s_range["valid"] or max_str_len <= 0:
                results.append({
                    "panel": panel,
                    "status": "FAIL",
                    "recommendation": "Rejected",
                    "badge": "🔴 Incompatible",
                    "reason": f"No electrically valid string length for {panel.model} (Vmp/Voc out of inverter window).",
                    "panel_count": 0,
                    "strings_count": 0,
                    "panels_per_string": 0,
                    "actual_dc_kwp": 0.0,
                    "dc_ac_ratio": 0.0,
                    "deviation_kwp": 999.0
                })
                continue

            # Check candidate counts starting from raw_count upwards (next valid panel count)
            # and only checking downward if no upward candidate works
            candidate_counts = [
                raw_count,
                raw_count + 1,
                raw_count + 2,
                raw_count + 3,
                raw_count + 4,
                max(1, raw_count - 1),
                max(1, raw_count - 2)
            ]

            best_config = None
            min_score = float("inf")

            for count in candidate_counts:
                # Find valid string configurations (preferring 2 strings for 2 MPPT inverters)
                for num_strings in range(1, inverter.mppt_count * inverter.string_inputs_per_mppt + 1):
                    if count % num_strings == 0:
                        panels_per_str = count // num_strings
                        if min_str_len <= panels_per_str <= max_str_len:
                            v_res = voltage_check(panel, inverter, proj, panels_per_str)
                            if v_res["cold"]["status"] == "FAIL" or v_res["hot"]["status"] == "FAIL":
                                continue

                            actual_dc = round(count * p_kw, 3)
                            dev = abs(actual_dc - target_dc_kwp)

                            # Favor configurations meeting target DC (count >= raw_count)
                            under_penalty = 2.0 if count < raw_count else 0.0
                            # Require/favor balanced utilization of all inverter MPPTs (e.g. 2 strings on 2 MPPTs)
                            if inverter.mppt_count > 1 and num_strings < inverter.mppt_count:
                                mppt_balance_penalty = 5.0  # Strongly disfavor leaving MPPT inputs unused
                            elif num_strings == inverter.mppt_count or num_strings % inverter.mppt_count == 0:
                                mppt_balance_penalty = 0.0
                            else:
                                mppt_balance_penalty = 1.0

                            score = dev + under_penalty + mppt_balance_penalty

                            if score < min_score:
                                min_score = score
                                best_config = {
                                    "panel_count": count,
                                    "strings_count": num_strings,
                                    "panels_per_string": panels_per_str,
                                    "actual_dc_kwp": actual_dc,
                                    "dc_ac_ratio": round(actual_dc / inverter.rated_ac_power_kw, 3),
                                    "deviation_kwp": round(actual_dc - target_dc_kwp, 3),
                                    "voltage_check": v_res,
                                    "string_range": s_range
                                }

            if best_config:
                results.append({
                    "panel": panel,
                    "status": "PASS",
                    "recommendation": "Pending",
                    "reason": f"Compliant: {best_config['panel_count']} modules ({best_config['strings_count']} str × {best_config['panels_per_string']} mod), DC/AC {best_config['dc_ac_ratio']:.2f}",
                    **best_config
                })
            else:
                results.append({
                    "panel": panel,
                    "status": "FAIL",
                    "recommendation": "Rejected",
                    "badge": "🔴 Incompatible",
                    "reason": f"Could not find a valid string configuration within {min_str_len}-{max_str_len} panels/string for {panel.model}.",
                    "panel_count": raw_count,
                    "strings_count": 0,
                    "panels_per_string": 0,
                    "actual_dc_kwp": round(raw_count * p_kw, 3),
                    "dc_ac_ratio": 0.0,
                    "deviation_kwp": 999.0
                })

        passing = [r for r in results if r["status"] == "PASS"]
        failing = [r for r in results if r["status"] == "FAIL"]

        # Sort passing: prioritize 630W default approved panel, then lowest deviation
        passing.sort(key=lambda x: (
            0 if abs(x["panel"].rated_power_wp - 630.0) < 2.0 else 1,
            abs(x["deviation_kwp"])
        ))

        for i, r in enumerate(passing):
            if i == 0:
                r["recommendation"] = "Recommended"
                r["badge"] = "🟢 Recommended"
            else:
                r["recommendation"] = "Alternative"
                r["badge"] = "🟡 Alternative"

        return passing + failing

    # ---------------------------------------------------------------------------
    # 4. String & MPPT Distribution
    # ---------------------------------------------------------------------------
    def calculate_string_and_mppt(
        self,
        panel: Panel,
        inverter: Inverter,
        total_panels: int,
        min_temp_c: float = -30.0,
        max_temp_c: float = 60.0
    ) -> Dict[str, Any]:
        """
        Determines valid string split and maps strings across inverter MPPTs.
        Computes string voltages (cold Voc, hot Vmp) and operating currents.
        """
        class TempProj:
            min_design_temp_c = min_temp_c
            max_design_temp_c = max_temp_c

        proj = TempProj()
        s_range = panels_per_string_range(panel, inverter, proj)
        min_p = s_range["min_panels_per_string"]
        max_p = s_range["max_panels_per_string"]

        best_strings = 0
        best_p_per_s = 0

        max_possible_strings = inverter.mppt_count * inverter.string_inputs_per_mppt
        # Prefer matching inverter MPPT count (e.g. 2 strings on 2 MPPTs)
        preferred_string_counts = [inverter.mppt_count] + [s for s in range(1, max_possible_strings + 1) if s != inverter.mppt_count]

        for num_strings in preferred_string_counts:
            if total_panels % num_strings == 0:
                p_per_s = total_panels // num_strings
                if min_p <= p_per_s <= max_p:
                    best_strings = num_strings
                    best_p_per_s = p_per_s
                    break

        # If not divisible, adjust to nearest valid count
        if best_strings == 0:
            for delta in [1, 2, -1, -2, 3, -3]:
                adj_count = total_panels + delta
                for num_strings in preferred_string_counts:
                    if adj_count % num_strings == 0:
                        p_per_s = adj_count // num_strings
                        if min_p <= p_per_s <= max_p:
                            best_strings = num_strings
                            best_p_per_s = p_per_s
                            total_panels = adj_count
                            break
                if best_strings > 0:
                    break

        if best_strings == 0:
            best_strings = max(1, inverter.mppt_count)
            best_p_per_s = max(1, total_panels // best_strings)

        voc_c = cold_voc(panel, min_temp_c)
        vmp_h, _ = hot_vmp(panel, max_temp_c)
        vmp_c, _ = cold_vmp(panel, min_temp_c)

        string_voc_cold = round(best_p_per_s * voc_c, 1)
        string_vmp_hot = round(best_p_per_s * vmp_h, 1)
        string_vmp_cold = round(best_p_per_s * vmp_c, 1)
        string_imp = panel.imp
        string_isc = panel.isc

        # MPPT distribution
        mppt_distribution = []
        strings_remaining = best_strings
        for m_idx in range(1, inverter.mppt_count + 1):
            if strings_remaining <= 0:
                mppt_distribution.append({
                    "mppt_number": m_idx,
                    "strings_count": 0,
                    "panels_per_string": 0,
                    "operating_current_a": 0.0,
                    "isc_current_a": 0.0,
                    "status": "UNUSED"
                })
                continue

            allocated = min(inverter.string_inputs_per_mppt, math.ceil(strings_remaining / (inverter.mppt_count - m_idx + 1)))
            allocated = min(allocated, strings_remaining)
            strings_remaining -= allocated

            mppt_imp = round(allocated * string_imp, 2)
            mppt_isc = round(allocated * string_isc, 2)

            status = "PASS"
            if mppt_isc > inverter.max_isc_per_mppt_a:
                status = "FAIL"
            elif mppt_imp > inverter.max_input_current_per_mppt_a:
                status = "WARNING (Clipping)"

            mppt_distribution.append({
                "mppt_number": m_idx,
                "strings_count": allocated,
                "panels_per_string": best_p_per_s,
                "operating_current_a": mppt_imp,
                "isc_current_a": mppt_isc,
                "status": status,
                "label": f"MPPT {m_idx}: {allocated} string(s) × {best_p_per_s} panels ({mppt_imp} A)"
            })

        return {
            "total_panels": total_panels,
            "total_strings": best_strings,
            "panels_per_string": best_p_per_s,
            "string_voc_cold_v": string_voc_cold,
            "string_vmp_hot_v": string_vmp_hot,
            "string_vmp_cold_v": string_vmp_cold,
            "string_imp_a": string_imp,
            "string_isc_a": string_isc,
            "max_dc_voltage_limit_v": inverter.max_dc_voltage_v,
            "mppt_min_limit_v": inverter.mppt_voltage_min_v,
            "mppt_max_limit_v": inverter.mppt_voltage_max_v,
            "mppt_distribution": mppt_distribution,
            "is_valid": (string_voc_cold <= inverter.max_dc_voltage_v and string_vmp_hot >= inverter.mppt_voltage_min_v)
        }

    # ---------------------------------------------------------------------------
    # 5. DC Protection Selection
    # ---------------------------------------------------------------------------
    def select_dc_protection(
        self,
        string_voc_cold: float,
        string_isc: float,
        total_strings: int,
        strings_per_mppt: int = 1,
        phase: int = 1,
        panel_max_fuse: float = 30.0
    ) -> Dict[str, Any]:
        """
        Selects DC isolator, DC SPD, and DC string fuse based on configured master catalog.
        Rule source: IEC 60269-6, BS 7671, and Company Standards.
        """
        prot_rules = self.rules.get("protection_rules", {})
        iso_rules = prot_rules.get("dc_isolator", {})
        spd_rules = prot_rules.get("dc_spd", {})
        fuse_rules = prot_rules.get("dc_fuse", {})

        # --- A. DC Isolator ---
        preferred_pole = "2P" if phase == 1 else "4P"
        min_iso_current = string_isc * 1.25

        iso_candidates = self.components.get("dc_isolators", [])
        valid_isos = [
            iso for iso in iso_candidates
            if iso.get("active", True)
            and iso.get("voltage_rating", 0) >= string_voc_cold
            and iso.get("current_rating", 0) >= min_iso_current
        ]

        valid_isos.sort(key=lambda x: (
            0 if x.get("pole") == preferred_pole else 1,
            0 if x.get("preferred", False) else 1,
            x.get("current_rating", 999),
            x.get("voltage_rating", 999)
        ))

        if valid_isos:
            selected_iso = valid_isos[0]
            iso_status = "PASS"
            iso_reason = f"Rated {selected_iso['voltage_rating']}V / {selected_iso['current_rating']}A exceeds string Voc ({string_voc_cold}V) and Isc ({min_iso_current:.1f}A)."
        else:
            selected_iso = {
                "brand": "BENY",
                "model": f"BYT-32 {preferred_pole} 1000V 32A",
                "pole": preferred_pole,
                "voltage_rating": 1000.0,
                "current_rating": 32.0,
                "description": f"DC Rotary Isolator Switch {preferred_pole} 1000V 32A IP66"
            }
            iso_status = "WARNING"
            iso_reason = "⚠ No exact matching DC isolator found in catalog; defaulted to 1000V 32A."

        iso_quantity = max(1, total_strings)

        # --- B. DC SPD ---
        min_uc = string_voc_cold * spd_rules.get("min_uc_voltage_factor", 1.20)
        spd_candidates = self.components.get("dc_spds", [])
        valid_spds = [
            s for s in spd_candidates
            if s.get("active", True) and s.get("voltage_rating", 0) >= min_uc
        ]
        valid_spds.sort(key=lambda x: (
            0 if x.get("pole") == preferred_pole else 1,
            0 if x.get("preferred", False) else 1,
            x.get("voltage_rating", 999)
        ))

        if valid_spds:
            selected_spd = valid_spds[0]
            spd_status = "PASS"
            spd_reason = f"Uc {selected_spd['voltage_rating']}V >= 1.20 × Voc ({min_uc:.1f}V), In={selected_spd.get('ka_rating', 20)}kA."
        else:
            selected_spd = {
                "brand": "BENY",
                "model": f"BUD-40/{2 if phase == 1 else 4} 1000V",
                "pole": preferred_pole,
                "voltage_rating": 1000.0,
                "ka_rating": 40.0,
                "description": f"DC Surge Protective Device {preferred_pole} 1000V In=20kA Imax=40kA"
            }
            spd_status = "WARNING"
            spd_reason = "⚠ Defaulted to 1000V 40kA DC SPD."

        # --- C. DC Fuse (IEC 60269-6) ---
        fuse_threshold = fuse_rules.get("fuse_required_threshold_parallel_strings", 3)
        fuse_required = (strings_per_mppt >= fuse_threshold) or (total_strings >= 3)
        min_fuse_a = string_isc * fuse_rules.get("min_current_factor", 1.50)

        fuse_candidates = self.components.get("dc_fuses", [])
        valid_fuses = [
            f for f in fuse_candidates
            if f.get("active", True)
            and f.get("current_rating", 0) >= min_fuse_a
            and f.get("current_rating", 0) <= panel_max_fuse
        ]
        valid_fuses.sort(key=lambda x: (
            0 if x.get("preferred", False) else 1,
            x.get("current_rating", 999)
        ))

        if valid_fuses:
            selected_fuse = valid_fuses[0]
            fuse_status = "PASS"
            fuse_reason = f"Rated {selected_fuse['current_rating']}A >= 1.5 × Isc ({min_fuse_a:.1f}A) and <= panel max series fuse ({panel_max_fuse}A)."
        else:
            selected_fuse = {
                "brand": "BENY",
                "model": "BR-30 30A",
                "current_rating": 30.0,
                "voltage_rating": 1000.0,
                "description": "10x38mm gPV Solar String Fuse Link 1000V DC 30A"
            }
            fuse_status = "PASS"
            fuse_reason = f"Standard 30A gPV fuse complying with panel max series fuse ({panel_max_fuse}A)."

        fuse_quantity = total_strings * 2 if fuse_required else 0
        fuse_holder_qty = fuse_quantity

        spd_quantity = max(1, total_strings if phase == 1 else math.ceil(total_strings / max(1, strings_per_mppt)))
        return {
            "dc_isolator": {
                **selected_iso,
                "quantity": iso_quantity,
                "status": iso_status,
                "reason": f"1 Isolator per String ({total_strings} strings = {iso_quantity} nos). {iso_reason}",
                "rule_source": RULE_SOURCE_COMPANY
            },
            "dc_spd": {
                **selected_spd,
                "quantity": spd_quantity,
                "status": spd_status,
                "reason": f"1 SPD per MPPT input/string ({spd_quantity} nos). {spd_reason}",
                "rule_source": RULE_SOURCE_ENGINEERING
            },
            "dc_fuse": {
                **selected_fuse,
                "required": fuse_required,
                "quantity": fuse_quantity,
                "holder_quantity": fuse_holder_qty,
                "status": fuse_status,
                "reason": fuse_reason,
                "rule_source": RULE_SOURCE_ENGINEERING
            }
        }

    # ---------------------------------------------------------------------------
    # 6. AC Protection Selection
    # ---------------------------------------------------------------------------
    def select_ac_protection(
        self,
        inverter: Inverter,
        system_capacity_kw: float,
        phase: int = 3,
        ac_voltage: float = 400.0,
        pf: float = 0.95
    ) -> Dict[str, Any]:
        """
        Calculates AC output current and selects AC isolator, AC SPD, MCB/MCCB,
        and final lockable utility disconnect switch.
        """
        prot_rules = self.rules.get("protection_rules", {})
        breaker_sf = prot_rules.get("ac_breaker", {}).get("min_safety_current_factor", 1.25)
        preferred_pole = "2P" if phase == 1 else "4P"

        if hasattr(inverter, "max_ac_current_a") and inverter.max_ac_current_a > 0:
            rated_ac_current = float(inverter.max_ac_current_a)
            calc_basis = "Inverter datasheet rated AC current"
        else:
            p_w = inverter.rated_ac_power_kw * 1000.0
            if phase == 1:
                rated_ac_current = round(p_w / (ac_voltage * pf), 2)
                calc_basis = f"Formula: P / (V × PF) = {p_w} / ({ac_voltage} × {pf})"
            else:
                rated_ac_current = round(p_w / (math.sqrt(3) * ac_voltage * pf), 2)
                calc_basis = f"Formula: P / (√3 × V × PF) = {p_w} / (1.732 × {ac_voltage} × {pf})"

        design_current_a = round(rated_ac_current * breaker_sf, 2)

        # AC Isolator
        ac_iso_candidates = self.components.get("ac_isolators", [])
        valid_ac_isos = [
            iso for iso in ac_iso_candidates
            if iso.get("active", True)
            and iso.get("pole") == preferred_pole
            and iso.get("current_rating", 0) >= rated_ac_current
        ]
        valid_ac_isos.sort(key=lambda x: (
            0 if x.get("preferred", False) else 1,
            x.get("current_rating", 999)
        ))

        if valid_ac_isos:
            selected_ac_iso = valid_ac_isos[0]
            ac_iso_reason = f"{preferred_pole} {selected_ac_iso['current_rating']}A accommodates rated AC current ({rated_ac_current}A)."
        else:
            cur_rat = 40.0 if rated_ac_current <= 32.0 else 60.0
            selected_ac_iso = {
                "brand": "YRO",
                "model": f"YRO-{preferred_pole}-{int(cur_rat)}A",
                "pole": preferred_pole,
                "voltage_rating": 240.0 if phase == 1 else 415.0,
                "current_rating": cur_rat,
                "description": f"AC Rotary Isolator Switch {preferred_pole} {int(cur_rat)}A IP66 Weatherproof"
            }
            ac_iso_reason = f"{preferred_pole} {int(cur_rat)}A selected for {rated_ac_current}A inverter output."

        # AC SPD
        ac_spd_candidates = self.components.get("ac_spds", [])
        valid_ac_spds = [
            s for s in ac_spd_candidates
            if s.get("active", True) and s.get("pole") == preferred_pole
        ]
        valid_ac_spds.sort(key=lambda x: (
            0 if x.get("preferred", False) else 1,
            x.get("voltage_rating", 999)
        ))

        if valid_ac_spds:
            selected_ac_spd = valid_ac_spds[0]
            ac_spd_reason = f"{preferred_pole} {selected_ac_spd['voltage_rating']}V Class II SPD provides mains surge protection."
        else:
            selected_ac_spd = {
                "brand": "YRO",
                "model": f"YRO-AC-SPD-{preferred_pole}",
                "pole": preferred_pole,
                "voltage_rating": 275.0 if phase == 1 else 385.0,
                "ka_rating": 40.0,
                "description": f"AC Surge Protective Device {preferred_pole} Class II In=20kA Imax=40kA"
            }
            ac_spd_reason = f"{preferred_pole} Type II AC SPD."

        # MCB / MCCB Sizing
        use_mccb = (design_current_a > 63.0) or (system_capacity_kw >= 30.0 and phase == 3)
        target_db = self.components.get("mccbs" if use_mccb else "mcbs", [])

        valid_breakers = [
            b for b in target_db
            if b.get("active", True)
            and b.get("current_rating", 0) >= design_current_a
            and (b.get("pole") == preferred_pole or preferred_pole in b.get("poles", []))
        ]
        valid_breakers.sort(key=lambda x: (
            0 if x.get("preferred", False) else 1,
            x.get("current_rating", 999)
        ))

        if valid_breakers:
            selected_breaker = valid_breakers[0]
            breaker_type = "MCCB" if use_mccb else "MCB"
            breaker_reason = f"{breaker_type} {selected_breaker['current_rating']}A satisfies Ib ({rated_ac_current}A) × 1.25 = {design_current_a}A."
        else:
            std_ratings = [16.0, 20.0, 25.0, 32.0, 40.0, 50.0, 63.0, 80.0, 100.0, 125.0, 160.0, 200.0, 250.0]
            selected_rating = next((r for r in std_ratings if r >= design_current_a), 63.0)
            breaker_type = "MCCB" if selected_rating > 63.0 else "MCB"
            selected_breaker = {
                "brand": "SUNTREE" if breaker_type == "MCB" else "Schneider / ABB",
                "model": f"{breaker_type} {preferred_pole} {int(selected_rating)}A",
                "pole": preferred_pole,
                "current_rating": selected_rating,
                "voltage_rating": 230.0 if phase == 1 else 400.0,
                "description": f"{breaker_type} {preferred_pole} {int(selected_rating)}A 10kA C-Curve"
            }
            breaker_reason = f"{breaker_type} {int(selected_rating)}A sized for design current {design_current_a}A."

        # Final Lockable Utility Isolator (CEB Grid Interconnection)
        lock_candidates = self.components.get("lockable_isolators", [])
        valid_locks = [
            l for l in lock_candidates
            if l.get("active", True)
            and l.get("pole") == preferred_pole
            and l.get("current_rating", 0) >= rated_ac_current
        ]
        valid_locks.sort(key=lambda x: (
            0 if x.get("preferred", False) else 1,
            x.get("current_rating", 999)
        ))

        if valid_locks:
            selected_lock = valid_locks[0]
            lock_reason = f"CEB Grid Code requires padlockable point of isolation ({selected_lock['current_rating']}A {preferred_pole})."
        else:
            lock_rating = 32.0 if (phase == 1 and rated_ac_current <= 30.0) else 63.0
            selected_lock = {
                "brand": "SUNTREE",
                "model": f"LK-{preferred_pole}-{int(lock_rating)}A",
                "pole": preferred_pole,
                "current_rating": lock_rating,
                "voltage_rating": 230.0 if phase == 1 else 400.0,
                "description": f"Padlockable AC Utility Disconnect Switch {preferred_pole} {int(lock_rating)}A IP65"
            }
            lock_reason = f"CEB Grid Code requires padlockable point of isolation ({int(lock_rating)}A {preferred_pole})."

        return {
            "rated_ac_current_a": rated_ac_current,
            "design_current_a": design_current_a,
            "calculation_basis": calc_basis,
            "ac_isolator": {
                **selected_ac_iso,
                "quantity": 1,
                "status": "PASS",
                "reason": ac_iso_reason,
                "rule_source": RULE_SOURCE_ENGINEERING
            },
            "ac_spd": {
                **selected_ac_spd,
                "quantity": 1,
                "status": "PASS",
                "reason": ac_spd_reason,
                "rule_source": RULE_SOURCE_ENGINEERING
            },
            "ac_breaker": {
                **selected_breaker,
                "breaker_type": breaker_type,
                "quantity": 1,
                "status": "PASS",
                "reason": breaker_reason,
                "rule_source": RULE_SOURCE_ENGINEERING
            },
            "lockable_isolator": {
                **selected_lock,
                "quantity": 1,
                "status": "PASS",
                "reason": lock_reason,
                "rule_source": RULE_SOURCE_CEB
            }
        }

    def get_ac_protection_table(self) -> List[Dict[str, Any]]:
        """Returns the configurable AC protection selection table from rules."""
        return self.rules.get("ac_protection_table", [
            {"capacity_kw": 5.0, "phase": "1P", "inverter_output_a": 22.8, "ac_isolator": "40A 2P", "ac_spd": "2P 275V 20/40kA", "mccb_mcb": "32A 2P MCB", "lockable": "32A 2P Padlockable", "lockable_required": True, "editable": True},
            {"capacity_kw": 10.0, "phase": "3P", "inverter_output_a": 15.2, "ac_isolator": "40A 4P", "ac_spd": "4P 385V 20/40kA", "mccb_mcb": "25A 4P MCB", "lockable": "63A 4P Padlockable", "lockable_required": True, "editable": True},
            {"capacity_kw": 20.0, "phase": "3P", "inverter_output_a": 30.4, "ac_isolator": "63A 4P", "ac_spd": "4P 385V 20/40kA", "mccb_mcb": "40A 4P MCB", "lockable": "63A 4P Padlockable", "lockable_required": True, "editable": True},
            {"capacity_kw": 30.0, "phase": "3P", "inverter_output_a": 45.6, "ac_isolator": "63A 4P", "ac_spd": "4P 385V 20/40kA", "mccb_mcb": "63A 4P MCB", "lockable": "63A 4P Padlockable", "lockable_required": True, "editable": True},
            {"capacity_kw": 50.0, "phase": "3P", "inverter_output_a": 76.0, "ac_isolator": "100A 4P", "ac_spd": "4P 385V 20/40kA", "mccb_mcb": "100A 4P MCCB", "lockable": "100A 4P Padlockable", "lockable_required": True, "editable": True},
            {"capacity_kw": 100.0, "phase": "3P", "inverter_output_a": 152.0, "ac_isolator": "200A 4P", "ac_spd": "4P 385V 20/40kA", "mccb_mcb": "200A 4P MCCB", "lockable": "200A 4P Padlockable", "lockable_required": True, "editable": True}
        ])

    def save_ac_protection_table(self, table_data: List[Dict[str, Any]]) -> bool:
        """Saves updated AC protection table to rules file."""
        try:
            self.rules["ac_protection_table"] = table_data
            with open(RULES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, indent=2)
            return True
        except Exception:
            return False

    def select_rf_production_equipment(
        self,
        system_capacity_kw: float,
        phase: int = 1,
        inverter: Optional[Inverter] = None,
        grid_arrangement: str = "Net Metering"
    ) -> List[Dict[str, Any]]:
        """
        Structured equipment-selection system for RF / Production-related equipment:
        - System capacity
        - Inverter type / quantity
        - Single-phase / three-phase
        - Grid connection arrangement
        - Required monitoring/communication
        - Required production/metering equipment
        """
        rf_rules = self.rules.get("rf_production_rules", {})
        comm_rules = rf_rules.get("communication", {})
        meter_rules = rf_rules.get("metering", {})
        ct_rules = rf_rules.get("ct_sensors", {})
        cable_rules = rf_rules.get("communication_cable", {})

        items = []

        # 1. Monitoring / Datalogger
        if system_capacity_kw <= 15.0:
            c_data = comm_rules.get("residential", {
                "type": "Wi-Fi Datalogger Stick",
                "brand": "Sunways",
                "model": "DLS-W WiFi Stick IP65",
                "description": "Plug & Play Wi-Fi Datalogger Stick for Remote Monitoring via Cloud Portal",
                "specification": "2.4GHz Wi-Fi / IP65",
                "unit": "nos",
                "quantity": 1
            })
            comm_remarks = "Plug & play wireless inverter monitoring"
        else:
            c_data = comm_rules.get("commercial", {
                "type": "4G/LTE Cellular Gateway",
                "brand": "Sunways / Approved Standard",
                "model": "DLS-4G Wireless Gateway",
                "description": "4G/LTE Cellular Remote Communications Gateway for Commercial Solar Plants",
                "specification": "4G LTE / RS485 / IP65",
                "unit": "nos",
                "quantity": 1
            })
            comm_remarks = "Commercial cellular datalogger gateway"

        items.append({
            "category": "RF / Production",
            "item_name": "Datalogger / Communication",
            "description": c_data["description"],
            "brand": c_data["brand"],
            "model": c_data["model"],
            "specification": c_data["specification"],
            "capacity": c_data["specification"],
            "rating": c_data["specification"],
            "unit": c_data.get("unit", "nos"),
            "quantity": c_data.get("quantity", 1),
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": comm_remarks,
            "rule_source": RULE_SOURCE_COMPANY,
            "mode": "AUTO"
        })

        # 2. Bi-directional / Production Meter
        if phase == 1:
            m_data = meter_rules.get("single_phase", {
                "type": "Single Phase Bi-directional Smart Energy Meter",
                "brand": "Chint / Acrel / Eastron",
                "model": "DDSU666 Single Phase",
                "description": "Single Phase Bi-directional DIN-rail Smart Energy Meter with RS485 Modbus",
                "specification": "230V 5(80)A Class 1.0 RS485",
                "unit": "nos",
                "quantity": 1
            })
            meter_remarks = "CEB/LECO Single Phase Bi-directional Net Metering"
            meter_source = RULE_SOURCE_COMPANY
        elif system_capacity_kw <= 20.0:
            m_data = meter_rules.get("three_phase_direct_30a", {
                "type": "Three Phase Direct Bi-directional Smart Energy Meter (30A)",
                "brand": "Chint / Acrel / Eastron",
                "model": "DTSU666 Three Phase (30A)",
                "description": "Three Phase 4-Wire Bi-directional Smart Energy Meter with RS485 Modbus (30A)",
                "specification": "3x230/400V 5(80)A Class 1.0 RS485",
                "unit": "nos",
                "quantity": 1
            })
            meter_remarks = "CEB/LECO 3-Phase 30A Bi-directional Net Metering"
            meter_source = RULE_SOURCE_COMPANY
        elif system_capacity_kw <= 40.0:
            m_data = meter_rules.get("three_phase_direct_60a", {
                "type": "Three Phase Direct Bi-directional Smart Energy Meter (60A)",
                "brand": "Chint / Acrel / Eastron",
                "model": "DTSU666 Three Phase (60A)",
                "description": "Three Phase 4-Wire Bi-directional Smart Energy Meter with RS485 Modbus (60A)",
                "specification": "3x230/400V 5(80)A Class 1.0 RS485",
                "unit": "nos",
                "quantity": 1
            })
            meter_remarks = "CEB/LECO 3-Phase 60A Bi-directional Net Metering"
            meter_source = RULE_SOURCE_COMPANY
        else:
            m_data = meter_rules.get("utility_ct_meter", {
                "type": "CEB / Utility Grade CT-Operated Bi-directional Tariff Meter",
                "brand": "CEB / Utility Approved",
                "model": "Premier 300 / Mk10 Class 0.2s/0.5s",
                "description": "3-Phase 4-Wire CT-Operated Bi-directional Tariff Energy Meter with Remote GSM Modem",
                "specification": "3x230/400V -/5A Class 0.2s/0.5s IEC 62053-22",
                "unit": "nos",
                "quantity": 1
            })
            meter_remarks = "CEB/LECO Utility Interconnection Review Required (> 40 kW)"
            meter_source = RULE_SOURCE_CEB

        items.append({
            "category": "RF / Production",
            "item_name": "Bi-directional Smart Meter",
            "description": m_data["description"],
            "brand": m_data["brand"],
            "model": m_data["model"],
            "specification": m_data["specification"],
            "capacity": m_data["specification"],
            "rating": m_data["specification"],
            "unit": m_data.get("unit", "nos"),
            "quantity": m_data.get("quantity", 1),
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": meter_remarks,
            "rule_source": meter_source,
            "mode": "AUTO"
        })

        # 3. Current Transformers (CT Sensors)
        if phase == 1:
            ct_data = ct_rules.get("single_phase", {
                "type": "Split-Core Current Transformer",
                "brand": "Approved Standard",
                "model": "CT-100A/50mA",
                "description": "Split-Core Current Transformer 100A / 50mA for Zero-Export / Production Sensing",
                "specification": "100A / 50mA Split Core",
                "unit": "nos",
                "quantity": 1
            })
            ct_remarks = "1x CT sensor for single-phase export sensing"
        elif system_capacity_kw <= 40.0:
            ct_data = ct_rules.get("three_phase_direct", {
                "type": "Split-Core Current Transformer Set",
                "brand": "Approved Standard",
                "model": "CT-100A/5A Set (3x)",
                "description": "Split-Core Current Transformer Set (3 nos) for 3-Phase Export / Production Sensing",
                "specification": "100A / 5A Split Core (3x)",
                "unit": "set",
                "quantity": 1
            })
            ct_remarks = "3x CT sensors for 3-phase export sensing"
        else:
            ct_data = ct_rules.get("three_phase_ct", {
                "type": "Utility Metering Class Current Transformer Set",
                "brand": "CEB Approved Standard",
                "model": "CT-Class 0.2s 200/5A Set (3x)",
                "description": "Class 0.2s Utility Current Transformers (3 nos) for Interconnection Tariff Metering",
                "specification": "Class 0.2s / 5VA 200/5A (3x)",
                "unit": "set",
                "quantity": 1
            })
            ct_remarks = "3x Class 0.2s CTs subject to CEB utility approval"

        items.append({
            "category": "RF / Production",
            "item_name": "Current Transformer (CT)",
            "description": ct_data["description"],
            "brand": ct_data["brand"],
            "model": ct_data["model"],
            "specification": ct_data["specification"],
            "capacity": ct_data["specification"],
            "rating": ct_data["specification"],
            "unit": ct_data.get("unit", "nos"),
            "quantity": ct_data.get("quantity", 1),
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": ct_remarks,
            "rule_source": RULE_SOURCE_ENGINEERING,
            "mode": "AUTO"
        })

        # 4. RS485 Communication Cable
        cable_m = cable_rules.get("estimated_m_residential", 15.0) if system_capacity_kw <= 15.0 else cable_rules.get("estimated_m_commercial", 30.0)
        items.append({
            "category": "RF / Production",
            "item_name": "RS485 Communication Cable",
            "description": cable_rules.get("description", "1-Pair 24AWG Shielded Twisted Pair RS485 Modbus Cable with Drain Wire"),
            "brand": cable_rules.get("brand", "Belden / Equivalent"),
            "model": cable_rules.get("model", "9841 Shielded Twisted Pair"),
            "specification": cable_rules.get("specification", "1P 24AWG Shielded RS485"),
            "capacity": "300V RS485",
            "rating": "RS485 Modbus",
            "unit": cable_rules.get("unit", "meter"),
            "quantity": float(cable_m),
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": "Inverter to meter / datalogger communication",
            "rule_source": RULE_SOURCE_INSTALLER,
            "mode": "AUTO"
        })

        return items

    def validate_system_configuration(
        self,
        panel: Panel,
        inverter: Inverter,
        string_info: Dict[str, Any],
        dc_prot: Dict[str, Any],
        ac_prot: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Validates electrical and protection compatibility.
        Returns list of warnings / failures: ⚠️ Configuration not recommended.
        """
        warnings = []

        # 1. Max DC Voltage Check
        voc_cold = string_info.get("string_voc_cold_v", 0.0)
        if voc_cold > inverter.max_dc_voltage_v:
            warnings.append({
                "severity": "FAIL",
                "parameter": "Max DC Voltage",
                "message": f"String Voc cold ({voc_cold:.1f} V) exceeds inverter maximum DC input ({inverter.max_dc_voltage_v:.1f} V). High risk of inverter overvoltage damage!"
            })
        elif voc_cold > inverter.max_dc_voltage_v * 0.95:
            warnings.append({
                "severity": "WARNING",
                "parameter": "Max DC Voltage Margin",
                "message": f"String Voc cold ({voc_cold:.1f} V) is within 5% of inverter maximum ({inverter.max_dc_voltage_v:.1f} V)."
            })

        # 2. MPPT Voltage Window
        vmp_hot = string_info.get("string_vmp_hot_v", 0.0)
        if vmp_hot < inverter.mppt_voltage_min_v:
            warnings.append({
                "severity": "FAIL",
                "parameter": "MPPT Minimum Voltage",
                "message": f"String Vmp hot ({vmp_hot:.1f} V) drops below inverter MPPT minimum ({inverter.mppt_voltage_min_v:.1f} V). Inverter will fail to track peak power under high temperatures."
            })

        vmp_cold = string_info.get("string_vmp_cold_v", 0.0)
        if vmp_cold > inverter.mppt_voltage_max_v:
            warnings.append({
                "severity": "WARNING",
                "parameter": "MPPT Maximum Voltage",
                "message": f"String Vmp cold ({vmp_cold:.1f} V) exceeds inverter MPPT upper limit ({inverter.mppt_voltage_max_v:.1f} V)."
            })

        # 3. MPPT Current Check
        imp = string_info.get("string_imp_a", 0.0)
        if imp > inverter.max_input_current_per_mppt_a:
            warnings.append({
                "severity": "WARNING",
                "parameter": "MPPT Current Clipping",
                "message": f"String Imp ({imp:.2f} A) exceeds inverter MPPT rating ({inverter.max_input_current_per_mppt_a:.1f} A). Current will be clipped during peak irradiance."
            })

        isc = string_info.get("string_isc_a", 0.0)
        if isc > inverter.max_isc_per_mppt_a:
            warnings.append({
                "severity": "FAIL",
                "parameter": "MPPT Short Circuit Current",
                "message": f"String Isc ({isc:.2f} A) exceeds inverter absolute Isc limit ({inverter.max_isc_per_mppt_a:.1f} A). Violates equipment warranty and safety."
            })

        # 4. DC Protection Rating Check
        iso = dc_prot.get("dc_isolator", {})
        if iso.get("status") == "FAIL":
            warnings.append({
                "severity": "FAIL",
                "parameter": "DC Isolator",
                "message": f"DC Isolator rating insufficient: {iso.get('reason', '')}"
            })

        # 5. AC Protection Rating Check
        brk = ac_prot.get("ac_breaker", {})
        if brk.get("status") == "FAIL":
            warnings.append({
                "severity": "FAIL",
                "parameter": "AC Breaker",
                "message": f"AC Breaker rating insufficient: {brk.get('reason', '')}"
            })

        return warnings

    # ---------------------------------------------------------------------------
    # 7. BoS & Installation Materials Takeoff
    # ---------------------------------------------------------------------------
    def calculate_bos_quantities(
        self,
        total_panels: int,
        total_strings: int,
        inverter_units: int = 1,
        installation_type: str = "rooftop",
        dc_cable_len_per_string_m: float = 30.0,
        ac_cable_len_m: float = 20.0,
        earth_cable_len_m: float = 25.0
    ) -> List[Dict[str, Any]]:
        """
        Calculates mounting structure hardware, fasteners, conduits, and accessories
        matching the sample BOQ structure.
        """
        bos_rules = self.rules.get("bos_takeoff_rules", {})
        cable_catalog = {item["id"]: item for item in self.components.get("cables", [])}

        items = []

        # Cables
        dc_tot_m = round(total_strings * dc_cable_len_per_string_m * 2, 0)
        c_dc = cable_catalog.get("cable-dc-4mm2" if total_strings <= 2 else "cable-dc-6mm2", {})
        items.append({
            "category": "Power Cable items",
            "item_name": "DC Wire B/R",
            "description": c_dc.get("description", "4mm² / 6mm² 1500V DC Solar Cable Black/Red"),
            "brand": c_dc.get("brand", "Kelani Cables"),
            "model": c_dc.get("model", "H1Z2Z2-K"),
            "specification": "4|6| mm",
            "rating": "1500V DC UV-Resistant",
            "unit": "meter",
            "quantity": dc_tot_m,
            "rule_source": RULE_SOURCE_ENGINEERING,
            "remarks": f"{total_strings} strings × {dc_cable_len_per_string_m}m × 2"
        })

        items.append({
            "category": "Power Cable items",
            "item_name": "Earth wire",
            "description": "10mm² / 16mm² Single Core Copper Earthing Cable Green/Yellow",
            "brand": "Kelani Cables",
            "model": "Cu/PVC Earth",
            "specification": "6|10|16mm",
            "rating": "600/1000V",
            "unit": "meter",
            "quantity": earth_cable_len_m,
            "rule_source": RULE_SOURCE_ENGINEERING,
            "remarks": "Array & inverter grounding"
        })

        items.append({
            "category": "Power Cable items",
            "item_name": "AC wire",
            "description": "Multicore Copper XLPE/PVC AC Cable to main switchboard",
            "brand": "Kelani Cables",
            "model": "4C Cu/XLPE/PVC",
            "specification": "6|10|16mm",
            "rating": "600/1000V",
            "unit": "meter",
            "quantity": ac_cable_len_m,
            "rule_source": RULE_SOURCE_ENGINEERING,
            "remarks": "Inverter output run"
        })

        # DC Side Accessories
        mc4_qty = total_strings * bos_rules.get("mc4_pairs_per_string", 2)
        items.append({
            "category": "DC Side",
            "item_name": "MC4 Connector",
            "description": "PV MC4 Connector Pair Male & Female 1500V 30A IP68",
            "brand": "Staubli / Equivalent",
            "model": "MC4-Evo2",
            "specification": "1500V DC 30A IP68",
            "rating": "30A",
            "unit": "pair",
            "quantity": mc4_qty,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": f"2 pairs per string × {total_strings} strings"
        })

        items.append({
            "category": "DC Side",
            "item_name": "Earth Rod",
            "description": "Copper Bonded Steel Earth Rod 5/8 inch dia x 8 ft with brass clamp",
            "brand": "Approved Standard",
            "model": "5/8in x 8ft",
            "specification": "5/8\" x 8ft Copper Clad",
            "rating": "BS 7430",
            "unit": "nos",
            "quantity": bos_rules.get("earth_rods_default", 2),
            "rule_source": RULE_SOURCE_CEB,
            "remarks": "Earthing electrode pit"
        })

        # AC Side Enclosures
        items.append({
            "category": "AC Side",
            "item_name": "Bus Bar Box",
            "description": "Tinned Copper Busbar Enclosure with neutral & earth links",
            "brand": "Approved Standard",
            "model": "Tinned Copper Busbar",
            "specification": "Copper Busbar Box",
            "rating": "100A / 160A",
            "unit": "nos",
            "quantity": 1,
            "rule_source": RULE_SOURCE_ENGINEERING,
            "remarks": "AC distribution connection"
        })

        items.append({
            "category": "AC Side",
            "item_name": "ABC Box",
            "description": "Weatherproof IP65 Surface Mount DB Box (ABC Box)",
            "brand": "Approved Standard",
            "model": "ABC DB Box",
            "specification": "4|9|12",
            "rating": "IP65",
            "unit": "ways",
            "quantity": 12 if total_panels >= 20 else 9,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Protection component housing"
        })

        items.append({
            "category": "AC Side",
            "item_name": "Steel Box",
            "description": "Powder Coated Steel Distribution Box 2|3|4 Rows IP65",
            "brand": "Approved Standard",
            "model": "Steel DB Enclosure",
            "specification": "2|3|4",
            "rating": "IP65",
            "unit": "raws",
            "quantity": 2,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Switchgear housing"
        })

        # Aluminium Mounting Materials
        bars_qty = math.ceil((total_panels * bos_rules.get("rails_meters_per_panel", 2.30)) / 4.2)
        items.append({
            "category": "Aluminium",
            "item_name": "Bar",
            "description": "Anodized Aluminium Mounting Rail Profile 6005-T5 (4.2m length)",
            "brand": "Aluminium 6005-T5",
            "model": "Rail 4.2m",
            "specification": "6005-T5 Anodized",
            "rating": "Structural Grade",
            "unit": "bar",
            "quantity": max(2, bars_qty),
            "rule_source": RULE_SOURCE_COMPANY,
            "remarks": "Module supporting rails"
        })

        mid_clamps_qty = max(2, (total_panels - 2) * 2) if total_panels > 2 else 2
        items.append({
            "category": "Aluminium",
            "item_name": "Mid Clamp",
            "description": "Aluminium Mid Clamp with SS304 Allen Bolt & Spring Nut",
            "brand": "Aluminium 6005-T5",
            "model": "Mid Clamp 30/35mm",
            "specification": "30mm / 35mm",
            "rating": "Aluminium / SS304",
            "unit": "nos",
            "quantity": mid_clamps_qty,
            "rule_source": RULE_SOURCE_COMPANY,
            "remarks": "Inter-module clamping"
        })

        end_clamps_qty = 4 * max(1, math.ceil(total_panels / 10))
        items.append({
            "category": "Aluminium",
            "item_name": "End Clamp",
            "description": "Aluminium End Clamp with SS304 Allen Bolt & Spring Nut",
            "brand": "Aluminium 6005-T5",
            "model": "End Clamp 30/35mm",
            "specification": "30mm / 35mm",
            "rating": "Aluminium / SS304",
            "unit": "nos",
            "quantity": end_clamps_qty,
            "rule_source": RULE_SOURCE_COMPANY,
            "remarks": "Array outer clamping"
        })

        items.append({
            "category": "Aluminium",
            "item_name": "Ceat Clip",
            "description": "SUS304 Stainless Steel Solar Cable Clip for Rail & Module",
            "brand": "Stainless Steel 304",
            "model": "Solar Cable Clip",
            "specification": "SUS304 Clip",
            "rating": "UV Proof",
            "unit": "nos",
            "quantity": total_panels * 2,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "String cable retention"
        })

        items.append({
            "category": "Aluminium",
            "item_name": "Serrated Angle Clamp",
            "description": "Serrated Aluminium L-Foot / Angle Clamp with EPDM rubber pad",
            "brand": "Aluminium 6005-T5",
            "model": "L-Foot Bracket",
            "specification": "Serrated Aluminium",
            "rating": "M10 Fastener",
            "unit": "nos",
            "quantity": max(4, math.ceil(total_panels * 1.5)),
            "rule_source": RULE_SOURCE_COMPANY,
            "remarks": "Roof fixing attachment"
        })

        items.append({
            "category": "Aluminium",
            "item_name": "Splicer",
            "description": "Aluminium Rail Splicer with SS304 Hardware",
            "brand": "Aluminium 6005-T5",
            "model": "Rail Splice Kit",
            "specification": "Rail Connector",
            "rating": "Structural Grade",
            "unit": "nos",
            "quantity": max(2, bars_qty - 2) if bars_qty > 2 else 2,
            "rule_source": RULE_SOURCE_COMPANY,
            "remarks": "Rail extension joining"
        })

        if "tile" in installation_type.lower():
            items.append({
                "category": "Aluminium",
                "item_name": "Tile hook",
                "description": "Heavy Duty Adjustable Stainless Steel Tile Hook",
                "brand": "SUS304 Stainless Steel",
                "model": "Roof Tile Hook",
                "specification": "SUS304 Heavy Duty",
                "rating": "SUS304",
                "unit": "nos",
                "quantity": max(4, math.ceil(total_panels * 1.5)),
                "rule_source": RULE_SOURCE_COMPANY,
                "remarks": "Tile roof purlin anchor"
            })
        else:
            items.append({
                "category": "Aluminium",
                "item_name": "Panel Z Bracket Double",
                "description": "Panel Z-Bracket Double for sheet metal / flat roof",
                "brand": "Aluminium 6005-T5",
                "model": "Z Bracket Double",
                "specification": "Aluminium Z-Bracket",
                "rating": "Double Fixing",
                "unit": "nos",
                "quantity": max(4, math.ceil(total_panels * 1.2)),
                "rule_source": RULE_SOURCE_COMPANY,
                "remarks": "Sheet roof mounting anchor"
            })
            items.append({
                "category": "Aluminium",
                "item_name": "Panel Z Bracket Single",
                "description": "Panel Z-Bracket Single for sheet metal / flat roof",
                "brand": "Aluminium 6005-T5",
                "model": "Z Bracket Single",
                "specification": "Aluminium Z-Bracket",
                "rating": "Single Fixing",
                "unit": "nos",
                "quantity": 4,
                "rule_source": RULE_SOURCE_COMPANY,
                "remarks": "Corner / edge fixing"
            })

        nut_bolt_qty = total_panels * 4
        items.append({
            "category": "Aluminium",
            "item_name": "Nut",
            "description": "SS304 M8 Flange Locking Nut",
            "brand": "SUS304",
            "model": "M8 Flange Nut",
            "specification": "M8 Stainless Steel",
            "rating": "SS304",
            "unit": "nos",
            "quantity": nut_bolt_qty,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Structure bolting"
        })
        items.append({
            "category": "Aluminium",
            "item_name": "Bolt",
            "description": "SS304 M8 Hex Socket Head Allen Bolt",
            "brand": "SUS304",
            "model": "M8 Allen Bolt",
            "specification": "M8 x 25/30mm",
            "rating": "SS304",
            "unit": "nos",
            "quantity": nut_bolt_qty,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Structure bolting"
        })
        items.append({
            "category": "Aluminium",
            "item_name": "Amana screw",
            "description": "Self-Drilling Screw with EPDM Sealing Washer",
            "brand": "Ruspert Coated",
            "model": "Amana Screw",
            "specification": "Self-Drilling with EPDM",
            "rating": "Corrosion Resistant",
            "unit": "nos",
            "quantity": max(10, math.ceil(total_panels * 2.5)),
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Sheet roofing fastening"
        })

        # PVC Conduits & Accessories (Sheet 2)
        pvc_bars = max(3, math.ceil(total_strings * 2.5))
        items.append({
            "category": "PVC",
            "item_name": "PVC pipe",
            "description": "Heavy Duty Rigid PVC Electrical Conduit Pipe 1 inch",
            "brand": "National / Equivalent",
            "model": "1 inch Conduit",
            "specification": "1'",
            "rating": "Heavy Duty",
            "unit": "bar",
            "quantity": pvc_bars,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Cable containment"
        })
        items.append({
            "category": "PVC",
            "item_name": "Joint",
            "description": "Rigid PVC Conduit Straight Coupling 1 inch",
            "brand": "National / Equivalent",
            "model": "1 inch Joint",
            "specification": "1'",
            "rating": "Fittings",
            "unit": "nos",
            "quantity": max(4, pvc_bars),
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Conduit extension"
        })
        items.append({
            "category": "PVC",
            "item_name": "Bend",
            "description": "Rigid PVC Conduit Normal Bend 90 deg 1 inch",
            "brand": "National / Equivalent",
            "model": "1 inch Bend",
            "specification": "1'",
            "rating": "Fittings",
            "unit": "nos",
            "quantity": 6,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Directional change"
        })
        items.append({
            "category": "PVC",
            "item_name": "Casing",
            "description": "PVC Solid Electrical Casing Trunking 50x25mm",
            "brand": "National / Equivalent",
            "model": "50*25 Casing",
            "specification": "50*25",
            "rating": "Trunking",
            "unit": "bar",
            "quantity": 4,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Indoor surface routing"
        })
        items.append({
            "category": "PVC",
            "item_name": "Flexible hose",
            "description": "UV Resistant Corrugated Flexible Conduit 1 inch",
            "brand": "National / Equivalent",
            "model": "1 inch Flexible",
            "specification": "1'",
            "rating": "UV Protected",
            "unit": "meter",
            "quantity": 10.0,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Inverter & box connection"
        })
        items.append({
            "category": "PVC",
            "item_name": "GI clip",
            "description": "Galvanized Iron Heavy Duty Saddle Conduit Clip 1 inch",
            "brand": "Galvanized Iron",
            "model": "1 inch GI Clip",
            "specification": "1'",
            "rating": "Galvanized",
            "unit": "nos",
            "quantity": max(12, pvc_bars * 4),
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Wall / purlin conduit fixing"
        })
        items.append({
            "category": "PVC",
            "item_name": "Sun Box",
            "description": "IP65 Weatherproof Terminal Junction Box (Sun Box 3x3)",
            "brand": "Approved Standard",
            "model": "Sun Box 3*3",
            "specification": "3*3",
            "rating": "IP65",
            "unit": "nos",
            "quantity": 2,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "String junction / transition"
        })
        items.append({
            "category": "PVC",
            "item_name": "Plug Point",
            "description": "13A Industrial Weatherproof Switched Socket Outlet IP66",
            "brand": "Approved Standard",
            "model": "13A Weatherproof Socket",
            "specification": "13A",
            "rating": "IP66",
            "unit": "nos",
            "quantity": 1,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Maintenance utility supply"
        })
        items.append({
            "category": "PVC",
            "item_name": "Wire gland (PG)",
            "description": "Nylon Cable Gland with Locknut IP68 PG16/PG21",
            "brand": "Approved Standard",
            "model": "PG16/PG21",
            "specification": "PG Gland",
            "rating": "IP68",
            "unit": "nos",
            "quantity": max(6, total_strings * 2 + 4),
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Enclosure cable entry sealing"
        })
        items.append({
            "category": "PVC",
            "item_name": "NO leak Tape",
            "description": "Self-Amalgamating Waterproof & Insulation Sealing Tape",
            "brand": "Approved Standard",
            "model": "Waterproof Tape",
            "specification": "No Leak Tape",
            "rating": "Waterproof",
            "unit": "nos",
            "quantity": 2,
            "rule_source": RULE_SOURCE_INSTALLER,
            "remarks": "Weatherproofing sealing"
        })

        return items

    # ---------------------------------------------------------------------------
    # 8. Master BOQ Generator
    # ---------------------------------------------------------------------------
    def generate_boq(
        self,
        project_inputs: Dict[str, Any],
        user_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the complete, end-to-end BOM generation workflow.
        """
        overrides = user_overrides or {}

        capacity_kw = float(project_inputs.get("system_capacity_kw", 5.0))
        installation_type = project_inputs.get("installation_type", "rooftop")
        oversize_val = project_inputs.get("dc_oversizing_factor", None)

        phase_info = self.select_phase(capacity_kw)
        phase = int(project_inputs.get("phase", phase_info["phase"]))

        inverter = project_inputs.get("inverter")
        if inverter is None:
            inverter = self._get_default_inverter(capacity_kw, phase)

        dc_target = self.calculate_dc_target(inverter.rated_ac_power_kw, installation_type, oversize_val)
        target_dc_kwp = dc_target["target_dc_kwp"]

        panel = project_inputs.get("panel")
        min_temp = float(project_inputs.get("min_design_temp_c", -30.0))
        max_temp = float(project_inputs.get("max_design_temp_c", 60.0))

        panel_options = self.optimize_panel_selection(target_dc_kwp, inverter, min_temp, max_temp)
        recommended_opt = next((p for p in panel_options if p["recommendation"] == "Recommended"), panel_options[0] if panel_options else None)

        if panel is None:
            p_630 = next((p for p in self.get_available_panels() if abs(p.rated_power_wp - 630.0) < 2.0), None)
            if p_630:
                panel = p_630
            elif recommended_opt and recommended_opt.get("panel"):
                panel = recommended_opt["panel"]
            else:
                panel = self.get_available_panels()[0]

        # Determine total panels
        if "panel_count" in overrides and overrides["panel_count"] > 0:
            total_panels = int(overrides["panel_count"])
        else:
            matching_opt = next((p for p in panel_options if p["panel"].id == panel.id and p.get("panel_count", 0) > 0), None)
            if matching_opt:
                total_panels = matching_opt["panel_count"]
            else:
                raw_c = math.ceil(target_dc_kwp / (panel.rated_power_wp / 1000.0))
                if inverter.mppt_count == 2 and raw_c % 2 != 0:
                    raw_c += 1
                total_panels = raw_c

        string_info = self.calculate_string_and_mppt(panel, inverter, total_panels, min_temp, max_temp)
        total_strings = string_info["total_strings"]
        panels_per_str = string_info["panels_per_string"]
        actual_dc_kwp = round(total_panels * panel.rated_power_wp / 1000.0, 3)
        dc_ac_ratio = round(actual_dc_kwp / inverter.rated_ac_power_kw, 3)

        dc_prot = self.select_dc_protection(
            string_voc_cold=string_info["string_voc_cold_v"],
            string_isc=panel.isc,
            total_strings=total_strings,
            strings_per_mppt=max(1, math.ceil(total_strings / inverter.mppt_count)),
            phase=phase,
            panel_max_fuse=panel.max_series_fuse
        )

        ac_prot = self.select_ac_protection(
            inverter=inverter,
            system_capacity_kw=capacity_kw,
            phase=phase,
            ac_voltage=inverter.ac_voltage,
            pf=getattr(inverter, "pf", 0.95)
        )

        bos_items = self.calculate_bos_quantities(
            total_panels=total_panels,
            total_strings=total_strings,
            inverter_units=1,
            installation_type=installation_type,
            dc_cable_len_per_string_m=float(project_inputs.get("dc_cable_len_per_string_m", 30.0)),
            ac_cable_len_m=float(project_inputs.get("ac_cable_len_m", 20.0)),
            earth_cable_len_m=float(project_inputs.get("earth_cable_len_m", 25.0))
        )

        boq_items = []
        sn = 1

        # S/N 1: Panel
        boq_items.append({
            "sn": sn,
            "category": "Solar PV Modules",
            "item_name": "Panel",
            "description": f"{panel.rated_power_wp}Wp Solar PV Module",
            "brand": panel.manufacturer,
            "model": panel.model,
            "specification": f"{panel.rated_power_wp}Wp, Voc={panel.voc}V, Vmp={panel.vmp}V",
            "capacity": f"{panel.rated_power_wp}W",
            "rating": f"{panel.rated_power_wp}W",
            "unit": "nos",
            "quantity": total_panels,
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": f"{total_strings} strings × {panels_per_str} modules (Total: {actual_dc_kwp:.2f} kWp)",
            "rule_source": RULE_SOURCE_COMPANY
        })
        sn += 1

        # S/N 2: Inverter
        boq_items.append({
            "sn": sn,
            "category": "Inverter",
            "item_name": "Inverter",
            "description": f"{inverter.rated_ac_power_kw}kW {'Single Phase' if phase == 1 else '3-Phase'} Grid-tie Inverter",
            "brand": inverter.manufacturer,
            "model": inverter.model,
            "specification": f"{inverter.rated_ac_power_kw}kW AC, {inverter.mppt_count} MPPT, Max DC: {inverter.max_dc_voltage_v}V",
            "capacity": f"{inverter.rated_ac_power_kw}kW",
            "rating": f"{inverter.rated_ac_power_kw}kW",
            "unit": "nos",
            "quantity": 1,
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": f"DC/AC Ratio: {dc_ac_ratio:.2f}",
            "rule_source": RULE_SOURCE_COMPANY
        })
        sn += 1

        # S/N 3: DC Isolator
        dc_iso = dc_prot["dc_isolator"]
        boq_items.append({
            "sn": sn,
            "category": "DC Side",
            "item_name": "Isolator",
            "description": dc_iso["description"],
            "brand": dc_iso["brand"],
            "model": dc_iso["model"],
            "specification": f"{dc_iso['pole']} {dc_iso['voltage_rating']}V {dc_iso['current_rating']}A",
            "capacity": f"{dc_iso['voltage_rating']}V",
            "rating": f"{dc_iso['current_rating']}A",
            "unit": "nos",
            "quantity": dc_iso["quantity"],
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": f"1 per string (Voc: {string_info['string_voc_cold_v']}V)",
            "rule_source": dc_iso["rule_source"]
        })
        sn += 1

        # S/N 4: DC SPD
        dc_spd = dc_prot["dc_spd"]
        boq_items.append({
            "sn": sn,
            "category": "DC Side",
            "item_name": "SPD",
            "description": dc_spd["description"],
            "brand": dc_spd["brand"],
            "model": dc_spd["model"],
            "specification": f"{dc_spd['pole']} {dc_spd['voltage_rating']}V 20/40kA",
            "capacity": f"{dc_spd['voltage_rating']}V",
            "rating": f"{dc_spd.get('ka_rating', 40)}kA",
            "unit": "nos",
            "quantity": dc_spd["quantity"],
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": "DC surge protection",
            "rule_source": dc_spd["rule_source"]
        })
        sn += 1

        # S/N 5: DC Fuse
        dc_fuse = dc_prot["dc_fuse"]
        if dc_fuse["required"] or dc_fuse["quantity"] > 0:
            boq_items.append({
                "sn": sn,
                "category": "DC Side",
                "item_name": "Fuse ",
                "description": dc_fuse["description"],
                "brand": dc_fuse["brand"],
                "model": dc_fuse["model"],
                "specification": f"10x38mm gPV {dc_fuse['voltage_rating']}V {dc_fuse['current_rating']}A",
                "capacity": f"{dc_fuse['voltage_rating']}V",
                "rating": f"{dc_fuse['current_rating']}A",
                "unit": "nos",
                "quantity": dc_fuse["quantity"],
                "unit_price": "",
                "total_price": "",
                "supplier": "",
                "remarks": "String overcurrent protection",
                "rule_source": dc_fuse["rule_source"]
            })
            sn += 1

            boq_items.append({
                "sn": sn,
                "category": "DC Side",
                "item_name": "Fuse Holder",
                "description": "Modular 10x38mm DC Fuse Holder 1000V 32A 1-Pole DIN Rail",
                "brand": "BENY",
                "model": "BR-30 Holder",
                "specification": "1000V 32A 1P DIN Rail",
                "capacity": "1000V",
                "rating": "32A",
                "unit": "nos",
                "quantity": dc_fuse["holder_quantity"],
                "unit_price": "",
                "total_price": "",
                "supplier": "",
                "remarks": "DIN rail fuse mounting",
                "rule_source": RULE_SOURCE_ENGINEERING
            })
            sn += 1

        # S/N 7: MC4 Connector
        mc4_item = next((b for b in bos_items if b["item_name"] == "MC4 Connector"), None)
        if mc4_item:
            boq_items.append({
                "sn": sn,
                "category": "DC Side",
                "item_name": "MC4 Connector",
                "description": mc4_item["description"],
                "brand": mc4_item["brand"],
                "model": mc4_item["model"],
                "specification": mc4_item["specification"],
                "capacity": "1500V",
                "rating": "30A",
                "unit": "pair",
                "quantity": mc4_item["quantity"],
                "unit_price": "",
                "total_price": "",
                "supplier": "",
                "remarks": mc4_item["remarks"],
                "rule_source": mc4_item["rule_source"]
            })
            sn += 1

        # S/N 8: Earth Rod
        er_item = next((b for b in bos_items if b["item_name"] == "Earth Rod"), None)
        if er_item:
            boq_items.append({
                "sn": sn,
                "category": "DC Side",
                "item_name": "Earth Rod",
                "description": er_item["description"],
                "brand": er_item["brand"],
                "model": er_item["model"],
                "specification": er_item["specification"],
                "capacity": "8ft",
                "rating": "5/8\"",
                "unit": "nos",
                "quantity": er_item["quantity"],
                "unit_price": "",
                "total_price": "",
                "supplier": "",
                "remarks": er_item["remarks"],
                "rule_source": er_item["rule_source"]
            })
            sn += 1

        # S/N 9: AC Isolator
        ac_iso = ac_prot["ac_isolator"]
        boq_items.append({
            "sn": sn,
            "category": "AC Side",
            "item_name": "Isolator",
            "description": ac_iso["description"],
            "brand": ac_iso["brand"],
            "model": ac_iso["model"],
            "specification": f"{ac_iso['pole']} {ac_iso['voltage_rating']}V {ac_iso['current_rating']}A",
            "capacity": f"{ac_iso['voltage_rating']}V",
            "rating": f"{ac_iso['current_rating']}A",
            "unit": "nos",
            "quantity": ac_iso["quantity"],
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": f"Inverter AC isolation (Rated I: {ac_prot['rated_ac_current_a']}A)",
            "rule_source": ac_iso["rule_source"]
        })
        sn += 1

        # S/N 10: AC SPD
        ac_spd = ac_prot["ac_spd"]
        boq_items.append({
            "sn": sn,
            "category": "AC Side",
            "item_name": "SPD",
            "description": ac_spd["description"],
            "brand": ac_spd["brand"],
            "model": ac_spd["model"],
            "specification": f"{ac_spd['pole']} {ac_spd['voltage_rating']}V 20/40kA",
            "capacity": f"{ac_spd['voltage_rating']}V",
            "rating": f"{ac_spd.get('ka_rating', 40)}kA",
            "unit": "nos",
            "quantity": ac_spd["quantity"],
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": "AC mains surge protection",
            "rule_source": ac_spd["rule_source"]
        })
        sn += 1

        # S/N 11: AC MCB / MCCB
        breaker = ac_prot["ac_breaker"]
        boq_items.append({
            "sn": sn,
            "category": "AC Side",
            "item_name": breaker["breaker_type"],
            "description": breaker["description"],
            "brand": breaker["brand"],
            "model": breaker["model"],
            "specification": f"{breaker['pole']} {breaker['current_rating']}A",
            "capacity": f"{breaker['voltage_rating']}V",
            "rating": f"{breaker['current_rating']}A",
            "unit": "nos",
            "quantity": breaker["quantity"],
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": f"Design current: {ac_prot['design_current_a']}A",
            "rule_source": breaker["rule_source"]
        })
        sn += 1

        # Lockable Isolator
        lock_iso = ac_prot["lockable_isolator"]
        boq_items.append({
            "sn": sn,
            "category": "AC Side",
            "item_name": "Lockable Isolator",
            "description": lock_iso["description"],
            "brand": lock_iso["brand"],
            "model": lock_iso["model"],
            "specification": f"{lock_iso['pole']} {lock_iso['voltage_rating']}V {lock_iso['current_rating']}A Padlockable",
            "capacity": f"{lock_iso['voltage_rating']}V",
            "rating": f"{lock_iso['current_rating']}A",
            "unit": "nos",
            "quantity": lock_iso["quantity"],
            "unit_price": "",
            "total_price": "",
            "supplier": "",
            "remarks": "CEB mandatory padlockable grid disconnect switch",
            "rule_source": lock_iso["rule_source"]
        })
        sn += 1

        # S/N: RF / Production Equipment
        rf_items = self.select_rf_production_equipment(capacity_kw, phase, inverter)
        for rf in rf_items:
            rf["sn"] = sn
            # Check user overrides
            if rf["item_name"] in overrides:
                rf.update(overrides[rf["item_name"]])
                rf["mode"] = "MANUAL"
            boq_items.append(rf)
            sn += 1

        # BoS items
        for b in bos_items:
            if b["item_name"] in ["MC4 Connector", "Earth Rod"]:
                continue

            boq_items.append({
                "sn": sn,
                "category": b["category"],
                "item_name": b["item_name"],
                "description": b["description"],
                "brand": b.get("brand", "Standard Approved"),
                "model": b.get("model", ""),
                "specification": b.get("specification", ""),
                "capacity": b.get("specification", ""),
                "rating": b.get("rating", ""),
                "unit": b.get("unit", "nos"),
                "quantity": b.get("quantity", 1),
                "unit_price": "",
                "total_price": "",
                "supplier": "",
                "remarks": b.get("remarks", ""),
                "rule_source": b.get("rule_source", RULE_SOURCE_INSTALLER),
                "mode": "MANUAL" if b["item_name"] in overrides else "AUTO"
            })
            sn += 1

        # Set mode tags on all other items
        for item in boq_items:
            if "mode" not in item:
                is_manual = False
                it_name = item.get("item_name", "")
                if it_name in overrides:
                    is_manual = True
                elif it_name == "Panel" and ("panel" in overrides or "panel_count" in overrides):
                    is_manual = True
                elif it_name == "Inverter" and "inverter" in overrides:
                    is_manual = True
                elif it_name == "Isolator" and item.get("category") == "DC Side" and "dc_isolator" in overrides:
                    is_manual = True
                elif it_name == "Isolator" and item.get("category") == "AC Side" and "ac_isolator" in overrides:
                    is_manual = True
                elif it_name == "SPD" and item.get("category") == "DC Side" and "dc_spd" in overrides:
                    is_manual = True
                elif it_name == "SPD" and item.get("category") == "AC Side" and "ac_spd" in overrides:
                    is_manual = True
                elif "Breaker" in it_name and "ac_breaker" in overrides:
                    is_manual = True
                elif "Lockable" in it_name and "lockable_isolator" in overrides:
                    is_manual = True
                item["mode"] = "MANUAL" if is_manual else "AUTO"

        # Electrical & Configuration Validation Check
        validation_warnings = self.validate_system_configuration(
            panel=panel,
            inverter=inverter,
            string_info=string_info,
            dc_prot=dc_prot,
            ac_prot=ac_prot
        )

        return {
            "project_inputs": project_inputs,
            "phase_info": phase_info,
            "dc_target": dc_target,
            "inverter": inverter,
            "panel": panel,
            "panel_options": panel_options,
            "total_panels": total_panels,
            "actual_dc_kwp": actual_dc_kwp,
            "dc_ac_ratio": dc_ac_ratio,
            "string_info": string_info,
            "dc_protection": dc_prot,
            "ac_protection": ac_prot,
            "rf_production": rf_items,
            "boq_items": boq_items,
            "validation_warnings": validation_warnings,
            "is_valid": len([w for w in validation_warnings if w["severity"] == "FAIL"]) == 0,
            "disclaimer": ENGINEERING_DISCLAIMER
        }

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------
    def _get_default_inverter(self, capacity_kw: float, phase: int) -> Inverter:
        """Returns default inverter matching capacity and phase."""
        inv_list = self.master_data.get("inverters", [])
        matches = [
            inv for inv in inv_list
            if inv.get("is_active", True)
            and inv.get("phases", 3 if phase == 3 else 1) == phase
            and abs(inv.get("rated_ac_power_kw", 5.0) - capacity_kw) <= 5.0
        ]
        if not matches:
            matches = [inv for inv in inv_list if inv.get("is_active", True)]

        matches.sort(key=lambda x: abs(x.get("rated_ac_power_kw", 5.0) - capacity_kw))
        i_data = matches[0] if matches else {
            "id": "sunways-sts-5ktl" if phase == 1 else "sunways-stt-10ktl-p",
            "manufacturer": "Sunways",
            "model": "STS-5KTL" if phase == 1 else "STT-10KTL-P",
            "rated_ac_power_kw": 5.0 if phase == 1 else 10.0,
            "max_dc_power_kw": 7.0 if phase == 1 else 13.5,
            "mppt_count": 2,
            "string_inputs_per_mppt": 1,
            "mppt_voltage_min_v": 100.0 if phase == 1 else 160.0,
            "mppt_voltage_max_v": 550.0 if phase == 1 else 1000.0,
            "max_dc_voltage_v": 600.0 if phase == 1 else 1100.0,
            "max_input_current_per_mppt_a": 15.0,
            "max_isc_per_mppt_a": 20.0 if phase == 1 else 40.0,
            "max_ac_current_a": 22.8 if phase == 1 else 15.2,
            "phases": phase,
            "ac_voltage": 230.0 if phase == 1 else 400.0
        }

        return Inverter(
            id=i_data.get("id", "inv-default"),
            manufacturer=i_data.get("manufacturer", "Sunways"),
            model=i_data.get("model", f"{capacity_kw}kW Inverter"),
            rated_ac_power_kw=float(i_data.get("rated_ac_power_kw", capacity_kw)),
            max_dc_input_power_kw=float(i_data.get("max_dc_power_kw", capacity_kw * 1.35)),
            max_dc_voltage_v=float(i_data.get("max_dc_voltage_v", 600.0 if phase == 1 else 1100.0)),
            mppt_voltage_min_v=float(i_data.get("mppt_voltage_min_v", 100.0 if phase == 1 else 160.0)),
            mppt_voltage_max_v=float(i_data.get("mppt_voltage_max_v", 550.0 if phase == 1 else 1000.0)),
            mppt_count=int(i_data.get("mppt_count", 2)),
            string_inputs_per_mppt=int(i_data.get("string_inputs_per_mppt", 1)),
            max_input_current_per_mppt_a=float(i_data.get("max_input_current_per_mppt_a", 15.0)),
            max_isc_per_mppt_a=float(i_data.get("max_isc_per_mppt_a", 20.0)),
            max_total_dc_current_a=float(i_data.get("max_input_current_per_mppt_a", 15.0) * i_data.get("mppt_count", 2)),
            ac_voltage=float(i_data.get("ac_voltage", 230.0 if phase == 1 else 400.0)),
            rated_ac_current_a=float(i_data.get("max_ac_current_a", 22.8 if phase == 1 else 15.2)),
            max_ac_current_a=float(i_data.get("max_ac_current_a", 22.8 if phase == 1 else 15.2)),
            efficiency_pct=float(i_data.get("efficiency_pct", 98.2)),
            source="master_data"
        )
