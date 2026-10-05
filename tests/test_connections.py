"""Independent numeric benchmarks and connection domain boundaries."""

from math import pi

import pytest

from opencalcs_as4100.connections import run_connections


def bolt(**changes):
    return {
        "check_type": "bolt",
        "ultimate_strength_mpa": 830,
        "minor_area_mm2": 225,
        "shank_area_mm2": 314,
        "tensile_area_mm2": 245,
        "threaded_planes": 1,
        "plain_planes": 0,
        "grade": "8.8",
        "lap_length_mm": 0,
        "filler_thickness_mm": 0,
        "shear_action_kn": 50,
        "tension_action_kn": 80,
        "prying_tension_kn": 0,
        "prying_force_assessment_verified": True,
        **changes,
    }


def simple_beam_shear(**changes):
    return {
        "check_type": "minimum_beam_shear_action",
        "actual_design_shear_kn": 10,
        "member_design_shear_capacity_kn": 200,
        "simple_construction_beam_connection_verified": True,
        "excluded_connection_arrangement_absent_verified": True,
        **changes,
    }


def combined_connection(**changes):
    return {
        "check_type": "combined_connection_action_assignment",
        "component_groups": [
            {"group_id": "friction-bolts", "fastener_class": "non_slip"},
            {"group_id": "snug-bolts", "fastener_class": "slip_type"},
            {"group_id": "fitted-bolts", "fastener_class": "non_slip"},
        ],
        "load_cases": [
            {
                "case_id": "service-load",
                "stage": "non_weld_action",
                "actions": {
                    "axial_kn": 0,
                    "shear_x_kn": 0,
                    "shear_y_kn": 100,
                    "moment_x_knm": 0,
                    "moment_y_knm": 0,
                    "moment_z_knm": 25,
                },
                "shares": [
                    {"group_id": "friction-bolts", "fraction": 0.6},
                    {"group_id": "fitted-bolts", "fraction": 0.4},
                ],
            }
        ],
        "installation_sequence_assessed_verified": True,
        **changes,
    }


def appendix_j_slip_test(estimates=(0.35, 0.36, 0.40, 0.41, 0.45, 0.46)):
    def loading_increments(bolts):
        predicted_slip_kn = min(0.7 * bolt["calibrated_bolt_tension_kn"] for bolt in bolts)
        increment_limit_kn = min(25.0, 0.25 * predicted_slip_kn)
        final_load_kn = max(bolt["slip_load_kn"] for bolt in bolts)
        increments = []
        load_kn = 0.0
        while load_kn < final_load_kn - 1e-9:
            next_load_kn = min(load_kn + increment_limit_kn, final_load_kn)
            increment = {
                "load_before_kn": load_kn,
                "load_after_kn": next_load_kn,
                "maximum_rate_kn_per_min": 40,
                "loading_rate_approximately_uniform_verified": True,
            }
            if increments:
                increment["preceding_load_creep_effectively_ceased_verified"] = True
            increments.append(increment)
            load_kn = next_load_kn
        return increments

    specimens = []
    for i in range(0, len(estimates), 2):
        bolts = [
            {
                "bolt_id": f"B{j + 1}",
                "slip_load_kn": 200 * estimates[j],
                "slip_load_method": "clear_observed_slip",
                "bolt_extension_mm": 0.1,
                "calibrated_bolt_tension_kn": 100,
            }
            for j in (i, i + 1)
        ]
        specimens.append(
            {
                "specimen_id": f"S{i // 2 + 1}",
                "bolts": bolts,
                "loading_increments": loading_increments(bolts),
            }
        )
    return {
        "check_type": "slip_factor_test",
        "nominal_bolt_diameter_mm": 16,
        "bolt_grade": "8.8",
        "bolt_tension_method": "calibration_curve",
        "symmetrical_double_cover_butt_specimen_verified": True,
        "bolts_clear_of_bearing_in_loading_direction_verified": True,
        "specimen_geometry": {
            "bolt_centre_spacing_mm": 96,
            "left_bolt_to_test_section_end_mm": 32,
            "right_bolt_to_test_section_end_mm": 32,
            "upper_bolt_edge_distance_mm": 48,
            "lower_bolt_edge_distance_mm": 48,
            "inner_plate_thicknesses_mm": [21, 21],
            "cover_plate_thicknesses_mm": [10, 10],
            "cover_plate_hole_diameter_mm": 18,
            "inner_plate_hole_diameter_mm": 19,
            "butt_gap_mm": 8,
        },
        "friction_surface_condition_matches_field_verified": True,
        "machining_oil_contamination_absent_if_used_verified": True,
        "specimen_bolt_tensioning_matches_field_verified": True,
        "initial_snug_condition_finger_tight_verified": True,
        "extension_measurement_immediately_before_test_verified": True,
        "extension_instrument_resolution_mm": 0.003,
        "instrumentation_layout_per_appendix_j_verified": True,
        "instrumentation_deformation_reduction_per_appendix_j_verified": True,
        "tensile_loading_only_verified": True,
        "slip_load_identification_per_appendix_j_verified": True,
        "appendix_j_test_report_reference": "LAB-SLIP-001",
        "calibration_test_bolt_count": 3,
        "calibration_curve_reference": "CAL-CURVE-001",
        "calibration_test_bolts_from_test_batch_verified": True,
        "calibration_grip_and_measurement_method_match_verified": True,
        "calibration_curve_based_on_mean_result_verified": True,
        "specimens": specimens,
    }


def bolt_group_out_of_plane(**changes):
    return {
        "check_type": "bolt_group_out_of_plane",
        "ultimate_strength_mpa": 830,
        "minor_area_mm2": 225,
        "shank_area_mm2": 314,
        "tensile_area_mm2": 245,
        "threaded_planes": 1,
        "plain_planes": 0,
        "grade": "8.8",
        "lap_length_mm": 0,
        "filler_thickness_mm": 0,
        "bolt_actions": [
            {
                "bolt_id": "B1",
                "position_mm": [50, 0],
                "shear_x_kn": 20,
                "shear_y_kn": 0,
                "tension_action_kn": 80,
                "prying_tension_kn": 5,
                "prying_force_assessment_verified": True,
            },
            {
                "bolt_id": "B2",
                "position_mm": [-50, 0],
                "shear_x_kn": 20,
                "shear_y_kn": 0,
                "tension_action_kn": 20,
                "prying_tension_kn": 0,
                "prying_force_assessment_verified": True,
            },
        ],
        "group_force_x_kn": 40,
        "group_force_y_kn": 0,
        "group_tension_kn": 100,
        "group_moment_x_knm": 0,
        "group_moment_y_knm": -3,
        "group_moment_z_knm": 0,
        "positions_share_action_reference_verified": True,
        "bolt_action_distribution_assessed_under_clause_9_1_3": True,
        "connection_element_deformation_capacity_and_stability_verified": True,
        **changes,
    }


def bolt_group_elastic_3d(**changes):
    return {
        "check_type": "bolt_group_elastic_3d",
        "ultimate_strength_mpa": 830,
        "minor_area_mm2": 225,
        "shank_area_mm2": 314,
        "tensile_area_mm2": 245,
        "threaded_planes": 1,
        "plain_planes": 0,
        "grade": "8.8",
        "lap_length_mm": 0,
        "filler_thickness_mm": 0,
        "bolt_layout": [
            {
                "bolt_id": "B1",
                "position_mm": [50, 25],
                "prying_tension_kn": 1,
                "prying_force_assessment_verified": True,
            },
            {
                "bolt_id": "B2",
                "position_mm": [50, -25],
                "prying_tension_kn": 0,
                "prying_force_assessment_verified": True,
            },
            {
                "bolt_id": "B3",
                "position_mm": [-50, 25],
                "prying_tension_kn": 0,
                "prying_force_assessment_verified": True,
            },
            {
                "bolt_id": "B4",
                "position_mm": [-50, -25],
                "prying_tension_kn": 2,
                "prying_force_assessment_verified": True,
            },
        ],
        "group_force_x_kn": 40,
        "group_force_y_kn": 20,
        "group_tension_kn": 120,
        "group_moment_x_knm": 2,
        "group_moment_y_knm": 1,
        "group_moment_z_knm": 3,
        "group_actions_at_centroid_verified": True,
        "rigid_plates_and_equal_bolt_stiffness_verified": True,
        "elastic_method_experimental_basis_verified": True,
        "connection_element_deformation_capacity_and_stability_verified": True,
        **changes,
    }


@pytest.mark.parametrize(
    "actual_shear,member_capacity,expected_minimum,expected_action",
    [
        (10, 200, 30, 30),
        (10, 400, 40, 40),
        (60, 400, 40, 60),
        (0, 800 / 3, 40, 40),
    ],
)
def test_clause_9_1_4_b_ii_minimum_simple_beam_shear_hand_arithmetic(
    actual_shear, member_capacity, expected_minimum, expected_action
):
    result = run_connections(
        simple_beam_shear(
            actual_design_shear_kn=actual_shear,
            member_design_shear_capacity_kn=member_capacity,
        )
    )
    assert result["intermediate"]["minimum_design_shear_kn"] == pytest.approx(expected_minimum)
    assert result["intermediate"]["required_design_shear_kn"] == pytest.approx(expected_action)
    assert result["intermediate"]["governing_action"] == (
        "actual_design_shear" if actual_shear >= expected_minimum else "minimum_design_shear"
    )
    assert result["intermediate"]["member_capacity_includes_capacity_factor"]
    assert result["checks"] == {}


def test_clause_9_1_2_3_simple_beam_reaction_moment_from_eccentricity():
    result = run_connections(
        simple_beam_shear(
            reaction_shear_direction_unit_vector=[0, 1, 0],
            reaction_shear_eccentricity_vector_mm=[40, 0, 0],
            reaction_shear_eccentricity_assessment_verified=True,
        )
    )
    assert result["intermediate"]["required_design_shear_kn"] == 30
    assert result["intermediate"]["clause_9_1_2_3_reaction_shear_vector_kn"] == [0, 30, 0]
    assert result["intermediate"]["clause_9_1_2_3_eccentricity_moment_vector_knm"] == [
        0,
        0,
        1.2,
    ]
    assert "9.1.2.3" in result["scope"]


def test_clause_9_1_2_3_requires_complete_geometry_and_unit_direction():
    with pytest.raises(ValueError, match="(?i)provide the shear direction"):
        run_connections(simple_beam_shear(reaction_shear_direction_unit_vector=[0, 1, 0]))
    with pytest.raises(ValueError, match="unit vector"):
        run_connections(
            simple_beam_shear(
                reaction_shear_direction_unit_vector=[0, 2, 0],
                reaction_shear_eccentricity_vector_mm=[40, 0, 0],
                reaction_shear_eccentricity_assessment_verified=True,
            )
        )


@pytest.mark.parametrize("connection_capacity,expected_satisfied", [(29.9, False), (30, True)])
def test_clause_9_1_4_connection_design_shear_capacity_boundary(
    connection_capacity, expected_satisfied
):
    result = run_connections(
        simple_beam_shear(connection_design_shear_capacity_kn=connection_capacity)
    )
    check = result["checks"]["connection_shear_capacity"]
    assert check["design_action_kn"] == 30
    assert check["design_capacity_kn"] == connection_capacity
    assert check["satisfied"] is expected_satisfied


def test_clause_9_1_4_requires_scope_and_exclusion_confirmations():
    data = simple_beam_shear(simple_construction_beam_connection_verified=False)
    with pytest.raises(ValueError):
        run_connections(data)

    data = simple_beam_shear(excluded_connection_arrangement_absent_verified=False)
    with pytest.raises(ValueError):
        run_connections(data)

    with pytest.raises(ValueError):
        run_connections(simple_beam_shear(member_design_shear_capacity_kn=0))


def test_clause_9_1_4_b_i_rigid_connection_minimum_moment():
    result = run_connections(
        {
            "check_type": "minimum_rigid_connection_action",
            "rigid_construction_connection_verified": True,
            "actual_design_moment_knm": 25,
            "member_design_moment_capacity_knm": 100,
            "excluded_connection_arrangement_absent_verified": True,
            "connection_design_moment_capacity_knm": 49.9,
        }
    )
    assert result["intermediate"]["minimum_design_moment_knm"] == 50
    assert result["intermediate"]["required_design_moment_knm"] == 50
    assert not result["checks"]["connection_moment_capacity"]["satisfied"]


