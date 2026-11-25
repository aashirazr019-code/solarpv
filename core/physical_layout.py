"""
Physical layout — single rectangular area, north-south rows.
Port of src/physicalLayout.js. Rules per Phase 2 doc section 3.5.
"""
from .string_sizing import rnd


def layout_for_orientation(panel, project, orientation):
    sc = project.spacing_config
    usable_length = project.area_length_m - 2 * sc.edge_clearance_m
    usable_width = (
        project.area_width_m - 2 * sc.edge_clearance_m - sc.walkway_m - sc.inverter_access_m
    )

    dim_across_row = panel.width_m if orientation == "portrait" else panel.length_m
    dim_along_row = panel.length_m if orientation == "portrait" else panel.width_m

    panels_per_row = max(0, int((usable_width + sc.panel_gap_m) // (dim_across_row + sc.panel_gap_m)))
    rows = max(0, int((usable_length + sc.row_gap_m) // (dim_along_row + sc.row_gap_m)))
    total_fitting = panels_per_row * rows

    return {
        "orientation": orientation,
        "usable_length_m": rnd(usable_length, 2),
        "usable_width_m": rnd(usable_width, 2),
        "panels_per_row": panels_per_row,
        "rows": rows,
        "total_fitting": total_fitting,
    }


def physical_layout(panel, project, required_panel_qty):
    portrait = layout_for_orientation(panel, project, "portrait")
    landscape = layout_for_orientation(panel, project, "landscape")

    meets_portrait = portrait["total_fitting"] >= required_panel_qty
    meets_landscape = landscape["total_fitting"] >= required_panel_qty

    if meets_portrait and meets_landscape:
        chosen = (
            portrait
            if (portrait["total_fitting"] - required_panel_qty)
            <= (landscape["total_fitting"] - required_panel_qty)
            else landscape
        )
        status = "PASS"
    elif meets_portrait:
        chosen = portrait
        status = "PASS"
    elif meets_landscape:
        chosen = landscape
        status = "PASS"
    else:
        chosen = portrait if portrait["total_fitting"] >= landscape["total_fitting"] else landscape
        status = "NOT_FITTING"

    # Add backward compatible aliases inside portrait and landscape dicts
    portrait["total_panels"] = portrait["total_fitting"]
    portrait["cols"] = portrait["panels_per_row"]
    landscape["total_panels"] = landscape["total_fitting"]
    landscape["cols"] = landscape["panels_per_row"]

    area_total = project.area_length_m * project.area_width_m if (project.area_length_m and project.area_width_m) else 1.0
    panel_area = (chosen["total_fitting"] * panel.length_m * panel.width_m) if panel else 0.0
    area_utilization = rnd((panel_area / area_total) * 100.0, 1)

    return {
        "portrait": portrait,
        "landscape": landscape,
        "chosen_orientation": chosen["orientation"],
        "recommended_orientation": chosen["orientation"],
        "panels_per_row": chosen["panels_per_row"],
        "rows": chosen["rows"],
        "total_fitting": chosen["total_fitting"],
        "required_panel_qty": required_panel_qty,
        "area_utilization_pct": area_utilization,
        "status": status,
        "suggestion": (
            "Reduce panel count / lower DC capacity, try a different panel model/dimensions, "
            "or add a second installation zone."
            if status == "NOT_FITTING"
            else None
        ),
    }

