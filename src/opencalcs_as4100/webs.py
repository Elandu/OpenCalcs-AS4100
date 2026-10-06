# SPDX-License-Identifier: AGPL-3.0-only
"""Web geometry, bearing and stiffener checks, clauses 5.10 and 5.13 to 5.16."""

from math import isclose, sqrt

from .members import run_members
from .standards import ELASTIC_MODULUS_MPA
from .validation import (
    NONNEGATIVE,
    POSITIVE,
    SIGNED,
    YIELD_STRESS,
    capacity_check,
    object_schema,
    result,
    validate,
)

_WEB_THICKNESS_COMMON = {
    "operation": {"const": "web_minimum_thickness"},
    "clear_web_depth_mm": POSITIVE,
    "web_thickness_mm": POSITIVE,
    "web_yield_mpa": YIELD_STRESS,
}

_FLAT_STIFFENER_PLATE_SCHEMA = object_schema(
    {
        "clear_outstand_mm": POSITIVE,
        "thickness_mm": POSITIVE,
        "yield_mpa": YIELD_STRESS,
        "residual_stress_category": {
            "type": "string",
            "enum": ["SR", "HR", "CF", "LW", "HW"],
        },
    }
)


def _web_minimum_thickness_schema():
    variants = [
        object_schema(
            {
                **_WEB_THICKNESS_COMMON,
                "design_case": {"const": "unstiffened"},
                "edge_condition": {"enum": ["both_flange_bounded", "one_longitudinal_edge_free"]},
                "geometry_verified": {"const": True},
            }
        ),
        object_schema(
            {
                **_WEB_THICKNESS_COMMON,
                "design_case": {"const": "transversely_stiffened"},
                "stiffener_spacing_mm": POSITIVE,
                "greatest_panel_depth_mm": POSITIVE,
                "stiffener_layout_verified": {"const": True},
            }
        ),
        object_schema(
            {
                **_WEB_THICKNESS_COMMON,
                "design_case": {"const": "longitudinal_and_transverse"},
                "stiffener_spacing_mm": POSITIVE,
                "d2_mm": POSITIVE,
                "neutral_axis_stiffener_set_present": {"type": "boolean"},
                "stiffener_layout_verified": {"const": True},
            }
        ),
        object_schema(
            {
                **_WEB_THICKNESS_COMMON,
                "design_case": {"const": "plastic_hinge"},
                "hinge_zone_load_kn": NONNEGATIVE,
                "design_web_shear_yield_capacity_kn": POSITIVE,
                "bearing_or_shear_within_half_depth_of_hinge_verified": {"type": "boolean"},
                "load_bearing_stiffeners_provided": {"type": "boolean"},
                "stiffeners_within_half_depth_verified": {"type": "boolean"},
                "stiffener_design_5_14_verified": {"type": "boolean"},
                "flat_stiffener_plates": {
                    "type": "array",
                    "items": _FLAT_STIFFENER_PLATE_SCHEMA,
                    "minItems": 1,
                    "maxItems": 20,
                },
            },
            [
                "operation",
                "clear_web_depth_mm",
                "web_thickness_mm",
                "web_yield_mpa",
                "design_case",
                "hinge_zone_load_kn",
                "design_web_shear_yield_capacity_kn",
                "bearing_or_shear_within_half_depth_of_hinge_verified",
                "load_bearing_stiffeners_provided",
                "stiffeners_within_half_depth_verified",
                "stiffener_design_5_14_verified",
            ],
        ),
    ]
    return {"oneOf": variants}


_BEARING = {
    "operation": {"const": "web_bearing"},
    "section_type": {"enum": ["i_or_channel", "rhs_shs"]},
    "web_thickness_mm": {"type": "number", "minimum": 3, "maximum": 1e6},
    "web_yield_mpa": YIELD_STRESS,
    "clear_web_depth_mm": POSITIVE,
    "bearing_width_at_flange_mm": POSITIVE,
    "bearing_width_at_neutral_axis_mm": POSITIVE,
    "flange_thickness_mm": POSITIVE,
    "distance_flange_to_neutral_axis_mm": POSITIVE,
    "bearing_geometry_verified": {"type": "boolean"},
    "restrained_flange_count": {"type": "integer", "enum": [1, 2]},
    "bearing_action_kn": NONNEGATIVE,
    "outside_radius_mm": POSITIVE,
    "stiff_bearing_length_mm": POSITIVE,
    "distance_to_member_end_mm": NONNEGATIVE,
}

_TRANSVERSE_LOAD_BEARING_STIFFENER_PROPERTIES = {
    "web_bearing_yield_kn": POSITIVE,
    "contact_stiffener_area_mm2": POSITIVE,
    "radius_of_gyration_mm": POSITIVE,
    "both_flanges_rotation_restrained": {"type": "boolean"},
    "available_web_width_left_mm": NONNEGATIVE,
    "available_web_width_right_mm": NONNEGATIVE,
    "torsional_end_restraint_required": {"type": "boolean"},
    "critical_flange_centroid_spacing_mm": POSITIVE,
    "critical_flange_thickness_mm": POSITIVE,
    "total_design_load_between_supports_kn": POSITIVE,
    "stiffener_pair_second_moment_about_web_centerline_mm4": POSITIVE,
}
_TRANSVERSE_LOAD_BEARING_STIFFENER_REQUIRED = [
    "web_bearing_yield_kn",
    "contact_stiffener_area_mm2",
    "radius_of_gyration_mm",
    "both_flanges_rotation_restrained",
    "available_web_width_left_mm",
    "available_web_width_right_mm",
]
_TRANSVERSE_LOAD_BEARING_STIFFENER_SCHEMA = object_schema(
    _TRANSVERSE_LOAD_BEARING_STIFFENER_PROPERTIES,
    _TRANSVERSE_LOAD_BEARING_STIFFENER_REQUIRED,
) | {
    "allOf": [
        {
            "if": {
                "required": ["torsional_end_restraint_required"],
                "properties": {"torsional_end_restraint_required": {"const": True}},
            },
            "then": {
                "required": [
                    "critical_flange_centroid_spacing_mm",
                    "critical_flange_thickness_mm",
                    "total_design_load_between_supports_kn",
                    "stiffener_pair_second_moment_about_web_centerline_mm4",
                ]
            },
            "else": {
                "not": {
                    "anyOf": [
                        {"required": ["critical_flange_centroid_spacing_mm"]},
                        {"required": ["critical_flange_thickness_mm"]},
                        {"required": ["total_design_load_between_supports_kn"]},
                        {"required": ["stiffener_pair_second_moment_about_web_centerline_mm4"]},
                    ]
                }
            },
        }
    ]
}


_LOAD_BEARING_STIFFENER_ATTACHMENT_PROPERTIES = {
    "design_force_share_to_web_kn": NONNEGATIVE,
    "web_connection_design_capacity_kn": POSITIVE,
    "tight_uniform_bearing_against_loaded_flange_verified": {"type": "boolean"},
    "flange_to_stiffener_connection_design_capacity_kn": POSITIVE,
    "concentrated_force_directly_over_support": {"type": "boolean"},
    "both_flanges_fitted_or_connected_verified": {"type": "boolean"},
}
_LOAD_BEARING_STIFFENER_ATTACHMENT_REQUIRED = [
    "design_force_share_to_web_kn",
    "web_connection_design_capacity_kn",
    "tight_uniform_bearing_against_loaded_flange_verified",
    "concentrated_force_directly_over_support",
]


def _load_bearing_stiffener_attachment_schema(*, include_operation, include_action):
    properties = dict(_LOAD_BEARING_STIFFENER_ATTACHMENT_PROPERTIES)
    required = list(_LOAD_BEARING_STIFFENER_ATTACHMENT_REQUIRED)
    if include_operation:
        properties = {
            "operation": {"const": "load_bearing_stiffener_attachment"},
            **properties,
        }
        required.insert(0, "operation")
    if include_action:
        properties["design_bearing_force_kn"] = NONNEGATIVE
        required.append("design_bearing_force_kn")
    return object_schema(properties, required) | {
        "allOf": [
            {
                "if": {
                    "required": ["tight_uniform_bearing_against_loaded_flange_verified"],
                    "properties": {
                        "tight_uniform_bearing_against_loaded_flange_verified": {"const": False}
                    },
                },
                "then": {"required": ["flange_to_stiffener_connection_design_capacity_kn"]},
            },
            {
                "if": {
                    "required": ["concentrated_force_directly_over_support"],
                    "properties": {"concentrated_force_directly_over_support": {"const": True}},
                },
                "then": {"required": ["both_flanges_fitted_or_connected_verified"]},
            },
        ]
    }


_LOAD_BEARING_STIFFENER_ATTACHMENT_SCHEMA = _load_bearing_stiffener_attachment_schema(
    include_operation=False,
    include_action=False,
)

_END_POST_AREA_PROPERTIES = {
    "clear_web_depth_mm": POSITIVE,
    "design_shear_action_kn": NONNEGATIVE,
    "capacity_factor": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
    "shear_buckling_coefficient": {"type": "number", "minimum": 0, "maximum": 1},
    "nominal_web_shear_yield_capacity_kn": POSITIVE,
    "end_plate_to_load_bearing_stiffener_distance_mm": POSITIVE,
    "end_plate_yield_mpa": YIELD_STRESS,
    "end_plate_area_mm2": NONNEGATIVE,
}

_END_POST_STIFFENER_PROPERTIES = {
    **_TRANSVERSE_LOAD_BEARING_STIFFENER_PROPERTIES,
    "stiffener_area_mm2": POSITIVE,
    "stiffener_configuration": {"enum": ["pair", "single_angle", "single_plate"]},
    "web_yield_mpa": YIELD_STRESS,
    "stiffener_yield_mpa": YIELD_STRESS,
    "web_thickness_mm": POSITIVE,
    "clear_web_depth_mm": POSITIVE,
    "panel_spacing_mm": POSITIVE,
    "stiffener_outstand_mm": POSITIVE,
    "stiffener_thickness_mm": POSITIVE,
    "outer_edge_continuously_stiffened": {"type": "boolean"},
    "load_bearing_stiffener_not_smaller_than_end_plate_verified": {"type": "boolean"},
}
_END_POST_STIFFENER_REQUIRED = [
    "web_bearing_yield_kn",
    "contact_stiffener_area_mm2",
    "radius_of_gyration_mm",
    "both_flanges_rotation_restrained",
    "available_web_width_left_mm",
    "available_web_width_right_mm",
    "stiffener_area_mm2",
    "stiffener_configuration",
    "web_yield_mpa",
    "stiffener_yield_mpa",
    "web_thickness_mm",
    "clear_web_depth_mm",
    "panel_spacing_mm",
    "stiffener_outstand_mm",
    "stiffener_thickness_mm",
    "outer_edge_continuously_stiffened",
    "load_bearing_stiffener_not_smaller_than_end_plate_verified",
]
_END_POST_STIFFENER_SCHEMA = object_schema(
    _END_POST_STIFFENER_PROPERTIES,
    _END_POST_STIFFENER_REQUIRED,
)
_TRANSVERSE_STIFFENER_BUCKLING_GEOMETRY_SCHEMA = object_schema(
    {
        "radius_of_gyration_mm": POSITIVE,
        "available_web_width_left_mm": NONNEGATIVE,
        "available_web_width_right_mm": NONNEGATIVE,
    }
)

