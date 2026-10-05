"""Connection component calculations reviewed against AS 4100:2020 Section 9."""

from collections.abc import Mapping
from math import cos, fsum, hypot, isclose, isfinite, pi, radians, sin, sqrt
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

from .validation import validate_standard_strengths


def _number(minimum=0, positive=False):
    return {"type": "number", "exclusiveMinimum" if positive else "minimum": minimum}


def _schema(kind, fields, optional=()):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["check_type", *(field for field in fields if field not in optional)],
        "properties": {"check_type": {"const": kind}, **fields},
    }


P = _number(positive=True)
N = _number()
SIGNED = {"type": "number"}
QUALITY = {"enum": ["SP", "GP"]}
BOOL = {"type": "boolean"}
TEXT_REFERENCE = {"type": "string", "minLength": 1, "maxLength": 200}
POINT = {"type": "array", "minItems": 2, "maxItems": 2, "items": SIGNED}
VECTOR3 = {"type": "array", "minItems": 3, "maxItems": 3, "items": SIGNED}
CONNECTION_ACTIONS = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "axial_kn": SIGNED,
        "shear_x_kn": SIGNED,
        "shear_y_kn": SIGNED,
        "moment_x_knm": SIGNED,
        "moment_y_knm": SIGNED,
        "moment_z_knm": SIGNED,
    },
    "required": [
        "axial_kn",
        "shear_x_kn",
        "shear_y_kn",
        "moment_x_knm",
        "moment_y_knm",
        "moment_z_knm",
    ],
}
FIELDS = {
    "bolt": {
        "ultimate_strength_mpa": P,
        "minor_area_mm2": P,
        "shank_area_mm2": P,
        "tensile_area_mm2": P,
        "threaded_planes": {"type": "integer", "minimum": 0},
        "plain_planes": {"type": "integer", "minimum": 0},
        "grade": {"enum": ["4.6", "8.8", "10.9"]},
        "lap_length_mm": N,
        "filler_thickness_mm": {"type": "number", "minimum": 0, "exclusiveMaximum": 20},
        "filler_thickness_by_shear_plane_mm": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": {"type": "number", "minimum": 0, "exclusiveMaximum": 20},
        },
        "filler_plate_extends_beyond_connection_verified": BOOL,
        "filler_plate_force_transfer_through_combined_section_verified": BOOL,
        "shear_action_kn": N,
        "tension_action_kn": N,
        "prying_tension_kn": N,
        "prying_force_assessment_verified": {"const": True},
    },
    "bearing": {
        "diameter_mm": P,
        "ply_thickness_mm": P,
        "ultimate_strength_mpa": P,
        "effective_edge_distance_mm": P,
        "action_kn": N,
    },
    "slip": {
        "slip_factor": P,
        "interfaces": {"type": "integer", "minimum": 1},
        "installation_tension_kn": P,
        "hole_type": {"enum": ["standard", "short_slot", "oversize", "long_slot"]},
        "shear_action_kn": N,
        "tension_action_kn": N,
        "clean_as_rolled_contact_surfaces_verified": BOOL,
        "slip_factor_test_evidence_verified": BOOL,
        "friction_bolt_category_and_surface_treatment_masking_drawings_verified": BOOL,
    },
    "slip_factor_test": {
        "nominal_bolt_diameter_mm": {"enum": [16, 20, 24, 30, 36]},
        "bolt_grade": {"enum": ["8.8", "10.9"]},
        "bolt_tension_method": {"enum": ["calibration_curve", "equation_j1"]},
        "symmetrical_double_cover_butt_specimen_verified": {"const": True},
        "bolts_clear_of_bearing_in_loading_direction_verified": {"const": True},
        "friction_surface_condition_matches_field_verified": {"const": True},
        "machining_oil_contamination_absent_if_used_verified": {"const": True},
        "specimen_geometry": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "bolt_centre_spacing_mm",
                "left_bolt_to_test_section_end_mm",
                "right_bolt_to_test_section_end_mm",
                "upper_bolt_edge_distance_mm",
                "lower_bolt_edge_distance_mm",
                "inner_plate_thicknesses_mm",
                "cover_plate_thicknesses_mm",
                "cover_plate_hole_diameter_mm",
                "inner_plate_hole_diameter_mm",
                "butt_gap_mm",
            ],
            "properties": {
                "bolt_centre_spacing_mm": P,
                "left_bolt_to_test_section_end_mm": P,
                "right_bolt_to_test_section_end_mm": P,
                "upper_bolt_edge_distance_mm": P,
                "lower_bolt_edge_distance_mm": P,
                "inner_plate_thicknesses_mm": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": P,
                },
                "cover_plate_thicknesses_mm": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": P,
                },
                "cover_plate_hole_diameter_mm": P,
                "inner_plate_hole_diameter_mm": P,
                "butt_gap_mm": P,
            },
        },
        "specimen_bolt_tensioning_matches_field_verified": {"const": True},
        "initial_snug_condition_finger_tight_verified": {"const": True},
        "extension_measurement_immediately_before_test_verified": {"const": True},
        "extension_instrument_resolution_mm": {
            "type": "number",
            "exclusiveMinimum": 0,
            "maximum": 0.003,
        },
        "instrumentation_layout_per_appendix_j_verified": {"const": True},
        "instrumentation_deformation_reduction_per_appendix_j_verified": {"const": True},
        "tensile_loading_only_verified": {"const": True},
        "slip_load_identification_per_appendix_j_verified": {"const": True},
        "appendix_j_test_report_reference": TEXT_REFERENCE,
        "calibration_test_bolt_count": {"type": "integer", "minimum": 3, "maximum": 1000},
        "calibration_curve_reference": TEXT_REFERENCE,
        "calibration_test_bolts_from_test_batch_verified": {"const": True},
        "calibration_grip_and_measurement_method_match_verified": {"const": True},
        "calibration_curve_based_on_mean_result_verified": {"const": True},
        "specified_bolt_proof_load_kn": P,
        "proof_load_reference": TEXT_REFERENCE,
        "bolt_proof_load_specification_verified": {"const": True},
        "bolt_geometry_source_reference": TEXT_REFERENCE,
        "bolt_geometry_matches_tested_assembly_verified": {"const": True},
        "specimens": {
            "type": "array",
            "minItems": 3,
            "maxItems": 100,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["specimen_id", "bolts", "loading_increments"],
                "properties": {
                    "specimen_id": {"type": "string", "minLength": 1, "maxLength": 80},
                    "loading_increments": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 1000,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "load_before_kn",
                                "load_after_kn",
                                "maximum_rate_kn_per_min",
                                "loading_rate_approximately_uniform_verified",
                            ],
                            "properties": {
                                "load_before_kn": N,
                                "load_after_kn": P,
                                "maximum_rate_kn_per_min": P,
                                "loading_rate_approximately_uniform_verified": {"const": True},
                                "preceding_load_creep_effectively_ceased_verified": {"const": True},
                            },
                        },
                    },
                    "bolts": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "bolt_id",
                                "bolt_extension_mm",
                                "slip_load_method",
                            ],
                            "properties": {
                                "bolt_id": {"type": "string", "minLength": 1, "maxLength": 80},
                                "slip_load_method": {
                                    "enum": ["clear_observed_slip", "0.13_mm_deformation"]
                                },
                                "slip_load_kn": P,
                                "bolt_extension_mm": P,
                                "calibrated_bolt_tension_kn": P,
                                "deformation_readings": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 10000,
                                    "items": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": [
                                            "load_kn",
                                            "left_edge_deformation_mm",
                                            "right_edge_deformation_mm",
                                        ],
                                        "properties": {
                                            "load_kn": N,
                                            "left_edge_deformation_mm": N,
                                            "right_edge_deformation_mm": N,
                                        },
                                    },
                                },
                                "unthreaded_grip_length_mm": N,
                                "unthreaded_shank_area_mm2": P,
                                "threaded_grip_length_mm": N,
                                "nut_thickness_mm": P,
                                "tensile_stress_area_mm2": P,
                            },
                        },
                    },
                },
            },
        },
    },
    "block_shear": {
        "yield_strength_mpa": P,
        "ultimate_strength_mpa": P,
        "gross_shear_area_mm2": P,
        "net_shear_area_mm2": P,
        "net_tension_area_mm2": P,
        "uniform_tension": BOOL,
        "action_kn": N,
    },
    "block_shear_paths": {
        "yield_strength_mpa": P,
        "ultimate_strength_mpa": P,
        "thickness_mm": P,
        "candidate_paths": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "path_id",
                    "gross_shear_length_mm",
                    "net_shear_length_mm",
                    "net_tension_length_mm",
                    "uniform_tension",
                ],
                "properties": {
                    "path_id": {"type": "string", "minLength": 1, "maxLength": 80},
                    "gross_shear_length_mm": P,
                    "net_shear_length_mm": P,
                    "net_tension_length_mm": P,
                    "uniform_tension": BOOL,
                },
            },
        },
        "rupture_paths_complete_and_net_lengths_verified": {"const": True},
        "action_kn": N,
    },
    "pin": {
        "yield_strength_mpa": P,
        "diameter_mm": P,
        "shear_planes": {"type": "integer", "minimum": 1},
        "ply_thickness_mm": P,
        "rotates": BOOL,
        "shear_action_kn": N,
        "bearing_action_kn": N,
        "moment_action_knm": N,
    },
    "fillet": {
        "weld_strength_mpa": P,
        "throat_mm": P,
        "effective_length_mm": P,
        "quality": QUALITY,
        "thin_rhs_longitudinal": BOOL,
        "lap_length_mm": N,
        "action_kn": N,
    },
    "fillet_design": {
        "weld_strength_mpa": P,
        "quality": QUALITY,
        "leg_1_mm": P,
        "leg_2_mm": P,
        "included_angle_deg": {"type": "number", "minimum": 5, "maximum": 175},
        "root_gap_mm": N,
        "thickest_part_mm": P,
        "thinnest_part_mm": P,
        "edge_material_thickness_mm": P,
        "edge_built_out_verified": BOOL,
        "reinforces_butt_weld": BOOL,
        "overall_length_per_segment_mm": P,
        "segment_count": {"type": "integer", "minimum": 1, "maximum": 10000},
        "intermittent_segment": BOOL,
        "clear_spacing_mm": N,
        "at_built_up_member_end": BOOL,
        "member_force_type": {"enum": ["compression", "tension", "other"]},
        "forms_built_up_member": BOOL,
        "parallel_weld_count": {"type": "integer", "enum": [1, 2]},
        "parallel_load_share_verified": BOOL,
        "transverse_weld_spacing_mm": N,
        "thin_rhs_longitudinal": BOOL,
        "lap_length_mm": N,
        "automatic_arc_welding_process_verified": {"const": True},
        "production_weld_macro_test_verified": {"const": True},
        "macro_test_required_penetration_achieved_verified": {"const": True},
        "macro_test_record_reference": TEXT_REFERENCE,
        "macro_test_additional_penetration_mm": N,
        "action_kn": N,
    },
    "built_up_component_end_weld": {
        "connected_component_width_mm": P,
        "weld_length_per_joint_line_mm": P,
        "side_fillet_only": BOOL,
        "tapered_component": BOOL,
        "widest_component_width_mm": P,
        "taper_length_mm": N,
    },
    "cap_plate_weld": {
        "member_width_at_contact_face_mm": P,
        "weld_length_per_joint_line_mm": P,
    },
    "beam_compression_member_weld": {
        "beam_depth_mm": P,
        "compression_member_max_dimension_mm": P,
        "connection_restraint": {"enum": ["unrestrained", "restrained"]},
        "weld_length_between_beam_faces_mm": P,
        "weld_extension_above_top_mm": N,
        "weld_extension_below_bottom_mm": N,
    },
    "packing_construction": {
        "packing_thickness_mm": P,
        "too_thin_for_adequate_welds": BOOL,
        "too_thin_to_prevent_buckling": BOOL,
        "required_edge_weld_sizes_mm": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": P,
        },
        "provided_edge_weld_sizes_mm": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": N,
        },
        "trimmed_flush_with_member_edges": BOOL,
        "extends_beyond_member_edges": BOOL,
        "welded_to_fitted_piece": BOOL,
    },
    "complete_butt": {
        "weaker_part_nominal_capacity_kn": P,
        "quality": QUALITY,
        "qualified_matching_consumable": {"const": True},
        "action_kn": N,
    },
    "butt_weld_transition": {
        "dimension_change_mm": P,
        "effective_transition_run_mm": P,
        "transition_method": {"enum": ["chamfer_parent_part", "slope_weld_surface", "combined"]},
        "tension_loaded_joint_verified": {"const": True},
        "smooth_transition_verified": {"const": True},
        "fatigue_slope_limit": {
            "type": "number",
            "exclusiveMinimum": 0,
            "maximum": 1,
        },
        "fatigue_slope_limit_verified": {"const": True},
        "fatigue_assessment_reference": TEXT_REFERENCE,
    },
    "incomplete_butt_design": {
        "weld_strength_mpa": P,
        "quality": QUALITY,
        "preparation_type": {"enum": ["single_v", "double_v"]},
        "preparation_depth_mm": P,
        "double_v_preparation_depths_mm": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": P,
        },
        "preparation_angle_deg": {
            "type": "number",
            "exclusiveMinimum": 0,
            "maximum": 180,
        },
        "continuous_full_size_weld_length_mm": P,
        "thin_rhs_longitudinal": BOOL,
        "non_prequalified_v_preparation_verified": {"const": True},
        "welding_procedure_and_consumable_basis_verified": {"const": True},
        "automatic_arc_welding_process_verified": {"const": True},
        "production_weld_macro_test_verified": {"const": True},
        "macro_test_required_penetration_achieved_verified": {"const": True},
        "macro_test_record_reference": TEXT_REFERENCE,
        "macro_test_penetration_beyond_preparation_mm": N,
        "action_kn": N,
    },
    "prequalified_incomplete_butt_design": {
        "weld_strength_mpa": P,
        "quality": QUALITY,
        "prequalified_design_throat_mm": P,
        "prequalified_preparation_verified": {"const": True},
        "prequalified_preparation_reference": TEXT_REFERENCE,
        "welding_procedure_and_consumable_basis_verified": {"const": True},
        "continuous_full_size_weld_length_mm": P,
        "thin_rhs_longitudinal": BOOL,
        "preparation_depth_mm": P,
        "automatic_arc_welding_process_verified": {"const": True},
        "production_weld_macro_test_verified": {"const": True},
        "macro_test_required_penetration_achieved_verified": {"const": True},
        "macro_test_record_reference": TEXT_REFERENCE,
        "macro_test_penetration_beyond_preparation_mm": N,
        "action_kn": N,
    },
    "plug_slot": {
        "weld_strength_mpa": P,
        "effective_area_mm2": P,
        "quality": QUALITY,
        "permitted_shear_application": {"const": True},
        "action_kn": N,
        "hole_shape": {"enum": ["circular", "round_ended_slot", "rectangular_slot"]},
        "hole_diameter_mm": P,
        "slot_length_mm": P,
        "slot_width_mm": P,
        "hole_geometry_verified": {"const": True},
    },
    "layout": {
        "diameter_mm": P,
        "thinnest_ply_mm": P,
        "pitch_mm": P,
        "edge_distance_mm": P,
        "edge_type": {"enum": ["sheared", "machined", "rolled"]},
        "pitch_case": {"enum": ["general", "outside_line", "non_load_noncorrosive"]},
    },
    "hole_deduction": {
        "gross_area_mm2": P,
        "thickness_mm": P,
        "straight_hole_width_sum_mm": N,
        "zigzag_hole_width_sum_mm": N,
        "stagger_pairs": {
            "type": "array",
            "items": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "prefixItems": [N, P],
                "items": False,
            },
        },
    },
    "hole_deduction_layout": {
        "plate_width_mm": P,
        "thickness_mm": P,
        "flat_uniform_plate_and_complete_hole_layout_verified": {"const": True},
        "design_action_axis_verified": {"const": True},
        "holes": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "hole_id",
                    "longitudinal_mm",
                    "transverse_mm",
                    "gross_hole_width_mm",
                ],
                "properties": {
                    "hole_id": {"type": "string", "minLength": 1, "maxLength": 80},
                    "longitudinal_mm": SIGNED,
                    "transverse_mm": N,
                    "gross_hole_width_mm": P,
                },
            },
        },
    },
    "angle_hole_deduction": {
        "gross_area_mm2": P,
        "thickness_mm": P,
        "straight_hole_width_sum_mm": P,
        "straight_hole_width_sum_verified": {"const": True},
        "angle_geometry_and_back_marks_verified": {"const": True},
        "candidate_paths_complete_and_ordered_verified": {"const": True},
        "candidate_paths": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["path_id", "holes"],
                "properties": {
                    "path_id": {"type": "string", "minLength": 1, "maxLength": 80},
                    "holes": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 100,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "hole_id",
                                "angle_leg_id",
                                "longitudinal_mm",
                                "back_mark_mm",
                                "gross_hole_width_mm",
                            ],
                            "properties": {
                                "hole_id": {"type": "string", "minLength": 1, "maxLength": 80},
                                "angle_leg_id": {"enum": ["leg_1", "leg_2"]},
                                "longitudinal_mm": SIGNED,
                                "back_mark_mm": P,
                                "gross_hole_width_mm": P,
                            },
                        },
                    },
                },
            },
        },
    },
    "angle_hole_deduction_layout": {
        "gross_area_mm2": P,
        "thickness_mm": P,
        "leg_1_width_mm": P,
        "leg_2_width_mm": P,
        "angle_geometry_and_back_marks_verified": {"const": True},
        "complete_angle_hole_layout_and_action_axis_verified": {"const": True},
        "holes": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "hole_id",
                    "angle_leg_id",
                    "longitudinal_mm",
                    "back_mark_mm",
                    "gross_hole_width_mm",
                ],
                "properties": {
                    "hole_id": {"type": "string", "minLength": 1, "maxLength": 80},
                    "angle_leg_id": {"enum": ["leg_1", "leg_2"]},
                    "longitudinal_mm": SIGNED,
                    "back_mark_mm": P,
                    "gross_hole_width_mm": P,
                },
            },
        },
    },
    "minimum_beam_shear_action": {
        "actual_design_shear_kn": N,
        "member_design_shear_capacity_kn": P,
        "simple_construction_beam_connection_verified": {"const": True},
        "excluded_connection_arrangement_absent_verified": {"const": True},
        "reaction_shear_direction_unit_vector": VECTOR3,
        "reaction_shear_eccentricity_vector_mm": VECTOR3,
        "reaction_shear_eccentricity_assessment_verified": {"const": True},
        "connection_design_shear_capacity_kn": N,
    },
    "minimum_rigid_connection_action": {
        "rigid_construction_connection_verified": {"const": True},
        "actual_design_moment_knm": N,
        "member_design_moment_capacity_knm": P,
        "excluded_connection_arrangement_absent_verified": {"const": True},
        "connection_design_moment_capacity_knm": N,
    },
    "minimum_member_end_action": {
        "connection_at_member_end_verified": {"const": True},
        "member_end_case": {
            "enum": [
                "tension_member_end",
                "compression_member_end",
                "threaded_tension_bracing_with_turnbuckles",
            ]
        },
        "actual_design_axial_action_kn": N,
        "member_design_axial_capacity_kn": P,
        "threaded_bracing_turnbuckle_arrangement_verified": BOOL,
        "excluded_connection_arrangement_absent_verified": {"const": True},
        "connection_design_axial_capacity_kn": N,
    },
    "minimum_axial_splice_action": {
        "axial_member_splice_verified": {"const": True},
        "splice_case": {
            "enum": [
                "axial_tension",
                "compression_full_contact",
                "compression_not_full_contact",
            ]
        },
        "actual_design_axial_action_kn": N,
        "member_design_axial_capacity_kn": P,
        "full_contact_bearing_verified": BOOL,
        "splice_parts_and_fasteners_hold_all_parts_in_line_verified": BOOL,
        "excluded_connection_arrangement_absent_verified": {"const": True},
        "connection_design_axial_capacity_kn": N,
    },
    "minimum_combined_splice_actions": {
        "combined_axial_bending_splice_verified": {"const": True},
        "splice_case": {
            "enum": [
                "axial_tension",
                "compression_full_contact",
                "compression_not_full_contact",
            ]
        },
        "actual_design_axial_action_kn": N,
        "member_design_axial_capacity_kn": P,
        "full_contact_bearing_verified": BOOL,
        "splice_parts_and_fasteners_hold_all_parts_in_line_verified": BOOL,
        "actual_design_moment_knm": N,
        "member_design_moment_capacity_knm": P,
        "splice_between_effective_lateral_supports_verified": BOOL,
        "effective_lateral_support_distance_mm": P,
        "amplification_factor_type": {"enum": ["delta_b", "delta_s"]},
        "amplification_factor": P,
        "amplification_factor_verified": {"const": True},
        "excluded_connection_arrangement_absent_verified": {"const": True},
        "connection_design_axial_capacity_kn": N,
        "connection_design_moment_capacity_knm": N,
    },
    "minimum_compression_splice_between_supports": {
        "compression_member_splice_verified": {"const": True},
        "actual_design_axial_action_kn": N,
        "actual_design_moment_knm": N,
        "member_design_axial_capacity_kn": P,
        "full_contact_bearing_verified": BOOL,
        "splice_parts_and_fasteners_hold_all_parts_in_line_verified": BOOL,
        "splice_between_effective_lateral_supports_verified": {"const": True},
        "effective_lateral_support_distance_mm": P,
        "amplification_factor_type": {"enum": ["delta_b", "delta_s"]},
        "amplification_factor": P,
        "amplification_factor_verified": {"const": True},
        "excluded_connection_arrangement_absent_verified": {"const": True},
        "connection_design_axial_capacity_kn": N,
        "connection_design_moment_capacity_knm": N,
    },
    "minimum_flexural_splice_action": {
        "flexural_splice_not_shear_only_verified": {"const": True},
        "actual_design_moment_knm": N,
        "member_design_moment_capacity_knm": P,
        "excluded_connection_arrangement_absent_verified": {"const": True},
        "connection_design_moment_capacity_knm": N,
    },
    "shear_only_splice_eccentric_action": {
        "actual_design_shear_kn": N,
        "force_eccentricity_mm": N,
        "shear_only_splice_verified": {"const": True},
        "excluded_connection_arrangement_absent_verified": {"const": True},
        "connection_design_shear_capacity_kn": N,
        "connection_design_moment_capacity_knm": N,
    },
    "joint_eccentricity_action": {
        "connection_detail_case": {
            "enum": [
                "general",
                "single_angle_welded_end",
                "double_angle_welded_end",
                "bolted_single_angle_member",
            ]
        },
        "fatigue_loading": BOOL,
        "fatigue_detail_eccentricity_assessment_verified": BOOL,
        "centroidal_axes_meet_practicable_verified": BOOL,
        "centroidal_axes_meet_at_joint_verified": BOOL,
        "force_kn": VECTOR3,
        "eccentricity_vector_mm": VECTOR3,
        "joint_geometry_and_load_line_assessed_verified": {"const": True},
    },
    "fastener_selection_suitability": {
        "selected_fastener_system": {
            "enum": [
                "friction_type_8_8_TF",
                "friction_type_10_9_TF",
                "fitted_bolt",
                "weld",
                "locking_device",
                "ordinary_bolt",
                "other",
            ]
        },
        "serviceability_slip_to_be_avoided": BOOL,
        "impact_or_vibration_present": BOOL,
        "service_and_dynamic_action_assessment_verified": {"const": True},
    },
    "combined_connection_action_assignment": {
        "component_groups": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "group_id": {"type": "string", "minLength": 1, "maxLength": 80},
                    "fastener_class": {"enum": ["non_slip", "slip_type", "weld"]},
                },
                "required": ["group_id", "fastener_class"],
            },
        },
        "load_cases": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "case_id": {"type": "string", "minLength": 1, "maxLength": 80},
                    "stage": {
                        "enum": [
                            "non_weld_action",
                            "initially_applied_to_welds",
                            "after_welding",
                        ]
                    },
                    "actions": CONNECTION_ACTIONS,
                    "shares": {
                        "type": "array",
                        "maxItems": 100,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "group_id": {
                                    "type": "string",
                                    "minLength": 1,
                                    "maxLength": 80,
                                },
                                "fraction": {"type": "number", "minimum": 0, "maximum": 1},
                            },
                            "required": ["group_id", "fraction"],
                        },
                    },
                },
                "required": ["case_id", "stage", "actions", "shares"],
            },
        },
        "installation_sequence_assessed_verified": {"const": True},
    },
}
FIELDS["bolt_group"] = {
    **FIELDS["bolt"],
    "points_mm": {"type": "array", "minItems": 2, "items": POINT},
    "force_x_kn": SIGNED,
    "force_y_kn": SIGNED,
    "moment_z_knm": SIGNED,
}
FIELDS["bolt_group_out_of_plane"] = {
    **{
        field: FIELDS["bolt"][field]
        for field in (
            "ultimate_strength_mpa",
            "minor_area_mm2",
            "shank_area_mm2",
            "tensile_area_mm2",
            "threaded_planes",
            "plain_planes",
            "grade",
            "lap_length_mm",
            "filler_thickness_mm",
            "filler_thickness_by_shear_plane_mm",
            "filler_plate_extends_beyond_connection_verified",
            "filler_plate_force_transfer_through_combined_section_verified",
        )
    },
    "bolt_actions": {
        "type": "array",
        "minItems": 1,
        "maxItems": 100,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "bolt_id": {"type": "string", "minLength": 1, "maxLength": 80},
                "position_mm": POINT,
                "shear_x_kn": SIGNED,
                "shear_y_kn": SIGNED,
                "tension_action_kn": N,
                "prying_tension_kn": N,
                "prying_force_assessment_verified": {"const": True},
            },
            "required": [
                "bolt_id",
                "position_mm",
                "shear_x_kn",
                "shear_y_kn",
                "tension_action_kn",
                "prying_tension_kn",
                "prying_force_assessment_verified",
            ],
        },
    },
    "group_force_x_kn": SIGNED,
    "group_force_y_kn": SIGNED,
    "group_tension_kn": N,
    "group_moment_x_knm": SIGNED,
    "group_moment_y_knm": SIGNED,
    "group_moment_z_knm": SIGNED,
    "positions_share_action_reference_verified": {"const": True},
    "bolt_action_distribution_assessed_under_clause_9_1_3": {"const": True},
    "connection_element_deformation_capacity_and_stability_verified": {"const": True},
}
FIELDS["bolt_group_elastic_3d"] = {
    **{
        field: FIELDS["bolt"][field]
        for field in (
            "ultimate_strength_mpa",
            "minor_area_mm2",
            "shank_area_mm2",
            "tensile_area_mm2",
            "threaded_planes",
            "plain_planes",
            "grade",
            "lap_length_mm",
            "filler_thickness_mm",
            "filler_thickness_by_shear_plane_mm",
            "filler_plate_extends_beyond_connection_verified",
            "filler_plate_force_transfer_through_combined_section_verified",
        )
    },
    "bolt_layout": {
        "type": "array",
        "minItems": 3,
        "maxItems": 100,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "bolt_id": {"type": "string", "minLength": 1, "maxLength": 80},
                "position_mm": POINT,
                "prying_tension_kn": N,
                "prying_force_assessment_verified": {"const": True},
            },
            "required": [
                "bolt_id",
                "position_mm",
                "prying_tension_kn",
                "prying_force_assessment_verified",
            ],
        },
    },
    "group_force_x_kn": SIGNED,
    "group_force_y_kn": SIGNED,
    "group_tension_kn": N,
    "group_moment_x_knm": SIGNED,
    "group_moment_y_knm": SIGNED,
    "group_moment_z_knm": SIGNED,
    "group_actions_at_centroid_verified": {"const": True},
    "rigid_plates_and_equal_bolt_stiffness_verified": {"const": True},
    "elastic_method_experimental_basis_verified": {"const": True},
    "connection_element_deformation_capacity_and_stability_verified": {"const": True},
}
FIELDS["weld_group"] = {
    "weld_strength_mpa": P,
    "throat_mm": P,
    "quality": QUALITY,
    "segments_mm": {
        "type": "array",
        "minItems": 1,
        "items": {"type": "array", "minItems": 2, "maxItems": 2, "items": POINT},
    },
    **{f"force_{a}_kn": SIGNED for a in "xyz"},
    **{f"moment_{a}_knm": SIGNED for a in "xyz"},
}
FIELDS["combined_weld_types"] = {
    "design_action_basis": {"enum": ["force_kn", "moment_knm"]},
    "design_action": N,
    "complete_nonoverlapping_weld_component_set_verified": {"const": True},
    "common_action_basis_and_direction_verified": {"const": True},
    "weld_components": {
        "type": "array",
        "minItems": 2,
        "maxItems": 100,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "component_id",
                "weld_type",
                "design_capacity",
                "capacity_calculation_reference",
                "section_9_capacity_basis_verified",
            ],
            "properties": {
                "component_id": {"type": "string", "minLength": 1, "maxLength": 80},
                "weld_type": {"enum": ["fillet", "butt", "plug_or_slot", "compound"]},
                "design_capacity": P,
                "capacity_calculation_reference": TEXT_REFERENCE,
                "section_9_capacity_basis_verified": {"const": True},
            },
        },
    },
}
FILLER_PLATE_ASSESSMENT_FIELDS = (
    "filler_plate_extends_beyond_connection_verified",
    "filler_plate_force_transfer_through_combined_section_verified",
)
FILLER_PLATE_OPTIONAL_FIELDS = (
    "filler_thickness_mm",
    "filler_thickness_by_shear_plane_mm",
    *FILLER_PLATE_ASSESSMENT_FIELDS,
)
SLIP_SURFACE_OPTIONAL_FIELDS = (
    "clean_as_rolled_contact_surfaces_verified",
    "slip_factor_test_evidence_verified",
    "friction_bolt_category_and_surface_treatment_masking_drawings_verified",
)
SLIP_FACTOR_TEST_OPTIONAL_FIELDS = (
    "calibration_test_bolt_count",
    "calibration_curve_reference",
    "calibration_test_bolts_from_test_batch_verified",
    "calibration_grip_and_measurement_method_match_verified",
    "calibration_curve_based_on_mean_result_verified",
    "specified_bolt_proof_load_kn",
    "proof_load_reference",
    "bolt_proof_load_specification_verified",
    "bolt_geometry_source_reference",
    "bolt_geometry_matches_tested_assembly_verified",
)
OPTIONAL_FIELDS = {
    "bolt": FILLER_PLATE_OPTIONAL_FIELDS,
    "bolt_group": FILLER_PLATE_OPTIONAL_FIELDS,
    "bolt_group_out_of_plane": FILLER_PLATE_OPTIONAL_FIELDS,
    "bolt_group_elastic_3d": FILLER_PLATE_OPTIONAL_FIELDS,
    "slip": SLIP_SURFACE_OPTIONAL_FIELDS,
    "slip_factor_test": SLIP_FACTOR_TEST_OPTIONAL_FIELDS,
    "fillet_design": (
        "automatic_arc_welding_process_verified",
        "production_weld_macro_test_verified",
        "macro_test_required_penetration_achieved_verified",
        "macro_test_record_reference",
        "macro_test_additional_penetration_mm",
    ),
    "plug_slot": (
        "effective_area_mm2",
        "hole_shape",
        "hole_diameter_mm",
        "slot_length_mm",
        "slot_width_mm",
        "hole_geometry_verified",
    ),
    "butt_weld_transition": (
        "fatigue_slope_limit",
        "fatigue_slope_limit_verified",
        "fatigue_assessment_reference",
    ),
    "incomplete_butt_design": (
        "preparation_depth_mm",
        "double_v_preparation_depths_mm",
        "automatic_arc_welding_process_verified",
        "production_weld_macro_test_verified",
        "macro_test_required_penetration_achieved_verified",
        "macro_test_record_reference",
        "macro_test_penetration_beyond_preparation_mm",
    ),
    "prequalified_incomplete_butt_design": (
        "preparation_depth_mm",
        "automatic_arc_welding_process_verified",
        "production_weld_macro_test_verified",
        "macro_test_required_penetration_achieved_verified",
        "macro_test_record_reference",
        "macro_test_penetration_beyond_preparation_mm",
    ),
    "minimum_beam_shear_action": (
        "reaction_shear_direction_unit_vector",
        "reaction_shear_eccentricity_vector_mm",
        "reaction_shear_eccentricity_assessment_verified",
        "connection_design_shear_capacity_kn",
    ),
    "minimum_rigid_connection_action": ("connection_design_moment_capacity_knm",),
    "minimum_member_end_action": ("connection_design_axial_capacity_kn",),
    "minimum_axial_splice_action": ("connection_design_axial_capacity_kn",),
    "minimum_combined_splice_actions": (
        "effective_lateral_support_distance_mm",
        "amplification_factor_type",
        "amplification_factor",
        "amplification_factor_verified",
        "connection_design_axial_capacity_kn",
        "connection_design_moment_capacity_knm",
    ),
    "minimum_compression_splice_between_supports": (
        "connection_design_axial_capacity_kn",
        "connection_design_moment_capacity_knm",
    ),
    "minimum_flexural_splice_action": ("connection_design_moment_capacity_knm",),
    "shear_only_splice_eccentric_action": (
        "connection_design_shear_capacity_kn",
        "connection_design_moment_capacity_knm",
    ),
}
MINIMUM_ACTION_CHECKS = frozenset(
    {
        "minimum_beam_shear_action",
        "minimum_rigid_connection_action",
        "minimum_member_end_action",
        "minimum_axial_splice_action",
        "minimum_combined_splice_actions",
        "minimum_compression_splice_between_supports",
        "minimum_flexural_splice_action",
        "shear_only_splice_eccentric_action",
    }
)
INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "oneOf": [_schema(k, v, optional=OPTIONAL_FIELDS.get(k, ())) for k, v in FIELDS.items()],
}
INPUT_SCHEMAS_BY_CHECK_TYPE = {
    schema["properties"]["check_type"]["const"]: schema for schema in INPUT_SCHEMA["oneOf"]
}
OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["standard", "check_type", "checks", "scope"],
    "additionalProperties": False,
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "check_type": {"enum": list(FIELDS)},
        "checks": {"type": "object"},
        "intermediate": {"type": "object"},
        "scope": {"type": "string"},
    },
}


