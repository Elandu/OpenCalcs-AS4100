# SPDX-License-Identifier: AGPL-3.0-only
from math import pi

import pytest

from opencalcs_as4100.design_actions import run_design_actions as run


def test_euler_pin_ended_hand_benchmark():
    r = run(
        {
            "operation": "euler_buckling",
            "elastic_modulus_mpa": 200000,
            "second_moment_mm4": 8e6,
            "member_length_mm": 4000,
            "effective_length_factor": 1,
        }
    )
    assert r["values"]["elastic_buckling_load_kn"] == pytest.approx(100 * pi * pi)


def test_euler_buckling_uses_clause_2_2_4_elastic_modulus():
    with pytest.raises(ValueError, match="elastic_modulus_mpa"):
        run(
            {
                "operation": "euler_buckling",
                "elastic_modulus_mpa": 199000,
                "second_moment_mm4": 8e6,
                "member_length_mm": 4000,
                "effective_length_factor": 1,
            }
        )


@pytest.mark.parametrize(
    ("end_restraint_case", "expected_factor"),
    [
        ("braced_fixed_fixed", 0.7),
        ("braced_top_pinned_bottom_fixed", 0.85),
        ("braced_pinned_pinned", 1.0),
        ("sway_top_fixed_bottom_fixed", 1.2),
        ("sway_top_free_bottom_fixed", 2.2),
        ("sway_top_fixed_bottom_pinned", 2.2),
    ],
)
def test_idealized_end_restraint_cases_feed_euler_buckling(end_restraint_case, expected_factor):
    r = run(
        {
            "operation": "idealized_member_buckling",
            "second_moment_mm4": 8e6,
            "member_length_mm": 4000,
            "idealized_end_restraint_case": end_restraint_case,
            "idealized_end_restraint_verified": True,
            "end_restraint_evidence_reference": "FIGURE-4-6-3-2-REVIEW",
            "member_length_centre_to_centre_verified": True,
            "member_length_evidence_reference": "MEMBER-GEOMETRY-01",
        }
    )
    values = r["values"]
    assert r["checked_conditions_satisfied"]
    assert values["effective_length_factor"] == expected_factor
    assert values["effective_length_mm"] == expected_factor * 4000
    assert values["elastic_buckling_load_kn"] == pytest.approx(
        pi**2 * 200000 * 8e6 / (expected_factor * 4000) ** 2 / 1000
    )
    assert r["clauses"] == ["4.6.2", "4.6.3.2"]
    assert r["full_standard_compliance"] is False


def test_idealized_member_buckling_requires_verified_case_and_member_length():
    inputs = {
        "operation": "idealized_member_buckling",
        "second_moment_mm4": 8e6,
        "member_length_mm": 4000,
        "idealized_end_restraint_case": "braced_fixed_fixed",
        "idealized_end_restraint_verified": False,
        "end_restraint_evidence_reference": "RESTRAINT-REVIEW-01",
        "member_length_centre_to_centre_verified": False,
        "member_length_evidence_reference": "MEMBER-MEASURE-01",
    }
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert r["values"]["elastic_buckling_load_kn"] > 0
    assert not r["checks"][0]["satisfied"]
    assert not r["checks"][1]["satisfied"]

    inputs["idealized_end_restraint_case"] = "unlisted_case"
    with pytest.raises(ValueError):
        run(inputs)


