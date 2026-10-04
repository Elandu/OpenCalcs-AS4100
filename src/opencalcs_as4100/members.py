"""Clause-traced member calculation primitives from AS 4100:2020.

Inputs are design actions (including required second-order effects), not solver loads.
Each operation is a calculation primitive, not a declaration of whole-member compliance.
"""

from collections.abc import Mapping
from math import fsum, isclose, isfinite, pi, sqrt
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

from .standards import ELASTIC_MODULUS_MPA, SHEAR_MODULUS_MPA
from .validation import validate_standard_strengths


def _number(minimum=0, *, positive=False, maximum=None):
    result = {"type": "number", "exclusiveMinimum" if positive else "minimum": minimum}
    if maximum is not None:
        result["maximum"] = maximum
    return result


def _variant(operation, properties, required):
    return {
        "type": "object",
        "properties": {"operation": {"const": operation}, **properties},
        "required": ["operation", *required],
        "additionalProperties": False,
    }


P = _number(positive=True)
N = _number()
R = {"type": "string", "enum": ["SR", "HR", "CF", "LW", "HW"]}
INTERNAL_PLATE_YIELD_LIMITS = {"SR": 45, "HR": 45, "LW": 40, "CF": 40, "HW": 35}
PLATE = {
    "type": "object",
    "properties": {
        "width_mm": P,
        "thickness_mm": P,
        "edges": {"type": "string", "enum": ["one", "both", "circular"]},
        "stress": {
            "type": "string",
            "enum": ["uniform", "outstand_gradient", "internal_gradient"],
        },
        "residual": R,
    },
    "required": ["width_mm", "thickness_mm", "edges", "stress", "residual"],
    "additionalProperties": False,
}
INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "oneOf": [
        _variant(
            "plate",
            {
                "yield_strength_mpa": P,
                "plate": PLATE,
                "elastic_modulus_mm3": P,
                "plastic_modulus_mm3": P,
            },
            ["yield_strength_mpa", "plate", "elastic_modulus_mm3", "plastic_modulus_mm3"],
        ),
        _variant(
            "section_moduli",
            {
                "method": {"const": "area_ratio"},
                "yield_strength_mpa": P,
                "ultimate_strength_mpa": P,
                "gross_area_mm2": P,
                "gross_web_area_mm2": N,
                "gross_flange_areas_mm2": {
                    "type": "array",
                    "items": P,
                    "minItems": 1,
                    "maxItems": 20,
                },
                "net_flange_areas_mm2": {
                    "type": "array",
                    "items": N,
                    "minItems": 1,
                    "maxItems": 20,
                },
                "gross_elastic_modulus_mm3": P,
                "gross_plastic_modulus_mm3": P,
            },
            [
                "method",
                "yield_strength_mpa",
                "ultimate_strength_mpa",
                "gross_area_mm2",
                "gross_web_area_mm2",
                "gross_flange_areas_mm2",
                "net_flange_areas_mm2",
                "gross_elastic_modulus_mm3",
                "gross_plastic_modulus_mm3",
            ],
        ),
        _variant(
            "section_moduli",
            {
                "method": {"const": "net_section"},
                "yield_strength_mpa": P,
                "ultimate_strength_mpa": P,
                "gross_area_mm2": P,
                "gross_web_area_mm2": N,
                "gross_flange_areas_mm2": {
                    "type": "array",
                    "items": P,
                    "minItems": 1,
                    "maxItems": 20,
                },
                "net_flange_areas_mm2": {
                    "type": "array",
                    "items": N,
                    "minItems": 1,
                    "maxItems": 20,
                },
                "gross_elastic_modulus_mm3": P,
                "gross_plastic_modulus_mm3": P,
                "net_elastic_modulus_mm3": P,
                "net_plastic_modulus_mm3": P,
                "net_i_section_geometry": {
                    "type": "object",
                    "properties": {
                        "overall_depth_mm": P,
                        "flange_thickness_mm": P,
                        "web_thickness_mm": P,
                        "bending_axis": {"const": "major"},
                        "symmetric_sharp_corner_i_section_verified": {"const": True},
                        "flange_only_holes_verified": {"const": True},
                        "net_hole_layout_preserves_major_axis_verified": {"const": True},
                        "net_flange_areas_deducted_under_clause_9_1_10_verified": {"const": True},
                    },
                    "required": [
                        "overall_depth_mm",
                        "flange_thickness_mm",
                        "web_thickness_mm",
                        "bending_axis",
                        "symmetric_sharp_corner_i_section_verified",
                        "flange_only_holes_verified",
                        "net_hole_layout_preserves_major_axis_verified",
                        "net_flange_areas_deducted_under_clause_9_1_10_verified",
                    ],
                    "additionalProperties": False,
                },
                "net_rhs_geometry": {
                    "type": "object",
                    "properties": {
                        "overall_depth_mm": P,
                        "flange_thickness_mm": P,
                        "web_thickness_mm": P,
                        "bending_axis": {"const": "major"},
                        "symmetric_sharp_corner_rhs_section_verified": {"const": True},
                        "flange_only_holes_verified": {"const": True},
                        "net_hole_layout_preserves_major_axis_verified": {"const": True},
                        "net_flange_areas_deducted_under_clause_9_1_10_verified": {"const": True},
                    },
                    "required": [
                        "overall_depth_mm",
                        "flange_thickness_mm",
                        "web_thickness_mm",
                        "bending_axis",
                        "symmetric_sharp_corner_rhs_section_verified",
                        "flange_only_holes_verified",
                        "net_hole_layout_preserves_major_axis_verified",
                        "net_flange_areas_deducted_under_clause_9_1_10_verified",
                    ],
                    "additionalProperties": False,
                },
            },
            [
                "method",
                "yield_strength_mpa",
                "ultimate_strength_mpa",
                "gross_area_mm2",
                "gross_web_area_mm2",
                "gross_flange_areas_mm2",
                "net_flange_areas_mm2",
                "gross_elastic_modulus_mm3",
                "gross_plastic_modulus_mm3",
            ],
        ),
        _variant(
            "compression",
            {
                "yield_strength_mpa": P,
                "gross_area_mm2": P,
                "net_area_mm2": P,
                "effective_area_mm2": P,
                "effective_length_x_mm": P,
                "effective_length_y_mm": P,
                "radius_x_mm": P,
                "radius_y_mm": P,
                "section_constant_x": {"enum": [-1, -0.5, 0, 0.5, 1]},
                "section_constant_y": {"enum": [-1, -0.5, 0, 0.5, 1]},
                "action_kn": N,
                "geometry": {"enum": ["doubly_symmetric", "chs", "rhs"]},
            },
            [
                "yield_strength_mpa",
                "gross_area_mm2",
                "net_area_mm2",
                "effective_area_mm2",
                "effective_length_x_mm",
                "effective_length_y_mm",
                "radius_x_mm",
                "radius_y_mm",
                "section_constant_x",
                "section_constant_y",
                "action_kn",
                "geometry",
            ],
        ),
        _variant(
            "bending",
            {
                "section_capacity_knm": P,
                "iy_mm4": P,
                "torsion_constant_mm4": P,
                "warping_constant_mm6": N,
                "effective_length_mm": P,
                "moment_factor": _number(positive=True, maximum=2.5),
                "action_knm": N,
                "geometry": {"const": "equal_flanged_open"},
            },
            [
                "section_capacity_knm",
                "iy_mm4",
                "torsion_constant_mm4",
                "warping_constant_mm6",
                "effective_length_mm",
                "moment_factor",
                "action_knm",
                "geometry",
            ],
        ),
        _variant(
            "chs_shear",
            {
                "yield_strength_mpa": P,
                "gross_area_mm2": P,
                "net_area_mm2": P,
                "oversized_fastener_holes_present": {"type": "boolean"},
                "action_kn": N,
                "moment_action_knm": N,
                "section_moment_capacity_knm": P,
            },
            [
                "yield_strength_mpa",
                "gross_area_mm2",
                "net_area_mm2",
                "oversized_fastener_holes_present",
                "action_kn",
                "moment_action_knm",
                "section_moment_capacity_knm",
            ],
        ),
        _variant(
            "shear_proportioning",
            {
                "yield_strength_mpa": P,
                "compression_flange_gross_area_mm2": P,
                "compression_flange_effective_area_mm2": P,
                "tension_flange_gross_area_mm2": P,
                "tension_flange_net_area_mm2": P,
                "tension_flange_ultimate_strength_mpa": P,
                "flange_centroid_spacing_mm": P,
                "nominal_web_shear_capacity_kn": P,
                "action_kn": N,
                "moment_action_knm": N,
            },
            [
                "yield_strength_mpa",
                "compression_flange_gross_area_mm2",
                "compression_flange_effective_area_mm2",
                "tension_flange_gross_area_mm2",
                "tension_flange_net_area_mm2",
                "tension_flange_ultimate_strength_mpa",
                "flange_centroid_spacing_mm",
                "nominal_web_shear_capacity_kn",
                "action_kn",
                "moment_action_knm",
            ],
        ),
        _variant(
            "shear",
            {
                "yield_strength_mpa": P,
                "web_area_mm2": P,
                "panel_depth_mm": P,
                "web_thickness_mm": P,
                "stiffener_spacing_mm": P,
                "tension_field": {"type": "boolean"},
                "stress_max_average_ratio": _number(1),
                "action_kn": N,
                "moment_action_knm": N,
                "section_moment_capacity_knm": P,
            },
            [
                "yield_strength_mpa",
                "web_area_mm2",
                "panel_depth_mm",
                "web_thickness_mm",
                "action_kn",
                "moment_action_knm",
                "section_moment_capacity_knm",
            ],
        ),
        _variant(
            "shear_with_flange_restraint",
            {
                "yield_strength_mpa": P,
                "web_area_mm2": P,
                "panel_depth_mm": P,
                "web_thickness_mm": P,
                "stiffener_spacing_mm": P,
                "tension_field": {"type": "boolean"},
                "stress_max_average_ratio": _number(1),
                "action_kn": N,
                "moment_action_knm": N,
                "section_moment_capacity_knm": P,
                "flange_thickness_mm": P,
                "clear_web_depth_mm": P,
                "flange_outstand_from_web_midplane_mm": N,
                "number_of_webs": {"type": "integer", "minimum": 1, "maximum": 100},
                "clear_distance_between_webs_mm": P,
                "no_longitudinal_stiffeners_verified": {"const": True},
            },
            [
                "yield_strength_mpa",
                "web_area_mm2",
                "panel_depth_mm",
                "web_thickness_mm",
                "action_kn",
                "moment_action_knm",
                "section_moment_capacity_knm",
                "flange_thickness_mm",
                "clear_web_depth_mm",
                "flange_outstand_from_web_midplane_mm",
                "number_of_webs",
                "no_longitudinal_stiffeners_verified",
            ],
        ),
        _variant(
            "shear_with_rational_flange_restraint",
            {
                "yield_strength_mpa": P,
                "web_area_mm2": P,
                "panel_depth_mm": P,
                "web_thickness_mm": P,
                "stiffener_spacing_mm": P,
                "tension_field": {"const": False},
                "stress_max_average_ratio": _number(1),
                "action_kn": N,
                "moment_action_knm": N,
                "section_moment_capacity_knm": P,
                "alpha_f": P,
                "rational_analysis_verified": {"const": True},
                "rational_analysis_reference": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 2000,
                },
                "no_longitudinal_stiffeners_verified": {"const": True},
            },
            [
                "yield_strength_mpa",
                "web_area_mm2",
                "panel_depth_mm",
                "web_thickness_mm",
                "stiffener_spacing_mm",
                "tension_field",
                "action_kn",
                "moment_action_knm",
                "section_moment_capacity_knm",
                "alpha_f",
                "rational_analysis_verified",
                "rational_analysis_reference",
                "no_longitudinal_stiffeners_verified",
            ],
        ),
        _variant(
            "interaction",
            {
                "axial_mode": {"enum": ["compression", "tension"]},
                "section_axial_capacity_kn": P,
                "member_axial_x_kn": P,
                "member_axial_y_kn": P,
                "section_moment_x_knm": P,
                "section_moment_y_knm": P,
                "member_moment_x_knm": P,
                "axial_action_kn": N,
                "moment_x_knm": N,
                "moment_y_knm": N,
                "compact_doubly_symmetric_i_verified": {"const": True},
                "compact_rhs_shs_verified": {"const": True},
                "compression_form_factor_one_verified": {"const": True},
                "compression_form_factor_below_one_verified": {"const": True},
                "compact_i_out_of_plane_alternative": {"const": True},
                "uniform_moment_member_capacity_knm": P,
                "uniform_moment_member_capacity_verified": {"const": True},
                "uniform_moment_member_capacity_reference": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 2000,
                },
                "torsion_constant_j_mm4": P,
                "warping_constant_iw_mm6": P,
                "section_second_moment_x_mm4": P,
                "section_second_moment_y_mm4": P,
                "gross_area_mm2": P,
                "torsional_restraint_spacing_mm": P,
                "torsional_section_properties_verified": {"const": True},
                "beta_m": _number(-1, maximum=1),
                "no_transverse_loads_verified": {"const": True},
                "both_end_lateral_restraints_verified": {"const": True},
                "compression_form_factor": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "maximum": 1,
                },
                "web_clear_width_mm": P,
                "web_thickness_mm": P,
                "web_yield_strength_mpa": P,
                "web_residual_stress_category": R,
            },
            [
                "axial_mode",
                "section_axial_capacity_kn",
                "member_axial_x_kn",
                "member_axial_y_kn",
                "section_moment_x_knm",
                "section_moment_y_knm",
                "member_moment_x_knm",
                "axial_action_kn",
                "moment_x_knm",
                "moment_y_knm",
            ],
        )
        | {
            "allOf": [
                {
                    "if": {
                        "required": ["compact_i_out_of_plane_alternative"],
                        "properties": {"compact_i_out_of_plane_alternative": {"const": True}},
                    },
                    "then": {
                        "required": [
                            "compact_doubly_symmetric_i_verified",
                            "compression_form_factor_one_verified",
                            "uniform_moment_member_capacity_knm",
                            "uniform_moment_member_capacity_verified",
                            "uniform_moment_member_capacity_reference",
                            "torsion_constant_j_mm4",
                            "warping_constant_iw_mm6",
                            "section_second_moment_x_mm4",
                            "section_second_moment_y_mm4",
                            "gross_area_mm2",
                            "torsional_restraint_spacing_mm",
                            "torsional_section_properties_verified",
                            "beta_m",
                            "no_transverse_loads_verified",
                            "both_end_lateral_restraints_verified",
                        ],
                        "properties": {"axial_mode": {"const": "compression"}},
                    },
                    "else": {
                        "not": {
                            "anyOf": [
                                {"required": ["uniform_moment_member_capacity_knm"]},
                                {"required": ["uniform_moment_member_capacity_verified"]},
                                {"required": ["uniform_moment_member_capacity_reference"]},
                                {"required": ["torsion_constant_j_mm4"]},
                                {"required": ["warping_constant_iw_mm6"]},
                                {"required": ["section_second_moment_x_mm4"]},
                                {"required": ["section_second_moment_y_mm4"]},
                                {"required": ["gross_area_mm2"]},
                                {"required": ["torsional_restraint_spacing_mm"]},
                                {"required": ["torsional_section_properties_verified"]},
                                {"required": ["beta_m"]},
                                {"required": ["no_transverse_loads_verified"]},
                                {"required": ["both_end_lateral_restraints_verified"]},
                            ]
                        }
                    },
                }
            ]
        },
        _variant(
            "tension_distribution",
            {
                "configuration": {
                    "enum": [
                        "uniform",
                        "angle_short_leg",
                        "angle_other",
                        "channel_web",
                        "tee_flange",
                        "symmetric_paired",
                        "both_flanges",
                        "table_7_3_2_a",
                        "table_7_3_2_b",
                        "table_7_3_2_c",
                        "table_7_3_2_d",
                        "table_7_3_2_e",
                        "table_7_3_2_f",
                        "table_7_3_2_g",
                    ]
                },
                "unequal_angle_connected_by_short_leg": {"type": "boolean"},
                "connection_length_mm": P,
                "member_depth_mm": P,
                "maximum_member_design_force_kn": P,
                "top_flange_connection_design_capacity_kn": N,
                "bottom_flange_connection_design_capacity_kn": N,
                "member_part_count": {"type": "integer", "minimum": 1, "maximum": 100},
                "member_part_connections": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {
                        "type": "object",
                        "properties": {
                            "member_part_id": {
                                "type": "string",
                                "minLength": 1,
                                "maxLength": 100,
                            },
                            "maximum_part_design_force_kn": N,
                            "part_connection_design_capacity_kn": N,
                        },
                        "required": [
                            "member_part_id",
                            "maximum_part_design_force_kn",
                            "part_connection_design_capacity_kn",
                        ],
                        "additionalProperties": False,
                    },
                },
                "connection_conditions_verified": {"const": True},
            },
            ["configuration", "connection_conditions_verified"],
        ),
    ],
}
OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "standard",
        "operation",
        "scope",
        "values",
        "checks",
        "trace",
        "manual_requirements",
    ],
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "operation": {"type": "string"},
        "scope": {"type": "string"},
        "values": {"type": "object"},
        "checks": {"type": "object"},
        "trace": {"type": "array"},
        "manual_requirements": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}


