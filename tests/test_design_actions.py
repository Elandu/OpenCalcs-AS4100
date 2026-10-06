# SPDX-License-Identifier: AGPL-3.0-only
from math import cos, pi, sin, sqrt, tan, tanh

import pytest

from opencalcs_as4100.design_actions import run_design_actions as run
from opencalcs_as4100.frame_buckling import assemble_frame_matrices
from opencalcs_as4100.iterative_analysis import _corotational_element_response
from opencalcs_as4100.members import run_members


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


def whole_frame_elastic_buckling(**overrides):
    evidence = "FRAME-ANALYSIS-01"
    inputs = {
        "operation": "whole_frame_elastic_buckling",
        "design_load_set_id": "ULS-FRAME-01",
        "design_load_actions_verified": True,
        "design_load_evidence_reference": evidence,
        "frame_model_verified": True,
        "frame_model_evidence_reference": evidence,
        "all_frame_joints_listed_verified": True,
        "joint_list_evidence_reference": evidence,
        "all_frame_members_listed_verified": True,
        "member_list_evidence_reference": evidence,
        "joints": [
            {
                "joint_id": "A",
                "x_mm": 0,
                "y_mm": 0,
                "restrained_dofs": ["ux", "uy"],
                "joint_geometry_verified": True,
                "restraint_assessment_verified": True,
                "evidence_reference": evidence,
            },
            {
                "joint_id": "B",
                "x_mm": 4000,
                "y_mm": 0,
                "restrained_dofs": ["ux", "uy"],
                "joint_geometry_verified": True,
                "restraint_assessment_verified": True,
                "evidence_reference": evidence,
            },
        ],
        "members": [
            {
                "member_id": "COL-01",
                "start_joint_id": "A",
                "end_joint_id": "B",
                "area_mm2": 10_000,
                "second_moment_in_plane_mm4": 8e6,
                "axial_force_kn": 1,
                "prismatic_member_verified": True,
                "geometry_verified": True,
                "section_properties_verified": True,
                "axial_force_verified": True,
                "evidence_reference": evidence,
            }
        ],
    }
    inputs.update(overrides)
    return inputs


def second_order_elastic_frame(**overrides):
    evidence = "FRAME-ANALYSIS-01"
    inputs = {
        "operation": "second_order_elastic_frame_analysis",
        "design_load_set_id": "ULS-CANTILEVER-01",
        "design_load_actions_verified": True,
        "design_load_evidence_reference": evidence,
        "frame_model_verified": True,
        "frame_model_evidence_reference": evidence,
        "linearized_model_applicability_verified": True,
        "linearized_model_evidence_reference": evidence,
        "frame_action_equilibrium_verified": True,
        "frame_action_equilibrium_evidence_reference": evidence,
        "all_frame_joints_listed_verified": True,
        "joint_list_evidence_reference": evidence,
        "all_frame_members_listed_verified": True,
        "member_list_evidence_reference": evidence,
        "all_joint_actions_listed_verified": True,
        "joint_action_list_evidence_reference": evidence,
        "all_distributed_member_loads_listed_verified": True,
        "distributed_member_load_list_evidence_reference": evidence,
        "members_remain_elastic_verified": True,
        "elastic_response_evidence_reference": evidence,
        "joints": [
            {
                "joint_id": "BASE",
                "x_mm": 0,
                "y_mm": 0,
                "restrained_dofs": ["ux", "uy", "rz"],
                "joint_geometry_verified": True,
                "restraint_assessment_verified": True,
                "evidence_reference": evidence,
            },
            {
                "joint_id": "TOP",
                "x_mm": 0,
                "y_mm": 4000,
                "restrained_dofs": [],
                "joint_geometry_verified": True,
                "restraint_assessment_verified": True,
                "evidence_reference": evidence,
            },
        ],
        "members": [
            {
                "member_id": "COL-01",
                "start_joint_id": "BASE",
                "end_joint_id": "TOP",
                "area_mm2": 10000,
                "second_moment_in_plane_mm4": 8e6,
                "axial_force_profile_kn": [50, 50],
                "prismatic_member_verified": True,
                "geometry_verified": True,
                "section_properties_verified": True,
                "axial_force_verified": True,
                "evidence_reference": evidence,
            }
        ],
        "joint_actions": [
            {
                "joint_id": "BASE",
                "force_x_kn": 0,
                "force_y_kn": 0,
                "moment_knm": 0,
                "joint_actions_verified": True,
                "evidence_reference": evidence,
            },
            {
                "joint_id": "TOP",
                "force_x_kn": 10,
                "force_y_kn": -50,
                "moment_knm": 0,
                "joint_actions_verified": True,
                "evidence_reference": evidence,
            },
        ],
        "distributed_member_loads": [],
    }
    inputs.update(overrides)
    return inputs


def second_order_uniform_member_load_frame():
    evidence = "FRAME-ANALYSIS-02"
    inputs = second_order_elastic_frame(
        design_load_set_id="ULS-CANTILEVER-UDL-01",
        joint_actions=[
            {
                "joint_id": "BASE",
                "force_x_kn": 0,
                "force_y_kn": 0,
                "moment_knm": 0,
                "joint_actions_verified": True,
                "evidence_reference": evidence,
            },
            {
                "joint_id": "TOP",
                "force_x_kn": 0,
                "force_y_kn": -50,
                "moment_knm": 0,
                "joint_actions_verified": True,
                "evidence_reference": evidence,
            },
        ],
        distributed_member_loads=[
            {
                "load_id": "UDL-01",
                "member_id": "COL-01",
                "start_fraction": 0,
                "end_fraction": 1,
                "transverse_force_start_kn_per_m": 2.5,
                "transverse_force_end_kn_per_m": 2.5,
                "member_load_verified": True,
                "evidence_reference": evidence,
            }
        ],
    )
    inputs["frame_action_equilibrium_evidence_reference"] = evidence
    inputs["distributed_member_load_list_evidence_reference"] = evidence
    return inputs


def iterative_second_order_elastic_frame(**overrides):
    inputs = second_order_elastic_frame()
    inputs["operation"] = "iterative_second_order_elastic_frame_analysis"
    inputs.pop("linearized_model_applicability_verified")
    inputs.pop("linearized_model_evidence_reference")
    inputs["corotational_method_applicability_verified"] = True
    inputs["corotational_method_evidence_reference"] = "COROTATIONAL-METHOD-01"
    for member in inputs["members"]:
        member.pop("axial_force_profile_kn")
        member.pop("axial_force_verified")
    inputs.update(overrides)
    return inputs


def iterative_second_order_uniform_load_frame():
    inputs = iterative_second_order_elastic_frame(design_load_set_id="ULS-COROTATIONAL-UDL-01")
    inputs["joint_actions"][1]["force_x_kn"] = 0
    inputs["distributed_member_loads"] = [
        {
            "load_id": "COROTATIONAL-UDL-01",
            "member_id": "COL-01",
            "start_fraction": 0,
            "end_fraction": 1,
            "transverse_force_start_kn_per_m": 2.5,
            "transverse_force_end_kn_per_m": 2.5,
            "member_load_verified": True,
            "evidence_reference": "COROTATIONAL-UDL-REFERENCE-01",
        }
    ]
    return inputs


def test_second_order_elastic_frame_matches_independent_cantilever_solution():
    inputs = second_order_elastic_frame()
    inputs["joint_actions"].reverse()
    result = run(inputs)
    values = result["values"]
    elastic_modulus = 200000
    second_moment = 8e6
    length = 4000
    axial_force = 50000
    transverse_force = 10000
    wave_number = sqrt(axial_force / (elastic_modulus * second_moment))
    expected_base_moment = transverse_force * tan(wave_number * length) / wave_number / 1e6
    expected_tip_displacement = (
        transverse_force / axial_force * (tan(wave_number * length) / wave_number - length)
    )

    assert result["clauses"] == ["4.4.1.2", "4.5.1", "4.7.1", "4.7.2(b)", "E.1", "E.2(b)"]
    assert result["full_standard_compliance"] is False
    assert result["checked_conditions_satisfied"]
    assert values["elastic_buckling_load_factor"] == pytest.approx(4.9348, rel=5e-5)
    assert values["relative_mesh_difference"] < 0.001
    assert values["member_moments"][0]["maximum_absolute_element_end_moment_knm"] == pytest.approx(
        expected_base_moment, rel=1e-5
    )
    assert abs(values["joint_displacements"][-1]["ux_mm"]) == pytest.approx(
        expected_tip_displacement, rel=1e-5
    )
    assert values["support_reactions"][0]["force_x_kn"] == pytest.approx(-10)
    assert values["support_reactions"][0]["force_y_kn"] == pytest.approx(50)
    assert values["support_reactions"][0]["moment_knm"] == pytest.approx(expected_base_moment)
    assert values["global_equilibrium"]["satisfied"]
    assert all(
        abs(residual)
        <= values["global_equilibrium"]["numerical_tolerance"][
            "moment_knm" if name == "moment_knm" else "force_kn"
        ]
        for name, residual in values["global_equilibrium"]["residual"].items()
    )


def test_iterative_second_order_frame_matches_independent_beam_column_benchmark():
    result = run(iterative_second_order_elastic_frame())
    values = result["values"]
    elastic_modulus = 200000
    second_moment = 8e6
    length = 4000
    axial_force = 50000
    transverse_force = 10000
    wave_number = sqrt(axial_force / (elastic_modulus * second_moment))
    expected_base_moment = transverse_force * tan(wave_number * length) / wave_number / 1e6
    expected_tip_displacement = (
        transverse_force / axial_force * (tan(wave_number * length) / wave_number - length)
    )
    base_moment = values["member_moments"][0]["maximum_absolute_element_end_moment_knm"]
    tip_displacement = abs(values["joint_displacements"][-1]["ux_mm"])

    assert result["clauses"] == ["4.4.1.2", "4.5.1", "E.1", "E.2(b)"]
    assert result["full_standard_compliance"] is False
    assert result["checked_conditions_satisfied"]
    assert values["relative_mesh_difference"] <= 0.001
    assert values["nonlinear_residual_relative"] < 1e-8
    assert values["global_equilibrium"]["satisfied"]
    assert base_moment > 40
    assert base_moment == pytest.approx(expected_base_moment, rel=0.005)
    assert tip_displacement == pytest.approx(expected_tip_displacement, rel=0.005)
    assert base_moment == pytest.approx(48.27748141928913, rel=1e-7)
    assert tip_displacement == pytest.approx(166.4040891604727, rel=1e-7)


def test_iterative_second_order_frame_matches_opensees_uniform_member_load():
    values = run(iterative_second_order_uniform_load_frame())["values"]

    assert abs(values["joint_displacements"][-1]["ux_mm"]) == pytest.approx(
        62.15323697933561, rel=1e-7
    )
    assert values["member_moments"][0]["maximum_absolute_element_end_moment_knm"] == (
        pytest.approx(23.105265467937336, rel=1e-7)
    )
    assert values["support_reactions"][0]["moment_knm"] == pytest.approx(
        -23.105265467937336, rel=1e-7
    )
    assert values["global_equilibrium"]["satisfied"]


