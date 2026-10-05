# SPDX-License-Identifier: AGPL-3.0-only
"""Further member provisions with explicit external analysis prerequisites."""

from math import cos, isclose, isfinite, pi, radians, sqrt

from .standards import ELASTIC_MODULUS_MPA, SHEAR_MODULUS_MPA
from .validation import (
    NONNEGATIVE as N,
)
from .validation import (
    POSITIVE as P,
)
from .validation import (
    SIGNED as S,
)
from .validation import (
    YIELD_STRESS as FY,
)
from .validation import (
    capacity_check,
    object_schema,
    result,
    validate,
)


def _schema(operation, properties, optional=()):
    return object_schema(
        {"operation": {"const": operation}, **properties},
        required=["operation", *(key for key in properties if key not in optional)],
    )


def _full_lateral_restraint_schema():
    common = {
        "segment_length_mm": P,
        "yield_strength_mpa": FY,
        "section_properties_verified": VERIFIED,
        "both_ends_restrained_verified": VERIFIED,
    }
    sections = {
        "equal_flanged_i": (
            {"radius_of_gyration_y_mm": P},
            ["radius_of_gyration_y_mm"],
        ),
        "equal_flanged_channel": (
            {"radius_of_gyration_y_mm": P},
            ["radius_of_gyration_y_mm"],
        ),
        "unequal_flange_i": (
            {
                "radius_of_gyration_y_mm": P,
                "gross_area_mm2": P,
                "flange_centroid_spacing_mm": P,
                "compression_flange_minor_inertia_mm4": P,
                "section_minor_inertia_mm4": P,
                "effective_section_modulus_ex_mm3": P,
            },
            [
                "radius_of_gyration_y_mm",
                "gross_area_mm2",
                "flange_centroid_spacing_mm",
                "compression_flange_minor_inertia_mm4",
                "section_minor_inertia_mm4",
                "effective_section_modulus_ex_mm3",
            ],
        ),
        "rhs_or_shs": (
            {
                "radius_of_gyration_y_mm": P,
                "flange_width_mm": P,
                "web_depth_mm": P,
            },
            ["radius_of_gyration_y_mm", "flange_width_mm", "web_depth_mm"],
        ),
        "angle": (
            {
                "thickness_mm": P,
                "greater_leg_width_b1_mm": P,
                "lesser_leg_width_b2_mm": P,
            },
            ["thickness_mm", "greater_leg_width_b1_mm", "lesser_leg_width_b2_mm"],
        ),
    }
    beta_bases = {
        "conservative_minus_one": ({}, []),
        "transverse_loads": ({}, []),
        "end_moments": (
            {
                "end_moment_1_magnitude_knm": N,
                "end_moment_2_magnitude_knm": N,
                "curvature": {"enum": ["single", "reverse"]},
            },
            [
                "end_moment_1_magnitude_knm",
                "end_moment_2_magnitude_knm",
                "curvature",
            ],
        ),
    }
    variants = []
    for section, (geometry, geometry_required) in sections.items():
        for beta_basis, (beta_properties, beta_required) in beta_bases.items():
            properties = {
                "operation": {"const": "full_lateral_restraint_limit"},
                "section_type": {"const": section},
                "beta_m_basis": {"const": beta_basis},
                **common,
                **geometry,
                **beta_properties,
            }
            required = [
                "operation",
                "section_type",
                "beta_m_basis",
                *common,
                *geometry_required,
                *beta_required,
            ]
            variants.append(object_schema(properties, required))
    return {"oneOf": variants}


def _critical_flange_schema():
    common = {"segment_end_condition": {"const": "one_end_unrestrained"}}
    return {
        "oneOf": [
            object_schema(
                {
                    "operation": {"const": "critical_flange"},
                    "segment_end_condition": {"const": "both_ends_restrained"},
                    "compression_flange_position": {"enum": ["top", "bottom"]},
                }
            ),
            object_schema(
                {
                    "operation": {"const": "critical_flange"},
                    **common,
                    "dominant_load": {"const": "gravity"},
                }
            ),
            object_schema(
                {
                    "operation": {"const": "critical_flange"},
                    **common,
                    "dominant_load": {"const": "wind"},
                    "wind_case": {
                        "enum": [
                            "external_pressure",
                            "internal_suction",
                            "internal_pressure",
                            "external_suction",
                        ]
                    },
                    "exterior_flange_position": {"enum": ["top", "bottom"]},
                }
            ),
        ]
    }


def _unequal_flange_bending_schema():
    common = {
        "section_capacity_knm": P,
        "iy_mm4": P,
        "torsion_constant_mm4": P,
        "warping_constant_mm6": P,
        "effective_length_mm": P,
        "moment_factor": {"type": "number", "exclusiveMinimum": 0, "maximum": 2.5},
        "moment_factor_verified": VERIFIED,
        "both_ends_restrained_verified": VERIFIED,
        "action_knm": N,
        "section_properties_verified": VERIFIED,
        "constant_cross_section_verified": VERIFIED,
    }
    methods = {
        "compression_flange_inertia": {
            "flange_centroid_spacing_mm": P,
            "compression_flange_minor_inertia_mm4": P,
        },
        "section_integral": {
            "beta_x_mm": S,
            "beta_x_integral_verified": VERIFIED,
        },
    }
    variants = []
    for method, properties in methods.items():
        variant_properties = {
            "operation": {"const": "unequal_flange_bending"},
            "beta_x_method": {"const": method},
            **common,
            **properties,
        }
        variants.append(object_schema(variant_properties))
    return {"oneOf": variants}


def _moment_modification_factor_schema():
    return _schema(
        "moment_modification_factor",
        {
            "maximum_design_moment_knm": P,
            "quarter_point_moment_2_knm": N,
            "midpoint_moment_3_knm": N,
            "quarter_point_moment_4_knm": N,
            "moment_diagram_verified": VERIFIED,
            "both_ends_restrained_verified": VERIFIED,
        },
    )


def _table_5_6_1_moment_factor_schema():
    variants = []
    common = {
        "table_5_6_1_diagram_verified": VERIFIED,
        "both_ends_restrained_verified": VERIFIED,
    }
    beta = {"type": "number", "minimum": 0, "maximum": 1}
    twice_a_over_length = {"type": "number", "minimum": 0, "maximum": 1}

    def add(load_case, properties):
        variants.append(
            object_schema(
                {
                    "operation": {"const": "table_5_6_1_moment_factor"},
                    "load_case": {"const": load_case},
                    **common,
                    **properties,
                }
            )
        )

    add("end_moments", {"beta_m": {"type": "number", "minimum": -1, "maximum": 1}})
    add("two_symmetric_point_loads", {"twice_a_over_length": twice_a_over_length})
    add("single_point_load", {"twice_a_over_length": twice_a_over_length})
    add("midspan_point_load_with_one_end_moment", {"beta_m": beta})
    add("midspan_point_load_with_equal_end_moments", {"beta_m": beta})
    add("uniform_load_with_one_end_moment", {"beta_m": beta})
    add("uniform_load_with_equal_end_moments", {"beta_m": beta})
    for load_case in ("uniform_moment", "point_load", "uniform_load"):
        add(load_case, {})
    return {"oneOf": variants}


def _angle_eccentricity_schema():
    common = {
        "arrangement": {"enum": ["same_side", "opposite_sides"]},
        "compression_centroid_offset_mm": N,
        "tension_centroid_offset_mm": N,
        "leg_thickness_mm": P,
        "axial_action_kn": N,
    }
    operation = {"operation": {"const": "angle_eccentricity"}}
    rational_moment = {"rational_analysis_moment_knm": N}
    return {
        "oneOf": [
            object_schema(
                {
                    **operation,
                    **common,
                    "moment_method": {"const": "rational_analysis"},
                    **rational_moment,
                }
            ),
            object_schema(
                {
                    **operation,
                    **common,
                    "moment_method": {"const": "minimum_eccentricity"},
                }
            ),
            object_schema(
                {
                    **operation,
                    **common,
                    "moment_method": {"const": "conservative_max"},
                    **rational_moment,
                }
            ),
            # Preserve the existing input shape and conservative default.
            object_schema({**operation, **common, **rational_moment}),
        ]
    }


def _angle_section_bending_schema():
    return _schema(
        "angle_section_bending_capacity",
        {
            "section_capacity_knm": P,
            "iy_mm4": P,
            "torsion_constant_mm4": P,
            "effective_length_mm": P,
            "moment_factor": {"type": "number", "exclusiveMinimum": 0, "maximum": 2.5},
            "moment_factor_verified": VERIFIED,
            "section_properties_verified": VERIFIED,
            "angle_section_verified": VERIFIED,
            "constant_cross_section_verified": VERIFIED,
            "segment_without_full_lateral_restraint_verified": VERIFIED,
            "both_ends_restrained_verified": VERIFIED,
        },
    )


def _angle_compression_capacity_schema():
    return _schema(
        "angle_compression_capacity",
        {
            "gross_area_mm2": P,
            "net_area_mm2": P,
            "effective_area_mm2": P,
            "yield_strength_mpa": FY,
            "member_length_mm": P,
            "radius_about_loaded_leg_h_axis_mm": P,
            "section_properties_verified": VERIFIED,
            "figure_8_4_6_connection_and_loading_verified": VERIFIED,
            "loaded_leg_h_axis_orientation_verified": VERIFIED,
        },
    )


def _angle_bending_capacity_schema():
    common = {
        "member_length_mm": P,
        "angle_thickness_mm": P,
        "angle_leg_a_width_mm": P,
        "angle_leg_b_width_mm": P,
        "yield_strength_mpa": FY,
        "beta_m": BETA,
        "moment_gradient_factor_verified": VERIFIED,
        "section_capacity_knm": P,
        "section_properties_verified": VERIFIED,
        "figure_8_4_6_connection_and_loading_verified": VERIFIED,
        "without_full_lateral_support_verified": VERIFIED,
    }
    base = {"operation": {"const": "angle_bending_capacity"}, **common}
    with_moment_factor = {
        **base,
        "moment_factor": {"type": "number", "exclusiveMinimum": 0, "maximum": 2.5},
        "moment_factor_verified": VERIFIED,
    }
    return {"oneOf": [object_schema(base), object_schema(with_moment_factor)]}


def _varying_section_bending_schema():
    common = {
        "operation": {"const": "varying_section_bending"},
        "section_capacity_knm": P,
        "reference_buckling_moment_knm": P,
        "reference_buckling_moment_verified": VERIFIED,
        "moment_factor": {"type": "number", "exclusiveMinimum": 0, "maximum": 2.5},
        "moment_factor_verified": VERIFIED,
        "both_ends_restrained_verified": VERIFIED,
        "action_knm": N,
    }
    variants = [
        object_schema(
            {
                **common,
                "design_method": {"const": "minimum_section"},
                "minimum_section_values_verified": VERIFIED,
            }
        )
    ]
    critical_common = {
        **common,
        "design_method": {"const": "critical_section_reduced_reference"},
        "critical_section_values_verified": VERIFIED,
        "segment_length_mm": P,
        "minimum_flange_area_mm2": P,
        "critical_flange_area_mm2": P,
        "minimum_depth_mm": P,
        "critical_depth_mm": P,
    }
    variants.extend(
        [
            object_schema(
                {
                    **critical_common,
                    "variation_type": {"const": "stepped"},
                    "reduced_length_mm": P,
                }
            ),
            object_schema(
                {
                    **critical_common,
                    "variation_type": {"const": "tapered"},
                }
            ),
        ]
    )
    return {"oneOf": variants}