def _finite(value):
    if isinstance(value, Mapping):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return not isinstance(value, (int, float)) or isfinite(value)


def _check(action, capacity):
    if capacity < 0 or not isfinite(capacity):
        raise ValueError("Invalid design capacity.")
    return {
        "action": action,
        "design_capacity": capacity,
        "utilisation": action / capacity if capacity else None,
        "satisfied": action <= capacity,
    }


def _plate(d):
    p = d["plate"]
    b, t, fy = p["width_mm"], p["thickness_mm"], d["yield_strength_mpa"]
    edge, stress, residual = p["edges"], p["stress"], p["residual"]
    circular = edge == "circular"
    if circular and stress != "uniform":
        raise ValueError("Circular section requires uniform classification stress.")
    if (stress == "internal_gradient" and edge != "both") or (
        stress == "outstand_gradient" and edge != "one"
    ):
        raise ValueError("Plate stress pattern is incompatible with edge support.")
    if circular:
        lp, ly = (42 if residual in ("LW", "HW") else 50), 120
        compression_limit = 82
    elif stress == "internal_gradient":
        lp, ly = 82, 115
        compression_limit = None
    elif edge == "both":
        lp, ly = 30, INTERNAL_PLATE_YIELD_LIMITS[residual]
        compression_limit = ly
    else:
        lp = {"SR": 10, "HR": 9, "CF": 8, "LW": 8, "HW": 8}[residual]
        compression_limit = {"SR": 16, "HR": 16, "CF": 15, "LW": 15, "HW": 14}[residual]
        ly = (
            {"SR": 25, "HR": 25, "CF": 22, "LW": 22, "HW": 22}[residual]
            if stress == "outstand_gradient"
            else compression_limit
        )
    slenderness = b / t * (fy / 250 if circular else sqrt(fy / 250))
    compression_slenderness = b / t * (fy / 250 if circular else sqrt(fy / 250))
    z, s = d["elastic_modulus_mm3"], d["plastic_modulus_mm3"]
    if s < z:
        raise ValueError("Plastic modulus must not be below elastic modulus.")
    compact = min(s, 1.5 * z)
    if slenderness <= lp:
        effective, category = compact, "compact"
    elif slenderness <= ly:
        effective = z + (ly - slenderness) / (ly - lp) * (compact - z)
        category = "non_compact"
    else:
        ratio = ly / slenderness
        if circular:
            factor = min(sqrt(ratio), (2 * ratio) ** 2)
        elif stress == "internal_gradient" or stress == "outstand_gradient":
            factor = ratio**2
        else:
            factor = ratio
        effective, category = z * factor, "slender"
    if compression_limit is None:
        effective_width = None
    else:
        ratio_c = compression_limit / compression_slenderness
        effective_width = (
            b * min(1, sqrt(ratio_c), (3 * ratio_c) ** 2) if circular else b * min(1, ratio_c)
        )
    return (
        {
            "element_slenderness": slenderness,
            "plasticity_limit": lp,
            "yield_limit": ly,
            "classification": category,
            "effective_modulus_mm3": effective,
            "section_capacity_knm": fy * effective / 1e6,
            "compression_yield_limit": compression_limit,
            "compression_effective_width_mm": effective_width,
        },
        {},
        ["5.2.2", "5.2.3", "5.2.4", "5.2.5", "6.2.3", "6.2.4"],
        [
            "Select the controlling plate by greatest element-slenderness/yield-limit ratio.",
            "Moduli must include applicable hole deductions under 5.2.6.",
            "Effective width is for uniform compression; assemble effective area under 6.2.2.",
        ],
    )