def test_corotational_element_tangent_matches_finite_difference_of_internal_force():
    assembly = assemble_frame_matrices(second_order_elastic_frame(), 1)
    element = assembly["member_elements"][0][0]
    member = second_order_elastic_frame()["members"][0]
    displacement = [0.2, -0.1, 0.0002, 0.6, 0.3, -0.0001]
    tangent = _corotational_element_response(element, member, displacement)["tangent"]
    maximum_error = 0.0
    derivative_scale = 0.0
    step = 1e-4

    for column in range(6):
        positive = displacement[:]
        negative = displacement[:]
        positive[column] += step
        negative[column] -= step
        positive_force = _corotational_element_response(element, member, positive)["internal_force"]
        negative_force = _corotational_element_response(element, member, negative)["internal_force"]
        for row in range(6):
            derivative = (positive_force[row] - negative_force[row]) / (2 * step)
            derivative_scale = max(derivative_scale, abs(derivative))
            maximum_error = max(maximum_error, abs(derivative - tangent[row][column]))

    assert maximum_error / derivative_scale < 1e-8


def test_corotational_element_has_zero_internal_force_under_rigid_body_motion():
    inputs = second_order_elastic_frame()
    assembly = assemble_frame_matrices(inputs, 1)
    element = assembly["member_elements"][0][0]
    member = inputs["members"][0]
    angle = 0.1
    cosine = cos(angle)
    sine = sin(angle)
    start_x, start_y = element["reference_start"]
    end_x, end_y = element["reference_end"]
    moved_start = (100 + start_x * cosine - start_y * sine, 200 + start_x * sine + start_y * cosine)
    moved_end = (100 + end_x * cosine - end_y * sine, 200 + end_x * sine + end_y * cosine)
    displacement = [
        moved_start[0] - start_x,
        moved_start[1] - start_y,
        angle,
        moved_end[0] - end_x,
        moved_end[1] - end_y,
        angle,
    ]
    state = _corotational_element_response(element, member, displacement)

    assert max(abs(value) for value in state["basic_force"]) < 1e-3


def test_iterative_second_order_frame_requires_method_applicability_evidence():
    inputs = iterative_second_order_elastic_frame()
    del inputs["corotational_method_applicability_verified"]

    with pytest.raises(ValueError, match="Invalid input"):
        run(inputs)


def test_second_order_elastic_frame_matches_uniformly_loaded_beam_column_solution():
    result = run(second_order_uniform_member_load_frame())
    values = result["values"]
    elastic_rigidity = 200000 * 8e6
    axial_force = 50000
    length = 4000
    transverse_load = 2.5  # kN/m is numerically equal to N/mm.
    wave_number = sqrt(axial_force / elastic_rigidity)
    angle = wave_number * length
    coefficient_b = -transverse_load * length / (elastic_rigidity * wave_number)
    coefficient_a = (-transverse_load / axial_force - coefficient_b * sin(angle)) / cos(angle)
    expected_tip_displacement = (
        coefficient_a / wave_number**2 * (1 - cos(angle))
        + coefficient_b / wave_number * (length - sin(angle) / wave_number)
        + transverse_load * length**2 / (2 * axial_force)
    )
    expected_support_moment = (
        -elastic_rigidity * (coefficient_a + transverse_load / axial_force) / 1e6
    )

    assert result["checked_conditions_satisfied"]
    assert abs(values["joint_displacements"][-1]["ux_mm"]) == pytest.approx(
        expected_tip_displacement, rel=1e-4
    )
    assert values["support_reactions"][0]["force_x_kn"] == pytest.approx(10, rel=1e-6)
    assert values["support_reactions"][0]["moment_knm"] == pytest.approx(
        expected_support_moment, rel=1e-4
    )
    assert values["member_moments"][0]["element_end_moments"][0][
        "start_end_moment_knm"
    ] == pytest.approx(expected_support_moment, rel=1e-4)
    assert values["global_equilibrium"]["applied_action_resultants"]["force_x_kn"] == (
        pytest.approx(-10, abs=1e-8)
    )
    assert values["global_equilibrium"]["applied_action_resultants"]["moment_knm"] == (
        pytest.approx(20, abs=1e-8)
    )
    assert values["global_equilibrium"]["satisfied"]


def test_second_order_elastic_frame_integrates_partial_linearly_varying_member_load():
    inputs = second_order_uniform_member_load_frame()
    inputs["distributed_member_loads"] = [
        {
            "load_id": "TRIANGULAR-PARTIAL-01",
            "member_id": "COL-01",
            "start_fraction": 0.25,
            "end_fraction": 0.75,
            "transverse_force_start_kn_per_m": 0,
            "transverse_force_end_kn_per_m": 4,
            "member_load_verified": True,
            "evidence_reference": "FRAME-ANALYSIS-02",
        }
    ]
    values = run(inputs)["values"]
    applied = values["global_equilibrium"]["applied_action_resultants"]

    assert applied["force_x_kn"] == pytest.approx(-4, abs=1e-8)
    assert applied["force_y_kn"] == pytest.approx(-50, abs=1e-8)
    assert applied["moment_knm"] == pytest.approx(9.333333333333334, abs=1e-8)
    assert values["global_equilibrium"]["satisfied"]


def test_second_order_elastic_frame_transforms_member_loads_to_global_axes():
    inputs = second_order_uniform_member_load_frame()
    inputs["joints"][1]["x_mm"] = 3000
    inputs["members"][0]["axial_force_profile_kn"] = [0, 0]
    inputs["joint_actions"][1]["force_y_kn"] = 0
    inputs["distributed_member_loads"][0]["transverse_force_start_kn_per_m"] = 2
    inputs["distributed_member_loads"][0]["transverse_force_end_kn_per_m"] = 2

    values = run(inputs)["values"]
    applied = values["global_equilibrium"]["applied_action_resultants"]
    reaction = values["support_reactions"][0]

    assert applied["force_x_kn"] == pytest.approx(-8, abs=1e-8)
    assert applied["force_y_kn"] == pytest.approx(6, abs=1e-8)
    assert applied["moment_knm"] == pytest.approx(25, abs=1e-8)
    assert reaction["force_x_kn"] == pytest.approx(8, abs=1e-8)
    assert reaction["force_y_kn"] == pytest.approx(-6, abs=1e-8)
    assert reaction["moment_knm"] == pytest.approx(-25, abs=1e-8)
    assert values["global_equilibrium"]["satisfied"]


def _axially_distributed_second_order_column():
    inputs = second_order_elastic_frame()
    inputs["members"][0]["axial_force_profile_kn"] = [50, 0]
    inputs["joint_actions"][1]["force_y_kn"] = 0
    inputs["distributed_member_loads"] = [
        {
            "load_id": "COL-AXIAL-UDL-01",
            "member_id": "COL-01",
            "start_fraction": 0,
            "end_fraction": 1,
            "transverse_force_start_kn_per_m": 0,
            "transverse_force_end_kn_per_m": 0,
            "axial_force_kn_per_m": -12.5,
            "member_load_verified": True,
            "evidence_reference": "AXIAL-UDL-01",
        }
    ]
    return inputs


def _linear_axial_force_column_reference():
    """Integrate the continuous beam-column transfer equations with RK4."""
    length_mm = 4000.0
    elastic_modulus_mpa = 200_000.0
    second_moment_mm4 = 8e6
    axial_start_n = 50_000.0
    axial_end_n = 0.0
    tip_force_n = 10_000.0
    steps = 4000
    step_mm = length_mm / steps
    ei = elastic_modulus_mpa * second_moment_mm4

    def integrate(initial_moment_nmm, initial_shear_n):
        state = [0.0, 0.0, initial_moment_nmm, initial_shear_n]

        def derivative(position_mm, values):
            axial_n = axial_start_n + (axial_end_n - axial_start_n) * position_mm / length_mm
            displacement, rotation, moment_nmm, shear_n = values
            return [rotation, moment_nmm / ei, shear_n - axial_n * rotation, 0.0]

        for index in range(steps):
            position_mm = index * step_mm
            k1 = derivative(position_mm, state)
            k2 = derivative(
                position_mm + step_mm / 2,
                [value + step_mm * slope / 2 for value, slope in zip(state, k1, strict=True)],
            )
            k3 = derivative(
                position_mm + step_mm / 2,
                [value + step_mm * slope / 2 for value, slope in zip(state, k2, strict=True)],
            )
            k4 = derivative(
                position_mm + step_mm,
                [value + step_mm * slope for value, slope in zip(state, k3, strict=True)],
            )
            state = [
                value + step_mm * (slope_1 + 2 * slope_2 + 2 * slope_3 + slope_4) / 6
                for value, slope_1, slope_2, slope_3, slope_4 in zip(
                    state, k1, k2, k3, k4, strict=True
                )
            ]
        return state

    load_response = integrate(0.0, -tip_force_n)
    unit_moment_response = integrate(1.0, 0.0)
    base_moment_nmm = -load_response[2] / unit_moment_response[2]
    tip_displacement_mm = integrate(base_moment_nmm, -tip_force_n)[0]
    return abs(base_moment_nmm) / 1_000_000.0, abs(tip_displacement_mm)


def test_second_order_elastic_frame_applies_uniform_axial_member_load():
    values = run(_axially_distributed_second_order_column())["values"]
    reference_moment_knm, reference_tip_displacement_mm = _linear_axial_force_column_reference()

    assert values["global_equilibrium"]["satisfied"]
    assert values["support_reactions"][0]["force_y_kn"] == pytest.approx(50)
    assert values["member_axial_force_pattern"][0]["axial_force_profile_kn"] == [50, 0]
    assert values["relative_mesh_difference"] <= 0.001
    assert values["member_moments"][0]["maximum_absolute_element_end_moment_knm"] == pytest.approx(
        reference_moment_knm, rel=1e-6
    )
    assert abs(values["joint_displacements"][-1]["ux_mm"]) == pytest.approx(
        reference_tip_displacement_mm, rel=1e-6
    )


def test_second_order_elastic_frame_checks_axial_load_force_profile_equilibrium():
    inputs = _axially_distributed_second_order_column()
    inputs["distributed_member_loads"][0]["axial_force_kn_per_m"] = -10

    with pytest.raises(ValueError, match="must satisfy N_end - N_start"):
        run(inputs)


def test_axial_distributed_member_load_requires_full_member_span():
    inputs = _axially_distributed_second_order_column()
    inputs["distributed_member_loads"][0]["start_fraction"] = 0.1

    with pytest.raises(ValueError, match="complete member span"):
        run(inputs)


def test_iterative_second_order_frame_applies_uniform_axial_member_load():
    inputs = iterative_second_order_elastic_frame()
    inputs["joint_actions"][1]["force_y_kn"] = 0
    inputs["distributed_member_loads"] = _axially_distributed_second_order_column()[
        "distributed_member_loads"
    ]

    values = run(inputs)["values"]

    assert values["global_equilibrium"]["satisfied"]
    assert values["support_reactions"][0]["force_y_kn"] == pytest.approx(50)
    assert values["relative_mesh_difference"] <= 0.001