def rectangular_frame_stiffness_ratio(**overrides):
    inputs = {
        "operation": "rectangular_frame_stiffness_ratio",
        "frame_type": "braced",
        "member_under_consideration_id": "COL-01",
        "compression_members": [
            {
                "member_id": "COL-01",
                "second_moment_mm4": 8e6,
                "member_length_mm": 4000,
                "rigid_connection_at_joint_verified": True,
                "stiffness_evidence_reference": "COL-01-SECTION-01",
            },
            {
                "member_id": "COL-02",
                "second_moment_mm4": 12e6,
                "member_length_mm": 6000,
                "rigid_connection_at_joint_verified": True,
                "stiffness_evidence_reference": "COL-02-SECTION-01",
            },
        ],
        "compression_members_at_joint_complete_verified": True,
        "compression_members_evidence_reference": "JOINT-COLUMNS-01",
        "beams": [
            {
                "beam_id": "BEAM-01",
                "second_moment_mm4": 10e6,
                "member_length_mm": 5000,
                "near_end_rigid_connection_verified": True,
                "far_end_fixity": "pinned",
                "far_end_fixity_verified": True,
                "stiffness_evidence_reference": "BEAM-01-SECTION-01",
            },
            {
                "beam_id": "BEAM-02",
                "second_moment_mm4": 6e6,
                "member_length_mm": 3000,
                "near_end_rigid_connection_verified": True,
                "far_end_fixity": "rigidly_connected_to_column",
                "far_end_fixity_verified": True,
                "stiffness_evidence_reference": "BEAM-02-SECTION-01",
            },
        ],
        "beams_at_joint_complete_verified": True,
        "beams_evidence_reference": "JOINT-BEAMS-01",
        "rectangular_frame_geometry_verified": True,
        "regular_loading_verified": True,
        "beam_axial_forces_negligible_verified": True,
        "frame_assessment_evidence_reference": "FRAME-ANALYSIS-BASIS-01",
        "column_base_condition": "not_column_base",
        "column_base_condition_verified": True,
        "column_base_evidence_reference": "COLUMN-BASE-SCHEDULE-01",
    }
    inputs.update(overrides)
    return inputs


def test_rectangular_frame_stiffness_ratio_hand_benchmark():
    r = run(rectangular_frame_stiffness_ratio())
    values = r["values"]
    assert r["checked_conditions_satisfied"]
    assert r["clauses"] == ["4.6.3.4", "Table 4.6.3.4"]
    assert values["compression_stiffness_sum_mm3"] == 4000
    assert values["weighted_beam_stiffness_sum_mm3"] == 5000
    assert values["stiffness_ratio_at_end_gamma"] == pytest.approx(0.8)
    assert [beam["beta_e"] for beam in values["beams"]] == [1.5, 1.0]
    assert [beam["weighted_stiffness_mm3"] for beam in values["beams"]] == [3000, 2000]
    assert r["full_standard_compliance"] is False


@pytest.mark.parametrize(
    ("frame_type", "far_end_fixity", "expected_beta"),
    [
        ("braced", "pinned", 1.5),
        ("braced", "rigidly_connected_to_column", 1.0),
        ("braced", "fixed", 2.0),
        ("sway", "pinned", 0.5),
        ("sway", "rigidly_connected_to_column", 1.0),
        ("sway", "fixed", 0.67),
    ],
)
def test_rectangular_frame_stiffness_ratio_table_modifiers(
    frame_type, far_end_fixity, expected_beta
):
    inputs = rectangular_frame_stiffness_ratio(frame_type=frame_type)
    inputs["beams"][0]["far_end_fixity"] = far_end_fixity
    r = run(inputs)
    assert r["values"]["beams"][0]["beta_e"] == expected_beta


def test_rectangular_frame_stiffness_ratio_base_minimum_and_evidence_gates():
    inputs = rectangular_frame_stiffness_ratio(column_base_condition="rigidly_connected_to_footing")
    r = run(inputs)
    assert r["values"]["minimum_gamma"] == 0.6
    assert r["values"]["minimum_gamma_satisfied"]
    assert r["checked_conditions_satisfied"]

    inputs = rectangular_frame_stiffness_ratio(
        column_base_condition="not_rigidly_connected_to_footing"
    )
    r = run(inputs)
    assert r["values"]["minimum_gamma"] == 10
    assert not r["values"]["minimum_gamma_satisfied"]
    assert not r["checked_conditions_satisfied"]

    inputs = rectangular_frame_stiffness_ratio(
        rectangular_frame_geometry_verified=False,
        regular_loading_verified=False,
        beam_axial_forces_negligible_verified=False,
        compression_members_at_joint_complete_verified=False,
        beams_at_joint_complete_verified=False,
        column_base_condition_verified=False,
    )
    r = run(inputs)
    assert r["values"]["stiffness_ratio_at_end_gamma"] == pytest.approx(0.8)
    assert not r["checked_conditions_satisfied"]


def test_rectangular_frame_stiffness_ratio_requires_unique_target_and_far_end_evidence():
    inputs = rectangular_frame_stiffness_ratio()
    inputs["compression_members"][1]["member_id"] = "COL-01"
    inputs["beams"][0]["far_end_fixity_verified"] = False
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert not r["checks"][6]["satisfied"]
    assert not r["checks"][-1]["satisfied"]