def _major_axis_section_properties(depth, flange_thickness, web_width, flange_areas):
    web_depth = depth - 2 * flange_thickness
    if web_depth <= 0:
        raise ValueError("Overall depth must exceed twice the flange thickness.")
    if any(area <= 0 for area in flange_areas):
        raise ValueError("Section flange areas must both be positive.")

    widths = [area / flange_thickness for area in flange_areas]
    rectangles = [
        (widths[0], 0.0, flange_thickness),
        (web_width, flange_thickness, depth - flange_thickness),
        (widths[1], depth - flange_thickness, depth),
    ]
    areas = [width * (y1 - y0) for width, y0, y1 in rectangles]
    centroids = [(y0 + y1) / 2 for _, y0, y1 in rectangles]
    total_area = fsum(areas)
    centroid = fsum(area * y for area, y in zip(areas, centroids, strict=True)) / total_area
    second_moment = fsum(
        width * (y1 - y0) ** 3 / 12 + area * (y - centroid) ** 2
        for (width, y0, y1), area, y in zip(rectangles, areas, centroids, strict=True)
    )

    target_area = total_area / 2
    accumulated_area = 0.0
    plastic_axis = None
    for width, y0, y1 in rectangles:
        area = width * (y1 - y0)
        if accumulated_area + area >= target_area:
            plastic_axis = y0 + (target_area - accumulated_area) / width
            break
        accumulated_area += area
    if plastic_axis is None:
        raise ValueError("Could not locate the net-section plastic neutral axis.")
    plastic_moments = []
    for width, y0, y1 in rectangles:
        top_end = min(y1, plastic_axis)
        if top_end > y0:
            plastic_moments.append(
                width * (plastic_axis * (top_end - y0) - (top_end**2 - y0**2) / 2)
            )
        bottom_start = max(y0, plastic_axis)
        if y1 > bottom_start:
            plastic_moments.append(
                width * ((y1**2 - bottom_start**2) / 2 - plastic_axis * (y1 - bottom_start))
            )
    plastic_modulus = fsum(plastic_moments)
    elastic_modulus_top = second_moment / centroid
    elastic_modulus_bottom = second_moment / (depth - centroid)
    return {
        "net_area_mm2": total_area,
        "centroid_from_top_mm": centroid,
        "second_moment_of_area_mm4": second_moment,
        "plastic_neutral_axis_from_top_mm": plastic_axis,
        "elastic_modulus_top_mm3": elastic_modulus_top,
        "elastic_modulus_bottom_mm3": elastic_modulus_bottom,
        "governing_elastic_modulus_mm3": min(elastic_modulus_top, elastic_modulus_bottom),
        "governing_fibre": "top" if elastic_modulus_top <= elastic_modulus_bottom else "bottom",
        "plastic_modulus_mm3": plastic_modulus,
    }