@pytest.mark.parametrize(
    "case,turnbuckle,action,capacity,expected",
    [
        ("tension_member_end", False, 10, 200, 60),
        ("compression_member_end", False, 80, 200, 80),
        ("threaded_tension_bracing_with_turnbuckles", True, 10, 200, 200),
    ],
)
def test_clause_9_1_4_b_iii_member_end_minimum_actions(
    case, turnbuckle, action, capacity, expected
):
    result = run_connections(
        {
            "check_type": "minimum_member_end_action",
            "connection_at_member_end_verified": True,
            "member_end_case": case,
            "actual_design_axial_action_kn": action,
            "member_design_axial_capacity_kn": capacity,
            "threaded_bracing_turnbuckle_arrangement_verified": turnbuckle,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    assert result["intermediate"]["required_design_axial_action_kn"] == expected


@pytest.mark.parametrize(
    "case,full_contact,action,capacity,expected",
    [
        ("axial_tension", False, 50, 200, 60),
        ("compression_full_contact", True, 10, 200, 30),
        ("compression_not_full_contact", False, 80, 200, 80),
    ],
)
def test_clause_9_1_4_b_iv_v_axial_splice_minimum_actions(
    case, full_contact, action, capacity, expected
):
    result = run_connections(
        {
            "check_type": "minimum_axial_splice_action",
            "axial_member_splice_verified": True,
            "splice_case": case,
            "actual_design_axial_action_kn": action,
            "member_design_axial_capacity_kn": capacity,
            "full_contact_bearing_verified": full_contact,
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": True,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    assert result["intermediate"]["required_design_axial_action_kn"] == expected


def test_clause_9_1_4_b_v_compression_splice_between_lateral_supports():
    result = run_connections(
        {
            "check_type": "minimum_compression_splice_between_supports",
            "compression_member_splice_verified": True,
            "actual_design_axial_action_kn": 50,
            "actual_design_moment_knm": 200,
            "member_design_axial_capacity_kn": 400,
            "full_contact_bearing_verified": True,
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": True,
            "splice_between_effective_lateral_supports_verified": True,
            "effective_lateral_support_distance_mm": 3000,
            "amplification_factor_type": "delta_s",
            "amplification_factor": 1.5,
            "amplification_factor_verified": True,
            "excluded_connection_arrangement_absent_verified": True,
            "connection_design_axial_capacity_kn": 60,
            "connection_design_moment_capacity_knm": 270,
        }
    )
    assert result["intermediate"]["minimum_design_axial_action_kn"] == 60
    assert result["intermediate"]["moment_basis_axial_action_kn"] == 60
    assert result["intermediate"]["minimum_design_moment_knm"] == 270
    assert result["intermediate"]["required_design_moment_knm"] == 270
    assert result["checks"]["connection_axial_capacity"]["satisfied"]
    assert result["checks"]["connection_moment_capacity"]["satisfied"]


def test_clause_9_1_4_b_vi_flexural_splice_minimum_moment():
    result = run_connections(
        {
            "check_type": "minimum_flexural_splice_action",
            "flexural_splice_not_shear_only_verified": True,
            "actual_design_moment_knm": 20,
            "member_design_moment_capacity_knm": 200,
            "excluded_connection_arrangement_absent_verified": True,
            "connection_design_moment_capacity_knm": 59,
        }
    )
    assert result["intermediate"]["required_design_moment_knm"] == 60
    assert not result["checks"]["connection_moment_capacity"]["satisfied"]


def test_clause_9_1_4_b_vi_shear_only_splice_eccentric_moment():
    result = run_connections(
        {
            "check_type": "shear_only_splice_eccentric_action",
            "actual_design_shear_kn": 50,
            "force_eccentricity_mm": 100,
            "shear_only_splice_verified": True,
            "excluded_connection_arrangement_absent_verified": True,
            "connection_design_shear_capacity_kn": 50,
            "connection_design_moment_capacity_knm": 5,
        }
    )
    assert result["intermediate"]["required_design_shear_kn"] == 50
    assert result["intermediate"]["required_design_moment_knm"] == 5
    assert result["checks"]["connection_shear_capacity"]["satisfied"]
    assert result["checks"]["connection_moment_capacity"]["satisfied"]


def test_clause_9_1_4_b_vii_combined_tension_and_bending_splice_actions():
    result = run_connections(
        {
            "check_type": "minimum_combined_splice_actions",
            "combined_axial_bending_splice_verified": True,
            "splice_case": "axial_tension",
            "actual_design_axial_action_kn": 20,
            "member_design_axial_capacity_kn": 200,
            "full_contact_bearing_verified": False,
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": True,
            "actual_design_moment_knm": 20,
            "member_design_moment_capacity_knm": 200,
            "splice_between_effective_lateral_supports_verified": False,
            "excluded_connection_arrangement_absent_verified": True,
            "connection_design_axial_capacity_kn": 60,
            "connection_design_moment_capacity_knm": 60,
        }
    )
    assert result["intermediate"]["required_design_axial_action_kn"] == 60
    assert result["intermediate"]["required_design_moment_knm"] == 60
    assert result["checks"]["connection_axial_capacity"]["satisfied"]
    assert result["checks"]["connection_moment_capacity"]["satisfied"]


def test_clause_9_1_4_b_vii_combined_compression_splice_in_support_span():
    result = run_connections(
        {
            "check_type": "minimum_combined_splice_actions",
            "combined_axial_bending_splice_verified": True,
            "splice_case": "compression_not_full_contact",
            "actual_design_axial_action_kn": 50,
            "member_design_axial_capacity_kn": 400,
            "full_contact_bearing_verified": False,
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": True,
            "actual_design_moment_knm": 100,
            "member_design_moment_capacity_knm": 500,
            "splice_between_effective_lateral_supports_verified": True,
            "effective_lateral_support_distance_mm": 3000,
            "amplification_factor_type": "delta_s",
            "amplification_factor": 1.5,
            "amplification_factor_verified": True,
            "excluded_connection_arrangement_absent_verified": True,
            "connection_design_axial_capacity_kn": 120,
            "connection_design_moment_capacity_knm": 539.9,
        }
    )
    assert result["intermediate"]["required_design_axial_action_kn"] == 120
    assert result["intermediate"]["minimum_flexural_splice_moment_knm"] == 150
    assert result["intermediate"]["minimum_between_supports_moment_knm"] == 540
    assert result["intermediate"]["required_design_moment_knm"] == 540
    assert result["checks"]["connection_axial_capacity"]["satisfied"]
    assert not result["checks"]["connection_moment_capacity"]["satisfied"]


def test_clause_9_1_4_rejects_unverified_case_and_full_contact_mismatch():
    with pytest.raises(ValueError):
        run_connections(
            {
                "check_type": "minimum_rigid_connection_action",
                "rigid_construction_connection_verified": False,
                "actual_design_moment_knm": 0,
                "member_design_moment_capacity_knm": 100,
                "excluded_connection_arrangement_absent_verified": True,
            }
        )

    with pytest.raises(ValueError, match="full-contact"):
        run_connections(
            {
                "check_type": "minimum_axial_splice_action",
                "axial_member_splice_verified": True,
                "splice_case": "compression_full_contact",
                "actual_design_axial_action_kn": 0,
                "member_design_axial_capacity_kn": 100,
                "full_contact_bearing_verified": False,
                "splice_parts_and_fasteners_hold_all_parts_in_line_verified": False,
                "excluded_connection_arrangement_absent_verified": True,
            }
        )

    with pytest.raises(ValueError, match="hold all parts in line"):
        run_connections(
            {
                "check_type": "minimum_axial_splice_action",
                "axial_member_splice_verified": True,
                "splice_case": "compression_not_full_contact",
                "actual_design_axial_action_kn": 0,
                "member_design_axial_capacity_kn": 100,
                "full_contact_bearing_verified": False,
                "splice_parts_and_fasteners_hold_all_parts_in_line_verified": False,
                "excluded_connection_arrangement_absent_verified": True,
            }
        )

    with pytest.raises(ValueError, match="hold all parts in line"):
        run_connections(
            {
                "check_type": "minimum_combined_splice_actions",
                "combined_axial_bending_splice_verified": True,
                "splice_case": "compression_not_full_contact",
                "actual_design_axial_action_kn": 0,
                "member_design_axial_capacity_kn": 100,
                "full_contact_bearing_verified": False,
                "splice_parts_and_fasteners_hold_all_parts_in_line_verified": False,
                "actual_design_moment_knm": 0,
                "member_design_moment_capacity_knm": 100,
                "splice_between_effective_lateral_supports_verified": False,
                "excluded_connection_arrangement_absent_verified": True,
            }
        )

    with pytest.raises(ValueError, match="requires its verified span"):
        run_connections(
            {
                "check_type": "minimum_combined_splice_actions",
                "combined_axial_bending_splice_verified": True,
                "splice_case": "compression_full_contact",
                "actual_design_axial_action_kn": 0,
                "member_design_axial_capacity_kn": 100,
                "full_contact_bearing_verified": True,
                "splice_parts_and_fasteners_hold_all_parts_in_line_verified": True,
                "actual_design_moment_knm": 0,
                "member_design_moment_capacity_knm": 100,
                "splice_between_effective_lateral_supports_verified": True,
                "excluded_connection_arrangement_absent_verified": True,
            }
        )


def test_bolt_hand_benchmark():
    r = run_connections(bolt())
    # 0.8 * 0.62 * 830 * 225 / 1000 = 92.628 kN
    assert r["checks"]["shear"]["design_capacity_kn"] == pytest.approx(92.628)
    assert r["checks"]["tension"]["design_capacity_kn"] == pytest.approx(162.68)
    assert r["checks"]["interaction"]["utilisation"] == pytest.approx(
        (50 / 92.628) ** 2 + (80 / 162.68) ** 2
    )


def test_clause_9_1_8_prying_tension_is_added_to_bolt_tension_action():
    result = run_connections(bolt(shear_action_kn=0, tension_action_kn=40, prying_tension_kn=15))
    assert result["intermediate"]["member_tension_action_kn"] == 40
    assert result["intermediate"]["prying_tension_action_kn"] == 15
    assert result["intermediate"]["total_bolt_tension_action_kn"] == 55
    assert result["checks"]["tension"]["clause"] == "9.1.8; 9.2.2.2"


def test_clause_9_1_5_joint_eccentricity_moment_vector_hand_arithmetic():
    result = run_connections(
        {
            "check_type": "joint_eccentricity_action",
            "connection_detail_case": "general",
            "fatigue_loading": False,
            "fatigue_detail_eccentricity_assessment_verified": False,
            "centroidal_axes_meet_practicable_verified": False,
            "centroidal_axes_meet_at_joint_verified": False,
            "force_kn": [5, 2, 1],
            "eccentricity_vector_mm": [10, 20, 30],
            "joint_geometry_and_load_line_assessed_verified": True,
        }
    )
    assert result["intermediate"]["eccentricity_moment_vector_knm"] == pytest.approx(
        [-0.04, 0.14, -0.08]
    )


@pytest.mark.parametrize(
    "system,avoid_slip,impact_or_vibration,expected",
    [
        ("friction_type_8_8_TF", True, True, True),
        ("fitted_bolt", True, False, True),
        ("locking_device", False, True, True),
        ("fitted_bolt", False, True, False),
        ("ordinary_bolt", False, False, True),
    ],
)
def test_clause_9_1_6_fastener_selection_conditions(
    system, avoid_slip, impact_or_vibration, expected
):
    result = run_connections(
        {
            "check_type": "fastener_selection_suitability",
            "selected_fastener_system": system,
            "serviceability_slip_to_be_avoided": avoid_slip,
            "impact_or_vibration_present": impact_or_vibration,
            "service_and_dynamic_action_assessment_verified": True,
        }
    )
    assert result["checks"]["fastener_selection"]["satisfied"] is expected


def test_clause_9_1_5_rejects_practicable_axis_offset_and_unassessed_fatigue_angle():
    base = {
        "check_type": "joint_eccentricity_action",
        "connection_detail_case": "general",
        "fatigue_loading": False,
        "fatigue_detail_eccentricity_assessment_verified": False,
        "centroidal_axes_meet_practicable_verified": True,
        "centroidal_axes_meet_at_joint_verified": False,
        "force_kn": [0, 10, 0],
        "eccentricity_vector_mm": [25, 0, 0],
        "joint_geometry_and_load_line_assessed_verified": True,
    }
    with pytest.raises(ValueError, match="when that is practicable"):
        run_connections(base)

    base.update(
        connection_detail_case="single_angle_welded_end",
        centroidal_axes_meet_practicable_verified=False,
        fatigue_loading=True,
    )
    with pytest.raises(ValueError, match="(?i)fatigue-loaded angle"):
        run_connections(base)


def test_bolt_prying_assessment_must_be_verified_and_group_must_remain_in_plane():
    with pytest.raises(ValueError):
        run_connections(bolt(prying_force_assessment_verified=False))
    with pytest.raises(ValueError, match="prying actions must be zero"):
        run_connections(
            bolt(
                check_type="bolt_group",
                shear_action_kn=0,
                tension_action_kn=0,
                prying_tension_kn=1,
                points_mm=[[-50, 0], [50, 0]],
                force_x_kn=0,
                force_y_kn=10,
                moment_z_knm=0,
            )
        )


def test_clause_9_1_7_assigns_actions_to_non_slip_groups_and_preserves_moments():
    result = run_connections(combined_connection())
    assignment = result["intermediate"]["load_case_assignments"][0]["component_group_assignments"]
    by_group = {item["group_id"]: item for item in assignment}
    assert by_group["friction-bolts"]["assigned_actions"]["shear_y_kn"] == 60
    assert by_group["friction-bolts"]["assigned_actions"]["moment_z_knm"] == 15
    assert by_group["fitted-bolts"]["assigned_actions"]["shear_y_kn"] == 40
    assert by_group["fitted-bolts"]["assigned_actions"]["moment_z_knm"] == 10
    assert by_group["snug-bolts"]["assigned_share"] == 0
    assert by_group["snug-bolts"]["assigned_actions"]["shear_y_kn"] == 0


def test_clause_9_1_7_keeps_weld_stage_actions_on_welds():
    inputs = combined_connection(
        component_groups=[
            {"group_id": "weld-group", "fastener_class": "weld"},
            {"group_id": "later-bolts", "fastener_class": "non_slip"},
            {"group_id": "snug-bolts", "fastener_class": "slip_type"},
        ],
        load_cases=[
            {
                "case_id": "initial-weld-load",
                "stage": "initially_applied_to_welds",
                "actions": {
                    "axial_kn": 0,
                    "shear_x_kn": 12,
                    "shear_y_kn": 0,
                    "moment_x_knm": 0,
                    "moment_y_knm": 0,
                    "moment_z_knm": 3,
                },
                "shares": [],
            },
            {
                "case_id": "subsequent-load",
                "stage": "after_welding",
                "actions": {
                    "axial_kn": 0,
                    "shear_x_kn": 20,
                    "shear_y_kn": 0,
                    "moment_x_knm": 0,
                    "moment_y_knm": 0,
                    "moment_z_knm": 5,
                },
                "shares": [],
            },
        ],
    )
    cases = run_connections(inputs)["intermediate"]["load_case_assignments"]
    for case in cases:
        assigned = {item["group_id"]: item for item in case["component_group_assignments"]}
        weld = assigned["weld-group"]["assigned_actions"]
        later_bolts = assigned["later-bolts"]["assigned_actions"]
        snug_bolts = assigned["snug-bolts"]["assigned_actions"]
        assert weld["shear_x_kn"] == (12 if case["case_id"] == "initial-weld-load" else 20)
        assert later_bolts["shear_x_kn"] == snug_bolts["shear_x_kn"] == 0


@pytest.mark.parametrize(
    "shares,stage",
    [
        ([{"group_id": "snug-bolts", "fraction": 1}], "non_weld_action"),
        ([{"group_id": "friction-bolts", "fraction": 0.6}], "non_weld_action"),
        ([], "after_welding"),
    ],
)
def test_clause_9_1_7_rejects_invalid_action_shares_or_weld_sequence(shares, stage):
    case = combined_connection()["load_cases"][0]
    case["stage"] = stage
    case["shares"] = shares
    inputs = combined_connection(load_cases=[case])
    if stage == "after_welding":
        inputs["component_groups"] = [
            {"group_id": "friction-bolts", "fastener_class": "non_slip"},
            {"group_id": "snug-bolts", "fastener_class": "slip_type"},
        ]
    with pytest.raises(ValueError):
        run_connections(inputs)


def test_clause_9_3_2_out_of_plane_bolt_actions_check_equilibrium_and_capacity():
    result = run_connections(bolt_group_out_of_plane())
    assert result["checks"]["action_distribution_equilibrium"]["satisfied"]
    assert result["intermediate"]["actions_resolved_from_bolts"]["moment_y_knm"] == -3
    first = result["checks"]["bolts"][0]
    assert first["shear_action_kn"] == 20
    assert first["total_bolt_tension_action_kn"] == 85
    expected = (20 / 92.628) ** 2 + (85 / 162.68) ** 2
    assert first["interaction"]["utilisation"] == pytest.approx(expected)
    assert first["tension"]["clause"] == "9.1.8; 9.2.2.2"


def test_clause_9_3_2_reports_unequal_distribution_resultants_and_rejects_bad_details():
    unbalanced = run_connections(bolt_group_out_of_plane(group_tension_kn=99))
    equilibrium = unbalanced["checks"]["action_distribution_equilibrium"]
    assert not equilibrium["satisfied"]
    assert equilibrium["components"]["tension_kn"]["residual"] == 1

    invalid = bolt_group_out_of_plane()
    invalid["bolt_actions"][1]["position_mm"] = [50, 0]
    with pytest.raises(ValueError, match="positions must be distinct"):
        run_connections(invalid)

    invalid = bolt_group_out_of_plane()
    invalid["bolt_actions"][0]["prying_force_assessment_verified"] = False
    with pytest.raises(ValueError):
        run_connections(invalid)


@pytest.mark.parametrize(
    "length,expected", [(299, 1), (300, 1), (800, 0.875), (1300, 0.75), (1301, 0.75)]
)
def test_lap_boundaries(length, expected):
    assert run_connections(bolt(lap_length_mm=length))["intermediate"][
        "lap_factor"
    ] == pytest.approx(expected)


def test_grade_filler_and_plain_planes():
    r = run_connections(
        bolt(
            grade="10.9",
            filler_thickness_mm=10,
            filler_plate_extends_beyond_connection_verified=True,
            filler_plate_force_transfer_through_combined_section_verified=True,
        )
    )
    assert r["checks"]["shear"]["design_capacity_kn"] == pytest.approx(92.628 * 0.83 * 0.9384)
    assert r["checks"]["filler_plate_detailing"]["satisfied"]
    r = run_connections(bolt(grade="10.9", threaded_planes=0, plain_planes=2))
    assert r["intermediate"]["ductility_factor"] == 1
    assert r["checks"]["shear"]["design_capacity_kn"] == pytest.approx(
        0.8 * 0.62 * 830 * 628 / 1000
    )


def test_filler_plate_clause_9_2_2_5_requires_and_reports_detailing_assessment():
    with pytest.raises(
        ValueError, match="filler extension and force-transfer bolting must be verified"
    ):
        run_connections(bolt(filler_thickness_mm=10))

    result = run_connections(
        bolt(
            filler_thickness_mm=10,
            filler_plate_extends_beyond_connection_verified=True,
            filler_plate_force_transfer_through_combined_section_verified=False,
        )
    )
    detail = result["checks"]["filler_plate_detailing"]
    assert detail["clause"] == "9.2.2.5"
    assert detail["extension_beyond_connection_verified"]
    assert not detail["bolting_transfers_member_force_through_combined_section_verified"]
    assert not detail["satisfied"]
    assert result["intermediate"]["filler_factor"] == pytest.approx(1 - 0.0154 * 4)

    six_mm = run_connections(
        bolt(
            filler_thickness_mm=6,
            filler_plate_extends_beyond_connection_verified=True,
            filler_plate_force_transfer_through_combined_section_verified=True,
        )
    )
    assert six_mm["intermediate"]["filler_factor"] == 1
    assert six_mm["checks"]["filler_plate_detailing"]["satisfied"]


def test_clause_9_2_2_5_uses_maximum_filler_thickness_across_shear_planes():
    data = bolt(
        filler_thickness_by_shear_plane_mm=[8, 12, 10],
        filler_plate_extends_beyond_connection_verified=True,
        filler_plate_force_transfer_through_combined_section_verified=True,
    )
    data.pop("filler_thickness_mm")
    result = run_connections(data)

    assert result["intermediate"]["filler_thickness_used_mm"] == 12
    assert result["intermediate"]["filler_factor"] == pytest.approx(1 - 0.0154 * (12 - 6))
    assert result["checks"]["filler_plate_detailing"]["governing_filler_thickness_mm"] == 12

    inconsistent = bolt(
        filler_thickness_mm=11,
        filler_thickness_by_shear_plane_mm=[8, 12, 10],
        filler_plate_extends_beyond_connection_verified=True,
        filler_plate_force_transfer_through_combined_section_verified=True,
    )
    with pytest.raises(ValueError, match="must equal the maximum thickness"):
        run_connections(inconsistent)


@pytest.mark.parametrize("check", [bolt_group_out_of_plane, bolt_group_elastic_3d])
def test_filler_plate_detailing_is_required_for_bolt_group_checks(check):
    with pytest.raises(
        ValueError, match="filler extension and force-transfer bolting must be verified"
    ):
        run_connections(check(filler_thickness_mm=10))

    result = run_connections(
        check(
            filler_thickness_mm=10,
            filler_plate_extends_beyond_connection_verified=True,
            filler_plate_force_transfer_through_combined_section_verified=True,
        )
    )
    assert result["checks"]["filler_plate_detailing"]["satisfied"]


def test_bearing_edge_governs():
    r = run_connections(
        {
            "check_type": "bearing",
            "diameter_mm": 20,
            "ply_thickness_mm": 10,
            "ultimate_strength_mpa": 440,
            "effective_edge_distance_mm": 30,
            "action_kn": 100,
        }
    )
    assert r["checks"]["bearing"]["design_capacity_kn"] == pytest.approx(118.8)


@pytest.mark.parametrize(
    "hole,capacity",
    [("standard", 49), ("short_slot", 41.65), ("oversize", 41.65), ("long_slot", 34.3)],
)
def test_slip_service_phi_and_interaction(hole, capacity):
    r = run_connections(
        {
            "check_type": "slip",
            "slip_factor": 0.35,
            "interfaces": 1,
            "installation_tension_kn": 200,
            "hole_type": hole,
            "shear_action_kn": capacity / 2,
            "tension_action_kn": 70,
        }
    )
    assert r["checks"]["slip"]["design_capacity_kn"] == pytest.approx(capacity)
    assert r["checks"]["interaction"]["utilisation"] == pytest.approx(1)
    assert not r["checks"]["surface_requirements"]["satisfied"]


def test_clause_9_2_3_2_requires_surface_or_test_evidence_and_drawing_record():
    base = {
        "check_type": "slip",
        "slip_factor": 0.35,
        "interfaces": 1,
        "installation_tension_kn": 200,
        "hole_type": "standard",
        "shear_action_kn": 0,
        "tension_action_kn": 0,
        "friction_bolt_category_and_surface_treatment_masking_drawings_verified": True,
    }
    as_rolled = run_connections({**base, "clean_as_rolled_contact_surfaces_verified": True})
    assert as_rolled["checks"]["surface_requirements"]["slip_factor_basis"] == "clean_as_rolled"
    assert as_rolled["checks"]["surface_requirements"]["satisfied"]

    tested_surface = run_connections(
        {
            **base,
            "slip_factor": 0.42,
            "slip_factor_test_evidence_verified": True,
        }
    )
    assert tested_surface["checks"]["surface_requirements"]["slip_factor_basis"] == "test_evidence"
    assert tested_surface["checks"]["surface_requirements"]["satisfied"]

    missing_drawing_record = run_connections(
        {
            **base,
            "clean_as_rolled_contact_surfaces_verified": True,
            "friction_bolt_category_and_surface_treatment_masking_drawings_verified": False,
        }
    )
    assert not missing_drawing_record["checks"]["surface_requirements"]["satisfied"]


def test_appendix_j_three_specimen_factor_uses_sample_deviation_and_minimum_fallback():
    result = run_connections(appendix_j_slip_test())
    factor = result["checks"]["slip_factor"]
    expected_deviation = (0.01015 / 5) ** 0.5
    expected_unadjusted = 0.85 * (0.405 - 1.64 * expected_deviation)
    assert factor["mean_of_individual_estimates"] == pytest.approx(0.405)
    assert factor["sample_standard_deviation"] == pytest.approx(expected_deviation)
    assert factor["unadjusted_factor"] == pytest.approx(expected_unadjusted)
    assert factor["lowest_individual_estimate"] == pytest.approx(0.35)
    assert factor["minimum_estimate_fallback_applied"]
    assert factor["slip_factor_for_design"] == pytest.approx(0.35)
    assert factor["individual_estimate_count"] == 6
    assert factor["clause"] == "Appendix J.5"
    assert result["intermediate"]["appendix_j_prerequisites"][
        "instrumentation_layout_per_appendix_j_verified"
    ]
    assert (
        result["intermediate"]["bolt_tension_method_evidence"]["calibration_test_bolt_count"] == 3
    )
    assert result["checks"]["specimen_geometry"]["minimum_test_section_length_mm"] == 160
    assert result["checks"]["specimen_geometry"]["specimen_width_mm"] == 96


def test_appendix_j3_calculates_connection_slip_load_and_increment_limit():
    result = run_connections(appendix_j_slip_test())
    protocol = result["checks"]["loading_protocol"]
    specimen = protocol["specimens"][0]
    assert protocol["clause"] == "Appendix J.3"
    assert specimen["assumed_slip_factor"] == 0.35
    assert specimen["predicted_connection_slip_load_kn"] == pytest.approx(70)
    assert specimen["maximum_permitted_increment_kn"] == pytest.approx(17.5)
    assert specimen["satisfied"]
    assert all(increment["increment_satisfied"] for increment in specimen["increments"])
    assert all(increment["rate_satisfied"] for increment in specimen["increments"])


def test_appendix_j3_increment_limit_is_capped_at_25_kn():
    inputs = appendix_j_slip_test()
    inputs.update(
        {
            "nominal_bolt_diameter_mm": 30,
            "specimen_geometry": {
                "bolt_centre_spacing_mm": 180,
                "left_bolt_to_test_section_end_mm": 60,
                "right_bolt_to_test_section_end_mm": 60,
                "upper_bolt_edge_distance_mm": 90,
                "lower_bolt_edge_distance_mm": 90,
                "inner_plate_thicknesses_mm": [35, 35],
                "cover_plate_thicknesses_mm": [17, 17],
                "cover_plate_hole_diameter_mm": 32,
                "inner_plate_hole_diameter_mm": 33,
                "butt_gap_mm": 8,
            },
        }
    )
    for test_specimen in inputs["specimens"]:
        for bolt in test_specimen["bolts"]:
            bolt["calibrated_bolt_tension_kn"] = 400
    specimen = inputs["specimens"][0]
    specimen["loading_increments"] = [
        {
            "load_before_kn": 0,
            "load_after_kn": 25,
            "maximum_rate_kn_per_min": 40,
            "loading_rate_approximately_uniform_verified": True,
        },
        {
            "load_before_kn": 25,
            "load_after_kn": 50,
            "maximum_rate_kn_per_min": 40,
            "loading_rate_approximately_uniform_verified": True,
            "preceding_load_creep_effectively_ceased_verified": True,
        },
        {
            "load_before_kn": 50,
            "load_after_kn": 70,
            "maximum_rate_kn_per_min": 40,
            "loading_rate_approximately_uniform_verified": True,
            "preceding_load_creep_effectively_ceased_verified": True,
        },
        {
            "load_before_kn": 70,
            "load_after_kn": 92,
            "maximum_rate_kn_per_min": 60,
            "loading_rate_approximately_uniform_verified": True,
            "preceding_load_creep_effectively_ceased_verified": True,
        },
    ]

    result = run_connections(inputs)
    protocol = result["checks"]["loading_protocol"]["specimens"][0]
    assert protocol["predicted_connection_slip_load_kn"] == pytest.approx(280)
    assert protocol["maximum_permitted_increment_kn"] == pytest.approx(25)


def test_appendix_j3_uses_the_lower_predicted_slip_load_for_series_positions():
    inputs = appendix_j_slip_test()
    specimen = inputs["specimens"][0]
    second_bolt = specimen["bolts"][1]
    second_bolt["calibrated_bolt_tension_kn"] = 120
    second_bolt["slip_load_kn"] = 84
    specimen["loading_increments"].append(
        {
            "load_before_kn": 72,
            "load_after_kn": 84,
            "maximum_rate_kn_per_min": 60,
            "loading_rate_approximately_uniform_verified": True,
            "preceding_load_creep_effectively_ceased_verified": True,
        }
    )

    result = run_connections(inputs)
    protocol = result["checks"]["loading_protocol"]["specimens"][0]
    assert [
        item["predicted_slip_load_kn"] for item in protocol["predicted_position_slip_loads"]
    ] == pytest.approx([70, 84])
    assert protocol["predicted_connection_slip_load_kn"] == pytest.approx(70)
    assert protocol["maximum_permitted_increment_kn"] == pytest.approx(17.5)


def test_appendix_j4_interpolates_13mm_slip_from_the_mean_of_edge_readings():
    inputs = appendix_j_slip_test()
    bolt = inputs["specimens"][0]["bolts"][0]
    bolt.pop("slip_load_kn")
    bolt["slip_load_method"] = "0.13_mm_deformation"
    bolt["deformation_readings"] = [
        {
            "load_kn": 0,
            "left_edge_deformation_mm": 0,
            "right_edge_deformation_mm": 0,
        },
        {
            "load_kn": 60,
            "left_edge_deformation_mm": 0.08,
            "right_edge_deformation_mm": 0.12,
        },
        {
            "load_kn": 80,
            "left_edge_deformation_mm": 0.15,
            "right_edge_deformation_mm": 0.17,
        },
    ]

    result = run_connections(inputs)
    bolt_result = result["intermediate"]["specimens"][0]["bolts"][0]
    determination = bolt_result["slip_load_determination"]
    assert bolt_result["slip_load_kn"] == pytest.approx(70)
    assert bolt_result["individual_slip_factor_estimate"] == pytest.approx(0.35)
    assert determination["method"] == "0.13_mm_deformation"
    assert determination["deformation_threshold_mm"] == pytest.approx(0.13)
    assert determination["mean_edge_deformation_at_lower_reading_mm"] == pytest.approx(0.1)
    assert determination["mean_edge_deformation_at_upper_reading_mm"] == pytest.approx(0.16)
    assert determination["interpolated"]


def test_appendix_j4_rejects_unbracketed_or_nonincreasing_load_readings():
    inputs = appendix_j_slip_test()
    bolt = inputs["specimens"][0]["bolts"][0]
    bolt.pop("slip_load_kn")
    bolt["slip_load_method"] = "0.13_mm_deformation"
    bolt["deformation_readings"] = [
        {"load_kn": 0, "left_edge_deformation_mm": 0, "right_edge_deformation_mm": 0},
        {
            "load_kn": 60,
            "left_edge_deformation_mm": 0.1,
            "right_edge_deformation_mm": 0.1,
        },
    ]
    with pytest.raises(ValueError, match="do not reach 0.13 mm"):
        run_connections(inputs)

    bolt["deformation_readings"][1]["load_kn"] = 0
    with pytest.raises(ValueError, match="increasing load values"):
        run_connections(inputs)


def test_appendix_j3_rejects_excessive_increment_or_loading_rate_before_slip():
    inputs = appendix_j_slip_test()
    inputs["specimens"][0]["loading_increments"][0]["load_after_kn"] = 17.6
    with pytest.raises(ValueError, match="load increment exceeds"):
        run_connections(inputs)

    inputs = appendix_j_slip_test()
    inputs["specimens"][0]["loading_increments"][0]["maximum_rate_kn_per_min"] = 50.1
    with pytest.raises(ValueError, match="loading rate exceeds 50 kN/min"):
        run_connections(inputs)


def test_appendix_j3_requires_creep_to_cease_between_load_increments():
    inputs = appendix_j_slip_test()
    del inputs["specimens"][0]["loading_increments"][1][
        "preceding_load_creep_effectively_ceased_verified"
    ]
    with pytest.raises(ValueError, match="cessation of creep"):
        run_connections(inputs)


def test_appendix_j3_allows_operator_adjustment_after_first_bolt_position_slips():
    inputs = appendix_j_slip_test()
    final_increment = inputs["specimens"][0]["loading_increments"][-1]
    final_increment["maximum_rate_kn_per_min"] = 60
    result = run_connections(inputs)
    final_result = result["checks"]["loading_protocol"]["specimens"][0]["increments"][-1]
    assert final_result["load_before_kn"] == pytest.approx(70)
    assert not final_result["increment_and_rate_limits_apply"]
    assert final_result["rate_satisfied"]


def test_appendix_j_five_specimen_factor_uses_k_point_nine_without_fallback():
    result = run_connections(appendix_j_slip_test((0.1, *([0.5] * 9))))
    factor = result["checks"]["slip_factor"]
    expected_deviation = (0.144 / 9) ** 0.5
    expected_unadjusted = 0.9 * (0.46 - 1.64 * expected_deviation)
    assert factor["specimen_count"] == 5
    assert factor["k"] == pytest.approx(0.9)
    assert factor["mean_of_individual_estimates"] == pytest.approx(0.46)
    assert factor["sample_standard_deviation"] == pytest.approx(expected_deviation)
    assert factor["unadjusted_factor"] == pytest.approx(expected_unadjusted)
    assert factor["unadjusted_factor"] > 0.1
    assert not factor["minimum_estimate_fallback_applied"]
    assert factor["slip_factor_for_design"] == pytest.approx(expected_unadjusted)


def test_appendix_j_equation_j1_calculates_bolt_tension_and_enforces_proof_range():
    inputs = appendix_j_slip_test()
    inputs.update(
        {
            "bolt_tension_method": "equation_j1",
            "specified_bolt_proof_load_kn": 120,
            "proof_load_reference": "BOLT-SPEC-001",
            "bolt_proof_load_specification_verified": True,
            "bolt_geometry_source_reference": "BOLT-GEOMETRY-001",
            "bolt_geometry_matches_tested_assembly_verified": True,
        }
    )
    for specimen in inputs["specimens"]:
        for bolt_input in specimen["bolts"]:
            bolt_input.pop("calibrated_bolt_tension_kn")
            bolt_input.update(
                {
                    "bolt_extension_mm": 0.14,
                    "unthreaded_grip_length_mm": 20,
                    "unthreaded_shank_area_mm2": 201,
                    "threaded_grip_length_mm": 20,
                    "nut_thickness_mm": 16,
                    "tensile_stress_area_mm2": 157,
                    "slip_load_kn": 70,
                }
            )
    for field in (
        "calibration_test_bolt_count",
        "calibration_curve_reference",
        "calibration_test_bolts_from_test_batch_verified",
        "calibration_grip_and_measurement_method_match_verified",
        "calibration_curve_based_on_mean_result_verified",
    ):
        inputs.pop(field)
    result = run_connections(inputs)
    expected_tension = 28 / (20 / 201 + 28 / 157)
    position = result["intermediate"]["specimens"][0]["bolts"][0]
    assert position["bolt_tension_kn"] == pytest.approx(expected_tension)
    assert position["minimum_bolt_tension_kn"] == 95
    assert result["intermediate"]["standard_deviation_divisor"] == 5
    assert result["intermediate"]["bolt_tension_method_evidence"][
        "bolt_geometry_matches_tested_assembly_verified"
    ]
    for proof_load in (100, 130):
        inputs["specified_bolt_proof_load_kn"] = proof_load
        with pytest.raises(ValueError, match="80% to 100%"):
            run_connections(inputs)


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"specimens": appendix_j_slip_test().get("specimens", [])[:2]}, "too short"),
        ({"extension_instrument_resolution_mm": 0.004}, "maximum"),
        ({"symmetrical_double_cover_butt_specimen_verified": False}, "True"),
    ],
)
def test_appendix_j_rejects_incomplete_or_noncompliant_prerequisites(changes, message):
    with pytest.raises(ValueError, match=message):
        run_connections({**appendix_j_slip_test(), **changes})