SCHEMAS = {
    "web_minimum_thickness": _web_minimum_thickness_schema(),
    "web_opening_geometry": object_schema(
        {
            "operation": {"const": "web_opening_geometry"},
            "clear_web_depth_mm": POSITIVE,
            "opening_internal_dimension_mm": POSITIVE,
            "longitudinal_stiffeners_present": {"type": "boolean"},
            "adjacent_openings_present": {"type": "boolean"},
            "adjacent_opening_boundary_spacing_mm": NONNEGATIVE,
            "adjacent_opening_greatest_internal_dimension_mm": POSITIVE,
            "unstiffened_openings_at_cross_section": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10000,
            },
            "multiple_openings_rational_analysis_verified": {"type": "boolean"},
            "opening_geometry_verified": {"const": True},
        },
        [
            "operation",
            "clear_web_depth_mm",
            "opening_internal_dimension_mm",
            "longitudinal_stiffeners_present",
            "adjacent_openings_present",
            "adjacent_opening_boundary_spacing_mm",
            "unstiffened_openings_at_cross_section",
            "multiple_openings_rational_analysis_verified",
            "opening_geometry_verified",
        ],
    ),
    "web_opening_shear_design": object_schema(
        {
            "operation": {"const": "web_opening_shear_design"},
            "clear_web_depth_mm": POSITIVE,
            "opening_internal_dimension_mm": POSITIVE,
            "longitudinal_stiffeners_present": {"const": False},
            "adjacent_openings_present": {"type": "boolean"},
            "adjacent_opening_boundary_spacing_mm": NONNEGATIVE,
            "adjacent_opening_greatest_internal_dimension_mm": POSITIVE,
            "unstiffened_openings_at_cross_section": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10000,
            },
            "multiple_openings_rational_analysis_verified": {"type": "boolean"},
            "opening_geometry_verified": {"const": True},
            "yield_strength_mpa": YIELD_STRESS,
            "web_area_at_opening_mm2": POSITIVE,
            "web_area_basis_verified": {"type": "boolean"},
            "panel_depth_mm": POSITIVE,
            "web_thickness_mm": POSITIVE,
            "stiffener_spacing_mm": POSITIVE,
            "maximum_design_shear_stress_mpa": POSITIVE,
            "average_design_shear_stress_mpa": POSITIVE,
            "rational_elastic_analysis_reference": {
                "type": "string",
                "minLength": 1,
                "maxLength": 200,
            },
            "rational_elastic_analysis_verified": {"type": "boolean"},
            "action_kn": NONNEGATIVE,
            "moment_action_knm": NONNEGATIVE,
            "section_moment_capacity_knm": POSITIVE,
        },
        [
            "operation",
            "clear_web_depth_mm",
            "opening_internal_dimension_mm",
            "longitudinal_stiffeners_present",
            "adjacent_openings_present",
            "adjacent_opening_boundary_spacing_mm",
            "unstiffened_openings_at_cross_section",
            "multiple_openings_rational_analysis_verified",
            "opening_geometry_verified",
            "yield_strength_mpa",
            "web_area_at_opening_mm2",
            "web_area_basis_verified",
            "panel_depth_mm",
            "web_thickness_mm",
            "maximum_design_shear_stress_mpa",
            "average_design_shear_stress_mpa",
            "rational_elastic_analysis_reference",
            "rational_elastic_analysis_verified",
            "action_kn",
            "moment_action_knm",
            "section_moment_capacity_knm",
        ],
    ),
    "load_bearing_stiffener_requirement": object_schema(
        {
            "operation": {"const": "load_bearing_stiffener_requirement"},
            "design_compressive_bearing_force_kn": NONNEGATIVE,
            "design_web_bearing_capacity_kn": POSITIVE,
            "end_post_required_under_5_15_2_2": {"type": "boolean"},
            "load_bearing_stiffeners_provided": {"type": "boolean"},
        }
    ),
    "load_bearing_stiffener_attachment": _load_bearing_stiffener_attachment_schema(
        include_operation=True,
        include_action=True,
    ),
    "web_side_reinforcement": object_schema(
        {
            "operation": {"const": "web_side_reinforcement"},
            "design_shear_share_kn": NONNEGATIVE,
            "side_plate_design_shear_capacity_kn": POSITIVE,
            "fastener_design_shear_capacity_to_web_kn": POSITIVE,
            "fastener_design_shear_capacity_to_flanges_kn": POSITIVE,
            "symmetry_effects_accounted": {"type": "boolean"},
        }
    ),
    "web_bearing": object_schema(
        _BEARING,
        [
            "operation",
            "section_type",
            "web_thickness_mm",
            "web_yield_mpa",
            "clear_web_depth_mm",
            "bearing_action_kn",
            "restrained_flange_count",
        ],
    )
    | {
        "allOf": [
            {
                "if": {
                    "required": ["section_type"],
                    "properties": {"section_type": {"const": "i_or_channel"}},
                },
                "then": {
                    "oneOf": [
                        {
                            "required": [
                                "bearing_width_at_flange_mm",
                                "bearing_width_at_neutral_axis_mm",
                            ]
                        },
                        {
                            "required": [
                                "stiff_bearing_length_mm",
                                "flange_thickness_mm",
                                "distance_flange_to_neutral_axis_mm",
                                "bearing_geometry_verified",
                            ]
                        },
                    ]
                },
            }
        ]
    },
    "load_bearing_stiffener": object_schema(
        {
            "operation": {"const": "load_bearing_stiffener"},
            "web_bearing_yield_kn": POSITIVE,
            "stiffener_area_mm2": POSITIVE,
            "web_yield_mpa": YIELD_STRESS,
            "stiffener_yield_mpa": YIELD_STRESS,
            "contact_stiffener_area_mm2": POSITIVE,
            "web_thickness_mm": POSITIVE,
            "clear_web_depth_mm": POSITIVE,
            "panel_spacing_mm": POSITIVE,
            "radius_of_gyration_mm": POSITIVE,
            "both_flanges_rotation_restrained": {"type": "boolean"},
            "available_web_width_left_mm": NONNEGATIVE,
            "available_web_width_right_mm": NONNEGATIVE,
            "stiffener_outstand_mm": POSITIVE,
            "stiffener_thickness_mm": POSITIVE,
            "outer_edge_continuously_stiffened": {"type": "boolean"},
            "bearing_action_kn": NONNEGATIVE,
            "torsional_end_restraint_required": {"type": "boolean"},
            "stiffener_configuration": {"enum": ["pair", "single_angle", "single_plate"]},
            "critical_flange_centroid_spacing_mm": POSITIVE,
            "critical_flange_thickness_mm": POSITIVE,
            "total_design_load_between_supports_kn": POSITIVE,
            "stiffener_pair_second_moment_about_web_centerline_mm4": POSITIVE,
        },
        [
            "operation",
            "web_bearing_yield_kn",
            "stiffener_area_mm2",
            "web_yield_mpa",
            "stiffener_yield_mpa",
            "contact_stiffener_area_mm2",
            "web_thickness_mm",
            "clear_web_depth_mm",
            "panel_spacing_mm",
            "radius_of_gyration_mm",
            "both_flanges_rotation_restrained",
            "available_web_width_left_mm",
            "available_web_width_right_mm",
            "stiffener_outstand_mm",
            "stiffener_thickness_mm",
            "outer_edge_continuously_stiffened",
            "bearing_action_kn",
        ],
    )
    | {
        "allOf": [
            {
                "if": {
                    "required": ["torsional_end_restraint_required"],
                    "properties": {"torsional_end_restraint_required": {"const": True}},
                },
                "then": {
                    "required": [
                        "stiffener_configuration",
                        "critical_flange_centroid_spacing_mm",
                        "critical_flange_thickness_mm",
                        "total_design_load_between_supports_kn",
                        "stiffener_pair_second_moment_about_web_centerline_mm4",
                    ],
                    "properties": {"stiffener_configuration": {"const": "pair"}},
                },
                "else": {
                    "not": {
                        "anyOf": [
                            {"required": ["critical_flange_centroid_spacing_mm"]},
                            {"required": ["critical_flange_thickness_mm"]},
                            {"required": ["total_design_load_between_supports_kn"]},
                            {"required": ["stiffener_pair_second_moment_about_web_centerline_mm4"]},
                        ]
                    }
                },
            }
        ]
    },
    "transverse_stiffener": object_schema(
        {
            "operation": {"const": "transverse_stiffener"},
            "clear_web_depth_mm": POSITIVE,
            "web_panel_depth_mm": POSITIVE,
            "web_thickness_mm": POSITIVE,
            "panel_spacing_mm": POSITIVE,
            "web_area_mm2": POSITIVE,
            "web_yield_mpa": YIELD_STRESS,
            "shear_buckling_coefficient": {"type": "number", "minimum": 0, "maximum": 1},
            "stiffener_configuration": {"enum": ["pair", "single_angle", "single_plate"]},
            "shear_action_kn": NONNEGATIVE,
            "nominal_web_shear_kn": POSITIVE,
            "nominal_web_buckling_no_tension_field_kn": POSITIVE,
            "nominal_stiffener_buckling_kn": POSITIVE,
            "stiffener_buckling_geometry": _TRANSVERSE_STIFFENER_BUCKLING_GEOMETRY_SCHEMA,
            "stiffener_area_mm2": POSITIVE,
            "stiffener_second_moment_mm4": POSITIVE,
            "stiffener_outstand_mm": POSITIVE,
            "stiffener_thickness_mm": POSITIVE,
            "stiffener_yield_mpa": YIELD_STRESS,
            "outer_edge_continuously_stiffened": {"type": "boolean"},
            "stiffener_layout_verified": {"const": True},
            "longitudinal_stiffeners_present": {"type": "boolean"},
            "longitudinal_stiffener_d2_mm": POSITIVE,
            "neutral_axis_stiffener_set_present": {"type": "boolean"},
            "web_connection_design_shear_capacity_kn_per_mm": POSITIVE,
            "web_connection_capacity_verified": {"type": "boolean"},
            "stiffener_top_flange_gap_mm": NONNEGATIVE,
            "stiffener_bottom_flange_gap_mm": NONNEGATIVE,
            "flange_termination_geometry_verified": {"type": "boolean"},
            "external_normal_force_kn": NONNEGATIVE,
            "external_moment_knm": SIGNED,
            "external_parallel_force_kn": SIGNED,
            "force_eccentricity_mm": SIGNED,
            "capacity_factor": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
            "external_actions_verified": {"type": "boolean"},
            "load_bearing_stiffener_inputs": _TRANSVERSE_LOAD_BEARING_STIFFENER_SCHEMA,
            "load_bearing_stiffener_attachment_inputs": _LOAD_BEARING_STIFFENER_ATTACHMENT_SCHEMA,
        },
        [
            "operation",
            "clear_web_depth_mm",
            "web_panel_depth_mm",
            "web_thickness_mm",
            "panel_spacing_mm",
            "web_area_mm2",
            "web_yield_mpa",
            "stiffener_configuration",
            "shear_action_kn",
            "stiffener_area_mm2",
            "stiffener_second_moment_mm4",
            "stiffener_outstand_mm",
            "stiffener_thickness_mm",
            "stiffener_yield_mpa",
            "outer_edge_continuously_stiffened",
            "stiffener_layout_verified",
            "longitudinal_stiffeners_present",
        ],
    )
    | {
        "allOf": [
            {
                "if": {"required": ["stiffener_buckling_geometry"]},
                "then": {
                    "not": {
                        "anyOf": [
                            {"required": ["shear_buckling_coefficient"]},
                            {"required": ["nominal_web_shear_kn"]},
                            {"required": ["nominal_web_buckling_no_tension_field_kn"]},
                            {"required": ["nominal_stiffener_buckling_kn"]},
                        ]
                    }
                },
                "else": {
                    "required": [
                        "shear_buckling_coefficient",
                        "nominal_web_shear_kn",
                        "nominal_web_buckling_no_tension_field_kn",
                        "nominal_stiffener_buckling_kn",
                    ]
                },
            },
            {
                "if": {
                    "required": ["longitudinal_stiffeners_present"],
                    "properties": {"longitudinal_stiffeners_present": {"const": True}},
                },
                "then": {
                    "required": [
                        "longitudinal_stiffener_d2_mm",
                        "neutral_axis_stiffener_set_present",
                    ]
                },
                "else": {
                    "not": {
                        "anyOf": [
                            {"required": ["longitudinal_stiffener_d2_mm"]},
                            {"required": ["neutral_axis_stiffener_set_present"]},
                        ]
                    }
                },
            },
            {
                "if": {
                    "anyOf": [
                        {"required": ["stiffener_top_flange_gap_mm"]},
                        {"required": ["stiffener_bottom_flange_gap_mm"]},
                        {"required": ["flange_termination_geometry_verified"]},
                    ]
                },
                "then": {
                    "required": [
                        "stiffener_top_flange_gap_mm",
                        "stiffener_bottom_flange_gap_mm",
                        "flange_termination_geometry_verified",
                    ]
                },
            },
            {
                "if": {
                    "anyOf": [
                        {"required": ["external_normal_force_kn"]},
                        {"required": ["external_moment_knm"]},
                        {"required": ["external_parallel_force_kn"]},
                        {"required": ["force_eccentricity_mm"]},
                        {"required": ["capacity_factor"]},
                        {"required": ["external_actions_verified"]},
                    ]
                },
                "then": {
                    "required": [
                        "external_normal_force_kn",
                        "external_moment_knm",
                        "external_parallel_force_kn",
                        "force_eccentricity_mm",
                        "capacity_factor",
                        "external_actions_verified",
                    ]
                },
            },
            {
                "if": {
                    "required": ["external_parallel_force_kn"],
                    "properties": {
                        "external_parallel_force_kn": {"exclusiveMinimum": 0},
                    },
                },
                "then": {
                    "required": [
                        "load_bearing_stiffener_inputs",
                        "load_bearing_stiffener_attachment_inputs",
                    ]
                },
            },
            {
                "if": {
                    "required": ["external_parallel_force_kn"],
                    "properties": {
                        "external_parallel_force_kn": {"exclusiveMaximum": 0},
                    },
                },
                "then": {
                    "required": [
                        "load_bearing_stiffener_inputs",
                        "load_bearing_stiffener_attachment_inputs",
                    ]
                },
            },
            {
                "if": {
                    "anyOf": [
                        {
                            "required": ["external_normal_force_kn"],
                            "properties": {"external_normal_force_kn": {"exclusiveMinimum": 0}},
                        },
                        {
                            "required": ["external_moment_knm"],
                            "properties": {"external_moment_knm": {"not": {"const": 0}}},
                        },
                        {
                            "required": ["external_parallel_force_kn"],
                            "properties": {"external_parallel_force_kn": {"not": {"const": 0}}},
                        },
                    ]
                },
                "then": {
                    "not": {
                        "anyOf": [
                            {"required": ["web_connection_design_shear_capacity_kn_per_mm"]},
                            {"required": ["web_connection_capacity_verified"]},
                        ]
                    }
                },
                "else": {
                    "required": [
                        "web_connection_design_shear_capacity_kn_per_mm",
                        "web_connection_capacity_verified",
                    ]
                },
            },
        ]
    },
    "end_post_area": object_schema(
        {
            "operation": {"const": "end_post_area"},
            "end_post_required_under_5_15_2_2": {"const": True},
            **_END_POST_AREA_PROPERTIES,
        }
    ),
    "end_post_design": object_schema(
        {
            "operation": {"const": "end_post_design"},
            "end_post_required_under_5_15_2_2": {"const": True},
            **_END_POST_AREA_PROPERTIES,
            "design_bearing_force_kn": POSITIVE,
            "load_bearing_stiffener_inputs": _END_POST_STIFFENER_SCHEMA,
            "load_bearing_stiffener_attachment_inputs": _LOAD_BEARING_STIFFENER_ATTACHMENT_SCHEMA,
        }
    ),
    "end_panel_design": object_schema(
        {
            "operation": {"const": "end_panel_design"},
            "original_end_panel_spacing_mm": POSITIVE,
            "reduced_end_panel_spacing_mm": POSITIVE,
            "clear_web_depth_mm": POSITIVE,
            "panel_depth_mm": POSITIVE,
            "web_thickness_mm": POSITIVE,
            "web_area_mm2": POSITIVE,
            "web_yield_mpa": YIELD_STRESS,
            "design_shear_action_kn": NONNEGATIVE,
            "design_moment_action_knm": NONNEGATIVE,
            "section_moment_capacity_knm": POSITIVE,
            "stress_max_average_ratio": {"type": "number", "minimum": 1},
            "end_panel_geometry_verified": {"const": True},
        }
    ),
    "longitudinal_stiffener": object_schema(
        {
            "operation": {"const": "longitudinal_stiffener"},
            "web_depth_mm": POSITIVE,
            "web_thickness_mm": POSITIVE,
            "stiffener_area_mm2": POSITIVE,
            "stiffener_second_moment_mm4": POSITIVE,
            "location": {"enum": ["0.2_depth", "neutral_axis"]},
            "stiffener_continuous": {"type": "boolean"},
            "extends_between_transverse_stiffeners": {"type": "boolean"},
            "attached_to_transverse_stiffeners": {"type": "boolean"},
        },
        [
            "operation",
            "web_depth_mm",
            "web_thickness_mm",
            "stiffener_area_mm2",
            "stiffener_second_moment_mm4",
            "location",
        ],
    )
    | {
        "allOf": [
            {
                "if": {
                    "anyOf": [
                        {"required": ["stiffener_continuous"]},
                        {"required": ["extends_between_transverse_stiffeners"]},
                        {"required": ["attached_to_transverse_stiffeners"]},
                    ]
                },
                "then": {
                    "required": [
                        "stiffener_continuous",
                        "extends_between_transverse_stiffeners",
                        "attached_to_transverse_stiffeners",
                    ]
                },
            }
        ]
    },
    "rhs_bearing_bending": object_schema(
        {
            "operation": {"const": "rhs_bearing_bending"},
            "bearing_action_kn": NONNEGATIVE,
            "design_bearing_capacity_kn": POSITIVE,
            "bearing_capacity_5_13_2_verified": {"const": True},
            "bearing_capacity_5_13_2_reference": {"type": "string", "minLength": 1},
            "moment_action_knm": NONNEGATIVE,
            "design_moment_capacity_knm": POSITIVE,
            "moment_capacity_5_2_verified": {"const": True},
            "moment_capacity_5_2_reference": {"type": "string", "minLength": 1},
            "stiff_bearing_length_mm": POSITIVE,
            "section_width_mm": POSITIVE,
            "clear_web_depth_mm": POSITIVE,
            "web_thickness_mm": POSITIVE,
            "section_form_to_as_nzs_1163_verified": {"const": True},
            "section_form_evidence_reference": {"type": "string", "minLength": 1},
            "section_geometry_verified": {"const": True},
            "section_geometry_evidence_reference": {"type": "string", "minLength": 1},
        }
    ),
}
INPUT_SCHEMA = {"oneOf": list(SCHEMAS.values())}
OUTPUT_SCHEMA = {"type": "object"}