BOOL = {"type": "boolean"}
VERIFIED = {"const": True}
BETA = {"type": "number", "minimum": -1, "maximum": 1}
SCHEMAS = {
    "closed_section_torsion_constant": _schema(
        "closed_section_torsion_constant",
        {
            "enclosed_median_line_area_mm2": P,
            "wall_segments": {
                "type": "array",
                "minItems": 3,
                "maxItems": 1000,
                "items": object_schema(
                    {
                        "median_line_length_mm": P,
                        "thickness_mm": P,
                    }
                ),
            },
            "single_cell_thin_walled_closed_section_verified": VERIFIED,
            "median_line_geometry_verified": VERIFIED,
        },
    ),
    "continuous_lateral_restraints": _schema(
        "continuous_lateral_restraints",
        {
            "both_ends_restrained_verified": VERIFIED,
            "continuous_restraints_at_critical_flange_verified": VERIFIED,
            "continuous_restraints_satisfy_5_4_3_1_verified": VERIFIED,
        },
    ),
    "restraint_classification": _schema(
        "restraint_classification",
        {
            "critical_flange_lateral_deflection_prevented_verified": BOOL,
            "other_cross_section_point_lateral_deflection_prevented_verified": BOOL,
            "twist_rotation_effectively_prevented_verified": BOOL,
            "twist_rotation_partially_prevented_verified": BOOL,
            "critical_flange_out_of_plane_rotation_significantly_restrained_verified": BOOL,
        },
    ),
    "lateral_rotation_restraint": {
        "oneOf": [
            _schema(
                "lateral_rotation_restraint",
                {
                    "method": {"const": "comparable_stiffness"},
                    "cross_section_restraint_classification": {
                        "enum": [
                            "fully_restrained",
                            "partially_restrained",
                            "rotationally_restrained",
                        ]
                    },
                    "cross_section_restraint_classification_verified": BOOL,
                    "restraint_flexural_stiffness_comparable_to_member_verified": BOOL,
                    "stiffness_evidence_reference": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 128,
                    },
                },
            ),
            _schema(
                "lateral_rotation_restraint",
                {
                    "method": {"const": "adjacent_continuous_segment"},
                    "segment_full_lateral_restraint_verified": BOOL,
                    "adjacent_segment_laterally_continuous_verified": BOOL,
                    "restraint_evidence_reference": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 128,
                    },
                },
            ),
            _schema(
                "lateral_rotation_restraint",
                {
                    "method": {"const": "buckling_analysis"},
                    "member_resistance_determined_by_buckling_analysis_verified": BOOL,
                    "buckling_analysis_reference": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 128,
                    },
                },
            ),
        ]
    },
    "full_lateral_restraint_limit": _full_lateral_restraint_schema(),
    "intermediate_lateral_restraints": _schema(
        "intermediate_lateral_restraints",
        {
            "both_ends_restrained_verified": VERIFIED,
            "intermediate_restraints_at_critical_flange_verified": VERIFIED,
            "intermediate_restraints_satisfy_5_4_3_1_verified": VERIFIED,
            "subsegment_checks": {
                "type": "array",
                "items": _full_lateral_restraint_schema(),
                "minItems": 1,
                "maxItems": 1000,
            },
        },
    ),
    "critical_section": _schema(
        "critical_section",
        {
            "sections": {
                "type": "array",
                "items": object_schema(
                    {
                        "section_id": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 128,
                        },
                        "design_moment_knm": N,
                        "section_moment_capacity_knm": P,
                    }
                ),
                "minItems": 1,
                "maxItems": 1000,
            },
        },
    ),
    "critical_flange": _critical_flange_schema(),
    "moment_modification_factor": _moment_modification_factor_schema(),
    "table_5_6_1_moment_factor": _table_5_6_1_moment_factor_schema(),
    "unequal_flange_bending": _unequal_flange_bending_schema(),
    "varying_section_bending": _varying_section_bending_schema(),
    "varying_compression": _schema(
        "varying_compression",
        {
            "minimum_section_capacity_kn": P,
            "elastic_buckling_load_kn": P,
            "section_constant": {"enum": [-1, -0.5, 0, 0.5, 1]},
            "action_kn": N,
            "flexural_mode_verified": VERIFIED,
        },
    ),
    "torsional_flexural_compression": _schema(
        "torsional_flexural_compression",
        {
            "member_section_form": {
                "enum": [
                    "fabricated_monosymmetric",
                    "fabricated_nonsymmetric",
                    "hot_rolled_channel",
                    "unlipped_angle",
                    "tee",
                    "cruciform",
                ]
            },
            "bracing_axis": {"enum": ["major_principal", "minor_principal"]},
            "section_and_axis_applicability_verified": VERIFIED,
            "as_nzs_4600_nominal_member_capacity_kn": P,
            "as_nzs_4600_calculation_verified": VERIFIED,
            "as_nzs_4600_calculation_reference": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2000,
            },
            "action_kn": N,
        },
    ),
    "buckling_analysis_bending": _schema(
        "buckling_analysis_bending",
        {
            "section_capacity_knm": P,
            "elastic_buckling_moment_knm": P,
            "moment_factor": {"type": "number", "exclusiveMinimum": 0, "maximum": 2.5},
            "end_configuration": {"enum": ["both_restrained", "one_unrestrained"]},
            "restraint_and_load_model_verified": VERIFIED,
            "action_knm": N,
        },
    ),
    "one_unrestrained_table_bending": _schema(
        "one_unrestrained_table_bending",
        {
            "section_capacity_knm": P,
            "reference_buckling_moment_knm": P,
            "moment_distribution": {"enum": ["uniform_end_moment", "tip_force", "uniform_load"]},
            "action_knm": N,
            "one_end_restraint_and_continuity_verified": VERIFIED,
            "reference_buckling_moment_verified": VERIFIED,
        },
    ),
    "lateral_buckling_effective_length": _schema(
        "lateral_buckling_effective_length",
        {
            "segment_length_mm": P,
            "clear_flange_depth_mm": P,
            "critical_flange_thickness_mm": P,
            "web_thickness_mm": P,
            "number_of_webs": {"type": "integer", "minimum": 1, "maximum": 100},
            "restraint_arrangement": {"enum": ["FF", "FL", "LL", "FU", "FP", "PL", "PU", "PP"]},
            "gravity_load_position": {"enum": ["within_segment", "at_segment_end"]},
            "load_height_position": {"enum": ["shear_centre", "top_flange"]},
            "effective_rotation_restraint_count": {"type": "integer", "enum": [0, 1, 2]},
            "effective_rotation_restraints_verified": BOOL,
        },
    ),
    "nonprincipal_bending": _schema(
        "nonprincipal_bending",
        {
            "section_axial_capacity_kn": P,
            "section_moment_x_knm": P,
            "section_moment_y_knm": P,
            "reduced_member_moment_x_knm": P,
            "reduced_member_moment_y_knm": P,
            "axial_action_kn": N,
            "moment_x_knm": N,
            "moment_y_knm": N,
            "deflections_constrained": BOOL,
            "rational_analysis_verified": VERIFIED,
        },
    ),
    "plastic_in_plane": _schema(
        "plastic_in_plane",
        {
            "compact_doubly_symmetric_i_verified": VERIFIED,
            "section_axial_capacity_kn": P,
            "section_moment_x_knm": P,
            "section_moment_y_knm": P,
            "axial_action_kn": N,
            "axial_mode": {"enum": ["compression", "tension"]},
            "moment_x_knm": N,
            "moment_y_knm": N,
            "elastic_buckling_load_actual_length_kn": P,
            "beta_m": BETA,
            "web_clear_depth_mm": P,
            "web_thickness_mm": P,
            "yield_mpa": FY,
        },
    ),
    "built_up_compression": _schema(
        "built_up_compression",
        {
            "construction": {"enum": ["laced", "battened", "back_to_back"]},
            "section_capacity_kn": P,
            "member_capacity_kn": P,
            "modified_member_slenderness": P,
            "axial_action_kn": N,
            "integral_slenderness_perpendicular": P,
            "integral_slenderness_parallel": P,
            "component_slenderness": P,
            "number_of_bays": {"type": "integer", "minimum": 1, "maximum": 1000000},
            "similar_symmetric_components_verified": VERIFIED,
            "interconnection_design": object_schema(
                {"design_capacity_kn": N, "capacity_verified": VERIFIED}
            ),
        },
        optional=("interconnection_design",),
    ),
    "lacing": _schema(
        "lacing",
        {
            "mode": {"enum": ["single", "double_connected"]},
            "member_mode": {"enum": ["compression", "tension"]},
            "angle_degrees": {"type": "number", "minimum": 0, "maximum": 90},
            "inner_connection_distance_mm": P,
            "radius_mm": P,
            "tie_type": {"enum": ["end", "intermediate"]},
            "component_connection_centroid_distance_mm": P,
            "tie_width_mm": P,
            "tie_thickness_mm": P,
            "tie_inner_connection_distance_mm": P,
            "tie_edge_stiffened": BOOL,
            "tie_edge_stiffener_slenderness": N,
        },
    ),
    "batten": _schema(
        "batten",
        {
            "type": {"enum": ["end", "intermediate"]},
            "member_mode": {"enum": ["compression", "tension"]},
            "centroid_distance_mm": P,
            "narrower_component_width_mm": P,
            "radius_mm": P,
            "width_mm": P,
            "thickness_mm": P,
            "inner_connection_distance_mm": P,
            "edge_stiffened": BOOL,
            "edge_stiffener_slenderness": N,
            "transverse_shear_kn": N,
            "longitudinal_spacing_mm": P,
            "connection_centroid_distance_mm": P,
            "parallel_planes": {"type": "integer", "minimum": 1, "maximum": 1000000},
            "effective_end_width_mm": P,
            "connection_type": {"enum": ["bolted", "welded"]},
            "bolts_per_component_connection": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000000,
            },
        },
        optional=("connection_type", "bolts_per_component_connection"),
    ),
    "tension_connection_plane_distribution": _schema(
        "tension_connection_plane_distribution",
        {
            "connection_type": {"enum": ["lacing", "batten"]},
            "parallel_connection_planes": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000000,
            },
            "total_design_force_kn": S,
            "total_design_moment_knm": S,
        },
        optional=("total_design_moment_knm",),
    ),
    "tension_built_up_connection_layout": _schema(
        "tension_built_up_connection_layout",
        {
            "connection_arrangement": {"enum": ["separated", "in_contact"]},
            "two_eligible_components_verified": VERIFIED,
            "discontinuous_back_to_back_connection_verified": VERIFIED,
            "separated_within_end_gusset_spacing_verified": VERIFIED,
            "member_length_mm": P,
            "bay_lengths_mm": {
                "type": "array",
                "minItems": 3,
                "maxItems": 1000,
                "items": P,
            },
            "approximately_equal_bays_verified": VERIFIED,
            "end_connection_method": {"enum": ["fasteners", "welds"]},
            "fasteners_per_connection_line_at_each_end": {
                "type": "integer",
                "minimum": 2,
                "maximum": 1000000,
            },
            "equivalent_end_welds_verified": VERIFIED,
        },
        optional=(
            "separated_within_end_gusset_spacing_verified",
            "fasteners_per_connection_line_at_each_end",
            "equivalent_end_welds_verified",
        ),
    ),
    "tension_built_up_interconnection": _schema(
        "tension_built_up_interconnection",
        {
            "connection_arrangement": {"enum": ["separated", "in_contact"]},
            "parallel_connection_planes": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
            },
            "connection_plane_count_verified": VERIFIED,
            "all_interconnections_assessed_verified": VERIFIED,
            "interconnections": {
                "type": "array",
                "minItems": 1,
                "maxItems": 1000,
                "items": object_schema(
                    {
                        "local_design_transverse_shear_kn": N,
                        "transverse_shear_verified": VERIFIED,
                        "component_length_between_connections_mm": P,
                        "minimum_radius_of_gyration_mm": P,
                        "geometry_verified": VERIFIED,
                        "design_capacity_by_plane_kn": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 100,
                            "items": P,
                        },
                        "capacity_verified": VERIFIED,
                    }
                ),
            },
        },
    ),
    "tension_component_slenderness": _schema(
        "tension_component_slenderness",
        {
            "arrangement": {"enum": ["separated_back_to_back", "laced", "battened"]},
            "intervals_and_radii_verified": VERIFIED,
            "component_intervals": {
                "type": "array",
                "minItems": 1,
                "maxItems": 10000,
                "items": object_schema(
                    {
                        "unrestrained_length_mm": P,
                        "minimum_radius_of_gyration_mm": P,
                    }
                ),
            },
        },
    ),
    "pin_tension_member": _schema(
        "pin_tension_member",
        {
            "design_tension_kn": P,
            "yield_strength_mpa": FY,
            "ultimate_strength_mpa": P,
            "gross_area_mm2": P,
            "member_net_area_mm2": P,
            "tension_distribution_factor": {"enum": [0.75, 0.85, 0.9, 1.0]},
            "member_net_area_assessed_verified": VERIFIED,
            "tension_distribution_factor_assessed_verified": VERIFIED,
            "thickness_mm": P,
            "hole_to_edge_distance_mm": P,
            "internal_nut_clamped_ply": BOOL,
            "net_area_beyond_hole_planes_mm2": {
                "type": "array",
                "minItems": 1,
                "maxItems": 10000,
                "items": P,
            },
            "net_area_perpendicular_mm2": P,
            "all_beyond_hole_planes_assessed_verified": VERIFIED,
            "pin_plates_distribute_load_without_eccentricity_verified": VERIFIED,
        },
    ),
    "restraint_action": _schema(
        "restraint_action",
        {
            "type": {"enum": ["lateral_flange", "twist", "compression"]},
            "connected_force_kn": N,
            "beyond_forces_kn": {"type": "array", "items": N, "maxItems": 6},
            "analysis_restraint_force_kn": N,
        },
    ),
    "separator_diaphragm": _schema(
        "separator_diaphragm",
        {
            "device_type": {"enum": ["separator", "diaphragm"]},
            "member_count": {"type": "integer", "minimum": 2, "maximum": 1000000},
            "device_count": {"type": "integer", "minimum": 1, "maximum": 1000000},
            "maximum_compression_flange_force_kn": N,
            "external_vertical_force_transfer_required": BOOL,
            "side_by_side_i_sections_or_channels_verified": VERIFIED,
        },
    ),
    "angle_section_bending_capacity": _angle_section_bending_schema(),
    "angle_compression_capacity": _angle_compression_capacity_schema(),
    "angle_bending_capacity": _angle_bending_capacity_schema(),
    "angle_combined_interaction": _schema(
        "angle_combined_interaction",
        {
            "design_compression_kn": P,
            "design_moment_about_h_knm": N,
            "nominal_member_compression_nch_kn": P,
            "nominal_member_bending_mbx_knm": P,
            "angle_between_x_and_h_deg": {
                "type": "number",
                "minimum": 0,
                "exclusiveMaximum": 90,
            },
            "clause_8_3_interaction_satisfied": BOOL,
            "single_angle_web_compression_member_in_truss_verified": VERIFIED,
            "end_connection_at_least_two_bolts_or_welded_verified": VERIFIED,
            "loaded_through_one_leg_figure_8_4_6_verified": VERIFIED,
            "angle_axis_orientation_verified": VERIFIED,
            "nominal_nch_mbx_calculations_verified": VERIFIED,
        },
    ),
    "angle_eccentricity": _angle_eccentricity_schema(),
}
INPUT_SCHEMA = {"oneOf": list(SCHEMAS.values())}
OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "standard",
        "operation",
        "clauses",
        "values",
        "checks",
        "checked_conditions_satisfied",
        "full_standard_compliance",
        "limitations",
    ],
    "properties": {"full_standard_compliance": {"const": False}},
}