def test_second_order_elastic_frame_rejects_invalid_distributed_member_load():
    inputs = second_order_uniform_member_load_frame()
    inputs["distributed_member_loads"][0]["end_fraction"] = 0
    with pytest.raises(ValueError, match="fractions must satisfy"):
        run(inputs)

    inputs = second_order_uniform_member_load_frame()
    inputs["distributed_member_loads"][0]["member_id"] = "UNKNOWN"
    with pytest.raises(ValueError, match="must reference a listed frame member"):
        run(inputs)


def test_second_order_elastic_frame_requires_distributed_load_inventory_evidence():
    inputs = second_order_uniform_member_load_frame()
    inputs["all_distributed_member_loads_listed_verified"] = False
    result = run(inputs)

    assert not result["checked_conditions_satisfied"]
    assert not next(
        check for check in result["checks"] if "distributed member-load list" in check["condition"]
    )["satisfied"]


def test_second_order_elastic_frame_rejects_incomplete_joint_actions():
    inputs = second_order_elastic_frame()
    inputs["joint_actions"][1]["joint_id"] = "BASE"
    with pytest.raises(ValueError, match="exactly one complete joint-action record"):
        run(inputs)


def test_second_order_elastic_frame_rejects_design_load_at_or_above_buckling():
    inputs = second_order_elastic_frame()
    inputs["members"][0]["axial_force_profile_kn"] = [300, 300]
    inputs["joint_actions"][1]["force_y_kn"] = -300
    with pytest.raises(ValueError, match="reaches or exceeds the frame elastic buckling load"):
        run(inputs)


def test_second_order_elastic_frame_handles_tension_and_zero_axial_force_patterns():
    tension = second_order_elastic_frame()
    tension["members"][0]["axial_force_profile_kn"] = [-50, -50]
    tension["joint_actions"][1]["force_y_kn"] = 50
    tension_result = run(tension)
    tension_values = tension_result["values"]
    wave_number = sqrt(50000 / (200000 * 8e6))
    expected_tension_moment = 10000 * tanh(wave_number * 4000) / wave_number / 1e6
    expected_tension_displacement = 10000 / 50000 * (4000 - tanh(wave_number * 4000) / wave_number)
    assert tension_values["elastic_buckling_load_factor"] is None
    assert tension_values["relative_mesh_difference"] < 0.001
    assert tension_values["member_moments"][0]["maximum_absolute_element_end_moment_knm"] == (
        pytest.approx(expected_tension_moment, rel=1e-5)
    )
    assert abs(tension_values["joint_displacements"][-1]["ux_mm"]) == pytest.approx(
        expected_tension_displacement, rel=1e-5
    )
    assert tension_values["global_equilibrium"]["satisfied"]

    zero = second_order_elastic_frame()
    zero["members"][0]["axial_force_profile_kn"] = [0, 0]
    zero["joint_actions"][1]["force_y_kn"] = 0
    zero_values = run(zero)["values"]
    assert zero_values["elastic_buckling_load_factor"] is None
    assert zero_values["member_moments"][0]["maximum_absolute_element_end_moment_knm"] == (
        pytest.approx(40)
    )
    assert abs(zero_values["joint_displacements"][-1]["ux_mm"]) == pytest.approx(4000 / 30)
    assert zero_values["global_equilibrium"]["satisfied"]


def test_second_order_elastic_frame_reports_unverified_method_or_equilibrium_assessments():
    inputs = second_order_elastic_frame(
        linearized_model_applicability_verified=False,
        frame_action_equilibrium_verified=False,
    )
    result = run(inputs)

    assert not result["checked_conditions_satisfied"]
    assert not next(
        check
        for check in result["checks"]
        if check["clause"] == "4.4.1.2" and "linearized method" in check["condition"]
    )["satisfied"]
    assert not next(check for check in result["checks"] if check["clause"] == "4.5.1")["satisfied"]


def test_whole_frame_elastic_buckling_matches_independent_euler_solution():
    r = run(whole_frame_elastic_buckling())
    values = r["values"]
    expected_load_factor = 100 * pi**2
    assert r["clauses"] == ["4.7.1", "4.7.2(b)"]
    assert r["checked_conditions_satisfied"]
    assert r["full_standard_compliance"] is False
    assert values["elastic_buckling_load_factor"] == pytest.approx(expected_load_factor, rel=5e-5)
    assert values["lambda_c"] == values["elastic_buckling_load_factor"]
    assert values["relative_mesh_difference"] < 0.001
    assert values["design_load_set_id"] == "ULS-FRAME-01"
    assert values["refined_mesh"]["mesh_subdivisions_per_member"] in (8, 16, 32)
    assert values["members"][0]["axial_force_kn"] == 1
    assert "axial_force_profile_kn" not in values["members"][0]
    scaled = whole_frame_elastic_buckling()
    scaled["members"][0]["axial_force_kn"] = 3
    scaled_factor = run(scaled)["values"]["lambda_c"]
    assert scaled_factor * 3 == pytest.approx(values["lambda_c"], rel=1e-10)


def test_whole_frame_elastic_buckling_matches_fixed_end_euler_solution():
    inputs = whole_frame_elastic_buckling()
    for joint in inputs["joints"]:
        joint["restrained_dofs"] = ["ux", "uy", "rz"]
    values = run(inputs)["values"]
    assert values["elastic_buckling_load_factor"] == pytest.approx(4 * 100 * pi**2, rel=5e-5)
    assert values["refined_mesh"]["mesh_subdivisions_per_member"] >= 16


def test_whole_frame_elastic_buckling_matches_variable_force_transfer_solution():
    inputs = whole_frame_elastic_buckling()
    member = inputs["members"][0]
    member.pop("axial_force_kn")
    member["axial_force_profile_kn"] = [100, 20]

    values = run(inputs)["values"]
    # Independent RK4 transfer integration of EI*w'''' + (N(x)*w')' = 0.
    assert values["lambda_c"] == pytest.approx(15.98372499511359, rel=1e-4)
    assert values["relative_mesh_difference"] < 0.001
    assert values["members"][0]["axial_force_profile_kn"] == [100, 20]
    assert "axial_force_kn" not in values["members"][0]

    reverse = whole_frame_elastic_buckling()
    reverse_member = reverse["members"][0]
    reverse_member.pop("axial_force_kn")
    reverse_member["axial_force_profile_kn"] = [20, 100]
    assert run(reverse)["values"]["lambda_c"] == pytest.approx(values["lambda_c"], rel=1e-12)

    scaled = whole_frame_elastic_buckling()
    scaled_member = scaled["members"][0]
    scaled_member.pop("axial_force_kn")
    scaled_member["axial_force_profile_kn"] = [300, 60]
    assert run(scaled)["values"]["lambda_c"] * 3 == pytest.approx(values["lambda_c"], rel=1e-12)


def test_variable_force_profile_preserves_station_order_and_member_orientation():
    def factor(profile, *, reverse_member=False):
        inputs = whole_frame_elastic_buckling()
        inputs["joints"][0]["restrained_dofs"] = ["ux", "uy", "rz"]
        inputs["joints"][1]["restrained_dofs"] = []
        member = inputs["members"][0]
        member.pop("axial_force_kn")
        member["axial_force_profile_kn"] = list(profile)
        if reverse_member:
            member["start_joint_id"], member["end_joint_id"] = (
                member["end_joint_id"],
                member["start_joint_id"],
            )
            member["axial_force_profile_kn"] = list(reversed(profile))
        return run(inputs)["values"]["lambda_c"]

    start_compression = factor([100, 20])
    end_compression = factor([20, 100])
    assert start_compression == pytest.approx(5.537520283, rel=1e-3)
    assert end_compression == pytest.approx(3.219735399, rel=1e-3)
    assert factor([100, 20], reverse_member=True) == pytest.approx(
        start_compression,
        rel=1e-10,
    )


def test_variable_force_profile_with_tension_region_matches_transfer_solution():
    inputs = whole_frame_elastic_buckling()
    inputs["joints"][0]["restrained_dofs"] = ["ux", "uy", "rz"]
    inputs["joints"][1]["restrained_dofs"] = []
    member = inputs["members"][0]
    member.pop("axial_force_kn")
    member["axial_force_profile_kn"] = [100, -20]

    result = run(inputs)["values"]
    assert result["lambda_c"] == pytest.approx(12.4159456041, rel=1e-3)


def test_constant_axial_force_profile_matches_scalar_force_route():
    constant = run(whole_frame_elastic_buckling())["values"]["lambda_c"]
    inputs = whole_frame_elastic_buckling()
    member = inputs["members"][0]
    member.pop("axial_force_kn")
    member["axial_force_profile_kn"] = [1, 1]
    profiled = run(inputs)["values"]["lambda_c"]
    assert profiled == pytest.approx(constant, rel=1e-12)


def test_whole_frame_elastic_buckling_matches_piecewise_column_transfer_solution():
    evidence = "STEPPED-COLUMN-TRANSFER-REFERENCE"
    inputs = whole_frame_elastic_buckling(
        design_load_set_id="ULS-STEPPED-COLUMN-100KN",
        design_load_evidence_reference=evidence,
        frame_model_evidence_reference=evidence,
        joint_list_evidence_reference=evidence,
        member_list_evidence_reference=evidence,
        joints=[
            {
                "joint_id": "BASE",
                "x_mm": 0,
                "y_mm": 0,
                "restrained_dofs": ["ux", "uy"],
                "joint_geometry_verified": True,
                "restraint_assessment_verified": True,
                "evidence_reference": evidence,
            },
            {
                "joint_id": "STEP",
                "x_mm": 0,
                "y_mm": 2000,
                "restrained_dofs": [],
                "joint_geometry_verified": True,
                "restraint_assessment_verified": True,
                "evidence_reference": evidence,
            },
            {
                "joint_id": "TOP",
                "x_mm": 0,
                "y_mm": 4000,
                "restrained_dofs": ["ux", "uy"],
                "joint_geometry_verified": True,
                "restraint_assessment_verified": True,
                "evidence_reference": evidence,
            },
        ],
        members=[
            {
                "member_id": member_id,
                "start_joint_id": start_joint_id,
                "end_joint_id": end_joint_id,
                "area_mm2": 10_000,
                "second_moment_in_plane_mm4": inertia,
                "axial_force_kn": 100,
                "prismatic_member_verified": True,
                "geometry_verified": True,
                "section_properties_verified": True,
                "axial_force_verified": True,
                "evidence_reference": evidence,
            }
            for member_id, start_joint_id, end_joint_id, inertia in (
                ("LOWER", "BASE", "STEP", 8e6),
                ("UPPER", "STEP", "TOP", 2e6),
            )
        ],
    )

    values = run(inputs)["values"]
    # Exact piecewise Euler-Bernoulli transfer solution for two 2 m segments.
    assert values["lambda_c"] == pytest.approx(3.650519363459397, rel=1e-4)
    assert values["relative_mesh_difference"] < 0.001