def buckling_alpha(slenderness, fy):
    """Clause 6.3.3 with kf=1 and alpha_b=0.5, prescribed for web/stiffener buckling."""
    ln = slenderness * sqrt(fy / 250)
    aa = 2100 * (ln - 13.5) / (ln**2 - 15.3 * ln + 2050)
    lam = ln + 0.5 * aa
    eta = max(0.0, 0.00326 * (lam - 13.5))
    q = (lam / 90) ** 2
    s = 1 + eta + q
    alpha = 2 / (s + sqrt(max(0.0, s * s - 4 * q)))
    return min(1.0, alpha)


def _load_bearing_buckling_values(
    *,
    stiffener_area_mm2,
    web_yield_mpa,
    stiffener_yield_mpa,
    web_thickness_mm,
    clear_web_depth_mm,
    panel_spacing_mm,
    radius_of_gyration_mm,
    available_web_width_left_mm,
    available_web_width_right_mm,
    both_flanges_rotation_restrained=None,
    effective_length_factor=None,
):
    width_limit = min(17.5 * web_thickness_mm / sqrt(web_yield_mpa / 250), panel_spacing_mm / 2)
    web_width = sum(
        min(width_limit, width)
        for width in (available_web_width_left_mm, available_web_width_right_mm)
    )
    effective_area = stiffener_area_mm2 + web_thickness_mm * web_width
    if effective_length_factor is None:
        length_factor = 0.7 if both_flanges_rotation_restrained else 1
    else:
        length_factor = effective_length_factor
    effective_length = length_factor * clear_web_depth_mm
    effective_yield = min(web_yield_mpa, stiffener_yield_mpa)
    alpha = buckling_alpha(effective_length / radius_of_gyration_mm, effective_yield)
    capacity = alpha * effective_area * effective_yield / 1000
    return {
        "web_width_limit_mm": width_limit,
        "effective_web_width_mm": web_width,
        "effective_area_mm2": effective_area,
        "effective_length_mm": effective_length,
        "effective_yield_mpa": effective_yield,
        "alpha_c": alpha,
        "nominal_buckling_capacity_kn": capacity,
    }