def _section_moduli(d):
    gross_flanges = d["gross_flange_areas_mm2"]
    net_flanges = d["net_flange_areas_mm2"]
    if len(gross_flanges) != len(net_flanges):
        raise ValueError("Gross and net flange area lists must have the same length.")
    if any(net > gross for gross, net in zip(gross_flanges, net_flanges, strict=True)):
        raise ValueError("A net flange area must not exceed its gross flange area.")

    gross_area = d["gross_area_mm2"]
    gross_components = sum(gross_flanges) + d["gross_web_area_mm2"]
    if not isclose(gross_area, gross_components, rel_tol=1e-9, abs_tol=1e-6):
        raise ValueError("Gross area must equal the supplied flange areas plus gross web area.")
    net_area = sum(net_flanges) + d["gross_web_area_mm2"]
    area_ratio = net_area / gross_area

    fy, fu = d["yield_strength_mpa"], d["ultimate_strength_mpa"]
    minimum_net_flange_ratio = fy / (0.85 * fu)
    reductions = [
        100 * (1 - net / gross) for gross, net in zip(gross_flanges, net_flanges, strict=True)
    ]
    reduction_limit = 100 * (1 - minimum_net_flange_ratio)
    excessive_flange_indices = [
        index
        for index, (gross, net) in enumerate(zip(gross_flanges, net_flanges, strict=True), start=1)
        if net / gross < minimum_net_flange_ratio
    ]
    gross_permitted = not excessive_flange_indices
    i_section_geometry = d.get("net_i_section_geometry")
    rhs_geometry = d.get("net_rhs_geometry")
    if i_section_geometry is not None and rhs_geometry is not None:
        raise ValueError("Supply one derived net-section geometry form only.")
    geometry = i_section_geometry or rhs_geometry
    is_rhs = rhs_geometry is not None
    section_form = "RHS/SHS" if is_rhs else "I-section"
    net_properties = None
    if geometry is not None:
        if len(gross_flanges) != 2 or len(net_flanges) != 2:
            raise ValueError("Derived net geometry requires top and bottom flange areas only.")
        if not isclose(gross_flanges[0], gross_flanges[1], rel_tol=1e-9, abs_tol=1e-6):
            raise ValueError(f"Net {section_form} geometry requires equal gross flange areas.")
        depth = geometry["overall_depth_mm"]
        flange_thickness = geometry["flange_thickness_mm"]
        web_thickness = geometry["web_thickness_mm"]
        web_depth = depth - 2 * flange_thickness
        if web_depth <= 0:
            raise ValueError("Overall depth must exceed twice the flange thickness.")
        gross_flange_width = gross_flanges[0] / flange_thickness
        web_width = web_thickness * (2 if is_rhs else 1)
        if web_width > gross_flange_width:
            raise ValueError(
                "Web thickness must not exceed the gross flange width; for RHS/SHS, "
                "the combined width of both webs is checked."
            )
        expected_web_area = web_width * web_depth
        if not isclose(d["gross_web_area_mm2"], expected_web_area, rel_tol=1e-9, abs_tol=1e-6):
            raise ValueError(
                f"Gross web area is inconsistent with the supplied {section_form} geometry."
            )
        if any(area <= 0 for area in net_flanges):
            raise ValueError("Net flange areas must both be positive.")
        gross_properties = _major_axis_section_properties(
            depth, flange_thickness, web_width, gross_flanges
        )
        if not isclose(
            d["gross_elastic_modulus_mm3"],
            gross_properties["elastic_modulus_top_mm3"],
            rel_tol=1e-6,
            abs_tol=1e-6,
        ) or not isclose(
            d["gross_plastic_modulus_mm3"],
            gross_properties["plastic_modulus_mm3"],
            rel_tol=1e-6,
            abs_tol=1e-6,
        ):
            raise ValueError(
                f"Gross section moduli are inconsistent with the supplied {section_form} geometry."
            )
        net_properties = _major_axis_section_properties(
            depth, flange_thickness, web_width, net_flanges
        )
        if not isclose(net_properties["net_area_mm2"], net_area, rel_tol=1e-9, abs_tol=1e-6):
            raise ValueError("Net flange areas are inconsistent with the supplied section areas.")

    has_net_elastic_modulus = "net_elastic_modulus_mm3" in d
    has_net_plastic_modulus = "net_plastic_modulus_mm3" in d
    if has_net_elastic_modulus != has_net_plastic_modulus:
        raise ValueError("Supply both net elastic and plastic section moduli, or neither.")
    if geometry is not None and has_net_elastic_modulus:
        raise ValueError("Supply derived net geometry or net moduli, not both.")

    if gross_permitted:
        selected_method = "gross_section"
        elastic_modulus = d["gross_elastic_modulus_mm3"]
        plastic_modulus = d["gross_plastic_modulus_mm3"]
    elif d["method"] == "area_ratio":
        selected_method = "area_ratio"
        elastic_modulus = d["gross_elastic_modulus_mm3"] * area_ratio
        plastic_modulus = d["gross_plastic_modulus_mm3"] * area_ratio
    else:
        if geometry is not None:
            selected_method = "net_section"
            elastic_modulus = net_properties["governing_elastic_modulus_mm3"]
            plastic_modulus = net_properties["plastic_modulus_mm3"]
        elif not has_net_elastic_modulus:
            raise ValueError(
                "Net-section method requires both net_elastic_modulus_mm3 and "
                "net_plastic_modulus_mm3."
            )
        else:
            selected_method = "net_section"
            elastic_modulus = d["net_elastic_modulus_mm3"]
            plastic_modulus = d["net_plastic_modulus_mm3"]

    if d["gross_plastic_modulus_mm3"] < d["gross_elastic_modulus_mm3"]:
        raise ValueError("Gross plastic modulus must not be below gross elastic modulus.")
    if plastic_modulus < elastic_modulus:
        raise ValueError("Selected plastic modulus must not be below elastic modulus.")

    values = {
        "gross_area_mm2": gross_area,
        "net_area_mm2": net_area,
        "net_to_gross_area_ratio": area_ratio,
        "flange_area_reductions_pct": reductions,
        "permitted_flange_area_reduction_pct": reduction_limit,
        "gross_section_moduli_permitted": gross_permitted,
        "selected_method": selected_method,
        "elastic_modulus_mm3": elastic_modulus,
        "plastic_modulus_mm3": plastic_modulus,
    }
    if net_properties is not None:
        values["net_section_properties"] = net_properties
    return (
        values,
        {
            "flange_hole_limit": {
                "limit_reduction_pct": reduction_limit,
                "actual_reductions_pct": reductions,
                "gross_section_moduli_permitted": gross_permitted,
            }
        },
        ["5.2.6", "9.1.10"],
        [
            "Apply fastener-hole deductions in accordance with Clause 9.1.10.",
            "The area-ratio method assumes the supplied flange and gross-web areas make up "
            "the gross section.",
            "Feed the selected elastic and plastic moduli into the applicable "
            "Clause 5.2.2–5.2.5 check.",
            *(
                [
                    f"Derived net properties apply only to the verified sharp-corner symmetric "
                    f"{section_form} geometry with major-axis bending and flange-only holes. "
                    "Verify that the net hole layout preserves the principal major axis, and "
                    "confirm the net flange areas and Clause 9.1.10 deductions against the "
                    "connection geometry; the input attestations are not independently "
                    "authenticated."
                ]
                if geometry is not None
                else [
                    "For the net-section method, net moduli must be independently established "
                    "for the actual geometry."
                ]
            ),
        ],
    )


def _alpha(length, radius, kf, fy, constant):
    ln = length / radius * sqrt(kf * fy / 250)
    aa = 2100 * (ln - 13.5) / (ln * ln - 15.3 * ln + 2050)
    modified = max(0, ln + aa * constant)
    q = (modified / 90) ** 2
    eta = max(0, 0.00326 * (modified - 13.5))
    a = q + 1 + eta
    alpha = min(1, 2 / (a + sqrt(max(0, a * a - 4 * q))))
    return ln, modified, alpha