def _finite(value):
    if isinstance(value, Mapping):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return not isinstance(value, (int, float)) or isinstance(value, bool) or isfinite(value)


def _hole_deduction_layout(d):
    holes = sorted(
        d["holes"],
        key=lambda hole: (
            hole["transverse_mm"],
            hole["longitudinal_mm"],
            hole["hole_id"],
        ),
    )
    hole_ids = [hole["hole_id"] for hole in holes]
    positions = [(hole["longitudinal_mm"], hole["transverse_mm"]) for hole in holes]
    if len(set(hole_ids)) != len(hole_ids):
        raise ValueError("Hole IDs must be unique.")
    if len(set(positions)) != len(positions):
        raise ValueError("Hole centre positions must be distinct.")
    for hole in holes:
        half_width = hole["gross_hole_width_mm"] / 2
        if (
            hole["gross_hole_width_mm"] > d["plate_width_mm"]
            or hole["transverse_mm"] < half_width
            or hole["transverse_mm"] + half_width > d["plate_width_mm"]
        ):
            raise ValueError("Every gross hole width must fit within the plate edges.")

    straight_rows = {}
    for hole in holes:
        straight_rows.setdefault(hole["longitudinal_mm"], []).append(hole)
    straight_candidates = [
        {
            "longitudinal_mm": x,
            "hole_ids": [hole["hole_id"] for hole in row],
            "hole_width_sum_mm": fsum(hole["gross_hole_width_mm"] for hole in row),
        }
        for x, row in sorted(straight_rows.items())
    ]
    straight = max(straight_candidates, key=lambda candidate: candidate["hole_width_sum_mm"])

    # Every progressively ordered sequence is a Clause 9.1.10.3 zig-zag
    # candidate. The DAG recurrence finds the governing sequence in O(n^2)
    # without materializing the potentially exponential set of paths.
    best_widths = []
    predecessors = []
    transitions_considered = 0
    for j, hole in enumerate(holes):
        best_prefix = 0.0
        predecessor = None
        for i in range(j):
            previous = holes[i]
            gauge = hole["transverse_mm"] - previous["transverse_mm"]
            if gauge <= 0:
                continue
            transitions_considered += 1
            pitch = abs(hole["longitudinal_mm"] - previous["longitudinal_mm"])
            stagger_correction = pitch * pitch / (4 * gauge)
            candidate_prefix = best_widths[i] - stagger_correction
            if candidate_prefix > best_prefix:
                best_prefix = candidate_prefix
                predecessor = i
        best_widths.append(hole["gross_hole_width_mm"] + best_prefix)
        predecessors.append(predecessor)

    zigzag_end = max(range(len(holes)), key=lambda index: best_widths[index])
    zigzag_indices = []
    while zigzag_end is not None:
        zigzag_indices.append(zigzag_end)
        zigzag_end = predecessors[zigzag_end]
    zigzag_indices.reverse()
    zigzag_path = [holes[index] for index in zigzag_indices]
    zigzag_hole_width_sum = fsum(hole["gross_hole_width_mm"] for hole in zigzag_path)
    stagger_pairs = []
    for first, second in zip(zigzag_path, zigzag_path[1:], strict=False):
        pitch = abs(second["longitudinal_mm"] - first["longitudinal_mm"])
        gauge = second["transverse_mm"] - first["transverse_mm"]
        stagger_pairs.append(
            {
                "from_hole_id": first["hole_id"],
                "to_hole_id": second["hole_id"],
                "staggered_pitch_mm": pitch,
                "gauge_mm": gauge,
                "correction_width_mm": pitch * pitch / (4 * gauge),
            }
        )
    correction_width = fsum(pair["correction_width_mm"] for pair in stagger_pairs)
    zigzag_width = zigzag_hole_width_sum - correction_width

    governing_path_type = "straight" if straight["hole_width_sum_mm"] >= zigzag_width else "zigzag"
    deduction_width = max(straight["hole_width_sum_mm"], zigzag_width)
    gross_area = d["plate_width_mm"] * d["thickness_mm"]
    deduction_area = deduction_width * d["thickness_mm"]
    net_area = gross_area - deduction_area
    if net_area <= 0:
        raise ValueError("Hole deductions must leave positive net area.")
    return (
        {"net_area": {"satisfied": True, "clause": "9.1.10.1; 9.1.10.2; 9.1.10.3"}},
        {
            "gross_area_mm2": gross_area,
            "straight_path": straight,
            "zigzag_path": {
                "hole_ids": [hole["hole_id"] for hole in zigzag_path],
                "hole_width_sum_mm": zigzag_hole_width_sum,
                "stagger_pairs": stagger_pairs,
                "stagger_correction_width_mm": correction_width,
                "net_deduction_width_mm": zigzag_width,
            },
            "zigzag_transitions_considered": transitions_considered,
            "governing_path_type": governing_path_type,
            "governing_deduction_width_mm": deduction_width,
            "deduction_mm2": deduction_area,
            "net_area_mm2": net_area,
        },
    )