def test_appendix_j_rejects_four_specimens_without_a_defined_k_value():
    with pytest.raises(ValueError, match="no k value for four specimens"):
        run_connections(appendix_j_slip_test((0.35,) * 8))


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"bolt_centre_spacing_mm": 95.9}, "bolt_centre_spacing_mm"),
        (
            {
                "left_bolt_to_test_section_end_mm": 31.9,
                "right_bolt_to_test_section_end_mm": 31.9,
            },
            "left_bolt_to_test_section_end_mm",
        ),
        (
            {"upper_bolt_edge_distance_mm": 47.9, "lower_bolt_edge_distance_mm": 47.9},
            "upper_bolt_edge_distance_mm",
        ),
        ({"inner_plate_thicknesses_mm": [20.9, 20.9]}, "df \\+ 5"),
        ({"inner_plate_thicknesses_mm": [21, 22]}, "equal inner-plate"),
        ({"cover_plate_thicknesses_mm": [9.9, 9.9]}, "df/2 \\+ 2"),
        ({"cover_plate_thicknesses_mm": [10, 11]}, "equal cover-plate"),
        ({"cover_plate_hole_diameter_mm": 17}, "df \\+ 2"),
        ({"inner_plate_hole_diameter_mm": 18}, "df \\+ 3"),
        ({"butt_gap_mm": 7.9}, "8 mm butt gap"),
        ({"right_bolt_to_test_section_end_mm": 33}, "symmetric bolt layout"),
        ({"lower_bolt_edge_distance_mm": 49}, "equal bolt edge distances"),
    ],
)
def test_appendix_j_enforces_figure_j1_specimen_geometry(changes, message):
    inputs = appendix_j_slip_test()
    inputs["specimen_geometry"].update(changes)
    with pytest.raises(ValueError, match=message):
        run_connections(inputs)