def portal_frame_elastic_buckling():
    evidence = "PORTAL-FRAME-OPENSees-REFERENCE"
    joints = [
        {
            "joint_id": "BASE-L",
            "x_mm": 0,
            "y_mm": 0,
            "restrained_dofs": ["ux", "uy", "rz"],
            "joint_geometry_verified": True,
            "restraint_assessment_verified": True,
            "evidence_reference": evidence,
        },
        {
            "joint_id": "TOP-L",
            "x_mm": 0,
            "y_mm": 4000,
            "restrained_dofs": [],
            "joint_geometry_verified": True,
            "restraint_assessment_verified": True,
            "evidence_reference": evidence,
        },
        {
            "joint_id": "BASE-R",
            "x_mm": 6000,
            "y_mm": 0,
            "restrained_dofs": ["ux", "uy", "rz"],
            "joint_geometry_verified": True,
            "restraint_assessment_verified": True,
            "evidence_reference": evidence,
        },
        {
            "joint_id": "TOP-R",
            "x_mm": 6000,
            "y_mm": 4000,
            "restrained_dofs": [],
            "joint_geometry_verified": True,
            "restraint_assessment_verified": True,
            "evidence_reference": evidence,
        },
    ]

    def member(member_id, start, end, axial_force_kn):
        return {
            "member_id": member_id,
            "start_joint_id": start,
            "end_joint_id": end,
            "area_mm2": 10_000,
            "second_moment_in_plane_mm4": 8e6,
            "axial_force_kn": axial_force_kn,
            "prismatic_member_verified": True,
            "geometry_verified": True,
            "section_properties_verified": True,
            "axial_force_verified": True,
            "evidence_reference": evidence,
        }

    return whole_frame_elastic_buckling(
        design_load_set_id="ULS-PORTAL-30-20-KN",
        design_load_evidence_reference=evidence,
        frame_model_evidence_reference=evidence,
        joint_list_evidence_reference=evidence,
        member_list_evidence_reference=evidence,
        joints=joints,
        members=[
            member("COLUMN-L", "BASE-L", "TOP-L", 30),
            member("COLUMN-R", "BASE-R", "TOP-R", 20),
            member("BEAM", "TOP-L", "TOP-R", 0),
        ],
    )


def test_whole_frame_elastic_buckling_matches_independent_portal_frame_analysis():
    result = run(portal_frame_elastic_buckling())
    values = result["values"]
    # OpenSeesPy 3.8.0 P-Delta model, 32 elastic beam-column elements per member.
    assert values["lambda_c"] == pytest.approx(26.422688110351565, abs=0.01)
    assert values["relative_mesh_difference"] < 0.001
    assert result["checked_conditions_satisfied"]


def test_whole_frame_elastic_buckling_retains_failed_evidence_checks():
    inputs = whole_frame_elastic_buckling(
        frame_model_verified=False,
        all_frame_joints_listed_verified=False,
        all_frame_members_listed_verified=False,
    )
    inputs["members"][0]["axial_force_verified"] = False
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert not all(check["satisfied"] for check in r["checks"])
    assert r["values"]["elastic_buckling_load_factor"] > 0


def test_whole_frame_elastic_buckling_rejects_unstable_or_unrestrained_model():
    inputs = whole_frame_elastic_buckling()
    inputs["joints"][0]["restrained_dofs"] = ["uy"]
    inputs["joints"][1]["restrained_dofs"] = ["uy"]
    with pytest.raises(ValueError, match="singular or unstable"):
        run(inputs)


def test_whole_frame_elastic_buckling_rejects_unconnected_model():
    inputs = whole_frame_elastic_buckling()
    inputs["joints"].append(
        {
            "joint_id": "ISOLATED",
            "x_mm": 9000,
            "y_mm": 1000,
            "restrained_dofs": [],
            "joint_geometry_verified": True,
            "restraint_assessment_verified": True,
            "evidence_reference": "FRAME-ANALYSIS-01",
        }
    )
    with pytest.raises(ValueError, match="one connected"):
        run(inputs)


def test_whole_frame_elastic_buckling_rejects_all_tension_pattern():
    inputs = whole_frame_elastic_buckling()
    inputs["members"][0]["axial_force_kn"] = -1
    with pytest.raises(ValueError, match="no positive elastic buckling eigenvalue"):
        run(inputs)


def test_frame_buckling_requires_either_scalar_or_complete_axial_profile():
    scalar_and_profile = whole_frame_elastic_buckling()
    scalar_and_profile["members"][0]["axial_force_profile_kn"] = [1, 1]
    with pytest.raises(ValueError, match="Invalid input"):
        run(scalar_and_profile)

    incomplete_profile = whole_frame_elastic_buckling()
    incomplete_profile["members"][0].pop("axial_force_kn")
    incomplete_profile["members"][0]["axial_force_profile_kn"] = [1]
    with pytest.raises(ValueError, match="Invalid input"):
        run(incomplete_profile)


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


def test_clause_6_3_2_derives_compression_member_lengths_about_both_axes():
    inputs = {
        "operation": "compression_member_effective_lengths",
        "member_length_mm": 4000,
        "member_length_centre_to_centre_verified": True,
        "member_length_evidence_reference": "MEMBER-LENGTH-01",
        "principal_buckling_axes_verified": True,
        "principal_axes_evidence_reference": "MEMBER-PRINCIPAL-AXES-01",
        "effective_length_case_x": "braced_fixed_fixed",
        "effective_length_case_x_verified": True,
        "effective_length_case_x_reference": "RESTRAINT-X-01",
        "effective_length_case_y": "braced_pinned_pinned",
        "effective_length_case_y_verified": True,
        "effective_length_case_y_reference": "RESTRAINT-Y-01",
    }
    result = run(inputs)
    assert result["checked_conditions_satisfied"]
    assert result["clauses"] == ["6.3.2", "4.6.2", "4.6.3.2"]
    assert result["values"]["effective_length_factor_x"] == 0.7
    assert result["values"]["effective_length_x_mm"] == 2800
    assert result["values"]["effective_length_factor_y"] == 1.0
    assert result["values"]["effective_length_y_mm"] == 4000
    assert result["full_standard_compliance"] is False
    inputs["effective_length_case_x_verified"] = False
    unverified = run(inputs)
    assert not unverified["checked_conditions_satisfied"]
    assert not unverified["checks"][2]["satisfied"]
    inputs["effective_length_case_x_verified"] = True
    inputs["principal_buckling_axes_verified"] = False
    unverified_axes = run(inputs)
    assert not unverified_axes["checked_conditions_satisfied"]
    assert not unverified_axes["checks"][0]["satisfied"]


def test_clause_6_3_2_lengths_feed_the_compression_member_capacity_check():
    effective_lengths = run(
        {
            "operation": "compression_member_effective_lengths",
            "member_length_mm": 4000,
            "member_length_centre_to_centre_verified": True,
            "member_length_evidence_reference": "UB-4000-MEMBER-LENGTH",
            "principal_buckling_axes_verified": True,
            "principal_axes_evidence_reference": "UB-PRINCIPAL-AXES",
            "effective_length_case_x": "braced_fixed_fixed",
            "effective_length_case_x_verified": True,
            "effective_length_case_x_reference": "UB-X-FIXED-ENDS",
            "effective_length_case_y": "braced_fixed_fixed",
            "effective_length_case_y_verified": True,
            "effective_length_case_y_reference": "UB-Y-FIXED-ENDS",
        }
    )
    length_values = effective_lengths["values"]
    capacity = run_members(
        {
            "operation": "compression",
            "yield_strength_mpa": 250,
            "gross_area_mm2": 3000,
            "net_area_mm2": 3000,
            "effective_area_mm2": 3000,
            "effective_length_x_mm": length_values["effective_length_x_mm"],
            "effective_length_y_mm": length_values["effective_length_y_mm"],
            "radius_x_mm": 40,
            "radius_y_mm": 40,
            "section_constant_x": 0,
            "section_constant_y": 0,
            "action_kn": 500,
            "geometry": "doubly_symmetric",
        }
    )
    assert length_values["effective_length_x_mm"] == 2800
    assert capacity["values"]["modified_slenderness_x"] == 70
    assert capacity["values"]["reduction_x"] == pytest.approx(0.7482233419967513)
    assert capacity["values"]["member_capacity_x_kn"] == pytest.approx(561.1675064975635)
    assert capacity["checks"]["x"]["design_capacity"] == pytest.approx(505.0507558478072)
    assert capacity["checks"]["x"]["satisfied"]


def frame_chart_member_buckling(**overrides):
    inputs = {
        "operation": "frame_chart_member_buckling",
        "member_id": "COL-CHART-01",
        "frame_type": "braced",
        "frame_type_verified": True,
        "rigid_jointed_frame_verified": True,
        "frame_classification_evidence_reference": "FRAME-CLASSIFICATION-01",
        "stiffness_ratio_at_end_1": 0.7,
        "stiffness_ratio_at_end_2": 1.2,
        "stiffness_ratios_verified": True,
        "stiffness_ratio_evidence_reference": "END-RATIOS-01",
        "effective_length_factor": 0.85,
        "effective_length_factor_chart_verified": True,
        "chart_evidence_reference": "FIGURE-4-6-3-3-01",
        "second_moment_mm4": 8e6,
        "second_moment_about_buckling_axis_verified": True,
        "section_evidence_reference": "SECTION-01",
        "member_length_mm": 4000,
        "member_length_centre_to_centre_verified": True,
        "member_length_evidence_reference": "MEMBER-LENGTH-01",
    }
    inputs.update(overrides)
    return inputs


def test_frame_chart_member_buckling_uses_verified_factor_for_euler_load():
    r = run(frame_chart_member_buckling())
    values = r["values"]
    assert r["checked_conditions_satisfied"]
    assert r["clauses"] == ["4.6.2", "4.6.3.3"]
    assert values["effective_length_factor_figure"] == "Figure 4.6.3.3(a)"
    assert values["effective_length_mm"] == pytest.approx(3400)
    assert values["elastic_buckling_load_kn"] == pytest.approx(1366.0352112234405)
    assert r["full_standard_compliance"] is False


@pytest.mark.parametrize(
    ("frame_type", "gamma_1", "gamma_2", "expected_factor"),
    [
        ("braced", 0.1, 0.4, 0.6030256304844271),
        ("braced", 1.0, 1.0, 0.7742650686480755),
        ("braced", 0.8, 1.2, 0.7708101517503944),
        ("sway", 0.1, 0.4, 1.082506704547602),
        ("sway", 1.0, 1.0, 1.3172751026289122),
        ("sway", 0.8, 1.2, 1.3156717092299173),
    ],
)
def test_frame_chart_member_buckling_solves_alignment_equation(
    frame_type, gamma_1, gamma_2, expected_factor
):
    inputs = frame_chart_member_buckling(
        frame_type=frame_type,
        stiffness_ratio_at_end_1=gamma_1,
        stiffness_ratio_at_end_2=gamma_2,
    )
    inputs.pop("effective_length_factor")
    inputs.pop("effective_length_factor_chart_verified")
    inputs.pop("chart_evidence_reference")

    r = run(inputs)
    values = r["values"]

    assert r["checked_conditions_satisfied"]
    assert values["effective_length_factor"] == pytest.approx(expected_factor, abs=1e-12)
    assert values["effective_length_factor_source"] == "alignment_chart_equation"
    assert values["effective_length_mm"] == pytest.approx(expected_factor * 4000)
    assert values["elastic_buckling_load_kn"] == pytest.approx(
        pi**2 * 200000 * 8e6 / (expected_factor * 4000) ** 2 / 1000
    )
    assert r["checks"][3]["satisfied"]
    assert r["checks"][4]["satisfied"]
    assert r["full_standard_compliance"] is False