def _angle_hole_deduction(d):
    path_ids = [path["path_id"] for path in d["candidate_paths"]]
    if len(set(path_ids)) != len(path_ids):
        raise ValueError("Angle hole candidate path IDs must be unique.")
    paths = []
    for path in d["candidate_paths"]:
        holes = path["holes"]
        hole_ids = [hole["hole_id"] for hole in holes]
        hole_positions = [
            (hole["angle_leg_id"], hole["longitudinal_mm"], hole["back_mark_mm"]) for hole in holes
        ]
        if len(set(hole_ids)) != len(hole_ids):
            raise ValueError("Hole IDs must be unique within each angle candidate path.")
        if len(set(hole_positions)) != len(hole_positions):
            raise ValueError("Hole positions must be distinct within each angle candidate path.")

        stagger_pairs = []
        for first, second in zip(holes, holes[1:], strict=False):
            pitch = abs(second["longitudinal_mm"] - first["longitudinal_mm"])
            if first["angle_leg_id"] == second["angle_leg_id"]:
                gauge = abs(second["back_mark_mm"] - first["back_mark_mm"])
            else:
                gauge = first["back_mark_mm"] + second["back_mark_mm"] - d["thickness_mm"]
            if gauge <= 0:
                raise ValueError(
                    "Angle stagger gauges must be positive; check back marks and leg thickness."
                )
            stagger_pairs.append(
                {
                    "from_hole_id": first["hole_id"],
                    "to_hole_id": second["hole_id"],
                    "staggered_pitch_mm": pitch,
                    "gauge_mm": gauge,
                    "correction_width_mm": pitch * pitch / (4 * gauge),
                }
            )
        hole_width_sum = fsum(hole["gross_hole_width_mm"] for hole in holes)
        correction_width = fsum(pair["correction_width_mm"] for pair in stagger_pairs)
        paths.append(
            {
                "path_id": path["path_id"],
                "hole_ids": hole_ids,
                "hole_width_sum_mm": hole_width_sum,
                "stagger_pairs": stagger_pairs,
                "stagger_correction_width_mm": correction_width,
                "net_deduction_width_mm": hole_width_sum - correction_width,
            }
        )
    controlling_path = max(paths, key=lambda candidate: candidate["net_deduction_width_mm"])
    straight_width = d["straight_hole_width_sum_mm"]
    zigzag_width = controlling_path["net_deduction_width_mm"]
    governing_path_type = "straight" if straight_width >= zigzag_width else "zigzag"
    deduction_width = max(straight_width, zigzag_width)
    deduction_area = deduction_width * d["thickness_mm"]
    net_area = d["gross_area_mm2"] - deduction_area
    if net_area <= 0:
        raise ValueError("Hole deductions must leave positive net area.")
    return (
        {"net_area": {"satisfied": True, "clause": "9.1.10.1; 9.1.10.2; 9.1.10.3"}},
        {
            "straight_hole_width_sum_mm": straight_width,
            "candidate_paths": paths,
            "controlling_zigzag_path_id": controlling_path["path_id"],
            "governing_path_type": governing_path_type,
            "governing_deduction_width_mm": deduction_width,
            "deduction_mm2": deduction_area,
            "net_area_mm2": net_area,
        },
    )


def _angle_hole_deduction_layout(d):
    holes = sorted(
        d["holes"],
        key=lambda hole: (
            0 if hole["angle_leg_id"] == "leg_1" else 1,
            -hole["back_mark_mm"] if hole["angle_leg_id"] == "leg_1" else hole["back_mark_mm"],
            hole["longitudinal_mm"],
            hole["hole_id"],
        ),
    )
    hole_ids = [hole["hole_id"] for hole in holes]
    positions = [
        (hole["angle_leg_id"], hole["longitudinal_mm"], hole["back_mark_mm"]) for hole in holes
    ]
    if len(set(hole_ids)) != len(hole_ids):
        raise ValueError("Angle hole IDs must be unique across the complete layout.")
    if len(set(positions)) != len(positions):
        raise ValueError("Angle hole centres must be distinct in the complete layout.")

    leg_widths = {"leg_1": d["leg_1_width_mm"], "leg_2": d["leg_2_width_mm"]}
    for hole in holes:
        half_width = hole["gross_hole_width_mm"] / 2
        if (
            hole["back_mark_mm"] < half_width
            or hole["back_mark_mm"] + half_width > leg_widths[hole["angle_leg_id"]]
        ):
            raise ValueError("Every gross hole width must fit within its angle leg.")

    straight_rows = {}
    for hole in holes:
        straight_rows.setdefault(hole["longitudinal_mm"], []).append(hole)
    straight_candidates = [
        {
            "longitudinal_mm": longitudinal,
            "hole_ids": [hole["hole_id"] for hole in row],
            "hole_width_sum_mm": fsum(hole["gross_hole_width_mm"] for hole in row),
        }
        for longitudinal, row in sorted(straight_rows.items())
    ]
    straight = max(straight_candidates, key=lambda candidate: candidate["hole_width_sum_mm"])

    # Every forward sequence through the unfolded two-leg angle is a possible
    # progressive zig-zag. Dynamic programming evaluates all positive-gauge
    # transitions without materializing the potentially exponential path set.
    best_widths = []
    predecessors = []
    best_zigzag_width = float("-inf")
    best_zigzag_pair = None
    transitions_considered = 0
    for j, hole in enumerate(holes):
        best_prefix = 0.0
        predecessor = None
        for i, previous in enumerate(holes[:j]):
            if previous["angle_leg_id"] == hole["angle_leg_id"]:
                gauge = abs(hole["back_mark_mm"] - previous["back_mark_mm"])
            elif previous["angle_leg_id"] == "leg_1" and hole["angle_leg_id"] == "leg_2":
                gauge = previous["back_mark_mm"] + hole["back_mark_mm"] - d["thickness_mm"]
            else:
                continue
            if gauge <= 0:
                continue
            transitions_considered += 1
            pitch = abs(hole["longitudinal_mm"] - previous["longitudinal_mm"])
            correction = pitch * pitch / (4 * gauge)
            candidate_width = best_widths[i] - correction + hole["gross_hole_width_mm"]
            if candidate_width > best_zigzag_width:
                best_zigzag_width = candidate_width
                best_zigzag_pair = (i, j)
            candidate_prefix = best_widths[i] - correction
            if candidate_prefix > best_prefix:
                best_prefix = candidate_prefix
                predecessor = i
        best_widths.append(hole["gross_hole_width_mm"] + best_prefix)
        predecessors.append(predecessor)

    zigzag_indices = []
    if best_zigzag_pair is not None:
        start, end = best_zigzag_pair
        while start is not None:
            zigzag_indices.append(start)
            start = predecessors[start]
        zigzag_indices.reverse()
        zigzag_indices.append(end)
    zigzag_holes = [holes[index] for index in zigzag_indices]
    zigzag_width_sum = fsum(hole["gross_hole_width_mm"] for hole in zigzag_holes)
    stagger_pairs = []
    for first, second in zip(zigzag_holes, zigzag_holes[1:], strict=False):
        pitch = abs(second["longitudinal_mm"] - first["longitudinal_mm"])
        if first["angle_leg_id"] == second["angle_leg_id"]:
            gauge = abs(second["back_mark_mm"] - first["back_mark_mm"])
        else:
            gauge = first["back_mark_mm"] + second["back_mark_mm"] - d["thickness_mm"]
        stagger_pairs.append(
            {
                "from_hole_id": first["hole_id"],
                "to_hole_id": second["hole_id"],
                "staggered_pitch_mm": pitch,
                "gauge_mm": gauge,
                "correction_width_mm": pitch * pitch / (4 * gauge),
            }
        )
    stagger_correction = fsum(pair["correction_width_mm"] for pair in stagger_pairs)
    zigzag_width = zigzag_width_sum - stagger_correction
    straight_width = straight["hole_width_sum_mm"]
    governing_type = "straight" if straight_width >= zigzag_width else "zigzag"
    deduction_width = max(straight_width, zigzag_width)
    deduction_area = deduction_width * d["thickness_mm"]
    net_area = d["gross_area_mm2"] - deduction_area
    if net_area <= 0:
        raise ValueError("Hole deductions must leave positive net area.")
    return (
        {"net_area": {"satisfied": True, "clause": "9.1.10.1; 9.1.10.2; 9.1.10.3"}},
        {
            "gross_area_mm2": d["gross_area_mm2"],
            "angle_leg_widths_mm": leg_widths,
            "straight_path": straight,
            "zigzag_path": {
                "hole_ids": [hole["hole_id"] for hole in zigzag_holes],
                "hole_width_sum_mm": zigzag_width_sum,
                "stagger_pairs": stagger_pairs,
                "stagger_correction_width_mm": stagger_correction,
                "net_deduction_width_mm": zigzag_width,
            },
            "progressive_hole_order": hole_ids,
            "zigzag_transitions_considered": transitions_considered,
            "path_search_method": "dynamic_programming_all_positive_gauge_forward_transitions",
            "governing_path_type": governing_type,
            "governing_deduction_width_mm": deduction_width,
            "deduction_mm2": deduction_area,
            "net_area_mm2": net_area,
        },
    )


def _combined_weld_types(d):
    components = d["weld_components"]
    component_ids = [component["component_id"] for component in components]
    if len(set(component_ids)) != len(component_ids):
        raise ValueError("Combined weld component IDs must be unique.")
    capacities_by_type = {}
    for component in components:
        capacities_by_type.setdefault(component["weld_type"], []).append(
            component["design_capacity"]
        )
    if len(capacities_by_type) < 2:
        raise ValueError("Clause 9.7.4 requires at least two different weld types.")
    design_capacity_by_type = {
        weld_type: fsum(capacities) for weld_type, capacities in sorted(capacities_by_type.items())
    }
    total_design_capacity = fsum(design_capacity_by_type.values())
    unit = "kn" if d["design_action_basis"] == "force_kn" else "knm"
    return (
        {
            "combined_weld_connection_capacity": _connection_capacity_check(
                d["design_action"], total_design_capacity, unit, "9.7.4"
            )
        },
        {
            "design_action_basis": d["design_action_basis"],
            "design_capacity_by_type": design_capacity_by_type,
            "total_design_capacity": total_design_capacity,
            "weld_component_count": len(components),
            "weld_component_ids": component_ids,
            "capacity_calculation_references": {
                component["component_id"]: component["capacity_calculation_reference"]
                for component in components
            },
            "capacity_factor_applied_again": False,
        },
    )


def _appendix_j_slip_load(bolt):
    method = bolt["slip_load_method"]
    if method == "clear_observed_slip":
        if "slip_load_kn" not in bolt:
            raise ValueError(
                "Appendix J.4 clear slip identification requires the measured slip load."
            )
        if "deformation_readings" in bolt:
            raise ValueError(
                "Appendix J.4 clear slip identification does not accept 0.13 mm readings."
            )
        return bolt["slip_load_kn"], {
            "method": method,
            "slip_load_kn": bolt["slip_load_kn"],
            "clause": "Appendix J.4",
        }

    if "slip_load_kn" in bolt:
        raise ValueError(
            "Appendix J.4 unclear slip identification derives the load from 0.13 mm readings."
        )
    readings = bolt.get("deformation_readings")
    if readings is None:
        raise ValueError(
            "Appendix J.4 unclear slip identification requires two-edge deformation readings."
        )
    edge_mean_mm = [
        (reading["left_edge_deformation_mm"] + reading["right_edge_deformation_mm"]) / 2
        for reading in readings
    ]
    loads_kn = [reading["load_kn"] for reading in readings]
    if any(loads_kn[index] <= loads_kn[index - 1] for index in range(1, len(loads_kn))):
        raise ValueError("Appendix J.4 deformation readings must have increasing load values.")
    threshold_mm = 0.13
    if edge_mean_mm[0] > threshold_mm:
        raise ValueError("Appendix J.4 deformation history must begin at or below 0.13 mm.")
    if edge_mean_mm[0] == threshold_mm:
        if loads_kn[0] <= 0:
            raise ValueError("Appendix J.4 calculated slip load must be positive.")
        return loads_kn[0], {
            "method": method,
            "slip_load_kn": loads_kn[0],
            "deformation_threshold_mm": threshold_mm,
            "bracketing_readings": [0, 0],
            "interpolated": False,
            "clause": "Appendix J.4",
        }
    for index in range(1, len(readings)):
        if edge_mean_mm[index] >= threshold_mm:
            lower_deformation_mm = edge_mean_mm[index - 1]
            upper_deformation_mm = edge_mean_mm[index]
            if upper_deformation_mm <= lower_deformation_mm:
                raise ValueError("Appendix J.4 deformation readings must increase through 0.13 mm.")
            fraction = (threshold_mm - lower_deformation_mm) / (
                upper_deformation_mm - lower_deformation_mm
            )
            slip_load_kn = loads_kn[index - 1] + fraction * (loads_kn[index] - loads_kn[index - 1])
            return slip_load_kn, {
                "method": method,
                "slip_load_kn": slip_load_kn,
                "deformation_threshold_mm": threshold_mm,
                "mean_edge_deformation_at_lower_reading_mm": lower_deformation_mm,
                "mean_edge_deformation_at_upper_reading_mm": upper_deformation_mm,
                "bracketing_readings": [index - 1, index],
                "interpolated": True,
                "clause": "Appendix J.4",
            }
    raise ValueError("Appendix J.4 deformation readings do not reach 0.13 mm.")