def test_appendix_j_rejects_bolts_below_table_minimum_tension():
    inputs = appendix_j_slip_test()
    inputs["specimens"][0]["bolts"][0]["calibrated_bolt_tension_kn"] = 94.9
    with pytest.raises(ValueError, match="Table 15.2.2.2 minimum tension"):
        run_connections(inputs)


def test_block_shear_hand_benchmark():
    r = run_connections(
        {
            "check_type": "block_shear",
            "yield_strength_mpa": 300,
            "ultimate_strength_mpa": 440,
            "gross_shear_area_mm2": 2000,
            "net_shear_area_mm2": 1500,
            "net_tension_area_mm2": 500,
            "uniform_tension": False,
            "action_kn": 200,
        }
    )
    # Ru=min(396+110,360+110)=470kN; phi=0.75
    assert r["checks"]["block_shear"]["design_capacity_kn"] == pytest.approx(352.5)


def test_block_shear_path_set_selects_lowest_capacity_from_independent_arithmetic():
    result = run_connections(
        {
            "check_type": "block_shear_paths",
            "yield_strength_mpa": 300,
            "ultimate_strength_mpa": 440,
            "thickness_mm": 10,
            "candidate_paths": [
                {
                    "path_id": "path-a",
                    "gross_shear_length_mm": 200,
                    "net_shear_length_mm": 150,
                    "net_tension_length_mm": 50,
                    "uniform_tension": False,
                },
                {
                    "path_id": "path-b",
                    "gross_shear_length_mm": 180,
                    "net_shear_length_mm": 130,
                    "net_tension_length_mm": 60,
                    "uniform_tension": False,
                },
                {
                    "path_id": "path-c",
                    "gross_shear_length_mm": 200,
                    "net_shear_length_mm": 150,
                    "net_tension_length_mm": 50,
                    "uniform_tension": True,
                },
            ],
            "rupture_paths_complete_and_net_lengths_verified": True,
            "action_kn": 250,
        }
    )
    summary = result["checks"]["block_shear_path_set"]
    assert [path["design_capacity_kn"] for path in summary["paths"]] == pytest.approx(
        [352.5, 342, 435]
    )
    assert summary["controlling_path_id"] == "path-b"
    assert summary["design_capacity_kn"] == pytest.approx(342)
    assert summary["satisfied"]