def _web_shear_buckling_values(
    *, web_yield_mpa, web_area_mm2, panel_depth_mm, web_thickness_mm, stiffener_spacing_mm
):
    slenderness = panel_depth_mm / web_thickness_mm * sqrt(web_yield_mpa / 250)
    aspect_ratio = stiffener_spacing_mm / panel_depth_mm
    elastic_reduction = (82 / slenderness) ** 2
    if aspect_ratio <= 3:
        aspect_factor = (
            0.75 / aspect_ratio**2 + 1 if aspect_ratio >= 1 else 1 / aspect_ratio**2 + 0.75
        )
        alpha_v = min(1, elastic_reduction * aspect_factor)
        buckling_clause = "5.11.5.2"
    else:
        alpha_v = min(1, elastic_reduction)
        buckling_clause = "5.11.5.1"
    web_yield_capacity = 0.6 * web_yield_mpa * web_area_mm2 / 1000
    nominal_buckling = min(web_yield_capacity, alpha_v * web_yield_capacity)
    nominal_shear = web_yield_capacity if slenderness <= 82 else nominal_buckling
    return {
        "web_slenderness": slenderness,
        "stiffener_spacing_to_panel_depth_ratio": aspect_ratio,
        "shear_buckling_coefficient": alpha_v,
        "nominal_web_shear_yield_capacity_kn": web_yield_capacity,
        "nominal_web_shear_capacity_kn": nominal_shear,
        "nominal_web_buckling_capacity_kn": nominal_buckling,
        "buckling_clause": buckling_clause,
    }


def _web_opening_shear_design(d):
    maximum_stress = d["maximum_design_shear_stress_mpa"]
    average_stress = d["average_design_shear_stress_mpa"]
    if maximum_stress < average_stress:
        raise ValueError("Maximum design shear stress must not be below the average stress.")
    reference = d["rational_elastic_analysis_reference"].strip()
    if not reference:
        raise ValueError("Rational elastic analysis reference must not be blank.")

    opening = run_webs(
        {
            "operation": "web_opening_geometry",
            "clear_web_depth_mm": d["clear_web_depth_mm"],
            "opening_internal_dimension_mm": d["opening_internal_dimension_mm"],
            "longitudinal_stiffeners_present": d["longitudinal_stiffeners_present"],
            "adjacent_openings_present": d["adjacent_openings_present"],
            "adjacent_opening_boundary_spacing_mm": d["adjacent_opening_boundary_spacing_mm"],
            **(
                {
                    "adjacent_opening_greatest_internal_dimension_mm": d[
                        "adjacent_opening_greatest_internal_dimension_mm"
                    ]
                }
                if "adjacent_opening_greatest_internal_dimension_mm" in d
                else {}
            ),
            "unstiffened_openings_at_cross_section": d["unstiffened_openings_at_cross_section"],
            "multiple_openings_rational_analysis_verified": d[
                "multiple_openings_rational_analysis_verified"
            ],
            "opening_geometry_verified": d["opening_geometry_verified"],
        }
    )
    shear_inputs = {
        "operation": "shear",
        "yield_strength_mpa": d["yield_strength_mpa"],
        "web_area_mm2": d["web_area_at_opening_mm2"],
        "panel_depth_mm": d["panel_depth_mm"],
        "web_thickness_mm": d["web_thickness_mm"],
        "stress_max_average_ratio": maximum_stress / average_stress,
        "action_kn": d["action_kn"],
        "moment_action_knm": d["moment_action_knm"],
        "section_moment_capacity_knm": d["section_moment_capacity_knm"],
    }
    if "stiffener_spacing_mm" in d:
        shear_inputs["stiffener_spacing_mm"] = d["stiffener_spacing_mm"]
    shear = run_members(shear_inputs)
    values = shear["values"]
    shear_capacity = values["shear_capacity_kn"]
    shear_design_capacity = 0.9 * shear_capacity
    interaction = dict(shear["checks"]["shear_bending"])
    interaction["clause"] = "5.12.3 shear and bending interaction"
    bending = dict(shear["checks"]["bending"])
    bending["clause"] = "5.12.3 section moment capacity"

    checks = list(opening["checks"])
    checks.extend(
        [
            {
                "clause": "web area at opening evidence",
                "satisfied": d["web_area_basis_verified"],
            },
            {
                "clause": "5.11.3 rational elastic analysis evidence",
                "satisfied": d["rational_elastic_analysis_verified"],
            },
            capacity_check("5.11.1", shear_capacity, d["action_kn"]),
            interaction,
            bending,
        ]
    )
    clauses = ["5.10.7", "5.11.1"]
    clauses.extend(clause["clause"] for clause in shear["trace"] if clause["clause"] not in clauses)
    return result(
        "web_opening_shear_design",
        clauses,
        {
            **opening["values"],
            "web_area_at_opening_mm2": d["web_area_at_opening_mm2"],
            "web_area_basis_verified": d["web_area_basis_verified"],
            "stress_max_average_ratio": maximum_stress / average_stress,
            "maximum_design_shear_stress_mpa": maximum_stress,
            "average_design_shear_stress_mpa": average_stress,
            "rational_elastic_analysis_reference": reference,
            "rational_elastic_analysis_verified": d["rational_elastic_analysis_verified"],
            "web_slenderness": values["web_slenderness"],
            "shear_buckling_reduction": values["buckling_reduction"],
            "nominal_web_shear_yield_capacity_kn": values["shear_yield_capacity_kn"],
            "nominal_web_shear_capacity_kn": shear_capacity,
            "nominal_web_shear_capacity_with_bending_kn": values["shear_bending_capacity_kn"],
            "design_web_shear_capacity_kn": shear_design_capacity,
            "design_web_shear_capacity_with_bending_kn": interaction["design_capacity"],
            "moment_to_design_capacity_ratio": d["moment_action_knm"]
            / (0.9 * d["section_moment_capacity_knm"]),
        },
        checks,
        [
            "The rational elastic analysis and web area at the opening are supplied, "
            "referenced and evidence-gated inputs; this operation does not perform or "
            "authenticate that analysis.",
            "Only unstiffened openings within Clause 5.10.7 geometry are checked. "
            "Local opening bending and bearing resistance, stiffened openings and "
            "castellated members require separate analysis.",
            "The shear and bending resistance calculation uses the supplied web area "
            "and panel geometry; verify these values represent the governing opening section.",
        ],
    )