def test_moment_amplification_and_instability_gate():
    d = {
        "operation": "moment_amplification",
        "compression_kn": 500,
        "elastic_buckling_load_kn": 1000,
        "beta_m": -1,
        "first_order_moment_knm": -10,
    }
    r = run(d)
    assert r["values"]["governing_factor"] == 2
    assert r["values"]["amplified_moment_knm"] == -20
    assert r["values"]["second_order_analysis_required"]
    assert not r["checked_conditions_satisfied"]
    d["compression_kn"] = 1000
    with pytest.raises(ValueError):
        run(d)


def test_reverse_curvature_factor_floored_to_one():
    r = run(
        {
            "operation": "moment_amplification",
            "compression_kn": 100,
            "elastic_buckling_load_kn": 1000,
            "beta_m": 1,
            "first_order_moment_knm": 10,
        }
    )
    assert r["values"]["cm"] == pytest.approx(0.2)
    assert r["values"]["braced_factor"] == 1


def test_rectangular_storey_hand_benchmark():
    r = run(
        {
            "operation": "storey_sway_amplification",
            "storey_displacement_mm": 10,
            "storey_height_mm": 4000,
            "total_compression_kn": 1000,
            "total_storey_shear_kn": 100,
        }
    )
    assert r["values"]["sway_factor"] == pytest.approx(40 / 39)


@pytest.mark.parametrize("factor,amp", [(4, None), (5, 1.125), (10, 1)])
def test_plastic_analysis_boundaries(factor, amp):
    r = run(
        {
            "operation": "plastic_amplification",
            "frame_buckling_factor": factor,
            "first_order_action": 100,
        }
    )
    assert r["values"]["amplification_factor"] == amp
    assert r["checked_conditions_satisfied"] is (factor >= 5)


def plastic_analysis_limits(**material_changes):
    material = {
        "material_id": "G350-PLATE",
        "material_standard": "AS/NZS 3678",
        "material_standard_verified": True,
        "specified_yield_strength_mpa": 450,
        "specified_tensile_strength_mpa": 540,
        "yield_plateau_extension_in_yield_strains": 6,
        "elongation_percent": 15,
        "elongation_test_to_as1391_verified": True,
        "strain_hardening_capability_verified": True,
        "stress_strain_data_verified": True,
        "evidence_reference": "MATERIAL-CERT-01",
    }
    material.update(material_changes)
    member = {
        "member_id": "M1",
        "hot_formed": True,
        "hot_formed_status_verified": True,
        "section_form": "doubly_symmetric_i_section",
        "section_form_verified": True,
        "compact_under_clause_5_2_3": True,
        "compactness_assessment_verified": True,
        "impact_loading_present": False,
        "impact_loading_assessment_verified": True,
        "fatigue_assessment_required": False,
        "fatigue_loading_assessment_verified": True,
        "evidence_reference": "MEMBER-REVIEW-01",
    }
    return {
        "operation": "plastic_analysis_limits",
        "materials": [material],
        "members": [member],
    }


def test_plastic_analysis_prescriptive_limit_boundaries():
    r = run(plastic_analysis_limits())
    assert r["checked_conditions_satisfied"]
    assert r["values"]["prescriptive_4_5_2_conditions_satisfied"]
    assert r["values"]["materials"][0]["tensile_to_yield_strength_ratio"] == pytest.approx(1.2)
    assert {check["clause"] for check in r["checks"]} == {
        "4.5.2(a)",
        "4.5.2(b)",
        "4.5.2(b)(i)",
        "4.5.2(b)(ii)",
        "4.5.2(b)(iii)",
        "4.5.2(b)(iv)",
        "4.5.2(c)",
        "4.5.2(d)",
        "4.5.2(e)",
        "4.5.2(f)",
    }
    assert r["full_standard_compliance"] is False


@pytest.mark.parametrize(
    "changes,clause",
    [
        ({"specified_yield_strength_mpa": 450.001}, "4.5.2(a)"),
        ({"yield_plateau_extension_in_yield_strains": 5.999}, "4.5.2(b)(i)"),
        ({"specified_tensile_strength_mpa": 539.999}, "4.5.2(b)(ii)"),
        ({"elongation_percent": 14.999}, "4.5.2(b)(iii)"),
        ({"elongation_test_to_as1391_verified": False}, "4.5.2(b)(iii)"),
        ({"strain_hardening_capability_verified": False}, "4.5.2(b)(iv)"),
    ],
)
def test_plastic_analysis_material_limit_failures(changes, clause):
    r = run(plastic_analysis_limits(**changes))
    assert not r["checked_conditions_satisfied"]
    assert not next(check for check in r["checks"] if check["clause"] == clause)["satisfied"]


