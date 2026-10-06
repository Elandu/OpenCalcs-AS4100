# SPDX-License-Identifier: AGPL-3.0-only
"""AS 4100 sections 3/4 numerical design-action checks, reviewed against scanned text."""

from math import isclose, isfinite, pi, tan

from .frame_buckling import run_frame_buckling
from .iterative_analysis import run_iterative_second_order_frame_analysis
from .second_order import run_second_order_frame_analysis
from .standards import ELASTIC_MODULUS_MPA
from .validation import NONNEGATIVE, POSITIVE, SIGNED, object_schema, result, validate

_BOOL = {"type": "boolean"}
_REFERENCE = {"type": "string", "minLength": 1, "maxLength": 160}
_YIELD_STRESS = {"type": "number", "exclusiveMinimum": 0, "maximum": 690}
_VECTOR3 = {"type": "array", "minItems": 3, "maxItems": 3, "items": SIGNED}
_IDEALIZED_END_RESTRAINT_FACTORS = {
    "braced_fixed_fixed": 0.7,
    "braced_top_pinned_bottom_fixed": 0.85,
    "braced_pinned_pinned": 1.0,
    "sway_top_fixed_bottom_fixed": 1.2,
    "sway_top_free_bottom_fixed": 2.2,
    "sway_top_fixed_bottom_pinned": 2.2,
}
_BETA_M_FIGURE_CASES = {
    "figure_a_left_1": -1.0,
    "figure_a_left_2": 0.2,
    "figure_a_left_3": 0.6,
    "figure_a_left_4": -0.5,
    "figure_a_left_5": 0.2,
    "figure_a_left_6": 0.2,
    "figure_a_right_1": -1.0,
    "figure_a_right_2": 0.5,
    "figure_a_right_3": 1.0,
    "figure_a_right_4": 0.4,
    "figure_a_right_5": 0.0,
    "figure_a_right_6": 0.5,
    "figure_b_left_1": -0.4,
    "figure_b_left_2": 0.1,
    "figure_b_left_3": 0.7,
    "figure_b_left_4": -0.5,
    "figure_b_left_5": -0.2,
    "figure_b_right_1": -0.5,
    "figure_b_right_2": -0.1,
    "figure_b_right_3": 0.3,
    "figure_b_right_4": -0.4,
    "figure_b_right_5": -0.1,
    "figure_b_right_6": 1.0,
}
_FRAME_STIFFNESS_MODIFIERS = {
    "braced": {"pinned": 1.5, "rigidly_connected_to_column": 1.0, "fixed": 2.0},
    "sway": {"pinned": 0.5, "rigidly_connected_to_column": 1.0, "fixed": 0.67},
}

_FRAME_CHART = object_schema(
    {
        "operation": {"const": "frame_chart_member_buckling"},
        "member_id": _REFERENCE,
        "frame_type": {"enum": ["braced", "sway"]},
        "frame_type_verified": _BOOL,
        "rigid_jointed_frame_verified": _BOOL,
        "frame_classification_evidence_reference": _REFERENCE,
        "stiffness_ratio_at_end_1": NONNEGATIVE,
        "stiffness_ratio_at_end_2": NONNEGATIVE,
        "stiffness_ratios_verified": _BOOL,
        "stiffness_ratio_evidence_reference": _REFERENCE,
        "effective_length_factor": POSITIVE,
        "effective_length_factor_chart_verified": _BOOL,
        "chart_evidence_reference": _REFERENCE,
        "second_moment_mm4": POSITIVE,
        "second_moment_about_buckling_axis_verified": _BOOL,
        "section_evidence_reference": _REFERENCE,
        "member_length_mm": POSITIVE,
        "member_length_centre_to_centre_verified": _BOOL,
        "member_length_evidence_reference": _REFERENCE,
    },
    required=[
        "operation",
        "member_id",
        "frame_type",
        "frame_type_verified",
        "rigid_jointed_frame_verified",
        "frame_classification_evidence_reference",
        "stiffness_ratio_at_end_1",
        "stiffness_ratio_at_end_2",
        "stiffness_ratios_verified",
        "stiffness_ratio_evidence_reference",
        "second_moment_mm4",
        "second_moment_about_buckling_axis_verified",
        "section_evidence_reference",
        "member_length_mm",
        "member_length_centre_to_centre_verified",
        "member_length_evidence_reference",
    ],
)
_FRAME_CHART["allOf"] = [
    {
        "if": {"required": ["effective_length_factor"]},
        "then": {
            "required": ["effective_length_factor_chart_verified", "chart_evidence_reference"]
        },
        "else": {
            "not": {
                "anyOf": [
                    {"required": ["effective_length_factor_chart_verified"]},
                    {"required": ["chart_evidence_reference"]},
                ]
            }
        },
    }
]