@pytest.mark.parametrize(
    ("path_changes", "message"),
    [
        ({"path_id": "path-a"}, "unique"),
        ({"net_shear_length_mm": 201}, "cannot exceed gross"),
    ],
)
def test_block_shear_path_set_rejects_invalid_path_data(path_changes, message):
    valid_path = {
        "path_id": "path-a",
        "gross_shear_length_mm": 200,
        "net_shear_length_mm": 150,
        "net_tension_length_mm": 50,
        "uniform_tension": False,
    }
    second_path = {
        "path_id": "path-b",
        "gross_shear_length_mm": 100,
        "net_shear_length_mm": 90,
        "net_tension_length_mm": 50,
        "uniform_tension": True,
    }
    inputs = {
        "check_type": "block_shear_paths",
        "yield_strength_mpa": 300,
        "ultimate_strength_mpa": 440,
        "thickness_mm": 10,
        "candidate_paths": [valid_path, {**second_path, **path_changes}],
        "rupture_paths_complete_and_net_lengths_verified": True,
        "action_kn": 100,
    }
    with pytest.raises(ValueError, match=message):
        run_connections(inputs)


def test_pin_hand_benchmark():
    r = run_connections(
        {
            "check_type": "pin",
            "yield_strength_mpa": 300,
            "diameter_mm": 30,
            "shear_planes": 2,
            "ply_thickness_mm": 10,
            "rotates": True,
            "shear_action_kn": 100,
            "bearing_action_kn": 40,
            "moment_action_knm": 1,
        }
    )
    assert r["checks"]["shear"]["design_capacity_kn"] == pytest.approx(
        0.8 * 0.62 * 300 * 2 * pi * 225 / 1000
    )
    assert r["checks"]["bearing"]["design_capacity_kn"] == pytest.approx(50.4)
    assert r["checks"]["bending"]["design_capacity_knm"] == pytest.approx(1.08)


@pytest.mark.parametrize(
    "quality,thin,phi", [("SP", False, 0.8), ("SP", True, 0.7), ("GP", False, 0.6)]
)
def test_fillet_hand_benchmark(quality, thin, phi):
    r = run_connections(
        {
            "check_type": "fillet",
            "weld_strength_mpa": 490,
            "throat_mm": 4.2,
            "effective_length_mm": 100,
            "quality": quality,
            "thin_rhs_longitudinal": thin,
            "lap_length_mm": 0,
            "action_kn": 50,
        }
    )
    assert r["checks"]["weld"]["design_capacity_kn"] == pytest.approx(123.48 * phi)


@pytest.mark.parametrize(
    "lap_length_mm,lap_factor",
    [(1700, 1), (1701, 1.10 - 0.06 * 1.701), (8000, 0.62), (8001, 0.62)],
)
def test_fillet_lap_length_boundaries(lap_length_mm, lap_factor):
    r = run_connections(
        {
            "check_type": "fillet",
            "weld_strength_mpa": 490,
            "throat_mm": 4.2,
            "effective_length_mm": 100,
            "quality": "SP",
            "thin_rhs_longitudinal": False,
            "lap_length_mm": lap_length_mm,
            "action_kn": 50,
        }
    )
    assert r["checks"]["weld"]["design_capacity_kn"] == pytest.approx(
        0.8 * 0.6 * 490 * 4.2 * 100 * lap_factor / 1000
    )


def fillet_design(**changes):
    inputs = {
        "check_type": "fillet_design",
        "weld_strength_mpa": 490,
        "quality": "SP",
        "leg_1_mm": 6,
        "leg_2_mm": 6,
        "included_angle_deg": 90,
        "root_gap_mm": 0,
        "thickest_part_mm": 10,
        "thinnest_part_mm": 6,
        "edge_material_thickness_mm": 10,
        "edge_built_out_verified": False,
        "reinforces_butt_weld": False,
        "overall_length_per_segment_mm": 100,
        "segment_count": 1,
        "intermittent_segment": False,
        "clear_spacing_mm": 0,
        "at_built_up_member_end": False,
        "member_force_type": "other",
        "forms_built_up_member": False,
        "parallel_weld_count": 1,
        "parallel_load_share_verified": False,
        "transverse_weld_spacing_mm": 0,
        "thin_rhs_longitudinal": False,
        "lap_length_mm": 0,
        "action_kn": 50,
    }
    inputs.update(changes)
    return run_connections(inputs)


def fillet_macro_test_evidence(additional_penetration_mm=0):
    return {
        "automatic_arc_welding_process_verified": True,
        "production_weld_macro_test_verified": True,
        "macro_test_required_penetration_achieved_verified": True,
        "macro_test_record_reference": "FILLET-MACRO-01",
        "macro_test_additional_penetration_mm": additional_penetration_mm,
    }


def test_fillet_design_calculates_throat_effective_area_and_strength():
    result = fillet_design()
    throat = 6 / 2**0.5
    weld = result["checks"]["weld_strength"]
    assert result["intermediate"]["design_throat_mm"] == pytest.approx(throat)
    assert result["intermediate"]["effective_area_mm2"] == pytest.approx(throat * 100)
    assert weld["design_capacity_kn"] == pytest.approx(0.8 * 0.6 * 490 * throat * 100 / 1000)
    assert weld["satisfied"]
    assert result["checks"]["weld_size"]["satisfied"]
    assert result["checks"]["weld_length_and_area"]["satisfied"]
    assert result["check_type"] == "fillet_design"


def test_fillet_design_macro_test_increases_throat_using_figure_9_6_3_4():
    result = fillet_design(**fillet_macro_test_evidence(4), action_kn=0)
    intermediate = result["intermediate"]
    weld = result["checks"]["weld_strength"]
    expected_throat = 6 / 2**0.5 + 0.85 * 4

    assert intermediate["macro_test_throat_increase"]["t_t1_mm"] == pytest.approx(6 / 2**0.5)
    assert intermediate["macro_test_throat_increase"]["t_t2_mm"] == 4
    assert intermediate["geometric_throat_before_length_reduction_mm"] == pytest.approx(
        expected_throat
    )
    assert intermediate["design_throat_mm"] == pytest.approx(expected_throat)
    assert intermediate["effective_area_mm2"] == pytest.approx(expected_throat * 100)
    assert weld["nominal_capacity_kn"] == pytest.approx(0.6 * 490 * expected_throat * 100 / 1000)
    assert weld["design_capacity_kn"] == pytest.approx(
        0.8 * 0.6 * 490 * expected_throat * 100 / 1000
    )
    assert "9.6.3.4 macro-test throat" in weld["clause"]


def test_fillet_design_macro_throat_observes_short_length_reduction():
    result = fillet_design(
        **fillet_macro_test_evidence(4),
        overall_length_per_segment_mm=12,
        action_kn=0,
    )
    intermediate = result["intermediate"]
    figure_throat = 6 / 2**0.5 + 0.85 * 4

    assert intermediate["macro_test_throat_increase"][
        "figure_design_throat_before_length_reduction_mm"
    ] == pytest.approx(figure_throat)
    assert result["checks"]["weld_length_and_area"]["length_based_size_reduction_factor"] == 0.5
    assert intermediate["design_throat_mm"] == pytest.approx(figure_throat * 0.5)


def test_fillet_design_macro_test_requires_complete_verified_evidence():
    with pytest.raises(ValueError, match="fillet macro-test throat increase requires"):
        fillet_design(automatic_arc_welding_process_verified=True)
    invalid_evidence = fillet_macro_test_evidence()
    invalid_evidence["production_weld_macro_test_verified"] = False
    with pytest.raises(ValueError):
        fillet_design(**invalid_evidence)


def test_fillet_design_root_gap_short_length_and_minimum_size_boundaries():
    short = fillet_design(
        leg_1_mm=6,
        leg_2_mm=6,
        root_gap_mm=1,
        overall_length_per_segment_mm=10,
    )
    assert short["intermediate"]["provided_leg_lengths_after_root_gap_mm"] == [5, 5]
    assert short["checks"]["weld_length_and_area"]["length_based_size_reduction_factor"] == 0.5
    assert short["intermediate"]["design_throat_mm"] == pytest.approx(2.5 / 2**0.5)

    size_boundary = fillet_design(
        leg_1_mm=5,
        leg_2_mm=5,
        thickest_part_mm=15,
        edge_material_thickness_mm=6,
    )
    assert size_boundary["checks"]["weld_size"]["checks"]["minimum_size"]["required_mm"] == 5
    assert size_boundary["checks"]["weld_size"]["checks"]["minimum_size"]["satisfied"]
    assert (
        size_boundary["checks"]["weld_size"]["checks"]["maximum_size_along_edge"]["maximum_mm"] == 5
    )
    assert size_boundary["checks"]["weld_size"]["satisfied"]

    capped_minimum = fillet_design(
        leg_1_mm=4,
        leg_2_mm=4,
        thickest_part_mm=16,
        thinnest_part_mm=4,
    )
    assert capped_minimum["checks"]["weld_size"]["checks"]["minimum_size"]["required_mm"] == 4
    assert capped_minimum["checks"]["weld_size"]["satisfied"]