@pytest.mark.parametrize(
    "changes,clause",
    [
        ({"hot_formed": False}, "4.5.2(c)"),
        ({"hot_formed_status_verified": False}, "4.5.2(c)"),
        ({"section_form": "other"}, "4.5.2(d)"),
        ({"section_form_verified": False}, "4.5.2(d)"),
        ({"compact_under_clause_5_2_3": False}, "4.5.2(e)"),
        ({"compactness_assessment_verified": False}, "4.5.2(e)"),
        ({"impact_loading_present": True}, "4.5.2(f)"),
        ({"fatigue_assessment_required": True}, "4.5.2(f)"),
        ({"impact_loading_assessment_verified": False}, "4.5.2(f)"),
        ({"fatigue_loading_assessment_verified": False}, "4.5.2(f)"),
    ],
)
def test_plastic_analysis_member_limit_failures(changes, clause):
    inputs = plastic_analysis_limits()
    inputs["members"][0].update(changes)
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert not next(check for check in r["checks"] if check["clause"] == clause)["satisfied"]


def test_plastic_analysis_requires_complete_material_and_member_evidence():
    inputs = plastic_analysis_limits()
    inputs["materials"].append(
        {
            **inputs["materials"][0],
            "material_id": "G300-PLATE",
            "specified_yield_strength_mpa": 460,
        }
    )
    inputs["members"].append({**inputs["members"][0], "member_id": "M2", "hot_formed": False})
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert not r["values"]["materials"][1]["checks_satisfied"]
    assert not r["values"]["members"][1]["checks_satisfied"]


def plastic_analysis_connections(connection_changes=None, hinge_changes=None, **root_changes):
    connection = {
        "connection_id": "C1",
        "strength_type": "full_strength",
        "connection_design_moment_capacity_knm": 100,
        "connected_member_design_moment_capacity_knm": 100,
        "connection_capacity_used_in_analysis_verified": True,
        "all_required_plastic_hinges_develop_verified": True,
        "evidence_reference": "CONNECTION-REVIEW-01",
    }
    connection.update(connection_changes or {})
    hinge = {
        "hinge_id": "H1",
        "location_type": "member",
        "rotation_demand_rad": 0.025,
        "rotation_capacity_rad": 0.025,
        "rotation_demand_assessment_verified": True,
        "rotation_capacity_assessment_verified": True,
        "evidence_reference": "HINGE-REVIEW-01",
    }
    hinge.update(hinge_changes or {})
    inputs = {
        "operation": "plastic_analysis_connections",
        "rigid_plastic_analysis_verified": True,
        "all_assumed_connections_listed_verified": True,
        "all_collapse_mechanism_hinges_listed_verified": True,
        "analysis_evidence_reference": "PLASTIC-ANALYSIS-01",
        "connections": [connection],
        "plastic_hinges": [hinge],
    }
    inputs.update(root_changes)
    return inputs


def test_plastic_analysis_connection_and_hinge_capacity_boundaries():
    r = run(plastic_analysis_connections())
    assert r["checked_conditions_satisfied"]
    assert r["values"]["connections"][0]["capacity_ratio"] == 1
    assert r["values"]["plastic_hinges"][0]["rotation_demand_to_capacity_ratio"] == 1

    partial = run(
        plastic_analysis_connections(
            {
                "strength_type": "partial_strength",
                "connection_design_moment_capacity_knm": 80,
                "all_required_plastic_hinges_develop_verified": True,
            }
        )
    )
    assert partial["checked_conditions_satisfied"]
    assert partial["values"]["connections"][0]["capacity_ratio"] == 0.8
    assert partial["full_standard_compliance"] is False


def test_plastic_analysis_hinge_rotation_capacity_must_be_positive():
    inputs = plastic_analysis_connections(hinge_changes={"rotation_capacity_rad": 0})
    with pytest.raises(ValueError, match="rotation_capacity_rad"):
        run(inputs)