def _compression(d):
    ag, an, ae = d["gross_area_mm2"], d["net_area_mm2"], d["effective_area_mm2"]
    if max(an, ae) > ag:
        raise ValueError("Net and effective areas must not exceed gross area.")
    kf, fy = ae / ag, d["yield_strength_mpa"]
    if kf < 1 and min(d["section_constant_x"], d["section_constant_y"]) < -0.5:
        raise ValueError("Section constant -1 is unavailable for form factor below 1.")
    ns = kf * an * fy / 1000
    values = {"form_factor": kf, "section_capacity_kn": ns}
    checks = {"section": _check(d["action_kn"], 0.9 * ns)}
    for axis in "xy":
        ln, modified, alpha = _alpha(
            d[f"effective_length_{axis}_mm"],
            d[f"radius_{axis}_mm"],
            kf,
            fy,
            d[f"section_constant_{axis}"],
        )
        values.update(
            {
                f"modified_slenderness_{axis}": ln,
                f"imperfection_slenderness_{axis}": modified,
                f"reduction_{axis}": alpha,
                f"member_capacity_{axis}_kn": alpha * ns,
            }
        )
        checks[axis] = _check(d["action_kn"], 0.9 * alpha * ns)
    return (
        values,
        checks,
        ["6.2.1", "6.2.2", "6.3.2", "6.3.3"],
        [
            "Effective lengths require structural restraint/analysis assessment under 4.6.3.",
            "Select section constants from Table 6.3.3(A/B) for fabrication and form factor.",
            "Limited to constant-section members whose governing mode is flexural buckling.",
        ],
    )


def _bending(d):
    ms, le = d["section_capacity_knm"], d["effective_length_mm"]
    # E and G in MPa, dimensions in mm: result N.mm converted to kN.m.
    mo = (
        sqrt(
            (pi**2 * ELASTIC_MODULUS_MPA * d["iy_mm4"] / le**2)
            * (
                SHEAR_MODULUS_MPA * d["torsion_constant_mm4"]
                + pi**2 * ELASTIC_MODULUS_MPA * d["warping_constant_mm6"] / le**2
            )
        )
        / 1e6
    )
    ratio = ms / mo
    reduction = 1.8 / (sqrt(ratio * ratio + 3) + ratio)
    mb = min(ms, d["moment_factor"] * reduction * ms)
    return (
        {
            "reference_buckling_moment_knm": mo,
            "slenderness_reduction": reduction,
            "member_capacity_knm": mb,
            "full_lateral_restraint_qualifies": mb >= ms,
        },
        {"bending": _check(d["action_knm"], 0.9 * mb)},
        ["5.3.2.1", "5.6.1.1"],
        [
            "Constant equal-flanged open section with full/partial restraint at both ends only.",
            "Effective length must include twist/load-height/lateral-rotation factors under 5.6.3.",
            "Moment factor must be derived under 5.6.1.1; use the advanced_members "
            "moment_modification_factor operation for the quarter-point equation or assess "
            "another permitted route. Default conservative selection is 1.",
            "Clause 5.3.2.1 full-restraint qualification is true only when nominal Mb reaches Ms.",
            "Restraints and critical section/critical flange require 5.3–5.5 assessment.",
        ],
    )


def _shear(d, flange_restraint_factor=1, flange_restraint_values=None):
    fy = d["yield_strength_mpa"]
    slenderness = d["panel_depth_mm"] / d["web_thickness_mm"] * sqrt(fy / 250)
    vw = 0.6 * fy * d["web_area_mm2"] / 1000
    av = min(1, (82 / slenderness) ** 2)
    ad = 1
    if "stiffener_spacing_mm" in d:
        aspect = d["stiffener_spacing_mm"] / d["panel_depth_mm"]
        if aspect <= 3:
            av = min(
                1,
                (82 / slenderness) ** 2
                * (0.75 / aspect**2 + 1 if aspect >= 1 else 1 / aspect**2 + 0.75),
            )
            if d.get("tension_field", False):
                ad = 1 + (1 - av) / (1.15 * av * sqrt(1 + aspect**2))
        elif d.get("tension_field", False):
            raise ValueError("Tension field requires stiffener spacing/panel depth <= 3.")
    elif d.get("tension_field", False):
        raise ValueError("Tension field requires transverse stiffeners.")
    vu = min(vw, av * ad * flange_restraint_factor * vw)
    vv = vu * min(1, 2 / (0.9 + d.get("stress_max_average_ratio", 1)))
    moment_ratio = d["moment_action_knm"] / (0.9 * d["section_moment_capacity_knm"])
    vm = vv * (
        1
        if moment_ratio <= 0.75
        else (max(0, 2.2 - 1.6 * moment_ratio) if moment_ratio <= 1 else 0)
    )
    checks = {
        "shear_bending": _check(d["action_kn"], 0.9 * vm),
        "bending": _check(d["moment_action_knm"], 0.9 * d["section_moment_capacity_knm"]),
    }
    values = {
        "web_slenderness": slenderness,
        "shear_yield_capacity_kn": vw,
        "buckling_reduction": av,
        "tension_field_factor": ad,
        "flange_restraint_factor": flange_restraint_factor,
        "shear_capacity_kn": vv,
        "shear_bending_capacity_kn": vm,
    }
    if flange_restraint_values is not None:
        values.update(flange_restraint_values)
    clauses = ["5.11.2", "5.11.3", "5.11.4", "5.11.5"]
    manual = [
        "Flat webs only; web layout/thickness/openings require 5.9–5.10 assessment.",
        "Tension-field credit requires verified stiffener/end-post provisions in 5.15.",
        "Stress maximum/average ratio requires rational elastic stress analysis.",
    ]
    if flange_restraint_values is None:
        manual.append("Flange restraint factor taken conservatively as 1 under 5.11.5.2.")
    elif flange_restraint_values.get("flange_restraint_method") == "rational_buckling_analysis":
        clauses.append("5.11.5.2")
        manual.append(
            "The rational buckling analysis, its reference and the supplied alpha_f are "
            "recorded but not authenticated by this calculation. Verify the flat-web "
            "configuration and absence of longitudinal stiffeners."
        )
    else:
        clauses.append("5.11.5.2")
        manual.append(
            "Verify the no-longitudinal-stiffener condition and that supplied flange/web "
            "dimensions describe the section."
        )
    clauses.append("5.12.3")
    return values, checks, clauses, manual


def _shear_with_flange_restraint(d):
    if d["number_of_webs"] > 1:
        if "clear_distance_between_webs_mm" not in d:
            raise ValueError("Multiple webs require their clear distance for the flange limit.")
        clear_limit = d["clear_distance_between_webs_mm"] / 2
    else:
        if "clear_distance_between_webs_mm" in d:
            raise ValueError("Clear distance between webs applies only to multiple-web sections.")
        clear_limit = float("inf")
    material_limit = 12 * d["flange_thickness_mm"] / sqrt(d["yield_strength_mpa"] / 250)
    candidates = {
        "yield_scaled_flange_limit_mm": material_limit,
        "flange_edge_limit_mm": d["flange_outstand_from_web_midplane_mm"],
    }
    if d["number_of_webs"] > 1:
        candidates["half_clear_web_spacing_limit_mm"] = clear_limit
    effective_outstand = min(candidates.values())
    depth, thickness = d["clear_web_depth_mm"], d["web_thickness_mm"]
    restraint_factor = 1.6 - 0.6 / sqrt(
        1 + 40 * effective_outstand * d["flange_thickness_mm"] ** 2 / (depth**2 * thickness)
    )
    details = {
        "effective_flange_outstand_mm": effective_outstand,
        "effective_flange_outstand_limits_mm": candidates,
    }
    return _shear(d, restraint_factor, details)


def _shear_with_rational_flange_restraint(d):
    aspect = d["stiffener_spacing_mm"] / d["panel_depth_mm"]
    if aspect > 3:
        raise ValueError(
            "Rational flange-restraint analysis requires stiffener spacing/panel depth <= 3."
        )
    reference = d["rational_analysis_reference"].strip()
    if not reference:
        raise ValueError("Rational flange-restraint analysis reference must not be blank.")
    details = {
        "flange_restraint_method": "rational_buckling_analysis",
        "rational_analysis_reference": reference,
        "stiffener_spacing_to_panel_depth_ratio": aspect,
    }
    return _shear(d, d["alpha_f"], details)