def test_fillet_design_checks_parallel_and_intermittent_built_up_spacing():
    result = fillet_design(
        overall_length_per_segment_mm=40,
        segment_count=4,
        intermittent_segment=True,
        clear_spacing_mm=144,
        member_force_type="tension",
        forms_built_up_member=True,
        parallel_weld_count=2,
        parallel_load_share_verified=True,
        transverse_weld_spacing_mm=96,
    )
    assert result["checks"]["weld_length_and_area"]["satisfied"]
    assert result["checks"]["parallel_weld_spacing"]["maximum_mm"] == 96
    assert result["checks"]["parallel_weld_spacing"]["satisfied"]
    assert result["checks"]["intermittent_clear_spacing"]["maximum_mm"] == 144
    assert result["checks"]["intermittent_clear_spacing"]["satisfied"]

    too_wide = fillet_design(
        intermittent_segment=True,
        member_force_type="compression",
        forms_built_up_member=True,
        parallel_weld_count=2,
        parallel_load_share_verified=True,
        clear_spacing_mm=97,
        transverse_weld_spacing_mm=193,
    )
    assert not too_wide["checks"]["parallel_weld_spacing"]["satisfied"]
    assert not too_wide["checks"]["intermittent_clear_spacing"]["satisfied"]

    at_member_end = fillet_design(
        intermittent_segment=True,
        member_force_type="compression",
        forms_built_up_member=True,
        parallel_weld_count=2,
        parallel_load_share_verified=True,
        clear_spacing_mm=1000,
        at_built_up_member_end=True,
    )
    assert at_member_end["checks"]["intermittent_clear_spacing"]["satisfied"]

    with pytest.raises(ValueError, match="Load sharing"):
        fillet_design(parallel_weld_count=2)


def test_clause_9_6_3_9_built_up_component_end_and_cap_plate_weld_lengths():
    taper_end = run_connections(
        {
            "check_type": "built_up_component_end_weld",
            "connected_component_width_mm": 50,
            "weld_length_per_joint_line_mm": 90,
            "side_fillet_only": True,
            "tapered_component": True,
            "widest_component_width_mm": 80,
            "taper_length_mm": 90,
        }
    )
    assert taper_end["checks"]["built_up_termination"]["minimum_length_mm"] == 90
    assert taper_end["checks"]["built_up_termination"]["satisfied"]

    short_taper_end = run_connections(
        {
            "check_type": "built_up_component_end_weld",
            "connected_component_width_mm": 50,
            "weld_length_per_joint_line_mm": 89,
            "side_fillet_only": True,
            "tapered_component": True,
            "widest_component_width_mm": 80,
            "taper_length_mm": 90,
        }
    )
    assert not short_taper_end["checks"]["built_up_termination"]["satisfied"]

    non_side_fillet = run_connections(
        {
            "check_type": "built_up_component_end_weld",
            "connected_component_width_mm": 50,
            "weld_length_per_joint_line_mm": 40,
            "side_fillet_only": False,
            "tapered_component": False,
            "widest_component_width_mm": 50,
            "taper_length_mm": 0,
        }
    )
    assert not non_side_fillet["checks"]["built_up_termination"]["applicable"]
    assert non_side_fillet["checks"]["built_up_termination"]["satisfied"]

    cap_plate = run_connections(
        {
            "check_type": "cap_plate_weld",
            "member_width_at_contact_face_mm": 200,
            "weld_length_per_joint_line_mm": 200,
        }
    )
    assert cap_plate["checks"]["built_up_termination"]["satisfied"]
    short_cap_plate = run_connections(
        {
            "check_type": "cap_plate_weld",
            "member_width_at_contact_face_mm": 200,
            "weld_length_per_joint_line_mm": 199,
        }
    )
    assert not short_cap_plate["checks"]["built_up_termination"]["satisfied"]


@pytest.mark.parametrize("restraint,above", [("unrestrained", 0), ("restrained", 250)])
def test_clause_9_6_3_9_beam_to_compression_member_weld_lengths(restraint, above):
    result = run_connections(
        {
            "check_type": "beam_compression_member_weld",
            "beam_depth_mm": 300,
            "compression_member_max_dimension_mm": 250,
            "connection_restraint": restraint,
            "weld_length_between_beam_faces_mm": 300,
            "weld_extension_above_top_mm": above,
            "weld_extension_below_bottom_mm": 250,
        }
    )
    checks = result["checks"]["built_up_termination"]["checks"]
    assert result["checks"]["built_up_termination"]["satisfied"]
    if restraint == "restrained":
        assert checks["above_beam"]["required_mm"] == 250


@pytest.mark.parametrize("quality,expected", [("SP", 270), ("GP", 180)])
def test_complete_butt(quality, expected):
    r = run_connections(
        {
            "check_type": "complete_butt",
            "weaker_part_nominal_capacity_kn": 300,
            "quality": quality,
            "qualified_matching_consumable": True,
            "action_kn": 100,
        }
    )
    assert r["checks"]["weld"]["design_capacity_kn"] == expected


def incomplete_butt_design(**changes):
    inputs = {
        "check_type": "incomplete_butt_design",
        "weld_strength_mpa": 490,
        "quality": "SP",
        "preparation_type": "single_v",
        "preparation_depth_mm": 12,
        "preparation_angle_deg": 60,
        "continuous_full_size_weld_length_mm": 200,
        "thin_rhs_longitudinal": False,
        "non_prequalified_v_preparation_verified": True,
        "welding_procedure_and_consumable_basis_verified": True,
        "action_kn": 423.36,
    }
    inputs.update(changes)
    if inputs.get("preparation_depth_mm") is None:
        inputs.pop("preparation_depth_mm")
    return run_connections(inputs)


def macro_test_evidence(penetration_beyond_preparation_mm=0):
    return {
        "automatic_arc_welding_process_verified": True,
        "production_weld_macro_test_verified": True,
        "macro_test_required_penetration_achieved_verified": True,
        "macro_test_record_reference": "MACRO-TEST-01",
        "macro_test_penetration_beyond_preparation_mm": penetration_beyond_preparation_mm,
    }


def prequalified_incomplete_butt_design(**changes):
    inputs = {
        "check_type": "prequalified_incomplete_butt_design",
        "weld_strength_mpa": 490,
        "quality": "SP",
        "prequalified_design_throat_mm": 8,
        "prequalified_preparation_verified": True,
        "prequalified_preparation_reference": "AS/NZS 1554.1 project WPS 01",
        "welding_procedure_and_consumable_basis_verified": True,
        "continuous_full_size_weld_length_mm": 200,
        "thin_rhs_longitudinal": False,
        "action_kn": 0,
    }
    inputs.update(changes)
    return run_connections(inputs)


def butt_weld_transition(**changes):
    inputs = {
        "check_type": "butt_weld_transition",
        "dimension_change_mm": 12,
        "effective_transition_run_mm": 12,
        "transition_method": "chamfer_parent_part",
        "tension_loaded_joint_verified": True,
        "smooth_transition_verified": True,
    }
    inputs.update(changes)
    return run_connections(inputs)


def test_incomplete_butt_design_hand_benchmark():
    result = incomplete_butt_design()
    weld = result["checks"]["weld_strength"]
    intermediate = result["intermediate"]
    assert intermediate["preparation_type"] == "non_prequalified_single_v"
    assert intermediate["total_throat_reduction_mm"] == 3
    assert intermediate["design_throat_mm"] == pytest.approx(9)
    assert intermediate["effective_length_mm"] == 200
    assert intermediate["effective_area_mm2"] == pytest.approx(1800)
    assert weld["nominal_capacity_kn"] == pytest.approx(529.2)
    assert weld["capacity_factor"] == 0.8
    assert weld["design_capacity_kn"] == pytest.approx(423.36)
    assert weld["utilisation"] == pytest.approx(1)
    assert weld["satisfied"]
    assert "9.6.2.3(b)(ii)(A)" in weld["clause"]
    assert "9.6.2.7(c)" in weld["clause"]
    assert not incomplete_butt_design(action_kn=423.3601)["checks"]["weld_strength"]["satisfied"]


def test_prequalified_incomplete_butt_uses_assessed_throat_for_as4100_capacity():
    result = prequalified_incomplete_butt_design(action_kn=376.32)
    intermediate = result["intermediate"]
    weld = result["checks"]["weld_strength"]

    assert intermediate["preparation_type"] == "prequalified"
    assert intermediate["prequalified_design_throat_input_mm"] == 8
    assert intermediate["design_throat_mm"] == 8
    assert intermediate["effective_length_mm"] == 200
    assert intermediate["effective_area_mm2"] == 1600
    assert intermediate["prequalified_preparation_reference"] == "AS/NZS 1554.1 project WPS 01"
    assert weld["nominal_capacity_kn"] == pytest.approx(470.4)
    assert weld["design_capacity_kn"] == pytest.approx(376.32)
    assert weld["satisfied"]
    assert "9.6.2.3(b)(i)" in weld["clause"]
    assert "9.6.2.7(c)" in weld["clause"]
    assert "not authenticated" in result["scope"]


def test_prequalified_incomplete_butt_macro_test_can_increase_assessed_throat():
    result = prequalified_incomplete_butt_design(
        **macro_test_evidence(2),
        preparation_depth_mm=12,
    )
    intermediate = result["intermediate"]
    weld = result["checks"]["weld_strength"]
    expected_throat = 12 + 0.85 * 2
    expected_area = expected_throat * 200

    assert intermediate["design_throat_mm"] == pytest.approx(expected_throat)
    assert intermediate["effective_area_mm2"] == pytest.approx(expected_area)
    assert weld["nominal_capacity_kn"] == pytest.approx(0.6 * 490 * expected_area / 1000)
    assert weld["design_capacity_kn"] == pytest.approx(0.8 * 0.6 * 490 * expected_area / 1000)
    assert "9.6.2.3(b)(iii)" in weld["clause"]
    assert "Figure 9.6.3.4" in weld["clause"]


def test_prequalified_incomplete_butt_rejects_unverified_or_partial_macro_evidence():
    with pytest.raises(ValueError):
        prequalified_incomplete_butt_design(prequalified_preparation_verified=False)
    with pytest.raises(ValueError):
        prequalified_incomplete_butt_design(prequalified_preparation_reference="")
    with pytest.raises(ValueError, match="macro-test evidence"):
        prequalified_incomplete_butt_design(automatic_arc_welding_process_verified=True)


def test_incomplete_butt_design_rejects_unsupported_geometry_and_evidence():
    with pytest.raises(ValueError):
        incomplete_butt_design(preparation_depth_mm=3)
    with pytest.raises(ValueError):
        incomplete_butt_design(non_prequalified_v_preparation_verified=False)
    with pytest.raises(ValueError):
        incomplete_butt_design(welding_procedure_and_consumable_basis_verified=False)
    with pytest.raises(ValueError, match="Single-V preparation"):
        incomplete_butt_design(double_v_preparation_depths_mm=[8, 7])
    with pytest.raises(ValueError, match="Double-V preparation"):
        incomplete_butt_design(preparation_type="double_v")
    with pytest.raises(ValueError):
        incomplete_butt_design(preparation_angle_deg=180.001)


def test_incomplete_butt_design_single_v_greater_than_60_degrees_uses_full_depth():
    result = incomplete_butt_design(preparation_angle_deg=60.001)
    intermediate = result["intermediate"]
    weld = result["checks"]["weld_strength"]
    assert intermediate["design_throat_mm"] == 12
    assert intermediate["total_throat_reduction_mm"] == 0
    assert intermediate["effective_area_mm2"] == 2400
    assert weld["design_capacity_kn"] == pytest.approx(564.48)
    assert "9.6.2.3(b)(ii)(B)" in weld["clause"]


def test_incomplete_butt_macro_test_increases_throat_to_preparation_depth():
    result = incomplete_butt_design(**macro_test_evidence(), action_kn=564.48)
    intermediate = result["intermediate"]
    weld = result["checks"]["weld_strength"]

    assert intermediate["design_throat_mm"] == 12
    assert intermediate["effective_area_mm2"] == 2400
    assert weld["design_capacity_kn"] == pytest.approx(564.48)
    assert weld["satisfied"]
    assert "9.6.2.3(b)(iii)" in weld["clause"]
    assert "9.6.3.4" in weld["clause"]
    assert intermediate["macro_test_throat_increase"] == {
        "used": True,
        "automatic_arc_welding_process_verified": True,
        "production_weld_macro_test_verified": True,
        "required_penetration_achieved_verified": True,
        "record_reference": "MACRO-TEST-01",
        "preparation_depth_t_t1_mm": 12,
        "penetration_beyond_preparation_t_t2_mm": 0,
        "maximum_design_throat_mm": 12,
    }