@pytest.mark.parametrize(
    "connection_changes,hinge_changes,root_changes,clause",
    [
        ({"connection_design_moment_capacity_knm": 99.999}, None, {}, "4.5.3(a)"),
        (
            {
                "strength_type": "partial_strength",
                "connection_design_moment_capacity_knm": 80,
                "all_required_plastic_hinges_develop_verified": False,
            },
            None,
            {},
            "4.5.3(b)",
        ),
        ({"connection_capacity_used_in_analysis_verified": False}, None, {}, "4.5.3"),
        (None, {"rotation_capacity_rad": 0.024999}, {}, "4.5.3(a)/(b)"),
        (None, {"rotation_demand_assessment_verified": False}, {}, "4.5.3(a)/(b)"),
        (None, {"rotation_capacity_assessment_verified": False}, {}, "4.5.3(a)/(b)"),
        (None, None, {"rigid_plastic_analysis_verified": False}, "4.5.3"),
        (None, None, {"all_assumed_connections_listed_verified": False}, "4.5.3"),
        (None, None, {"all_collapse_mechanism_hinges_listed_verified": False}, "4.5.3(a)/(b)"),
    ],
)
def test_plastic_analysis_connection_and_hinge_failures(
    connection_changes, hinge_changes, root_changes, clause
):
    r = run(
        plastic_analysis_connections(
            connection_changes,
            hinge_changes,
            **root_changes,
        )
    )
    assert not r["checked_conditions_satisfied"]
    assert any(check["clause"] == clause and not check["satisfied"] for check in r["checks"])


def plastic_alternative_ductility_assessment(**overrides):
    component = {
        "rotation_demand_rad": 0.018,
        "rotation_capacity_rad": 0.02,
        "rotation_demand_assessment_verified": True,
        "rotation_capacity_assessment_verified": True,
        "evidence_reference": "ROTATION-ASSESSMENT-01",
    }
    inputs = {
        "operation": "plastic_alternative_ductility_assessment",
        "members": [
            {**component, "component_id": "MEMBER-01"},
            {
                **component,
                "component_id": "MEMBER-02",
                "rotation_demand_rad": 0.025,
                "rotation_capacity_rad": 0.025,
            },
        ],
        "connections": [
            {
                **component,
                "component_id": "CONNECTION-01",
                "rotation_demand_rad": 0.0125,
                "rotation_capacity_rad": 0.015,
            }
        ],
        "all_members_listed_verified": True,
        "member_list_evidence_reference": "MEMBER-LIST-01",
        "all_connections_listed_verified": True,
        "connection_list_evidence_reference": "CONNECTION-LIST-01",
        "structure_ductility_assessment_verified": True,
        "structure_ductility_evidence_reference": "STRUCTURE-DUCTILITY-01",
        "analysis_under_design_loading_verified": True,
        "analysis_evidence_reference": "PLASTIC-ANALYSIS-01",
    }
    inputs.update(overrides)
    return inputs


def test_plastic_alternative_ductility_rotation_boundaries():
    r = run(plastic_alternative_ductility_assessment())
    assert r["checked_conditions_satisfied"]
    assert r["values"]["all_component_rotation_conditions_satisfied"]
    assert [
        item["rotation_demand_to_capacity_ratio"] for item in r["values"]["members"]
    ] == pytest.approx([0.9, 1.0])
    assert r["values"]["connections"][0]["rotation_demand_to_capacity_ratio"] == pytest.approx(
        5 / 6
    )
    assert r["full_standard_compliance"] is False


def test_plastic_alternative_ductility_failures_and_evidence_gates():
    inputs = plastic_alternative_ductility_assessment()
    inputs["members"][0]["rotation_demand_rad"] = 0.0201
    inputs["connections"][0]["rotation_capacity_assessment_verified"] = False
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert not r["checks"][0]["satisfied"]
    assert not r["checks"][4]["satisfied"]

    inputs = plastic_alternative_ductility_assessment()
    inputs["all_members_listed_verified"] = False
    inputs["all_connections_listed_verified"] = False
    inputs["structure_ductility_assessment_verified"] = False
    inputs["analysis_under_design_loading_verified"] = False
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert r["values"]["all_component_rotation_conditions_satisfied"]
    assert not r["checks"][3]["satisfied"]
    assert not r["checks"][6]["satisfied"]
    assert not r["checks"][7]["satisfied"]
    assert not r["checks"][8]["satisfied"]