@pytest.mark.parametrize(
    ("frame_type", "gamma_1", "gamma_2", "expected_factor"),
    [
        ("braced", 0, 0, 0.5),
        ("braced", 0, 1000, 0.6990480148522852),
        ("braced", 50, 50, 0.9920235235222336),
        ("sway", 0, 0, 1.0),
        ("sway", 0, 1000, 1.9951601164997164),
    ],
)
def test_frame_chart_alignment_equation_limits(frame_type, gamma_1, gamma_2, expected_factor):
    inputs = frame_chart_member_buckling(
        frame_type=frame_type,
        stiffness_ratio_at_end_1=gamma_1,
        stiffness_ratio_at_end_2=gamma_2,
    )
    inputs.pop("effective_length_factor")
    inputs.pop("effective_length_factor_chart_verified")
    inputs.pop("chart_evidence_reference")

    values = run(inputs)["values"]
    assert values["effective_length_factor"] == pytest.approx(expected_factor, abs=1e-12)


def test_frame_chart_alignment_equations_are_symmetric_in_end_ratios():
    for frame_type in ("braced", "sway"):
        forward = frame_chart_member_buckling(
            frame_type=frame_type,
            stiffness_ratio_at_end_1=0.25,
            stiffness_ratio_at_end_2=2.5,
        )
        reverse = frame_chart_member_buckling(
            frame_type=frame_type,
            stiffness_ratio_at_end_1=2.5,
            stiffness_ratio_at_end_2=0.25,
        )
        for inputs in (forward, reverse):
            inputs.pop("effective_length_factor")
            inputs.pop("effective_length_factor_chart_verified")
            inputs.pop("chart_evidence_reference")
        assert run(forward)["values"]["effective_length_factor"] == pytest.approx(
            run(reverse)["values"]["effective_length_factor"], abs=1e-13
        )


def test_frame_chart_factor_reading_requires_chart_evidence():
    inputs = frame_chart_member_buckling()
    inputs.pop("effective_length_factor_chart_verified")
    inputs.pop("chart_evidence_reference")
    with pytest.raises(ValueError):
        run(inputs)


@pytest.mark.parametrize(
    ("frame_type", "effective_length_factor", "expected"),
    [
        ("braced", 0.5, True),
        ("braced", 1.0, True),
        ("braced", 0.49, False),
        ("braced", 1.01, False),
        ("sway", 1.0, True),
        ("sway", 1.2, True),
        ("sway", 0.99, False),
    ],
)
def test_frame_chart_member_buckling_factor_ranges(frame_type, effective_length_factor, expected):
    r = run(
        frame_chart_member_buckling(
            frame_type=frame_type,
            effective_length_factor=effective_length_factor,
        )
    )
    assert r["checks"][4]["satisfied"] is expected
    assert r["checked_conditions_satisfied"] is expected


def test_frame_chart_member_buckling_requires_ratio_chart_and_geometry_evidence():
    r = run(
        frame_chart_member_buckling(
            frame_type_verified=False,
            rigid_jointed_frame_verified=False,
            stiffness_ratios_verified=False,
            effective_length_factor_chart_verified=False,
            second_moment_about_buckling_axis_verified=False,
            member_length_centre_to_centre_verified=False,
        )
    )
    assert not r["checked_conditions_satisfied"]
    assert [check["satisfied"] for check in r["checks"]] == [
        False,
        False,
        False,
        False,
        True,
        False,
        False,
    ]


def test_frame_chart_member_buckling_rejects_negative_stiffness_ratios():
    with pytest.raises(ValueError):
        run(frame_chart_member_buckling(stiffness_ratio_at_end_1=-0.1))


def triangulated_member_buckling(**overrides):
    inputs = {
        "operation": "triangulated_member_buckling",
        "member_id": "TRUSS-MEMBER-01",
        "triangulated_structure_verified": True,
        "triangulated_structure_evidence_reference": "TRUSS-01",
        "second_moment_mm4": 4.5e6,
        "second_moment_about_buckling_axis_verified": True,
        "section_evidence_reference": "SECTION-TRUSS-01",
        "member_length_between_intersections_mm": 3000,
        "member_length_between_intersections_verified": True,
        "member_geometry_evidence_reference": "TRUSS-GEOMETRY-01",
        "effective_length_mm": 3000,
        "effective_length_assessment_verified": True,
        "effective_length_evidence_reference": "TRUSS-EFFECTIVE-LENGTH-01",
        "rational_buckling_analysis_consistent_with_appendix_g_verified": False,
    }
    inputs.update(overrides)
    return inputs


def test_triangulated_member_buckling_uses_centre_to_centre_minimum():
    r = run(triangulated_member_buckling())
    values = r["values"]
    assert r["checked_conditions_satisfied"]
    assert r["clauses"] == ["4.6.2", "4.6.3.5"]
    assert values["effective_length_factor"] == 1.0
    assert values["effective_length_mm"] == 3000
    assert values["elastic_buckling_load_kn"] == pytest.approx(986.9604401089358)


@pytest.mark.parametrize(
    ("assessed_length_mm", "rational_analysis_verified", "used_length_mm", "corrected"),
    [
        (2400, False, 3000, True),
        (3600, False, 3600, False),
        (2400, True, 2400, False),
    ],
)
def test_triangulated_member_buckling_effective_length_boundaries(
    assessed_length_mm, rational_analysis_verified, used_length_mm, corrected
):
    r = run(
        triangulated_member_buckling(
            effective_length_mm=assessed_length_mm,
            rational_buckling_analysis_consistent_with_appendix_g_verified=(
                rational_analysis_verified
            ),
        )
    )
    values = r["values"]
    assert r["checked_conditions_satisfied"]
    assert values["effective_length_mm"] == used_length_mm
    assert values["minimum_length_correction_applied"] is corrected


def test_triangulated_member_buckling_requires_structure_length_and_section_evidence():
    r = run(
        triangulated_member_buckling(
            triangulated_structure_verified=False,
            member_length_between_intersections_verified=False,
            effective_length_assessment_verified=False,
            second_moment_about_buckling_axis_verified=False,
        )
    )
    assert not r["checked_conditions_satisfied"]
    assert [check["satisfied"] for check in r["checks"]] == [False, False, True, False, False]


def braced_frame_buckling_factor(**overrides):
    inputs = {
        "operation": "braced_frame_buckling_factor",
        "rectangular_frame_verified": True,
        "all_members_braced_verified": True,
        "regular_loading_verified": True,
        "beam_axial_forces_negligible_verified": True,
        "frame_assessment_evidence_reference": "BRACED-FRAME-01",
        "design_load_set_id": "ULS-1",
        "design_load_set_actions_verified": True,
        "design_load_set_evidence_reference": "ULS-1-ACTIONS",
        "columns": [
            {
                "column_id": "BR-COL-01",
                "elastic_member_buckling_load_n_omb_kn": 900,
                "design_axial_force_n_star_kn": 300,
                "member_buckling_load_verified": True,
                "design_axial_force_verified": True,
                "evidence_reference": "BR-COL-01-LOADS",
            },
            {
                "column_id": "BR-COL-02",
                "elastic_member_buckling_load_n_omb_kn": 1500,
                "design_axial_force_n_star_kn": 300,
                "member_buckling_load_verified": True,
                "design_axial_force_verified": True,
                "evidence_reference": "BR-COL-02-LOADS",
            },
        ],
        "all_columns_in_frame_listed_verified": True,
        "column_list_evidence_reference": "BRACED-FRAME-COLUMNS",
    }
    inputs.update(overrides)
    return inputs


def test_braced_frame_buckling_factor_selects_lowest_column_ratio():
    r = run(braced_frame_buckling_factor())
    values = r["values"]
    assert r["checked_conditions_satisfied"]
    assert r["clauses"] == ["4.7.1", "4.7.2.1"]
    assert [column["lambda_m"] for column in values["columns"]] == [3.0, 5.0]
    assert values["governing_column_id"] == "BR-COL-01"
    assert values["lambda_c"] == 3.0
    assert values["design_load_set_id"] == "ULS-1"


def test_braced_frame_buckling_factor_requires_scope_action_and_column_evidence():
    inputs = braced_frame_buckling_factor(
        rectangular_frame_verified=False,
        all_members_braced_verified=False,
        regular_loading_verified=False,
        beam_axial_forces_negligible_verified=False,
        design_load_set_actions_verified=False,
        all_columns_in_frame_listed_verified=False,
    )
    inputs["columns"][0]["member_buckling_load_verified"] = False
    r = run(inputs)
    assert not r["checked_conditions_satisfied"]
    assert not all(check["satisfied"] for check in r["checks"])


def sway_frame_buckling_factor(**overrides):
    inputs = {
        "operation": "sway_frame_buckling_factor",
        "rectangular_frame_verified": True,
        "sway_member_classification_verified": True,
        "regular_loading_verified": True,
        "beam_axial_forces_negligible_verified": True,
        "frame_assessment_evidence_reference": "SWAY-FRAME-01",
        "design_load_set_id": "ULS-SWAY-1",
        "design_load_set_actions_verified": True,
        "design_load_set_evidence_reference": "ULS-SWAY-1-ACTIONS",
        "storeys": [
            {
                "storey_id": "LEVEL-1",
                "columns": [
                    {
                        "column_id": "SW-COL-1A",
                        "elastic_member_buckling_load_n_oms_kn": 900,
                        "design_axial_force_n_star_kn": 300,
                        "member_length_mm": 3000,
                        "member_buckling_load_verified": True,
                        "design_axial_force_verified": True,
                        "member_length_verified": True,
                        "evidence_reference": "SW-COL-1A-LOADS",
                    },
                    {
                        "column_id": "SW-COL-1B",
                        "elastic_member_buckling_load_n_oms_kn": 400,
                        "design_axial_force_n_star_kn": -100,
                        "member_length_mm": 3000,
                        "member_buckling_load_verified": True,
                        "design_axial_force_verified": True,
                        "member_length_verified": True,
                        "evidence_reference": "SW-COL-1B-LOADS",
                    },
                ],
                "all_columns_in_storey_listed_verified": True,
                "column_list_evidence_reference": "LEVEL-1-COLUMNS",
            },
            {
                "storey_id": "LEVEL-2",
                "columns": [
                    {
                        "column_id": "SW-COL-2A",
                        "elastic_member_buckling_load_n_oms_kn": 1000,
                        "design_axial_force_n_star_kn": 400,
                        "member_length_mm": 3000,
                        "member_buckling_load_verified": True,
                        "design_axial_force_verified": True,
                        "member_length_verified": True,
                        "evidence_reference": "SW-COL-2A-LOADS",
                    }
                ],
                "all_columns_in_storey_listed_verified": True,
                "column_list_evidence_reference": "LEVEL-2-COLUMNS",
            },
        ],
        "all_storeys_in_frame_listed_verified": True,
        "storey_list_evidence_reference": "SWAY-FRAME-STOREYS",
    }
    inputs.update(overrides)
    return inputs