def _appendix_j_slip_factor(d):
    """Calculate the Appendix J.5 factor from a compliant three- or five-plus series."""
    from .erection import MINIMUM_BOLT_TENSION_KN

    specimens = d["specimens"]
    specimen_count = len(specimens)
    if specimen_count == 4:
        raise ValueError(
            "Appendix J.5 gives no k value for four specimens; use three or at least five."
        )

    bolt_diameter = d["nominal_bolt_diameter_mm"]
    geometry = d["specimen_geometry"]
    if not isclose(
        geometry["left_bolt_to_test_section_end_mm"],
        geometry["right_bolt_to_test_section_end_mm"],
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("Appendix J Figure J.1 requires a symmetric bolt layout about the butt.")
    if not isclose(
        geometry["upper_bolt_edge_distance_mm"],
        geometry["lower_bolt_edge_distance_mm"],
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("Appendix J Figure J.1 requires equal bolt edge distances.")
    if not isclose(
        geometry["inner_plate_thicknesses_mm"][0],
        geometry["inner_plate_thicknesses_mm"][1],
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("Appendix J.1.1 requires equal inner-plate thicknesses.")
    if not isclose(
        geometry["cover_plate_thicknesses_mm"][0],
        geometry["cover_plate_thicknesses_mm"][1],
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("Appendix J Figure J.1 requires equal cover-plate thicknesses.")

    test_section_length_mm = (
        geometry["left_bolt_to_test_section_end_mm"]
        + geometry["bolt_centre_spacing_mm"]
        + geometry["right_bolt_to_test_section_end_mm"]
    )
    specimen_width_mm = (
        geometry["upper_bolt_edge_distance_mm"] + geometry["lower_bolt_edge_distance_mm"]
    )
    minimum_dimensions = {
        "bolt_centre_spacing_mm": 6 * bolt_diameter,
        "left_bolt_to_test_section_end_mm": 2 * bolt_diameter,
        "right_bolt_to_test_section_end_mm": 2 * bolt_diameter,
        "upper_bolt_edge_distance_mm": 3 * bolt_diameter,
        "lower_bolt_edge_distance_mm": 3 * bolt_diameter,
    }
    for name, minimum in minimum_dimensions.items():
        if geometry[name] < minimum:
            raise ValueError(
                f"Appendix J Figure J.1 requires {name} to be at least {minimum:g} mm."
            )
    if test_section_length_mm < 10 * bolt_diameter:
        raise ValueError("Appendix J Figure J.1 requires a 10 df minimum test-section length.")
    if specimen_width_mm < 6 * bolt_diameter:
        raise ValueError("Appendix J Figure J.1 requires a 6 df minimum specimen width.")
    minimum_inner_plate_thickness_mm = bolt_diameter + 5
    if any(
        thickness < minimum_inner_plate_thickness_mm
        for thickness in geometry["inner_plate_thicknesses_mm"]
    ):
        raise ValueError(
            "Appendix J Figure J.1 requires inner-plate thickness of at least df + 5 mm."
        )
    minimum_cover_plate_thickness_mm = bolt_diameter / 2 + 2
    if any(
        thickness < minimum_cover_plate_thickness_mm
        for thickness in geometry["cover_plate_thicknesses_mm"]
    ):
        raise ValueError(
            "Appendix J Figure J.1 requires cover-plate thickness of at least df/2 + 2 mm."
        )
    required_cover_hole_diameter_mm = bolt_diameter + 2
    if not isclose(
        geometry["cover_plate_hole_diameter_mm"],
        required_cover_hole_diameter_mm,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("Appendix J Figure J.1 cover-plate hole diameter must be df + 2 mm.")
    required_inner_hole_diameter_mm = bolt_diameter + 3
    if not isclose(
        geometry["inner_plate_hole_diameter_mm"],
        required_inner_hole_diameter_mm,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("Appendix J Figure J.1 inner-plate hole diameter must be df + 3 mm.")
    if not isclose(geometry["butt_gap_mm"], 8, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("Appendix J Figure J.1 specifies an 8 mm butt gap.")

    method = d["bolt_tension_method"]
    calibration_fields = {
        "calibration_test_bolt_count",
        "calibration_curve_reference",
        "calibration_test_bolts_from_test_batch_verified",
        "calibration_grip_and_measurement_method_match_verified",
        "calibration_curve_based_on_mean_result_verified",
    }
    proof_fields = {
        "specified_bolt_proof_load_kn",
        "proof_load_reference",
        "bolt_proof_load_specification_verified",
        "bolt_geometry_source_reference",
        "bolt_geometry_matches_tested_assembly_verified",
    }
    if method == "calibration_curve":
        required_fields, forbidden_fields = calibration_fields, proof_fields
    else:
        required_fields, forbidden_fields = proof_fields, calibration_fields
    missing_fields = required_fields - d.keys()
    if missing_fields:
        raise ValueError(f"{method} requires: {', '.join(sorted(missing_fields))}.")
    unexpected_fields = forbidden_fields & d.keys()
    if unexpected_fields:
        raise ValueError(f"{method} does not accept: {', '.join(sorted(unexpected_fields))}.")

    if method == "calibration_curve":
        bolt_only_required = {"calibrated_bolt_tension_kn"}
        bolt_only_forbidden = {
            "unthreaded_grip_length_mm",
            "unthreaded_shank_area_mm2",
            "threaded_grip_length_mm",
            "nut_thickness_mm",
            "tensile_stress_area_mm2",
        }
    else:
        bolt_only_required = {
            "unthreaded_grip_length_mm",
            "unthreaded_shank_area_mm2",
            "threaded_grip_length_mm",
            "nut_thickness_mm",
            "tensile_stress_area_mm2",
        }
        bolt_only_forbidden = {"calibrated_bolt_tension_kn"}

    table_key = (d["nominal_bolt_diameter_mm"], d["bolt_grade"])
    minimum_tension_kn = MINIMUM_BOLT_TENSION_KN[table_key]
    proof_load_kn = d.get("specified_bolt_proof_load_kn")
    estimates = []
    specimen_results = []
    loading_increments_by_specimen = {}
    specimen_ids = [specimen["specimen_id"] for specimen in specimens]
    if len(set(specimen_ids)) != specimen_count:
        raise ValueError("Appendix J specimen IDs must be unique.")

    for specimen in specimens:
        bolt_ids = [bolt["bolt_id"] for bolt in specimen["bolts"]]
        if len(set(bolt_ids)) != 2:
            raise ValueError("The two bolt IDs within each specimen must be distinct.")
        positions = []
        for bolt in specimen["bolts"]:
            missing_bolt_fields = bolt_only_required - bolt.keys()
            if missing_bolt_fields:
                raise ValueError(
                    f"{method} bolt data require: {', '.join(sorted(missing_bolt_fields))}."
                )
            unexpected_bolt_fields = bolt_only_forbidden & bolt.keys()
            if unexpected_bolt_fields:
                raise ValueError(
                    f"{method} bolt data do not accept: "
                    f"{', '.join(sorted(unexpected_bolt_fields))}."
                )

            if method == "calibration_curve":
                tension_kn = bolt["calibrated_bolt_tension_kn"]
            else:
                compliance_mm_per_mm2 = (
                    bolt["unthreaded_grip_length_mm"] / bolt["unthreaded_shank_area_mm2"]
                    + (bolt["threaded_grip_length_mm"] + bolt["nut_thickness_mm"] / 2)
                    / bolt["tensile_stress_area_mm2"]
                )
                if compliance_mm_per_mm2 <= 0 or not isfinite(compliance_mm_per_mm2):
                    raise ValueError("Equation J.1 bolt extension compliance must be positive.")
                tension_kn = 200_000 * bolt["bolt_extension_mm"] * 1e-3 / compliance_mm_per_mm2
                lower_proof_limit_kn = 0.8 * proof_load_kn
                if not lower_proof_limit_kn <= tension_kn <= proof_load_kn:
                    raise ValueError(
                        "Equation J.1 bolt tension must be 80% to 100% of specified proof load."
                    )
            if tension_kn < minimum_tension_kn:
                raise ValueError(
                    "Every Appendix J test bolt must reach the Table 15.2.2.2 minimum "
                    f"tension of {minimum_tension_kn:g} kN."
                )

            slip_load_kn, slip_load_result = _appendix_j_slip_load(bolt)
            slip_factor = 0.5 * slip_load_kn / tension_kn
            estimates.append(slip_factor)
            positions.append(
                {
                    "bolt_id": bolt["bolt_id"],
                    "slip_load_kn": slip_load_kn,
                    "bolt_extension_mm": bolt["bolt_extension_mm"],
                    "bolt_tension_kn": tension_kn,
                    "minimum_bolt_tension_kn": minimum_tension_kn,
                    "individual_slip_factor_estimate": slip_factor,
                    "slip_load_determination": slip_load_result,
                }
            )
        specimen_results.append({"specimen_id": specimen["specimen_id"], "bolts": positions})
        loading_increments_by_specimen[specimen["specimen_id"]] = specimen["loading_increments"]

    estimate_count = 2 * specimen_count
    mean_factor = fsum(estimates) / estimate_count
    standard_deviation = sqrt(
        fsum((estimate - mean_factor) ** 2 for estimate in estimates) / (estimate_count - 1)
    )
    k = 0.85 if specimen_count == 3 else 0.90
    unadjusted_factor = k * (mean_factor - 1.64 * standard_deviation)
    minimum_estimate = min(estimates)
    fallback_applied = unadjusted_factor < minimum_estimate
    design_factor = minimum_estimate if fallback_applied else unadjusted_factor
    loading_protocol_results = []
    for specimen in specimen_results:
        bolt_positions = specimen["bolts"]
        predicted_position_slips = [
            {
                "bolt_id": bolt["bolt_id"],
                "predicted_slip_load_kn": 2 * 0.35 * bolt["bolt_tension_kn"],
            }
            for bolt in bolt_positions
        ]
        # The specimen has two bolt positions in series. The first predicted position
        # to slip governs its connection load; J.3's note permits adjustment after that.
        predicted_connection_slip_kn = min(
            item["predicted_slip_load_kn"] for item in predicted_position_slips
        )
        maximum_increment_kn = min(25.0, 0.25 * predicted_connection_slip_kn)
        first_measured_slip_kn = min(bolt["slip_load_kn"] for bolt in bolt_positions)
        increments = loading_increments_by_specimen[specimen["specimen_id"]]
        if not isclose(increments[0]["load_before_kn"], 0.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("Appendix J.3 loading increments must start at zero applied load.")
        increment_results = []
        previous_end_kn = None
        for index, increment in enumerate(increments):
            start_kn = increment["load_before_kn"]
            end_kn = increment["load_after_kn"]
            if end_kn <= start_kn:
                raise ValueError("Appendix J.3 loading increments must increase tensile load.")
            if index and not isclose(start_kn, previous_end_kn, rel_tol=0.0, abs_tol=1e-6):
                raise ValueError(
                    "Appendix J.3 loading increments must form a continuous load history."
                )
            creep_ceased = increment.get("preceding_load_creep_effectively_ceased_verified")
            if index and creep_ceased is not True:
                raise ValueError(
                    "Appendix J.3 requires each load increment after the first to follow "
                    "cessation of creep from the preceding increment."
                )
            applies_before_slip = start_kn < first_measured_slip_kn
            applied_increment_kn = end_kn - start_kn
            increment_satisfied = (
                not applies_before_slip or applied_increment_kn <= maximum_increment_kn + 1e-9
            )
            rate_satisfied = (
                not applies_before_slip or increment["maximum_rate_kn_per_min"] <= 50.0 + 1e-9
            )
            if not increment_satisfied:
                raise ValueError(
                    "Appendix J.3 load increment exceeds the lesser of 25 kN and "
                    "one-quarter of the calculated connection slip load."
                )
            if not rate_satisfied:
                raise ValueError(
                    "Appendix J.3 loading rate exceeds 50 kN/min before the first slip."
                )
            increment_results.append(
                {
                    "load_before_kn": start_kn,
                    "load_after_kn": end_kn,
                    "applied_increment_kn": applied_increment_kn,
                    "maximum_permitted_increment_kn": maximum_increment_kn,
                    "maximum_measured_rate_kn_per_min": increment["maximum_rate_kn_per_min"],
                    "maximum_permitted_rate_kn_per_min": 50.0,
                    "increment_and_rate_limits_apply": applies_before_slip,
                    "increment_satisfied": increment_satisfied,
                    "rate_satisfied": rate_satisfied,
                    "preceding_load_creep_effectively_ceased": (
                        None if index == 0 else creep_ceased
                    ),
                }
            )
            previous_end_kn = end_kn
        if previous_end_kn + 1e-9 < max(bolt["slip_load_kn"] for bolt in bolt_positions):
            raise ValueError(
                "Appendix J.3 loading history must reach the measured slip load at both "
                "bolt positions."
            )
        loading_protocol_results.append(
            {
                "specimen_id": specimen["specimen_id"],
                "assumed_slip_factor": 0.35,
                "predicted_position_slip_loads": predicted_position_slips,
                "predicted_connection_slip_load_kn": predicted_connection_slip_kn,
                "maximum_permitted_increment_kn": maximum_increment_kn,
                "first_measured_slip_load_kn": first_measured_slip_kn,
                "increments": increment_results,
                "satisfied": True,
                "clause": "Appendix J.3",
            }
        )
    prerequisite_fields = (
        "symmetrical_double_cover_butt_specimen_verified",
        "bolts_clear_of_bearing_in_loading_direction_verified",
        "friction_surface_condition_matches_field_verified",
        "machining_oil_contamination_absent_if_used_verified",
        "specimen_bolt_tensioning_matches_field_verified",
        "initial_snug_condition_finger_tight_verified",
        "extension_measurement_immediately_before_test_verified",
        "extension_instrument_resolution_mm",
        "instrumentation_layout_per_appendix_j_verified",
        "instrumentation_deformation_reduction_per_appendix_j_verified",
        "tensile_loading_only_verified",
        "slip_load_identification_per_appendix_j_verified",
    )
    return (
        {
            "slip_factor": {
                "slip_factor_for_design": design_factor,
                "unadjusted_factor": unadjusted_factor,
                "mean_of_individual_estimates": mean_factor,
                "sample_standard_deviation": standard_deviation,
                "lowest_individual_estimate": minimum_estimate,
                "minimum_estimate_fallback_applied": fallback_applied,
                "individual_estimate_count": estimate_count,
                "specimen_count": specimen_count,
                "k": k,
                "clause": "Appendix J.5",
            },
            "loading_protocol": {
                "satisfied": True,
                "specimens": loading_protocol_results,
                "clause": "Appendix J.3",
            },
            "specimen_geometry": {
                "satisfied": True,
                "test_section_length_mm": test_section_length_mm,
                "minimum_test_section_length_mm": 10 * bolt_diameter,
                "specimen_width_mm": specimen_width_mm,
                "minimum_specimen_width_mm": 6 * bolt_diameter,
                "minimum_bolt_centre_spacing_mm": 6 * bolt_diameter,
                "minimum_bolt_end_distance_mm": 2 * bolt_diameter,
                "minimum_bolt_edge_distance_mm": 3 * bolt_diameter,
                "minimum_inner_plate_thickness_mm": minimum_inner_plate_thickness_mm,
                "minimum_cover_plate_thickness_mm": minimum_cover_plate_thickness_mm,
                "required_cover_plate_hole_diameter_mm": required_cover_hole_diameter_mm,
                "required_inner_plate_hole_diameter_mm": required_inner_hole_diameter_mm,
                "required_butt_gap_mm": 8,
                "clause": "Appendix J Figure J.1",
            },
        },
        {
            "bolt_tension_method": method,
            "nominal_bolt_diameter_mm": d["nominal_bolt_diameter_mm"],
            "bolt_grade": d["bolt_grade"],
            "table_15_2_2_2_minimum_bolt_tension_kn": minimum_tension_kn,
            "specimen_geometry": geometry,
            "appendix_j_test_report_reference": d["appendix_j_test_report_reference"],
            "appendix_j_prerequisites": {field: d[field] for field in prerequisite_fields},
            "bolt_tension_method_evidence": {field: d[field] for field in sorted(required_fields)},
            "calibration_curve_reference": d.get("calibration_curve_reference"),
            "proof_load_reference": d.get("proof_load_reference"),
            "individual_slip_factor_estimates": estimates,
            "specimens": specimen_results,
            "standard_deviation_divisor": estimate_count - 1,
        },
    )


def _check(capacity, phi, action, clause, unit="kn"):
    design = capacity * phi
    if design <= 0 or not isfinite(design):
        raise ValueError("Calculated capacity must be finite and positive.")
    return {
        f"nominal_capacity_{unit}": capacity,
        f"design_capacity_{unit}": design,
        "capacity_factor": phi,
        "utilisation": action / design,
        "satisfied": action <= design,
        "clause": clause,
    }


def _connection_capacity_check(action, capacity, unit, clause):
    return {
        f"design_action_{unit}": action,
        f"design_capacity_{unit}": capacity,
        "utilisation": action / capacity if capacity else None,
        "satisfied": action <= capacity,
        "clause": clause,
    }


def _fillet_strength_check(d, throat_mm, effective_length_mm, clause="9.6.3.10"):
    lap_m = d["lap_length_mm"] / 1000
    lap_factor = 1 if lap_m <= 1.7 else (1.10 - 0.06 * lap_m if lap_m <= 8 else 0.62)
    if d["thin_rhs_longitudinal"]:
        if d["quality"] != "SP":
            raise ValueError("Thin RHS longitudinal fillet requires SP quality.")
        phi = 0.7
    else:
        phi = 0.8 if d["quality"] == "SP" else 0.6
    nominal_capacity = (
        0.6 * d["weld_strength_mpa"] * throat_mm * effective_length_mm * lap_factor / 1000
    )
    return (
        _check(nominal_capacity, phi, d["action_kn"], clause),
        {"lap_factor": lap_factor, "capacity_factor": phi},
    )


def _bolt(d):
    nn, nx = d["threaded_planes"], d["plain_planes"]
    if nn + nx == 0:
        raise ValueError("At least one shear plane is required.")
    if d["minor_area_mm2"] > d["tensile_area_mm2"] or d["tensile_area_mm2"] > d["shank_area_mm2"]:
        raise ValueError("Bolt areas must satisfy minor <= tensile <= shank.")
    length = d["lap_length_mm"]
    kr = 1 if length < 300 else (1.075 - length / 4000 if length <= 1300 else 0.75)
    krd = 0.83 if d["grade"] == "10.9" and nn else 1
    filler = _effective_filler_thickness_mm(d)
    kf = 1 - 0.0154 * (filler - 6) if filler > 6 else 1
    shear = (
        0.62
        * d["ultimate_strength_mpa"]
        * kr
        * krd
        * kf
        * (nn * d["minor_area_mm2"] + nx * d["shank_area_mm2"])
        / 1000
    )
    tension = d["tensile_area_mm2"] * d["ultimate_strength_mpa"] / 1000
    return (
        shear,
        tension,
        {
            "lap_factor": kr,
            "ductility_factor": krd,
            "filler_factor": kf,
            "filler_thickness_used_mm": filler,
        },
    )


def _effective_filler_thickness_mm(d):
    thickness = d.get("filler_thickness_mm")
    plane_thicknesses = d.get("filler_thickness_by_shear_plane_mm")
    if thickness is None and plane_thicknesses is None:
        raise ValueError("Provide the filler thickness or its thickness on each shear plane.")
    if plane_thicknesses is None:
        return thickness
    governing_thickness = max(plane_thicknesses)
    if thickness is not None and not isclose(
        thickness, governing_thickness, rel_tol=0.0, abs_tol=1e-9
    ):
        raise ValueError(
            "filler_thickness_mm must equal the maximum thickness in "
            "filler_thickness_by_shear_plane_mm."
        )
    return governing_thickness


def _filler_plate_detailing_check(d):
    filler_thickness = _effective_filler_thickness_mm(d)
    if filler_thickness == 0:
        return None
    if any(field not in d for field in FILLER_PLATE_ASSESSMENT_FIELDS):
        raise ValueError(
            "Clause 9.2.2.5 filler extension and force-transfer bolting must be verified "
            "when a filler plate is present."
        )
    extension_verified, transfer_verified = (d[field] for field in FILLER_PLATE_ASSESSMENT_FIELDS)
    return {
        "clause": "9.2.2.5",
        "applicable": True,
        "governing_filler_thickness_mm": filler_thickness,
        "extension_beyond_connection_verified": extension_verified,
        "bolting_transfers_member_force_through_combined_section_verified": transfer_verified,
        "satisfied": extension_verified and transfer_verified,
        "assessment_basis": (
            "User-verified detailing; extension geometry and transfer-bolt capacity are "
            "not calculated by this operation."
        ),
    }


def _slip_surface_requirements_check(d):
    clean_as_rolled = d.get("clean_as_rolled_contact_surfaces_verified", False)
    test_evidence = d.get("slip_factor_test_evidence_verified", False)
    drawings_verified = d.get(
        "friction_bolt_category_and_surface_treatment_masking_drawings_verified", False
    )
    standard_factor = isclose(d["slip_factor"], 0.35, rel_tol=0.0, abs_tol=1e-12)
    if standard_factor and clean_as_rolled:
        factor_basis = "clean_as_rolled"
    elif test_evidence:
        factor_basis = "test_evidence"
    else:
        factor_basis = "unverified"
    return {
        "clause": "9.2.3.2",
        "slip_factor_basis": factor_basis,
        "clean_as_rolled_factor_route_available": standard_factor,
        "clean_as_rolled_contact_surfaces_verified": clean_as_rolled,
        "slip_factor_test_evidence_verified": test_evidence,
        "friction_bolt_category_and_surface_treatment_masking_drawings_verified": drawings_verified,
        "satisfied": factor_basis != "unverified" and drawings_verified,
    }


def _assess_out_of_plane_bolt_group(d, bolt_actions, design_actions, force_distribution_source):
    shear_capacity, tension_capacity, bolt_properties = _bolt(d)
    bolt_ids = [item["bolt_id"] for item in bolt_actions]
    positions = [tuple(item["position_mm"]) for item in bolt_actions]
    if len(set(bolt_ids)) != len(bolt_ids):
        raise ValueError("Bolt IDs must be unique.")
    if len(set(positions)) != len(positions):
        raise ValueError("Bolt positions must be distinct.")
    resultant = {
        "force_x_kn": sum(item["shear_x_kn"] for item in bolt_actions),
        "force_y_kn": sum(item["shear_y_kn"] for item in bolt_actions),
        "tension_kn": sum(item["tension_action_kn"] for item in bolt_actions),
        "moment_x_knm": sum(
            item["position_mm"][1] * item["tension_action_kn"] / 1000 for item in bolt_actions
        ),
        "moment_y_knm": sum(
            -item["position_mm"][0] * item["tension_action_kn"] / 1000 for item in bolt_actions
        ),
        "moment_z_knm": sum(
            (
                item["position_mm"][0] * item["shear_y_kn"]
                - item["position_mm"][1] * item["shear_x_kn"]
            )
            / 1000
            for item in bolt_actions
        ),
    }
    equilibrium = {}
    for action, calculated in resultant.items():
        required = design_actions[action]
        tolerance = 1e-6 * max(1.0, abs(required))
        equilibrium[action] = {
            "calculated": calculated,
            "required": required,
            "residual": calculated - required,
            "absolute_tolerance": tolerance,
            "satisfied": abs(calculated - required) <= tolerance,
            "clause": "9.1.3(a); 9.3.2; 9.3.3",
        }
    checks = {
        "action_distribution_equilibrium": {
            "satisfied": all(item["satisfied"] for item in equilibrium.values()),
            "components": equilibrium,
            "clause": "9.1.3(a); 9.3.2; 9.3.3",
        }
    }
    per_bolt = []
    for item in bolt_actions:
        shear = hypot(item["shear_x_kn"], item["shear_y_kn"])
        total_tension = item["tension_action_kn"] + item["prying_tension_kn"]
        shear_check = _check(shear_capacity, 0.8, shear, "9.2.2.1")
        tension_clause = "9.2.2.2"
        if item["prying_tension_kn"]:
            tension_clause = "9.1.8; 9.2.2.2"
        tension_check = _check(tension_capacity, 0.8, total_tension, tension_clause)
        interaction = (shear / (0.8 * shear_capacity)) ** 2 + (
            total_tension / (0.8 * tension_capacity)
        ) ** 2
        per_bolt.append(
            {
                "bolt_id": item["bolt_id"],
                "shear_action_kn": shear,
                "member_tension_action_kn": item["tension_action_kn"],
                "prying_tension_action_kn": item["prying_tension_kn"],
                "total_bolt_tension_action_kn": total_tension,
                "shear": shear_check,
                "tension": tension_check,
                "interaction": {
                    "utilisation": interaction,
                    "satisfied": interaction <= 1,
                    "clause": "9.2.2.3",
                },
            }
        )
    checks["bolts"] = per_bolt
    intermediate = {
        "clause": "9.3.2; 9.3.3",
        "capacity_factor": 0.8,
        "nominal_shear_capacity_kn": shear_capacity,
        "nominal_tension_capacity_kn": tension_capacity,
        "bolt_properties": bolt_properties,
        "design_actions_resolved_to_bolt_group": design_actions,
        "actions_resolved_from_bolts": resultant,
        "bolt_actions": per_bolt,
        "force_distribution_source": force_distribution_source,
    }
    return checks, intermediate


def run_connections(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Reject numerically unrepresentable calculations as invalid input domains."""
    try:
        return _run_connections(inputs)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Connection calculation exceeds the finite numeric domain.") from exc


def _run_connections(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate the tagged component check; actions include externally assessed prying."""
    if not isinstance(inputs, Mapping):
        raise ValueError("Inputs must be an object.")
    d = dict(inputs)
    validate_standard_strengths(d)
    try:
        check_type = d.get("check_type")
        schema = (
            INPUT_SCHEMAS_BY_CHECK_TYPE["slip_factor_test"]
            if check_type == "slip_factor_test"
            else INPUT_SCHEMA
        )
        Draft202012Validator(schema).validate(d)
    except ValidationError as exc:
        raise ValueError(exc.message) from exc
    if not _finite(d):
        raise ValueError("All numeric inputs must be finite.")
    k = d["check_type"]
    c, intermediate = {}, {}
    if k in MINIMUM_ACTION_CHECKS:
        excluded_absent = d["excluded_connection_arrangement_absent_verified"]
        if not excluded_absent:
            raise ValueError("Clause 9.1.4 excludes lacing, sag-rod, purlin and girt connections.")
    if k == "slip_factor_test":
        c, intermediate = _appendix_j_slip_factor(d)
    elif k == "minimum_beam_shear_action":
        actual = d["actual_design_shear_kn"]
        member_capacity = d["member_design_shear_capacity_kn"]
        fractional_minimum = 0.15 * member_capacity
        minimum = min(fractional_minimum, 40.0)
        required = max(actual, minimum)
        intermediate = {
            "clause": "9.1.4(b)(ii)",
            "actual_design_shear_kn": actual,
            "member_design_shear_capacity_kn": member_capacity,
            "fractional_minimum_shear_kn": fractional_minimum,
            "minimum_design_shear_kn": minimum,
            "required_design_shear_kn": required,
            "governing_action": (
                "actual_design_shear" if actual >= minimum else "minimum_design_shear"
            ),
            "minimum_fraction_of_member_design_capacity": 0.15,
            "maximum_minimum_shear_kn": 40.0,
            "member_capacity_includes_capacity_factor": True,
        }
        eccentricity_fields = (
            "reaction_shear_direction_unit_vector",
            "reaction_shear_eccentricity_vector_mm",
            "reaction_shear_eccentricity_assessment_verified",
        )
        eccentricity_fields_present = [field in d for field in eccentricity_fields]
        if any(eccentricity_fields_present) and not all(eccentricity_fields_present):
            raise ValueError(
                "Provide the shear direction, eccentricity vector and assessment together."
            )
        if all(eccentricity_fields_present):
            direction = d["reaction_shear_direction_unit_vector"]
            direction_length = sqrt(sum(component * component for component in direction))
            if not isclose(direction_length, 1.0, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError("Reaction shear direction must be a unit vector.")
            force = [required * component for component in direction]
            ex, ey, ez = d["reaction_shear_eccentricity_vector_mm"]
            fx, fy, fz = force
            moments = [
                (ey * fz - ez * fy) / 1000,
                (ez * fx - ex * fz) / 1000,
                (ex * fy - ey * fx) / 1000,
            ]
            intermediate.update(
                {
                    "clause_9_1_2_3_reaction_shear_vector_kn": force,
                    "reaction_shear_eccentricity_vector_mm": [ex, ey, ez],
                    "clause_9_1_2_3_eccentricity_moment_vector_knm": moments,
                }
            )
        if "connection_design_shear_capacity_kn" in d:
            capacity = d["connection_design_shear_capacity_kn"]
            intermediate["connection_design_shear_capacity_kn"] = capacity
            c["connection_shear_capacity"] = _connection_capacity_check(
                required, capacity, "kn", "9.1.4(b)(ii)"
            )
    elif k == "minimum_rigid_connection_action":
        actual = d["actual_design_moment_knm"]
        minimum = 0.5 * d["member_design_moment_capacity_knm"]
        required = max(actual, minimum)
        intermediate = {
            "clause": "9.1.4(b)(i)",
            "actual_design_moment_knm": actual,
            "member_design_moment_capacity_knm": d["member_design_moment_capacity_knm"],
            "minimum_design_moment_knm": minimum,
            "required_design_moment_knm": required,
            "minimum_fraction_of_member_design_capacity": 0.5,
        }
        if "connection_design_moment_capacity_knm" in d:
            capacity = d["connection_design_moment_capacity_knm"]
            intermediate["connection_design_moment_capacity_knm"] = capacity
            c["connection_moment_capacity"] = _connection_capacity_check(
                required, capacity, "knm", "9.1.4(b)(i)"
            )
    elif k == "minimum_member_end_action":
        case = d["member_end_case"]
        turnbuckle = d["threaded_bracing_turnbuckle_arrangement_verified"]
        is_threaded_bracing = case == "threaded_tension_bracing_with_turnbuckles"
        if turnbuckle != is_threaded_bracing:
            raise ValueError("Verify turnbuckles only for the threaded tension-bracing exception.")
        actual = d["actual_design_axial_action_kn"]
        member_capacity = d["member_design_axial_capacity_kn"]
        factor = 1.0 if is_threaded_bracing else 0.3
        minimum = factor * member_capacity
        required = max(actual, minimum)
        intermediate = {
            "clause": "9.1.4(b)(iii)",
            "member_end_case": case,
            "actual_design_axial_action_kn": actual,
            "member_design_axial_capacity_kn": member_capacity,
            "minimum_design_axial_action_kn": minimum,
            "required_design_axial_action_kn": required,
            "minimum_fraction_of_member_design_capacity": factor,
        }
        if "connection_design_axial_capacity_kn" in d:
            capacity = d["connection_design_axial_capacity_kn"]
            intermediate["connection_design_axial_capacity_kn"] = capacity
            c["connection_axial_capacity"] = _connection_capacity_check(
                required, capacity, "kn", "9.1.4(b)(iii)"
            )
    elif k == "minimum_axial_splice_action":
        case = d["splice_case"]
        full_contact = d["full_contact_bearing_verified"]
        expected_full_contact = case == "compression_full_contact"
        if full_contact != expected_full_contact:
            raise ValueError("Splice case must agree with its verified full-contact condition.")
        alignment_verified = d["splice_parts_and_fasteners_hold_all_parts_in_line_verified"]
        if case == "compression_not_full_contact" and not alignment_verified:
            raise ValueError("The non-full-contact compression splice must hold all parts in line.")
        factors = {
            "axial_tension": 0.3,
            "compression_full_contact": 0.15,
            "compression_not_full_contact": 0.3,
        }
        actual = d["actual_design_axial_action_kn"]
        member_capacity = d["member_design_axial_capacity_kn"]
        factor = factors[case]
        minimum = factor * member_capacity
        required = max(actual, minimum)
        intermediate = {
            "clause": "9.1.4(b)(iv)" if case == "axial_tension" else "9.1.4(b)(v)",
            "splice_case": case,
            "actual_design_axial_action_kn": actual,
            "member_design_axial_capacity_kn": member_capacity,
            "minimum_design_axial_action_kn": minimum,
            "required_design_axial_action_kn": required,
            "minimum_fraction_of_member_design_capacity": factor,
        }
        if "connection_design_axial_capacity_kn" in d:
            capacity = d["connection_design_axial_capacity_kn"]
            intermediate["connection_design_axial_capacity_kn"] = capacity
            clause = "9.1.4(b)(iv)" if case == "axial_tension" else "9.1.4(b)(v)"
            c["connection_axial_capacity"] = _connection_capacity_check(
                required, capacity, "kn", clause
            )
    elif k == "minimum_combined_splice_actions":
        case = d["splice_case"]
        full_contact = d["full_contact_bearing_verified"]
        expected_full_contact = case == "compression_full_contact"
        if full_contact != expected_full_contact:
            raise ValueError("Splice case must agree with its verified full-contact condition.")
        alignment_verified = d["splice_parts_and_fasteners_hold_all_parts_in_line_verified"]
        if case == "compression_not_full_contact" and not alignment_verified:
            raise ValueError("The non-full-contact compression splice must hold all parts in line.")
        between_supports = d["splice_between_effective_lateral_supports_verified"]
        support_fields = {
            "effective_lateral_support_distance_mm",
            "amplification_factor_type",
            "amplification_factor",
            "amplification_factor_verified",
        }
        supplied_support_fields = support_fields.intersection(d)
        if between_supports:
            if case == "axial_tension":
                raise ValueError(
                    "The Clause 9.1.4(b)(v) support-span moment applies to compression splices."
                )
            if supplied_support_fields != support_fields:
                raise ValueError(
                    "A between-support compression splice requires its verified span and "
                    "Clause 4.4 amplification factor."
                )
        elif supplied_support_fields:
            raise ValueError("Support-span inputs require a verified between-support splice.")

        axial_factors = {
            "axial_tension": 0.3,
            "compression_full_contact": 0.15,
            "compression_not_full_contact": 0.3,
        }
        actual_axial = d["actual_design_axial_action_kn"]
        member_axial_capacity = d["member_design_axial_capacity_kn"]
        axial_factor = axial_factors[case]
        minimum_axial = axial_factor * member_axial_capacity
        required_axial = max(actual_axial, minimum_axial)
        actual_moment = d["actual_design_moment_knm"]
        member_moment_capacity = d["member_design_moment_capacity_knm"]
        minimum_flexural_moment = 0.3 * member_moment_capacity
        minimum_support_moment = 0.0
        if between_supports:
            minimum_support_moment = (
                d["amplification_factor"]
                * required_axial
                * d["effective_lateral_support_distance_mm"]
                / 1000
            )
        required_moment = max(actual_moment, minimum_flexural_moment, minimum_support_moment)
        axial_clause = "9.1.4(b)(iv)" if case == "axial_tension" else "9.1.4(b)(v)"
        intermediate = {
            "clause": "9.1.4(b)(vii)",
            "splice_case": case,
            "actual_design_axial_action_kn": actual_axial,
            "member_design_axial_capacity_kn": member_axial_capacity,
            "minimum_design_axial_action_kn": minimum_axial,
            "required_design_axial_action_kn": required_axial,
            "actual_design_moment_knm": actual_moment,
            "member_design_moment_capacity_knm": member_moment_capacity,
            "minimum_flexural_splice_moment_knm": minimum_flexural_moment,
            "minimum_between_supports_moment_knm": minimum_support_moment,
            "required_design_moment_knm": required_moment,
            "axial_splice_clause": axial_clause,
            "flexural_splice_clause": "9.1.4(b)(vi)",
            "splice_between_effective_lateral_supports": between_supports,
        }
        if between_supports:
            intermediate.update(
                {
                    "amplification_factor_type": d["amplification_factor_type"],
                    "amplification_factor": d["amplification_factor"],
                    "effective_lateral_support_distance_mm": d[
                        "effective_lateral_support_distance_mm"
                    ],
                    "moment_basis_axial_action_kn": required_axial,
                }
            )
        if "connection_design_axial_capacity_kn" in d:
            capacity = d["connection_design_axial_capacity_kn"]
            intermediate["connection_design_axial_capacity_kn"] = capacity
            c["connection_axial_capacity"] = _connection_capacity_check(
                required_axial, capacity, "kn", axial_clause
            )
        if "connection_design_moment_capacity_knm" in d:
            capacity = d["connection_design_moment_capacity_knm"]
            intermediate["connection_design_moment_capacity_knm"] = capacity
            c["connection_moment_capacity"] = _connection_capacity_check(
                required_moment, capacity, "knm", "9.1.4(b)(vi); 9.1.4(b)(vii)"
            )
    elif k == "minimum_compression_splice_between_supports":
        full_contact = d["full_contact_bearing_verified"]
        alignment_verified = d["splice_parts_and_fasteners_hold_all_parts_in_line_verified"]
        if not full_contact and not alignment_verified:
            raise ValueError("A non-full-contact compression splice must hold all parts in line.")
        factor = 0.15 if full_contact else 0.3
        actual_axial = d["actual_design_axial_action_kn"]
        member_capacity = d["member_design_axial_capacity_kn"]
        minimum_axial = factor * member_capacity
        required_axial = max(actual_axial, minimum_axial)
        moment_basis_axial = required_axial
        minimum_moment = (
            d["amplification_factor"]
            * moment_basis_axial
            * d["effective_lateral_support_distance_mm"]
            / 1000
        )
        actual_moment = d["actual_design_moment_knm"]
        required_moment = max(actual_moment, minimum_moment)
        intermediate = {
            "clause": "9.1.4(b)(v)",
            "actual_design_axial_action_kn": actual_axial,
            "member_design_axial_capacity_kn": member_capacity,
            "minimum_design_axial_action_kn": minimum_axial,
            "required_design_axial_action_kn": required_axial,
            "actual_design_moment_knm": actual_moment,
            "amplification_factor_type": d["amplification_factor_type"],
            "amplification_factor": d["amplification_factor"],
            "effective_lateral_support_distance_mm": d["effective_lateral_support_distance_mm"],
            "moment_basis_axial_action_kn": moment_basis_axial,
            "minimum_design_moment_knm": minimum_moment,
            "required_design_moment_knm": required_moment,
            "minimum_fraction_of_member_design_capacity": factor,
        }
        if "connection_design_axial_capacity_kn" in d:
            capacity = d["connection_design_axial_capacity_kn"]
            intermediate["connection_design_axial_capacity_kn"] = capacity
            c["connection_axial_capacity"] = _connection_capacity_check(
                required_axial, capacity, "kn", "9.1.4(b)(v)"
            )
        if "connection_design_moment_capacity_knm" in d:
            capacity = d["connection_design_moment_capacity_knm"]
            intermediate["connection_design_moment_capacity_knm"] = capacity
            c["connection_moment_capacity"] = _connection_capacity_check(
                required_moment, capacity, "knm", "9.1.4(b)(v)"
            )
    elif k == "minimum_flexural_splice_action":
        actual = d["actual_design_moment_knm"]
        minimum = 0.3 * d["member_design_moment_capacity_knm"]
        required = max(actual, minimum)
        intermediate = {
            "clause": "9.1.4(b)(vi)",
            "actual_design_moment_knm": actual,
            "member_design_moment_capacity_knm": d["member_design_moment_capacity_knm"],
            "minimum_design_moment_knm": minimum,
            "required_design_moment_knm": required,
            "minimum_fraction_of_member_design_capacity": 0.3,
        }
        if "connection_design_moment_capacity_knm" in d:
            capacity = d["connection_design_moment_capacity_knm"]
            intermediate["connection_design_moment_capacity_knm"] = capacity
            c["connection_moment_capacity"] = _connection_capacity_check(
                required, capacity, "knm", "9.1.4(b)(vi)"
            )
    elif k == "shear_only_splice_eccentric_action":
        shear = d["actual_design_shear_kn"]
        eccentricity = d["force_eccentricity_mm"]
        eccentric_moment = shear * eccentricity / 1000
        intermediate = {
            "clause": "9.1.4(b)(vi)",
            "actual_design_shear_kn": shear,
            "force_eccentricity_mm": eccentricity,
            "required_design_shear_kn": shear,
            "eccentric_design_moment_knm": eccentric_moment,
            "required_design_moment_knm": eccentric_moment,
        }
        if "connection_design_shear_capacity_kn" in d:
            capacity = d["connection_design_shear_capacity_kn"]
            intermediate["connection_design_shear_capacity_kn"] = capacity
            c["connection_shear_capacity"] = _connection_capacity_check(
                shear, capacity, "kn", "9.1.4(b)(vi)"
            )
        if "connection_design_moment_capacity_knm" in d:
            capacity = d["connection_design_moment_capacity_knm"]
            intermediate["connection_design_moment_capacity_knm"] = capacity
            c["connection_moment_capacity"] = _connection_capacity_check(
                eccentric_moment, capacity, "knm", "9.1.4(b)(vi)"
            )
    elif k == "joint_eccentricity_action":
        special_detail = d["connection_detail_case"] != "general"
        if (
            d["fatigue_loading"]
            and special_detail
            and not d["fatigue_detail_eccentricity_assessment_verified"]
        ):
            raise ValueError(
                "Fatigue-loaded angle connections require the Clause 9.1.5 eccentricity "
                "detail to be assessed."
            )
        if (
            d["centroidal_axes_meet_practicable_verified"]
            and not d["centroidal_axes_meet_at_joint_verified"]
        ):
            raise ValueError(
                "Arrange the centroidal axes to meet at a point when that is practicable."
            )
        fx, fy, fz = d["force_kn"]
        ex, ey, ez = d["eccentricity_vector_mm"]
        moments = [
            (ey * fz - ez * fy) / 1000,
            (ez * fx - ex * fz) / 1000,
            (ex * fy - ey * fx) / 1000,
        ]
        intermediate = {
            "clause": "9.1.5",
            "connection_detail_case": d["connection_detail_case"],
            "force_kn": [fx, fy, fz],
            "eccentricity_vector_mm": [ex, ey, ez],
            "eccentricity_moment_vector_knm": moments,
            "centroidal_axes_meet_practicable_verified": d[
                "centroidal_axes_meet_practicable_verified"
            ],
            "centroidal_axes_meet_at_joint_verified": d["centroidal_axes_meet_at_joint_verified"],
            "fatigue_loading": d["fatigue_loading"],
        }
    elif k == "fastener_selection_suitability":
        selected = d["selected_fastener_system"]
        no_slip_systems = {"friction_type_8_8_TF", "friction_type_10_9_TF", "fitted_bolt", "weld"}
        dynamic_systems = {
            "friction_type_8_8_TF",
            "friction_type_10_9_TF",
            "locking_device",
            "weld",
        }
        no_slip_required = d["serviceability_slip_to_be_avoided"]
        dynamic_required = d["impact_or_vibration_present"]
        no_slip_satisfied = not no_slip_required or selected in no_slip_systems
        dynamic_satisfied = not dynamic_required or selected in dynamic_systems
        c["serviceability_slip_avoidance"] = {
            "required": no_slip_required,
            "satisfied": no_slip_satisfied,
            "clause": "9.1.6",
        }
        c["impact_or_vibration"] = {
            "required": dynamic_required,
            "satisfied": dynamic_satisfied,
            "clause": "9.1.6",
        }
        c["fastener_selection"] = {
            "satisfied": no_slip_satisfied and dynamic_satisfied,
            "clause": "9.1.6",
        }
        intermediate = {
            "selected_fastener_system": selected,
            "systems_suitable_when_service_slip_is_avoided": sorted(no_slip_systems),
            "systems_suitable_for_impact_or_vibration": sorted(dynamic_systems),
        }
    elif k == "combined_connection_action_assignment":
        groups = {item["group_id"]: item["fastener_class"] for item in d["component_groups"]}
        if len(groups) != len(d["component_groups"]):
            raise ValueError("Component group IDs must be unique.")
        cases = d["load_cases"]
        case_ids = [item["case_id"] for item in cases]
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("Load case IDs must be unique.")
        weld_groups = [group_id for group_id, kind in groups.items() if kind == "weld"]
        if len(weld_groups) > 1:
            raise ValueError("Represent all welds as one aggregate weld group.")
        non_slip_groups = {group_id for group_id, kind in groups.items() if kind == "non_slip"}
        all_non_slip_groups = non_slip_groups | set(weld_groups)
        has_slip_type = any(kind == "slip_type" for kind in groups.values())
        if not all_non_slip_groups or not (has_slip_type or len(all_non_slip_groups) > 1):
            raise ValueError("Clause 9.1.7 requires mixed slip/non-slip or non-slip groups.")
        assignments = []
        zero_actions = {name: 0.0 for name in CONNECTION_ACTIONS["required"]}
        for load_case in cases:
            stage = load_case["stage"]
            actions = load_case["actions"]
            if stage == "non_weld_action":
                shares = load_case["shares"]
                share_ids = [share["group_id"] for share in shares]
                if not shares or len(set(share_ids)) != len(share_ids):
                    raise ValueError("Non-weld actions require unique non-slip load shares.")
                if not set(share_ids) <= non_slip_groups:
                    raise ValueError(
                        "Clause 9.1.7 assigns non-weld-stage actions only to non-slip groups."
                    )
                share_total = sum(share["fraction"] for share in shares)
                if not isclose(share_total, 1.0, rel_tol=0.0, abs_tol=1e-9):
                    raise ValueError("Non-slip action shares must sum to 1.0.")
                fractions = {share["group_id"]: share["fraction"] for share in shares}
            else:
                if not weld_groups:
                    raise ValueError("Weld-sequence load cases require an aggregate weld group.")
                if load_case["shares"]:
                    raise ValueError("Weld-sequence actions must be assigned to the weld group.")
                fractions = {weld_groups[0]: 1.0}
            group_assignments = [
                {
                    "group_id": group_id,
                    "assigned_share": fractions.get(group_id, 0.0),
                    "assigned_actions": {
                        name: actions[name] * fractions.get(group_id, 0.0)
                        for name in CONNECTION_ACTIONS["required"]
                    }
                    if fractions.get(group_id, 0.0)
                    else dict(zero_actions),
                }
                for group_id in groups
            ]
            assignments.append(
                {
                    "case_id": load_case["case_id"],
                    "stage": stage,
                    "component_group_assignments": group_assignments,
                }
            )
        c["clause_9_1_7_action_assignment"] = {"satisfied": True, "clause": "9.1.7"}
        intermediate = {"load_case_assignments": assignments}
    elif k == "bolt_group_out_of_plane":
        design_actions = {
            "force_x_kn": d["group_force_x_kn"],
            "force_y_kn": d["group_force_y_kn"],
            "tension_kn": d["group_tension_kn"],
            "moment_x_knm": d["group_moment_x_knm"],
            "moment_y_knm": d["group_moment_y_knm"],
            "moment_z_knm": d["group_moment_z_knm"],
        }
        c, intermediate = _assess_out_of_plane_bolt_group(
            d,
            d["bolt_actions"],
            design_actions,
            "Externally assessed under Clause 9.1.3.",
        )
        filler_check = _filler_plate_detailing_check(d)
        if filler_check is not None:
            c["filler_plate_detailing"] = filler_check
    elif k == "bolt_group_elastic_3d":
        layout = d["bolt_layout"]
        bolt_ids = [item["bolt_id"] for item in layout]
        points = [tuple(item["position_mm"]) for item in layout]
        if len(set(bolt_ids)) != len(bolt_ids):
            raise ValueError("Bolt IDs must be unique.")
        if len(set(points)) != len(points):
            raise ValueError("Bolt positions must be distinct.")
        count = len(points)
        cx, cy = (sum(point[axis] for point in points) / count for axis in (0, 1))
        centered_points = [(x - cx, y - cy) for x, y in points]
        polar_sum = sum(x * x + y * y for x, y in centered_points)
        if not isfinite(polar_sum) or polar_sum <= 0:
            raise ValueError("Bolt group polar sum must be finite and positive.")
        sxx = sum(x * x for x, _ in centered_points)
        syy = sum(y * y for _, y in centered_points)
        sxy = sum(x * y for x, y in centered_points)
        determinant = sxx * syy - sxy * sxy
        if not isfinite(determinant) or determinant <= 1e-12 * max(sxx * syy, 1.0):
            raise ValueError("Bolt layout must be non-collinear for biaxial tension distribution.")
        moment_x = d["group_moment_x_knm"] * 1000
        moment_y = d["group_moment_y_knm"] * 1000
        coefficient_x = (-moment_y * syy - moment_x * sxy) / determinant
        coefficient_y = (moment_x * sxx + moment_y * sxy) / determinant
        tension_actions = [
            d["group_tension_kn"] / count + coefficient_x * x + coefficient_y * y
            for x, y in centered_points
        ]
        tension_tolerance = max(1e-9, 1e-9 * d["group_tension_kn"])
        if any(action < -tension_tolerance for action in tension_actions):
            raise ValueError(
                "Elastic distribution produces bolt compression; use a verified contact/slack-bolt "
                "analysis for this load case."
            )
        tension_actions = [max(0.0, action) for action in tension_actions]
        moment_z = d["group_moment_z_knm"] * 1000
        bolt_actions = []
        for item, (x, y), tension in zip(layout, centered_points, tension_actions, strict=True):
            bolt_actions.append(
                {
                    "bolt_id": item["bolt_id"],
                    "position_mm": [x, y],
                    "shear_x_kn": d["group_force_x_kn"] / count - moment_z * y / polar_sum,
                    "shear_y_kn": d["group_force_y_kn"] / count + moment_z * x / polar_sum,
                    "tension_action_kn": tension,
                    "prying_tension_kn": item["prying_tension_kn"],
                    "prying_force_assessment_verified": item["prying_force_assessment_verified"],
                }
            )
        design_actions = {
            "force_x_kn": d["group_force_x_kn"],
            "force_y_kn": d["group_force_y_kn"],
            "tension_kn": d["group_tension_kn"],
            "moment_x_knm": d["group_moment_x_knm"],
            "moment_y_knm": d["group_moment_y_knm"],
            "moment_z_knm": d["group_moment_z_knm"],
        }
        c, intermediate = _assess_out_of_plane_bolt_group(
            d,
            bolt_actions,
            design_actions,
            "Calculated by a rigid-plate, equal-bolt-stiffness elastic method; project assumptions "
            "and experimental basis are attested.",
        )
        filler_check = _filler_plate_detailing_check(d)
        if filler_check is not None:
            c["filler_plate_detailing"] = filler_check
        intermediate.update(
            {
                "distribution_method": "rigid_plate_equal_stiffness_linear_elastic",
                "centroid_mm": [cx, cy],
                "polar_sum_mm2": polar_sum,
                "axial_distribution_second_moments_mm2": {
                    "sum_x2": sxx,
                    "sum_xy": sxy,
                    "sum_y2": syy,
                },
                "distributed_bolt_actions": bolt_actions,
            }
        )
    elif k in {"bolt", "bolt_group"}:
        v, n, intermediate = _bolt(d)
        tension_action = d["tension_action_kn"]
        if k == "bolt":
            tension_action += d["prying_tension_kn"]
            intermediate.update(
                {
                    "member_tension_action_kn": d["tension_action_kn"],
                    "prying_tension_action_kn": d["prying_tension_kn"],
                    "total_bolt_tension_action_kn": tension_action,
                }
            )
        actions = [(d["shear_action_kn"], tension_action)]
        if k == "bolt_group":
            if d["shear_action_kn"] or d["tension_action_kn"] or d["prying_tension_kn"]:
                raise ValueError(
                    "Group uses signed in-plane actions only; component and prying actions "
                    "must be zero."
                )
            points = d["points_mm"]
            if len({tuple(p) for p in points}) != len(points):
                raise ValueError("Bolt positions must be distinct.")
            count = len(points)
            cx, cy = (sum(p[i] for p in points) / count for i in (0, 1))
            j = sum((x - cx) ** 2 + (y - cy) ** 2 for x, y in points)
            if not isfinite(j) or j <= 0:
                raise ValueError("Bolt group polar sum must be finite and positive.")
            mz = d["moment_z_knm"] * 1000
            forces = [
                [
                    d["force_x_kn"] / count - mz * (y - cy) / j,
                    d["force_y_kn"] / count + mz * (x - cx) / j,
                ]
                for x, y in points
            ]
            actions = [(hypot(*f), 0) for f in forces]
            intermediate.update(centroid_mm=[cx, cy], polar_sum_mm2=j, bolt_forces_kn=forces)
        for i, (va, na) in enumerate(actions):
            prefix = f"bolt_{i}_" if k == "bolt_group" else ""
            c[prefix + "shear"] = _check(v, 0.8, va, "9.2.2.1")
            tension_clause = "9.1.8; 9.2.2.2" if k == "bolt" else "9.2.2.2"
            c[prefix + "tension"] = _check(n, 0.8, na, tension_clause)
            u = (va / (0.8 * v)) ** 2 + (na / (0.8 * n)) ** 2
            c[prefix + "interaction"] = {"utilisation": u, "satisfied": u <= 1, "clause": "9.2.2.3"}
        filler_check = _filler_plate_detailing_check(d)
        if filler_check is not None:
            c["filler_plate_detailing"] = filler_check
    elif k == "bearing":
        a = 3.2 * d["diameter_mm"] * d["ply_thickness_mm"] * d["ultimate_strength_mpa"] / 1000
        b = (
            d["effective_edge_distance_mm"]
            * d["ply_thickness_mm"]
            * d["ultimate_strength_mpa"]
            / 1000
        )
        c["bearing"] = _check(min(a, b), 0.9, d["action_kn"], "9.2.2.4")
        intermediate = {"bearing_kn": a, "edge_kn": b}
    elif k == "slip":
        kh = {"standard": 1, "short_slot": 0.85, "oversize": 0.85, "long_slot": 0.7}[d["hole_type"]]
        v = d["slip_factor"] * d["interfaces"] * d["installation_tension_kn"] * kh
        u = d["shear_action_kn"] / (0.7 * v) + d["tension_action_kn"] / (
            0.7 * d["installation_tension_kn"]
        )
        c["slip"] = _check(v, 0.7, d["shear_action_kn"], "9.2.3.1; 3.5.5")
        c["interaction"] = {"utilisation": u, "satisfied": u <= 1, "clause": "9.2.3.3"}
        c["surface_requirements"] = _slip_surface_requirements_check(d)
        intermediate = {"hole_factor": kh}
    elif k == "block_shear":
        if d["net_shear_area_mm2"] > d["gross_shear_area_mm2"]:
            raise ValueError("Net shear area cannot exceed gross shear area.")
        fy, fu = d["yield_strength_mpa"], d["ultimate_strength_mpa"]
        if fu < fy:
            raise ValueError("Ultimate strength cannot be below yield strength.")
        kb = 1 if d["uniform_tension"] else 0.5
        t = kb * fu * d["net_tension_area_mm2"]
        modes = [
            (0.6 * fu * d["net_shear_area_mm2"] + t) / 1000,
            (0.6 * fy * d["gross_shear_area_mm2"] + t) / 1000,
        ]
        c["block_shear"] = _check(min(modes), 0.75, d["action_kn"], "9.1.9(e)")
        intermediate = {"eccentricity_factor": kb, "nominal_modes_kn": modes}
    elif k == "block_shear_paths":
        fy, fu, thickness = (
            d["yield_strength_mpa"],
            d["ultimate_strength_mpa"],
            d["thickness_mm"],
        )
        if fu < fy:
            raise ValueError("Ultimate strength cannot be below yield strength.")
        paths = d["candidate_paths"]
        path_ids = [path["path_id"] for path in paths]
        if len(set(path_ids)) != len(path_ids):
            raise ValueError("Block-shear path IDs must be unique.")
        evaluated_paths = []
        for path in paths:
            gross_length = path["gross_shear_length_mm"]
            net_length = path["net_shear_length_mm"]
            if net_length > gross_length:
                raise ValueError("Net shear length cannot exceed gross shear length.")
            gross_area = thickness * gross_length
            net_shear_area = thickness * net_length
            net_tension_area = thickness * path["net_tension_length_mm"]
            kbs = 1.0 if path["uniform_tension"] else 0.5
            tension_term_kn = kbs * fu * net_tension_area / 1000
            nominal_rupture_kn = 0.6 * fu * net_shear_area / 1000 + tension_term_kn
            nominal_yielding_kn = 0.6 * fy * gross_area / 1000 + tension_term_kn
            nominal_capacity_kn = min(nominal_rupture_kn, nominal_yielding_kn)
            governing_mode = (
                "shear_rupture_plus_tension_rupture"
                if nominal_rupture_kn <= nominal_yielding_kn
                else "shear_yielding_plus_tension_rupture"
            )
            capacity_check = _check(nominal_capacity_kn, 0.75, d["action_kn"], "9.1.9(e)")
            evaluated_paths.append(
                {
                    "path_id": path["path_id"],
                    "gross_shear_area_mm2": gross_area,
                    "net_shear_area_mm2": net_shear_area,
                    "net_tension_area_mm2": net_tension_area,
                    "eccentricity_factor_kbs": kbs,
                    "nominal_tension_term_kn": tension_term_kn,
                    "nominal_shear_rupture_mode_capacity_kn": nominal_rupture_kn,
                    "nominal_shear_yielding_mode_capacity_kn": nominal_yielding_kn,
                    "governing_mode": governing_mode,
                    **capacity_check,
                }
            )
        controlling_path = min(evaluated_paths, key=lambda item: item["nominal_capacity_kn"])
        c["block_shear_path_set"] = {
            "paths": evaluated_paths,
            "controlling_path_id": controlling_path["path_id"],
            "nominal_capacity_kn": controlling_path["nominal_capacity_kn"],
            "design_capacity_kn": controlling_path["design_capacity_kn"],
            "capacity_factor": 0.75,
            "utilisation": controlling_path["utilisation"],
            "satisfied": controlling_path["satisfied"],
            "clause": "9.1.9(e)",
        }
        intermediate = {
            "thickness_mm": thickness,
            "yield_strength_mpa": fy,
            "ultimate_strength_mpa": fu,
            "action_kn": d["action_kn"],
            "rupture_path_set_completeness_and_net_length_basis_verified": True,
            "clause": "9.1.9(e); 9.1.10",
        }
    elif k == "pin":
        fy, dia = d["yield_strength_mpa"], d["diameter_mm"]
        c["shear"] = _check(
            0.62 * fy * d["shear_planes"] * pi * dia**2 / 4000, 0.8, d["shear_action_kn"], "9.4.1"
        )
        c["bearing"] = _check(
            1.4 * fy * dia * d["ply_thickness_mm"] * (0.5 if d["rotates"] else 1) / 1000,
            0.8,
            d["bearing_action_kn"],
            "9.4.2",
        )
        c["bending"] = _check(fy * dia**3 / 6e6, 0.8, d["moment_action_knm"], "9.4.3", "knm")
    elif k == "butt_weld_transition":
        fatigue_fields = {
            "fatigue_slope_limit",
            "fatigue_slope_limit_verified",
            "fatigue_assessment_reference",
        }
        supplied_fatigue_fields = fatigue_fields.intersection(d)
        fatigue_limit_used = bool(supplied_fatigue_fields)
        if fatigue_limit_used and supplied_fatigue_fields != fatigue_fields:
            raise ValueError(
                "A fatigue-specific transition slope requires its assessed limit, verification, "
                "and assessment reference."
            )
        maximum_slope_ratio = d["fatigue_slope_limit"] if fatigue_limit_used else 1.0
        slope_ratio = d["dimension_change_mm"] / d["effective_transition_run_mm"]
        minimum_transition_run = d["dimension_change_mm"] / maximum_slope_ratio
        clause = (
            "9.6.2.6; externally assessed fatigue-specific slope"
            if fatigue_limit_used
            else "9.6.2.6"
        )
        c["transition_geometry"] = {
            "clause": clause,
            "applicable": True,
            "tension_loaded_joint_verified": d["tension_loaded_joint_verified"],
            "smooth_transition_verified": d["smooth_transition_verified"],
            "transition_method": d["transition_method"],
            "dimension_change_mm": d["dimension_change_mm"],
            "effective_transition_run_mm": d["effective_transition_run_mm"],
            "slope_ratio": slope_ratio,
            "maximum_permitted_slope_ratio": maximum_slope_ratio,
            "minimum_transition_run_mm": minimum_transition_run,
            "fatigue_assessment_reference": d.get("fatigue_assessment_reference"),
            "satisfied": slope_ratio <= maximum_slope_ratio,
        }
        intermediate = {
            "slope_ratio": slope_ratio,
            "maximum_permitted_slope_ratio": maximum_slope_ratio,
            "minimum_transition_run_mm": minimum_transition_run,
            "fatigue_slope_limit_used": fatigue_limit_used,
        }
    elif k == "built_up_component_end_weld":
        applicable = d["side_fillet_only"]
        minimum_length = None
        if applicable:
            minimum_length = d["connected_component_width_mm"]
            if d["tapered_component"]:
                minimum_length = max(minimum_length, d["widest_component_width_mm"])
                minimum_length = max(minimum_length, d["taper_length_mm"])
        weld_length = d["weld_length_per_joint_line_mm"]
        c["built_up_termination"] = {
            "clause": "9.6.3.9(a)",
            "applicable": applicable,
            "minimum_length_mm": minimum_length,
            "provided_length_per_joint_line_mm": weld_length,
            "satisfied": not applicable or weld_length >= minimum_length,
        }
        intermediate = {
            "connected_component_width_mm": d["connected_component_width_mm"],
            "widest_component_width_mm": d["widest_component_width_mm"],
            "taper_length_mm": d["taper_length_mm"],
        }
    elif k == "cap_plate_weld":
        minimum_length = d["member_width_at_contact_face_mm"]
        weld_length = d["weld_length_per_joint_line_mm"]
        c["built_up_termination"] = {
            "clause": "9.6.3.9(b)",
            "minimum_length_per_joint_line_mm": minimum_length,
            "provided_length_per_joint_line_mm": weld_length,
            "satisfied": weld_length >= minimum_length,
        }
        intermediate = {"member_width_at_contact_face_mm": d["member_width_at_contact_face_mm"]}
    elif k == "beam_compression_member_weld":
        required_extension = d["compression_member_max_dimension_mm"]
        checks = {
            "between_beam_faces": {
                "clause": "9.6.3.9(c)",
                "required_mm": d["beam_depth_mm"],
                "provided_mm": d["weld_length_between_beam_faces_mm"],
                "satisfied": d["weld_length_between_beam_faces_mm"] >= d["beam_depth_mm"],
            },
            "below_beam": {
                "clause": "9.6.3.9(c)(i)/(ii)",
                "required_mm": required_extension,
                "provided_mm": d["weld_extension_below_bottom_mm"],
                "satisfied": d["weld_extension_below_bottom_mm"] >= required_extension,
            },
        }
        if d["connection_restraint"] == "restrained":
            checks["above_beam"] = {
                "clause": "9.6.3.9(c)(ii)",
                "required_mm": required_extension,
                "provided_mm": d["weld_extension_above_top_mm"],
                "satisfied": d["weld_extension_above_top_mm"] >= required_extension,
            }
        c["built_up_termination"] = {
            "clause": "9.6.3.9(c)",
            "connection_restraint": d["connection_restraint"],
            "checks": checks,
            "satisfied": all(check["satisfied"] for check in checks.values()),
        }
        intermediate = {
            "beam_depth_mm": d["beam_depth_mm"],
            "compression_member_max_dimension_mm": required_extension,
        }
    elif k == "fillet_design":
        if d["thinnest_part_mm"] > d["thickest_part_mm"]:
            raise ValueError("Thinnest part cannot be thicker than the thickest part.")
        if d["parallel_weld_count"] == 2 and not d["parallel_load_share_verified"]:
            raise ValueError("Load sharing between the two parallel welds must be verified.")
        macro_test_fields = {
            "automatic_arc_welding_process_verified",
            "production_weld_macro_test_verified",
            "macro_test_required_penetration_achieved_verified",
            "macro_test_record_reference",
            "macro_test_additional_penetration_mm",
        }
        supplied_macro_test_fields = macro_test_fields.intersection(d)
        macro_test_used = bool(supplied_macro_test_fields)
        if macro_test_used and supplied_macro_test_fields != macro_test_fields:
            raise ValueError(
                "A fillet macro-test throat increase requires automatic arc process verification, "
                "a production-weld macro-test record, achieved required penetration, the record "
                "reference, and measured penetration beyond the theoretical root."
            )
        macro_test_extra_penetration = (
            d["macro_test_additional_penetration_mm"] if macro_test_used else 0
        )
        leg_1 = d["leg_1_mm"] - d["root_gap_mm"]
        leg_2 = d["leg_2_mm"] - d["root_gap_mm"]
        if min(leg_1, leg_2) <= 0:
            raise ValueError("Root gap must leave a positive inscribed fillet triangle.")
        thickness = d["thickest_part_mm"]
        minimum_table_size = (
            3 if thickness <= 7 else 4 if thickness <= 10 else 5 if thickness <= 15 else 6
        )
        minimum_size = (
            0 if d["reinforces_butt_weld"] else min(minimum_table_size, d["thinnest_part_mm"])
        )
        edge_thickness = d["edge_material_thickness_mm"]
        maximum_edge_size = (
            edge_thickness
            if edge_thickness < 6 or d["edge_built_out_verified"]
            else edge_thickness - 1
        )
        size_checks = {
            "minimum_size": {
                "required_mm": minimum_size,
                "provided_leg_1_mm": leg_1,
                "provided_leg_2_mm": leg_2,
                "satisfied": min(leg_1, leg_2) >= minimum_size,
            },
            "maximum_size_along_edge": {
                "maximum_mm": maximum_edge_size,
                "largest_provided_leg_mm": max(leg_1, leg_2),
                "built_out_verified": d["edge_built_out_verified"],
                "satisfied": max(leg_1, leg_2) <= maximum_edge_size,
            },
        }
        theta = radians(d["included_angle_deg"])
        opposite_side = sqrt(leg_1**2 + leg_2**2 - 2 * leg_1 * leg_2 * cos(theta))
        geometric_throat = leg_1 * leg_2 * sin(theta) / opposite_side
        macro_test_throat = geometric_throat + 0.85 * macro_test_extra_penetration
        nominal_size = max(leg_1, leg_2)
        segment_length = d["overall_length_per_segment_mm"]
        length_reduction_factor = min(1, segment_length / (4 * nominal_size))
        design_throat = macro_test_throat * length_reduction_factor
        intermittent_minimum_length = max(40, 4 * nominal_size)
        total_effective_length = segment_length * d["segment_count"] * d["parallel_weld_count"]
        effective_area = design_throat * total_effective_length
        length_checks = {
            "overall_length_per_segment_mm": segment_length,
            "segment_count_per_weld_line": d["segment_count"],
            "parallel_weld_count": d["parallel_weld_count"],
            "total_effective_length_mm": total_effective_length,
            "length_based_size_reduction_factor": length_reduction_factor,
            "design_throat_mm": design_throat,
            "effective_area_mm2": effective_area,
            "intermittent_minimum_length_mm": intermittent_minimum_length,
            "satisfied": not d["intermittent_segment"]
            or segment_length >= intermittent_minimum_length,
        }
        c["weld_size"] = {
            "clause": "9.6.3.2; 9.6.3.3",
            "checks": size_checks,
            "satisfied": all(check["satisfied"] for check in size_checks.values()),
        }
        c["weld_length_and_area"] = {
            "clause": "9.6.3.5; 9.6.3.6",
            **length_checks,
        }
        clauses = ["9.6.3.1", "9.6.3.2", "9.6.3.3", "9.6.3.4", "9.6.3.5", "9.6.3.6"]
        if d["parallel_weld_count"] == 2 and d["forms_built_up_member"]:
            transverse_limit = (
                min(16 * d["thinnest_part_mm"], 200)
                if d["member_force_type"] == "tension"
                else 32 * d["thinnest_part_mm"]
            )
            c["parallel_weld_spacing"] = {
                "clause": "9.6.3.7",
                "provided_mm": d["transverse_weld_spacing_mm"],
                "maximum_mm": transverse_limit,
                "satisfied": d["transverse_weld_spacing_mm"] <= transverse_limit,
            }
            clauses.append("9.6.3.7")
            if d["intermittent_segment"] and d["member_force_type"] != "other":
                clear_spacing_limit = (
                    min(24 * d["thinnest_part_mm"], 300)
                    if d["member_force_type"] == "tension"
                    else min(16 * d["thinnest_part_mm"], 300)
                )
                c["intermittent_clear_spacing"] = {
                    "clause": "9.6.3.8",
                    "provided_mm": d["clear_spacing_mm"],
                    "maximum_mm": clear_spacing_limit,
                    "at_built_up_member_end": d["at_built_up_member_end"],
                    "satisfied": d["at_built_up_member_end"]
                    or d["clear_spacing_mm"] <= clear_spacing_limit,
                }
                clauses.append("9.6.3.8")
        strength_check, strength_intermediate = _fillet_strength_check(
            d, design_throat, total_effective_length
        )
        strength_clause = "9.6.3.10; 9.6.3.4 macro-test throat" if macro_test_used else "9.6.3.10"
        c["weld_strength"] = {**strength_check, "clause": strength_clause}
        clauses.append("9.6.3.10")
        intermediate = {
            "provided_leg_lengths_after_root_gap_mm": [leg_1, leg_2],
            "geometric_throat_without_macro_test_mm": geometric_throat,
            "geometric_throat_before_length_reduction_mm": macro_test_throat,
            "macro_test_throat_increase": {
                "used": macro_test_used,
                "automatic_arc_welding_process_verified": d.get(
                    "automatic_arc_welding_process_verified", False
                ),
                "production_weld_macro_test_verified": d.get(
                    "production_weld_macro_test_verified", False
                ),
                "required_penetration_achieved_verified": d.get(
                    "macro_test_required_penetration_achieved_verified", False
                ),
                "record_reference": d.get("macro_test_record_reference"),
                "t_t1_mm": geometric_throat if macro_test_used else None,
                "t_t2_mm": macro_test_extra_penetration if macro_test_used else None,
                "figure_design_throat_before_length_reduction_mm": (
                    macro_test_throat if macro_test_used else None
                ),
            },
            "design_throat_mm": design_throat,
            "total_effective_length_mm": total_effective_length,
            "effective_area_mm2": effective_area,
            **strength_intermediate,
        }
    elif k == "incomplete_butt_design":
        has_single_v_depth = "preparation_depth_mm" in d
        has_double_v_depths = "double_v_preparation_depths_mm" in d
        if d["preparation_type"] == "single_v":
            if not has_single_v_depth or has_double_v_depths:
                raise ValueError("Single-V preparation requires only preparation_depth_mm.")
            preparation_depth = d["preparation_depth_mm"]
        else:
            if has_single_v_depth or not has_double_v_depths:
                raise ValueError("Double-V preparation requires only two double-V depth values.")
            preparation_depth = sum(d["double_v_preparation_depths_mm"])
        throat_reduction_per_side = 3 if d["preparation_angle_deg"] <= 60 else 0
        throat_reduction = throat_reduction_per_side * (
            2 if d["preparation_type"] == "double_v" else 1
        )
        throat = preparation_depth - throat_reduction
        if throat <= 0:
            raise ValueError("Preparation geometry must produce a positive design throat.")
        macro_test_fields = {
            "automatic_arc_welding_process_verified",
            "production_weld_macro_test_verified",
            "macro_test_required_penetration_achieved_verified",
            "macro_test_record_reference",
            "macro_test_penetration_beyond_preparation_mm",
        }
        supplied_macro_test_fields = macro_test_fields.intersection(d)
        macro_test_used = bool(supplied_macro_test_fields)
        if macro_test_used and supplied_macro_test_fields != macro_test_fields:
            raise ValueError(
                "A macro-test throat increase requires automatic arc process verification, "
                "a production-weld macro-test record, achieved required penetration, the "
                "record reference, and measured penetration beyond the preparation depth."
            )
        macro_test_extra_penetration = (
            d["macro_test_penetration_beyond_preparation_mm"] if macro_test_used else 0
        )
        macro_test_throat_limit = preparation_depth + 0.85 * macro_test_extra_penetration
        if macro_test_used:
            throat = max(throat, macro_test_throat_limit)
        length = d["continuous_full_size_weld_length_mm"]
        weld_data = {
            "weld_strength_mpa": d["weld_strength_mpa"],
            "quality": d["quality"],
            "thin_rhs_longitudinal": d["thin_rhs_longitudinal"],
            "lap_length_mm": 0,
            "action_kn": d["action_kn"],
        }
        throat_clause = (
            "9.6.2.3(b)(ii)(A)" if d["preparation_angle_deg"] <= 60 else "9.6.2.3(b)(ii)(B)"
        )
        macro_clause = "; 9.6.2.3(b)(iii); 9.6.3.4" if macro_test_used else ""
        clause = f"{throat_clause}{macro_clause}; 9.6.2.4; 9.6.2.5; 9.6.2.7(c); 9.6.3.10"
        strength_check, strength_intermediate = _fillet_strength_check(
            weld_data, throat, length, clause
        )
        c["weld_strength"] = {"clause": clause, **strength_check}
        intermediate = {
            "preparation_type": f"non_prequalified_{d['preparation_type']}",
            "preparation_depth_mm": d.get("preparation_depth_mm"),
            "double_v_preparation_depths_mm": d.get("double_v_preparation_depths_mm"),
            "combined_preparation_depth_mm": preparation_depth,
            "preparation_angle_deg": d["preparation_angle_deg"],
            "total_throat_reduction_mm": throat_reduction,
            "design_throat_mm": throat,
            "macro_test_throat_increase": {
                "used": macro_test_used,
                "automatic_arc_welding_process_verified": d.get(
                    "automatic_arc_welding_process_verified", False
                ),
                "production_weld_macro_test_verified": d.get(
                    "production_weld_macro_test_verified", False
                ),
                "required_penetration_achieved_verified": d.get(
                    "macro_test_required_penetration_achieved_verified", False
                ),
                "record_reference": d.get("macro_test_record_reference"),
                "preparation_depth_t_t1_mm": preparation_depth if macro_test_used else None,
                "penetration_beyond_preparation_t_t2_mm": (
                    macro_test_extra_penetration if macro_test_used else None
                ),
                "maximum_design_throat_mm": macro_test_throat_limit if macro_test_used else None,
            },
            "effective_length_mm": length,
            "effective_area_mm2": throat * length,
            **strength_intermediate,
        }
    elif k == "prequalified_incomplete_butt_design":
        macro_test_fields = {
            "preparation_depth_mm",
            "automatic_arc_welding_process_verified",
            "production_weld_macro_test_verified",
            "macro_test_required_penetration_achieved_verified",
            "macro_test_record_reference",
            "macro_test_penetration_beyond_preparation_mm",
        }
        supplied_macro_test_fields = macro_test_fields.intersection(d)
        macro_test_used = bool(supplied_macro_test_fields)
        if macro_test_used and supplied_macro_test_fields != macro_test_fields:
            raise ValueError(
                "A prequalified butt-weld throat increase requires preparation depth, "
                "automatic arc process verification, production-weld macro-test evidence, "
                "achieved required penetration, the record reference, and measured "
                "penetration beyond the preparation."
            )
        macro_test_extra_penetration = (
            d["macro_test_penetration_beyond_preparation_mm"] if macro_test_used else 0
        )
        macro_test_throat_limit = (
            d["preparation_depth_mm"] + 0.85 * macro_test_extra_penetration
            if macro_test_used
            else None
        )
        throat = (
            max(d["prequalified_design_throat_mm"], macro_test_throat_limit)
            if macro_test_used
            else d["prequalified_design_throat_mm"]
        )
        length = d["continuous_full_size_weld_length_mm"]
        weld_data = {
            "weld_strength_mpa": d["weld_strength_mpa"],
            "quality": d["quality"],
            "thin_rhs_longitudinal": d["thin_rhs_longitudinal"],
            "lap_length_mm": 0,
            "action_kn": d["action_kn"],
        }
        clause = "9.6.2.3(b)(i); 9.6.2.4; 9.6.2.5; 9.6.2.7(c); 9.6.3.10"
        if macro_test_used:
            clause = (
                "9.6.2.3(b)(i); 9.6.2.3(b)(iii); Figure 9.6.3.4; "
                "9.6.2.4; 9.6.2.5; 9.6.2.7(c); 9.6.3.10"
            )
        strength_check, strength_intermediate = _fillet_strength_check(
            weld_data, throat, length, clause
        )
        c["weld_strength"] = {"clause": clause, **strength_check}
        intermediate = {
            "preparation_type": "prequalified",
            "prequalified_design_throat_input_mm": d["prequalified_design_throat_mm"],
            "prequalified_preparation_verified": d["prequalified_preparation_verified"],
            "prequalified_preparation_reference": d["prequalified_preparation_reference"],
            "design_throat_mm": throat,
            "macro_test_throat_increase": {
                "used": macro_test_used,
                "automatic_arc_welding_process_verified": d.get(
                    "automatic_arc_welding_process_verified", False
                ),
                "production_weld_macro_test_verified": d.get(
                    "production_weld_macro_test_verified", False
                ),
                "required_penetration_achieved_verified": d.get(
                    "macro_test_required_penetration_achieved_verified", False
                ),
                "record_reference": d.get("macro_test_record_reference"),
                "preparation_depth_t_t1_mm": d.get("preparation_depth_mm"),
                "penetration_beyond_preparation_t_t2_mm": (
                    macro_test_extra_penetration if macro_test_used else None
                ),
                "maximum_design_throat_mm": macro_test_throat_limit,
            },
            "effective_length_mm": length,
            "effective_area_mm2": throat * length,
            **strength_intermediate,
        }
    elif k in {"fillet", "complete_butt", "plug_slot"}:
        phi = 0.8 if d["quality"] == "SP" else 0.6
        if k == "fillet":
            clause = "9.6.3.10; 9.6.2.7(c) for incomplete butt"
            c["weld"], intermediate = _fillet_strength_check(
                d, d["throat_mm"], d["effective_length_mm"], clause
            )
        elif k == "complete_butt":
            phi = 0.9 if d["quality"] == "SP" else 0.6
            capacity = d["weaker_part_nominal_capacity_kn"]
            clause = "9.6.2.7(a)"
        else:
            area_fields = {"hole_shape", "hole_diameter_mm", "slot_length_mm", "slot_width_mm"}
            supplied_geometry_fields = area_fields.intersection(d)
            geometry_used = bool(supplied_geometry_fields)
            if "effective_area_mm2" in d and (geometry_used or "hole_geometry_verified" in d):
                raise ValueError("Use either an assessed area or geometry, not both.")
            if geometry_used:
                if "hole_shape" not in d:
                    raise ValueError("Plug/slot geometry requires hole_shape.")
                if "hole_geometry_verified" not in d:
                    raise ValueError("Plug/slot geometry requires hole_geometry_verified.")
                expected_dimension_fields = (
                    {"hole_diameter_mm"}
                    if d["hole_shape"] == "circular"
                    else {"slot_length_mm", "slot_width_mm"}
                )
                supplied_dimension_fields = supplied_geometry_fields - {"hole_shape"}
                missing_dimension_fields = expected_dimension_fields - supplied_dimension_fields
                extra_dimension_fields = supplied_dimension_fields - expected_dimension_fields
                if missing_dimension_fields:
                    names = ", ".join(sorted(missing_dimension_fields))
                    raise ValueError(f"Plug/slot geometry is incomplete; provide {names}.")
                if extra_dimension_fields:
                    names = ", ".join(sorted(extra_dimension_fields))
                    raise ValueError(
                        f"Plug/slot geometry for {d['hole_shape']} must not include {names}."
                    )
                if d["hole_shape"] == "circular":
                    area = pi * d["hole_diameter_mm"] ** 2 / 4
                elif d["hole_shape"] == "round_ended_slot":
                    slot_length = d["slot_length_mm"]
                    slot_width = d["slot_width_mm"]
                    if slot_length < slot_width:
                        raise ValueError("A round-ended slot length cannot be less than its width.")
                    area = slot_width * (slot_length - slot_width) + pi * slot_width**2 / 4
                else:
                    area = d["slot_length_mm"] * d["slot_width_mm"]
                area_basis = "nominal_faying_plane_hole_geometry"
            elif "effective_area_mm2" in d and "hole_geometry_verified" not in d:
                area = d["effective_area_mm2"]
                area_basis = "externally_assessed_faying_plane_area"
            else:
                raise ValueError("Provide either effective_area_mm2 or verified hole geometry.")
            capacity = 0.6 * d["weld_strength_mpa"] * area / 1000
            clause = "9.6.4.2"
            c["application"] = {
                "clause": "9.6.4.3",
                "permitted_shear_application_verified": d["permitted_shear_application"],
                "satisfied": True,
            }
            intermediate = {
                "effective_area_mm2": area,
                "area_basis": area_basis,
                "hole_shape": d.get("hole_shape"),
                "hole_diameter_mm": d.get("hole_diameter_mm"),
                "slot_length_mm": d.get("slot_length_mm"),
                "slot_width_mm": d.get("slot_width_mm"),
            }
        if k != "fillet":
            c["weld"] = _check(capacity, phi, d["action_kn"], clause)
    elif k == "packing_construction":
        if len(d["required_edge_weld_sizes_mm"]) != len(d["provided_edge_weld_sizes_mm"]):
            raise ValueError("Provide one actual weld size for every required edge weld.")
        flush_required = (
            d["packing_thickness_mm"] < 6
            or d["too_thin_for_adequate_welds"]
            or d["too_thin_to_prevent_buckling"]
        )
        if flush_required:
            required_sizes = [
                size + d["packing_thickness_mm"] for size in d["required_edge_weld_sizes_mm"]
            ]
            c["trimmed_flush"] = {
                "required": True,
                "provided": d["trimmed_flush_with_member_edges"],
                "satisfied": d["trimmed_flush_with_member_edges"],
                "clause": "9.8",
            }
            c["edge_weld_sizes"] = {
                "required_mm": required_sizes,
                "provided_mm": d["provided_edge_weld_sizes_mm"],
                "satisfied": all(
                    provided >= required
                    for provided, required in zip(
                        d["provided_edge_weld_sizes_mm"], required_sizes, strict=True
                    )
                ),
                "clause": "9.8",
            }
            intermediate = {
                "flush_required": True,
                "edge_weld_size_increase_mm": d["packing_thickness_mm"],
            }
        else:
            c["extends_beyond_edges"] = {
                "required": True,
                "provided": d["extends_beyond_member_edges"],
                "satisfied": d["extends_beyond_member_edges"],
                "clause": "9.8",
            }
            c["welded_to_fitted_piece"] = {
                "required": True,
                "provided": d["welded_to_fitted_piece"],
                "satisfied": d["welded_to_fitted_piece"],
                "clause": "9.8",
            }
            intermediate = {"flush_required": False}
    elif k == "layout":
        dia, t = d["diameter_mm"], d["thinnest_ply_mm"]
        min_edge = {"sheared": 1.75, "machined": 1.5, "rolled": 1.25}[d["edge_type"]] * dia
        max_pitch = {
            "general": min(15 * t, 200),
            "outside_line": min(4 * t + 100, 200),
            "non_load_noncorrosive": min(32 * t, 300),
        }[d["pitch_case"]]
        c["pitch"] = {
            "satisfied": 2.5 * dia <= d["pitch_mm"] <= max_pitch,
            "clause": "9.5.1; 9.5.3",
        }
        c["edge"] = {
            "satisfied": min_edge <= d["edge_distance_mm"] <= min(12 * t, 150),
            "clause": "9.5.2; 9.5.4",
        }
        intermediate = {
            "minimum_pitch_mm": 2.5 * dia,
            "maximum_pitch_mm": max_pitch,
            "minimum_edge_mm": min_edge,
            "maximum_edge_mm": min(12 * t, 150),
        }
    elif k == "hole_deduction":
        correction = sum(s * s / (4 * g) for s, g in d["stagger_pairs"])
        deduction = d["thickness_mm"] * max(
            d["straight_hole_width_sum_mm"], d["zigzag_hole_width_sum_mm"] - correction
        )
        if deduction >= d["gross_area_mm2"]:
            raise ValueError("Hole deductions must leave positive net area.")
        intermediate = {"deduction_mm2": deduction, "net_area_mm2": d["gross_area_mm2"] - deduction}
        c["net_area"] = {"satisfied": True, "clause": "9.1.10"}
    elif k == "hole_deduction_layout":
        c, intermediate = _hole_deduction_layout(d)
    elif k == "angle_hole_deduction":
        c, intermediate = _angle_hole_deduction(d)
    elif k == "angle_hole_deduction_layout":
        c, intermediate = _angle_hole_deduction_layout(d)
    elif k == "combined_weld_types":
        c, intermediate = _combined_weld_types(d)
    else:
        c, intermediate = _weld_group(d)
    if k == "slip_factor_test":
        scope = (
            "Appendix J.1–J.5 slip-factor calculation from two bolt-position results per "
            "specimen, including the Table 15.2.2.2 minimum bolt tension and, where selected, "
            "Equation J.1. The declared specimen, calibration, instrumentation and test-procedure "
            "evidence is not authenticated; laboratory compliance and surface classification "
            "remain subject to engineering review."
        )
    elif k == "incomplete_butt_design":
        scope = (
            "Clause 9.6.2.3(b)(ii)(A)–(B) throat formulas for non-prequalified single-V and "
            "double-V welds on either side of the 60-degree preparation-angle threshold; effective "
            "length and area under 9.6.2.4–5; strength "
            "under 9.6.2.7(c)/9.6.3.10. The supplied preparation classification, dimensions, "
            "welding procedure, consumable strength, quality and any thin-RHS condition require "
            "project evidence. Optional Clause 9.6.2.3(b)(iii)/Figure 9.6.3.4 throat increases "
            "require verified automatic arc welding and a production-weld macro-test record; "
            "the declared evidence is not authenticated. "
            "Prequalified preparations, other preparation forms, fatigue quality, inspection and "
            "complete connection "
            "design are outside this operation."
        )
    elif k == "prequalified_incomplete_butt_design":
        scope = (
            "Clause 9.6.2.3(b)(i) accepts a design throat established for a prequalified "
            "preparation under AS/NZS 1554.1 or AS/NZS 1554.4; this operation calculates the "
            "effective length and area under 9.6.2.4–5 and capacity under 9.6.2.7(c)/9.6.3.10. "
            "The preparation, throat, welding procedure, consumable strength, quality, inspection "
            "and referenced-standard evidence are externally assessed and not authenticated. "
            "Optional Clause 9.6.2.3(b)(iii)/Figure 9.6.3.4 throat increases require automatic arc "
            "process verification and a production-weld macro-test record. Fatigue quality and "
            "complete connection design remain separate."
        )
    elif k == "butt_weld_transition":
        scope = (
            "Clause 9.6.2.6 transition slope for a tension-loaded butt joint with a verified "
            "thickness or width change. Smoothness and the measured geometry are declared inputs. "
            "Any stricter fatigue-detail slope must be assessed externally and supplied with its "
            "reference; classification and evidence are not authenticated."
        )
    elif k == "fillet_design":
        scope = (
            "Selected Clause 9.6.3.1–10 fillet-weld geometry, detailing and strength checks. "
            "Optional Clause 9.6.3.4 throat increases require verified automatic arc welding and "
            "a production-weld macro-test record; declarations and measured penetration are not "
            "authenticated. Fatigue quality and complete connection design remain separate."
        )
    elif k == "plug_slot":
        scope = (
            "Clause 9.6.4.2 effective shear area and nominal capacity for a filled plug/slot weld. "
            "Area is calculated from verified circular, round-ended slot or rectangular slot "
            "geometry, or supplied as an externally assessed faying-plane area. Clause 9.6.4.3 "
            "limits use to shear transfer in lap joints, preventing buckling of lapped parts, or "
            "joining built-up-member components. Geometry and application declarations are not "
            "authenticated."
        )
    elif k in MINIMUM_ACTION_CHECKS:
        scope = (
            "Clause 9.1.4 required action effects only; check that the connection is not "
            "lacing or to a sag rod, purlin or girt. For a compression splice between lateral "
            "supports, the moment is based conservatively on the greater of the actual axial "
            "action and the minimum splice axial action. The supplied amplification factor "
            "must be selected under Clause 4.4, and supplied connection capacities already "
            "include their capacity factor. Component resistance, action interaction, "
            "earthquake increases, detailing, fabrication, prying and local effects require "
            "separate assessment."
        )
        if k == "minimum_beam_shear_action":
            if "clause_9_1_2_3_eccentricity_moment_vector_knm" in intermediate:
                scope = (
                    "Clauses 9.1.4(b)(ii) and 9.1.2.3 required shear and its eccentric moment "
                    "from supplied direction and geometry; separately verify connection strength, "
                    "local components, installation and detailing."
                )
            else:
                scope = (
                    "Clause 9.1.4(b)(ii) minimum shear only. Supply the assessed reaction-shear "
                    "direction and connection eccentricity under Clause 9.1.2.3 to calculate its "
                    "moment; separately verify connection strength, local components, installation "
                    "and detailing."
                )
    elif k == "joint_eccentricity_action":
        scope = (
            "Clause 9.1.5 signed eccentric moments only; verify axis convergence where "
            "practicable and supply the complete force and eccentricity vectors. For fatigue-"
            "loaded angle details, assess weld balancing and bolt gauge-line eccentricity from "
            "the actual connection geometry. Member and component resistance checks remain "
            "separate."
        )
    elif k == "fastener_selection_suitability":
        scope = (
            "Clause 9.1.6 fastener selection conditions only; verify serviceability, impact "
            "and vibration requirements for the actual joint. Clause 9.1.7 load-sharing rules "
            "and fastener resistance remain separate."
        )
    elif k == "combined_connection_action_assignment":
        scope = (
            "Clause 9.1.7 action allocation only. Non-slip shares are explicit design inputs; "
            "slip-type groups receive no assigned action in the mixed case. Weld-stage actions "
            "are allocated to the aggregate weld group under the declared installation sequence. "
            "Verify the sequence and design resistance, interaction and detailing of every "
            "connection component separately."
        )
    elif k == "bolt_group_elastic_3d":
        scope = (
            "Clauses 9.1.3(a) and 9.3.2–3 use a rigid-plate, equal-bolt-stiffness elastic "
            "distribution for a planar bolt group. The action origin, experimental basis, "
            "stiffness assumptions, connection deformation capacity and stability must be "
            "verified from project evidence. Cases with a calculated compressive bolt action "
            "are rejected; compression/contact, slack-bolt redistribution and ply bearing need "
            "separate assessment."
        )
    elif k == "bolt_group_out_of_plane":
        scope = (
            "Clauses 9.3.2 and 9.3.3 check only the supplied per-bolt force distribution, "
            "resultant equilibrium, bolt shear/tension interaction and externally assessed "
            "prying. Determine bolt actions under Clause 9.1.3 and verify connection-element "
            "deformation, stability, and each ply's Clause 9.2.2.4 bearing resistance separately."
            " Compression/contact reactions are outside this bolt-only operation."
        )
    elif k == "bolt":
        scope = (
            "Bolt tension includes the supplied Clause 9.1.8 prying force, assessed using a "
            "recognized method supported by experimental evidence. This operation does not "
            "calculate prying force; verify eccentricity, plate flexibility and connection "
            "geometry separately."
        )
    elif k == "block_shear_paths":
        scope = (
            "Clause 9.1.9(e) block-shear resistance for the supplied rupture-path set. "
            "The engineer must enumerate every feasible path and verify gross/net path lengths, "
            "including fastener-hole deductions under Clause 9.1.10. This operation does not "
            "derive rupture paths or hole geometry."
        )
    elif k == "hole_deduction_layout":
        scope = (
            "Clause 9.1.10.1–3 governing gross-hole deduction for a complete, uniform-thickness "
            "flat-plate layout. The operation searches all exact straight hole rows and all "
            "progressively ordered zig-zag hole paths, applying the stagger correction to each "
            "successive pair. Verify the plate/action axes, hole dimensions, coordinates and "
            "completeness of the layout. Angle sections with holes in both legs, other section "
            "geometries, net-section modulus calculations and block-shear rupture paths require "
            "separate assessment."
        )
    elif k == "angle_hole_deduction":
        scope = (
            "Clause 9.1.10.1–3 compares the supplied straight-row hole-width sum with each "
            "supplied ordered zig-zag path. For consecutive holes in opposite angle legs, the "
            "gauge is calculated from the Figure 9.1.10.3(B) back marks less the common leg "
            "thickness; holes in one leg use their back-mark difference. Verify the complete "
            "straight and zig-zag candidate sets, hole widths, back marks and path order. The "
            "operation does not derive angle geometry, enumerate paths, or calculate member "
            "capacity."
        )
    elif k == "angle_hole_deduction_layout":
        scope = (
            "Clause 9.1.10.1–3 for a verified complete two-leg angle hole layout. It groups "
            "exact longitudinal rows for the straight deduction and uses dynamic programming "
            "over every positive-gauge forward hole transition to find the greatest progressive "
            "zig-zag deduction. Same-leg gauges use back-mark differences; opposite-leg gauges "
            "use the Figure 9.1.10.3(B) sum of back marks less leg thickness. Verify the angle, "
            "all holes, dimensions, axes and coordinates. Other section forms, nonstandard angle "
            "geometries and member-capacity calculations are outside this operation."
        )
    elif k == "combined_weld_types":
        scope = (
            "Clause 9.7.4 sums the supplied design capacities of different weld types in one "
            "connection and compares their total with the stated design action. Each capacity "
            "must already be calculated under the applicable Section 9 weld provisions and "
            "include its capacity factor. Verify the complete, non-overlapping weld component "
            "set and that every capacity applies to the same action basis and direction. This "
            "operation does not calculate individual weld capacities or resolve different "
            "actions among weld types."
        )
    else:
        scope = (
            "Selected connection component checks; detailing, fabrication, prying, local "
            "effects and complete connection compliance require separate assessment."
        )
    result = {
        "standard": "AS 4100:2020",
        "check_type": k,
        "checks": c,
        "intermediate": intermediate,
        "scope": scope,
    }
    if not _finite(result):
        raise ValueError("Calculated results must be finite.")
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result


def _weld_group(d):
    segments = d["segments_mm"]
    lengths = [hypot(b[0] - a[0], b[1] - a[1]) for a, b in segments]
    if any(length == 0 for length in lengths):
        raise ValueError("Weld segments must have positive length.")
    for i, (a, b) in enumerate(segments):
        dx, dy = b[0] - a[0], b[1] - a[1]
        denominator = dx * dx + dy * dy
        for c, e in segments[i + 1 :]:
            cross_c = dx * (c[1] - a[1]) - dy * (c[0] - a[0])
            cross_e = dx * (e[1] - a[1]) - dy * (e[0] - a[0])
            if abs(cross_c) <= 1e-12 * denominator and abs(cross_e) <= 1e-12 * denominator:
                tc = ((c[0] - a[0]) * dx + (c[1] - a[1]) * dy) / denominator
                te = ((e[0] - a[0]) * dx + (e[1] - a[1]) * dy) / denominator
                if min(1, max(tc, te)) > max(0, min(tc, te)):
                    raise ValueError("Weld segments must not overlap or repeat.")
    total = sum(lengths)
    cx, cy = (
        sum(length * (a[i] + b[i]) / 2 for (a, b), length in zip(segments, lengths, strict=True))
        / total
        for i in (0, 1)
    )
    ix = iy = ixy = 0
    for (a, b), length in zip(segments, lengths, strict=True):
        x1, y1, x2, y2 = a[0] - cx, a[1] - cy, b[0] - cx, b[1] - cy
        ix += length * (y1 * y1 + y1 * y2 + y2 * y2) / 3
        iy += length * (x1 * x1 + x1 * x2 + x2 * x2) / 3
        ixy += length * (2 * x1 * y1 + x1 * y2 + x2 * y1 + 2 * x2 * y2) / 6
    determinant = ix * iy - ixy * ixy
    mx, my, mz = (d[f"moment_{a}_knm"] * 1000 for a in "xyz")
    if (mx or my) and determinant <= 1e-12 * max(ix * iy, 1):
        raise ValueError("Weld geometry cannot support both-axis out-of-plane moment analysis.")
    aa = (-my * ix - mx * ixy) / determinant if mx or my else 0
    bb = (mx * iy + my * ixy) / determinant if mx or my else 0
    j = ix + iy
    if mz and j <= 0:
        raise ValueError("Weld polar inertia must be positive.")
    forces = []
    for a, b in segments:
        for x, y in (a, b):
            x, y = x - cx, y - cy
            forces.append(
                [
                    d["force_x_kn"] / total - mz * y / j,
                    d["force_y_kn"] / total + mz * x / j,
                    d["force_z_kn"] / total + aa * x + bb * y,
                ]
            )
    action = max(hypot(*f) for f in forces)
    phi = 0.8 if d["quality"] == "SP" else 0.6
    capacity = 0.6 * d["weld_strength_mpa"] * d["throat_mm"] / 1000
    return {
        "weld_group": _check(capacity, phi, action, "9.7.1.1; 9.7.2.1; 9.7.3.1", "kn_per_mm")
    }, {
        "centroid_mm": [cx, cy],
        "length_mm": total,
        "ix_mm3": ix,
        "iy_mm3": iy,
        "ixy_mm3": ixy,
        "endpoint_forces_kn_per_mm": forces,
    }