def plastic_global_equilibrium(**overrides):
    actions = [
        {
            "action_id": "LOAD-1",
            "action_type": "applied_load",
            "force_kn": [0, -100, 0],
            "moment_knm": [0, 0, 0],
            "position_mm": [2000, 0, 0],
            "evidence_reference": "LOADS-01",
        },
        {
            "action_id": "REACTION-1",
            "action_type": "support_reaction",
            "force_kn": [0, 50, 0],
            "moment_knm": [0, 0, 0],
            "position_mm": [0, 0, 0],
            "evidence_reference": "REACTIONS-01",
        },
        {
            "action_id": "REACTION-2",
            "action_type": "support_reaction",
            "force_kn": [0, 50, 0],
            "moment_knm": [0, 0, 0],
            "position_mm": [4000, 0, 0],
            "evidence_reference": "REACTIONS-02",
        },
    ]
    inputs = {
        "operation": "plastic_global_equilibrium",
        "actions": actions,
        "force_tolerance_kn": 0,
        "moment_tolerance_knm": 0,
        "boundary_conditions_verified": True,
        "boundary_conditions_evidence_reference": "SUPPORTS-01",
    }
    inputs.update(overrides)
    return inputs


def test_plastic_global_equilibrium_force_and_moment_hand_benchmark():
    r = run(plastic_global_equilibrium())
    assert r["checked_conditions_satisfied"]
    assert r["values"]["force_resultant_kn"] == [0, 0, 0]
    assert r["values"]["moment_resultant_knm"] == [0, 0, 0]
    assert r["values"]["action_counts"] == {"applied_load": 1, "support_reaction": 2}
    assert r["full_standard_compliance"] is False


def test_plastic_global_equilibrium_tolerance_is_inclusive():
    inputs = plastic_global_equilibrium(force_tolerance_kn=1, moment_tolerance_knm=4)
    inputs["actions"][2]["force_kn"] = [0, 49, 0]
    r = run(inputs)
    assert r["checked_conditions_satisfied"]
    assert r["values"]["force_resultant_kn"] == [0, -1, 0]
    assert r["values"]["moment_resultant_knm"] == [0, 0, -4]


def test_plastic_global_equilibrium_checks_moments_and_boundary_evidence():
    inputs = plastic_global_equilibrium(moment_tolerance_knm=0.499)
    inputs["actions"][2]["position_mm"] = [3990, 0, 0]
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert r["checks"][0]["satisfied"]
    assert not r["checks"][1]["satisfied"]

    inputs = plastic_global_equilibrium(boundary_conditions_verified=False)
    r = run(inputs)
    assert r["values"]["global_equilibrium_satisfied"]
    assert not r["checked_conditions_satisfied"]
    assert not r["checks"][2]["satisfied"]

    inputs = plastic_global_equilibrium()
    inputs["actions"] = [{**inputs["actions"][0], "force_kn": [0, 0, 0]}]
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert r["values"]["global_equilibrium_satisfied"] is False
    assert not r["checks"][3]["satisfied"]


def plastic_joint_equilibrium(**overrides):
    inputs = {
        "operation": "plastic_joint_equilibrium",
        "joints": [
            {
                "joint_id": "JOINT-01",
                "actions": [
                    {
                        "action_id": "MEMBER-END-01",
                        "action_type": "member_end_action",
                        "force_kn": [0, 2, 3],
                        "moment_knm": [0, 0, 0],
                        "position_offset_mm": [1000, 0, 0],
                        "evidence_reference": "MEMBER-END-01-ACTIONS",
                    },
                    {
                        "action_id": "MEMBER-END-02",
                        "action_type": "member_end_action",
                        "force_kn": [4, 0, -3],
                        "moment_knm": [0, 0, 0],
                        "position_offset_mm": [0, 1000, 0],
                        "evidence_reference": "MEMBER-END-02-ACTIONS",
                    },
                    {
                        "action_id": "LOAD-01",
                        "action_type": "applied_load",
                        "force_kn": [-4, -2, 0],
                        "moment_knm": [3, 3, 2],
                        "position_offset_mm": [0, 0, 0],
                        "evidence_reference": "NODE-LOAD-01",
                    },
                ],
                "joint_actions_complete_verified": True,
                "joint_actions_evidence_reference": "JOINT-01-ACTION-LIST",
            }
        ],
        "force_tolerance_kn": 0,
        "moment_tolerance_knm": 0,
    }
    inputs.update(overrides)
    return inputs


def test_plastic_joint_equilibrium_three_axis_hand_benchmark():
    r = run(plastic_joint_equilibrium())
    assert r["checked_conditions_satisfied"]
    assert r["values"]["all_joint_equilibria_satisfied"]
    assert r["values"]["joints"][0]["force_resultant_kn"] == [0, 0, 0]
    assert r["values"]["joints"][0]["moment_resultant_knm"] == [0, 0, 0]
    assert r["full_standard_compliance"] is False