_PLASTIC_MATERIAL = object_schema(
    {
        "material_id": _REFERENCE,
        "material_standard": {"enum": ["AS/NZS 3678", "AS/NZS 3679.1"]},
        "material_standard_verified": _BOOL,
        "specified_yield_strength_mpa": _YIELD_STRESS,
        "specified_tensile_strength_mpa": POSITIVE,
        "yield_plateau_extension_in_yield_strains": NONNEGATIVE,
        "elongation_percent": NONNEGATIVE,
        "elongation_test_to_as1391_verified": _BOOL,
        "strain_hardening_capability_verified": _BOOL,
        "stress_strain_data_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_PLASTIC_MEMBER = object_schema(
    {
        "member_id": _REFERENCE,
        "hot_formed": _BOOL,
        "hot_formed_status_verified": _BOOL,
        "section_form": {"enum": ["doubly_symmetric_i_section", "other"]},
        "section_form_verified": _BOOL,
        "compact_under_clause_5_2_3": _BOOL,
        "compactness_assessment_verified": _BOOL,
        "impact_loading_present": _BOOL,
        "impact_loading_assessment_verified": _BOOL,
        "fatigue_assessment_required": _BOOL,
        "fatigue_loading_assessment_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_PLASTIC_CONNECTION = object_schema(
    {
        "connection_id": _REFERENCE,
        "strength_type": {"enum": ["full_strength", "partial_strength"]},
        "connection_design_moment_capacity_knm": POSITIVE,
        "connected_member_design_moment_capacity_knm": POSITIVE,
        "connection_capacity_used_in_analysis_verified": _BOOL,
        "all_required_plastic_hinges_develop_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_PLASTIC_HINGE = object_schema(
    {
        "hinge_id": _REFERENCE,
        "location_type": {"enum": ["member", "connection"]},
        "rotation_demand_rad": NONNEGATIVE,
        "rotation_capacity_rad": POSITIVE,
        "rotation_demand_assessment_verified": _BOOL,
        "rotation_capacity_assessment_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_PLASTIC_DUCTILITY_COMPONENT = object_schema(
    {
        "component_id": _REFERENCE,
        "rotation_demand_rad": NONNEGATIVE,
        "rotation_capacity_rad": POSITIVE,
        "rotation_demand_assessment_verified": _BOOL,
        "rotation_capacity_assessment_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_GLOBAL_ACTION = object_schema(
    {
        "action_id": _REFERENCE,
        "action_type": {"enum": ["applied_load", "support_reaction"]},
        "force_kn": _VECTOR3,
        "moment_knm": _VECTOR3,
        "position_mm": _VECTOR3,
        "evidence_reference": _REFERENCE,
    }
)
_JOINT_ACTION = object_schema(
    {
        "action_id": _REFERENCE,
        "action_type": {"enum": ["member_end_action", "applied_load", "support_reaction"]},
        "force_kn": _VECTOR3,
        "moment_knm": _VECTOR3,
        "position_offset_mm": _VECTOR3,
        "evidence_reference": _REFERENCE,
    }
)
_PLASTIC_SPAN_LOAD = object_schema(
    {
        "action_id": _REFERENCE,
        "force_kn": _VECTOR3,
        "moment_knm": _VECTOR3,
        "position_offset_mm": _VECTOR3,
        "evidence_reference": _REFERENCE,
    }
)
_PLASTIC_MEMBER_SPAN = object_schema(
    {
        "member_id": _REFERENCE,
        "member_vector_mm": _VECTOR3,
        "member_geometry_verified": _BOOL,
        "member_geometry_evidence_reference": _REFERENCE,
        "start_end_force_kn": _VECTOR3,
        "start_end_moment_knm": _VECTOR3,
        "start_end_evidence_reference": _REFERENCE,
        "end_end_force_kn": _VECTOR3,
        "end_end_moment_knm": _VECTOR3,
        "end_end_evidence_reference": _REFERENCE,
        "span_actions": {"type": "array", "items": _PLASTIC_SPAN_LOAD},
        "span_actions_complete_verified": _BOOL,
        "span_actions_evidence_reference": _REFERENCE,
    }
)
_FRAME_COMPRESSION_MEMBER = object_schema(
    {
        "member_id": _REFERENCE,
        "second_moment_mm4": POSITIVE,
        "member_length_mm": POSITIVE,
        "rigid_connection_at_joint_verified": _BOOL,
        "stiffness_evidence_reference": _REFERENCE,
    }
)
_FRAME_BEAM = object_schema(
    {
        "beam_id": _REFERENCE,
        "second_moment_mm4": POSITIVE,
        "member_length_mm": POSITIVE,
        "near_end_rigid_connection_verified": _BOOL,
        "far_end_fixity": {"enum": ["pinned", "rigidly_connected_to_column", "fixed"]},
        "far_end_fixity_verified": _BOOL,
        "stiffness_evidence_reference": _REFERENCE,
    }
)
_BRACED_FRAME_COLUMN = object_schema(
    {
        "column_id": _REFERENCE,
        "elastic_member_buckling_load_n_omb_kn": POSITIVE,
        "design_axial_force_n_star_kn": POSITIVE,
        "member_buckling_load_verified": _BOOL,
        "design_axial_force_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_SWAY_FRAME_COLUMN = object_schema(
    {
        "column_id": _REFERENCE,
        "elastic_member_buckling_load_n_oms_kn": POSITIVE,
        "design_axial_force_n_star_kn": SIGNED,
        "member_length_mm": POSITIVE,
        "member_buckling_load_verified": _BOOL,
        "design_axial_force_verified": _BOOL,
        "member_length_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_SWAY_FRAME_STOREY = object_schema(
    {
        "storey_id": _REFERENCE,
        "columns": {"type": "array", "minItems": 1, "items": _SWAY_FRAME_COLUMN},
        "all_columns_in_storey_listed_verified": _BOOL,
        "column_list_evidence_reference": _REFERENCE,
    }
)
_FRAME_BUCKLING_JOINT = object_schema(
    {
        "joint_id": _REFERENCE,
        "x_mm": SIGNED,
        "y_mm": SIGNED,
        "restrained_dofs": {
            "type": "array",
            "items": {"enum": ["ux", "uy", "rz"]},
            "uniqueItems": True,
        },
        "joint_geometry_verified": _BOOL,
        "restraint_assessment_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_FRAME_BUCKLING_MEMBER = object_schema(
    {
        "member_id": _REFERENCE,
        "start_joint_id": _REFERENCE,
        "end_joint_id": _REFERENCE,
        "area_mm2": POSITIVE,
        "second_moment_in_plane_mm4": POSITIVE,
        "axial_force_kn": SIGNED,
        "axial_force_profile_kn": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": SIGNED,
        },
        "prismatic_member_verified": _BOOL,
        "geometry_verified": _BOOL,
        "section_properties_verified": _BOOL,
        "axial_force_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    },
    required=[
        "member_id",
        "start_joint_id",
        "end_joint_id",
        "area_mm2",
        "second_moment_in_plane_mm4",
        "prismatic_member_verified",
        "geometry_verified",
        "section_properties_verified",
        "axial_force_verified",
        "evidence_reference",
    ],
)
_FRAME_BUCKLING_MEMBER["oneOf"] = [
    {"required": ["axial_force_kn"], "not": {"required": ["axial_force_profile_kn"]}},
    {"required": ["axial_force_profile_kn"], "not": {"required": ["axial_force_kn"]}},
]
_ITERATIVE_FRAME_MEMBER = object_schema(
    {
        "member_id": _REFERENCE,
        "start_joint_id": _REFERENCE,
        "end_joint_id": _REFERENCE,
        "area_mm2": POSITIVE,
        "second_moment_in_plane_mm4": POSITIVE,
        "prismatic_member_verified": _BOOL,
        "geometry_verified": _BOOL,
        "section_properties_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_FRAME_JOINT_ACTION = object_schema(
    {
        "joint_id": _REFERENCE,
        "force_x_kn": SIGNED,
        "force_y_kn": SIGNED,
        "moment_knm": SIGNED,
        "joint_actions_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_FRAME_DISTRIBUTED_MEMBER_LOAD = object_schema(
    {
        "load_id": _REFERENCE,
        "member_id": _REFERENCE,
        "start_fraction": {"type": "number", "minimum": 0, "maximum": 1},
        "end_fraction": {"type": "number", "minimum": 0, "maximum": 1},
        "transverse_force_start_kn_per_m": SIGNED,
        "transverse_force_end_kn_per_m": SIGNED,
        "member_load_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_PLASTIC_JOINT = object_schema(
    {
        "joint_id": _REFERENCE,
        "actions": {"type": "array", "minItems": 2, "items": _JOINT_ACTION},
        "joint_actions_complete_verified": _BOOL,
        "joint_actions_evidence_reference": _REFERENCE,
    }
)
_TRANSLATION_CONSTRAINT = object_schema(
    {
        "dof": {"enum": ["ux", "uy", "uz"]},
        "prescribed_translation_mm": SIGNED,
        "calculated_translation_mm": SIGNED,
        "tolerance_mm": NONNEGATIVE,
        "analysis_result_evidence_reference": _REFERENCE,
    }
)
_ROTATION_CONSTRAINT = object_schema(
    {
        "dof": {"enum": ["rx", "ry", "rz"]},
        "prescribed_rotation_rad": SIGNED,
        "calculated_rotation_rad": SIGNED,
        "tolerance_rad": NONNEGATIVE,
        "analysis_result_evidence_reference": _REFERENCE,
    }
)
_SUPPORT_CONSTRAINT = {"oneOf": [_TRANSLATION_CONSTRAINT, _ROTATION_CONSTRAINT]}
_PLASTIC_SUPPORT = object_schema(
    {
        "support_id": _REFERENCE,
        "constraints": {"type": "array", "minItems": 1, "items": _SUPPORT_CONSTRAINT},
        "support_restraint_verified": _BOOL,
        "support_evidence_reference": _REFERENCE,
    }
)

SCHEMAS = {
    "euler_buckling": object_schema(
        {
            "operation": {"const": "euler_buckling"},
            "elastic_modulus_mpa": {"const": ELASTIC_MODULUS_MPA},
            "second_moment_mm4": POSITIVE,
            "member_length_mm": POSITIVE,
            "effective_length_factor": POSITIVE,
        }
    ),
    "idealized_member_buckling": object_schema(
        {
            "operation": {"const": "idealized_member_buckling"},
            "second_moment_mm4": POSITIVE,
            "member_length_mm": POSITIVE,
            "idealized_end_restraint_case": {"enum": list(_IDEALIZED_END_RESTRAINT_FACTORS)},
            "idealized_end_restraint_verified": _BOOL,
            "end_restraint_evidence_reference": _REFERENCE,
            "member_length_centre_to_centre_verified": _BOOL,
            "member_length_evidence_reference": _REFERENCE,
        }
    ),
    "compression_member_effective_lengths": object_schema(
        {
            "operation": {"const": "compression_member_effective_lengths"},
            "member_length_mm": POSITIVE,
            "member_length_centre_to_centre_verified": _BOOL,
            "member_length_evidence_reference": _REFERENCE,
            "principal_buckling_axes_verified": _BOOL,
            "principal_axes_evidence_reference": _REFERENCE,
            "effective_length_case_x": {"enum": list(_IDEALIZED_END_RESTRAINT_FACTORS)},
            "effective_length_case_x_verified": _BOOL,
            "effective_length_case_x_reference": _REFERENCE,
            "effective_length_case_y": {"enum": list(_IDEALIZED_END_RESTRAINT_FACTORS)},
            "effective_length_case_y_verified": _BOOL,
            "effective_length_case_y_reference": _REFERENCE,
        }
    ),
    "frame_chart_member_buckling": _FRAME_CHART,
    "triangulated_member_buckling": object_schema(
        {
            "operation": {"const": "triangulated_member_buckling"},
            "member_id": _REFERENCE,
            "triangulated_structure_verified": _BOOL,
            "triangulated_structure_evidence_reference": _REFERENCE,
            "second_moment_mm4": POSITIVE,
            "second_moment_about_buckling_axis_verified": _BOOL,
            "section_evidence_reference": _REFERENCE,
            "member_length_between_intersections_mm": POSITIVE,
            "member_length_between_intersections_verified": _BOOL,
            "member_geometry_evidence_reference": _REFERENCE,
            "effective_length_mm": POSITIVE,
            "effective_length_assessment_verified": _BOOL,
            "effective_length_evidence_reference": _REFERENCE,
            "rational_buckling_analysis_consistent_with_appendix_g_verified": _BOOL,
        }
    ),
    "braced_frame_buckling_factor": object_schema(
        {
            "operation": {"const": "braced_frame_buckling_factor"},
            "rectangular_frame_verified": _BOOL,
            "all_members_braced_verified": _BOOL,
            "regular_loading_verified": _BOOL,
            "beam_axial_forces_negligible_verified": _BOOL,
            "frame_assessment_evidence_reference": _REFERENCE,
            "design_load_set_id": _REFERENCE,
            "design_load_set_actions_verified": _BOOL,
            "design_load_set_evidence_reference": _REFERENCE,
            "columns": {"type": "array", "minItems": 1, "items": _BRACED_FRAME_COLUMN},
            "all_columns_in_frame_listed_verified": _BOOL,
            "column_list_evidence_reference": _REFERENCE,
        }
    ),
    "sway_frame_buckling_factor": object_schema(
        {
            "operation": {"const": "sway_frame_buckling_factor"},
            "rectangular_frame_verified": _BOOL,
            "sway_member_classification_verified": _BOOL,
            "regular_loading_verified": _BOOL,
            "beam_axial_forces_negligible_verified": _BOOL,
            "frame_assessment_evidence_reference": _REFERENCE,
            "design_load_set_id": _REFERENCE,
            "design_load_set_actions_verified": _BOOL,
            "design_load_set_evidence_reference": _REFERENCE,
            "storeys": {"type": "array", "minItems": 1, "items": _SWAY_FRAME_STOREY},
            "all_storeys_in_frame_listed_verified": _BOOL,
            "storey_list_evidence_reference": _REFERENCE,
        }
    ),
    "whole_frame_elastic_buckling": object_schema(
        {
            "operation": {"const": "whole_frame_elastic_buckling"},
            "design_load_set_id": _REFERENCE,
            "design_load_actions_verified": _BOOL,
            "design_load_evidence_reference": _REFERENCE,
            "frame_model_verified": _BOOL,
            "frame_model_evidence_reference": _REFERENCE,
            "all_frame_joints_listed_verified": _BOOL,
            "joint_list_evidence_reference": _REFERENCE,
            "all_frame_members_listed_verified": _BOOL,
            "member_list_evidence_reference": _REFERENCE,
            "joints": {
                "type": "array",
                "minItems": 2,
                "items": _FRAME_BUCKLING_JOINT,
            },
            "members": {
                "type": "array",
                "minItems": 1,
                "items": _FRAME_BUCKLING_MEMBER,
            },
        }
    ),
    "second_order_elastic_frame_analysis": object_schema(
        {
            "operation": {"const": "second_order_elastic_frame_analysis"},
            "design_load_set_id": _REFERENCE,
            "design_load_actions_verified": _BOOL,
            "design_load_evidence_reference": _REFERENCE,
            "frame_model_verified": _BOOL,
            "frame_model_evidence_reference": _REFERENCE,
            "linearized_model_applicability_verified": _BOOL,
            "linearized_model_evidence_reference": _REFERENCE,
            "frame_action_equilibrium_verified": _BOOL,
            "frame_action_equilibrium_evidence_reference": _REFERENCE,
            "all_frame_joints_listed_verified": _BOOL,
            "joint_list_evidence_reference": _REFERENCE,
            "all_frame_members_listed_verified": _BOOL,
            "member_list_evidence_reference": _REFERENCE,
            "all_joint_actions_listed_verified": _BOOL,
            "joint_action_list_evidence_reference": _REFERENCE,
            "all_distributed_member_loads_listed_verified": _BOOL,
            "distributed_member_load_list_evidence_reference": _REFERENCE,
            "members_remain_elastic_verified": _BOOL,
            "elastic_response_evidence_reference": _REFERENCE,
            "joints": {
                "type": "array",
                "minItems": 2,
                "items": _FRAME_BUCKLING_JOINT,
            },
            "members": {
                "type": "array",
                "minItems": 1,
                "items": _FRAME_BUCKLING_MEMBER,
            },
            "joint_actions": {
                "type": "array",
                "minItems": 2,
                "items": _FRAME_JOINT_ACTION,
            },
            "distributed_member_loads": {
                "type": "array",
                "items": _FRAME_DISTRIBUTED_MEMBER_LOAD,
            },
        }
    ),
    "iterative_second_order_elastic_frame_analysis": object_schema(
        {
            "operation": {"const": "iterative_second_order_elastic_frame_analysis"},
            "design_load_set_id": _REFERENCE,
            "design_load_actions_verified": _BOOL,
            "design_load_evidence_reference": _REFERENCE,
            "frame_model_verified": _BOOL,
            "frame_model_evidence_reference": _REFERENCE,
            "corotational_method_applicability_verified": _BOOL,
            "corotational_method_evidence_reference": _REFERENCE,
            "frame_action_equilibrium_verified": _BOOL,
            "frame_action_equilibrium_evidence_reference": _REFERENCE,
            "all_frame_joints_listed_verified": _BOOL,
            "joint_list_evidence_reference": _REFERENCE,
            "all_frame_members_listed_verified": _BOOL,
            "member_list_evidence_reference": _REFERENCE,
            "all_joint_actions_listed_verified": _BOOL,
            "joint_action_list_evidence_reference": _REFERENCE,
            "all_distributed_member_loads_listed_verified": _BOOL,
            "distributed_member_load_list_evidence_reference": _REFERENCE,
            "members_remain_elastic_verified": _BOOL,
            "elastic_response_evidence_reference": _REFERENCE,
            "joints": {
                "type": "array",
                "minItems": 2,
                "items": _FRAME_BUCKLING_JOINT,
            },
            "members": {
                "type": "array",
                "minItems": 1,
                "items": _ITERATIVE_FRAME_MEMBER,
            },
            "joint_actions": {
                "type": "array",
                "minItems": 2,
                "items": _FRAME_JOINT_ACTION,
            },
            "distributed_member_loads": {
                "type": "array",
                "items": _FRAME_DISTRIBUTED_MEMBER_LOAD,
            },
        }
    ),
    "rectangular_frame_stiffness_ratio": object_schema(
        {
            "operation": {"const": "rectangular_frame_stiffness_ratio"},
            "frame_type": {"enum": ["braced", "sway"]},
            "member_under_consideration_id": _REFERENCE,
            "compression_members": {
                "type": "array",
                "minItems": 1,
                "items": _FRAME_COMPRESSION_MEMBER,
            },
            "compression_members_at_joint_complete_verified": _BOOL,
            "compression_members_evidence_reference": _REFERENCE,
            "beams": {"type": "array", "minItems": 1, "items": _FRAME_BEAM},
            "beams_at_joint_complete_verified": _BOOL,
            "beams_evidence_reference": _REFERENCE,
            "rectangular_frame_geometry_verified": _BOOL,
            "regular_loading_verified": _BOOL,
            "beam_axial_forces_negligible_verified": _BOOL,
            "frame_assessment_evidence_reference": _REFERENCE,
            "column_base_condition": {
                "enum": [
                    "not_column_base",
                    "rigidly_connected_to_footing",
                    "not_rigidly_connected_to_footing",
                ]
            },
            "column_base_condition_verified": _BOOL,
            "column_base_evidence_reference": _REFERENCE,
        }
    ),
    "moment_amplification": object_schema(
        {
            "operation": {"const": "moment_amplification"},
            "compression_kn": SIGNED,
            "elastic_buckling_load_kn": POSITIVE,
            "beta_m": {"type": "number", "minimum": -1, "maximum": 1},
            "beta_m_figure_case": {"enum": [*_BETA_M_FIGURE_CASES, "figure_b_left_6"]},
            "end_moment_1_abs_knm": NONNEGATIVE,
            "end_moment_2_abs_knm": NONNEGATIVE,
            "end_moment_curvature": {"enum": ["single_curvature", "reverse_curvature"]},
            "end_moments_only_verified": {"const": True},
            "end_moment_curvature_verified": {"const": True},
            "end_moment_evidence_reference": _REFERENCE,
            "conservative_transverse_beta_m": {"const": True},
            "delta_ct_mm": NONNEGATIVE,
            "delta_cw_mm": POSITIVE,
            "first_order_moment_knm": SIGNED,
            "sway_buckling_factor": {"type": "number", "exclusiveMinimum": 1, "maximum": 1e15},
        },
        [
            "operation",
            "compression_kn",
            "first_order_moment_knm",
        ],
    ),
    "storey_sway_amplification": object_schema(
        {
            "operation": {"const": "storey_sway_amplification"},
            "storey_displacement_mm": NONNEGATIVE,
            "storey_height_mm": POSITIVE,
            "total_compression_kn": NONNEGATIVE,
            "total_storey_shear_kn": POSITIVE,
        }
    ),
    "plastic_amplification": object_schema(
        {
            "operation": {"const": "plastic_amplification"},
            "frame_buckling_factor": POSITIVE,
            "first_order_action": SIGNED,
        }
    ),
    "plastic_analysis_limits": object_schema(
        {
            "operation": {"const": "plastic_analysis_limits"},
            "materials": {"type": "array", "minItems": 1, "items": _PLASTIC_MATERIAL},
            "members": {"type": "array", "minItems": 1, "items": _PLASTIC_MEMBER},
        }
    ),
    "plastic_alternative_ductility_assessment": object_schema(
        {
            "operation": {"const": "plastic_alternative_ductility_assessment"},
            "members": {
                "type": "array",
                "minItems": 1,
                "items": _PLASTIC_DUCTILITY_COMPONENT,
            },
            "connections": {
                "type": "array",
                "minItems": 1,
                "items": _PLASTIC_DUCTILITY_COMPONENT,
            },
            "all_members_listed_verified": _BOOL,
            "member_list_evidence_reference": _REFERENCE,
            "all_connections_listed_verified": _BOOL,
            "connection_list_evidence_reference": _REFERENCE,
            "structure_ductility_assessment_verified": _BOOL,
            "structure_ductility_evidence_reference": _REFERENCE,
            "analysis_under_design_loading_verified": _BOOL,
            "analysis_evidence_reference": _REFERENCE,
        }
    ),
    "plastic_analysis_connections": object_schema(
        {
            "operation": {"const": "plastic_analysis_connections"},
            "rigid_plastic_analysis_verified": _BOOL,
            "all_assumed_connections_listed_verified": _BOOL,
            "all_collapse_mechanism_hinges_listed_verified": _BOOL,
            "analysis_evidence_reference": _REFERENCE,
            "connections": {"type": "array", "minItems": 1, "items": _PLASTIC_CONNECTION},
            "plastic_hinges": {"type": "array", "minItems": 1, "items": _PLASTIC_HINGE},
        }
    ),
    "plastic_global_equilibrium": object_schema(
        {
            "operation": {"const": "plastic_global_equilibrium"},
            "actions": {"type": "array", "minItems": 1, "items": _GLOBAL_ACTION},
            "force_tolerance_kn": NONNEGATIVE,
            "moment_tolerance_knm": NONNEGATIVE,
            "boundary_conditions_verified": _BOOL,
            "boundary_conditions_evidence_reference": _REFERENCE,
        }
    ),
    "plastic_joint_equilibrium": object_schema(
        {
            "operation": {"const": "plastic_joint_equilibrium"},
            "joints": {"type": "array", "minItems": 1, "items": _PLASTIC_JOINT},
            "force_tolerance_kn": NONNEGATIVE,
            "moment_tolerance_knm": NONNEGATIVE,
        }
    ),
    "plastic_member_span_equilibrium": object_schema(
        {
            "operation": {"const": "plastic_member_span_equilibrium"},
            "members": {"type": "array", "minItems": 1, "items": _PLASTIC_MEMBER_SPAN},
            "force_tolerance_kn": NONNEGATIVE,
            "moment_tolerance_knm": NONNEGATIVE,
            "all_members_listed_verified": _BOOL,
            "member_list_evidence_reference": _REFERENCE,
        }
    ),
    "plastic_support_boundary_conditions": object_schema(
        {
            "operation": {"const": "plastic_support_boundary_conditions"},
            "supports": {"type": "array", "minItems": 1, "items": _PLASTIC_SUPPORT},
            "all_supports_listed_verified": _BOOL,
            "support_list_evidence_reference": _REFERENCE,
        }
    ),
    "notional_horizontal_load": object_schema(
        {
            "operation": {"const": "notional_horizontal_load"},
            "floor_vertical_design_load_kn": NONNEGATIVE,
        }
    ),
    "stability": object_schema(
        {
            "operation": {"const": "stability"},
            "destabilising_design_effect": NONNEGATIVE,
            "stabilising_dead_effect": NONNEGATIVE,
            "resisting_design_capacity": NONNEGATIVE,
        }
    ),
    "serviceability": object_schema(
        {
            "operation": {"const": "serviceability"},
            "deflection_mm": SIGNED,
            "deflection_limit_mm": POSITIVE,
            "limit_basis": {"type": "string", "minLength": 1, "maxLength": 500},
        }
    ),
}
INPUT_SCHEMA = {"oneOf": list(SCHEMAS.values())}
OUTPUT_SCHEMA = {"type": "object"}


def _moment_from_position_mm(position_mm, force_kn):
    x, y, z = (coordinate / 1000 for coordinate in position_mm)
    force_x, force_y, force_z = force_kn
    return [
        y * force_z - z * force_y,
        z * force_x - x * force_z,
        x * force_y - y * force_x,
    ]


def _elastic_buckling_load(second_moment_mm4, member_length_mm, effective_length_factor):
    load = (
        pi**2
        * ELASTIC_MODULUS_MPA
        * second_moment_mm4
        / (effective_length_factor * member_length_mm) ** 2
        / 1000
    )
    if not isfinite(load) or load <= 0:
        raise ValueError("Invalid elastic buckling load.")
    return load


def _z_cot(z):
    if abs(z) < 1e-4:
        z2 = z * z
        return 1 - z2 / 3 - z2 * z2 / 45 - 2 * z2 * z2 * z2 / 945
    return z / tan(z)


def _frame_chart_effective_length_factor(frame_type, gamma_1, gamma_2):
    """Solve the Figure 4.6.3.3 alignment-chart equations for the first mode."""
    stiffness_sum = gamma_1 + gamma_2
    if frame_type == "braced":
        if stiffness_sum <= 1e-14:
            return 0.5
        if min(gamma_1, gamma_2) >= 1e14:
            return 1.0

        def residual(z):
            return (
                gamma_1 * gamma_2 * z * z / 4
                + stiffness_sum / 2 * (1 - _z_cot(z))
                + 2 * tan(z / 2) / z
                - 1
            )

        lower_delta = max(4e-15, 1e-6 / max(gamma_1, gamma_2, 1))
        upper_delta = max(4e-15, min(1e-3, stiffness_sum * 1e-3))
        lower = pi + lower_delta
        upper = 2 * pi - upper_delta
        lower_value = residual(lower)
        upper_value = residual(upper)
        if lower_value >= 0 or upper_value <= 0:
            raise ValueError("Could not bracket the braced Figure 4.6.3.3 factor.")
        for _ in range(120):
            middle = (lower + upper) / 2
            middle_value = residual(middle)
            if middle_value > 0:
                upper = middle
            else:
                lower = middle
        return pi / ((lower + upper) / 2)

    if stiffness_sum <= 1e-14:
        return 1.0

    smaller = min(gamma_1, gamma_2)
    larger = max(gamma_1, gamma_2)
    product_over_sum = smaller / (1 + smaller / larger) if larger else 0.0

    def residual(z):
        right_hand_side = (product_over_sum * z * z - 36 / stiffness_sum) / 6
        return _z_cot(z) - right_hand_side

    upper_delta = max(4e-15, min(1e-3, stiffness_sum * 0.1))
    lower = 0.0
    upper = pi - upper_delta
    if residual(lower) <= 0 or residual(upper) >= 0:
        raise ValueError("Could not bracket the sway Figure 4.6.3.3 factor.")
    for _ in range(120):
        middle = (lower + upper) / 2
        if residual(middle) > 0:
            lower = middle
        else:
            upper = middle
    return pi / ((lower + upper) / 2)


def _run_braced_frame_buckling_factor(d):
    columns = []
    for column in d["columns"]:
        factor = (
            column["elastic_member_buckling_load_n_omb_kn"] / column["design_axial_force_n_star_kn"]
        )
        if not isfinite(factor) or factor <= 0:
            raise ValueError("Invalid braced-column elastic buckling load factor.")
        columns.append(
            {
                "column_id": column["column_id"],
                "elastic_member_buckling_load_n_omb_kn": column[
                    "elastic_member_buckling_load_n_omb_kn"
                ],
                "design_axial_force_n_star_kn": column["design_axial_force_n_star_kn"],
                "lambda_m": factor,
                "member_buckling_load_verified": column["member_buckling_load_verified"],
                "design_axial_force_verified": column["design_axial_force_verified"],
                "evidence_reference": column["evidence_reference"],
            }
        )
    column_ids = [column["column_id"] for column in columns]
    unique_column_ids = len(column_ids) == len(set(column_ids))
    governing_column = min(columns, key=lambda column: column["lambda_m"])
    checks = [
        {
            "clause": "4.7.2.1",
            "condition": "frame is a verified rectangular frame",
            "satisfied": d["rectangular_frame_verified"],
            "evidence_reference": d["frame_assessment_evidence_reference"],
        },
        {
            "clause": "4.7.2.1",
            "condition": "all frame members are verified as braced",
            "satisfied": d["all_members_braced_verified"],
            "evidence_reference": d["frame_assessment_evidence_reference"],
        },
        {
            "clause": "4.7.2.1",
            "condition": "frame loading is regular",
            "satisfied": d["regular_loading_verified"],
            "evidence_reference": d["frame_assessment_evidence_reference"],
        },
        {
            "clause": "4.7.2.1",
            "condition": "beam axial forces are negligible",
            "satisfied": d["beam_axial_forces_negligible_verified"],
            "evidence_reference": d["frame_assessment_evidence_reference"],
        },
        {
            "clause": "4.7.2.1",
            "condition": "all frame columns are listed",
            "satisfied": d["all_columns_in_frame_listed_verified"],
            "column_count": len(columns),
            "evidence_reference": d["column_list_evidence_reference"],
        },
        {
            "clause": "4.7.2.1",
            "condition": "all member buckling loads and design axial forces are verified",
            "satisfied": all(
                column["member_buckling_load_verified"] and column["design_axial_force_verified"]
                for column in d["columns"]
            ),
        },
        {
            "clause": "4.7.1",
            "condition": "all design axial forces use the selected design load set",
            "load_set_id": d["design_load_set_id"],
            "satisfied": d["design_load_set_actions_verified"],
            "evidence_reference": d["design_load_set_evidence_reference"],
        },
        {
            "clause": "4.7.2.1",
            "condition": "column identifiers are unique",
            "satisfied": unique_column_ids,
        },
    ]
    return result(
        "braced_frame_buckling_factor",
        ["4.7.1", "4.7.2.1"],
        {
            "columns": columns,
            "design_load_set_id": d["design_load_set_id"],
            "governing_column_id": governing_column["column_id"],
            "lambda_c": governing_column["lambda_m"],
        },
        checks,
        limitations=[
            "The N_omb member buckling loads are verified inputs that must follow the applicable "
            "Clauses 4.6.2, 4.6.3.3 and 4.6.3.4 route.",
            "This calculates the approximate in-plane elastic buckling factor for the listed "
            "columns; it does not perform whole-frame buckling analysis or establish full design "
            "compliance.",
        ],
    )


def _run_sway_frame_buckling_factor(d):
    storeys = []
    all_columns_verified = True
    unique_columns_verified = True
    for storey in d["storeys"]:
        column_ids = [column["column_id"] for column in storey["columns"]]
        unique_columns_verified &= len(column_ids) == len(set(column_ids))
        columns = []
        sum_n_oms_over_l = 0.0
        sum_n_star_over_l = 0.0
        for column in storey["columns"]:
            n_oms_over_l = (
                column["elastic_member_buckling_load_n_oms_kn"] / column["member_length_mm"]
            )
            n_star_over_l = column["design_axial_force_n_star_kn"] / column["member_length_mm"]
            sum_n_oms_over_l += n_oms_over_l
            sum_n_star_over_l += n_star_over_l
            all_columns_verified &= (
                column["member_buckling_load_verified"]
                and column["design_axial_force_verified"]
                and column["member_length_verified"]
            )
            columns.append(
                {
                    "column_id": column["column_id"],
                    "elastic_member_buckling_load_n_oms_kn": column[
                        "elastic_member_buckling_load_n_oms_kn"
                    ],
                    "design_axial_force_n_star_kn": column["design_axial_force_n_star_kn"],
                    "member_length_mm": column["member_length_mm"],
                    "n_oms_over_l_kn_per_mm": n_oms_over_l,
                    "n_star_over_l_kn_per_mm": n_star_over_l,
                    "member_buckling_load_verified": column["member_buckling_load_verified"],
                    "design_axial_force_verified": column["design_axial_force_verified"],
                    "member_length_verified": column["member_length_verified"],
                    "evidence_reference": column["evidence_reference"],
                }
            )
        if not isfinite(sum_n_oms_over_l) or not isfinite(sum_n_star_over_l):
            raise ValueError("Invalid sway-storey buckling-factor summation.")
        if sum_n_star_over_l <= 0:
            raise ValueError("Sway-storey design-force sum per length must be positive.")
        factor = sum_n_oms_over_l / sum_n_star_over_l
        if not isfinite(factor) or factor <= 0:
            raise ValueError("Invalid sway-storey elastic buckling load factor.")
        storeys.append(
            {
                "storey_id": storey["storey_id"],
                "columns": columns,
                "sum_n_oms_over_l_kn_per_mm": sum_n_oms_over_l,
                "sum_n_star_over_l_kn_per_mm": sum_n_star_over_l,
                "lambda_ms": factor,
                "all_columns_in_storey_listed_verified": storey[
                    "all_columns_in_storey_listed_verified"
                ],
                "column_list_evidence_reference": storey["column_list_evidence_reference"],
            }
        )
    storey_ids = [storey["storey_id"] for storey in storeys]
    unique_storey_ids = len(storey_ids) == len(set(storey_ids))
    governing_storey = min(storeys, key=lambda storey: storey["lambda_ms"])
    checks = [
        {
            "clause": "4.7.2.2",
            "condition": "frame is a verified rectangular frame",
            "satisfied": d["rectangular_frame_verified"],
            "evidence_reference": d["frame_assessment_evidence_reference"],
        },
        {
            "clause": "4.7.2.2",
            "condition": "sway-member classification is verified",
            "satisfied": d["sway_member_classification_verified"],
            "evidence_reference": d["frame_assessment_evidence_reference"],
        },
        {
            "clause": "4.7.2.2",
            "condition": "frame loading is regular",
            "satisfied": d["regular_loading_verified"],
            "evidence_reference": d["frame_assessment_evidence_reference"],
        },
        {
            "clause": "4.7.2.2",
            "condition": "beam axial forces are negligible",
            "satisfied": d["beam_axial_forces_negligible_verified"],
            "evidence_reference": d["frame_assessment_evidence_reference"],
        },
        {
            "clause": "4.7.2.2",
            "condition": "all frame storeys are listed",
            "satisfied": d["all_storeys_in_frame_listed_verified"],
            "storey_count": len(storeys),
            "evidence_reference": d["storey_list_evidence_reference"],
        },
        {
            "clause": "4.7.2.2",
            "condition": "all buckling loads, axial forces and member lengths are verified",
            "satisfied": all_columns_verified,
        },
        {
            "clause": "4.7.1",
            "condition": "all design axial forces use the selected design load set",
            "load_set_id": d["design_load_set_id"],
            "satisfied": d["design_load_set_actions_verified"],
            "evidence_reference": d["design_load_set_evidence_reference"],
        },
        {
            "clause": "4.7.2.2",
            "condition": "all columns in each storey are listed",
            "satisfied": all(
                storey["all_columns_in_storey_listed_verified"] for storey in d["storeys"]
            ),
        },
        {
            "clause": "4.7.2.2",
            "condition": "storey and column identifiers are unique",
            "satisfied": unique_storey_ids and unique_columns_verified,
        },
    ]
    return result(
        "sway_frame_buckling_factor",
        ["4.7.1", "4.7.2.2"],
        {
            "storeys": storeys,
            "design_load_set_id": d["design_load_set_id"],
            "governing_storey_id": governing_storey["storey_id"],
            "lambda_c": governing_storey["lambda_ms"],
        },
        checks,
        limitations=[
            "The N_oms member buckling loads are verified inputs that must follow the applicable "
            "Clauses 4.6.2, 4.6.3.3 and 4.6.3.4 route. Tension design forces are included as "
            "negative values in each storey's denominator.",
            "This calculates the approximate in-plane elastic buckling factor for the listed "
            "storeys; it does not perform whole-frame buckling analysis or establish full design "
            "compliance.",
        ],
    )


def run_design_actions(inputs):
    d = validate(inputs, INPUT_SCHEMA)
    op = d["operation"]
    if op == "euler_buckling":
        load = _elastic_buckling_load(
            d["second_moment_mm4"],
            d["member_length_mm"],
            d["effective_length_factor"],
        )
        return result(
            op,
            ["4.6.2"],
            {"elastic_buckling_load_kn": load},
            limitations=[
                "Effective length factor requires restraint/frame assessment under 4.6.3.",
            ],
        )
    if op == "idealized_member_buckling":
        effective_length_factor = _IDEALIZED_END_RESTRAINT_FACTORS[
            d["idealized_end_restraint_case"]
        ]
        elastic_buckling_load = _elastic_buckling_load(
            d["second_moment_mm4"],
            d["member_length_mm"],
            effective_length_factor,
        )
        return result(
            op,
            ["4.6.2", "4.6.3.2"],
            {
                "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
                "second_moment_mm4": d["second_moment_mm4"],
                "member_length_mm": d["member_length_mm"],
                "idealized_end_restraint_case": d["idealized_end_restraint_case"],
                "effective_length_factor": effective_length_factor,
                "effective_length_mm": effective_length_factor * d["member_length_mm"],
                "elastic_buckling_load_kn": elastic_buckling_load,
            },
            [
                {
                    "clause": "4.6.3.2",
                    "condition": "idealized end-restraint case is verified against Figure 4.6.3.2",
                    "satisfied": d["idealized_end_restraint_verified"],
                    "evidence_reference": d["end_restraint_evidence_reference"],
                },
                {
                    "clause": "4.6.2",
                    "condition": "member length is verified centre-to-centre between "
                    "supporting members",
                    "satisfied": d["member_length_centre_to_centre_verified"],
                    "evidence_reference": d["member_length_evidence_reference"],
                },
            ],
            limitations=[
                "Figure 4.6.3.2 supplies idealized end-restraint cases only; actual restraint "
                "classification and the selected buckling axis require engineering assessment.",
                "The elastic buckling load uses the supplied section second moment and verified "
                "centre-to-centre member length. It is not a Clause 6.3 design capacity or a "
                "frame stability analysis.",
            ],
        )
    if op == "compression_member_effective_lengths":
        member_length = d["member_length_mm"]
        values = {"member_length_mm": member_length}
        checks = [
            {
                "clause": "6.3.2",
                "condition": "x and y are verified principal buckling axes of the member",
                "satisfied": d["principal_buckling_axes_verified"],
                "evidence_reference": d["principal_axes_evidence_reference"],
            },
            {
                "clause": "4.6.2",
                "condition": (
                    "member length is verified centre-to-centre between supporting members"
                ),
                "satisfied": d["member_length_centre_to_centre_verified"],
                "evidence_reference": d["member_length_evidence_reference"],
            },
        ]
        for axis in "xy":
            case_key = f"effective_length_case_{axis}"
            case = d[case_key]
            factor = _IDEALIZED_END_RESTRAINT_FACTORS[case]
            values.update(
                {
                    case_key: case,
                    f"effective_length_factor_{axis}": factor,
                    f"effective_length_{axis}_mm": factor * member_length,
                }
            )
            checks.append(
                {
                    "clause": "4.6.3.2",
                    "condition": (f"{axis}-axis restraint classification matches Figure 4.6.3.2"),
                    "satisfied": d[f"{case_key}_verified"],
                    "evidence_reference": d[f"{case_key}_reference"],
                }
            )
        return result(
            op,
            ["6.3.2", "4.6.2", "4.6.3.2"],
            values,
            checks,
            limitations=[
                "The end-restraint cases are idealizations from Figure 4.6.3.2. Verify the "
                "restraint and buckling-axis classification for each axis from the actual frame.",
                "This operation does not analyse the frame or calculate compression capacity. "
                "Pass effective_length_x_mm and effective_length_y_mm to run_members with "
                "operation='compression'.",
            ],
        )
    if op == "frame_chart_member_buckling":
        frame_type = d["frame_type"]
        chart_factor_supplied = "effective_length_factor" in d
        effective_length_factor = (
            d["effective_length_factor"]
            if chart_factor_supplied
            else _frame_chart_effective_length_factor(
                frame_type,
                d["stiffness_ratio_at_end_1"],
                d["stiffness_ratio_at_end_2"],
            )
        )
        chart_factor_range_satisfied = (
            0.5 <= effective_length_factor <= 1.0
            if frame_type == "braced"
            else effective_length_factor >= 1.0
        )
        elastic_buckling_load = _elastic_buckling_load(
            d["second_moment_mm4"],
            d["member_length_mm"],
            effective_length_factor,
        )
        figure = "Figure 4.6.3.3(a)" if frame_type == "braced" else "Figure 4.6.3.3(b)"
        chart_factor_check = {
            "clause": "4.6.3.3",
            "condition": (
                "effective length factor is assessed from the applicable chart"
                if chart_factor_supplied
                else "effective length factor is calculated from the applicable "
                "alignment-chart equation"
            ),
            "effective_length_factor": effective_length_factor,
            "figure": figure,
            "satisfied": (
                d["effective_length_factor_chart_verified"] if chart_factor_supplied else True
            ),
        }
        if chart_factor_supplied:
            chart_factor_check["evidence_reference"] = d["chart_evidence_reference"]
        return result(
            op,
            ["4.6.2", "4.6.3.3"],
            {
                "member_id": d["member_id"],
                "frame_type": frame_type,
                "stiffness_ratio_at_end_1": d["stiffness_ratio_at_end_1"],
                "stiffness_ratio_at_end_2": d["stiffness_ratio_at_end_2"],
                "effective_length_factor": effective_length_factor,
                "effective_length_factor_source": (
                    "external_chart_reading"
                    if chart_factor_supplied
                    else "alignment_chart_equation"
                ),
                "effective_length_factor_figure": figure,
                "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
                "second_moment_mm4": d["second_moment_mm4"],
                "member_length_mm": d["member_length_mm"],
                "effective_length_mm": effective_length_factor * d["member_length_mm"],
                "elastic_buckling_load_kn": elastic_buckling_load,
            },
            [
                {
                    "clause": "4.6.3.3",
                    "condition": "frame type is verified for selecting the braced or sway chart",
                    "satisfied": d["frame_type_verified"],
                    "evidence_reference": d["frame_classification_evidence_reference"],
                },
                {
                    "clause": "4.6.3.3",
                    "condition": "compression member forms part of a rigid-jointed frame",
                    "satisfied": d["rigid_jointed_frame_verified"],
                    "evidence_reference": d["frame_classification_evidence_reference"],
                },
                {
                    "clause": "4.6.3.3",
                    "condition": (
                        "both end stiffness ratios are verified under Clause 4.6.3.4 or Appendix G"
                    ),
                    "stiffness_ratio_at_end_1": d["stiffness_ratio_at_end_1"],
                    "stiffness_ratio_at_end_2": d["stiffness_ratio_at_end_2"],
                    "satisfied": d["stiffness_ratios_verified"],
                    "evidence_reference": d["stiffness_ratio_evidence_reference"],
                },
                {
                    **chart_factor_check,
                },
                {
                    "clause": "4.6.3.3",
                    "condition": "effective length factor is within the selected chart range",
                    "satisfied": chart_factor_range_satisfied,
                },
                {
                    "clause": "4.6.2",
                    "condition": "second moment of area is verified about the buckling axis",
                    "satisfied": d["second_moment_about_buckling_axis_verified"],
                    "evidence_reference": d["section_evidence_reference"],
                },
                {
                    "clause": "4.6.2",
                    "condition": (
                        "member length is verified centre-to-centre between supporting members"
                    ),
                    "satisfied": d["member_length_centre_to_centre_verified"],
                    "evidence_reference": d["member_length_evidence_reference"],
                },
            ],
            limitations=[
                "The alignment-chart equation assumes the idealized elastic frame restraints "
                "represented by Figure 4.6.3.3; verify frame classification and both end ratios.",
                "End stiffness ratios are not calculated here; use Clause 4.6.3.4 for "
                "rectangular-frame ratios or Appendix G where applicable. "
                "This is an elastic buckling load, not a Clause 6.3 member design capacity or a "
                "whole-frame buckling analysis.",
            ],
        )
    if op == "triangulated_member_buckling":
        member_length = d["member_length_between_intersections_mm"]
        assessed_effective_length = d["effective_length_mm"]
        rational_analysis_verified = d[
            "rational_buckling_analysis_consistent_with_appendix_g_verified"
        ]
        minimum_length_correction_applied = (
            assessed_effective_length < member_length and not rational_analysis_verified
        )
        effective_length = (
            member_length if minimum_length_correction_applied else assessed_effective_length
        )
        effective_length_factor = effective_length / member_length
        elastic_buckling_load = _elastic_buckling_load(
            d["second_moment_mm4"], member_length, effective_length_factor
        )
        return result(
            op,
            ["4.6.2", "4.6.3.5"],
            {
                "member_id": d["member_id"],
                "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
                "second_moment_mm4": d["second_moment_mm4"],
                "member_length_between_intersections_mm": member_length,
                "assessed_effective_length_mm": assessed_effective_length,
                "effective_length_mm": effective_length,
                "minimum_length_correction_applied": minimum_length_correction_applied,
                "effective_length_factor": effective_length_factor,
                "elastic_buckling_load_kn": elastic_buckling_load,
            },
            [
                {
                    "clause": "4.6.3.5",
                    "condition": "member is verified as part of a triangulated structure",
                    "satisfied": d["triangulated_structure_verified"],
                    "evidence_reference": d["triangulated_structure_evidence_reference"],
                },
                {
                    "clause": "4.6.3.5",
                    "condition": "member length is verified centre-to-centre between intersections",
                    "satisfied": d["member_length_between_intersections_verified"],
                    "evidence_reference": d["member_geometry_evidence_reference"],
                },
                {
                    "clause": "4.6.3.5",
                    "condition": (
                        "effective length is not less than member length unless an "
                        "Appendix G-consistent rational buckling analysis justifies a shorter value"
                    ),
                    "assessed_effective_length_mm": assessed_effective_length,
                    "effective_length_used_mm": effective_length,
                    "rational_analysis_verified": rational_analysis_verified,
                    "satisfied": effective_length >= member_length or rational_analysis_verified,
                    "evidence_reference": d["effective_length_evidence_reference"],
                },
                {
                    "clause": "4.6.2",
                    "condition": "effective length assessment is verified",
                    "satisfied": d["effective_length_assessment_verified"],
                    "evidence_reference": d["effective_length_evidence_reference"],
                },
                {
                    "clause": "4.6.2",
                    "condition": "second moment of area is verified about the buckling axis",
                    "satisfied": d["second_moment_about_buckling_axis_verified"],
                    "evidence_reference": d["section_evidence_reference"],
                },
            ],
            limitations=[
                "This operation applies the Clause 4.6.3.5 centre-to-centre minimum unless "
                "a shorter "
                "effective length is supported by externally verified rational elastic buckling "
                "analysis consistent with Appendix G.",
                "Appendix G analysis is not performed. The result is an elastic buckling load, "
                "not a "
                "Clause 6.3 design capacity or complete triangulated-member assessment.",
            ],
        )
    if op == "braced_frame_buckling_factor":
        return _run_braced_frame_buckling_factor(d)
    if op == "sway_frame_buckling_factor":
        return _run_sway_frame_buckling_factor(d)
    if op == "whole_frame_elastic_buckling":
        values = run_frame_buckling(d)
        checks = [
            {
                "clause": "4.7.2(b)",
                "condition": (
                    "the planar elastic frame model, rigid connections, section properties, "
                    "and restraint assumptions have been assessed"
                ),
                "satisfied": d["frame_model_verified"],
                "evidence_reference": d["frame_model_evidence_reference"],
            },
            {
                "clause": "4.7.1",
                "condition": "the complete frame joint inventory is represented",
                "satisfied": d["all_frame_joints_listed_verified"],
                "evidence_reference": d["joint_list_evidence_reference"],
            },
            {
                "clause": "4.7.1",
                "condition": "the complete frame member inventory is represented",
                "satisfied": d["all_frame_members_listed_verified"],
                "evidence_reference": d["member_list_evidence_reference"],
            },
            {
                "clause": "4.7.1",
                "condition": "all joint coordinates and support restraints are assessed",
                "satisfied": all(
                    joint["joint_geometry_verified"] and joint["restraint_assessment_verified"]
                    for joint in d["joints"]
                ),
                "joint_count": len(d["joints"]),
            },
            {
                "clause": "4.7.1",
                "condition": (
                    "all prismatic member geometry, in-plane properties, and constant or "
                    "linearly varying axial-force profiles are assessed"
                ),
                "satisfied": all(
                    member["prismatic_member_verified"]
                    and member["geometry_verified"]
                    and member["section_properties_verified"]
                    and member["axial_force_verified"]
                    for member in d["members"]
                ),
                "member_count": len(d["members"]),
            },
            {
                "clause": "4.7.1",
                "condition": "member axial forces belong to one proportional design load set",
                "load_set_id": d["design_load_set_id"],
                "satisfied": d["design_load_actions_verified"],
                "evidence_reference": d["design_load_evidence_reference"],
            },
            {
                "clause": "4.7.2(b)",
                "condition": "consecutive member meshes agree within 0.1%",
                "relative_difference": values["relative_mesh_difference"],
                "satisfied": values["relative_mesh_difference"] <= 0.001,
            },
        ]
        return result(
            op,
            ["4.7.1", "4.7.2(b)"],
            values,
            checks,
            limitations=[
                "The calculation is a two-dimensional, first-mode elastic eigenvalue analysis "
                "of prismatic, rigidly connected frame members. Axial force is constant or "
                "varies linearly between the verified member-end values. Verify that the "
                "frame model is planar, complete, and suitable for this idealization.",
                "The analysis uses elastic frame stiffness and beam-column geometric stiffness; "
                "it excludes out-of-plane and torsional modes, shear deformation, member-end "
                "releases, initial imperfections, residual stresses, material nonlinearity, "
                "connection flexibility, and second-order strength design checks.",
                "The returned load factor scales the supplied member axial-force pattern. It "
                "does not establish load combinations, member resistance, second-order actions, "
                "or full AS 4100 compliance.",
            ],
        )
    if op == "second_order_elastic_frame_analysis":
        values = run_second_order_frame_analysis(d)
        checks = [
            {
                "clause": "4.4.1.2",
                "condition": "the second-order analysis model and design load set are assessed",
                "satisfied": d["frame_model_verified"] and d["design_load_actions_verified"],
                "frame_evidence_reference": d["frame_model_evidence_reference"],
                "load_evidence_reference": d["design_load_evidence_reference"],
            },
            {
                "clause": "4.4.1.2",
                "condition": (
                    "the fixed-force linearized method is assessed as applicable to the design case"
                ),
                "satisfied": d["linearized_model_applicability_verified"],
                "evidence_reference": d["linearized_model_evidence_reference"],
            },
            {
                "clause": "E.1",
                "condition": "members remain elastic for the design load set",
                "satisfied": d["members_remain_elastic_verified"],
                "evidence_reference": d["elastic_response_evidence_reference"],
            },
            {
                "clause": "4.7.1",
                "condition": "the member axial-force pattern belongs to one design load set",
                "load_set_id": d["design_load_set_id"],
                "satisfied": d["design_load_actions_verified"],
                "evidence_reference": d["design_load_evidence_reference"],
            },
            {
                "clause": "4.7.2(b)",
                "condition": (
                    "the supplied design load set is below the first positive elastic buckling "
                    "load factor, if one exists"
                ),
                "elastic_buckling_load_factor": values["elastic_buckling_load_factor"],
                "satisfied": values["elastic_buckling_load_factor"] is None
                or values["elastic_buckling_load_factor"] > 1.0,
            },
            {
                "clause": "E.2(b)",
                "condition": "element-end moments converge with mesh refinement",
                "relative_difference": values["relative_mesh_difference"],
                "satisfied": values["relative_mesh_difference"] <= 0.001,
            },
            {
                "clause": "4.7.1",
                "condition": "the complete frame joint inventory is represented",
                "satisfied": d["all_frame_joints_listed_verified"],
                "evidence_reference": d["joint_list_evidence_reference"],
            },
            {
                "clause": "4.7.1",
                "condition": "the complete frame member inventory is represented",
                "satisfied": d["all_frame_members_listed_verified"],
                "evidence_reference": d["member_list_evidence_reference"],
            },
            {
                "clause": "4.5.1",
                "condition": (
                    "the supplied first-order member axial-force pattern is assessed for the "
                    "complete applied action set"
                ),
                "satisfied": d["frame_action_equilibrium_verified"]
                and d["all_joint_actions_listed_verified"]
                and all(action["joint_actions_verified"] for action in d["joint_actions"]),
                "evidence_reference": d["frame_action_equilibrium_evidence_reference"],
                "joint_action_list_evidence_reference": d["joint_action_list_evidence_reference"],
            },
            {
                "clause": "4.5.1",
                "condition": "the complete distributed member-load list has been assessed",
                "satisfied": d["all_distributed_member_loads_listed_verified"]
                and all(load["member_load_verified"] for load in d["distributed_member_loads"]),
                "evidence_reference": d["distributed_member_load_list_evidence_reference"],
                "load_count": len(d["distributed_member_loads"]),
            },
            {
                "clause": "4.5.1",
                "condition": (
                    "applied actions, support reactions and geometric-stiffness resultants "
                    "balance in the assembled frame"
                ),
                "residual": values["global_equilibrium"]["residual"],
                "numerical_tolerance": values["global_equilibrium"]["numerical_tolerance"],
                "satisfied": values["global_equilibrium"]["satisfied"],
            },
            {
                "clause": "4.7.1",
                "condition": "all member geometry, properties and axial-force actions are assessed",
                "satisfied": all(
                    member["prismatic_member_verified"]
                    and member["geometry_verified"]
                    and member["section_properties_verified"]
                    and member["axial_force_verified"]
                    for member in d["members"]
                ),
                "member_count": len(d["members"]),
            },
        ]
        return result(
            op,
            ["4.4.1.2", "4.5.1", "4.7.1", "4.7.2(b)", "E.1", "E.2(b)"],
            values,
            checks,
            limitations=[
                "This is a linearized in-plane second-order elastic analysis of a complete "
                "planar frame with rigid joints and prismatic Euler-Bernoulli members. The "
                "supplied first-order axial-force pattern is held fixed in the geometric "
                "stiffness matrix; deformed geometry and member axial forces are not iteratively "
                "updated. A separately evidenced assessment must confirm that this fixed-force "
                "linearization captures the required second-order response.",
                "Joint forces and moments must be the complete applied design actions resolved "
                "at every listed joint. Piecewise-linear transverse member loads are applied "
                "in local member axes over verified fractions of each member. The operation "
                "does not derive or check equilibrium between these actions and the supplied "
                "member axial-force pattern; supply an evidenced equilibrium assessment. "
                "Axial distributed member loads, "
                "member-end releases, connection flexibility, shear "
                "deformation, initial imperfections, residual stresses, and material "
                "nonlinearity are outside this model.",
                "The reported design bending moments use the converged maximum element-end "
                "moment route in Appendix E.2(b). Assess whether the mesh and model represent "
                "the complete design situation; the operation does not determine load "
                "combinations, section/member capacities, or full AS 4100 compliance.",
            ],
        )
    if op == "iterative_second_order_elastic_frame_analysis":
        values = run_iterative_second_order_frame_analysis(d)
        all_member_properties_verified = all(
            member["prismatic_member_verified"]
            and member["geometry_verified"]
            and member["section_properties_verified"]
            for member in d["members"]
        )
        all_joint_geometry_and_restraints_verified = all(
            joint["joint_geometry_verified"] and joint["restraint_assessment_verified"]
            for joint in d["joints"]
        )
        checks = [
            {
                "clause": "4.4.1.2",
                "condition": "the second-order analysis model and design load set are assessed",
                "satisfied": d["frame_model_verified"] and d["design_load_actions_verified"],
                "frame_evidence_reference": d["frame_model_evidence_reference"],
                "load_evidence_reference": d["design_load_evidence_reference"],
            },
            {
                "clause": "E.1",
                "condition": (
                    "the corotational elastic method and its in-plane model assumptions are "
                    "assessed as applicable"
                ),
                "satisfied": d["corotational_method_applicability_verified"],
                "evidence_reference": d["corotational_method_evidence_reference"],
            },
            {
                "clause": "E.1",
                "condition": "members remain elastic for the design load set",
                "satisfied": d["members_remain_elastic_verified"],
                "evidence_reference": d["elastic_response_evidence_reference"],
            },
            {
                "clause": "4.5.1",
                "condition": (
                    "the complete frame action inventory and member-load equilibrium are assessed"
                ),
                "satisfied": d["frame_action_equilibrium_verified"],
                "evidence_reference": d["frame_action_equilibrium_evidence_reference"],
            },
            {
                "clause": "4.5.1",
                "condition": "calculated global force and moment equilibrium is satisfied",
                "satisfied": values["global_equilibrium"]["satisfied"],
                "residual": values["global_equilibrium"]["residual"],
                "numerical_tolerance": values["global_equilibrium"]["numerical_tolerance"],
            },
            {
                "clause": "E.1",
                "condition": (
                    "the complete joint and member model, geometry, restraints and properties "
                    "are assessed"
                ),
                "satisfied": (
                    d["all_frame_joints_listed_verified"]
                    and d["all_frame_members_listed_verified"]
                    and all_member_properties_verified
                    and all_joint_geometry_and_restraints_verified
                ),
                "joint_list_evidence_reference": d["joint_list_evidence_reference"],
                "member_list_evidence_reference": d["member_list_evidence_reference"],
            },
            {
                "clause": "4.5.1",
                "condition": "all joint actions and transverse member loads are listed",
                "satisfied": (
                    d["all_joint_actions_listed_verified"]
                    and d["all_distributed_member_loads_listed_verified"]
                    and all(action["joint_actions_verified"] for action in d["joint_actions"])
                    and all(load["member_load_verified"] for load in d["distributed_member_loads"])
                ),
                "joint_action_list_evidence_reference": d["joint_action_list_evidence_reference"],
                "distributed_member_load_list_evidence_reference": d[
                    "distributed_member_load_list_evidence_reference"
                ],
            },
            {
                "clause": "E.2(b)",
                "condition": (
                    "the greatest element-end moment response is mesh-converged within 0.1%"
                ),
                "satisfied": values["relative_mesh_difference"] <= 0.001,
                "relative_mesh_difference": values["relative_mesh_difference"],
            },
        ]
        return result(
            op,
            ["4.4.1.2", "4.5.1", "E.1", "E.2(b)"],
            values,
            checks,
            limitations=[
                "This is a two-dimensional corotational elastic analysis of a complete planar "
                "frame with rigid joints and prismatic Euler-Bernoulli members. It updates the "
                "deformed member geometry and axial-force response during proportional load "
                "stepping. The model assumes small axial strain and constant elastic modulus "
                "of 200 000 MPa; only stable equilibrium paths are accepted.",
                "Nodal actions remain fixed in global directions. Piecewise-linear transverse "
                "loads act in the initial local axes of each member. Axial distributed loads, "
                "follower loads, member-end releases, semi-rigid connections, shear deformation, "
                "initial imperfections, residual stress, material nonlinearity, and out-of-plane "
                "or torsional response are outside this model.",
                "The reported element-end moments and axial forces are analysis actions. This "
                "operation does not calculate section or member capacities, apply any separate "
                "Clause 4.4.2.2 member moment amplification required for design, or establish "
                "full AS 4100 compliance. Assess the applicable Clause E.2 design-moment route "
                "and avoid double-counting second-order effects.",
                "Evidence flags record engineer assessments; the operation does not authenticate "
                "the source model, action inventory, elastic-response assessment, or method "
                "applicability evidence.",
            ],
        )
    if op == "rectangular_frame_stiffness_ratio":
        compression_member_ids = [member["member_id"] for member in d["compression_members"]]
        beam_ids = [beam["beam_id"] for beam in d["beams"]]
        unique_compression_member_ids = len(compression_member_ids) == len(
            set(compression_member_ids)
        )
        unique_beam_ids = len(beam_ids) == len(set(beam_ids))
        target_member_count = compression_member_ids.count(d["member_under_consideration_id"])
        target_member_verified = target_member_count == 1 and all(
            member["rigid_connection_at_joint_verified"]
            for member in d["compression_members"]
            if member["member_id"] == d["member_under_consideration_id"]
        )

        compression_stiffness_terms = [
            member["second_moment_mm4"] / member["member_length_mm"]
            for member in d["compression_members"]
        ]
        compression_stiffness_sum = sum(compression_stiffness_terms)
        beam_results = []
        weighted_beam_stiffness_sum = 0.0
        for beam in d["beams"]:
            beta_e = _FRAME_STIFFNESS_MODIFIERS[d["frame_type"]][beam["far_end_fixity"]]
            stiffness = beam["second_moment_mm4"] / beam["member_length_mm"]
            weighted_stiffness = beta_e * stiffness
            weighted_beam_stiffness_sum += weighted_stiffness
            beam_results.append(
                {
                    "beam_id": beam["beam_id"],
                    "far_end_fixity": beam["far_end_fixity"],
                    "beta_e": beta_e,
                    "beam_stiffness_mm3": stiffness,
                    "weighted_stiffness_mm3": weighted_stiffness,
                    "near_end_rigid_connection_verified": beam[
                        "near_end_rigid_connection_verified"
                    ],
                    "far_end_fixity_verified": beam["far_end_fixity_verified"],
                    "stiffness_evidence_reference": beam["stiffness_evidence_reference"],
                }
            )
        if weighted_beam_stiffness_sum <= 0:
            raise ValueError("At least one positive rigidly connected beam stiffness is required.")

        gamma = compression_stiffness_sum / weighted_beam_stiffness_sum
        base_condition = d["column_base_condition"]
        minimum_gamma = (
            10.0
            if base_condition == "not_rigidly_connected_to_footing"
            else 0.6
            if base_condition == "rigidly_connected_to_footing"
            else None
        )
        base_condition_satisfied = d["column_base_condition_verified"]
        minimum_gamma_satisfied = minimum_gamma is None or gamma >= minimum_gamma
        all_compression_members_verified = all(
            member["rigid_connection_at_joint_verified"] for member in d["compression_members"]
        )
        all_near_beam_connections_verified = all(
            beam["near_end_rigid_connection_verified"] for beam in d["beams"]
        )
        all_far_end_fixities_verified = all(beam["far_end_fixity_verified"] for beam in d["beams"])
        checks = [
            {
                "clause": "4.6.3.4",
                "condition": "the rectangular frame geometry is verified",
                "satisfied": d["rectangular_frame_geometry_verified"],
                "evidence_reference": d["frame_assessment_evidence_reference"],
            },
            {
                "clause": "4.6.3.4",
                "condition": "frame loading is regular",
                "satisfied": d["regular_loading_verified"],
                "evidence_reference": d["frame_assessment_evidence_reference"],
            },
            {
                "clause": "4.6.3.4",
                "condition": "beam axial forces are negligible",
                "satisfied": d["beam_axial_forces_negligible_verified"],
                "evidence_reference": d["frame_assessment_evidence_reference"],
            },
            {
                "clause": "4.6.3.4",
                "condition": "all compression members rigidly connected at the joint are listed",
                "satisfied": d["compression_members_at_joint_complete_verified"]
                and all_compression_members_verified,
                "member_count": len(compression_member_ids),
                "evidence_reference": d["compression_members_evidence_reference"],
            },
            {
                "clause": "4.6.3.4",
                "condition": "the member under consideration is listed once",
                "member_occurrences": target_member_count,
                "satisfied": target_member_verified,
            },
            {
                "clause": "4.6.3.4",
                "condition": "all rigidly connected beams at the joint are listed",
                "satisfied": d["beams_at_joint_complete_verified"]
                and all_near_beam_connections_verified,
                "beam_count": len(beam_ids),
                "evidence_reference": d["beams_evidence_reference"],
            },
            {
                "clause": "Table 4.6.3.4",
                "condition": "beam far-end fixity classifications are verified",
                "satisfied": all_far_end_fixities_verified,
                "evidence_reference": d["beams_evidence_reference"],
            },
            {
                "clause": "4.6.3.4(a)/(b)",
                "condition": "the column-base or non-base joint condition is verified",
                "satisfied": base_condition_satisfied,
                "evidence_reference": d["column_base_evidence_reference"],
            },
            {
                "clause": "4.6.3.4(a)/(b)",
                "condition": "the calculated end stiffness ratio meets the base minimum",
                "stiffness_ratio_gamma": gamma,
                "minimum_gamma": minimum_gamma,
                "satisfied": minimum_gamma_satisfied,
            },
            {
                "clause": "4.6.3.4",
                "condition": "compression-member and beam identifiers are unique",
                "satisfied": unique_compression_member_ids and unique_beam_ids,
            },
        ]
        return result(
            op,
            ["4.6.3.4", "Table 4.6.3.4"],
            {
                "frame_type": d["frame_type"],
                "member_under_consideration_id": d["member_under_consideration_id"],
                "compression_member_count": len(compression_member_ids),
                "compression_stiffness_sum_mm3": compression_stiffness_sum,
                "beams": beam_results,
                "weighted_beam_stiffness_sum_mm3": weighted_beam_stiffness_sum,
                "stiffness_ratio_at_end_gamma": gamma,
                "minimum_gamma": minimum_gamma,
                "minimum_gamma_satisfied": minimum_gamma_satisfied,
            },
            checks,
            limitations=[
                "This calculates one end stiffness ratio for the Clause 4.6.3.4 rectangular-frame "
                "route. Calculate the opposite-end ratio separately and assess the "
                "effective-length factor from Figure 4.6.3.3.",
                "Member stiffness properties, frame classification, joint connectivity, beam "
                "far-end fixity, base restraint, loading regularity and negligible "
                "beam axial force are verified inputs, not authenticated model facts.",
                "A rational-analysis alternative to the Clause 4.6.3.4(a)/(b) minimum gamma values "
                "and the whole-frame buckling analysis remain external.",
            ],
        )
    if op == "moment_amplification":
        axial_force = d["compression_kn"]
        has_conservative_beta = "conservative_transverse_beta_m" in d
        has_delta_ct = "delta_ct_mm" in d
        has_delta_cw = "delta_cw_mm" in d
        has_figure_beta = "beta_m_figure_case" in d
        end_moment_fields = (
            "end_moment_1_abs_knm",
            "end_moment_2_abs_knm",
            "end_moment_curvature",
            "end_moments_only_verified",
            "end_moment_curvature_verified",
            "end_moment_evidence_reference",
        )
        end_moment_fields_present = [field in d for field in end_moment_fields]
        if any(end_moment_fields_present) and not all(end_moment_fields_present):
            raise ValueError(
                "The end-moment ratio route requires both moment magnitudes, curvature "
                "classification and verification evidence."
            )
        has_end_moment_ratio = all(end_moment_fields_present)
        if has_delta_ct != has_delta_cw:
            raise ValueError("Clause 4.4.2.2(c) requires both delta_ct_mm and delta_cw_mm.")
        if has_conservative_beta and (
            has_delta_ct or "beta_m" in d or has_figure_beta or has_end_moment_ratio
        ):
            raise ValueError(
                "Use the Clause 4.4.2.2(a) route alone; do not combine it with "
                "beta_m, a figure case, end moments or deflections."
            )
        if has_delta_ct and ("beta_m" in d or has_figure_beta or has_end_moment_ratio):
            raise ValueError(
                "Supply beta_m, a figure case or end moments, or the Clause 4.4.2.2(c) "
                "deflections, not both."
            )
        symbolic_figure_beta = has_figure_beta and d["beta_m_figure_case"] == "figure_b_left_6"
        if symbolic_figure_beta and "beta_m" not in d:
            raise ValueError(
                "Figure B left row 6 requires beta_m because the figure gives beta_m = beta."
            )
        if has_figure_beta and "beta_m" in d and not symbolic_figure_beta:
            raise ValueError("A numeric figure case cannot be combined with a separate beta_m.")
        if has_end_moment_ratio and ("beta_m" in d or has_figure_beta):
            raise ValueError(
                "The end-moment ratio route cannot be combined with another beta basis."
            )
        beta_m_figure_reference = None
        beta_m_end_moment_ratio = None
        end_moment_curvature = None
        if has_delta_ct:
            beta_m = 1 - 2 * d["delta_ct_mm"] / d["delta_cw_mm"]
            if not -1 <= beta_m <= 1:
                raise ValueError(
                    "Clause 4.4.2.2(c) deflections must produce beta_m within [-1, 1]."
                )
            beta_m_method = "4.4.2.2(c)_deflection_ratio"
        elif has_conservative_beta:
            beta_m = -1.0
            beta_m_method = "4.4.2.2(a)_conservative_transverse_load"
        elif has_figure_beta:
            if symbolic_figure_beta:
                beta_m = d["beta_m"]
                beta_m_method = "4.4.2.2_figure_symbolic_beta"
            else:
                beta_m = _BETA_M_FIGURE_CASES[d["beta_m_figure_case"]]
                beta_m_method = "4.4.2.2_figure_lookup"
            figure = "A" if d["beta_m_figure_case"].startswith("figure_a_") else "B"
            beta_m_figure_reference = f"Figure 4.4.2.2({figure})"
        elif has_end_moment_ratio:
            larger_end_moment = max(d["end_moment_1_abs_knm"], d["end_moment_2_abs_knm"])
            if larger_end_moment <= 0:
                raise ValueError("The end-moment ratio requires at least one non-zero end moment.")
            if not isclose(
                abs(d["first_order_moment_knm"]),
                larger_end_moment,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                raise ValueError(
                    "For end moments only, first_order_moment_knm must equal the larger "
                    "absolute end moment."
                )
            beta_m_end_moment_ratio = (
                min(d["end_moment_1_abs_knm"], d["end_moment_2_abs_knm"]) / larger_end_moment
            )
            end_moment_curvature = d["end_moment_curvature"]
            beta_m = beta_m_end_moment_ratio * (
                1 if end_moment_curvature == "reverse_curvature" else -1
            )
            beta_m_method = "4.4.2.2_end_moment_ratio"
        elif "beta_m" in d:
            beta_m = d["beta_m"]
            beta_m_method = "supplied"
        elif axial_force > 0:
            raise ValueError(
                "Provide beta_m or both Clause 4.4.2.2(c) deflection values for compression."
            )
        else:
            beta_m = None
            beta_m_method = "not_required_zero_or_tensile_axial_force"
        cm = min(1.0, 0.6 - 0.4 * beta_m) if beta_m is not None else None
        if axial_force > 0:
            if "elastic_buckling_load_kn" not in d:
                raise ValueError("Positive compression requires elastic_buckling_load_kn.")
            ratio = axial_force / d["elastic_buckling_load_kn"]
            if ratio >= 1:
                raise ValueError("Axial compression reaches elastic instability.")
            db = max(1.0, cm / (1 - ratio))
        else:
            db = 1.0
        ds = 1.0
        if "sway_buckling_factor" in d:
            ds = 1 / (1 - 1 / d["sway_buckling_factor"])
        factor = max(db, ds)
        clauses = []
        if axial_force > 0:
            if has_conservative_beta:
                beta_clause = "4.4.2.2(a)"
            elif has_delta_ct:
                beta_clause = "4.4.2.2(c)"
            elif has_figure_beta:
                beta_clause = "4.4.2.2"
            else:
                beta_clause = "4.4.2.2"
            clauses.extend(["4.4.1.2", beta_clause])
        else:
            clauses.append("4.4.2.2")
        if "sway_buckling_factor" in d:
            if "4.4.1.2" not in clauses:
                clauses.insert(0, "4.4.1.2")
            clauses.append("4.4.2.3")
        checks = (
            [{"clause": "4.4.1.2", "satisfied": factor <= 1.4}]
            if "4.4.1.2" in clauses
            else [{"clause": "4.4.2.2", "satisfied": True}]
        )
        return result(
            op,
            clauses,
            {
                "beta_m": beta_m,
                "beta_m_method": beta_m_method,
                "beta_m_figure_case": d.get("beta_m_figure_case"),
                "beta_m_figure_reference": beta_m_figure_reference,
                "beta_m_end_moment_ratio": beta_m_end_moment_ratio,
                "end_moment_curvature": end_moment_curvature,
                "delta_ct_mm": d.get("delta_ct_mm"),
                "delta_cw_mm": d.get("delta_cw_mm"),
                "cm": cm,
                "braced_factor": db,
                "sway_factor": ds,
                "governing_factor": factor,
                "amplified_moment_knm": factor * d["first_order_moment_knm"],
                "second_order_analysis_required": factor > 1.4,
            },
            checks,
            limitations=[
                "Factors above 1.4 require second-order analysis; values are diagnostic only.",
                "Reverse curvature is positive beta_m. When beta_m is supplied, verify it under "
                "the applicable Clause 4.4.2.2 end-moment or transverse-load method. The "
                "end-moment ratio route requires a verified end-moments-only case and curvature "
                "classification; these supplied analysis facts are not authenticated.",
                "Deflections used for the Clause 4.4.2.2(c) route are supplied analysis results; "
                "this operation does not perform the elastic member analysis or determine the "
                "first-order maximum moment from the actual load distribution.",
            ],
        )
    if op == "storey_sway_amplification":
        ratio = (
            d["storey_displacement_mm"]
            * d["total_compression_kn"]
            / (d["storey_height_mm"] * d["total_storey_shear_kn"])
        )
        if ratio >= 1:
            raise ValueError("Storey sway expression reaches instability.")
        factor = 1 / (1 - ratio)
        return result(
            op,
            ["4.4.2.3(a)(i)"],
            {
                "sway_factor": factor,
                "second_order_analysis_required": factor > 1.4,
            },
            [{"clause": "4.4.1.2", "satisfied": factor <= 1.4}],
            limitations=["Rectangular frame storeys only; all column actions must be included."],
        )
    if op == "plastic_amplification":
        factor = d["frame_buckling_factor"]
        required = factor < 5
        amp = None if required else (1.0 if factor >= 10 else 0.9 / (1 - 1 / factor))
        return result(
            op,
            ["4.5.4"],
            {
                "amplification_factor": amp,
                "amplified_action": None if required else amp * d["first_order_action"],
                "second_order_plastic_analysis_required": required,
            },
            [{"clause": "4.5.4", "satisfied": not required}],
            limitations=[
                "Plastic analysis applicability under 4.5.2 must be separately established."
            ],
        )
    if op == "plastic_analysis_limits":
        checks = []
        material_results = []
        for material in d["materials"]:
            fy = material["specified_yield_strength_mpa"]
            fu = material["specified_tensile_strength_mpa"]
            yield_ratio = fu / fy
            plateau_ratio = material["yield_plateau_extension_in_yield_strains"]
            elongation = material["elongation_percent"]
            standard_verified = (
                material["material_standard_verified"] and material["stress_strain_data_verified"]
            )
            material_checks = [
                {
                    "clause": "4.5.2(a)",
                    "subject_id": material["material_id"],
                    "minimum_specified_yield_strength_mpa": fy,
                    "limit_mpa": 450,
                    "evidence_verified": material["material_standard_verified"],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": material["material_standard_verified"] and fy <= 450,
                },
                {
                    "clause": "4.5.2(b)",
                    "subject_id": material["material_id"],
                    "material_standard": material["material_standard"],
                    "stress_strain_data_verified": material["stress_strain_data_verified"],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": standard_verified,
                },
                {
                    "clause": "4.5.2(b)(i)",
                    "subject_id": material["material_id"],
                    "yield_plateau_extension_in_yield_strains": plateau_ratio,
                    "minimum_ratio": 6,
                    "evidence_verified": material["stress_strain_data_verified"],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": standard_verified and plateau_ratio >= 6,
                },
                {
                    "clause": "4.5.2(b)(ii)",
                    "subject_id": material["material_id"],
                    "tensile_to_yield_strength_ratio": yield_ratio,
                    "minimum_ratio": 1.2,
                    "evidence_verified": material["stress_strain_data_verified"],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": standard_verified and yield_ratio >= 1.2,
                },
                {
                    "clause": "4.5.2(b)(iii)",
                    "subject_id": material["material_id"],
                    "elongation_percent": elongation,
                    "minimum_percent": 15,
                    "as1391_test_verified": material["elongation_test_to_as1391_verified"],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": (
                        standard_verified
                        and elongation >= 15
                        and material["elongation_test_to_as1391_verified"]
                    ),
                },
                {
                    "clause": "4.5.2(b)(iv)",
                    "subject_id": material["material_id"],
                    "strain_hardening_capability_verified": material[
                        "strain_hardening_capability_verified"
                    ],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": (
                        standard_verified and material["strain_hardening_capability_verified"]
                    ),
                },
            ]
            checks.extend(material_checks)
            material_results.append(
                {
                    "material_id": material["material_id"],
                    "tensile_to_yield_strength_ratio": yield_ratio,
                    "checks_satisfied": all(check["satisfied"] for check in material_checks),
                }
            )

        member_results = []
        for member in d["members"]:
            section_verified = member["section_form_verified"]
            compactness_verified = member["compactness_assessment_verified"]
            loading_verified = (
                member["impact_loading_assessment_verified"]
                and member["fatigue_loading_assessment_verified"]
            )
            member_checks = [
                {
                    "clause": "4.5.2(c)",
                    "subject_id": member["member_id"],
                    "hot_formed": member["hot_formed"],
                    "status_verified": member["hot_formed_status_verified"],
                    "evidence_reference": member["evidence_reference"],
                    "satisfied": member["hot_formed"] and member["hot_formed_status_verified"],
                },
                {
                    "clause": "4.5.2(d)",
                    "subject_id": member["member_id"],
                    "section_form": member["section_form"],
                    "status_verified": section_verified,
                    "evidence_reference": member["evidence_reference"],
                    "satisfied": (
                        section_verified and member["section_form"] == "doubly_symmetric_i_section"
                    ),
                },
                {
                    "clause": "4.5.2(e)",
                    "subject_id": member["member_id"],
                    "compact_under_clause_5_2_3": member["compact_under_clause_5_2_3"],
                    "assessment_verified": compactness_verified,
                    "evidence_reference": member["evidence_reference"],
                    "satisfied": member["compact_under_clause_5_2_3"] and compactness_verified,
                },
                {
                    "clause": "4.5.2(f)",
                    "subject_id": member["member_id"],
                    "impact_loading_present": member["impact_loading_present"],
                    "fatigue_assessment_required": member["fatigue_assessment_required"],
                    "loading_assessment_verified": loading_verified,
                    "evidence_reference": member["evidence_reference"],
                    "satisfied": (
                        loading_verified
                        and not member["impact_loading_present"]
                        and not member["fatigue_assessment_required"]
                    ),
                },
            ]
            checks.extend(member_checks)
            member_results.append(
                {
                    "member_id": member["member_id"],
                    "checks_satisfied": all(check["satisfied"] for check in member_checks),
                }
            )

        return result(
            op,
            ["4.5.2(a)–(f)"],
            {
                "materials": material_results,
                "members": member_results,
                "prescriptive_4_5_2_conditions_satisfied": all(
                    check["satisfied"] for check in checks
                ),
            },
            checks,
            limitations=[
                "This checks the prescriptive Clause 4.5.2 route only; an alternative "
                "ductility assessment is not evaluated.",
                "Clause 4.5.1 equilibrium and boundary conditions and Clause 4.5.3 "
                "connection strength and plastic-rotation capacity remain separate assessments.",
                "No plastic frame analysis, hinge sequence or design action effects are "
                "calculated.",
            ],
        )
    if op == "plastic_alternative_ductility_assessment":
        checks = []
        component_results = {"members": [], "connections": []}
        all_rotation_conditions_satisfied = True
        for component_type in ("members", "connections"):
            component_ids = []
            for component in d[component_type]:
                component_ids.append(component["component_id"])
                demand = component["rotation_demand_rad"]
                capacity = component["rotation_capacity_rad"]
                demand_verified = component["rotation_demand_assessment_verified"]
                capacity_verified = component["rotation_capacity_assessment_verified"]
                rotation_satisfied = demand <= capacity and demand_verified and capacity_verified
                all_rotation_conditions_satisfied = (
                    all_rotation_conditions_satisfied and rotation_satisfied
                )
                checks.append(
                    {
                        "clause": "4.5.2",
                        "component_type": component_type[:-1],
                        "component_id": component["component_id"],
                        "rotation_demand_rad": demand,
                        "rotation_capacity_rad": capacity,
                        "rotation_demand_assessment_verified": demand_verified,
                        "rotation_capacity_assessment_verified": capacity_verified,
                        "rotation_demand_to_capacity_ratio": demand / capacity,
                        "evidence_reference": component["evidence_reference"],
                        "satisfied": rotation_satisfied,
                    }
                )
                component_results[component_type].append(
                    {
                        "component_id": component["component_id"],
                        "rotation_demand_to_capacity_ratio": demand / capacity,
                        "checks_satisfied": rotation_satisfied,
                    }
                )
            unique_component_ids = len(component_ids) == len(set(component_ids))
            list_flag = f"all_{component_type}_listed_verified"
            list_reference = f"{component_type[:-1]}_list_evidence_reference"
            checks.extend(
                [
                    {
                        "clause": "4.5.2",
                        "component_type": component_type[:-1],
                        "condition": "component identifiers are unique",
                        "satisfied": unique_component_ids,
                    },
                    {
                        "clause": "4.5.2",
                        "component_type": component_type[:-1],
                        "condition": "all required components are listed",
                        "satisfied": d[list_flag],
                        "evidence_reference": d[list_reference],
                    },
                ]
            )
        checks.extend(
            [
                {
                    "clause": "4.5.2",
                    "condition": "structure-level ductility assessment is verified",
                    "satisfied": d["structure_ductility_assessment_verified"],
                    "evidence_reference": d["structure_ductility_evidence_reference"],
                },
                {
                    "clause": "4.5.2",
                    "condition": "analysis covers the design loading conditions",
                    "satisfied": d["analysis_under_design_loading_verified"],
                    "evidence_reference": d["analysis_evidence_reference"],
                },
            ]
        )
        return result(
            op,
            ["4.5.2"],
            {
                **component_results,
                "all_component_rotation_conditions_satisfied": all_rotation_conditions_satisfied,
            },
            checks,
            limitations=[
                "Rotation demands, capacities, structure-level ductility, design loading and "
                "component-list completeness are supplied assessments; only listed demand-to-"
                "capacity comparisons are calculated.",
                "A passing result does not independently establish adequate structural ductility "
                "or complete member and connection design.",
            ],
        )
    if op == "plastic_analysis_connections":
        checks = [
            {
                "clause": "4.5.3",
                "condition": "rigid plastic analysis is used",
                "satisfied": d["rigid_plastic_analysis_verified"],
                "evidence_reference": d["analysis_evidence_reference"],
            },
            {
                "clause": "4.5.3",
                "condition": "all assumed full/partial-strength connections are listed",
                "satisfied": d["all_assumed_connections_listed_verified"],
                "evidence_reference": d["analysis_evidence_reference"],
            },
            {
                "clause": "4.5.3(a)/(b)",
                "condition": "all plastic hinges in the collapse mechanism are listed",
                "satisfied": d["all_collapse_mechanism_hinges_listed_verified"],
                "evidence_reference": d["analysis_evidence_reference"],
            },
        ]
        connection_results = []
        for connection in d["connections"]:
            connection_capacity = connection["connection_design_moment_capacity_knm"]
            member_capacity = connection["connected_member_design_moment_capacity_knm"]
            capacity_ratio = connection_capacity / member_capacity
            common_satisfied = connection["connection_capacity_used_in_analysis_verified"]
            if connection["strength_type"] == "full_strength":
                strength_clause = "4.5.3(a)"
                strength_condition = "connection capacity is at least the connected member capacity"
                strength_satisfied = connection_capacity >= member_capacity
            else:
                strength_clause = "4.5.3(b)"
                strength_condition = "all plastic hinges required by the mechanism can develop"
                strength_satisfied = connection["all_required_plastic_hinges_develop_verified"]
            connection_checks = [
                {
                    "clause": strength_clause,
                    "subject_id": connection["connection_id"],
                    "condition": strength_condition,
                    "connection_design_moment_capacity_knm": connection_capacity,
                    "connected_member_design_moment_capacity_knm": member_capacity,
                    "capacity_ratio": capacity_ratio,
                    "satisfied": strength_satisfied,
                    "evidence_reference": connection["evidence_reference"],
                },
                {
                    "clause": "4.5.3",
                    "subject_id": connection["connection_id"],
                    "condition": "connection capacity is included in the analysis",
                    "satisfied": common_satisfied,
                    "evidence_reference": connection["evidence_reference"],
                },
            ]
            checks.extend(connection_checks)
            connection_results.append(
                {
                    "connection_id": connection["connection_id"],
                    "strength_type": connection["strength_type"],
                    "capacity_ratio": capacity_ratio,
                    "checks_satisfied": all(check["satisfied"] for check in connection_checks),
                }
            )

        hinge_results = []
        for hinge in d["plastic_hinges"]:
            assessments_verified = (
                hinge["rotation_demand_assessment_verified"]
                and hinge["rotation_capacity_assessment_verified"]
            )
            rotation_satisfied = (
                assessments_verified
                and hinge["rotation_capacity_rad"] >= hinge["rotation_demand_rad"]
            )
            hinge_check = {
                "clause": "4.5.3(a)/(b)",
                "subject_id": hinge["hinge_id"],
                "location_type": hinge["location_type"],
                "rotation_demand_rad": hinge["rotation_demand_rad"],
                "rotation_capacity_rad": hinge["rotation_capacity_rad"],
                "assessments_verified": assessments_verified,
                "satisfied": rotation_satisfied,
                "evidence_reference": hinge["evidence_reference"],
            }
            checks.append(hinge_check)
            hinge_results.append(
                {
                    "hinge_id": hinge["hinge_id"],
                    "rotation_demand_to_capacity_ratio": (
                        hinge["rotation_demand_rad"] / hinge["rotation_capacity_rad"]
                    ),
                    "checks_satisfied": rotation_satisfied,
                }
            )

        return result(
            op,
            ["4.5.3", "4.5.3(a)", "4.5.3(b)"],
            {
                "connections": connection_results,
                "plastic_hinges": hinge_results,
                "connection_and_rotation_conditions_satisfied": all(
                    check["satisfied"] for check in checks
                ),
            },
            checks,
            limitations=[
                "Connection capacities, the completeness of the connection/hinge lists and "
                "rotation assessments are supplied evidence and are not authenticated here.",
                "This does not verify global equilibrium, boundary conditions, the collapse "
                "mechanism or the underlying plastic analysis results.",
            ],
        )
    if op == "plastic_global_equilibrium":
        force_resultant = [0.0, 0.0, 0.0]
        moment_resultant = [0.0, 0.0, 0.0]
        action_counts = {"applied_load": 0, "support_reaction": 0}
        for action in d["actions"]:
            action_counts[action["action_type"]] += 1
            force = action["force_kn"]
            couple = action["moment_knm"]
            lever_moment = _moment_from_position_mm(action["position_mm"], force)
            for axis in range(3):
                force_resultant[axis] += force[axis]
                moment_resultant[axis] += couple[axis] + lever_moment[axis]

        force_satisfied = all(
            abs(component) <= d["force_tolerance_kn"] for component in force_resultant
        )
        moment_satisfied = all(
            abs(component) <= d["moment_tolerance_knm"] for component in moment_resultant
        )
        action_types_satisfied = all(count > 0 for count in action_counts.values())
        checks = [
            {
                "clause": "4.5.1",
                "condition": "global force equilibrium",
                "resultant_force_kn": force_resultant,
                "maximum_component_residual_kn": max(abs(value) for value in force_resultant),
                "tolerance_kn": d["force_tolerance_kn"],
                "satisfied": force_satisfied,
            },
            {
                "clause": "4.5.1",
                "condition": "global moment equilibrium about the supplied origin",
                "resultant_moment_knm": moment_resultant,
                "maximum_component_residual_knm": max(abs(value) for value in moment_resultant),
                "tolerance_knm": d["moment_tolerance_knm"],
                "satisfied": moment_satisfied,
            },
            {
                "clause": "4.5.1",
                "condition": "boundary conditions are verified",
                "satisfied": d["boundary_conditions_verified"],
                "evidence_reference": d["boundary_conditions_evidence_reference"],
            },
            {
                "clause": "4.5.1",
                "condition": "applied loads and support reactions are both supplied",
                "action_counts": action_counts,
                "satisfied": action_types_satisfied,
            },
        ]
        return result(
            op,
            ["4.5.1"],
            {
                "force_resultant_kn": force_resultant,
                "moment_resultant_knm": moment_resultant,
                "action_counts": action_counts,
                "global_equilibrium_satisfied": (
                    force_satisfied and moment_satisfied and action_types_satisfied
                ),
            },
            checks,
            limitations=[
                "The global resultants are calculated from supplied action effects; include all "
                "applied loads and support reactions with consistent signs and coordinates.",
                "This does not check member/joint equilibrium, the plastic action distribution, or "
                "the underlying structural analysis. Boundary conditions remain supplied evidence.",
            ],
        )
    if op == "plastic_joint_equilibrium":
        joint_results = []
        checks = []
        for joint in d["joints"]:
            force_resultant = [0.0, 0.0, 0.0]
            moment_resultant = [0.0, 0.0, 0.0]
            action_counts = {
                "member_end_action": 0,
                "applied_load": 0,
                "support_reaction": 0,
            }
            for action in joint["actions"]:
                action_counts[action["action_type"]] += 1
                force = action["force_kn"]
                couple = action["moment_knm"]
                lever_moment = _moment_from_position_mm(action["position_offset_mm"], force)
                for axis in range(3):
                    force_resultant[axis] += force[axis]
                    moment_resultant[axis] += couple[axis] + lever_moment[axis]

            force_satisfied = all(
                abs(component) <= d["force_tolerance_kn"] for component in force_resultant
            )
            moment_satisfied = all(
                abs(component) <= d["moment_tolerance_knm"] for component in moment_resultant
            )
            member_end_action_present = action_counts["member_end_action"] > 0
            joint_results.append(
                {
                    "joint_id": joint["joint_id"],
                    "force_resultant_kn": force_resultant,
                    "moment_resultant_knm": moment_resultant,
                    "action_counts": action_counts,
                    "joint_equilibrium_satisfied": force_satisfied and moment_satisfied,
                }
            )
            checks.extend(
                [
                    {
                        "clause": "4.5.1",
                        "joint_id": joint["joint_id"],
                        "condition": "joint force equilibrium",
                        "resultant_force_kn": force_resultant,
                        "maximum_component_residual_kn": max(
                            abs(value) for value in force_resultant
                        ),
                        "tolerance_kn": d["force_tolerance_kn"],
                        "satisfied": force_satisfied,
                    },
                    {
                        "clause": "4.5.1",
                        "joint_id": joint["joint_id"],
                        "condition": "joint moment equilibrium",
                        "resultant_moment_knm": moment_resultant,
                        "maximum_component_residual_knm": max(
                            abs(value) for value in moment_resultant
                        ),
                        "tolerance_knm": d["moment_tolerance_knm"],
                        "satisfied": moment_satisfied,
                    },
                    {
                        "clause": "4.5.1",
                        "joint_id": joint["joint_id"],
                        "condition": "at least one member-end action is supplied",
                        "action_counts": action_counts,
                        "satisfied": member_end_action_present,
                    },
                    {
                        "clause": "4.5.1",
                        "joint_id": joint["joint_id"],
                        "condition": "joint action completeness is verified",
                        "satisfied": joint["joint_actions_complete_verified"],
                        "evidence_reference": joint["joint_actions_evidence_reference"],
                    },
                ]
            )
        return result(
            op,
            ["4.5.1"],
            {
                "joints": joint_results,
                "all_joint_equilibria_satisfied": all(
                    joint["joint_equilibrium_satisfied"] for joint in joint_results
                ),
            },
            checks,
            limitations=[
                "Supply member-end actions, nodal loads and support reactions using one sign "
                "convention; position offsets are measured from each joint.",
                "The completeness declaration is supplied evidence. The operation does not "
                "verify member-span equilibrium, boundary conditions or analysis validity.",
            ],
        )
    if op == "plastic_member_span_equilibrium":
        member_results = []
        checks = []
        member_ids = [member["member_id"] for member in d["members"]]
        unique_member_ids = len(member_ids) == len(set(member_ids))
        for member in d["members"]:
            member_vector = member["member_vector_mm"]
            if not any(component != 0 for component in member_vector):
                raise ValueError(f"Member {member['member_id']} must have nonzero length.")

            force_resultant = [
                member["start_end_force_kn"][axis] + member["end_end_force_kn"][axis]
                for axis in range(3)
            ]
            end_lever_moment = _moment_from_position_mm(
                member_vector,
                member["end_end_force_kn"],
            )
            moment_resultant = [
                member["start_end_moment_knm"][axis]
                + member["end_end_moment_knm"][axis]
                + end_lever_moment[axis]
                for axis in range(3)
            ]
            span_action_ids = [action["action_id"] for action in member["span_actions"]]
            unique_span_action_ids = len(span_action_ids) == len(set(span_action_ids))
            for action in member["span_actions"]:
                lever_moment = _moment_from_position_mm(
                    action["position_offset_mm"],
                    action["force_kn"],
                )
                for axis in range(3):
                    force_resultant[axis] += action["force_kn"][axis]
                    moment_resultant[axis] += action["moment_knm"][axis] + lever_moment[axis]

            force_satisfied = all(
                abs(component) <= d["force_tolerance_kn"] for component in force_resultant
            )
            moment_satisfied = all(
                abs(component) <= d["moment_tolerance_knm"] for component in moment_resultant
            )
            member_equilibrium_satisfied = force_satisfied and moment_satisfied
            member_results.append(
                {
                    "member_id": member["member_id"],
                    "member_vector_mm": member_vector,
                    "span_action_count": len(member["span_actions"]),
                    "force_resultant_kn": force_resultant,
                    "moment_resultant_about_start_knm": moment_resultant,
                    "member_equilibrium_satisfied": member_equilibrium_satisfied,
                }
            )
            checks.extend(
                [
                    {
                        "clause": "4.5.1",
                        "member_id": member["member_id"],
                        "condition": "member force equilibrium",
                        "resultant_force_kn": force_resultant,
                        "maximum_component_residual_kn": max(
                            abs(value) for value in force_resultant
                        ),
                        "tolerance_kn": d["force_tolerance_kn"],
                        "satisfied": force_satisfied,
                    },
                    {
                        "clause": "4.5.1",
                        "member_id": member["member_id"],
                        "condition": "member moment equilibrium about its start end",
                        "resultant_moment_knm": moment_resultant,
                        "maximum_component_residual_knm": max(
                            abs(value) for value in moment_resultant
                        ),
                        "tolerance_knm": d["moment_tolerance_knm"],
                        "satisfied": moment_satisfied,
                    },
                    {
                        "clause": "4.5.1",
                        "member_id": member["member_id"],
                        "condition": "member geometry is verified",
                        "satisfied": member["member_geometry_verified"],
                        "evidence_reference": member["member_geometry_evidence_reference"],
                    },
                    {
                        "clause": "4.5.1",
                        "member_id": member["member_id"],
                        "condition": "span action resultants are complete",
                        "span_action_count": len(member["span_actions"]),
                        "satisfied": member["span_actions_complete_verified"],
                        "evidence_reference": member["span_actions_evidence_reference"],
                    },
                    {
                        "clause": "4.5.1",
                        "member_id": member["member_id"],
                        "condition": "span action identifiers are unique",
                        "satisfied": unique_span_action_ids,
                    },
                ]
            )

        checks.extend(
            [
                {
                    "clause": "4.5.1",
                    "condition": "member identifiers are unique",
                    "satisfied": unique_member_ids,
                },
                {
                    "clause": "4.5.1",
                    "condition": "all analyzed member spans are listed",
                    "satisfied": d["all_members_listed_verified"],
                    "evidence_reference": d["member_list_evidence_reference"],
                },
            ]
        )
        return result(
            op,
            ["4.5.1"],
            {
                "members": member_results,
                "all_member_equilibria_satisfied": all(
                    member["member_equilibrium_satisfied"] for member in member_results
                ),
                "unique_member_identifiers": unique_member_ids,
            },
            checks,
            limitations=[
                "End actions act on each member; forces use the stated global axes, end moments "
                "are about their respective ends, and span action offsets are measured from the "
                "member start.",
                "Span actions must include the equivalent resultant and couple of every applied "
                "point or distributed load. Completeness, geometry and source records are supplied "
                "evidence and are not authenticated.",
                "This checks the listed member free-body resultants only; it does not derive load "
                "resultants, check joints or the whole structure, or validate the analysis model.",
            ],
        )
    if op == "plastic_support_boundary_conditions":
        support_results = []
        checks = []
        for support in d["supports"]:
            constraint_results = []
            dofs = []
            for constraint in support["constraints"]:
                dof = constraint["dof"]
                dofs.append(dof)
                if "prescribed_translation_mm" in constraint:
                    unit = "mm"
                    prescribed = constraint["prescribed_translation_mm"]
                    calculated = constraint["calculated_translation_mm"]
                    tolerance = constraint["tolerance_mm"]
                else:
                    unit = "rad"
                    prescribed = constraint["prescribed_rotation_rad"]
                    calculated = constraint["calculated_rotation_rad"]
                    tolerance = constraint["tolerance_rad"]
                residual = calculated - prescribed
                satisfied = abs(residual) <= tolerance
                constraint_results.append(
                    {
                        "dof": dof,
                        "unit": unit,
                        "prescribed_value": prescribed,
                        "calculated_value": calculated,
                        "residual": residual,
                        "tolerance": tolerance,
                        "satisfied": satisfied,
                        "analysis_result_evidence_reference": constraint[
                            "analysis_result_evidence_reference"
                        ],
                    }
                )
                checks.append(
                    {
                        "clause": "4.5.1",
                        "support_id": support["support_id"],
                        "condition": f"{dof} meets the prescribed boundary value",
                        "residual": residual,
                        "unit": unit,
                        "tolerance": tolerance,
                        "satisfied": satisfied,
                        "evidence_reference": constraint["analysis_result_evidence_reference"],
                    }
                )
            unique_dofs = len(dofs) == len(set(dofs))
            checks.extend(
                [
                    {
                        "clause": "4.5.1",
                        "support_id": support["support_id"],
                        "condition": "each restrained degree of freedom is listed once",
                        "satisfied": unique_dofs,
                    },
                    {
                        "clause": "4.5.1",
                        "support_id": support["support_id"],
                        "condition": "support restraint is verified",
                        "satisfied": support["support_restraint_verified"],
                        "evidence_reference": support["support_evidence_reference"],
                    },
                ]
            )
            support_results.append(
                {
                    "support_id": support["support_id"],
                    "constraints": constraint_results,
                    "support_conditions_satisfied": all(
                        item["satisfied"] for item in constraint_results
                    )
                    and unique_dofs
                    and support["support_restraint_verified"],
                }
            )
        support_ids = [support["support_id"] for support in d["supports"]]
        unique_supports = len(support_ids) == len(set(support_ids))
        checks.extend(
            [
                {
                    "clause": "4.5.1",
                    "condition": "support identifiers are unique",
                    "satisfied": unique_supports,
                },
                {
                    "clause": "4.5.1",
                    "condition": "all model supports are listed",
                    "satisfied": d["all_supports_listed_verified"],
                    "evidence_reference": d["support_list_evidence_reference"],
                },
            ]
        )
        return result(
            op,
            ["4.5.1"],
            {
                "supports": support_results,
                "all_support_conditions_satisfied": all(
                    support["support_conditions_satisfied"] for support in support_results
                )
                and unique_supports
                and d["all_supports_listed_verified"],
            },
            checks,
            limitations=[
                "Tolerances are project-selected; the operation compares supplied analysis "
                "translations and rotations with the declared support restraints.",
                "Support identity, restraint selection and list completeness are supplied "
                "evidence. Other member restraints, member-span equilibrium and analysis "
                "validity are not checked.",
            ],
        )
    if op == "notional_horizontal_load":
        return result(
            op,
            ["3.2.4"],
            {
                "notional_horizontal_load_kn": 0.002 * d["floor_vertical_design_load_kn"],
            },
            limitations=[
                "Multi-storey dead/live combinations only; excludes stability limit state.",
            ],
        )
    if op == "stability":
        resistance = 0.9 * d["stabilising_dead_effect"] + d["resisting_design_capacity"]
        check = {
            "clause": "3.3",
            "resistance": resistance,
            "design_effect": d["destabilising_design_effect"],
            "satisfied": resistance >= d["destabilising_design_effect"],
        }
        return result(
            op,
            ["3.3"],
            {"design_resistance_effect": resistance},
            [check],
            [
                "Use matching effects and units; resistance already includes the appropriate phi.",
            ],
        )
    check = {
        "clause": "3.5.3",
        "utilisation": abs(d["deflection_mm"]) / d["deflection_limit_mm"],
        "satisfied": abs(d["deflection_mm"]) <= d["deflection_limit_mm"],
    }
    return result(
        op,
        ["3.5.2", "3.5.3"],
        {"limit_basis": d["limit_basis"]},
        [check],
        [
            "Use serviceability combinations and elastic deflections; check vibration separately.",
        ],
    )