def test_sway_frame_buckling_factor_includes_tension_and_selects_lowest_storey():
    r = run(sway_frame_buckling_factor())
    values = r["values"]
    assert r["checked_conditions_satisfied"]
    assert r["clauses"] == ["4.7.1", "4.7.2.2"]
    assert values["storeys"][0]["lambda_ms"] == pytest.approx(6.5)
    assert values["storeys"][0]["sum_n_star_over_l_kn_per_mm"] == pytest.approx(200 / 3000)
    assert values["storeys"][1]["lambda_ms"] == pytest.approx(2.5)
    assert values["governing_storey_id"] == "LEVEL-2"
    assert values["lambda_c"] == pytest.approx(2.5)
    assert values["design_load_set_id"] == "ULS-SWAY-1"


def test_sway_frame_buckling_factor_rejects_nonpositive_storey_axial_sum():
    inputs = sway_frame_buckling_factor()
    inputs["storeys"][0]["columns"][0]["design_axial_force_n_star_kn"] = 50
    inputs["storeys"][0]["columns"][1]["design_axial_force_n_star_kn"] = -100
    with pytest.raises(ValueError, match="sum per length must be positive"):
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


def test_clause_4_4_2_2_transverse_load_beta_m_from_deflection_ratio():
    result = run(
        {
            "operation": "moment_amplification",
            "compression_kn": 600,
            "elastic_buckling_load_kn": 1000,
            "delta_ct_mm": 4,
            "delta_cw_mm": 10,
            "first_order_moment_knm": 20,
        }
    )

    assert result["values"]["beta_m"] == pytest.approx(0.2)
    assert result["values"]["beta_m_method"] == "4.4.2.2(c)_deflection_ratio"
    assert result["values"]["cm"] == pytest.approx(0.52)
    assert result["values"]["braced_factor"] == pytest.approx(1.3)
    assert result["values"]["governing_factor"] == pytest.approx(1.3)
    assert result["values"]["amplified_moment_knm"] == pytest.approx(26)
    assert result["values"]["delta_ct_mm"] == 4
    assert result["values"]["delta_cw_mm"] == 10
    assert result["clauses"] == ["4.4.1.2", "4.4.2.2(c)"]
    assert result["checked_conditions_satisfied"]


def test_clause_4_4_2_2_a_conservative_transverse_load_beta_m():
    result = run(
        {
            "operation": "moment_amplification",
            "compression_kn": 600,
            "elastic_buckling_load_kn": 1000,
            "conservative_transverse_beta_m": True,
            "first_order_moment_knm": 20,
        }
    )

    assert result["values"]["beta_m"] == -1
    assert result["values"]["beta_m_method"] == "4.4.2.2(a)_conservative_transverse_load"
    assert result["values"]["cm"] == 1
    assert result["values"]["braced_factor"] == pytest.approx(2.5)
    assert result["values"]["governing_factor"] == pytest.approx(2.5)
    assert result["values"]["amplified_moment_knm"] == pytest.approx(50)
    assert result["values"]["second_order_analysis_required"]
    assert result["clauses"] == ["4.4.1.2", "4.4.2.2(a)"]
    assert not result["checked_conditions_satisfied"]


def test_clause_4_4_2_2_transverse_beta_m_rejects_incomplete_or_inconsistent_inputs():
    base = {
        "operation": "moment_amplification",
        "compression_kn": 600,
        "elastic_buckling_load_kn": 1000,
        "first_order_moment_knm": 20,
    }
    cases = [
        ({"delta_ct_mm": 4}, "requires both delta_ct_mm and delta_cw_mm"),
        ({"delta_cw_mm": 10}, "requires both delta_ct_mm and delta_cw_mm"),
        (
            {"beta_m": 0.2, "delta_ct_mm": 4, "delta_cw_mm": 10},
            "Clause 4.4.2.2(c) deflections, not both",
        ),
        (
            {"conservative_transverse_beta_m": True, "beta_m": 0.2},
            "Use the Clause 4.4.2.2(a) route alone",
        ),
        (
            {"conservative_transverse_beta_m": True, "delta_ct_mm": 4, "delta_cw_mm": 10},
            "Use the Clause 4.4.2.2(a) route alone",
        ),
        (
            {"delta_ct_mm": 11, "delta_cw_mm": 10},
            "must produce beta_m within [-1, 1]",
        ),
        ({}, "Provide beta_m or both Clause 4.4.2.2(c) deflection values"),
    ]
    for changes, message in cases:
        with pytest.raises(ValueError) as error:
            run({**base, **changes})
        assert message in str(error.value)


@pytest.mark.parametrize(
    ("figure_case", "expected_beta_m"),
    [
        ("figure_a_left_1", -1.0),
        ("figure_a_left_2", 0.2),
        ("figure_a_left_3", 0.6),
        ("figure_a_left_4", -0.5),
        ("figure_a_left_5", 0.2),
        ("figure_a_left_6", 0.2),
        ("figure_a_right_1", -1.0),
        ("figure_a_right_2", 0.5),
        ("figure_a_right_3", 1.0),
        ("figure_a_right_4", 0.4),
        ("figure_a_right_5", 0.0),
        ("figure_a_right_6", 0.5),
        ("figure_b_left_1", -0.4),
        ("figure_b_left_2", 0.1),
        ("figure_b_left_3", 0.7),
        ("figure_b_left_4", -0.5),
        ("figure_b_left_5", -0.2),
        ("figure_b_right_1", -0.5),
        ("figure_b_right_2", -0.1),
        ("figure_b_right_3", 0.3),
        ("figure_b_right_4", -0.4),
        ("figure_b_right_5", -0.1),
        ("figure_b_right_6", 1.0),
    ],
)
def test_clause_4_4_2_2_figure_beta_m_cases(figure_case, expected_beta_m):
    result = run(
        {
            "operation": "moment_amplification",
            "compression_kn": 600,
            "elastic_buckling_load_kn": 1000,
            "beta_m_figure_case": figure_case,
            "first_order_moment_knm": 20,
        }
    )
    values = result["values"]
    expected_cm = min(1, 0.6 - 0.4 * expected_beta_m)
    expected_factor = max(1, expected_cm / (1 - 600 / 1000))

    assert values["beta_m"] == pytest.approx(expected_beta_m)
    assert values["beta_m_figure_case"] == figure_case
    assert values["beta_m_method"] == "4.4.2.2_figure_lookup"
    assert values["cm"] == pytest.approx(expected_cm)
    assert values["braced_factor"] == pytest.approx(expected_factor)
    assert values["amplified_moment_knm"] == pytest.approx(20 * expected_factor)
    figure = "A" if figure_case.startswith("figure_a_") else "B"
    assert values["beta_m_figure_reference"] == f"Figure 4.4.2.2({figure})"
    assert result["clauses"] == ["4.4.1.2", "4.4.2.2"]


def test_clause_4_4_2_2_figure_beta_m_cases_are_exclusive_and_symbolic_requires_beta():
    base = {
        "operation": "moment_amplification",
        "compression_kn": 600,
        "elastic_buckling_load_kn": 1000,
        "first_order_moment_knm": 20,
    }
    for extra in (
        {"beta_m": 0.2},
        {"delta_ct_mm": 4, "delta_cw_mm": 10},
        {"conservative_transverse_beta_m": True},
    ):
        with pytest.raises(ValueError):
            run({**base, "beta_m_figure_case": "figure_a_left_2", **extra})
    with pytest.raises(ValueError, match="requires beta_m"):
        run({**base, "beta_m_figure_case": "figure_b_left_6"})


def test_clause_4_4_2_2_figure_b_left_row_6_uses_supplied_symbolic_beta():
    result = run(
        {
            "operation": "moment_amplification",
            "compression_kn": 600,
            "elastic_buckling_load_kn": 1000,
            "beta_m_figure_case": "figure_b_left_6",
            "beta_m": 0.3,
            "first_order_moment_knm": 20,
        }
    )
    values = result["values"]

    assert values["beta_m"] == pytest.approx(0.3)
    assert values["beta_m_method"] == "4.4.2.2_figure_symbolic_beta"
    assert values["beta_m_figure_reference"] == "Figure 4.4.2.2(B)"
    assert values["cm"] == pytest.approx(0.48)
    assert values["braced_factor"] == pytest.approx(1.2)
    assert values["amplified_moment_knm"] == pytest.approx(24)
    assert result["clauses"] == ["4.4.1.2", "4.4.2.2"]


def test_clause_4_4_2_2_figure_b_left_row_6_derives_beta_from_verified_end_moments():
    result = run(
        {
            "operation": "moment_amplification",
            "compression_kn": 600,
            "elastic_buckling_load_kn": 1000,
            "beta_m_figure_case": "figure_b_left_6",
            "end_moment_1_abs_knm": 20,
            "end_moment_2_abs_knm": 50,
            "end_moment_curvature": "reverse_curvature",
            "end_moments_only_verified": True,
            "end_moment_curvature_verified": True,
            "end_moment_evidence_reference": "BENCHMARK-FIGURE-B-LEFT-6-END-MOMENTS",
            "first_order_moment_knm": 50,
        }
    )
    values = result["values"]

    # Independent hand arithmetic: beta=20/50=0.4, Cm=0.6-0.4(0.4)=0.44,
    # delta_b=0.44/(1-600/1000)=1.1, and M*=50(1.1)=55 kN.m.
    assert values["beta_m"] == pytest.approx(0.4)
    assert values["beta_m_end_moment_ratio"] == pytest.approx(0.4)
    assert values["beta_m_method"] == "4.4.2.2_figure_symbolic_beta_end_moment_ratio"
    assert values["beta_m_figure_reference"] == "Figure 4.4.2.2(B)"
    assert values["end_moment_curvature"] == "reverse_curvature"
    assert values["cm"] == pytest.approx(0.44)
    assert values["braced_factor"] == pytest.approx(1.1)
    assert values["amplified_moment_knm"] == pytest.approx(55)
    assert values["end_moment_evidence_reference"] == "BENCHMARK-FIGURE-B-LEFT-6-END-MOMENTS"
    assert result["clauses"] == ["4.4.1.2", "4.4.2.2"]


def test_clause_4_4_2_2_figure_b_left_row_6_rejects_incompatible_beta_basis():
    base = {
        "operation": "moment_amplification",
        "compression_kn": 600,
        "elastic_buckling_load_kn": 1000,
        "beta_m_figure_case": "figure_b_left_6",
        "end_moment_1_abs_knm": 20,
        "end_moment_2_abs_knm": 50,
        "end_moment_curvature": "single_curvature",
        "end_moments_only_verified": True,
        "end_moment_curvature_verified": True,
        "end_moment_evidence_reference": "BENCHMARK-FIGURE-B-LEFT-6-END-MOMENTS",
        "first_order_moment_knm": 50,
    }
    with pytest.raises(ValueError, match="depicts reverse curvature"):
        run(base)
    with pytest.raises(ValueError, match="another beta basis"):
        run({**base, "beta_m_figure_case": "figure_b_left_5"})
    with pytest.raises(ValueError, match="nonnegative"):
        run(
            {
                "operation": "moment_amplification",
                "compression_kn": 600,
                "elastic_buckling_load_kn": 1000,
                "beta_m_figure_case": "figure_b_left_6",
                "beta_m": -0.3,
                "first_order_moment_knm": 50,
            }
        )