def test_plastic_joint_equilibrium_inclusive_tolerance_and_evidence_gates():
    inputs = plastic_joint_equilibrium(moment_tolerance_knm=0.5)
    inputs["joints"][0]["actions"][2]["moment_knm"] = [3, 3, 1.5]
    r = run(inputs)
    assert r["checked_conditions_satisfied"]
    assert r["values"]["joints"][0]["moment_resultant_knm"] == [0, 0, -0.5]

    inputs = plastic_joint_equilibrium()
    inputs["joints"][0]["joint_actions_complete_verified"] = False
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert r["values"]["all_joint_equilibria_satisfied"]
    assert not r["checks"][3]["satisfied"]

    inputs = plastic_joint_equilibrium()
    for action in inputs["joints"][0]["actions"]:
        action["action_type"] = "applied_load"
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert r["values"]["all_joint_equilibria_satisfied"]
    assert not r["checks"][2]["satisfied"]


def plastic_member_span_equilibrium(**overrides):
    inputs = {
        "operation": "plastic_member_span_equilibrium",
        "members": [
            {
                "member_id": "BEAM-01",
                "member_vector_mm": [4000, 0, 0],
                "member_geometry_verified": True,
                "member_geometry_evidence_reference": "BEAM-01-MODEL",
                "start_end_force_kn": [0, 20, -7.5],
                "start_end_moment_knm": [0, 0, 0],
                "start_end_evidence_reference": "BEAM-01-START-ACTIONS",
                "end_end_force_kn": [0, 20, -7.5],
                "end_end_moment_knm": [-1, 2, -3],
                "end_end_evidence_reference": "BEAM-01-END-ACTIONS",
                "span_actions": [
                    {
                        "action_id": "UDL-01",
                        "force_kn": [0, -40, 15],
                        "moment_knm": [0, 0, 0],
                        "position_offset_mm": [2000, 0, 0],
                        "evidence_reference": "BEAM-01-LOAD-RESULTANT",
                    },
                    {
                        "action_id": "COUPLE-01",
                        "force_kn": [0, 0, 0],
                        "moment_knm": [1, -2, 3],
                        "position_offset_mm": [2000, 0, 0],
                        "evidence_reference": "BEAM-01-APPLIED-COUPLE",
                    },
                ],
                "span_actions_complete_verified": True,
                "span_actions_evidence_reference": "BEAM-01-LOAD-REGISTER",
            }
        ],
        "force_tolerance_kn": 0,
        "moment_tolerance_knm": 0,
        "all_members_listed_verified": True,
        "member_list_evidence_reference": "MODEL-MEMBER-LIST",
    }
    inputs.update(overrides)
    return inputs


def test_plastic_member_span_equilibrium_three_axis_hand_benchmark():
    r = run(plastic_member_span_equilibrium())
    member = r["values"]["members"][0]
    assert r["checked_conditions_satisfied"]
    assert r["values"]["all_member_equilibria_satisfied"]
    assert member["force_resultant_kn"] == [0, 0, 0]
    assert member["moment_resultant_about_start_knm"] == [0, 0, 0]
    assert member["span_action_count"] == 2
    assert r["full_standard_compliance"] is False


def test_plastic_member_span_equilibrium_residuals_tolerances_and_evidence():
    inputs = plastic_member_span_equilibrium(force_tolerance_kn=1, moment_tolerance_knm=2)
    inputs["members"][0]["end_end_force_kn"] = [0, 19, -7.5]
    inputs["members"][0]["end_end_moment_knm"] = [-1, 2, -1]
    inputs["members"][0]["span_actions"][1]["moment_knm"] = [1, -2, 3]
    r = run(inputs)
    assert r["checked_conditions_satisfied"]
    assert r["values"]["members"][0]["force_resultant_kn"] == [0, -1, 0]
    assert r["values"]["members"][0]["moment_resultant_about_start_knm"] == [0, 0, -2]

    inputs = plastic_member_span_equilibrium()
    inputs["members"][0]["span_actions_complete_verified"] = False
    inputs["members"][0]["member_geometry_verified"] = False
    inputs["all_members_listed_verified"] = False
    r = run(inputs)
    assert r["values"]["all_member_equilibria_satisfied"]
    assert not r["checked_conditions_satisfied"]
    assert not r["checks"][2]["satisfied"]
    assert not r["checks"][3]["satisfied"]
    assert not r["checks"][-1]["satisfied"]


