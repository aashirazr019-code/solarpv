"""
core/project_state.py — Central State Bridge & Dynamic Data Flow Manager
Manages single source of truth across all engineering sections in st.session_state.
Integrates with core.dynamic_system_engine to enforce the strict dependency chain:
Required Capacity -> Inverter Combination -> Panel Quantity -> String Configuration
-> MPPT Allocation -> DC Protection -> DC Cable -> Individual AC Switchgear
-> Main AC Switchgear & Cable -> Dynamic Earthing -> Dynamic BOM/BOQ.

Designed & Engineered by Eng. Aashir © 2026. All Rights Reserved.
"""
from typing import Dict, Any, Optional, List
import streamlit as st

from .models import Panel, Inverter, Project, SpacingConfig, DesignResult, BOMItem
from data.library_data import PANEL_FAMILIES, INVERTER_FAMILIES, build_panel, build_inverter
from .dynamic_system_engine import (
    calculate_dynamic_system,
    generate_inverter_combinations,
    validate_inverter_combination
)


APPROVED_PANELS_SPECS = [
    {
        "id": "yingli-550w",
        "manufacturer": "Yingli Solar",
        "model": "PANDA 3.0 PRO CF72-550W",
        "rated_power_wp": 550.0,
        "voc": 50.26,
        "vmp": 41.57,
        "isc": 13.99,
        "imp": 13.24,
        "max_system_voltage": 1500.0,
        "max_series_fuse": 30.0,
        "temp_coeff_voc": -0.25,
        "temp_coeff_vmp": -0.27,
        "temp_coeff_isc": 0.046,
        "temp_coeff_pmax": -0.30,
        "length_m": 2.278,
        "width_m": 1.134,
        "thickness_mm": 30.0,
        "weight_kg": 32.0,
        "cell_technology": "N-type TOPCon Bifacial",
        "cell_count": 144,
        "source": "library"
    },
    {
        "id": "yingli-575w",
        "manufacturer": "Yingli Solar",
        "model": "PANDA 3.0 PRO CF72-575W",
        "rated_power_wp": 575.0,
        "voc": 51.26,
        "vmp": 42.47,
        "isc": 14.32,
        "imp": 13.54,
        "max_system_voltage": 1500.0,
        "max_series_fuse": 30.0,
        "temp_coeff_voc": -0.25,
        "temp_coeff_vmp": -0.27,
        "temp_coeff_isc": 0.046,
        "temp_coeff_pmax": -0.30,
        "length_m": 2.278,
        "width_m": 1.134,
        "thickness_mm": 30.0,
        "weight_kg": 32.0,
        "cell_technology": "N-type TOPCon Bifacial",
        "cell_count": 144,
        "source": "library"
    },
    {
        "id": "yingli-580w",
        "manufacturer": "Yingli Solar",
        "model": "PANDA 3.0 PRO CF72-580W",
        "rated_power_wp": 580.0,
        "voc": 51.46,
        "vmp": 42.65,
        "isc": 14.38,
        "imp": 13.60,
        "max_system_voltage": 1500.0,
        "max_series_fuse": 30.0,
        "temp_coeff_voc": -0.25,
        "temp_coeff_vmp": -0.27,
        "temp_coeff_isc": 0.046,
        "temp_coeff_pmax": -0.30,
        "length_m": 2.278,
        "width_m": 1.134,
        "thickness_mm": 30.0,
        "weight_kg": 32.0,
        "cell_technology": "N-type TOPCon Bifacial",
        "cell_count": 144,
        "source": "library"
    },
    {
        "id": "yingli-615w",
        "manufacturer": "Yingli Solar",
        "model": "PANDA 3.0 Pro 2 CF66-615W",
        "rated_power_wp": 615.0,
        "voc": 49.31,
        "vmp": 41.34,
        "isc": 15.86,
        "imp": 14.88,
        "max_system_voltage": 1500.0,
        "max_series_fuse": 30.0,
        "temp_coeff_voc": -0.24,
        "temp_coeff_vmp": -0.26,
        "temp_coeff_isc": 0.042,
        "temp_coeff_pmax": -0.29,
        "length_m": 2.382,
        "width_m": 1.134,
        "thickness_mm": 30.0,
        "weight_kg": 33.0,
        "cell_technology": "N-type TOPCon Bifacial",
        "cell_count": 132,
        "source": "library"
    },
    {
        "id": "yingli-630w",
        "manufacturer": "Yingli Solar",
        "model": "PANDA 3.0 Pro 2 CF66-630W",
        "rated_power_wp": 630.0,
        "voc": 49.44,
        "vmp": 41.47,
        "isc": 16.18,
        "imp": 15.19,
        "max_system_voltage": 1500.0,
        "max_series_fuse": 30.0,
        "temp_coeff_voc": -0.24,
        "temp_coeff_vmp": -0.26,
        "temp_coeff_isc": 0.042,
        "temp_coeff_pmax": -0.29,
        "length_m": 2.382,
        "width_m": 1.134,
        "thickness_mm": 30.0,
        "weight_kg": 33.0,
        "cell_technology": "N-type TOPCon Bifacial",
        "cell_count": 132,
        "source": "library"
    },
    {
        "id": "yingli-635w",
        "manufacturer": "Yingli Solar",
        "model": "PANDA 3.0 Pro 1 C78-635W",
        "rated_power_wp": 635.0,
        "voc": 57.42,
        "vmp": 47.57,
        "isc": 14.01,
        "imp": 13.35,
        "max_system_voltage": 1500.0,
        "max_series_fuse": 30.0,
        "temp_coeff_voc": -0.24,
        "temp_coeff_vmp": -0.26,
        "temp_coeff_isc": 0.042,
        "temp_coeff_pmax": -0.29,
        "length_m": 2.465,
        "width_m": 1.134,
        "thickness_mm": 30.0,
        "weight_kg": 34.5,
        "cell_technology": "N-type TOPCon Bifacial",
        "cell_count": 156,
        "source": "library"
    },
    {
        "id": "yingli-660w",
        "manufacturer": "Yingli Solar",
        "model": "PANDA 3.0 Pro 1 C78-660W",
        "rated_power_wp": 660.0,
        "voc": 58.42,
        "vmp": 48.35,
        "isc": 14.23,
        "imp": 13.65,
        "max_system_voltage": 1500.0,
        "max_series_fuse": 30.0,
        "temp_coeff_voc": -0.24,
        "temp_coeff_vmp": -0.26,
        "temp_coeff_isc": 0.042,
        "temp_coeff_pmax": -0.29,
        "length_m": 2.465,
        "width_m": 1.134,
        "thickness_mm": 30.0,
        "weight_kg": 34.5,
        "cell_technology": "N-type TOPCon Bifacial",
        "cell_count": 156,
        "source": "library"
    }
]