def _limit(clause, value, limit):
    return {
        "clause": clause,
        "value": value,
        "limit": limit,
        "utilisation": value / limit if limit > 0 else None,
        "satisfied": value <= limit,
    }


def _minimum(clause, actual, minimum):
    return {
        "clause": clause,
        "actual": actual,
        "required_minimum": minimum,
        "satisfied": actual >= minimum,
    }


def _reduced_check(clause, moment, nominal):
    if nominal <= 0:
        return {
            "clause": clause,
            "design_capacity": 0,
            "action": moment,
            "utilisation": None,
            "satisfied": moment == 0,
        }
    return capacity_check(clause, nominal, moment)


def run_advanced_members(inputs):
    d = validate(inputs, INPUT_SCHEMA)
    op = d["operation"]
    if op == "restraint_classification":
        critical_lateral = d["critical_flange_lateral_deflection_prevented_verified"]
        other_point_lateral = d["other_cross_section_point_lateral_deflection_prevented_verified"]
        effective_twist = d["twist_rotation_effectively_prevented_verified"]
        partial_twist = d["twist_rotation_partially_prevented_verified"]
        full_a = critical_lateral and (effective_twist or partial_twist)
        full_b = other_point_lateral and effective_twist
        partial = other_point_lateral and partial_twist
        rotational = d["critical_flange_out_of_plane_rotation_significantly_restrained_verified"]
        clauses = ["5.4.2.1", "5.4.2.2", "5.4.2.3", "5.4.2.4"]
        values = {
            "full_lateral_restraint_criterion_a_satisfied": full_a,
            "full_lateral_restraint_criterion_b_satisfied": full_b,
            "full_lateral_restraint_qualifies": full_a or full_b,
            "partial_lateral_restraint_qualifies": partial,
            "rotational_restraint_qualifies": rotational,
            "lateral_restraint_qualifies": critical_lateral,
        }
        checks = [
            {"clause": "5.4.2.1(a)", "satisfied": full_a},
            {"clause": "5.4.2.1(b)", "satisfied": full_b},
            {"clause": "5.4.2.2", "satisfied": partial},
            {"clause": "5.4.2.3", "satisfied": rotational},
            {"clause": "5.4.2.4", "satisfied": critical_lateral},
        ]
        return result(
            op,
            clauses,
            values,
            checks,
            [
                "Verify the cross-section point identified as critical flange and establish "
                "effective lateral, twist and out-of-plane rotational restraint from the "
                "actual support and connection details.",
                "The classification outcomes can overlap. This operation records supplied "
                "evidence; it does not calculate restraint stiffness or force, nor establish "
                "segment-level full lateral restraint under 5.3.2.",
            ],
        )
    if op == "lateral_rotation_restraint":
        method = d["method"]
        values = {"method": method}
        if method == "comparable_stiffness":
            classification_verified = d["cross_section_restraint_classification_verified"]
            stiffness_verified = d["restraint_flexural_stiffness_comparable_to_member_verified"]
            classification = d["cross_section_restraint_classification"]
            classification_clause = {
                "fully_restrained": "5.4.2.1",
                "partially_restrained": "5.4.2.2",
                "rotationally_restrained": "5.4.2.3",
            }[classification]
            effective = classification_verified and stiffness_verified
            values.update(
                {
                    "cross_section_restraint_classification": classification,
                    "stiffness_evidence_reference": d["stiffness_evidence_reference"],
                }
            )
            checks = [
                {"clause": classification_clause, "satisfied": classification_verified},
                {
                    "clause": "5.4.3.4 comparable flexural stiffness",
                    "satisfied": stiffness_verified,
                },
            ]
        elif method == "adjacent_continuous_segment":
            full_restraint = d["segment_full_lateral_restraint_verified"]
            continuity = d["adjacent_segment_laterally_continuous_verified"]
            effective = full_restraint and continuity
            values.update(
                {
                    "segment_full_lateral_restraint_verified": full_restraint,
                    "adjacent_segment_laterally_continuous_verified": continuity,
                    "restraint_evidence_reference": d["restraint_evidence_reference"],
                }
            )
            checks = [
                {"clause": "5.3.2 full lateral restraint", "satisfied": full_restraint},
                {"clause": "5.4.3.4 adjacent-segment continuity", "satisfied": continuity},
            ]
        else:
            analysis_verified = d["member_resistance_determined_by_buckling_analysis_verified"]
            effective = analysis_verified
            values.update({"buckling_analysis_reference": d["buckling_analysis_reference"]})
            checks = [
                {
                    "clause": "5.6.4 member resistance by buckling analysis",
                    "satisfied": analysis_verified,
                },
            ]
        values["lateral_rotation_restraint_effective"] = effective
        return result(
            op,
            ["5.4.3.4"],
            values,
            checks,
            [
                "Verify a Clause 5.4.2.1, 5.4.2.2 or 5.4.2.3 cross-section classification "
                "and comparable flexural stiffness in the plane of rotation; or verify full "
                "lateral restraint and continuity for the adjacent-segment route.",
                "The comparable-stiffness and adjacent-segment routes record engineering "
                "evidence; the operation does not derive stiffness or restraint capacity.",
                "A segment without full lateral restraint provides no rotational-restraint "
                "credit unless member resistance is determined by buckling analysis under "
                "Clause 5.6.4. The analysis remains externally performed and verified.",
            ],
        )
    if op == "closed_section_torsion_constant":
        enclosed_area = d["enclosed_median_line_area_mm2"]
        wall_ratio_sum = sum(
            segment["median_line_length_mm"] / segment["thickness_mm"]
            for segment in d["wall_segments"]
        )
        torsion_constant = 4 * enclosed_area**2 / wall_ratio_sum
        if not isfinite(wall_ratio_sum) or wall_ratio_sum <= 0:
            raise ValueError(
                "Appendix H.4 wall length-to-thickness sum must be positive and finite."
            )
        if not isfinite(torsion_constant) or torsion_constant <= 0:
            raise ValueError("Appendix H.4 torsion constant must be positive and finite.")
        return result(
            op,
            ["Appendix H.4 (Amd 1:2021)"],
            {
                "enclosed_median_line_area_mm2": enclosed_area,
                "wall_length_to_thickness_sum": wall_ratio_sum,
                "torsion_constant_j_mm4": torsion_constant,
            },
            [],
            [
                "Applies the AS 4100:2020 Appendix H.4 formula corrected by Amendment No. 1:2021 "
                "to a thin-walled, single-cell closed section.",
                "Supply the enclosed median-line area and each wall length measured along the "
                "median line, with its matching wall thickness; verify the closed-cell geometry.",
                "Multi-cell and open sections are outside this operation. It calculates J only; "
                "warping constant Iw and other section properties are separate.",
            ],
        )
    if op == "continuous_lateral_restraints":
        return result(
            op,
            ["5.3.2.1", "5.3.2.2"],
            {
                "restraint_route": "continuous_lateral_restraints",
                "full_lateral_restraint_qualifies": True,
            },
            [
                {"clause": "5.3.2.2(a)", "satisfied": True},
                {"clause": "5.3.2.2(b)", "satisfied": True},
                {"clause": "5.4.3.1", "satisfied": True},
            ],
            [
                "Both ends must be fully or partially restrained under Clauses 5.4.2.1, "
                "5.4.2.2, 5.4.3.1 and 5.4.3.2.",
                "Continuous restraints must act at the critical flange and their "
                "effectiveness must be established under 5.4.3.1.",
                "This route records verified conditions; it does not design or independently "
                "validate the restraint system.",
            ],
        )
    if op == "intermediate_lateral_restraints":
        subsegments = []
        checks = [
            {"clause": "5.3.2.3(a)", "satisfied": True},
            {"clause": "5.3.2.3(c)", "satisfied": True},
            {"clause": "5.4.3.1", "satisfied": True},
        ]
        for index, subsegment in enumerate(d["subsegment_checks"], start=1):
            checked = run_advanced_members(subsegment)
            values = checked["values"]
            satisfied = values["full_lateral_restraint_qualifies"]
            checks.append(
                {
                    "clause": "5.3.2.3(b)",
                    "subsegment_number": index,
                    "actual_slenderness": values["segment_slenderness"],
                    "permitted_slenderness": values["permitted_slenderness"],
                    "satisfied": satisfied,
                }
            )
            subsegments.append(
                {
                    "subsegment_number": index,
                    "section_type": values["section_type"],
                    "beta_m": values["beta_m"],
                    "actual_slenderness": values["segment_slenderness"],
                    "permitted_slenderness": values["permitted_slenderness"],
                    "satisfied": satisfied,
                }
            )
        return result(
            op,
            ["5.3.2.1", "5.3.2.3", "5.3.2.4"],
            {
                "restraint_route": "intermediate_lateral_restraints",
                "subsegment_count": len(subsegments),
                "subsegments": subsegments,
                "full_lateral_restraint_qualifies": all(check["satisfied"] for check in checks),
            },
            checks,
            [
                "Both segment ends must be fully or partially restrained under Clauses "
                "5.4.2.1, 5.4.2.2, 5.4.3.1 and 5.4.3.2.",
                "Every subsegment is checked against Clause 5.3.2.4 using its own "
                "verified section properties and beta_m basis.",
                "Intermediate restraints must act at the critical flange and be effective "
                "under 5.4.3.1; their strength, stiffness and force path remain assessed.",
            ],
        )
    if op == "critical_flange":
        if d["segment_end_condition"] == "both_ends_restrained":
            position = d["compression_flange_position"]
            location = "compression"
            clauses = ["5.5.1", "5.5.2"]
            basis = "compression flange for a segment restrained at both ends"
        elif d["dominant_load"] == "gravity":
            position = "top"
            location = "top"
            clauses = ["5.5.1", "5.5.3"]
            basis = "top flange for a one-end-unrestrained segment with dominant gravity load"
        else:
            exterior_controls = d["wind_case"] in {
                "external_pressure",
                "internal_suction",
            }
            location = "exterior" if exterior_controls else "interior"
            exterior_position = d["exterior_flange_position"]
            position = (
                exterior_position
                if exterior_controls
                else ("bottom" if exterior_position == "top" else "top")
            )
            clauses = ["5.5.1", "5.5.3"]
            basis = (
                "exterior flange for external pressure or internal suction"
                if exterior_controls
                else "interior flange for internal pressure or external suction"
            )
        return result(
            op,
            clauses,
            {
                "critical_flange_position": position,
                "critical_flange_location": location,
                "selection_basis": basis,
                "wind_case": d.get("wind_case"),
            },
            [],
            [
                "Segment end conditions, gravity/wind load dominance, wind pressure/suction "
                "case and exterior-flange orientation must be assessed for the actual member.",
                "This selects the prescribed critical flange under Clauses 5.5.2–5.5.3; "
                "it does not determine restraint effectiveness or calculate buckling capacity.",
                "Clause 5.5.1 permits elastic buckling analysis for other configurations; "
                "those cases require a separately verified analysis.",
            ],
        )
    if op == "critical_section":
        candidates = d["sections"]
        identifiers = [candidate["section_id"] for candidate in candidates]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Section identifiers must be unique.")
        section_ratios = [
            {
                "section_id": candidate["section_id"],
                "design_moment_knm": candidate["design_moment_knm"],
                "section_moment_capacity_knm": candidate["section_moment_capacity_knm"],
                "moment_to_capacity_ratio": (
                    candidate["design_moment_knm"] / candidate["section_moment_capacity_knm"]
                ),
            }
            for candidate in candidates
        ]
        controlling_ratio = max(
            candidate["moment_to_capacity_ratio"] for candidate in section_ratios
        )
        controlling = [
            candidate
            for candidate in section_ratios
            if candidate["moment_to_capacity_ratio"] == controlling_ratio
        ]
        return result(
            op,
            ["5.3.3"],
            {
                "critical_section_id": controlling[0]["section_id"],
                "critical_section_ids": [candidate["section_id"] for candidate in controlling],
                "maximum_moment_to_capacity_ratio": controlling_ratio,
                "section_ratios": section_ratios,
            },
            [],
            [
                "Supply design moments and nominal section moment capacities at all "
                "candidate cross-sections in this segment.",
                "Use nonnegative design-moment magnitudes from the same bending axis and "
                "design action case.",
                "This operation selects the critical section only; it does not calculate "
                "actions, section capacities or member adequacy.",
                "Run separately for each applicable bending axis and design action case.",
            ],
        )
    if op == "full_lateral_restraint_limit":
        beta_basis = d["beta_m_basis"]
        if beta_basis == "conservative_minus_one":
            beta_m = -1.0
        elif beta_basis == "transverse_loads":
            beta_m = -0.8
        else:
            end_moments = sorted(
                [
                    d["end_moment_1_magnitude_knm"],
                    d["end_moment_2_magnitude_knm"],
                ]
            )
            if end_moments[1] == 0:
                raise ValueError("At least one end moment must be non-zero.")
            beta_m = end_moments[0] / end_moments[1]
            if d["curvature"] == "single":
                beta_m = -beta_m

        length = d["segment_length_mm"]
        fy = d["yield_strength_mpa"]
        section = d["section_type"]
        details = {}
        if section in {"equal_flanged_i", "equal_flanged_channel", "unequal_flange_i"}:
            slenderness = length / d["radius_of_gyration_y_mm"]
            coefficient = (
                60 + 40 * beta_m if section == "equal_flanged_channel" else 80 + 50 * beta_m
            )
            geometry_factor = 1.0
            if section == "unequal_flange_i":
                flange_inertia = d["compression_flange_minor_inertia_mm4"]
                section_inertia = d["section_minor_inertia_mm4"]
                if flange_inertia > section_inertia:
                    raise ValueError(
                        "Compression-flange minor inertia must not exceed section minor inertia."
                    )
                rho = flange_inertia / section_inertia
                geometry_factor = sqrt(
                    2
                    * rho
                    * d["gross_area_mm2"]
                    * d["flange_centroid_spacing_mm"]
                    / (2.5 * d["effective_section_modulus_ex_mm3"])
                )
                details["compression_flange_inertia_ratio"] = rho
                details["unequal_flange_geometry_factor"] = geometry_factor
            permitted = coefficient * geometry_factor * sqrt(250 / fy)
        elif section == "rhs_or_shs":
            slenderness = length / d["radius_of_gyration_y_mm"]
            permitted = (
                (1800 + 1500 * beta_m) * d["flange_width_mm"] / d["web_depth_mm"] * (250 / fy)
            )
        else:
            greater_leg = d["greater_leg_width_b1_mm"]
            lesser_leg = d["lesser_leg_width_b2_mm"]
            if lesser_leg > greater_leg:
                raise ValueError("b2 must not exceed b1 for an angle section.")
            slenderness = length / d["thickness_mm"]
            permitted = (210 + 175 * beta_m) * sqrt(lesser_leg / greater_leg) * (250 / fy)
        check = _limit("5.3.2.4", slenderness, permitted)
        return result(
            op,
            ["5.3.2.4"],
            {
                "section_type": section,
                "beta_m_basis": beta_basis,
                "beta_m": beta_m,
                "segment_slenderness": slenderness,
                "permitted_slenderness": permitted,
                "full_lateral_restraint_qualifies": check["satisfied"],
                **details,
            },
            [check],
            [
                "Applies only to a segment restrained at both ends as verified under "
                "Clauses 5.4.2.1, 5.4.2.2, 5.4.3.1 and 5.4.3.2.",
                "Verify section type and properties, including the effective Z_ex under "
                "Clause 5.2 for unequal-flange I-sections.",
                "Use end-moment beta_m only when there are no transverse loads in the "
                "segment; verify the signed curvature classification.",
                "This check establishes only the Clause 5.3.2.4 length criterion. "
                "Restraint stiffness, strength and force transfer remain separate checks.",
            ],
        )
    if op == "varying_compression":
        ns, nom = d["minimum_section_capacity_kn"], d["elastic_buckling_load_kn"]
        ln = 90 * sqrt(ns / nom)
        aa = 2100 * (ln - 13.5) / (ln * ln - 15.3 * ln + 2050)
        lam = max(0, ln + aa * d["section_constant"])
        q, eta = (lam / 90) ** 2, max(0, 0.00326 * (lam - 13.5))
        a = 1 + q + eta
        alpha = min(1, 2 / (a + sqrt(max(0, a * a - 4 * q))))
        nc = alpha * ns
        return result(
            op,
            ["6.3.3", "6.3.4"],
            {
                "modified_slenderness": ln,
                "reduction": alpha,
                "member_capacity_kn": nc,
            },
            [capacity_check("6.3.4", nc, d["action_kn"])],
            [
                "Minimum section capacity must include every cross-section and hole deduction.",
                "Elastic flexural buckling load requires rational analysis of actual "
                "varying section.",
                "Assess both axes separately and select applicable Table 6.3.3(A/B) "
                "section constant.",
            ],
        )
    if op == "torsional_flexural_compression":
        form, axis = d["member_section_form"], d["bracing_axis"]
        if form in {"unlipped_angle", "tee", "cruciform"}:
            raise ValueError(
                "Clause 6.3.3's AS/NZS 4600 flexural-torsional route excludes "
                "unlipped angles, tees and cruciform sections."
            )
        if form == "hot_rolled_channel" and axis == "minor_principal":
            raise ValueError(
                "Clause 6.3.3's AS/NZS 4600 route excludes hot-rolled channels "
                "braced about the minor principal axis."
            )
        reference = d["as_nzs_4600_calculation_reference"].strip()
        if not reference:
            raise ValueError("AS/NZS 4600 calculation reference must not be blank.")
        external_capacity = d["as_nzs_4600_nominal_member_capacity_kn"]
        reduction = 0.85
        nominal_capacity = reduction * external_capacity
        return result(
            op,
            ["6.3.3"],
            {
                "member_section_form": form,
                "bracing_axis": axis,
                "as_nzs_4600_nominal_member_capacity_kn": external_capacity,
                "as_nzs_4600_calculation_reference": reference,
                "as_4100_torsional_flexural_reduction_factor": reduction,
                "nominal_member_capacity_kn": nominal_capacity,
            },
            [capacity_check("6.3.3", nominal_capacity, d["action_kn"])],
            [
                "The caller must establish that the section, bracing axis and restraint "
                "conditions fall within the Clause 6.3.3 flexural-torsional provision.",
                "Supply the unreduced nominal flexural-torsional member capacity calculated "
                "to AS/NZS 4600 for the actual section, restraints and loading. This operation "
                "applies the AS 4100 reduction factor of 0.85 and capacity factor of 0.90.",
                "The AS/NZS 4600 analysis, its reference and applicability evidence are "
                "recorded but not authenticated or recalculated here.",
            ],
        )
    if op == "moment_modification_factor":
        moments = [
            d["quarter_point_moment_2_knm"],
            d["midpoint_moment_3_knm"],
            d["quarter_point_moment_4_knm"],
        ]
        if d["maximum_design_moment_knm"] < max(moments):
            raise ValueError("Maximum design moment must not be below a sampled segment moment.")
        denominator = sqrt(sum(moment**2 for moment in moments))
        if denominator == 0:
            raise ValueError("At least one quarter-point or midpoint moment must be non-zero.")
        uncapped = 1.7 * d["maximum_design_moment_knm"] / denominator
        factor = min(2.5, uncapped)
        return result(
            op,
            ["5.6.1.1(a)(iii)"],
            {
                "moment_factor": factor,
                "uncapped_moment_factor": uncapped,
                "maximum_moment_factor": 2.5,
                "upper_cap_applied": uncapped > 2.5,
            },
            [],
            [
                "The supplied moments are nonnegative design-moment magnitudes from the "
                "same segment; the maximum moment and quarter-point/midpoint values must "
                "represent the assessed moment diagram.",
                "Both ends of the segment must be fully or partially restrained under "
                "Clause 5.6.1.",
                "Use this equation for the moment-modification-factor option in Clause "
                "5.6.1.1(a). Table 5.6.1 and elastic-buckling alternatives remain separate "
                "assessed paths.",
            ],
        )
    if op == "table_5_6_1_moment_factor":
        load_case = d["load_case"]
        beta = d.get("beta_m")
        ratio = d.get("twice_a_over_length")
        if load_case == "end_moments":
            factor = 1.75 + 1.05 * beta + 0.3 * beta**2 if beta <= 0.6 else 2.5
        elif load_case == "two_symmetric_point_loads":
            factor = 1.0 + 0.35 * (1 - ratio) ** 2
        elif load_case == "single_point_load":
            factor = 1.35 + 0.4 * ratio**2
        elif load_case == "midspan_point_load_with_one_end_moment":
            factor = 1.35 + 0.15 * beta if beta < 0.9 else -1.2 + 3.0 * beta
        elif load_case == "midspan_point_load_with_equal_end_moments":
            factor = 1.35 + 0.36 * beta
        elif load_case == "uniform_load_with_one_end_moment":
            factor = 1.13 + 0.10 * beta if beta <= 0.7 else -1.25 + 3.5 * beta
        elif load_case == "uniform_load_with_equal_end_moments":
            factor = 1.13 + 0.12 * beta if beta <= 0.75 else -2.38 + 4.8 * beta
        elif load_case == "uniform_moment":
            factor = 1.0
        elif load_case == "point_load":
            factor = 1.75
        else:
            factor = 2.5
        values = {"load_case": load_case, "moment_factor": factor}
        if beta is not None:
            values["beta_m"] = beta
        if ratio is not None:
            values["twice_a_over_length"] = ratio
        return result(
            op,
            ["5.6.1", "Table 5.6.1"],
            values,
            [],
            [
                "Select and verify the exact Table 5.6.1 moment-distribution diagram; both "
                "segment ends must be fully or partially restrained.",
                "For the selected diagram, supply beta_m or 2a/l exactly as defined in the "
                "table. This operation returns alpha_m only; establish the reference buckling "
                "moment and complete the member capacity check separately.",
            ],
        )
    if op == "unequal_flange_bending":
        if d["beta_x_method"] == "compression_flange_inertia":
            iy = d["iy_mm4"]
            inertia_ratio = d["compression_flange_minor_inertia_mm4"] / iy
            if inertia_ratio > 1:
                raise ValueError(
                    "Compression-flange minor inertia must not exceed section minor inertia."
                )
            beta_x = 0.8 * d["flange_centroid_spacing_mm"] * (2 * inertia_ratio - 1)
        else:
            beta_x = d["beta_x_mm"]

        iy = d["iy_mm4"]
        length = d["effective_length_mm"]
        a = pi**2 * ELASTIC_MODULUS_MPA * iy / length**2
        stiffness = (
            SHEAR_MODULUS_MPA * d["torsion_constant_mm4"]
            + pi**2 * ELASTIC_MODULUS_MPA * d["warping_constant_mm6"] / length**2
            + (beta_x**2 / 4) * a
        )
        mo = sqrt(a) * (sqrt(stiffness) + (beta_x / 2) * sqrt(a)) / 1e6
        if not isfinite(mo) or mo <= 0:
            raise ValueError(
                "Clause 5.6.1.2 reference buckling moment must be positive and finite."
            )

        ms = d["section_capacity_knm"]
        alpha_m = d["moment_factor"]
        ratio = ms / mo
        alpha_s = 0.6 * (sqrt(ratio**2 + 3) - ratio)
        mb = min(ms, alpha_m * alpha_s * ms)
        return result(
            op,
            ["5.6.1.1(a)", "5.6.1.1(2)", "5.6.1.2"],
            {
                "beta_x_method": d["beta_x_method"],
                "beta_x_mm": beta_x,
                "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
                "shear_modulus_mpa": SHEAR_MODULUS_MPA,
                "reference_buckling_moment_knm": mo,
                "slenderness_reduction": alpha_s,
                "moment_factor": alpha_m,
                "member_capacity_knm": mb,
            },
            [capacity_check("5.6.1.2", mb, d["action_knm"])],
            [
                "Verify full or partial restraint at both ends under Clause 5.6.1.",
                "Use gross-section Ms from Clause 5.2 and effective length including the "
                "applicable Clause 5.6.3 factors.",
                "Verify section properties and compression-flange selection. Clause "
                "5.6.1.2 defines beta_x as positive for the larger flange in compression "
                "and negative for the smaller flange in compression.",
                "The supplied moment factor must be independently selected under Clause "
                "5.6.1.1; the operation does not derive it from the member moment diagram.",
                "The section-integral beta_x route requires independent verification of "
                "the Clause 5.6.1.2 integral and shear-centre coordinate.",
                "The elastic buckling-analysis alternative under Clause 5.6.1.2(b) is "
                "available through the separate buckling-analysis operation.",
            ],
        )
    if op == "varying_section_bending":
        design_method = d["design_method"]
        alpha_st = 1.0
        if design_method == "critical_section_reduced_reference":
            if d["minimum_flange_area_mm2"] > d["critical_flange_area_mm2"]:
                raise ValueError(
                    "Minimum-section flange area must not exceed critical-section area."
                )
            if d["minimum_depth_mm"] > d["critical_depth_mm"]:
                raise ValueError("Minimum-section depth must not exceed critical-section depth.")
            if d["variation_type"] == "stepped":
                if d["reduced_length_mm"] > d["segment_length_mm"]:
                    raise ValueError("Reduced length must not exceed the segment length.")
                r_r = d["reduced_length_mm"] / d["segment_length_mm"]
            else:
                r_r = 0.5
            r_s = (d["minimum_flange_area_mm2"] / d["critical_flange_area_mm2"]) * (
                0.6 + 0.4 * d["minimum_depth_mm"] / d["critical_depth_mm"]
            )
            alpha_st = 1 - 1.2 * r_r * (1 - r_s)
            if not isfinite(alpha_st) or alpha_st <= 0:
                raise ValueError("Section variation reduction factor must be positive and finite.")

        moa = d["reference_buckling_moment_knm"] * alpha_st
        if not isfinite(moa) or moa <= 0:
            raise ValueError("Adjusted reference buckling moment must be positive and finite.")
        ms = d["section_capacity_knm"]
        ratio = ms / moa
        alpha_s = 0.6 * (sqrt(ratio**2 + 3) - ratio)
        alpha_m = d["moment_factor"]
        mb = min(ms, alpha_m * alpha_s * ms)
        if design_method == "minimum_section":
            clauses = ["5.6.1.1(a)", "5.6.1.1(b)(i)", "5.6.1.1(2)"]
        else:
            clauses = ["5.6.1.1(a)", "5.6.1.1(b)(ii)", "5.6.1.1(2)"]
        return result(
            op,
            clauses,
            {
                "design_method": design_method,
                "alpha_st": (
                    alpha_st if design_method == "critical_section_reduced_reference" else None
                ),
                "reference_buckling_moment_knm": d["reference_buckling_moment_knm"],
                "adjusted_reference_buckling_moment_knm": moa,
                "slenderness_reduction": alpha_s,
                "moment_factor": alpha_m,
                "member_capacity_knm": mb,
            },
            [capacity_check("5.6.1.1(b)", mb, d["action_knm"])],
            [
                "Verify full or partial restraint at both ends under Clause 5.6.1.",
                "The supplied nominal section capacity and reference buckling moment must "
                "both use the verified minimum cross-section for method (i), or the "
                "verified critical cross-section for method (ii).",
                "Method (ii) reduces the critical-section reference moment by alpha_st; "
                "the operation calculates alpha_st from the stepped/tapered geometry.",
                "The moment factor must be independently selected under Clause 5.6.1.1. "
                "The buckling-analysis alternative under Clause 5.6.1.1(b)(iii) requires "
                "a separately verified analysis.",
            ],
        )
    if op == "buckling_analysis_bending":
        ms, mob = d["section_capacity_knm"], d["elastic_buckling_moment_knm"]
        am = d["moment_factor"]
        # For 5.6.2(ii), no moment-factor enhancement multiplies alpha_s.
        if d["end_configuration"] == "one_unrestrained":
            if am != 1:
                raise ValueError("5.6.2(ii) uses elastic buckling moment directly and factor 1.")
            moa = mob
        else:
            moa = mob / am
        ratio = ms / moa
        reduction = 1.8 / (sqrt(ratio * ratio + 3) + ratio)
        mb = min(ms, am * reduction * ms)
        return result(
            op,
            ["5.6.2", "5.6.4"],
            {
                "reference_analysis_moment_knm": moa,
                "reduction": reduction,
                "member_capacity_knm": mb,
            },
            [capacity_check("5.6", mb, d["action_knm"])],
            [
                "External elastic flexural-torsional buckling analysis must model "
                "supports, restraints and loading.",
                "One-unrestrained-end segment requires other end full/partial restraint"
                " and lateral continuity/rotation restraint.",
                "Both-restrained path uses Moa=Mob/alpha_m under 5.6.4; moment factor "
                "needs 5.6.1.1 assessment.",
            ],
        )
    if op == "one_unrestrained_table_bending":
        # Table 5.6.2 applies to the three illustrated one-end-unrestrained cases.
        factors = {"uniform_end_moment": 0.25, "tip_force": 1.25, "uniform_load": 2.25}
        am = factors[d["moment_distribution"]]
        ms, mo = d["section_capacity_knm"], d["reference_buckling_moment_knm"]
        ratio = ms / mo
        reduction = 1.8 / (sqrt(ratio * ratio + 3) + ratio)
        mb = min(ms, am * reduction * ms)
        return result(
            op,
            ["5.6.1.1(1)", "5.6.1.1(2)", "5.6.1.1(3)", "5.6.2", "Table 5.6.2"],
            {
                "moment_factor": am,
                "reduction": reduction,
                "member_capacity_knm": mb,
            },
            [capacity_check("5.6.2(i)", mb, d["action_knm"])],
            [
                "Only the three Table 5.6.2 loading and moment-distribution cases "
                "are represented; combined or different cases need separate assessment.",
                "One end must be fully or partially restrained and laterally continuous "
                "or restrained against lateral rotation; the opposite end is unrestrained.",
                "Reference buckling moment Mo must be determined from 5.6.1.1(3) "
                "using effective length from 5.6.3 and eligible section properties.",
            ],
        )
    if op == "lateral_buckling_effective_length":
        arrangement = d["restraint_arrangement"]
        if (
            d["effective_rotation_restraint_count"]
            and not d["effective_rotation_restraints_verified"]
        ):
            raise ValueError("Count only effective rotational restraints verified under 5.4.3.4.")
        kt = 1.0
        if arrangement in {"FP", "PL", "PU", "PP"}:
            ratio = (d["clear_flange_depth_mm"] / d["segment_length_mm"]) * (
                d["critical_flange_thickness_mm"] / (2 * d["web_thickness_mm"])
            ) ** 3
            kt += ratio * (2 if arrangement == "PP" else 1) / d["number_of_webs"]
        if d["gravity_load_position"] == "within_segment":
            kl = (
                1.0
                if d["load_height_position"] == "shear_centre"
                else (2.0 if arrangement in {"FU", "PU"} else 1.4)
            )
        else:
            kl = (
                1.0
                if d["load_height_position"] == "shear_centre"
                else (2.0 if arrangement in {"FU", "PU"} else 1.0)
            )
        rotation_count = d["effective_rotation_restraint_count"]
        kr = 1.0
        if arrangement in {"FF", "FP", "PP"}:
            kr = {0: 1.0, 1: 0.85, 2: 0.70}[rotation_count]
        factor = kt * kl * kr
        return result(
            op,
            ["5.6.3", "Table 5.6.3(A)", "Table 5.6.3(B)", "Table 5.6.3(C)"],
            {
                "twist_restraint_factor": kt,
                "load_height_factor": kl,
                "lateral_rotation_factor": kr,
                "effective_length_factor": factor,
                "effective_length_mm": factor * d["segment_length_mm"],
            },
            [],
            [
                "Tables 5.6.3(A) and (B) cover only the listed beam-end restraint "
                "and gravity-load cases.",
                "Only effective lateral-rotation restraints under 5.4.3.4 reduce kr.",
                "The segment length must use restraint spacing or a valid sub-segment length.",
                "Verify geometry, end labels, loading, intermediate restraint and "
                "applicability independently.",
            ],
        )
    if op == "nonprincipal_bending":
        n = d["axial_action_kn"]
        mx, my = d["moment_x_knm"], d["moment_y_knm"]
        section = n / (0.9 * d["section_axial_capacity_kn"]) + (
            mx / (0.9 * d["section_moment_x_knm"]) + my / (0.9 * d["section_moment_y_knm"])
        )
        member = (mx / (0.9 * d["reduced_member_moment_x_knm"])) ** 1.4 + (
            my / (0.9 * d["reduced_member_moment_y_knm"])
        ) ** 1.4
        checks = [_limit("8.3.4", section, 1)]
        if not d["deflections_constrained"]:
            checks.append(_limit("8.4.5", member, 1))
        return result(
            op,
            ["5.7", "8.3.4", "8.4.5"],
            {
                "section_interaction": section,
                "member_interaction": member,
            },
            checks,
            [
                "Principal-axis moments and restraint forces must come from rational analysis.",
                "Reduced member capacities must already include axial and lateral-"
                "buckling reductions.",
                "Constrained path requires continuous restraints preventing lateral "
                "deflection under 5.7.1.",
            ],
        )
    if op == "plastic_in_plane":
        ns, n = d["section_axial_capacity_kn"], d["axial_action_kn"]
        ratio, beta = n / (0.9 * ns), d["beta_m"]
        web_lambda = d["web_clear_depth_mm"] / d["web_thickness_mm"] * sqrt(d["yield_mpa"] / 250)
        buckling_ratio = sqrt(ns / d["elastic_buckling_load_actual_length_kn"])
        if ratio <= 0.15:
            member_limit = ((0.6 + 0.4 * beta) / buckling_ratio) ** 2
        else:
            member_limit = (1 + beta - buckling_ratio) / (1 + beta + buckling_ratio)
        web_limit = (
            1
            if web_lambda <= 25
            else min(1, 1.91 - web_lambda / 27.4)
            if web_lambda < 45
            else 0.6 - web_lambda / 137
        )
        mrx = min(d["section_moment_x_knm"], 1.18 * d["section_moment_x_knm"] * max(0, 1 - ratio))
        mry = min(
            d["section_moment_y_knm"], 1.19 * d["section_moment_y_knm"] * max(0, 1 - ratio**2)
        )
        checks = [
            _limit("8.4.3.4 axial", ratio, 1),
            _reduced_check("8.4.3.4 x", d["moment_x_knm"], mrx),
            _reduced_check("8.4.3.4 y", d["moment_y_knm"], mry),
        ]
        if d["moment_x_knm"] and d["moment_y_knm"]:
            raise ValueError("Plastic in-plane operation is uniaxial only.")
        if d["axial_mode"] == "compression":
            checks.extend(
                [
                    _limit("8.4.3.2", ratio, member_limit),
                    _limit("8.4.3.3", ratio, web_limit),
                    _limit("8.4.3.3 plastic hinge eligibility", web_lambda, 82),
                ]
            )
        return result(
            op,
            ["8.4.3"],
            {
                "axial_ratio": ratio,
                "member_ratio_limit": member_limit,
                "web_slenderness": web_lambda,
                "web_ratio_limit": web_limit,
                "reduced_moment_x_knm": mrx,
                "reduced_moment_y_knm": mry,
            },
            checks,
            [
                "Compact doubly symmetric I-sections only; structure must satisfy "
                "plastic analysis provisions 4.5.",
                "No1 uses actual member length and inertia about bending axis.",
                "beta_m is positive for reverse curvature; lateral plastic-hinge "
                "restraints need 4.5.5.",
            ],
        )
    if op == "built_up_compression":
        ns, nc, n = d["section_capacity_kn"], d["member_capacity_kn"], d["axial_action_kn"]
        if nc > ns:
            raise ValueError("Member capacity cannot exceed section capacity.")
        ln, component = d["modified_member_slenderness"], d["component_slenderness"]
        transverse = max(0.01 * n, pi * (ns / nc - 1) * n / ln)
        perpendicular, parallel = (
            d["integral_slenderness_perpendicular"],
            d["integral_slenderness_parallel"],
        )
        if d["construction"] == "laced":
            effective_perpendicular = max(perpendicular, 1.4 * component)
            effective_parallel = max(parallel, 1.4 * component)
            limit = min(50, 0.6 * min(effective_perpendicular, effective_parallel))
        else:
            effective_perpendicular = sqrt(perpendicular**2 + component**2)
            effective_parallel = max(parallel, 1.4 * component)
            limit = min(50, 0.6 * min(effective_perpendicular, effective_parallel))
        checks = [_limit("6.4 main component", component, limit)]
        clauses = ["6.4.1", "6.4.2", "6.4.3", "6.5"]
        limitations = [
            "Recalculate member capacity and lambda_n from reported effective "
            "slenderness before design-force use.",
            "Back-to-back path limited to similar symmetric angle/channel/tee pairs"
            " and eligible spacing/packing.",
            "Approximately equal bays, end fasteners, tie plates and torsional "
            "effects need separate assessment.",
        ]
        if d["construction"] == "back_to_back":
            checks.append(_minimum("6.5 minimum bays", d["number_of_bays"], 3))
            if "interconnection_design" in d:
                demand = 0.25 * transverse * component
                capacity = d["interconnection_design"]["design_capacity_kn"]
                checks.append(
                    {
                        "clause": "6.5.1.5",
                        "design_demand_kn": demand,
                        "verified_design_capacity_kn": capacity,
                        "utilisation": demand / capacity if capacity > 0 else None,
                        "satisfied": demand <= capacity,
                    }
                )
                clauses.append("6.5.1.5")
            else:
                limitations.append(
                    "Clause 6.5.1.5 resistance comparison is omitted until a verified "
                    "per-interconnection design capacity is supplied."
                )
        elif "interconnection_design" in d:
            raise ValueError(
                "The Clause 6.5.1.5 interconnection check applies to back-to-back members."
            )
        return result(
            op,
            clauses,
            {
                "transverse_design_shear_kn": transverse,
                "effective_slenderness_perpendicular": effective_perpendicular,
                "effective_slenderness_parallel": effective_parallel,
                "component_slenderness_limit": limit,
                "back_to_back_connection_longitudinal_shear_kn": 0.25 * transverse * component,
            },
            checks,
            limitations,
        )
    if op == "lacing":
        double = d["mode"] == "double_connected"
        le = d["inner_connection_distance_mm"] * (0.7 if double else 1)
        slenderness = le / d["radius_mm"]
        compression = d["member_mode"] == "compression"
        limits = (40, 50) if double else (50, 70)
        required_width = d["component_connection_centroid_distance_mm"] * (
            1 if d["tie_type"] == "end" else 0.75
        )
        thickness = (0.02 if compression else 0.017) * d["tie_inner_connection_distance_mm"]
        thickness_ok = (
            compression and d["tie_edge_stiffened"] and d["tie_edge_stiffener_slenderness"] < 170
        )
        lacing_slenderness_clause = "6.4.2.5" if compression else "7.4.4(a)"
        tie_thickness_clause = "6.4.2.7" if compression else "7.4.4"
        return result(
            op,
            ["6.4.2.3", "6.4.2.4", "6.4.2.5", "6.4.2.7", "7.4.4"],
            {
                "effective_length_mm": le,
                "slenderness": slenderness,
                "required_tie_width_mm": required_width,
                "required_tie_thickness_mm": thickness,
            },
            [
                _limit(lacing_slenderness_clause, slenderness, 140 if compression else 210),
                {"clause": "6.4.2.3", "satisfied": limits[0] <= d["angle_degrees"] <= limits[1]},
                _minimum("tie width", d["tie_width_mm"], required_width),
                {
                    "clause": tie_thickness_clause,
                    "minimum_thickness_mm": thickness,
                    "provided_thickness_mm": d["tie_thickness_mm"],
                    "satisfied": thickness_ok
                    or d["tie_thickness_mm"] >= thickness
                    or isclose(d["tie_thickness_mm"], thickness, rel_tol=1e-12, abs_tol=1e-12),
                },
            ],
            [
                "Double lacing length reduction requires crossing weld/fastener connection.",
                "Tie plates require end/interruption/member-connection placement and "
                "7.4.2 design-force assessment; equal connection-plane allocation of supplied "
                "actions is available through tension_connection_plane_distribution.",
                "Opposed lacing and transverse members require 6.4.2.6 torsional-effect"
                " assessment.",
            ],
        )
    if op == "tension_connection_plane_distribution":
        if d["connection_type"] == "lacing" and "total_design_moment_knm" in d:
            raise ValueError("Clause 7.4.2 lacing distribution accepts design forces only.")
        planes = d["parallel_connection_planes"]
        force_per_plane = d["total_design_force_kn"] / planes
        moment_per_plane = (
            d["total_design_moment_knm"] / planes if "total_design_moment_knm" in d else None
        )
        checks = [
            {
                "clause": "7.4.2",
                "action": "design_force",
                "parallel_connection_planes": planes,
                "design_force_per_plane_kn": force_per_plane,
                "satisfied": True,
            }
        ]
        if moment_per_plane is not None:
            checks.append(
                {
                    "clause": "7.4.2",
                    "action": "design_bending_moment",
                    "parallel_connection_planes": planes,
                    "design_moment_per_plane_knm": moment_per_plane,
                    "satisfied": True,
                }
            )
        return result(
            op,
            ["7.4.2"],
            {
                "connection_type": d["connection_type"],
                "parallel_connection_planes": planes,
                "total_design_force_kn": d["total_design_force_kn"],
                "design_force_per_plane_kn": force_per_plane,
                "total_design_moment_knm": d.get("total_design_moment_knm"),
                "design_moment_per_plane_knm": moment_per_plane,
            },
            checks,
            [
                "Supply the verified total action assigned to all parallel connection planes; "
                "member actions and lacing/batten actions are not derived here.",
                "This applies the equal-share rule only. Design the lacing/batten sections, "
                "connections and load path separately.",
            ],
        )
    if op == "tension_built_up_connection_layout":
        separated = d["connection_arrangement"] == "separated"
        if separated and "separated_within_end_gusset_spacing_verified" not in d:
            raise ValueError(
                "Separated components require verification against the end-gusset "
                "connection spacing."
            )
        if not separated and "separated_within_end_gusset_spacing_verified" in d:
            raise ValueError(
                "End-gusset separation confirmation applies only to separated components."
            )
        if not isclose(sum(d["bay_lengths_mm"]), d["member_length_mm"], rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("Connection bay lengths must sum to the member length.")
        if d["end_connection_method"] == "fasteners":
            if "fasteners_per_connection_line_at_each_end" not in d:
                raise ValueError(
                    "Fastener end connections require the count on each connection line "
                    "at each end."
                )
            if "equivalent_end_welds_verified" in d:
                raise ValueError(
                    "Equivalent-weld confirmation applies only to welded end connections."
                )
            end_detail = {
                "method": "fasteners",
                "fasteners_per_connection_line_at_each_end": d[
                    "fasteners_per_connection_line_at_each_end"
                ],
                "satisfied": True,
            }
        else:
            if "equivalent_end_welds_verified" not in d:
                raise ValueError("Welded end connections require verification of weld equivalence.")
            if "fasteners_per_connection_line_at_each_end" in d:
                raise ValueError("Fastener count applies only to fastener end connections.")
            end_detail = {
                "method": "equivalent_welds",
                "equivalent_end_welds_verified": True,
                "satisfied": True,
            }
        layout_clause = "6.5.1.4" if separated else "6.5.2.4"
        tension_clause = "7.4.3(a)(ii)" if separated else "7.4.3(b)"
        checks = [
            {
                "clause": tension_clause,
                "connection_arrangement": d["connection_arrangement"],
                "satisfied": True,
            },
            {
                "clause": layout_clause,
                "bay_count": len(d["bay_lengths_mm"]),
                "minimum_bay_count": 3,
                "bay_lengths_mm": d["bay_lengths_mm"],
                "approximately_equal_bays_verified": True,
                "satisfied": True,
            },
            {"clause": layout_clause, "end_connection": end_detail, "satisfied": True},
        ]
        manual = [
            "Verify this is a two-component, discontinuously connected back-to-back member "
            "made from flats, angles, channels or tees.",
            "Use tension_built_up_interconnection for the 6.5.1.5 or 6.5.2.5 "
            "capacity comparison after deriving local actions under Clause 7.4.2.",
        ]
        if separated:
            manual.append(
                "Verify that component separation does not exceed the end-gusset "
                "connection requirement."
            )
        return result(
            op,
            [tension_clause, layout_clause],
            {
                "connection_arrangement": d["connection_arrangement"],
                "member_length_mm": d["member_length_mm"],
                "bay_count": len(d["bay_lengths_mm"]),
                "bay_lengths_mm": d["bay_lengths_mm"],
                "end_connection": end_detail,
            },
            checks,
            manual,
        )
    if op == "tension_built_up_interconnection":
        planes = d["parallel_connection_planes"]
        interconnections = d["interconnections"]
        if len(interconnections) * planes > 10000:
            raise ValueError("At most 10000 interconnection-plane checks are supported per call.")
        connection_clause = "6.5.1.5" if d["connection_arrangement"] == "separated" else "6.5.2.5"
        tension_clause = (
            "7.4.3(a)(ii)" if d["connection_arrangement"] == "separated" else "7.4.3(b)"
        )
        checks = []
        interconnection_results = []
        for index, interconnection in enumerate(interconnections, start=1):
            capacities = interconnection["design_capacity_by_plane_kn"]
            if len(capacities) != planes:
                raise ValueError(
                    f"Interconnection {index} must have one verified design capacity "
                    "for each parallel connection plane."
                )
            slenderness = (
                interconnection["component_length_between_connections_mm"]
                / interconnection["minimum_radius_of_gyration_mm"]
            )
            local_shear = interconnection["local_design_transverse_shear_kn"]
            total_demand = 0.25 * local_shear * slenderness
            plane_demand = total_demand / planes
            interconnection_results.append(
                {
                    "interconnection_index": index,
                    "local_design_transverse_shear_kn": local_shear,
                    "component_slenderness": slenderness,
                    "total_design_longitudinal_shear_kn": total_demand,
                    "design_shear_per_plane_kn": plane_demand,
                }
            )
            for plane_index, capacity in enumerate(capacities, start=1):
                checks.append(
                    {
                        "clause": connection_clause,
                        "interconnection_index": index,
                        "parallel_plane_index": plane_index,
                        "component_slenderness": slenderness,
                        "design_demand_kn": plane_demand,
                        "verified_design_capacity_kn": capacity,
                        "utilisation": plane_demand / capacity,
                        "satisfied": plane_demand <= capacity,
                    }
                )
        return result(
            op,
            ["7.4.2", tension_clause, connection_clause],
            {
                "connection_arrangement": d["connection_arrangement"],
                "parallel_connection_planes": planes,
                "interconnections": interconnection_results,
            },
            checks,
            [
                "Derive each interconnection's local transverse shear from verified external "
                "design actions under Clause 7.4.2; the compression-member transverse-shear "
                "envelope in Clause 6.4.1 is not applied here.",
                "Use tension_built_up_connection_layout separately for the connection "
                "geometry in Clause 6.5.1.4 or 6.5.2.4.",
                "Supply design capacity for each interconnection in every parallel plane; "
                "the capacities and their Clause 9 fastener/weld checks remain externally "
                "verified. Other connection moments and load paths require assessment.",
            ],
        )
    if op == "batten":
        end = d["type"] == "end"
        compression = d["member_mode"] == "compression"
        le = d["centroid_distance_mm"] * (1 if end else 0.7)
        width = max(
            d["centroid_distance_mm"] * (1 if end else 0.5),
            d["narrower_component_width_mm"] * (1 if end else 2),
        )
        if not compression and not end:
            width = 0.5 * d["effective_end_width_mm"]
        thickness = (0.02 if compression else 0.017) * d["inner_connection_distance_mm"]
        thickness_ok = (
            compression and d["edge_stiffened"] and d["edge_stiffener_slenderness"] <= 170
        )
        shear = (
            d["transverse_shear_kn"]
            * d["longitudinal_spacing_mm"]
            / (d["parallel_planes"] * d["connection_centroid_distance_mm"])
        )
        moment = (
            d["transverse_shear_kn"]
            * d["longitudinal_spacing_mm"]
            / (2 * d["parallel_planes"] * 1000)
        )
        clauses = ["6.4.3.3", "6.4.3.4", "6.4.3.5", "6.4.3.6"]
        width_clause = "6.4.3.5"
        thickness_clause = "6.4.3.6" if compression else "7.4.5(c)"
        checks = [
            _limit("6.4.3.4", le / d["radius_mm"], 180),
            {
                "clause": "7.4.5(d)" if not compression and not end else width_clause,
                "satisfied": d["width_mm"] >= width,
                "required_width_mm": width,
                "provided_width_mm": d["width_mm"],
            },
            {
                "clause": thickness_clause,
                "satisfied": (
                    thickness_ok
                    or d["thickness_mm"] >= thickness
                    or isclose(d["thickness_mm"], thickness, rel_tol=1e-12, abs_tol=1e-12)
                ),
                "minimum_thickness_mm": thickness,
                "provided_thickness_mm": d["thickness_mm"],
            },
        ]
        manual = []
        if compression:
            clauses.append("6.4.3.7")
            manual.append(
                "Simultaneous connection shear and moment require section and connection design."
            )
        else:
            if "connection_type" not in d:
                raise ValueError("Tension batten requires its connection type.")
            if d["connection_type"] == "bolted" and "bolts_per_component_connection" not in d:
                raise ValueError(
                    "Bolted tension batten requires the bolt count per component connection."
                )
            clauses.extend(["7.4.5(b)", "7.4.5(c)", "7.4.5(d)"])
            bolted = d["connection_type"] == "bolted"
            bolt_check = {
                "clause": "7.4.5(b)",
                "connection_type": d["connection_type"],
                "satisfied": (not bolted or d["bolts_per_component_connection"] >= 2),
            }
            if bolted:
                bolt_check["bolts_per_component_connection"] = d["bolts_per_component_connection"]
            checks.append(bolt_check)
            manual.append(
                "Under Clause 7.4.2, design tension battens and their connections for the "
                "internal actions from the external design forces and bending moments, divided "
                "equally among connection planes parallel to the force. Those actions are not "
                "calculated here."
            )
            if bolted:
                manual.append(
                    "Clause 7.4.5(b) is checked using the bolt count at each batten-to-component "
                    "connection; Clause 6.4.3.7 does not apply to this bolted tension route."
                )
        return result(
            op,
            clauses,
            {
                "effective_length_mm": le,
                "slenderness": le / d["radius_mm"],
                "minimum_width_mm": width,
                "minimum_thickness_mm": thickness,
                "connection_longitudinal_shear_kn": shear if compression else None,
                "connection_moment_knm": moment if compression else None,
            },
            checks,
            manual,
        )
    if op == "tension_component_slenderness":
        clause = {
            "separated_back_to_back": "7.4.3(a)(i)",
            "laced": "7.4.4(b)",
            "battened": "7.4.5(a)",
        }[d["arrangement"]]
        checks = []
        slenderness_values = []
        for index, interval in enumerate(d["component_intervals"], start=1):
            slenderness = (
                interval["unrestrained_length_mm"] / interval["minimum_radius_of_gyration_mm"]
            )
            check = _limit(clause, slenderness, 300)
            check.update(
                {
                    "interval_number": index,
                    "unrestrained_length_mm": interval["unrestrained_length_mm"],
                    "minimum_radius_of_gyration_mm": interval["minimum_radius_of_gyration_mm"],
                }
            )
            checks.append(check)
            slenderness_values.append(slenderness)
        return result(
            op,
            [clause],
            {
                "arrangement": d["arrangement"],
                "maximum_component_slenderness": max(slenderness_values),
                "interval_checks": checks,
            },
            checks,
            [
                "Supply every component interval between consecutive connections and "
                "its verified minimum radius of gyration.",
                "Verify the selected 7.4 arrangement and its other connection, spacing "
                "and tie/batten requirements separately.",
            ],
        )
    if op == "pin_tension_member":
        if d["ultimate_strength_mpa"] < d["yield_strength_mpa"]:
            raise ValueError("Ultimate strength must not be below yield strength.")
        if d["member_net_area_mm2"] > d["gross_area_mm2"]:
            raise ValueError("Member net area must not exceed gross area.")
        net_areas = [*d["net_area_beyond_hole_planes_mm2"], d["net_area_perpendicular_mm2"]]
        if any(area > d["gross_area_mm2"] for area in net_areas):
            raise ValueError("Pin-member net areas must not exceed gross area.")

        tension = d["design_tension_kn"]
        fy, fu = d["yield_strength_mpa"], d["ultimate_strength_mpa"]
        gross_area, net_area = d["gross_area_mm2"], d["member_net_area_mm2"]
        kt = d["tension_distribution_factor"]
        gross_yielding = gross_area * fy / 1000
        net_fracture = 0.85 * kt * net_area * fu / 1000
        governing_mode = (
            "gross section yielding" if gross_yielding <= net_fracture else "net section fracture"
        )
        required_gross_area = tension * 1000 / (0.9 * fy)
        required_net_area = tension * 1000 / (0.9 * 0.85 * kt * fu)
        thickness = 0.25 * d["hole_to_edge_distance_mm"]
        checks = [
            capacity_check("7.2 gross-section yielding", gross_yielding, tension),
            capacity_check("7.2 net-section fracture", net_fracture, tension),
            (
                {"clause": "7.5(a)", "satisfied": True}
                if d["internal_nut_clamped_ply"]
                else _minimum("7.5(a)", d["thickness_mm"], thickness)
            ),
        ]
        checks.extend(
            {
                "clause": "7.5(b)",
                "plane_index": index,
                "actual": area,
                "required_minimum": required_net_area,
                "satisfied": area >= required_net_area,
            }
            for index, area in enumerate(d["net_area_beyond_hole_planes_mm2"], start=1)
        )
        checks.extend(
            [
                _minimum("7.5(c)", d["net_area_perpendicular_mm2"], 1.33 * required_net_area),
                {"clause": "7.5(d)", "satisfied": True},
            ]
        )
        return result(
            op,
            ["7.1", "7.2", "7.5"],
            {
                "tension_distribution_factor": kt,
                "gross_yield_nominal_capacity_kn": gross_yielding,
                "net_fracture_nominal_capacity_kn": net_fracture,
                "nominal_section_tension_capacity_kn": min(gross_yielding, net_fracture),
                "design_section_tension_capacity_kn": 0.9 * min(gross_yielding, net_fracture),
                "governing_capacity_mode": governing_mode,
                "required_gross_area_mm2": required_gross_area,
                "required_member_net_area_mm2": required_net_area,
                "minimum_thickness_mm": thickness,
                "minimum_net_area_beyond_hole_mm2": required_net_area,
                "minimum_net_area_perpendicular_mm2": 1.33 * required_net_area,
            },
            checks,
            [
                "Gross and net areas and the Clause 7.3 tension-distribution factor are "
                "assessed inputs; apply all relevant deductions and use the appropriate "
                "verified factor.",
                "Supply every candidate beyond-hole plane parallel to or within 45 degrees "
                "of the member axis; completeness is an assessed prerequisite.",
                "Clause 7.5(d) load transfer and eccentricity are supplied as verified "
                "evidence. Pin shear, bearing and bending resistance are checked separately "
                "under Clause 9.4.",
            ],
        )
    if op == "restraint_action":
        beyond = d["beyond_forces_kn"]
        if d["type"] == "twist" and beyond:
            raise ValueError("Twist restraint operation applies to one member's critical flange.")
        minimum = 0.025 * d["connected_force_kn"] + 0.0125 * sum(beyond)
        force = max(minimum, d["analysis_restraint_force_kn"])
        return result(
            op,
            ["5.4.3", "6.6"],
            {"minimum_transverse_force_kn": minimum, "design_restraint_force_kn": force},
            [],
            [
                "Connected force is critical flange force for bending or local maximum "
                "compression force for compression.",
                "For 5.4.3.1, use the maximum critical-flange force from adjacent segments "
                "or sub-segments at the restraint.",
                "Parallel sequence includes connected member plus at most six connected"
                " members beyond.",
                "Analysis force includes design loads/notional loads and the full route"
                " to anchorage/reaction points.",
                "Grouping closer restraints, stiffness, rotational slip and force "
                "transfer remain engineering assessments.",
            ],
        )
    if op == "separator_diaphragm":
        if d["device_type"] == "separator" and d["external_vertical_force_transfer_required"]:
            raise ValueError("5.8 requires diaphragms for external vertical force transfer.")
        transverse_force = 0.025 * d["maximum_compression_flange_force_kn"]
        return result(
            op,
            ["5.8"],
            {
                "minimum_total_transverse_force_kn": transverse_force,
                "minimum_transverse_force_per_device_kn": transverse_force / d["device_count"],
            },
            [],
            [
                "Applies to two or more side-by-side I-sections or channels acting "
                "together in external-load distribution.",
                "Separators must comprise spacers and through bolts; assess any "
                "external transverse forces in addition to the stated minimum.",
                "Diaphragms and fastenings must distribute applied external vertical "
                "and transverse forces and resist resulting shear in addition to the "
                "stated minimum.",
                "Only the 5.8 minimum transverse force is shared equally. External "
                "force distribution, resulting shear and device capacities require "
                "separate design.",
            ],
        )
    if op == "angle_section_bending_capacity":
        ms = d["section_capacity_knm"]
        elastic_term = pi**2 * ELASTIC_MODULUS_MPA * d["iy_mm4"] / d["effective_length_mm"] ** 2
        mo = sqrt(elastic_term * SHEAR_MODULUS_MPA * d["torsion_constant_mm4"]) / 1e6
        if not isfinite(mo) or mo <= 0:
            raise ValueError(
                "Clause 5.6.1.1 reference buckling moment must be positive and finite."
            )
        ratio = ms / mo
        alpha_s = 0.6 * (sqrt(ratio**2 + 3) - ratio)
        alpha_m = d["moment_factor"]
        mb = min(ms, alpha_m * alpha_s * ms)
        return result(
            op,
            ["5.6.1.1(a)", "5.6.1.1(1)", "5.6.1.1(2)", "5.6.1.1(3)", "5.6.1.3"],
            {
                "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
                "shear_modulus_mpa": SHEAR_MODULUS_MPA,
                "reference_buckling_moment_knm": mo,
                "slenderness_reduction_alpha_s": alpha_s,
                "moment_factor_alpha_m": alpha_m,
                "nominal_member_moment_capacity_mb_knm": mb,
                "warping_constant_used_mm6": 0,
            },
            [],
            [
                "Applies to constant-cross-section angle members without full lateral "
                "restraint, with restraint conditions verified at both ends under Clause 5.6.1. "
                "Supply gross-section Ms from Clause 5.2 and angle Iy/J values.",
                "Clause 5.6.1.3 specifies Iw=0. The effective length must include the "
                "applicable Clause 5.6.3 assessment.",
                "Select alpha_m independently under Clause 5.6.1.1(1); this operation "
                "does not validate the moment-distribution route.",
                "This operation returns the Clause 5.6.1.3 bending capacity only. For the "
                "special equal-leg truss-angle provisions use the separate 8.4.6 operation; "
                "no combined action interaction is evaluated.",
            ],
        )
    if op == "angle_combined_interaction":
        phi = 0.9
        alpha = radians(d["angle_between_x_and_h_deg"])
        cos_alpha = cos(alpha)
        axial_utilisation = d["design_compression_kn"] / (
            phi * d["nominal_member_compression_nch_kn"]
        )
        moment_utilisation = d["design_moment_about_h_knm"] / (
            phi * d["nominal_member_bending_mbx_knm"] * cos_alpha
        )
        interaction_utilisation = axial_utilisation + moment_utilisation
        checks = [
            {
                "clause": "8.3",
                "satisfied": d["clause_8_3_interaction_satisfied"],
            },
            _limit("8.4.6 (Amd 1:2021)", interaction_utilisation, 1.0),
        ]
        return result(
            op,
            ["8.3", "8.4.6"],
            {
                "amendment_applied": "AS 4100:2020 Amd 1:2021",
                "capacity_factor_phi": phi,
                "angle_between_x_and_h_deg": d["angle_between_x_and_h_deg"],
                "cos_alpha": cos_alpha,
                "axial_utilisation": axial_utilisation,
                "moment_utilisation": moment_utilisation,
                "interaction_utilisation": interaction_utilisation,
                "clause_8_3_interaction_satisfied": d["clause_8_3_interaction_satisfied"],
            },
            checks,
            [
                "Uses the Clause 8.4.6 equation corrected by AS 4100:2020 Amendment No. 1 (2021).",
                "Nch and Mbx are supplied nominal capacities; verify them from their respective "
                "Clause 8.4.6 capacity operations and verify the angle-axis orientation.",
                "This operation applies only to a single-angle web compression member in a truss "
                "connected by at least two bolts or welded at its ends and loaded through one leg.",
                "Clause 8.3 is a required separate check. This result does not establish "
                "whole-member or full-standard compliance.",
            ],
        )
    if op == "angle_compression_capacity":
        ag = d["gross_area_mm2"]
        an = d["net_area_mm2"]
        ae = d["effective_area_mm2"]
        if an > ag or ae > ag:
            raise ValueError("Net and effective areas must not exceed gross area.")
        kf = ae / ag
        fy = d["yield_strength_mpa"]
        ns = kf * an * fy / 1000
        alpha_b = 0.5 if kf == 1 else 1.0
        lambda_n = (
            d["member_length_mm"] / d["radius_about_loaded_leg_h_axis_mm"] * sqrt(kf * fy / 250)
        )
        alpha_a = 2100 * (lambda_n - 13.5) / (lambda_n**2 - 15.3 * lambda_n + 2050)
        slenderness = max(0, lambda_n + alpha_a * alpha_b)
        eta = max(0, 0.00326 * (slenderness - 13.5))
        q = (slenderness / 90) ** 2
        a = 1 + q + eta
        alpha_c = min(1, 2 / (a + sqrt(max(0, a * a - 4 * q))))
        nch = min(ns, alpha_c * ns)
        return result(
            op,
            ["6.2.1", "6.2.2", "6.3.2", "6.3.3", "Table 6.3.3(A/B)", "8.4.6"],
            {
                "form_factor_kf": kf,
                "nominal_section_capacity_ns_kn": ns,
                "effective_length_mm": d["member_length_mm"],
                "buckling_axis": "rectangular h-axis parallel to the loaded leg",
                "modified_member_slenderness_lambda_n": lambda_n,
                "section_constant_alpha_b": alpha_b,
                "alpha_a": alpha_a,
                "imperfection_adjusted_slenderness": slenderness,
                "eta": eta,
                "member_reduction_alpha_c": alpha_c,
                "nominal_member_capacity_nch_kn": nch,
            },
            [],
            [
                "Applies to the single-angle truss arrangement and loaded-leg orientation "
                "in Figure 8.4.6; these conditions and section "
                "properties are supplied as verified.",
                "The effective length is set equal to the member length as required by "
                "Clause 8.4.6. Supply the verified radius of gyration about the rectangular "
                "h-axis parallel to the loaded leg.",
                "The effective area must follow Clause 6.2.4. Apply the Clause 6.2.1 net-area "
                "exception and Clause 9.1.10 fastener-hole deductions when selecting An.",
                "For angles, Table 6.3.3(A) gives alpha_b=0.5 when kf=1; Table 6.3.3(B) "
                "gives alpha_b=1.0 for other sections, including angles, when kf<1.",
                "Returns nominal Nch only. No axial demand/capacity check or combined "
                "Clause 8.4.6 interaction is evaluated for this eccentric-load case.",
            ],
        )
    if op == "angle_bending_capacity":
        if d["angle_leg_a_width_mm"] != d["angle_leg_b_width_mm"]:
            raise ValueError("This 8.4.6 route applies only to equal-leg angles.")

        member_slenderness = d["member_length_mm"] / d["angle_thickness_mm"]
        slenderness_limit = (210 + 175 * d["beta_m"]) * (250 / d["yield_strength_mpa"])
        use_shortcut = member_slenderness <= slenderness_limit
        msx = d["section_capacity_knm"]
        mo = None
        alpha_s = None
        alpha_m = None
        if use_shortcut:
            mbx = msx
        else:
            if "moment_factor" not in d:
                raise ValueError(
                    "A verified Clause 5.6.1.1 moment_factor is required when the "
                    "equal-leg slenderness limit is not satisfied."
                )
            mo = (
                (525 * d["angle_thickness_mm"] / d["member_length_mm"])
                * (250 / d["yield_strength_mpa"])
                * msx
            )
            ratio = msx / mo
            alpha_s = 0.6 * (sqrt(ratio**2 + 3) - ratio)
            alpha_m = d["moment_factor"]
            mbx = min(msx, alpha_m * alpha_s * msx)

        clauses = ["8.4.6", "5.2"]
        if not use_shortcut:
            clauses.extend(["5.6.1.1(1)", "5.6.1.1(2)"])
        return result(
            op,
            clauses,
            {
                "member_slenderness_l_over_t": member_slenderness,
                "equal_leg_slenderness_limit_l_over_t": slenderness_limit,
                "equal_leg_shortcut_used": use_shortcut,
                "section_moment_capacity_msx_knm": msx,
                "reference_buckling_moment_mo_knm": mo,
                "slenderness_reduction_alpha_s": alpha_s,
                "moment_factor_alpha_m": alpha_m,
                "member_moment_capacity_mbx_knm": mbx,
            },
            [],
            [
                "Applies only to equal-leg angles meeting the Clause 8.4.6 single-angle "
                "truss arrangement, connection and loading conditions, without full lateral "
                "support; these conditions and section properties are supplied as verified.",
                "Supply gross-section Msx from Clause 5.2 and beta_m selected for the "
                "applicable moment distribution. If the equal-leg limit is not met, supply "
                "alpha_m independently selected under Clause 5.6.1.1(1).",
                "Calculates the angle member bending capacity Mbx only. It does not calculate "
                "Nch or compare a design moment with capacity. Supply Mbx to the separate "
                "angle_combined_interaction operation when checking Clause 8.4.6.",
                "For equal-leg angles within the limit, Clause 8.4.6 permits Mbx=Msx; the "
                "moment factor is not used on that route.",
            ],
        )
    # Geometry-only primitive: calculate the eccentricity and design end moment.
    if d["arrangement"] == "same_side":
        eccentricity = d["compression_centroid_offset_mm"] - d["leg_thickness_mm"] / 2
        if eccentricity < 0:
            raise ValueError("Same-side centroid offset must be at least half leg thickness.")
    else:
        eccentricity = d["compression_centroid_offset_mm"] + d["tension_centroid_offset_mm"]
    minimum_moment = d["axial_action_kn"] * eccentricity / 1000
    moment_method = d.get("moment_method", "conservative_max")
    rational_moment = d.get("rational_analysis_moment_knm")
    if moment_method == "rational_analysis":
        design_moment = rational_moment
    elif moment_method == "minimum_eccentricity":
        design_moment = minimum_moment
    else:
        design_moment = max(minimum_moment, rational_moment)
    return result(
        op,
        ["8.4.6"],
        {
            "eccentricity_mm": eccentricity,
            "minimum_design_moment_knm": minimum_moment,
            "moment_method": moment_method,
            "rational_analysis_moment_knm": rational_moment,
            "design_moment_knm": design_moment,
        },
        [],
        [
            "The rational-analysis route uses the verified elastic truss moment as written "
            "in Clause 8.4.6 and does not impose the separate N*e minimum.",
            "The minimum_eccentricity route sets M_h* to N*e; use a larger value if required "
            "by the design assessment.",
            "The legacy input shape defaults to conservative_max, taking the greater of the "
            "rational-analysis moment and N*e.",
            "The operation calculates design moment only; the special angle interaction "
            "is checked separately by angle_combined_interaction using Amendment No. 1:2021.",
            "Angles must be double-bolted or welded and loading through one leg "
            "must match Figure 8.4.6.",
        ],
    )
