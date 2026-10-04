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
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": (
                case == "compression_not_full_contact"
            ),
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
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": False,
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
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": False,
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
                "splice_parts_and_fasteners_hold_all_parts_in_line_verified": False,
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


@pytest.mark.parametrize(
    "length,expected", [(299, 1), (300, 1), (800, 0.875), (1300, 0.75), (1301, 0.75)]
)
def test_lap_boundaries(length, expected):
    assert run_connections(bolt(lap_length_mm=length))["intermediate"][
        "lap_factor"
    ] == pytest.approx(expected)


def test_grade_filler_and_plain_planes():
    r = run_connections(bolt(grade="10.9", filler_thickness_mm=10))
    assert r["checks"]["shear"]["design_capacity_kn"] == pytest.approx(92.628 * 0.83 * 0.9384)
    r = run_connections(bolt(grade="10.9", threaded_planes=0, plain_planes=2))
    assert r["intermediate"]["ductility_factor"] == 1
    assert r["checks"]["shear"]["design_capacity_kn"] == pytest.approx(
        0.8 * 0.62 * 830 * 628 / 1000
    )


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


def test_plug_slot():
    r = run_connections(
        {
            "check_type": "plug_slot",
            "weld_strength_mpa": 490,
            "effective_area_mm2": 1000,
            "quality": "SP",
            "permitted_shear_application": True,
            "action_kn": 200,
        }
    )
    assert r["checks"]["weld"]["design_capacity_kn"] == pytest.approx(235.2)


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