def test_incomplete_butt_macro_test_applies_figure_9_6_3_4_penetration_factor():
    result = incomplete_butt_design(
        **macro_test_evidence(4),
        action_kn=724.416,
    )
    intermediate = result["intermediate"]
    weld = result["checks"]["weld_strength"]

    assert intermediate["macro_test_throat_increase"]["maximum_design_throat_mm"] == pytest.approx(
        12 + 0.85 * 4
    )
    assert intermediate["design_throat_mm"] == pytest.approx(15.4)
    assert intermediate["effective_area_mm2"] == pytest.approx(3080)
    assert weld["nominal_capacity_kn"] == pytest.approx(905.52)
    assert weld["design_capacity_kn"] == pytest.approx(724.416)
    assert weld["satisfied"]


def test_incomplete_double_v_macro_test_uses_combined_preparation_depth():
    result = incomplete_butt_design(
        preparation_type="double_v",
        preparation_depth_mm=None,
        double_v_preparation_depths_mm=[8, 7],
        **macro_test_evidence(3),
        action_kn=800,
    )
    intermediate = result["intermediate"]
    weld = result["checks"]["weld_strength"]

    assert intermediate["design_throat_mm"] == pytest.approx(15 + 0.85 * 3)
    assert intermediate["effective_area_mm2"] == pytest.approx(17.55 * 200)
    assert weld["design_capacity_kn"] == pytest.approx(825.552)
    assert weld["satisfied"]


def test_incomplete_butt_macro_test_requires_complete_verified_evidence():
    with pytest.raises(ValueError, match="macro-test throat increase requires"):
        incomplete_butt_design(automatic_arc_welding_process_verified=True)
    invalid_evidence = macro_test_evidence()
    invalid_evidence["production_weld_macro_test_verified"] = False
    with pytest.raises(ValueError):
        incomplete_butt_design(**invalid_evidence)


def test_butt_weld_transition_enforces_one_to_one_limit():
    boundary = butt_weld_transition()
    boundary_check = boundary["checks"]["transition_geometry"]
    assert boundary_check["clause"] == "9.6.2.6"
    assert boundary_check["slope_ratio"] == 1
    assert boundary_check["minimum_transition_run_mm"] == 12
    assert boundary_check["satisfied"]

    failed = butt_weld_transition(effective_transition_run_mm=11.99)
    failed_check = failed["checks"]["transition_geometry"]
    assert failed_check["slope_ratio"] == pytest.approx(12 / 11.99)
    assert not failed_check["satisfied"]


def test_butt_weld_transition_accepts_assessed_fatigue_slope_limit():
    result = butt_weld_transition(
        dimension_change_mm=10,
        effective_transition_run_mm=40,
        transition_method="combined",
        fatigue_slope_limit=0.25,
        fatigue_slope_limit_verified=True,
        fatigue_assessment_reference="FATIGUE-DETAIL-01",
    )
    check = result["checks"]["transition_geometry"]
    assert check["clause"] == "9.6.2.6; externally assessed fatigue-specific slope"
    assert check["maximum_permitted_slope_ratio"] == 0.25
    assert check["minimum_transition_run_mm"] == 40
    assert check["satisfied"]

    failed = butt_weld_transition(
        dimension_change_mm=10,
        effective_transition_run_mm=39,
        fatigue_slope_limit=0.25,
        fatigue_slope_limit_verified=True,
        fatigue_assessment_reference="FATIGUE-DETAIL-01",
    )
    assert not failed["checks"]["transition_geometry"]["satisfied"]


def test_butt_weld_transition_requires_tension_and_complete_fatigue_evidence():
    with pytest.raises(ValueError):
        butt_weld_transition(tension_loaded_joint_verified=False)
    with pytest.raises(ValueError, match="fatigue-specific transition slope requires"):
        butt_weld_transition(fatigue_slope_limit=0.5)


@pytest.mark.parametrize(
    "angle,expected_throat,expected_capacity",
    [(60, 9, 423.36), (60.001, 15, 705.6)],
)
def test_incomplete_butt_design_double_v_throat_at_angle_boundary(
    angle, expected_throat, expected_capacity
):
    result = incomplete_butt_design(
        preparation_type="double_v",
        preparation_depth_mm=None,
        double_v_preparation_depths_mm=[8, 7],
        preparation_angle_deg=angle,
        action_kn=400,
    )
    intermediate = result["intermediate"]
    weld = result["checks"]["weld_strength"]
    assert intermediate["preparation_depth_mm"] is None
    assert intermediate["combined_preparation_depth_mm"] == 15
    assert intermediate["design_throat_mm"] == expected_throat
    assert intermediate["effective_area_mm2"] == expected_throat * 200
    assert weld["design_capacity_kn"] == pytest.approx(expected_capacity)
    assert weld["satisfied"]
    expected_clause = "(A)" if angle == 60 else "(B)"
    assert f"9.6.2.3(b)(ii){expected_clause}" in weld["clause"]


def test_incomplete_butt_design_applies_thin_rhs_quality_factor_route():
    result = incomplete_butt_design(thin_rhs_longitudinal=True, action_kn=300)
    weld = result["checks"]["weld_strength"]
    assert weld["capacity_factor"] == 0.7
    assert weld["design_capacity_kn"] == pytest.approx(370.44)
    assert weld["satisfied"]

    with pytest.raises(ValueError, match="SP quality"):
        incomplete_butt_design(quality="GP", thin_rhs_longitudinal=True)


def plug_slot(**changes):
    inputs = {
        "check_type": "plug_slot",
        "weld_strength_mpa": 490,
        "quality": "SP",
        "permitted_shear_application": True,
        "action_kn": 0,
    }
    inputs.update(changes)
    return run_connections(inputs)


def test_plug_slot_accepts_externally_assessed_effective_area():
    r = plug_slot(effective_area_mm2=1000, action_kn=200)
    assert r["checks"]["weld"]["design_capacity_kn"] == pytest.approx(235.2)


@pytest.mark.parametrize(
    ("geometry", "expected_area"),
    [
        ({"hole_shape": "circular", "hole_diameter_mm": 40}, 400 * pi),
        (
            {"hole_shape": "round_ended_slot", "slot_length_mm": 50, "slot_width_mm": 20},
            600 + 100 * pi,
        ),
        ({"hole_shape": "rectangular_slot", "slot_length_mm": 50, "slot_width_mm": 20}, 1000),
    ],
)
def test_plug_slot_calculates_verified_faying_plane_area(geometry, expected_area):
    result = plug_slot(**geometry, hole_geometry_verified=True)
    area = result["intermediate"]["effective_area_mm2"]

    assert area == pytest.approx(expected_area)
    assert result["intermediate"]["area_basis"] == "nominal_faying_plane_hole_geometry"
    assert result["checks"]["weld"]["nominal_capacity_kn"] == pytest.approx(
        0.6 * 490 * expected_area / 1000
    )
    assert result["checks"]["weld"]["design_capacity_kn"] == pytest.approx(
        0.8 * 0.6 * 490 * expected_area / 1000
    )


def test_plug_slot_rejects_incomplete_unverified_and_mixed_geometry():
    with pytest.raises(ValueError, match="requires hole_shape"):
        plug_slot(hole_diameter_mm=40, hole_geometry_verified=True)
    with pytest.raises(ValueError, match="incomplete.*hole_diameter_mm"):
        plug_slot(hole_shape="circular", hole_geometry_verified=True)
    with pytest.raises(ValueError, match="incomplete.*slot_width_mm"):
        plug_slot(
            hole_shape="round_ended_slot",
            slot_length_mm=50,
            hole_geometry_verified=True,
        )
    with pytest.raises(ValueError, match="hole_geometry_verified"):
        plug_slot(hole_shape="circular", hole_diameter_mm=40)
    with pytest.raises(ValueError, match="not include.*hole_diameter_mm"):
        plug_slot(
            hole_shape="rectangular_slot",
            hole_diameter_mm=40,
            slot_length_mm=50,
            slot_width_mm=20,
            hole_geometry_verified=True,
        )
    with pytest.raises(ValueError, match="either an assessed area or geometry"):
        plug_slot(
            effective_area_mm2=1000,
            hole_shape="circular",
            hole_diameter_mm=40,
            hole_geometry_verified=True,
        )
    with pytest.raises(ValueError, match="cannot be less than its width"):
        plug_slot(
            hole_shape="round_ended_slot",
            slot_length_mm=19,
            slot_width_mm=20,
            hole_geometry_verified=True,
        )


def test_layout_and_hole_deduction():
    r = run_connections(
        {
            "check_type": "layout",
            "diameter_mm": 20,
            "thinnest_ply_mm": 10,
            "pitch_mm": 50,
            "edge_distance_mm": 35,
            "edge_type": "sheared",
            "pitch_case": "general",
        }
    )
    assert all(c["satisfied"] for c in r["checks"].values())
    r = run_connections(
        {
            "check_type": "hole_deduction",
            "gross_area_mm2": 2000,
            "thickness_mm": 10,
            "straight_hole_width_sum_mm": 22,
            "zigzag_hole_width_sum_mm": 44,
            "stagger_pairs": [[30, 50]],
        }
    )
    assert r["intermediate"]["net_area_mm2"] == pytest.approx(1605)


def test_hole_layout_searches_straight_and_all_progressive_zigzag_paths():
    result = run_connections(
        {
            "check_type": "hole_deduction_layout",
            "plate_width_mm": 200,
            "thickness_mm": 10,
            "flat_uniform_plate_and_complete_hole_layout_verified": True,
            "design_action_axis_verified": True,
            "holes": [
                {
                    "hole_id": "A",
                    "longitudinal_mm": 0,
                    "transverse_mm": 50,
                    "gross_hole_width_mm": 22,
                },
                {
                    "hole_id": "B",
                    "longitudinal_mm": 40,
                    "transverse_mm": 100,
                    "gross_hole_width_mm": 22,
                },
                {
                    "hole_id": "C",
                    "longitudinal_mm": 0,
                    "transverse_mm": 150,
                    "gross_hole_width_mm": 22,
                },
            ],
        }
    )

    result_data = result["intermediate"]
    assert result["checks"]["net_area"]["clause"] == "9.1.10.1; 9.1.10.2; 9.1.10.3"
    assert result_data["straight_path"]["hole_width_sum_mm"] == pytest.approx(44)
    assert result_data["zigzag_path"]["hole_ids"] == ["A", "B", "C"]
    assert [
        pair["correction_width_mm"] for pair in result_data["zigzag_path"]["stagger_pairs"]
    ] == pytest.approx([8, 8])
    assert result_data["zigzag_path"]["net_deduction_width_mm"] == pytest.approx(50)
    assert result_data["governing_path_type"] == "zigzag"
    assert result_data["deduction_mm2"] == pytest.approx(500)
    assert result_data["net_area_mm2"] == pytest.approx(1500)


def test_hole_layout_uses_the_maximum_straight_section_when_it_controls():
    result = run_connections(
        {
            "check_type": "hole_deduction_layout",
            "plate_width_mm": 200,
            "thickness_mm": 10,
            "flat_uniform_plate_and_complete_hole_layout_verified": True,
            "design_action_axis_verified": True,
            "holes": [
                {
                    "hole_id": hole_id,
                    "longitudinal_mm": 0,
                    "transverse_mm": transverse,
                    "gross_hole_width_mm": 22,
                }
                for hole_id, transverse in (("A", 50), ("B", 100), ("C", 150))
            ],
        }
    )

    assert result["intermediate"]["governing_path_type"] == "straight"
    assert result["intermediate"]["straight_path"]["hole_width_sum_mm"] == pytest.approx(66)
    assert result["intermediate"]["net_area_mm2"] == pytest.approx(1340)