def run_webs(inputs):
    d = validate(inputs, INPUT_SCHEMA)
    op = d["operation"]
    if op == "web_opening_shear_design":
        return _web_opening_shear_design(d)
    if op == "web_minimum_thickness":
        depth, fy, actual = (
            d["clear_web_depth_mm"],
            d["web_yield_mpa"],
            d["web_thickness_mm"],
        )
        factor = sqrt(fy / 250)
        if d["design_case"] == "unstiffened":
            denominator = 90 if d["edge_condition"] == "one_longitudinal_edge_free" else 180
            required = depth / denominator * factor
            clauses = ["5.10.1"]
            details = {"edge_condition": d["edge_condition"]}
        elif d["design_case"] == "transversely_stiffened":
            spacing = d["stiffener_spacing_mm"]
            panel_depth = d["greatest_panel_depth_mm"]
            if panel_depth > depth:
                raise ValueError("Greatest panel depth must not exceed the clear web depth.")
            ratio = spacing / depth
            if spacing / panel_depth > 3:
                required = depth / 180 * factor
                clauses = ["5.10.1", "5.10.4"]
                details = {
                    "stiffener_spacing_to_panel_depth_ratio": spacing / panel_depth,
                    "web_treated_as_unstiffened": True,
                }
            else:
                if ratio > 3:
                    raise ValueError(
                        "Transverse stiffener spacing is outside Clause 5.10.4 limits."
                    )
                if ratio <= 0.74:
                    required = depth / 270 * factor
                elif ratio < 1:
                    required = spacing / 200 * factor
                else:
                    required = depth / 200 * factor
                clauses = ["5.10.4"]
                details = {
                    "stiffener_spacing_to_web_depth_ratio": ratio,
                    "stiffener_spacing_to_panel_depth_ratio": spacing / panel_depth,
                    "web_treated_as_unstiffened": False,
                }
        elif d["design_case"] == "longitudinal_and_transverse":
            spacing = d["stiffener_spacing_mm"]
            ratio = spacing / depth
            if ratio > 2.4:
                raise ValueError(
                    "Longitudinal/transverse stiffener spacing exceeds Clause 5.10.5 limits."
                )
            if ratio < 0.74:
                required = depth / 340 * factor
            elif ratio < 1:
                required = spacing / 250 * factor
            else:
                required = depth / 250 * factor
            if d["neutral_axis_stiffener_set_present"]:
                if ratio > 1.5:
                    raise ValueError(
                        "The Clause 5.10.5 neutral-axis thickness equation applies only "
                        "when s/d1 is no greater than 1.5."
                    )
                required = max(required, depth / 400 * factor)
            clauses = ["5.10.5"]
            details = {
                "stiffener_spacing_to_web_depth_ratio": ratio,
                "compression_flange_stiffener_target_distance_mm": 0.2 * d["d2_mm"],
                "neutral_axis_stiffener_set_present": d["neutral_axis_stiffener_set_present"],
            }
        else:
            required = depth / 82 * factor
            trigger = (
                d["bearing_or_shear_within_half_depth_of_hinge_verified"]
                and d["hinge_zone_load_kn"] > 0.1 * d["design_web_shear_yield_capacity_kn"]
            )
            stiffener_condition = not trigger or (
                d["load_bearing_stiffeners_provided"]
                and d["stiffeners_within_half_depth_verified"]
                and d["stiffener_design_5_14_verified"]
            )
            clauses = ["5.10.6"]
            details = {"hinge_zone_stiffeners_required": trigger}
            flat_plate_checks = []
            for index, plate in enumerate(d.get("flat_stiffener_plates", []), start=1):
                slenderness = (
                    plate["clear_outstand_mm"]
                    / plate["thickness_mm"]
                    * sqrt(plate["yield_mpa"] / 250)
                )
                plasticity_limit = {
                    "SR": 10,
                    "HR": 9,
                    "CF": 8,
                    "LW": 8,
                    "HW": 8,
                }[plate["residual_stress_category"]]
                flat_plate_checks.append(
                    {
                        "plate_number": index,
                        "slenderness": slenderness,
                        "plasticity_limit": plasticity_limit,
                        "residual_stress_category": plate["residual_stress_category"],
                        "satisfied": slenderness < plasticity_limit,
                    }
                )
            if flat_plate_checks:
                details["flat_stiffener_plate_checks"] = flat_plate_checks
                clauses.append("5.2.2")

        thickness_clause = clauses[0]
        clauses.insert(0, "5.9.3")
        thickness_check = {
            "clause": thickness_clause,
            "required_thickness_mm": required,
            "provided_thickness_mm": actual,
            "satisfied": actual >= required,
        }
        checks = [thickness_check]
        if d["design_case"] == "plastic_hinge":
            checks.append(
                {
                    "clause": "5.10.6 load-bearing stiffener trigger",
                    "satisfied": stiffener_condition,
                }
            )
            if "flat_stiffener_plate_checks" in details:
                flat_plate_checks = details["flat_stiffener_plate_checks"]
                checks.append(
                    {
                        "clause": (
                            "5.10.6 flat-plate stiffener plasticity classification under 5.2.2"
                        ),
                        "plate_checks": flat_plate_checks,
                        "satisfied": all(plate["satisfied"] for plate in flat_plate_checks),
                    }
                )
        return result(
            op,
            clauses,
            {
                "design_case": d["design_case"],
                "required_web_thickness_mm": required,
                "provided_web_thickness_mm": actual,
                "web_thickness_adequate": actual >= required,
                **details,
            },
            checks,
            [
                "This is a web thickness/arrangement check only; verify shear, bearing, "
                "stiffener resistance and load transfer under the applicable clauses.",
                "A lower thickness justified by rational analysis under 5.10.1 requires "
                "a separate verified analysis.",
            ],
        )
    if op == "web_opening_geometry":
        dimension, depth = d["opening_internal_dimension_mm"], d["clear_web_depth_mm"]
        ratio = dimension / depth
        permitted = 0.33 if d["longitudinal_stiffeners_present"] else 0.10
        adjacent_dimension = d.get("adjacent_opening_greatest_internal_dimension_mm")
        stiffener_condition = (
            d["unstiffened_openings_at_cross_section"] <= 1
            or d["multiple_openings_rational_analysis_verified"]
        )
        checks = [
            {
                "clause": "5.10.7(b)" if d["longitudinal_stiffeners_present"] else "5.10.7(a)",
                "opening_dimension_to_web_depth_ratio": ratio,
                "permitted_ratio": permitted,
                "satisfied": ratio <= permitted,
            },
            {
                "clause": "5.10.7 multiple openings at one cross-section",
                "satisfied": stiffener_condition,
            },
        ]
        if d["adjacent_openings_present"]:
            has_adjacent_dimension = adjacent_dimension is not None
            spacing_dimension = max(dimension, adjacent_dimension or dimension)
            required_spacing = 3 * spacing_dimension
            checks.append(
                {
                    "clause": "5.10.7 adjacent opening greatest internal dimension",
                    "current_opening_dimension_mm": dimension,
                    "adjacent_opening_greatest_internal_dimension_mm": adjacent_dimension,
                    "satisfied": has_adjacent_dimension,
                }
            )
            checks.append(
                {
                    "clause": "5.10.7 adjacent opening spacing",
                    "required_boundary_spacing_mm": required_spacing,
                    "provided_boundary_spacing_mm": d["adjacent_opening_boundary_spacing_mm"],
                    "spacing_reference_dimension_mm": spacing_dimension,
                    "satisfied": has_adjacent_dimension
                    and d["adjacent_opening_boundary_spacing_mm"] >= required_spacing,
                }
            )
        return result(
            op,
            ["5.10.7"],
            {
                "opening_dimension_to_web_depth_ratio": ratio,
                "permitted_ratio": permitted,
                "required_adjacent_opening_spacing_mm": (
                    3 * max(dimension, adjacent_dimension or dimension)
                    if d["adjacent_openings_present"]
                    else None
                ),
                "adjacent_opening_greatest_internal_dimension_mm": adjacent_dimension,
            },
            checks,
            [
                "Applies only to unstiffened web openings meeting the geometric limits. "
                "Stiffened openings and castellated members require rational analysis.",
                "For adjacent openings of different sizes, use the greater internal "
                "dimension when checking their boundary spacing.",
                "This geometry check does not calculate the member's reduced section or "
                "web capacity at an opening.",
            ],
        )
    if op == "load_bearing_stiffener_requirement":
        force = d["design_compressive_bearing_force_kn"]
        web_capacity = d["design_web_bearing_capacity_kn"]
        required_by_bearing = force > web_capacity
        required_by_end_post = d["end_post_required_under_5_15_2_2"]
        required = required_by_bearing or required_by_end_post
        return result(
            op,
            ["5.10.2"],
            {
                "stiffeners_required": required,
                "required_by_web_bearing_capacity": required_by_bearing,
                "required_to_form_end_post": required_by_end_post,
                "design_compressive_bearing_force_kn": force,
                "design_web_bearing_capacity_kn": web_capacity,
            },
            [
                {
                    "clause": "5.10.2 load-bearing stiffener provision",
                    "satisfied": not required or d["load_bearing_stiffeners_provided"],
                }
            ],
            [
                "Use the design bearing capacity of the web alone from Clause 5.13.2; "
                "the end-post requirement under Clause 5.15.2.2 is an assessed input.",
                "This trigger does not calculate load-bearing stiffener resistance, "
                "detailing or force transfer under Clause 5.14.",
            ],
        )
    if op == "web_side_reinforcement":
        share = d["design_shear_share_kn"]
        plate_capacity = d["side_plate_design_shear_capacity_kn"]
        web_transfer = d["fastener_design_shear_capacity_to_web_kn"]
        flange_transfer = d["fastener_design_shear_capacity_to_flanges_kn"]
        available = min(plate_capacity, web_transfer, flange_transfer)
        return result(
            op,
            ["5.10.3"],
            {
                "design_shear_share_kn": share,
                "maximum_supported_shear_share_kn": available,
                "side_plate_design_shear_capacity_kn": plate_capacity,
                "fastener_design_shear_capacity_to_web_kn": web_transfer,
                "fastener_design_shear_capacity_to_flanges_kn": flange_transfer,
            },
            [
                {
                    "clause": "5.10.3 side-plate shear resistance",
                    "satisfied": share <= plate_capacity,
                },
                {
                    "clause": "5.10.3 fastener transfer to web",
                    "satisfied": share <= web_transfer,
                },
                {
                    "clause": "5.10.3 fastener transfer to flanges",
                    "satisfied": share <= flange_transfer,
                },
                {
                    "clause": "5.10.3 symmetry effects",
                    "satisfied": d["symmetry_effects_accounted"],
                },
            ],
            [
                "Enter the design shear assigned to the side plates after accounting "
                "for any lack of symmetry.",
                "Plate and fastener design capacities are supplied inputs; their "
                "resistance and connection design are not calculated here.",
            ],
        )
    if op == "load_bearing_stiffener_attachment":
        bearing_force = d["design_bearing_force_kn"]
        web_share = d["design_force_share_to_web_kn"]
        if web_share > bearing_force:
            raise ValueError(
                "The force share transferred to the web cannot exceed the applied force."
            )
        web_capacity = d["web_connection_design_capacity_kn"]
        tight_fit = d["tight_uniform_bearing_against_loaded_flange_verified"]
        flange_capacity = d.get("flange_to_stiffener_connection_design_capacity_kn")
        flange_transfer_ok = tight_fit or (
            flange_capacity is not None and flange_capacity >= bearing_force
        )
        both_flanges_ok = not d["concentrated_force_directly_over_support"] or d.get(
            "both_flanges_fitted_or_connected_verified", False
        )
        return result(
            op,
            ["5.14.4"],
            {
                "maximum_supported_web_force_share_kn": web_capacity,
                "design_force_share_to_web_kn": web_share,
                "flange_to_stiffener_connection_capacity_kn": flange_capacity,
            },
            [
                {
                    "clause": "5.14.4 tight flange fit or concentrated-force connection",
                    "satisfied": flange_transfer_ok,
                },
                {
                    "clause": "5.14.4 both-flange provision at support",
                    "satisfied": both_flanges_ok,
                },
                {
                    "clause": "5.14.4 connection force transfer to web",
                    "design_capacity_kn": web_capacity,
                    "action_kn": web_share,
                    "utilisation": web_share / web_capacity,
                    "satisfied": web_share <= web_capacity,
                },
            ],
            [
                "Weld and bolt design capacities are supplied from the applicable Clause 9 checks.",
                "Verify the stated flange fit and connection arrangement against actual details.",
            ],
        )
    if op == "web_bearing":
        t, fy, depth = d["web_thickness_mm"], d["web_yield_mpa"], d["clear_web_depth_mm"]
        if d["section_type"] == "i_or_channel":
            manual_widths = (
                "bearing_width_at_flange_mm" in d,
                "bearing_width_at_neutral_axis_mm" in d,
            )
            geometry_inputs = (
                "flange_thickness_mm" in d,
                "distance_flange_to_neutral_axis_mm" in d,
                "bearing_geometry_verified" in d,
            )
            if all(manual_widths) and not any(geometry_inputs):
                bbf, bb = d["bearing_width_at_flange_mm"], d["bearing_width_at_neutral_axis_mm"]
                geometry_check = None
            elif not any(manual_widths) and all(geometry_inputs):
                tf = d["flange_thickness_mm"]
                distance_to_na = d["distance_flange_to_neutral_axis_mm"]
                if "stiff_bearing_length_mm" not in d:
                    raise ValueError("Geometric dispersion requires stiff_bearing_length_mm.")
                if distance_to_na > depth:
                    raise ValueError(
                        "Distance to the neutral axis must not exceed the clear web depth."
                    )
                bbf = d["stiff_bearing_length_mm"] + 5 * tf
                bb = bbf + 2 * distance_to_na
                geometry_check = {
                    "clause": "5.13.1 bearing-dispersion geometry verified",
                    "satisfied": d["bearing_geometry_verified"],
                }
            else:
                raise ValueError(
                    "I/channel bearing requires both assessed widths or the complete "
                    "Clause 5.13.1 geometry input set."
                )
            if any(
                name in d
                for name in [
                    "outside_radius_mm",
                    "distance_to_member_end_mm",
                ]
            ):
                raise ValueError("Hollow-section inputs cannot be used with an I/channel section.")
            if bb < bbf:
                raise ValueError("Neutral-axis dispersed width must not be below flange width.")
            yield_capacity = 1.25 * bbf * t * fy / 1000
            geometric_slenderness = (2.5 if d["restrained_flange_count"] == 2 else 5) * depth / t
            ap = None
        else:
            if d["restrained_flange_count"] != 2:
                raise ValueError(
                    "RHS/SHS bearing requires the hollow section's integral flange restraint."
                )
            required = ["outside_radius_mm", "stiff_bearing_length_mm", "distance_to_member_end_mm"]
            if any(name not in d for name in required):
                raise ValueError(
                    "RHS/SHS bearing requires radius, bearing length and end distance."
                )
            if any(
                name in d
                for name in ["bearing_width_at_flange_mm", "bearing_width_at_neutral_axis_mm"]
            ):
                raise ValueError("RHS/SHS dispersed widths are derived, not supplied.")
            radius, bs, bd = (d[name] for name in required)
            if radius < t or depth / t <= 1:
                raise ValueError("Invalid hollow-section radius or flat web depth.")
            ks, kv = 2 * radius / t - 1, depth / t
            interior = bd >= 1.5 * depth
            if interior:
                apm = 1 / ks + 0.5 / kv
                ap = 0.5 / ks * (1 + (1 - apm**2) * (1 + ks / kv - (1 - apm**2) * 0.25 / kv**2))
                bb = bs + 5 * radius + depth
                geometric_slenderness = 3.5 * depth / t
            else:
                ap = sqrt(2 + ks**2) - ks
                bb = bs + 2.5 * radius + depth / 2
                geometric_slenderness = 3.8 * depth / t
            if ap <= 0:
                raise ValueError("Hollow-section bearing coefficient outside the supported domain.")
            yield_capacity = 2 * bb * t * fy * ap / 1000
        alpha = buckling_alpha(geometric_slenderness, fy)
        buckling_capacity = alpha * t * bb * fy / 1000
        nominal = min(yield_capacity, buckling_capacity)
        return result(
            op,
            ["5.13.1", "5.13.2", "5.13.3", "5.13.4"],
            {
                "bearing_yield_kn": yield_capacity,
                "bearing_buckling_kn": buckling_capacity,
                "alpha_c": alpha,
                "alpha_p": ap,
                "dispersed_width_mm": bb,
                "geometric_slenderness": geometric_slenderness,
                **(
                    {
                        "bearing_width_at_flange_mm": bbf,
                        "bearing_width_at_neutral_axis_mm": bb,
                        "dispersion_method": "clause_5_13_1_geometry",
                    }
                    if d["section_type"] == "i_or_channel"
                    else {}
                ),
            },
            [
                capacity_check("5.13.2", nominal, d["bearing_action_kn"]),
                *(
                    [geometry_check]
                    if d["section_type"] == "i_or_channel" and geometry_check
                    else []
                ),
            ],
            [
                "No transverse stiffeners; limit end widths to available web (Figure 5.13.1.1).",
                "Clause 5.13.1 automatic dispersion uses b_bf = b_s + 5 t_f and adds "
                "twice the flange-to-neutral-axis distance; confirm the figure geometry applies.",
                "RHS/SHS to AS/NZS 1163; combined bearing/bending needs separate 5.13.5 check.",
            ],
        )
    if op == "rhs_bearing_bending":
        evidence_fields = (
            "bearing_capacity_5_13_2_reference",
            "moment_capacity_5_2_reference",
            "section_form_evidence_reference",
            "section_geometry_evidence_reference",
        )
        for field in evidence_fields:
            if not d[field].strip():
                raise ValueError(f"{field} must not be blank.")
        rr = d["bearing_action_kn"] / d["design_bearing_capacity_kn"]
        mr = d["moment_action_knm"] / d["design_moment_capacity_knm"]
        width_ratio = d["stiff_bearing_length_mm"] / d["section_width_mm"]
        depth_thickness_ratio = d["clear_web_depth_mm"] / d["web_thickness_mm"]
        wide = width_ratio >= 1.0 and depth_thickness_ratio <= 30.0
        value, limit = (1.2 * rr + mr, 1.5) if wide else (0.8 * rr + mr, 1.0)
        route = "wide_bearing_compact_web" if wide else "otherwise"
        return result(
            op,
            ["5.2", "5.13.2", "5.13.5"],
            {
                "bearing_utilisation": rr,
                "moment_utilisation": mr,
                "bearing_length_to_section_width_ratio": width_ratio,
                "clear_web_depth_to_thickness_ratio": depth_thickness_ratio,
                "interaction": value,
                "limit": limit,
                "equation_route": route,
                "design_bearing_capacity_kn": d["design_bearing_capacity_kn"],
                "design_moment_capacity_knm": d["design_moment_capacity_knm"],
                "bearing_capacity_5_13_2_reference": d["bearing_capacity_5_13_2_reference"].strip(),
                "moment_capacity_5_2_reference": d["moment_capacity_5_2_reference"].strip(),
                "section_form_evidence_reference": d["section_form_evidence_reference"].strip(),
                "section_geometry_evidence_reference": d[
                    "section_geometry_evidence_reference"
                ].strip(),
            },
            [
                {
                    "clause": "5.13.5 section form, geometry and capacity evidence",
                    "satisfied": True,
                },
                {
                    "clause": "5.13.2 bearing resistance",
                    "satisfied": rr <= 1,
                    "utilisation": rr,
                },
                {
                    "clause": "5.2 bending resistance",
                    "satisfied": mr <= 1,
                    "utilisation": mr,
                },
                {
                    "clause": "5.13.5 combined bearing and bending",
                    "satisfied": rr <= 1 and mr <= 1 and value <= limit,
                    "utilisation": max(rr, mr, value / limit),
                },
            ],
            [
                "AS/NZS 1163 RHS/SHS only. The supplied design capacities must already "
                "include their capacity factors; this operation does not calculate or "
                "authenticate the Clause 5.2 or 5.13.2 capacities.",
            ],
        )
    if op == "load_bearing_stiffener":
        fy = min(d["web_yield_mpa"], d["stiffener_yield_mpa"])
        t, depth = d["web_thickness_mm"], d["clear_web_depth_mm"]
        if d["contact_stiffener_area_mm2"] > d["stiffener_area_mm2"]:
            raise ValueError("Contact stiffener area must not exceed the section area.")
        buckling_values = _load_bearing_buckling_values(
            stiffener_area_mm2=d["stiffener_area_mm2"],
            web_yield_mpa=d["web_yield_mpa"],
            stiffener_yield_mpa=d["stiffener_yield_mpa"],
            web_thickness_mm=t,
            clear_web_depth_mm=depth,
            panel_spacing_mm=d["panel_spacing_mm"],
            radius_of_gyration_mm=d["radius_of_gyration_mm"],
            both_flanges_rotation_restrained=d["both_flanges_rotation_restrained"],
            available_web_width_left_mm=d["available_web_width_left_mm"],
            available_web_width_right_mm=d["available_web_width_right_mm"],
        )
        area = buckling_values["effective_area_mm2"]
        length = buckling_values["effective_length_mm"]
        alpha = buckling_values["alpha_c"]
        yield_capacity = (
            d["web_bearing_yield_kn"]
            + d["contact_stiffener_area_mm2"] * d["stiffener_yield_mpa"] / 1000
        )
        buckling_capacity = buckling_values["nominal_buckling_capacity_kn"]
        outstand_limit = 15 * d["stiffener_thickness_mm"] / sqrt(d["stiffener_yield_mpa"] / 250)
        outstand_ok = (
            d["outer_edge_continuously_stiffened"] or d["stiffener_outstand_mm"] <= outstand_limit
        )
        checks = [
            capacity_check("5.14.1", yield_capacity, d["bearing_action_kn"]),
            capacity_check("5.14.2", buckling_capacity, d["bearing_action_kn"]),
            {"clause": "5.14.3", "satisfied": outstand_ok},
        ]
        clauses = ["5.14.1", "5.14.2", "5.14.3"]
        values = {
            "effective_area_mm2": area,
            "effective_length_mm": length,
            "alpha_c": alpha,
            "web_width_limit_mm": buckling_values["web_width_limit_mm"],
            "effective_web_width_mm": buckling_values["effective_web_width_mm"],
            "effective_yield_mpa": buckling_values["effective_yield_mpa"],
            "bearing_yield_kn": yield_capacity,
            "bearing_buckling_kn": buckling_capacity,
            "outstand_limit_mm": outstand_limit,
        }
        if d.get("torsional_end_restraint_required", False):
            slenderness = length / d["radius_of_gyration_mm"]
            alpha_t_raw = 230 / slenderness - 0.60
            alpha_t = min(4, max(0, alpha_t_raw))
            required_inertia = (
                (alpha_t / 1000)
                * d["critical_flange_centroid_spacing_mm"] ** 3
                * d["critical_flange_thickness_mm"]
                * d["bearing_action_kn"]
                / d["total_design_load_between_supports_kn"]
            )
            supplied_inertia = d["stiffener_pair_second_moment_about_web_centerline_mm4"]
            values.update(
                {
                    "stiffener_slenderness": slenderness,
                    "torsional_restraint_factor_raw": alpha_t_raw,
                    "torsional_restraint_factor": alpha_t,
                    "required_stiffener_pair_second_moment_mm4": required_inertia,
                }
            )
            checks.append(
                {
                    "clause": "5.14.5 torsional end restraint",
                    "satisfied": supplied_inertia >= required_inertia,
                }
            )
            clauses.append("5.14.5")
        return result(
            op,
            clauses,
            values,
            checks,
            [
                "Effective-section buckling uses the lower web/stiffener yield stress.",
                "Radius must be calculated for the effective section parallel to web.",
                "Check fitting, fastener force transfer and torsional restraint under 5.14.4/5.",
            ],
        )
    if op == "end_post_area":
        residual_shear_kn = max(
            0,
            d["design_shear_action_kn"] / d["capacity_factor"]
            - d["shear_buckling_coefficient"] * d["nominal_web_shear_yield_capacity_kn"],
        )
        required_area = (
            d["clear_web_depth_mm"]
            * residual_shear_kn
            * 1000
            / (8 * d["end_plate_to_load_bearing_stiffener_distance_mm"] * d["end_plate_yield_mpa"])
        )
        return result(
            op,
            ["5.15.9"],
            {
                "residual_panel_shear_kn": residual_shear_kn,
                "minimum_end_plate_area_mm2": required_area,
                "provided_end_plate_area_mm2": d["end_plate_area_mm2"],
            },
            [
                {
                    "clause": "5.15.9 end-plate minimum area",
                    "satisfied": d["end_plate_area_mm2"] >= required_area,
                }
            ],
            [
                "The end post must include the load-bearing stiffener required by 5.15.2.2.",
                "Design the load-bearing stiffener under 5.14 and verify the end-plate "
                "connection and geometry separately.",
            ],
        )
    if op == "end_post_design":
        load_bearing_inputs = d["load_bearing_stiffener_inputs"]
        if load_bearing_inputs["clear_web_depth_mm"] != d["clear_web_depth_mm"]:
            raise ValueError("End-post and load-bearing stiffener clear web depths must match.")
        load_bearing = run_webs(
            {
                "operation": "load_bearing_stiffener",
                **{
                    key: value
                    for key, value in load_bearing_inputs.items()
                    if key != "load_bearing_stiffener_not_smaller_than_end_plate_verified"
                },
                "bearing_action_kn": d["design_bearing_force_kn"],
            }
        )
        attachment = run_webs(
            {
                "operation": "load_bearing_stiffener_attachment",
                **d["load_bearing_stiffener_attachment_inputs"],
                "design_bearing_force_kn": d["design_bearing_force_kn"],
            }
        )
        end_plate = run_webs(
            {
                "operation": "end_post_area",
                "end_post_required_under_5_15_2_2": True,
                **{key: d[key] for key in _END_POST_AREA_PROPERTIES},
            }
        )
        stiffener_area = load_bearing_inputs["stiffener_area_mm2"]
        end_plate_area = d["end_plate_area_mm2"]

        def trace_checks(label, calculation):
            return [
                {**check, "clause": f"{label}: {check['clause']}"}
                for check in calculation["checks"]
            ]

        checks = [
            *trace_checks("5.14 end-post stiffener", load_bearing),
            *trace_checks("5.14 end-post attachment", attachment),
            *trace_checks("5.15.9 end plate", end_plate),
            {
                "clause": "5.15.9 load-bearing stiffener verified no smaller than end plate",
                "end_plate_area_mm2": end_plate_area,
                "stiffener_area_mm2": stiffener_area,
                "satisfied": load_bearing_inputs[
                    "load_bearing_stiffener_not_smaller_than_end_plate_verified"
                ],
            },
        ]
        clauses = [
            "5.15.2.2",
            *load_bearing["clauses"],
            *attachment["clauses"],
            *end_plate["clauses"],
        ]
        return result(
            op,
            list(dict.fromkeys(clauses)),
            {
                "design_bearing_force_kn": d["design_bearing_force_kn"],
                "load_bearing_stiffener_area_mm2": stiffener_area,
                "load_bearing_stiffener_not_smaller_than_end_plate_verified": load_bearing_inputs[
                    "load_bearing_stiffener_not_smaller_than_end_plate_verified"
                ],
                "end_plate_area_mm2": end_plate_area,
                "clause_5_14_load_bearing_stiffener": load_bearing,
                "clause_5_14_load_bearing_stiffener_attachment": attachment,
                "clause_5_15_9_end_plate": end_plate,
                **end_plate["values"],
            },
            checks,
            [
                "Supply the governing end-post bearing reaction and verify the web bearing yield "
                "resistance, effective section, restraints and connection capacities against "
                "the member and support details.",
                "Supply Clause 5.14.5 restraint inputs when the load-bearing stiffener pair is "
                "the sole torsional end restraint.",
                "Design the end-plate-to-stiffener and end-post-to-member connections and verify "
                "end-plate geometry separately under Section 9.",
            ],
        )
    if op == "transverse_stiffener":
        depth, spacing, t = d["clear_web_depth_mm"], d["panel_spacing_mm"], d["web_thickness_mm"]
        if not d["longitudinal_stiffeners_present"] and d["web_panel_depth_mm"] != depth:
            raise ValueError(
                "Without longitudinal stiffeners, web_panel_depth_mm must equal clear_web_depth_mm."
            )
        spacing_check_inputs = {
            "operation": "web_minimum_thickness",
            "clear_web_depth_mm": depth,
            "web_thickness_mm": t,
            "web_yield_mpa": d["web_yield_mpa"],
            "stiffener_spacing_mm": spacing,
            "stiffener_layout_verified": d["stiffener_layout_verified"],
        }
        if d["longitudinal_stiffeners_present"]:
            spacing_check_inputs.update(
                {
                    "design_case": "longitudinal_and_transverse",
                    "d2_mm": d["longitudinal_stiffener_d2_mm"],
                    "neutral_axis_stiffener_set_present": d["neutral_axis_stiffener_set_present"],
                }
            )
        else:
            spacing_check_inputs.update(
                {
                    "design_case": "transversely_stiffened",
                    "greatest_panel_depth_mm": d["web_panel_depth_mm"],
                }
            )
        web_thickness_check = run_webs(spacing_check_inputs)
        if "stiffener_buckling_geometry" in d:
            web_buckling = _web_shear_buckling_values(
                web_yield_mpa=d["web_yield_mpa"],
                web_area_mm2=d["web_area_mm2"],
                panel_depth_mm=d["web_panel_depth_mm"],
                web_thickness_mm=t,
                stiffener_spacing_mm=spacing,
            )
            stiffener_geometry = d["stiffener_buckling_geometry"]
            stiffener_buckling = _load_bearing_buckling_values(
                stiffener_area_mm2=d["stiffener_area_mm2"],
                web_yield_mpa=d["web_yield_mpa"],
                stiffener_yield_mpa=d["stiffener_yield_mpa"],
                web_thickness_mm=t,
                clear_web_depth_mm=depth,
                panel_spacing_mm=spacing,
                radius_of_gyration_mm=stiffener_geometry["radius_of_gyration_mm"],
                available_web_width_left_mm=stiffener_geometry["available_web_width_left_mm"],
                available_web_width_right_mm=stiffener_geometry["available_web_width_right_mm"],
                effective_length_factor=1.0,
            )
            shear_buckling_coefficient = web_buckling["shear_buckling_coefficient"]
            nominal_web_shear = web_buckling["nominal_web_shear_capacity_kn"]
            nominal_web_buckling = web_buckling["nominal_web_buckling_capacity_kn"]
            nominal_stiffener_buckling = stiffener_buckling["nominal_buckling_capacity_kn"]
            capacity_basis = {
                "method": "calculated_from_geometry",
                "clause_5_11": web_buckling,
                "clause_5_14_2": stiffener_buckling,
                "alpha_d": 1.0,
                "alpha_f": 1.0,
            }
            derived_clauses = ["5.11.2", web_buckling["buckling_clause"], "5.14.2"]
        else:
            shear_buckling_coefficient = d["shear_buckling_coefficient"]
            nominal_web_shear = d["nominal_web_shear_kn"]
            nominal_web_buckling = d["nominal_web_buckling_no_tension_field_kn"]
            nominal_stiffener_buckling = d["nominal_stiffener_buckling_kn"]
            capacity_basis = {"method": "supplied_capacities"}
            derived_clauses = []
        ratio = spacing / d["web_panel_depth_mm"]
        gamma = {"pair": 1, "single_angle": 1.8, "single_plate": 2.4}[d["stiffener_configuration"]]
        area_min = (
            0.5
            * gamma
            * d["web_area_mm2"]
            * (1 - shear_buckling_coefficient)
            * (d["shear_action_kn"] / (0.9 * nominal_web_shear))
            * (ratio / (sqrt(1 + ratio**2) * (sqrt(1 + ratio**2) + ratio)))
        )
        inertia_min = (
            0.75 * depth * t**3 if spacing / depth < sqrt(2) else 1.5 * depth**3 * t**3 / spacing**2
        )
        outstand_limit = 15 * d["stiffener_thickness_mm"] / sqrt(d["stiffener_yield_mpa"] / 250)
        shear_per_length = 0.0008 * t * t * d["web_yield_mpa"] / d["stiffener_outstand_mm"]
        nominal = nominal_stiffener_buckling + nominal_web_buckling
        clauses = [
            "5.15.2.1",
            *web_thickness_check["clauses"],
            *derived_clauses,
            "5.15.3",
            "5.15.4",
            "5.15.5",
            "5.15.6",
        ]
        values = {
            "clause_5_15_2_1_web_thickness_check": web_thickness_check,
            "minimum_area_mm2": area_min,
            "minimum_second_moment_mm4": inertia_min,
            "outstand_limit_mm": outstand_limit,
            "connection_design_shear_kn_per_mm": shear_per_length,
            "shear_buckling_coefficient": shear_buckling_coefficient,
            "nominal_web_shear_capacity_kn": nominal_web_shear,
            "nominal_web_buckling_no_tension_field_kn": nominal_web_buckling,
            "nominal_stiffener_buckling_kn": nominal_stiffener_buckling,
            "capacity_basis": capacity_basis,
        }
        checks = [
            {
                "clause": "5.15.2.1 interior panel spacing via 5.10.4/5.10.5",
                "required_web_thickness_mm": web_thickness_check["values"][
                    "required_web_thickness_mm"
                ],
                "provided_web_thickness_mm": t,
                "satisfied": web_thickness_check["checked_conditions_satisfied"],
            },
            {"clause": "5.15.3", "satisfied": d["stiffener_area_mm2"] >= area_min},
            {"clause": "5.15.5", "satisfied": d["stiffener_second_moment_mm4"] >= inertia_min},
            {
                "clause": "5.15.6",
                "satisfied": d["outer_edge_continuously_stiffened"]
                or d["stiffener_outstand_mm"] <= outstand_limit,
            },
            capacity_check("5.15.4", nominal, d["shear_action_kn"]),
        ]
        has_external_actions = "external_normal_force_kn" in d and any(
            d[field] != 0
            for field in (
                "external_normal_force_kn",
                "external_moment_knm",
                "external_parallel_force_kn",
            )
        )
        if not has_external_actions:
            connection_capacity = d["web_connection_design_shear_capacity_kn_per_mm"]
            connection_verified = d["web_connection_capacity_verified"]
            values.update(
                {
                    "web_connection_design_shear_capacity_kn_per_mm": connection_capacity,
                    "web_connection_capacity_verified": connection_verified,
                }
            )
            clauses.append("5.15.8")
            checks.append(
                {
                    "clause": "5.15.8 web-connection shear per unit length",
                    "required_kn_per_mm": shear_per_length,
                    "provided_design_capacity_kn_per_mm": connection_capacity,
                    "utilisation": shear_per_length / connection_capacity,
                    "satisfied": connection_verified and connection_capacity >= shear_per_length,
                }
            )
        if "stiffener_top_flange_gap_mm" in d:
            gap_limit = 4 * t
            values.update(
                {
                    "maximum_flange_termination_gap_mm": gap_limit,
                    "top_flange_termination_gap_mm": d["stiffener_top_flange_gap_mm"],
                    "bottom_flange_termination_gap_mm": d["stiffener_bottom_flange_gap_mm"],
                }
            )
            clauses.append("5.15.1")
            checks.extend(
                [
                    {
                        "clause": "5.15.1 top-flange termination",
                        "satisfied": d["stiffener_top_flange_gap_mm"] <= gap_limit,
                    },
                    {
                        "clause": "5.15.1 bottom-flange termination",
                        "satisfied": d["stiffener_bottom_flange_gap_mm"] <= gap_limit,
                    },
                    {
                        "clause": "5.15.1 termination geometry verified",
                        "satisfied": d["flange_termination_geometry_verified"],
                    },
                ]
            )
        limitations = [
            "Clause 5.15.2.1 selects the 5.10.4 or 5.10.5 web-thickness path from the "
            "declared longitudinal-stiffener condition and supplied panel geometry.",
            "No external stiffener loads/moments; check end posts, geometry and fasteners.",
            "Intermediate stiffeners subject to external forces or moments need 5.15.7.",
        ]
        if "stiffener_buckling_geometry" in d:
            limitations.append(
                "The effective-section radius of gyration is supplied; verify it about the axis "
                "parallel to the web under 5.14.2."
            )
        else:
            limitations.append(
                "The supplied shear buckling coefficient and nominal 5.11/5.14 capacities must "
                "be verified against the member and stiffener details."
            )
        if has_external_actions:
            action_term_kn = 2 * d["external_normal_force_kn"] + abs(
                (
                    1000 * d["external_moment_knm"]
                    + d["external_parallel_force_kn"] * d["force_eccentricity_mm"]
                )
                / depth
            )
            increase = (
                depth**4
                * action_term_kn
                * 1000
                / (d["capacity_factor"] * ELASTIC_MODULUS_MPA * depth * t)
            )
            total_inertia = inertia_min + increase
            supplied_inertia = d["stiffener_second_moment_mm4"]
            values.update(
                {
                    "external_action_term_kn": action_term_kn,
                    "external_load_stiffness_increase_mm4": increase,
                    "required_second_moment_with_external_actions_mm4": total_inertia,
                    "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
                    "capacity_factor": d["capacity_factor"],
                }
            )
            clauses.append("5.15.7.1")
            checks.extend(
                [
                    {
                        "clause": "5.15.7.1 minimum inertia increase",
                        "satisfied": supplied_inertia >= total_inertia,
                    },
                    {
                        "clause": "5.15.7.1 external actions verified",
                        "satisfied": d["external_actions_verified"],
                    },
                ]
            )
            limitations = [
                "The 5.15.7.1 increase is added to the 5.15.5 minimum using E from 2.2.4.",
                "The supplied external-action and flange-termination declarations must match "
                "the design details.",
            ]
            if d["external_parallel_force_kn"] != 0:
                parallel_force_kn = abs(d["external_parallel_force_kn"])
                load_bearing_inputs = d["load_bearing_stiffener_inputs"]
                stiffener_geometry = d.get("stiffener_buckling_geometry")
                if stiffener_geometry is not None:
                    for field in (
                        "radius_of_gyration_mm",
                        "available_web_width_left_mm",
                        "available_web_width_right_mm",
                    ):
                        if not isclose(
                            stiffener_geometry[field],
                            load_bearing_inputs[field],
                            rel_tol=1e-9,
                            abs_tol=1e-9,
                        ):
                            raise ValueError(
                                "5.14.2 effective-section geometry must match the linked "
                                f"5.15.7.2 load-bearing input {field}."
                            )
                pair_inertia = load_bearing_inputs.get(
                    "stiffener_pair_second_moment_about_web_centerline_mm4"
                )
                if pair_inertia is not None and not isclose(
                    pair_inertia,
                    d["stiffener_second_moment_mm4"],
                    rel_tol=1e-9,
                    abs_tol=1e-6,
                ):
                    raise ValueError(
                        "5.14.5 pair inertia must match the 5.15.5 stiffener second moment."
                    )
                load_bearing = run_webs(
                    {
                        "operation": "load_bearing_stiffener",
                        **load_bearing_inputs,
                        "stiffener_configuration": d["stiffener_configuration"],
                        "stiffener_area_mm2": d["stiffener_area_mm2"],
                        "web_yield_mpa": d["web_yield_mpa"],
                        "stiffener_yield_mpa": d["stiffener_yield_mpa"],
                        "web_thickness_mm": t,
                        "clear_web_depth_mm": depth,
                        "panel_spacing_mm": spacing,
                        "stiffener_outstand_mm": d["stiffener_outstand_mm"],
                        "stiffener_thickness_mm": d["stiffener_thickness_mm"],
                        "outer_edge_continuously_stiffened": d["outer_edge_continuously_stiffened"],
                        "bearing_action_kn": parallel_force_kn,
                    }
                )
                attachment = run_webs(
                    {
                        "operation": "load_bearing_stiffener_attachment",
                        **d["load_bearing_stiffener_attachment_inputs"],
                        "design_bearing_force_kn": parallel_force_kn,
                    }
                )
                values.update(
                    {
                        "parallel_web_force_kn": parallel_force_kn,
                        "clause_5_14_load_bearing_stiffener": load_bearing,
                        "clause_5_14_load_bearing_stiffener_attachment": attachment,
                    }
                )
                clauses.extend(["5.15.7.2", *load_bearing["clauses"], *attachment["clauses"]])
                checks.extend(
                    {
                        **check,
                        "clause": f"5.15.7.2 -> {check['clause']}",
                    }
                    for check in [*load_bearing["checks"], *attachment["checks"]]
                )
                limitations.extend(
                    [
                        "Clause 5.15.7.2 calculates the 5.14.1–5.14.4 checks from the supplied "
                        "stiffener, bearing and connection inputs; verify those properties and "
                        "force shares against the design details.",
                        "Assess whether the load-bearing stiffener is the sole torsional end "
                        "restraint and supply the 5.14.5 inputs when it is.",
                    ]
                )
        return result(
            op,
            clauses,
            values,
            checks,
            limitations,
        )
    if op == "end_panel_design":
        if d["panel_depth_mm"] > d["clear_web_depth_mm"]:
            raise ValueError("The end-panel depth cannot exceed the clear web depth.")
        shear = run_members(
            {
                "operation": "shear",
                "yield_strength_mpa": d["web_yield_mpa"],
                "web_area_mm2": d["web_area_mm2"],
                "panel_depth_mm": d["panel_depth_mm"],
                "web_thickness_mm": d["web_thickness_mm"],
                "stiffener_spacing_mm": d["reduced_end_panel_spacing_mm"],
                "tension_field": False,
                "stress_max_average_ratio": d["stress_max_average_ratio"],
                "action_kn": d["design_shear_action_kn"],
                "moment_action_knm": d["design_moment_action_knm"],
                "section_moment_capacity_knm": d["section_moment_capacity_knm"],
            }
        )
        nominal_shear_capacity = shear["values"]["shear_capacity_kn"]
        reduced = d["reduced_end_panel_spacing_mm"] < d["original_end_panel_spacing_mm"]
        checks = [
            {
                "clause": "5.15.2.2 reduced end-panel spacing",
                "original_spacing_mm": d["original_end_panel_spacing_mm"],
                "reduced_spacing_mm": d["reduced_end_panel_spacing_mm"],
                "satisfied": reduced,
            },
            capacity_check(
                "5.11.1 end-panel shear buckling with alpha_d = 1.0",
                nominal_shear_capacity,
                d["design_shear_action_kn"],
            ),
            {
                "clause": "5.12 end-panel shear and bending interaction",
                **shear["checks"]["shear_bending"],
            },
            {"clause": "5.12 end-panel section bending", **shear["checks"]["bending"]},
        ]
        return result(
            op,
            [
                "5.15.2.2",
                "5.11.1",
                "5.11.5.2",
                *[entry["clause"] for entry in shear["trace"]],
            ],
            {
                "alpha_d": shear["values"]["tension_field_factor"],
                "nominal_shear_buckling_capacity_kn": nominal_shear_capacity,
                "design_shear_buckling_capacity_kn": 0.9 * nominal_shear_capacity,
                "original_end_panel_spacing_mm": d["original_end_panel_spacing_mm"],
                "reduced_end_panel_spacing_mm": d["reduced_end_panel_spacing_mm"],
                "section_shear_calculation": shear,
            },
            checks,
            [
                "This is the reduced-width end-panel route under 5.15.2.2; assess the separate "
                "5.15.9 end-post route when that is used.",
                "Confirm the supplied web area, panel depth, stress ratio and section moment "
                "capacity against the actual member and governing load combinations.",
                "The shear calculation uses alpha_d = 1.0 and the conservative flange restraint "
                "factor of 1.0.",
            ],
        )
    depth, t = d["web_depth_mm"], d["web_thickness_mm"]
    if d["location"] == "neutral_axis":
        minimum = depth * t**3
    else:
        ratio = d["stiffener_area_mm2"] / (depth * t)
        minimum = 4 * depth * t**3 * (1 + 4 * ratio * (1 + ratio))
    clauses = ["5.16.2"]
    values = {"minimum_second_moment_mm4": minimum}
    checks = [{"clause": "5.16.2", "satisfied": d["stiffener_second_moment_mm4"] >= minimum}]
    limitations = ["Inertia is about the web face; assess location and geometry against 5.16.1."]
    if "stiffener_continuous" in d:
        detailing_ok = d["stiffener_continuous"] or (
            d["extends_between_transverse_stiffeners"] and d["attached_to_transverse_stiffeners"]
        )
        clauses.insert(0, "5.16.1")
        values.update(
            {
                "stiffener_continuous": d["stiffener_continuous"],
                "extends_between_transverse_stiffeners": d["extends_between_transverse_stiffeners"],
                "attached_to_transverse_stiffeners": d["attached_to_transverse_stiffeners"],
            }
        )
        checks.insert(
            0, {"clause": "5.16.1 continuity or attached end condition", "satisfied": detailing_ok}
        )
        limitations = [
            "Verify the reported continuity and attachment geometry against the details."
        ]
    return result(
        op,
        clauses,
        values,
        checks,
        limitations,
    )