@pytest.mark.parametrize(
    ("curvature", "expected_beta_m", "expected_cm", "expected_factor"),
    [
        ("reverse_curvature", 0.4, 0.44, 1.1),
        ("single_curvature", -0.4, 0.76, 1.9),
    ],
)
def test_clause_4_4_2_2_end_moment_ratio(curvature, expected_beta_m, expected_cm, expected_factor):
    result = run(
        {
            "operation": "moment_amplification",
            "compression_kn": 600,
            "elastic_buckling_load_kn": 1000,
            "end_moment_1_abs_knm": 20,
            "end_moment_2_abs_knm": 50,
            "end_moment_curvature": curvature,
            "end_moments_only_verified": True,
            "end_moment_curvature_verified": True,
            "end_moment_evidence_reference": "BENCHMARK-END-MOMENT-DISTRIBUTION-01",
            "first_order_moment_knm": 50,
        }
    )
    values = result["values"]

    assert values["beta_m"] == pytest.approx(expected_beta_m)
    assert values["beta_m_end_moment_ratio"] == pytest.approx(0.4)
    assert values["end_moment_curvature"] == curvature
    assert values["beta_m_method"] == "4.4.2.2_end_moment_ratio"
    assert values["cm"] == pytest.approx(expected_cm)
    assert values["braced_factor"] == pytest.approx(expected_factor)
    assert values["amplified_moment_knm"] == pytest.approx(50 * expected_factor)
    assert result["clauses"] == ["4.4.1.2", "4.4.2.2"]


def test_clause_4_4_2_2_end_moment_ratio_requires_consistent_complete_evidence():
    inputs = {
        "operation": "moment_amplification",
        "compression_kn": 600,
        "elastic_buckling_load_kn": 1000,
        "end_moment_1_abs_knm": 20,
        "end_moment_2_abs_knm": 50,
        "end_moment_curvature": "reverse_curvature",
        "end_moments_only_verified": True,
        "end_moment_curvature_verified": True,
        "end_moment_evidence_reference": "BENCHMARK-END-MOMENT-DISTRIBUTION-01",
        "first_order_moment_knm": 50,
    }
    with pytest.raises(ValueError, match="larger absolute end moment"):
        run({**inputs, "first_order_moment_knm": 49})
    with pytest.raises(ValueError, match="cannot be combined with another beta basis"):
        run({**inputs, "beta_m": 0.4})
    with pytest.raises(ValueError, match="both moment magnitudes"):
        run({key: value for key, value in inputs.items() if key != "end_moment_evidence_reference"})
    with pytest.raises(ValueError, match="non-zero end moment"):
        run(
            {
                **inputs,
                "end_moment_1_abs_knm": 0,
                "end_moment_2_abs_knm": 0,
                "first_order_moment_knm": 0,
            }
        )


@pytest.mark.parametrize("axial_force_kn", [0, -50])
def test_clause_4_4_2_2_zero_or_tensile_axial_force_needs_no_braced_amplification_inputs(
    axial_force_kn,
):
    result = run(
        {
            "operation": "moment_amplification",
            "compression_kn": axial_force_kn,
            "first_order_moment_knm": 20,
        }
    )

    assert result["values"]["beta_m"] is None
    assert result["values"]["beta_m_method"] == "not_required_zero_or_tensile_axial_force"
    assert result["values"]["cm"] is None
    assert result["values"]["braced_factor"] == 1
    assert result["values"]["governing_factor"] == 1
    assert result["values"]["amplified_moment_knm"] == 20
    assert result["clauses"] == ["4.4.2.2"]
    assert result["checked_conditions_satisfied"]


def nonprincipal_bending_unconstrained_member(**overrides):
    evidence = "NONPRINCIPAL-UNCONSTRAINED-01"
    inputs = {
        "operation": "nonprincipal_bending_unconstrained_analysis",
        "design_load_set_id": "ULS-NONPRINCIPAL-02",
        "member_id": "BEAM-NP-02",
        "member_length_mm": 4000,
        "load_plane_angle_deg": 30,
        "principal_properties_verified": True,
        "principal_properties_evidence_reference": evidence,
        "continuous_lateral_restraint_absent_verified": True,
        "restraint_absence_evidence_reference": evidence,
        "support_translation_conditions_verified": True,
        "support_conditions_evidence_reference": evidence,
        "elastic_prismatic_model_verified": True,
        "analysis_model_evidence_reference": evidence,
        "distributed_loads": [
            {
                "load_id": "UDL-02",
                "start_fraction": 0,
                "end_fraction": 1,
                "transverse_force_start_kn_per_m": 2,
                "transverse_force_end_kn_per_m": 2,
                "load_verified": True,
                "evidence_reference": evidence,
            }
        ],
        "point_loads": [],
        "complete_load_set_verified": True,
        "load_set_evidence_reference": evidence,
        "section_axial_capacity_kn": 1000,
        "section_moment_x_knm": 100,
        "section_moment_y_knm": 50,
        "reduced_member_moment_x_knm": 80,
        "reduced_member_moment_y_knm": 40,
        "section_and_member_capacities_verified": True,
        "capacity_evidence_reference": evidence,
        "axial_action_kn": 0,
    }
    inputs.update(overrides)
    return inputs


def nonprincipal_bending_member(**overrides):
    evidence = "NONPRINCIPAL-ANALYSIS-01"
    inputs = {
        "operation": "nonprincipal_bending_analysis",
        "design_load_set_id": "ULS-NONPRINCIPAL-01",
        "member_id": "BEAM-NP-01",
        "member_length_mm": 4000,
        "restraint_plane_angle_deg": 45,
        "second_moment_about_principal_x_mm4": 200e6,
        "second_moment_about_principal_y_mm4": 50e6,
        "principal_properties_verified": True,
        "principal_properties_evidence_reference": evidence,
        "continuous_lateral_restraint_verified": True,
        "continuous_lateral_restraint_evidence_reference": evidence,
        "support_translation_conditions_verified": True,
        "support_conditions_evidence_reference": evidence,
        "elastic_prismatic_model_verified": True,
        "analysis_model_evidence_reference": evidence,
        "distributed_loads": [
            {
                "load_id": "UDL-01",
                "start_fraction": 0,
                "end_fraction": 1,
                "transverse_force_start_kn_per_m": 2,
                "transverse_force_end_kn_per_m": 2,
                "load_verified": True,
                "evidence_reference": evidence,
            }
        ],
        "point_loads": [],
        "complete_load_set_verified": True,
        "load_set_evidence_reference": evidence,
        "section_axial_capacity_kn": 1000,
        "section_moment_x_knm": 100,
        "section_moment_y_knm": 50,
        "reduced_member_moment_x_knm": 80,
        "reduced_member_moment_y_knm": 40,
        "section_and_member_capacities_verified": True,
        "capacity_evidence_reference": evidence,
        "axial_action_kn": 0,
    }
    inputs.update(overrides)
    return inputs


def test_clause_5_7_1_rigid_continuous_restraint_hand_benchmark():
    result = run(nonprincipal_bending_member())
    values = result["values"]
    root_two = sqrt(2)

    # EI_x / EI_y = 4. Compatibility gives r = 3/5, then the 4 kN.m
    # simple-beam maximum resolves into the principal-axis moments below.
    assert values["continuous_lateral_restraint_force_ratio"] == pytest.approx(0.6)
    assert values["principal_x_transverse_load_coefficient"] == pytest.approx(0.4 / root_two)
    assert values["principal_y_transverse_load_coefficient"] == pytest.approx(1.6 / root_two)
    assert values["maximum_abs_moment_about_principal_x_knm"] == pytest.approx(6.4 / root_two)
    assert values["maximum_abs_moment_about_principal_y_knm"] == pytest.approx(1.6 / root_two)
    assert values["maximum_x_moment_position_mm"] == pytest.approx(2000)
    assert values["maximum_y_moment_position_mm"] == pytest.approx(2000)

    restraint = values["lateral_restraint_distributed_loads"][0]
    assert restraint["start_force_x_kn_per_m"] == pytest.approx(-1.2 / root_two)
    assert restraint["start_force_y_kn_per_m"] == pytest.approx(1.2 / root_two)
    assert restraint["end_force_x_kn_per_m"] == pytest.approx(-1.2 / root_two)
    assert restraint["end_force_y_kn_per_m"] == pytest.approx(1.2 / root_two)
    assert values["transverse_equilibrium_residual_x_kn"] == pytest.approx(0, abs=1e-12)
    assert values["transverse_equilibrium_residual_y_kn"] == pytest.approx(0, abs=1e-12)
    assert result["clauses"] == ["5.7.1", "8.3.4"]
    assert result["checked_conditions_satisfied"]


def test_clause_5_7_1_equal_principal_inertias_need_no_restraint_force():
    result = run(
        nonprincipal_bending_member(
            restraint_plane_angle_deg=30,
            second_moment_about_principal_x_mm4=100e6,
            second_moment_about_principal_y_mm4=100e6,
            distributed_loads=[],
            point_loads=[
                {
                    "load_id": "MIDSPAN-01",
                    "position_fraction": 0.5,
                    "transverse_force_kn": 8,
                    "load_verified": True,
                    "evidence_reference": "NONPRINCIPAL-POINT-01",
                }
            ],
        )
    )
    values = result["values"]

    assert values["continuous_lateral_restraint_force_ratio"] == pytest.approx(0)
    assert values["total_lateral_restraint_resultant_x_kn"] == pytest.approx(0)
    assert values["total_lateral_restraint_resultant_y_kn"] == pytest.approx(0)
    assert values["maximum_abs_moment_about_principal_x_knm"] == pytest.approx(4)
    assert values["maximum_abs_moment_about_principal_y_knm"] == pytest.approx(4 * sqrt(3))
    assert values["lateral_restraint_point_loads"][0]["force_x_kn"] == pytest.approx(0)
    assert values["lateral_restraint_point_loads"][0]["force_y_kn"] == pytest.approx(0)
    assert result["checked_conditions_satisfied"]


def test_clause_5_7_1_rejects_compression_without_second_order_analysis():
    with pytest.raises(ValueError, match="does not include axial-force effects"):
        run(nonprincipal_bending_member(axial_action_kn=100))


def test_clause_5_7_2_unconstrained_simply_supported_hand_benchmark():
    result = run(nonprincipal_bending_unconstrained_member())
    values = result["values"]

    # The 4 kN.m major-plane beam moment resolves directly at 30 degrees.
    assert values["principal_x_transverse_load_coefficient"] == pytest.approx(sqrt(3) / 2)
    assert values["principal_y_transverse_load_coefficient"] == pytest.approx(0.5)
    assert values["maximum_abs_moment_about_principal_x_knm"] == pytest.approx(2)
    assert values["maximum_abs_moment_about_principal_y_knm"] == pytest.approx(2 * sqrt(3))
    assert values["principal_x_support_reactions_kn"] == pytest.approx([-2 * sqrt(3), -2 * sqrt(3)])
    assert values["principal_y_support_reactions_kn"] == pytest.approx([-2, -2])
    assert values["maximum_x_moment_position_mm"] == pytest.approx(2000)
    assert values["maximum_y_moment_position_mm"] == pytest.approx(2000)
    assert result["clauses"] == ["5.7.2", "8.3.4", "8.4.5"]
    assert result["checked_conditions_satisfied"]