def test_angle_hole_deduction_uses_figure_9_1_10_3_b_cross_leg_gauge():
    result = run_connections(
        {
            "check_type": "angle_hole_deduction",
            "gross_area_mm2": 4000,
            "thickness_mm": 10,
            "straight_hole_width_sum_mm": 25,
            "straight_hole_width_sum_verified": True,
            "angle_geometry_and_back_marks_verified": True,
            "candidate_paths_complete_and_ordered_verified": True,
            "candidate_paths": [
                {
                    "path_id": "opposite-legs",
                    "holes": [
                        {
                            "hole_id": "A",
                            "angle_leg_id": "leg_1",
                            "longitudinal_mm": 0,
                            "back_mark_mm": 20,
                            "gross_hole_width_mm": 20,
                        },
                        {
                            "hole_id": "B",
                            "angle_leg_id": "leg_2",
                            "longitudinal_mm": 40,
                            "back_mark_mm": 30,
                            "gross_hole_width_mm": 20,
                        },
                    ],
                },
                {
                    "path_id": "same-leg",
                    "holes": [
                        {
                            "hole_id": "C",
                            "angle_leg_id": "leg_1",
                            "longitudinal_mm": 0,
                            "back_mark_mm": 10,
                            "gross_hole_width_mm": 18,
                        },
                        {
                            "hole_id": "D",
                            "angle_leg_id": "leg_1",
                            "longitudinal_mm": 30,
                            "back_mark_mm": 40,
                            "gross_hole_width_mm": 18,
                        },
                    ],
                },
            ],
        }
    )

    result_data = result["intermediate"]
    cross_leg_path = result_data["candidate_paths"][0]
    same_leg_path = result_data["candidate_paths"][1]
    assert cross_leg_path["stagger_pairs"][0]["gauge_mm"] == pytest.approx(40)
    assert cross_leg_path["stagger_pairs"][0]["correction_width_mm"] == pytest.approx(10)
    assert same_leg_path["stagger_pairs"][0]["gauge_mm"] == pytest.approx(30)
    assert same_leg_path["stagger_pairs"][0]["correction_width_mm"] == pytest.approx(7.5)
    assert result_data["controlling_zigzag_path_id"] == "opposite-legs"
    assert result_data["governing_path_type"] == "zigzag"
    assert result_data["governing_deduction_width_mm"] == pytest.approx(30)
    assert result_data["deduction_mm2"] == pytest.approx(300)
    assert result_data["net_area_mm2"] == pytest.approx(3700)


def test_angle_hole_deduction_rejects_nonpositive_cross_leg_gauge():
    with pytest.raises(ValueError, match="Angle stagger gauges must be positive"):
        run_connections(
            {
                "check_type": "angle_hole_deduction",
                "gross_area_mm2": 4000,
                "thickness_mm": 10,
                "straight_hole_width_sum_mm": 20,
                "straight_hole_width_sum_verified": True,
                "angle_geometry_and_back_marks_verified": True,
                "candidate_paths_complete_and_ordered_verified": True,
                "candidate_paths": [
                    {
                        "path_id": "invalid-cross-leg-pair",
                        "holes": [
                            {
                                "hole_id": "A",
                                "angle_leg_id": "leg_1",
                                "longitudinal_mm": 0,
                                "back_mark_mm": 3,
                                "gross_hole_width_mm": 20,
                            },
                            {
                                "hole_id": "B",
                                "angle_leg_id": "leg_2",
                                "longitudinal_mm": 30,
                                "back_mark_mm": 5,
                                "gross_hole_width_mm": 20,
                            },
                        ],
                    }
                ],
            }
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {
                "holes": [
                    {
                        "hole_id": "A",
                        "longitudinal_mm": 0,
                        "transverse_mm": 50,
                        "gross_hole_width_mm": 20,
                    },
                    {
                        "hole_id": "A",
                        "longitudinal_mm": 10,
                        "transverse_mm": 100,
                        "gross_hole_width_mm": 20,
                    },
                ]
            },
            "Hole IDs must be unique",
        ),
        (
            {
                "holes": [
                    {
                        "hole_id": "A",
                        "longitudinal_mm": 0,
                        "transverse_mm": 50,
                        "gross_hole_width_mm": 20,
                    },
                    {
                        "hole_id": "B",
                        "longitudinal_mm": 0,
                        "transverse_mm": 50,
                        "gross_hole_width_mm": 20,
                    },
                ]
            },
            "Hole centre positions must be distinct",
        ),
        (
            {
                "holes": [
                    {
                        "hole_id": "A",
                        "longitudinal_mm": 0,
                        "transverse_mm": 5,
                        "gross_hole_width_mm": 20,
                    }
                ]
            },
            "must fit within the plate edges",
        ),
    ],
)
def test_hole_layout_rejects_inconsistent_geometry(changes, message):
    inputs = {
        "check_type": "hole_deduction_layout",
        "plate_width_mm": 200,
        "thickness_mm": 10,
        "flat_uniform_plate_and_complete_hole_layout_verified": True,
        "design_action_axis_verified": True,
        "holes": [
            {
                "hole_id": "A",
                "longitudinal_mm": 0,
                "transverse_mm": 50,
                "gross_hole_width_mm": 20,
            }
        ],
    }
    inputs.update(changes)

    with pytest.raises(ValueError, match=message):
        run_connections(inputs)


def test_bolt_group_vector_superposition_and_equilibrium():
    r = run_connections(
        bolt(
            check_type="bolt_group",
            shear_action_kn=0,
            tension_action_kn=0,
            points_mm=[[-50, -50], [50, -50], [50, 50], [-50, 50]],
            force_x_kn=40,
            force_y_kn=20,
            moment_z_knm=2,
        )
    )
    forces = r["intermediate"]["bolt_forces_kn"]
    assert forces[0] == [15, 0]
    assert sum(f[0] for f in forces) == pytest.approx(40)
    assert sum(f[1] for f in forces) == pytest.approx(20)
    points = [[-50, -50], [50, -50], [50, 50], [-50, 50]]
    assert sum(
        x * fy - y * fx for (x, y), (fx, fy) in zip(points, forces, strict=True)
    ) == pytest.approx(2000)


def test_clause_9_1_3_and_9_3_2_3_rigid_plate_bolt_group_distribution():
    result = run_connections(bolt_group_elastic_3d())
    assert result["checks"]["action_distribution_equilibrium"]["satisfied"]
    assert result["intermediate"]["distribution_method"] == (
        "rigid_plate_equal_stiffness_linear_elastic"
    )
    actions = result["intermediate"]["distributed_bolt_actions"]
    assert [
        [action["shear_x_kn"], action["shear_y_kn"], action["tension_action_kn"]]
        for action in actions
    ] == [[4, 17, 45], [16, 17, 5], [4, -7, 55], [16, -7, 15]]
    assert result["checks"]["bolts"][0]["total_bolt_tension_action_kn"] == 46
    assert result["intermediate"]["actions_resolved_from_bolts"] == pytest.approx(
        {
            "force_x_kn": 40,
            "force_y_kn": 20,
            "tension_kn": 120,
            "moment_x_knm": 2,
            "moment_y_knm": 1,
            "moment_z_knm": 3,
        }
    )


def test_elastic_3d_bolt_group_rejects_compression_and_singular_layouts():
    with pytest.raises(ValueError, match="bolt compression"):
        run_connections(bolt_group_elastic_3d(group_tension_kn=10, group_moment_x_knm=2))
    collinear = [
        {**item, "position_mm": [index * 50, 0]}
        for index, item in enumerate(bolt_group_elastic_3d()["bolt_layout"])
    ]
    with pytest.raises(ValueError, match="non-collinear"):
        run_connections(bolt_group_elastic_3d(bolt_layout=collinear))
    with pytest.raises(ValueError, match="not valid under any of the given schemas"):
        run_connections(bolt_group_elastic_3d(elastic_method_experimental_basis_verified=False))


def test_elastic_3d_bolt_actions_are_invariant_to_layout_origin_translation():
    base = run_connections(bolt_group_elastic_3d())
    translated_layout = [
        {
            **item,
            "position_mm": [item["position_mm"][0] + 800, item["position_mm"][1] - 350],
        }
        for item in bolt_group_elastic_3d()["bolt_layout"]
    ]
    translated = run_connections(bolt_group_elastic_3d(bolt_layout=translated_layout))
    base_actions = base["intermediate"]["distributed_bolt_actions"]
    translated_actions = translated["intermediate"]["distributed_bolt_actions"]
    assert translated["intermediate"]["centroid_mm"] == [800, -350]
    for first, second in zip(base_actions, translated_actions, strict=True):
        assert [first[key] for key in ("shear_x_kn", "shear_y_kn", "tension_action_kn")] == [
            second[key] for key in ("shear_x_kn", "shear_y_kn", "tension_action_kn")
        ]


def weld_group(**changes):
    return {
        "check_type": "weld_group",
        "weld_strength_mpa": 490,
        "throat_mm": 4,
        "quality": "SP",
        "segments_mm": [
            [[-50, -50], [50, -50]],
            [[50, -50], [50, 50]],
            [[50, 50], [-50, 50]],
            [[-50, 50], [-50, -50]],
        ],
        **{f"force_{a}_kn": 0 for a in "xyz"},
        **{f"moment_{a}_knm": 0 for a in "xyz"},
        **changes,
    }


def test_weld_group_pure_shear_and_bending():
    r = run_connections(weld_group(force_x_kn=40))
    assert r["checks"]["weld_group"]["utilisation"] == pytest.approx(0.1 / 0.9408)
    r = run_connections(weld_group(moment_x_knm=2, moment_y_knm=1))
    assert r["intermediate"]["ix_mm3"] == pytest.approx(2e6 / 3)
    assert max(abs(f[2]) for f in r["intermediate"]["endpoint_forces_kn_per_mm"]) == pytest.approx(
        0.225
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"ultimate_strength_mpa": float("nan")},
        {"lap_length_mm": float("inf")},
        {"filler_thickness_mm": 20},
        {"filler_thickness_by_shear_plane_mm": [20]},
        {"threaded_planes": 0, "plain_planes": 0},
        {"threaded_planes": True},
        {"unknown": 1},
        {"tensile_area_mm2": 100},
    ],
)
def test_reject_invalid_bolts(changes):
    with pytest.raises(ValueError):
        run_connections(bolt(**changes))


def test_reject_degenerate_group():
    with pytest.raises(ValueError):
        run_connections(weld_group(segments_mm=[[[0, 0], [100, 0]]], moment_x_knm=1))


def test_reject_overlapping_welds():
    with pytest.raises(ValueError, match="overlap"):
        run_connections(weld_group(segments_mm=[[[0, 0], [100, 0]], [[50, 0], [150, 0]]]))


def test_reject_numeric_overflow():
    with pytest.raises(ValueError):
        run_connections(bolt(shank_area_mm2=1e308, plain_planes=2))


def test_reject_yield_strength_above_as4100_scope():
    data = {
        "check_type": "pin",
        "yield_strength_mpa": 690,
        "diameter_mm": 30,
        "shear_planes": 2,
        "ply_thickness_mm": 10,
        "rotates": True,
        "shear_action_kn": 100,
        "bearing_action_kn": 40,
        "moment_action_knm": 1,
    }
    assert run_connections(data)["checks"]["shear"]["satisfied"]
    with pytest.raises(ValueError, match="690 MPa"):
        run_connections({**data, "yield_strength_mpa": 690.1})


def test_packing_construction_thin_and_extended_routes():
    data = {
        "check_type": "packing_construction",
        "packing_thickness_mm": 5.99,
        "too_thin_for_adequate_welds": False,
        "too_thin_to_prevent_buckling": False,
        "required_edge_weld_sizes_mm": [4, 5],
        "provided_edge_weld_sizes_mm": [10, 11],
        "trimmed_flush_with_member_edges": True,
        "extends_beyond_member_edges": False,
        "welded_to_fitted_piece": False,
    }
    result = run_connections(data)
    assert result["intermediate"]["flush_required"]
    assert result["checks"]["edge_weld_sizes"]["required_mm"] == pytest.approx([9.99, 10.99])
    assert result["checks"]["edge_weld_sizes"]["satisfied"]
    data["provided_edge_weld_sizes_mm"][0] = 9.98
    assert not run_connections(data)["checks"]["edge_weld_sizes"]["satisfied"]
    data.update(
        packing_thickness_mm=6,
        too_thin_to_prevent_buckling=True,
        provided_edge_weld_sizes_mm=[10, 11],
        trimmed_flush_with_member_edges=False,
    )
    assert not run_connections(data)["checks"]["trimmed_flush"]["satisfied"]
    data.update(
        too_thin_to_prevent_buckling=False,
        extends_beyond_member_edges=True,
        welded_to_fitted_piece=True,
    )
    result = run_connections(data)
    assert not result["intermediate"]["flush_required"]
    assert result["checks"]["extends_beyond_edges"]["satisfied"]
    assert result["checks"]["welded_to_fitted_piece"]["satisfied"]
    data["extends_beyond_member_edges"] = False
    assert not run_connections(data)["checks"]["extends_beyond_edges"]["satisfied"]