def _chs_shear(d):
    gross = d["gross_area_mm2"]
    net = d["net_area_mm2"]
    if net > gross:
        raise ValueError("Net area must not exceed gross area.")
    use_gross = not d["oversized_fastener_holes_present"] or net > 0.9 * gross
    effective_area = gross if use_gross else net
    nominal_shear = 0.36 * d["yield_strength_mpa"] * effective_area / 1000
    section_capacity = d["section_moment_capacity_knm"]
    moment_design_capacity = 0.9 * section_capacity
    moment_ratio = d["moment_action_knm"] / moment_design_capacity
    if moment_ratio <= 0.75:
        reduced_nominal = nominal_shear
    elif moment_ratio <= 1:
        reduced_nominal = nominal_shear * (2.2 - 1.6 * moment_ratio)
    else:
        reduced_nominal = 0
    return (
        {
            "effective_shear_area_mm2": effective_area,
            "effective_area_method": "gross" if use_gross else "net",
            "nominal_shear_yield_capacity_kn": nominal_shear,
            "nominal_shear_capacity_with_bending_kn": reduced_nominal,
            "moment_to_design_capacity_ratio": moment_ratio,
        },
        {
            "shear_bending": _check(d["action_kn"], 0.9 * reduced_nominal),
            "bending": _check(d["moment_action_knm"], moment_design_capacity),
        },
        ["5.11.3", "5.11.4", "5.12.3"],
        [
            "Circular hollow section only. Verify gross/net areas and hole conditions, "
            "including Clause 9.1.10 deductions.",
            "Use the whole-section interaction method in Clause 5.12.3; flange-only "
            "proportioning under 5.12.2 is outside this operation.",
            "Section shear area and moment capacity are supplied inputs; this does not "
            "verify cross-section classification or connection capacity.",
        ],
    )


def _shear_proportioning(d):
    if d["compression_flange_effective_area_mm2"] > d["compression_flange_gross_area_mm2"]:
        raise ValueError("Compression flange effective area must not exceed its gross area.")
    if d["tension_flange_net_area_mm2"] > d["tension_flange_gross_area_mm2"]:
        raise ValueError("Tension flange net area must not exceed its gross area.")
    tension_area_by_fracture = (
        0.85
        * d["tension_flange_net_area_mm2"]
        * d["tension_flange_ultimate_strength_mpa"]
        / d["yield_strength_mpa"]
    )
    tension_effective_area = min(d["tension_flange_gross_area_mm2"], tension_area_by_fracture)
    effective_flange_area = min(d["compression_flange_effective_area_mm2"], tension_effective_area)
    nominal_flange_moment = (
        effective_flange_area * d["flange_centroid_spacing_mm"] * d["yield_strength_mpa"] / 1e6
    )
    design_moment = 0.9 * nominal_flange_moment
    design_shear = 0.9 * d["nominal_web_shear_capacity_kn"]
    return (
        {
            "tension_flange_area_by_fracture_limit_mm2": tension_area_by_fracture,
            "effective_tension_flange_area_mm2": tension_effective_area,
            "effective_flange_area_mm2": effective_flange_area,
            "nominal_flange_moment_capacity_knm": nominal_flange_moment,
            "design_flange_moment_capacity_knm": design_moment,
            "design_web_shear_capacity_kn": design_shear,
        },
        {
            "flange_moment": _check(d["moment_action_knm"], design_moment),
            "web_shear": _check(d["action_kn"], design_shear),
        },
        ["5.12.2"],
        [
            "Use only when bending is assumed to be resisted by the flanges; the web "
            "shear capacity is supplied from Clause 5.11.",
            "Compression flange effective area is supplied from Clause 6.2.2. Verify "
            "tension-flange net area using Clause 9.1.10.",
            "A single flange yield strength is used. Sections with differing flange "
            "grades require separate assessment.",
        ],
    )