def get_approved_panels() -> List[Panel]:
    """Returns the list of controlled approved panels: 550W, 575W, 580W, 615W, 630W, 635W, 660W."""
    return [Panel(**spec) for spec in APPROVED_PANELS_SPECS]


def get_approved_panel_by_wattage(wp: float) -> Panel:
    """Returns matching approved panel or default 630W panel."""
    for p in get_approved_panels():
        if abs(p.rated_power_wp - wp) < 2.0:
            return p
    return get_default_panel()


def get_default_panel() -> Panel:
    """Returns standard approved default 630W Tier-1 PV Module."""
    try:
        fam = PANEL_FAMILIES[3]  # PANDA 3.0 Pro 2 (CF66, 610-630W)
        var = next(v for v in fam["variants"] if v["wp"] == 630)
        return build_panel(fam, var)
    except Exception:
        return Panel(**APPROVED_PANELS_SPECS[2])


def get_default_inverter() -> Inverter:
    """Returns standard default 5 kW Single-Phase Grid-tie Inverter."""
    try:
        fam = INVERTER_FAMILIES[2]  # STS-3~6KTL-P (1-Phase Grid-tie)
        var = next(v for v in fam["variants"] if v["model"] == "STS-5KTL-P")
        return build_inverter(fam, var)
    except Exception:
        return Inverter(
            id="default-5kw",
            manufacturer="Sunways",
            model="STS-5KTL-P",
            rated_ac_power_kw=5.0,
            max_dc_input_power_kw=6.75,
            max_dc_voltage_v=600.0,
            mppt_voltage_min_v=100.0,
            mppt_voltage_max_v=550.0,
            mppt_count=2,
            string_inputs_per_mppt=1,
            max_input_current_per_mppt_a=15.0,
            max_isc_per_mppt_a=20.0,
            max_total_dc_current_a=30.0,
            ac_voltage=230.0,
            rated_ac_current_a=21.7,
            max_ac_current_a=22.8,
            efficiency_pct=98.1,
            source="library"
        )