def test_clause_5_7_2_rejects_compression_without_second_order_analysis():
    with pytest.raises(ValueError, match="does not include axial-force effects"):
        run(nonprincipal_bending_unconstrained_member(axial_action_kn=100))


def appendix_e_superposition_member(**overrides):
    evidence = "APPENDIX-E2-C-SUPERPOSITION-01"
    inputs = {
        "operation": "appendix_e_superposition_member_moment",
        "design_load_set_id": "ULS-E2C-01",
        "member_id": "BEAM-01",
        "member_length_mm": 4000,
        "member_geometry_verified": True,
        "member_geometry_evidence_reference": evidence,
        "second_order_start_moment_knm": 0,
        "second_order_end_moment_knm": 0,
        "second_order_end_moments_verified": True,
        "second_order_end_moment_evidence_reference": evidence,
        "end_moment_sign_convention_verified": True,
        "end_moment_sign_evidence_reference": evidence,
        "distributed_loads": [
            {
                "load_id": "UDL-01",
                "start_fraction": 0,
                "end_fraction": 1,
                "transverse_force_start_kn_per_m": 2.5,
                "transverse_force_end_kn_per_m": 2.5,
                "load_verified": True,
                "evidence_reference": evidence,
            }
        ],
        "point_loads": [],
        "all_transverse_loads_listed_verified": True,
        "transverse_load_list_evidence_reference": evidence,
        "simple_beam_model_verified": True,
        "simple_beam_model_evidence_reference": evidence,
        "bending_axis_verified": True,
        "bending_axis_evidence_reference": evidence,
    }
    inputs.update(overrides)
    return inputs


def test_appendix_e2c_uniform_load_superposition_and_postprocessing():
    superposition = run(appendix_e_superposition_member())
    values = superposition["values"]

    assert values["simple_beam_reaction_start_kn"] == pytest.approx(5)
    assert values["simple_beam_reaction_end_kn"] == pytest.approx(5)
    assert values["maximum_second_order_moment_knm"] == pytest.approx(5)
    assert values["maximum_moment_position_mm"] == pytest.approx(2000)
    assert values["governing_candidate_type"] == "stationary_point"
    assert superposition["checked_conditions_satisfied"]

    design = run(
        {
            "operation": "appendix_e_design_bending_moment",
            "design_load_set_id": "ULS-E2C-01",
            "second_order_method": "superposition",
            "maximum_second_order_moment_knm": values["maximum_second_order_moment_knm"],
            "maximum_second_order_moment_verified": True,
            "second_order_analysis_evidence_reference": "APPENDIX-E2-C-SUPERPOSITION-01",
            "compression_kn": 20,
            "compression_force_verified": True,
            "compression_force_evidence_reference": "ULS-E2C-01-FORCE",
            "elastic_buckling_load_kn": 100,
            "elastic_buckling_load_verified": True,
            "buckling_load_evidence_reference": "APPENDIX-E2C-NOMB-01",
            "braced_member_verified": True,
            "braced_member_evidence_reference": "APPENDIX-E2C-BRACING-01",
            "beta_m_basis_verified": True,
            "beta_m_evidence_reference": "APPENDIX-E2C-BETA-01",
            "beta_m": -1,
        }
    )
    assert design["values"]["delta_b"] == pytest.approx(1.25)
    assert design["values"]["design_bending_moment_knm"] == pytest.approx(6.25)


def test_appendix_e2c_finds_maximum_for_triangular_distributed_load():
    result = run(
        appendix_e_superposition_member(
            member_length_mm=5000,
            distributed_loads=[
                {
                    "load_id": "TRIANGULAR-01",
                    "start_fraction": 0,
                    "end_fraction": 1,
                    "transverse_force_start_kn_per_m": 0,
                    "transverse_force_end_kn_per_m": 4,
                    "load_verified": True,
                    "evidence_reference": "TRIANGULAR-LOAD-01",
                }
            ],
        )
    )
    expected_position_mm = sqrt((2 * (10 / 3)) / 8e-7)
    expected_moment_knm = (
        (10 / 3) * expected_position_mm - 8e-7 * expected_position_mm**3 / 6
    ) / 1000

    assert result["values"]["simple_beam_reaction_start_kn"] == pytest.approx(10 / 3)
    assert result["values"]["maximum_moment_position_mm"] == pytest.approx(expected_position_mm)
    assert result["values"]["maximum_second_order_moment_knm"] == pytest.approx(expected_moment_knm)
    assert result["values"]["governing_candidate_type"] == "stationary_point"


def test_appendix_e2c_combines_second_order_end_moments_with_point_load():
    result = run(
        appendix_e_superposition_member(
            second_order_start_moment_knm=2,
            second_order_end_moment_knm=-2,
            distributed_loads=[],
            point_loads=[
                {
                    "load_id": "MIDSPAN-01",
                    "position_fraction": 0.5,
                    "transverse_force_kn": 10,
                    "load_verified": True,
                    "evidence_reference": "MIDSPAN-LOAD-01",
                }
            ],
        )
    )

    assert result["values"]["simple_beam_reaction_start_kn"] == pytest.approx(5)
    assert result["values"]["simple_beam_reaction_end_kn"] == pytest.approx(5)
    assert result["values"]["maximum_second_order_moment_knm"] == pytest.approx(10)
    assert result["values"]["maximum_moment_position_fraction"] == pytest.approx(0.5)


def test_appendix_e2c_applies_linear_end_moment_gradient_to_distributed_load():
    result = run(
        appendix_e_superposition_member(
            second_order_start_moment_knm=1,
            second_order_end_moment_knm=-1,
        )
    )

    assert result["values"]["maximum_second_order_moment_knm"] == pytest.approx(5.05)
    assert result["values"]["maximum_moment_position_mm"] == pytest.approx(1800)


def test_appendix_e_design_moment_applies_braced_factor_to_second_order_moment():
    result = run(
        {
            "operation": "appendix_e_design_bending_moment",
            "design_load_set_id": "BENCHMARK-BRACED-MEMBER-01",
            "second_order_method": "element_end_moments",
            "maximum_second_order_moment_knm": -24,
            "maximum_second_order_moment_verified": True,
            "second_order_analysis_evidence_reference": "BENCHMARK-E2-MEMBER-MOMENT-01",
            "compression_kn": 50,
            "compression_force_verified": True,
            "compression_force_evidence_reference": "BENCHMARK-MEMBER-FORCE-01",
            "elastic_buckling_load_kn": 200,
            "elastic_buckling_load_verified": True,
            "buckling_load_evidence_reference": "BENCHMARK-SAME-AXIS-NOMB-01",
            "braced_member_verified": True,
            "braced_member_evidence_reference": "BENCHMARK-BRACING-01",
            "beta_m_basis_verified": True,
            "beta_m_evidence_reference": "BENCHMARK-BETA-M-BASIS-01",
            "beta_m": -1,
        }
    )

    values = result["values"]
    assert values["maximum_second_order_moment_knm"] == pytest.approx(-24)
    assert values["cm"] == pytest.approx(1)
    assert values["delta_b"] == pytest.approx(4 / 3)
    assert values["design_bending_moment_knm"] == pytest.approx(-32)
    assert values["design_bending_moment_magnitude_knm"] == pytest.approx(32)
    assert values["beta_m_method"] == "supplied"
    assert result["clauses"] == ["4.4.2.2", "4.6.2", "E.2"]
    assert result["checked_conditions_satisfied"]


@pytest.mark.parametrize("compression_kn", [0, -50])
def test_appendix_e_design_moment_does_not_amplify_zero_or_tension(compression_kn):
    result = run(
        {
            "operation": "appendix_e_design_bending_moment",
            "design_load_set_id": "ULS-TENSION-01",
            "second_order_method": "direct_analysis",
            "maximum_second_order_moment_knm": -12,
            "maximum_second_order_moment_verified": True,
            "second_order_analysis_evidence_reference": "E2-DIRECT-ANALYSIS-01",
            "compression_kn": compression_kn,
            "compression_force_verified": True,
            "compression_force_evidence_reference": "ULS-TENSION-01-FORCES",
        }
    )

    assert result["values"]["delta_b"] == 1
    assert result["values"]["design_bending_moment_knm"] == -12
    assert result["values"]["beta_m_method"] == "not_required_zero_or_tensile_axial_force"
    assert result["clauses"] == ["4.4.2.2", "E.2"]
    assert result["checked_conditions_satisfied"]


def test_appendix_e_design_moment_requires_stable_same_axis_compression_inputs():
    inputs = {
        "operation": "appendix_e_design_bending_moment",
        "design_load_set_id": "ULS-COLUMN-01",
        "second_order_method": "element_end_moments",
        "maximum_second_order_moment_knm": 10,
        "maximum_second_order_moment_verified": True,
        "second_order_analysis_evidence_reference": "E2-ELEMENT-ENDS-01",
        "compression_kn": 50,
        "compression_force_verified": True,
        "compression_force_evidence_reference": "ULS-COLUMN-01-FORCES",
        "elastic_buckling_load_kn": 100,
        "elastic_buckling_load_verified": True,
        "buckling_load_evidence_reference": "CLAUSE-4-6-2-COLUMN-01",
        "braced_member_verified": True,
        "braced_member_evidence_reference": "COLUMN-BRACING-01",
        "beta_m_basis_verified": True,
        "beta_m_evidence_reference": "COLUMN-BETA-M-01",
        "beta_m": 0,
    }

    with pytest.raises(ValueError, match="elastic instability"):
        run({**inputs, "elastic_buckling_load_kn": 50})
    with pytest.raises(ValueError, match="not valid under any of the given schemas"):
        run({key: value for key, value in inputs.items() if key != "beta_m"})


def test_clause_4_4_2_2_positive_compression_requires_elastic_buckling_load():
    with pytest.raises(ValueError) as error:
        run(
            {
                "operation": "moment_amplification",
                "compression_kn": 600,
                "beta_m": 0.2,
                "first_order_moment_knm": 20,
            }
        )

    assert "Positive compression requires elastic_buckling_load_kn" in str(error.value)


def test_clause_4_4_2_3_sway_factor_combines_with_transverse_load_amplification():
    result = run(
        {
            "operation": "moment_amplification",
            "compression_kn": 600,
            "elastic_buckling_load_kn": 1000,
            "delta_ct_mm": 4,
            "delta_cw_mm": 10,
            "first_order_moment_knm": 20,
            "sway_buckling_factor": 2,
        }
    )

    assert result["values"]["braced_factor"] == pytest.approx(1.3)
    assert result["values"]["sway_factor"] == pytest.approx(2)
    assert result["values"]["governing_factor"] == pytest.approx(2)
    assert result["values"]["amplified_moment_knm"] == pytest.approx(40)
    assert result["clauses"] == ["4.4.1.2", "4.4.2.2(c)", "4.4.2.3"]
    assert not result["checked_conditions_satisfied"]


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