def _interaction(d):
    phi = 0.9
    n, mx, my = d["axial_action_kn"], d["moment_x_knm"], d["moment_y_knm"]
    ns, msx, msy = (
        d["section_axial_capacity_kn"],
        d["section_moment_x_knm"],
        d["section_moment_y_knm"],
    )
    mb = d["member_moment_x_knm"]
    if mb > msx:
        raise ValueError("Member moment capacity must not exceed section capacity.")
    compact_i_verified = d.get("compact_doubly_symmetric_i_verified", False)
    compact_rhs_shs_verified = d.get("compact_rhs_shs_verified", False)
    kf_one_verified = d.get("compression_form_factor_one_verified", False)
    kf_below_one_verified = d.get("compression_form_factor_below_one_verified", False)
    web_input_names = (
        "compression_form_factor",
        "web_clear_width_mm",
        "web_thickness_mm",
        "web_yield_strength_mpa",
        "web_residual_stress_category",
    )
    has_web_route_inputs = any(name in d for name in web_input_names)
    if compact_i_verified and compact_rhs_shs_verified:
        raise ValueError("Select one verified compact section type for the Clause 8.3 route.")
    if kf_one_verified and kf_below_one_verified:
        raise ValueError("Select one Clause 8.3.2 compression form-factor route.")
    if kf_one_verified and not (compact_i_verified or compact_rhs_shs_verified):
        raise ValueError("Clause 8.3.2(a) requires a verified compact section route.")
    if kf_one_verified and d["axial_mode"] != "compression":
        raise ValueError("The kf=1.0 confirmation applies only to compression members.")
    if has_web_route_inputs and not kf_below_one_verified:
        raise ValueError("Clause 8.3.2(b) inputs require its explicit verification flag.")
    web_route = None
    if kf_below_one_verified:
        if d["axial_mode"] != "compression":
            raise ValueError("Clause 8.3.2(b) applies only to compression members.")
        if not (compact_i_verified or compact_rhs_shs_verified):
            raise ValueError("Clause 8.3.2(b) requires a verified compact section route.")
        missing = [name for name in web_input_names if name not in d]
        if missing:
            raise ValueError(
                "Clause 8.3.2(b) requires the form factor and web geometry/material inputs."
            )
        kf = d["compression_form_factor"]
        if kf >= 1.0:
            raise ValueError("Clause 8.3.2(b) requires a verified compression form factor kf<1.0.")
        web_slenderness = (
            d["web_clear_width_mm"]
            / d["web_thickness_mm"]
            * sqrt(d["web_yield_strength_mpa"] / 250)
        )
        web_yield_limit = INTERNAL_PLATE_YIELD_LIMITS[d["web_residual_stress_category"]]
        if web_slenderness > 82:
            raise ValueError(
                "Clause 8.3.2(b) web slenderness exceeds the Clause 5.2.3 compactness limit."
            )
        web_route = {
            "compression_form_factor": kf,
            "web_slenderness": web_slenderness,
            "web_yield_limit": web_yield_limit,
        }
    ratio = n / (phi * ns)
    mrx, mry = msx * max(0, 1 - ratio), msy * max(0, 1 - ratio)
    compact_i_out_of_plane = d.get("compact_i_out_of_plane_alternative", False)
    out_of_plane_alternative_values = None
    if d["axial_mode"] == "compression":
        ncx, ncy = d["member_axial_x_kn"], d["member_axial_y_kn"]
        if max(ncx, ncy) > ns:
            raise ValueError("Member axial capacity must not exceed section capacity.")
        mix = msx * max(0, 1 - n / (phi * ncx))
        miy = msy * max(0, 1 - n / (phi * ncy))
        mox = mb * max(0, 1 - n / (phi * ncy))
        if compact_i_out_of_plane:
            uniform_mb = d["uniform_moment_member_capacity_knm"]
            if uniform_mb > msx:
                raise ValueError(
                    "Uniform-moment member capacity must not exceed section moment capacity."
                )
            torsional_stiffness = SHEAR_MODULUS_MPA * d["torsion_constant_j_mm4"]
            warping_stiffness = (
                pi**2
                * ELASTIC_MODULUS_MPA
                * d["warping_constant_iw_mm6"]
                / d["torsional_restraint_spacing_mm"] ** 2
            )
            polar_radius_squared = (
                d["section_second_moment_x_mm4"] + d["section_second_moment_y_mm4"]
            ) / d["gross_area_mm2"]
            noz = (torsional_stiffness + warping_stiffness) / polar_radius_squared / 1000
            if not isfinite(noz) or noz <= 0:
                raise ValueError("Clause 8.4.4.1 elastic torsional buckling capacity is invalid.")
            compression_ratio = n / (phi * ncy)
            torsional_ratio = n / (phi * noz)
            inverse_alpha_bc = (1 - d["beta_m"]) / 2 + ((1 + d["beta_m"]) / 2) ** 3 * (
                0.4 - 0.23 * compression_ratio
            )
            if compression_ratio >= 1 or torsional_ratio >= 1:
                alpha_bc = None
                unconstrained_mox = 0.0
            else:
                alpha_bc = 1 / inverse_alpha_bc
                unconstrained_mox = (
                    alpha_bc * uniform_mb * sqrt((1 - compression_ratio) * (1 - torsional_ratio))
                )
            compact_mrx = min(msx, max(0.0, 1.18 * msx * (1 - ratio)))
            mox = min(unconstrained_mox, compact_mrx)
            out_of_plane_alternative_values = {
                "beta_m": d["beta_m"],
                "alpha_bc": alpha_bc,
                "uniform_moment_member_capacity_knm": uniform_mb,
                "uniform_moment_member_capacity_reference": d[
                    "uniform_moment_member_capacity_reference"
                ],
                "elastic_torsional_buckling_capacity_kn": noz,
                "torsion_constant_j_mm4": d["torsion_constant_j_mm4"],
                "warping_constant_iw_mm6": d["warping_constant_iw_mm6"],
                "section_second_moment_x_mm4": d["section_second_moment_x_mm4"],
                "section_second_moment_y_mm4": d["section_second_moment_y_mm4"],
                "gross_area_mm2": d["gross_area_mm2"],
                "torsional_restraint_spacing_mm": d["torsional_restraint_spacing_mm"],
                "torsion_stiffness_nmm2": torsional_stiffness,
                "warping_stiffness_nmm2": warping_stiffness,
                "polar_radius_squared_mm2": polar_radius_squared,
                "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
                "shear_modulus_mpa": SHEAR_MODULUS_MPA,
                "compression_capacity_ratio": compression_ratio,
                "torsional_buckling_ratio": torsional_ratio,
                "unconstrained_out_of_plane_capacity_knm": unconstrained_mox,
                "section_reduced_moment_capacity_knm": compact_mrx,
                "section_capacity_limit_applied": unconstrained_mox > compact_mrx,
                "compact_doubly_symmetric_i_verified": True,
                "compression_form_factor_one_verified": True,
                "uniform_moment_member_capacity_verified": True,
                "torsional_section_properties_verified": True,
                "no_transverse_loads_verified": True,
                "both_end_lateral_restraints_verified": True,
            }
        mcx = min(mix, mox)
    else:
        mix, miy = mrx, mry
        mox = min(mb * (1 + ratio), mrx)
        mcx = min(mrx, mox)
    section_util = ratio + mx / (phi * msx) + my / (phi * msy)
    if (mx and mcx == 0) or (my and miy == 0):
        member_util = None
        member_satisfied = False
    else:
        member_util = (mx / (phi * mcx) if mcx else 0) ** 1.4 + (
            my / (phi * miy) if miy else 0
        ) ** 1.4
        member_satisfied = member_util <= 1 and ratio <= 1
    if compact_i_out_of_plane and (compression_ratio >= 1 or torsional_ratio >= 1):
        member_satisfied = False
    checks = {
        "section_combined": {"utilisation": section_util, "satisfied": section_util <= 1},
        "member_combined": {"utilisation": member_util, "satisfied": member_satisfied},
        "in_plane_x": _check(mx, phi * mix),
        "in_plane_y": _check(my, phi * miy),
        "out_of_plane_x": _check(mx, phi * mox),
    }
    if compact_i_out_of_plane:
        checks["out_of_plane_elastic_torsional_buckling"] = _check(
            n, phi * out_of_plane_alternative_values["elastic_torsional_buckling_capacity_kn"]
        )
        checks["member_combined"]["satisfied"] &= checks["out_of_plane_elastic_torsional_buckling"][
            "satisfied"
        ]
    if d["axial_mode"] == "compression":
        checks["member_axial_x"] = _check(n, phi * d["member_axial_x_kn"])
        checks["member_axial_y"] = _check(n, phi * d["member_axial_y_kn"])
        checks["member_combined"]["satisfied"] &= all(
            checks[key]["satisfied"] for key in ("member_axial_x", "member_axial_y")
        )
    values = {
        "section_reduced_x_knm": mrx,
        "section_reduced_y_knm": mry,
        "in_plane_x_knm": mix,
        "in_plane_y_knm": miy,
        "out_of_plane_x_knm": mox,
        "out_of_plane_method": ("compact_i_alternative" if compact_i_out_of_plane else "general"),
    }
    if out_of_plane_alternative_values is not None:
        values.update(out_of_plane_alternative_values)
    clauses = ["8.3.2", "8.3.3", "8.3.4", "8.4.2", "8.4.4", "8.4.5"]
    manual = [
        "Elastic analysis only; moments must satisfy 8.2 second-order requirements.",
        "Section general linear paths used; optional compact-section enhancements omitted.",
        "Compression in-plane effective-length assumptions must satisfy 8.4.2.2.",
        "Special eccentrically connected angle and plastic-analysis paths excluded.",
    ]
    if compact_i_out_of_plane:
        clauses.append("8.4.4.1 compact-I alternative")
        manual.append(
            "The compact-I out-of-plane alternative requires a verified compact doubly "
            "symmetric I-section with kf=1.0, no transverse loads, and lateral restraint "
            "at both ends. Verify the supplied section constants and torsional-restraint "
            "spacing independently. This operation calculates N_oz, the Clause 8.3.2(a) "
            "section limit and the alpha_bc interaction. The supplied M_bxo must be "
            "calculated to Clause 5.6 with alpha_m=1 and is recorded with its reference. "
            "Verify beta_m from the end moments; reverse curvature is positive."
        )
    if compact_i_verified or compact_rhs_shs_verified:
        compact_mrx = mrx
        compact_x_method = "8.3.2 general"
        compact_x_factor = None
        if web_route is not None:
            compact_x_factor = 1 + 0.18 * (82 - web_route["web_slenderness"]) / (
                82 - web_route["web_yield_limit"]
            )
            compact_mrx = min(
                msx,
                max(0.0, msx * (1 - ratio) * compact_x_factor),
            )
            compact_x_method = "8.3.2(b)"
        elif d["axial_mode"] == "tension" or kf_one_verified:
            compact_mrx = min(msx, max(0.0, 1.18 * msx * (1 - ratio)))
            compact_x_method = "8.3.2(a)"
        if compact_i_verified:
            compact_mry = min(msy, max(0.0, 1.19 * msy * (1 - ratio**2)))
            compact_y_method = "8.3.3(a)"
        else:
            compact_mry = min(msy, max(0.0, 1.18 * msy * (1 - ratio)))
            compact_y_method = "8.3.3(b)"
        compact_gamma = min(1.4 + ratio, 2.0)
        compact_x_design = phi * compact_mrx
        compact_y_design = phi * compact_mry

        def powered_term(action, capacity):
            if capacity == 0:
                return 0.0 if action == 0 else None
            return (action / capacity) ** compact_gamma

        x_term = powered_term(mx, compact_x_design)
        y_term = powered_term(my, compact_y_design)
        compact_biaxial_util = None if x_term is None or y_term is None else x_term + y_term
        values.update(
            {
                "compact_section_reduced_x_knm": compact_mrx,
                "compact_section_reduced_y_knm": compact_mry,
                "compact_section_design_capacity_x_knm": compact_x_design,
                "compact_section_design_capacity_y_knm": compact_y_design,
                "compact_section_biaxial_gamma": compact_gamma,
                "compact_section_x_reduction_method": compact_x_method,
                "compact_section_y_reduction_method": compact_y_method,
            }
        )
        if web_route is not None:
            values.update(
                {
                    "compact_section_compression_form_factor": web_route["compression_form_factor"],
                    "compact_section_web_lambda_w": web_route["web_slenderness"],
                    "compact_section_web_lambda_wy": web_route["web_yield_limit"],
                    "compact_section_x_reduction_factor": compact_x_factor,
                }
            )
        compact_minor_check = _check(my, compact_y_design)
        compact_minor_check["axial_capacity_satisfied"] = ratio <= 1
        compact_minor_check["satisfied"] &= ratio <= 1
        checks["compact_minor_axis_component"] = compact_minor_check
        checks["compact_section_biaxial"] = {
            "utilisation": compact_biaxial_util,
            "satisfied": (
                ratio <= 1 and compact_biaxial_util is not None and compact_biaxial_util <= 1
            ),
        }
        clauses.append(compact_y_method)
        if compact_x_method in ("8.3.2(a)", "8.3.2(b)"):
            clauses.append(compact_x_method)
        manual[1] = (
            "The verified compact section route is reported alongside the "
            "general linear section interaction."
        )
        manual.extend(
            [
                "The compact route requires independently verified Clause 5.2.3 compactness, "
                "doubly symmetric I-section or AS/NZS 1163 RHS/SHS geometry as selected, "
                "Clause 5.2 moment capacities and the Clause 6.2 or 7.2 axial capacity.",
                "The compact biaxial check uses the general Clause 8.3.2 major-axis reduction "
                "unless Clause 8.3.2(a) applies to tension or verified compression with kf=1.0, "
                "or Clause 8.3.2(b) applies to verified compression with kf<1.0. It uses Clause "
                "8.3.3(a) for I-sections or 8.3.3(b) for RHS/SHS. Repeat at all critical "
                "sections along the member.",
            ]
        )
        if web_route is not None:
            manual.append(
                "Verify that the supplied section axial capacity uses this Clause 6.2.2 form "
                "factor, that the web clear width and yield strength are correct, and that the "
                "residual-stress category matches the fabrication evidence. Other section "
                "elements must also satisfy Clause 5.2.3 compactness."
            )
    return (
        values,
        checks,
        clauses,
        manual,
    )