def test_plastic_member_span_equilibrium_rejects_zero_length_and_duplicate_identifiers():
    inputs = plastic_member_span_equilibrium()
    inputs["members"][0]["member_vector_mm"] = [0, 0, 0]
    with pytest.raises(ValueError, match="nonzero length"):
        run(inputs)

    inputs = plastic_member_span_equilibrium()
    inputs["members"].append(dict(inputs["members"][0]))
    r = run(inputs)
    assert not r["values"]["unique_member_identifiers"]
    assert not r["checked_conditions_satisfied"]


def plastic_support_boundary_conditions(**overrides):
    inputs = {
        "operation": "plastic_support_boundary_conditions",
        "supports": [
            {
                "support_id": "SUPPORT-01",
                "constraints": [
                    {
                        "dof": "ux",
                        "prescribed_translation_mm": 0,
                        "calculated_translation_mm": 0.01,
                        "tolerance_mm": 0.01,
                        "analysis_result_evidence_reference": "SUPPORT-01-UX-RESULT",
                    },
                    {
                        "dof": "uy",
                        "prescribed_translation_mm": 0,
                        "calculated_translation_mm": 0,
                        "tolerance_mm": 0,
                        "analysis_result_evidence_reference": "SUPPORT-01-UY-RESULT",
                    },
                    {
                        "dof": "rz",
                        "prescribed_rotation_rad": 0,
                        "calculated_rotation_rad": 0.001,
                        "tolerance_rad": 0.001,
                        "analysis_result_evidence_reference": "SUPPORT-01-RZ-RESULT",
                    },
                ],
                "support_restraint_verified": True,
                "support_evidence_reference": "SUPPORT-01-DRAWING",
            }
        ],
        "all_supports_listed_verified": True,
        "support_list_evidence_reference": "SUPPORT-SCHEDULE-01",
    }
    inputs.update(overrides)
    return inputs


def test_plastic_support_boundary_conditions_translation_rotation_benchmark():
    r = run(plastic_support_boundary_conditions())
    assert r["checked_conditions_satisfied"]
    assert r["values"]["all_support_conditions_satisfied"]
    constraints = r["values"]["supports"][0]["constraints"]
    assert [item["residual"] for item in constraints] == [0.01, 0, 0.001]
    assert [item["unit"] for item in constraints] == ["mm", "mm", "rad"]
    assert r["full_standard_compliance"] is False


def test_plastic_support_boundary_conditions_limits_and_evidence():
    inputs = plastic_support_boundary_conditions()
    inputs["supports"][0]["constraints"][0]["calculated_translation_mm"] = 0.0101
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert not r["checks"][0]["satisfied"]

    inputs = plastic_support_boundary_conditions()
    inputs["supports"][0]["support_restraint_verified"] = False
    inputs["all_supports_listed_verified"] = False
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert not r["values"]["all_support_conditions_satisfied"]
    assert all(item["satisfied"] for item in r["checks"][:3])
    assert not r["checks"][4]["satisfied"]
    assert not r["checks"][6]["satisfied"]

    inputs = plastic_support_boundary_conditions()
    duplicate_constraint = dict(inputs["supports"][0]["constraints"][0])
    inputs["supports"][0]["constraints"].append(duplicate_constraint)
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert not r["checks"][4]["satisfied"]


def test_notional_and_stability_checks():
    assert (
        run({"operation": "notional_horizontal_load", "floor_vertical_design_load_kn": 1000})[
            "values"
        ]["notional_horizontal_load_kn"]
        == 2
    )
    d = {
        "operation": "stability",
        "destabilising_design_effect": 100,
        "stabilising_dead_effect": 100,
        "resisting_design_capacity": 10,
    }
    assert run(d)["checked_conditions_satisfied"]
    d["destabilising_design_effect"] = 100.001
    assert not run(d)["checked_conditions_satisfied"]


def test_serviceability_signed_deflection():
    d = {
        "operation": "serviceability",
        "deflection_mm": -10,
        "deflection_limit_mm": 10,
        "limit_basis": "project specification",
    }
    assert run(d)["checked_conditions_satisfied"]
    d["deflection_mm"] = -10.01
    assert not run(d)["checked_conditions_satisfied"]