def recalculate_system_state(
    target_kw: Optional[float] = None,
    panel: Optional[Panel] = None,
    selected_combination: Optional[Dict[str, Any]] = None,
    calculation_mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes full downstream recalculation across the dependency chain:
      Capacity -> Inverter Combination -> Panel Sizing -> Strings -> MPPT
      -> DC Switchgear -> AC Switchgear -> Earthing -> Classified Schedule.
    Synchronizes st.session_state.design_state and st.session_state.dynamic_system.
    """
    if "active_project" not in st.session_state or not st.session_state.active_project:
        init_project_state()

    proj = st.session_state.active_project

    if target_kw is not None:
        target_val = float(target_kw)
        proj["target_ac_capacity_kw"] = target_val
        proj["target_ac_kw"] = target_val
        # Automatically update grid phase and voltage based on engineering standards
        if target_val <= 5.0:
            proj["grid_phases"] = 1
            proj["grid_voltage_v"] = 230.0
        else:
            proj["grid_phases"] = 3
            proj["grid_voltage_v"] = 400.0

    if panel is not None:
        st.session_state.active_panel = panel

    if calculation_mode is not None:
        st.session_state.calculation_mode = calculation_mode
    elif "calculation_mode" not in st.session_state:
        st.session_state.calculation_mode = "AUTO"

    active_p = st.session_state.get("active_panel", get_default_panel())
    cur_kw = float(proj.get("target_ac_capacity_kw", 100.0))
    pref_ratio = float(proj.get("dc_ac_ratio_preferred", 1.30))

    # Run dynamic calculation engine
    try:
        dynamic_res = calculate_dynamic_system(
            target_ac_kw=cur_kw,
            panel=active_p,
            project_params=proj,
            selected_combination=selected_combination,
            target_dc_ac_ratio=pref_ratio
        )
    except Exception as e:
        # Fallback to auto search if selected combination had an issue
        dynamic_res = calculate_dynamic_system(
            target_ac_kw=cur_kw,
            panel=active_p,
            project_params=proj,
            selected_combination=None,
            target_dc_ac_ratio=pref_ratio
        )

    # Apply manual overrides if present
    overrides = st.session_state.get("manual_overrides", {})
    if overrides:
        if "dc_cable_csa_mm2" in overrides:
            for d in dynamic_res.get("per_inverter_designs", []):
                d["dc_cable_csa_mm2"] = float(overrides["dc_cable_csa_mm2"])
                d["dc_cable_source"] = "MANUAL OVERRIDE"
        if "ac_cable_csa_mm2" in overrides:
            for d in dynamic_res.get("per_inverter_designs", []):
                d["ac_cable_csa_mm2"] = float(overrides["ac_cable_csa_mm2"])
                d["ac_cable_source"] = "MANUAL OVERRIDE"
        if "main_ac_cable_csa_mm2" in overrides and "whole_system_ac" in dynamic_res:
            csa = float(overrides["main_ac_cable_csa_mm2"])
            dynamic_res["whole_system_ac"]["main_cable_csa_mm2"] = csa
            dynamic_res["whole_system_ac"]["main_cable_source"] = "MANUAL OVERRIDE"
            if proj.get("grid_phases", 3) == 3:
                dynamic_res["whole_system_ac"]["main_cable_spec"] = f"4C {csa:.0f}sqmm/CU/PVC" if csa <= 50.0 else f"1C*4 {csa:.0f}mm sq CU/XLPE/PVC"
            else:
                dynamic_res["whole_system_ac"]["main_cable_spec"] = f"2C/{csa:.0f}sq.mm/Cu/PVC"
        if "main_breaker_spec" in overrides and "whole_system_ac" in dynamic_res:
            dynamic_res["whole_system_ac"]["main_breaker_spec"] = str(overrides["main_breaker_spec"])
            dynamic_res["whole_system_ac"]["main_breaker_source"] = "MANUAL OVERRIDE"
        if "main_breaker_rating_a" in overrides and "whole_system_ac" in dynamic_res:
            r = int(overrides["main_breaker_rating_a"])
            dynamic_res["whole_system_ac"]["main_breaker_rating_a"] = r
            b_type = "MCB" if r <= 63 else "MCCB"
            poles = "4P" if proj.get("grid_phases", 3) == 3 else "2P"
            dynamic_res["whole_system_ac"]["main_breaker_spec"] = f"{r}A {poles} {b_type}"
            dynamic_res["whole_system_ac"]["main_breaker_source"] = "MANUAL OVERRIDE"
        if "main_busbar_rating_a" in overrides and "whole_system_ac" in dynamic_res:
            b_rating = int(overrides["main_busbar_rating_a"])
            dynamic_res["whole_system_ac"]["main_busbar_rating_a"] = b_rating
            dynamic_res["whole_system_ac"]["main_busbar_label"] = f"{b_rating} A Bus Bar Cu"
            dynamic_res["whole_system_ac"]["main_busbar_source"] = "MANUAL OVERRIDE"

    st.session_state.dynamic_system = dynamic_res

    # Update active inverter to primary unit
    if dynamic_res.get("per_inverter_designs"):
        st.session_state.active_inverter = dynamic_res["per_inverter_designs"][0]["inverter"]

    combo = dynamic_res.get("active_combination", {})
    first_inv_design = dynamic_res["per_inverter_designs"][0] if dynamic_res.get("per_inverter_designs") else {}

    # Synchronize design_state for seamless backward-compatibility
    ds_updates = {
        "target_ac_kw": cur_kw,
        "target_dc_kwp": dynamic_res.get("target_dc_kwp", round(cur_kw * pref_ratio, 2)),
        "actual_ac_kw": dynamic_res.get("actual_ac_kw", cur_kw),
        "actual_dc_kwp": dynamic_res.get("actual_dc_kwp", 0.0),
        "panel_qty": dynamic_res.get("total_panels", 0),
        "panels_per_string": first_inv_design.get("panels_per_string", 0),
        "total_strings": dynamic_res.get("total_strings", 0),
        "dc_ac_ratio": dynamic_res.get("dc_ac_ratio", pref_ratio),
        "inverter_count": len(dynamic_res.get("per_inverter_designs", [])),
        "inverter_breakdown": combo.get("breakdown", []),
        "inverter_summary": combo.get("label", ""),
        "active_combination": combo,
        "per_inverter_designs": dynamic_res.get("per_inverter_designs", []),
        "whole_system_ac": dynamic_res.get("whole_system_ac", {}),
        "earthing_design": dynamic_res.get("earthing_design", {}),
        "classified_schedule": dynamic_res.get("classified_schedule", {}),
        "dc_operating_current_a": round(active_p.imp, 2),
        "dc_isc_current_a": round(active_p.isc, 2),
        "ac_operating_current_a": dynamic_res.get("whole_system_ac", {}).get("total_ac_current_a", 0.0),
        "string_voc_cold_v": first_inv_design.get("string_voc_cold_v", 0.0),
        "string_vmp_hot_v": first_inv_design.get("string_vmp_hot_v", 0.0),
        "dc_isolator_qty": sum(d.get("dc_isolator_qty", 1) for d in dynamic_res.get("per_inverter_designs", [])),
        "dc_spd_qty": len(dynamic_res.get("per_inverter_designs", [])),
        "ac_isolator_spec": dynamic_res.get("whole_system_ac", {}).get("main_isolator_spec", ""),
        "lockable_isolator_spec": dynamic_res.get("whole_system_ac", {}).get("lockable_switch_spec", ""),
        "ac_breaker_spec": dynamic_res.get("whole_system_ac", {}).get("main_breaker_spec", ""),
        "ac_cable_csa_mm2": dynamic_res.get("whole_system_ac", {}).get("main_cable_csa_mm2", 6.0),
        "dc_cable_csa_mm2": first_inv_design.get("dc_cable_csa_mm2", 4.0),
        "performance_ratio_pct": dynamic_res.get("performance_ratio_pct", 79.5),
        "annual_ac_energy_kwh": dynamic_res.get("annual_ac_energy_kwh", 0.0),
        "overall_status": dynamic_res.get("overall_status", "PASS")
    }

    if "design_state" not in st.session_state:
        st.session_state.design_state = ds_updates
    else:
        st.session_state.design_state.update(ds_updates)

    return dynamic_res


def get_manual_overrides() -> Dict[str, Any]:
    """Returns dictionary of active manual overrides."""
    if "manual_overrides" not in st.session_state:
        st.session_state.manual_overrides = {}
    return st.session_state.manual_overrides


def set_manual_override(key: str, value: Any):
    """Sets a manual override and triggers recalculation to update SLD & BOQ."""
    if "manual_overrides" not in st.session_state:
        st.session_state.manual_overrides = {}
    st.session_state.manual_overrides[key] = value
    recalculate_system_state()


def clear_manual_overrides():
    """Clears all manual overrides, returning system to 100% AUTO calculation."""
    st.session_state.manual_overrides = {}
    recalculate_system_state()


def init_project_state():
    """Initializes and verifies standard session state keys with 100 kW Commercial default system."""
    if "active_project" not in st.session_state or not st.session_state.active_project:
        st.session_state.active_project = {
            "id": "proj-default-001",
            "name": "100 kW Commercial Solar PV Plant",
            "customer_name": "Commercial Client",
            "site_name": "Commercial Facility Rooftop",
            "location": "Colombo, Sri Lanka",
            "installation_type": "rooftop",
            "target_ac_capacity_kw": 100.0,
            "target_ac_kw": 100.0,
            "grid_voltage_v": 400.0,
            "grid_phases": 3,
            "min_design_temp_c": -30.0,
            "max_design_temp_c": 60.0,
            "ceb_export_tariff_lkr": 19.0,
            "dc_ac_ratio_min": 1.05,
            "dc_ac_ratio_preferred": 1.30,
            "dc_ac_ratio_max": 1.45,
            "panel_available_qty": 500,
            "area_length_m": 80.0,
            "area_width_m": 30.0,
            "spacing_config": SpacingConfig(0.02, 0.5, 0.5, 0.8, 1.0),
            "status": "draft",
            "revision": 1
        }

    if "active_panel" not in st.session_state or not st.session_state.active_panel:
        st.session_state.active_panel = get_default_panel()

    if "active_inverter" not in st.session_state or not st.session_state.active_inverter:
        st.session_state.active_inverter = get_default_inverter()

    if "calculation_mode" not in st.session_state:
        st.session_state.calculation_mode = "AUTO"

    if "dynamic_system" not in st.session_state or "design_state" not in st.session_state:
        recalculate_system_state(target_kw=100.0)


def get_active_project() -> dict:
    init_project_state()
    return st.session_state.active_project


def set_active_project(project_dict: dict):
    st.session_state.active_project = project_dict
    ac_kw = float(project_dict.get("target_ac_capacity_kw", project_dict.get("target_ac_kw", 5.0)))
    recalculate_system_state(target_kw=ac_kw)


def get_active_panel() -> Panel:
    init_project_state()
    return st.session_state.active_panel


def set_active_panel(panel: Panel):
    st.session_state.active_panel = panel
    recalculate_system_state(panel=panel)


def get_active_inverter() -> Inverter:
    init_project_state()
    return st.session_state.active_inverter


def set_active_inverter(inverter: Inverter):
    st.session_state.active_inverter = inverter


def get_dynamic_system() -> Dict[str, Any]:
    init_project_state()
    if "dynamic_system" not in st.session_state:
        recalculate_system_state()
    return st.session_state.dynamic_system


def get_calculation_mode() -> str:
    init_project_state()
    return st.session_state.get("calculation_mode", "AUTO")


def set_calculation_mode(mode: str):
    init_project_state()
    st.session_state.calculation_mode = mode


def get_design_value(key: str, default=None):
    init_project_state()
    val = st.session_state.design_state.get(key, default)
    if val is None and default is not None:
        return default
    return val


def set_design_value(key: str, value):
    init_project_state()
    st.session_state.design_state[key] = value


def update_design_state(updates: dict):
    init_project_state()
    st.session_state.design_state.update(updates)


def render_active_project_banner():
    """
    Renders a clean, compact engineering context ribbon at the top of pages.
    Displays active project name, client, capacity, selected equipment, and quick links.
    """
    init_project_state()
    proj = st.session_state.active_project
    panel = st.session_state.active_panel
    ds = st.session_state.design_state

    p_name = proj.get("name", "Active Project")
    p_cust = proj.get("customer_name", "Client")
    ac_kw = ds.get("actual_ac_kw", proj.get("target_ac_capacity_kw", 5.0))
    dc_kwp = ds.get("actual_dc_kwp", round(ac_kw * 1.25, 2))
    p_qty = ds.get("panel_qty", 0)
    strings = ds.get("total_strings", 0)
    ratio = ds.get("dc_ac_ratio", round(dc_kwp / ac_kw, 2) if ac_kw > 0 else 1.25)
    status = ds.get("overall_status", "PASS")
    inv_label = ds.get("inverter_summary", f"{ac_kw:.0f} kW Inverter System")

    status_icon = "🟢" if status == "PASS" else ("🟡" if status == "WARNING" else "🔴")

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        with c1:
            st.markdown(f"📁 **{p_name}** (`{p_cust}`)")
            st.caption(f"Target: **{ac_kw:.1f} kW AC** | Grid: **{proj.get('grid_voltage_v', 400.0)}V {proj.get('grid_phases', 3)}P** | Site: {proj.get('location', 'N/A')}")
        with c2:
            st.markdown(f"🔋 **{panel.manufacturer} {panel.model}** ({panel.rated_power_wp} Wp)")
            st.caption(f"Panels: **{p_qty}** ({strings} strings total) | DC: **{dc_kwp:.2f} kWp**")
        with c3:
            st.markdown(f"⚡ **{inv_label}**")
            st.caption(f"DC/AC Ratio: **{ratio:.2f}** | PR: **{ds.get('performance_ratio_pct', 79.5):.1f}%**")
        with c4:
            st.markdown(f"<div style='text-align: center;'><b>Status</b><br/>{status_icon} <b>{status}</b></div>", unsafe_allow_html=True)


def get_design_result() -> DesignResult:
    """
    Constructs and returns a strongly-typed DesignResult dataclass instance
    from the current session state / dynamic calculation results.
    Guarantees full backward-compatibility with downstream modules.
    """
    init_project_state()
    ds = st.session_state.get("design_state", {})
    proj = st.session_state.get("active_project", {})
    panel = st.session_state.get("active_panel", get_default_panel())
    inverter = st.session_state.get("active_inverter", get_default_inverter())

    # Safely convert BOM items to BOMItem dataclasses if present
    raw_bom = ds.get("bom_items", [])
    typed_bom = []
    for item in raw_bom:
        if isinstance(item, BOMItem):
            typed_bom.append(item)
        elif isinstance(item, dict):
            typed_bom.append(BOMItem(
                category=item.get("category", "General"),
                item=item.get("item", item.get("name", "")),
                specification=item.get("specification", item.get("spec", "")),
                quantity=float(item.get("quantity", item.get("qty", 1.0))),
                unit=item.get("unit", "pcs"),
                notes=item.get("notes", item.get("source", ""))
            ))

    return DesignResult(
        target_ac_kw=float(proj.get("target_ac_capacity_kw", ds.get("actual_ac_kw", 100.0))),
        actual_ac_kw=float(ds.get("actual_ac_kw", proj.get("target_ac_capacity_kw", 100.0))),
        actual_dc_kwp=float(ds.get("actual_dc_kwp", 130.0)),
        dc_ac_ratio=float(ds.get("dc_ac_ratio", 1.30)),
        panel_id=panel.id,
        panel_model=f"{panel.manufacturer} {panel.model}",
        panel_rated_wp=panel.rated_power_wp,
        total_panels=int(ds.get("panel_qty", 0)),
        panels_per_string=int(ds.get("panels_per_string", 16)),
        total_strings=int(ds.get("total_strings", 0)),
        inverter_breakdown=ds.get("inverter_breakdown", [{
            "model": inverter.model,
            "quantity": 1,
            "unit_kw": inverter.rated_ac_power_kw,
            "total_kw": inverter.rated_ac_power_kw
        }]),
        inverter_summary=ds.get("inverter_summary", f"{inverter.model}"),
        total_inverters=int(ds.get("total_inverters", 1)),
        mppt_allocations=ds.get("mppt_allocation", []),
        voc_cold_v=float(ds.get("voc_cold_v", 0.0)),
        vmp_hot_v=float(ds.get("vmp_hot_v", 0.0)),
        voltage_status=ds.get("voltage_status", "PASS"),
        max_dc_current_a=float(ds.get("max_dc_current_a", 0.0)),
        current_status=ds.get("current_status", "PASS"),
        dc_cable_csa_mm2=float(ds.get("dc_cable_csa_mm2", 6.0)),
        dc_cable_ampacity_a=float(ds.get("dc_cable_ampacity_a", 50.0)),
        dc_protection=ds.get("dc_protection_device", "Fuse 15A"),
        dc_voltage_drop_pct=float(ds.get("dc_voltage_drop_pct", 1.2)),
        ac_cable_csa_mm2=float(ds.get("ac_cable_csa_mm2", 70.0)),
        ac_cable_ampacity_a=float(ds.get("ac_cable_ampacity_a", 160.0)),
        ac_protection=ds.get("ac_protection_device", "MCCB 160A"),
        ac_voltage_drop_pct=float(ds.get("ac_voltage_drop_pct", 1.1)),
        busbar_rating_a=float(ds.get("busbar_rating_a", 200.0)),
        busbar_current_a=float(ds.get("busbar_current_a", 158.8)),
        recommended_orientation=ds.get("recommended_orientation", "portrait"),
        panels_fitting=int(ds.get("panels_fitting", 0)),
        area_status=ds.get("area_status", "PASS"),
        performance_ratio_pct=float(ds.get("performance_ratio_pct", 79.5)),
        annual_energy_kwh=float(ds.get("annual_energy_kwh", 0.0)),
        specific_yield_kwh_kwp=float(ds.get("specific_yield_kwh_kwp", 0.0)),
        overall_status=ds.get("overall_status", "PASS"),
        bom_items=typed_bom,
        classified_bom=ds.get("classified_bom", {}),
        warnings=ds.get("warnings", []),
        calculation_steps=ds.get("calculation_steps", [])
    )