def _distribution(d):
    configuration = d["configuration"]
    factors = {
        "uniform": 1,
        "angle_short_leg": 0.75,
        "angle_other": 0.85,
        "channel_web": 0.85,
        "tee_flange": 0.9,
        "symmetric_paired": 1,
        "both_flanges": 0.85,
    }
    checks = {}
    manual = []
    if configuration.startswith("table_7_3_2_"):
        case = configuration[-1]
        if case in ("a", "b"):
            if "unequal_angle_connected_by_short_leg" not in d:
                raise ValueError(
                    "Table 7.3.2 cases (a) and (b) require the unequal-angle short-leg condition."
                )
            factor = 0.75 if d["unequal_angle_connected_by_short_leg"] else 0.85
        else:
            if "unequal_angle_connected_by_short_leg" in d:
                raise ValueError(
                    "The unequal-angle short-leg condition applies only to Table 7.3.2 "
                    "cases (a) and (b)."
                )
            factor = {"c": 0.85, "d": 0.90, "e": 1.0, "f": 1.0, "g": 1.0}[case]
        checks["table_7_3_2_correction_factor"] = {
            "clause": "Table 7.3.2",
            "case": f"({case})",
            "tension_distribution_factor": factor,
            "satisfied": True,
        }
        manual.append(
            f"Verify that the member and connection geometry match Table 7.3.2 case ({case}); "
            "case selection is not inferred from section geometry."
        )
        if case in ("a", "b"):
            manual.append(
                "For cases (a) and (b), confirm whether unequal angles are connected by "
                "the short leg."
            )
    elif configuration == "uniform":
        transfer_inputs = ("member_part_count", "member_part_connections")
        if any(name not in d for name in transfer_inputs):
            raise ValueError(
                "Uniform distribution requires a count and design force/capacity for each "
                "connected member part."
            )
        parts = d["member_part_connections"]
        if len(parts) != d["member_part_count"]:
            raise ValueError("List every connected member part exactly once.")
        part_ids = [part["member_part_id"] for part in parts]
        if len(set(part_ids)) != len(part_ids):
            raise ValueError("Member part identifiers must be unique.")
        part_checks = [
            {
                "member_part_id": part["member_part_id"],
                "maximum_part_design_force_kn": part["maximum_part_design_force_kn"],
                "part_connection_design_capacity_kn": part["part_connection_design_capacity_kn"],
                "satisfied": (
                    part["part_connection_design_capacity_kn"]
                    >= part["maximum_part_design_force_kn"]
                ),
            }
            for part in parts
        ]
        transfer_satisfied = all(part["satisfied"] for part in part_checks)
        checks["uniform_connection_part_capacity"] = {
            "clause": "7.3.1(b)",
            "parts": part_checks,
            "satisfied": transfer_satisfied,
        }
        factor = factors[configuration] if transfer_satisfied else None
        manual.append(
            "Verify under Clause 7.3.1(a) that connections are made to every member part and "
            "are symmetrically placed about the member centroidal axis. The Clause 7.3.1(b) "
            "capacity comparison uses the supplied maximum force for each part."
        )
    elif configuration == "both_flanges":
        if "connection_length_mm" not in d or "member_depth_mm" not in d:
            raise ValueError("Both-flange connection requires length and depth.")
        if d["connection_length_mm"] < d["member_depth_mm"]:
            raise ValueError("Both-flange connection length must be at least member depth.")
        transfer_inputs = (
            "maximum_member_design_force_kn",
            "top_flange_connection_design_capacity_kn",
            "bottom_flange_connection_design_capacity_kn",
        )
        if any(name not in d for name in transfer_inputs):
            raise ValueError(
                "Both-flange connection requires the maximum member design force and "
                "connection capacity for each flange."
            )
        minimum_flange_capacity = d["maximum_member_design_force_kn"] / 2
        top_capacity = d["top_flange_connection_design_capacity_kn"]
        bottom_capacity = d["bottom_flange_connection_design_capacity_kn"]
        transfer_satisfied = all(
            capacity >= minimum_flange_capacity for capacity in (top_capacity, bottom_capacity)
        )
        checks["both_flange_force_transfer"] = {
            "clause": "7.3.2(b)(ii)",
            "maximum_member_design_force_kn": d["maximum_member_design_force_kn"],
            "minimum_design_capacity_each_flange_kn": minimum_flange_capacity,
            "top_flange_connection_design_capacity_kn": top_capacity,
            "bottom_flange_connection_design_capacity_kn": bottom_capacity,
            "satisfied": transfer_satisfied,
        }
        factor = factors[configuration] if transfer_satisfied else None
        manual.append(
            "Verify the member is a solid I-section or channel connected by both flanges only. "
            "The Clause 7.3.2(b)(ii) force-transfer check must pass before "
            "its kt factor can be used."
        )
    else:
        factor = factors[configuration]
        manual.append(
            "Verify the selected configuration against the applicable Table 7.3.2 diagram; "
            "the table case is not inferred from member geometry."
        )
    if configuration in ("angle_short_leg", "angle_other"):
        manual.append(
            "The short-leg factor applies only to unequal angles connected by the short leg."
        )
    if configuration == "symmetric_paired":
        manual.append("Verify that the paired member arrangement is symmetric.")
    return (
        {"tension_distribution_factor": factor},
        checks,
        ["7.3.1", "7.3.2"],
        manual,
    )


def run_members(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and calculate one documented member-design operation."""
    if not isinstance(inputs, Mapping):
        raise ValueError("Inputs must be an object.")
    data = dict(inputs)
    validate_standard_strengths(data)
    try:
        Draft202012Validator(INPUT_SCHEMA).validate(data)
    except ValidationError as exc:
        raise ValueError(exc.message) from exc
    if not _finite(data):
        raise ValueError("All numerical values must be finite.")
    functions = {
        "plate": _plate,
        "section_moduli": _section_moduli,
        "compression": _compression,
        "bending": _bending,
        "shear": _shear,
        "shear_with_flange_restraint": _shear_with_flange_restraint,
        "shear_with_rational_flange_restraint": _shear_with_rational_flange_restraint,
        "chs_shear": _chs_shear,
        "shear_proportioning": _shear_proportioning,
        "interaction": _interaction,
        "tension_distribution": _distribution,
    }
    try:
        values, checks, clauses, manual = functions[data["operation"]](data)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Input magnitudes exceed the numerical calculation range.") from exc
    result = {
        "standard": "AS 4100:2020",
        "operation": data["operation"],
        "scope": "Calculation primitive; manual applicability and restraint checks required",
        "values": values,
        "checks": checks,
        "trace": [{"clause": clause} for clause in clauses],
        "manual_requirements": manual,
    }
    if not _finite(result):
        raise ValueError("Calculated values must be finite.")
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result
