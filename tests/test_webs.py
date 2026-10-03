# SPDX-License-Identifier: AGPL-3.0-only
import pytest

from opencalcs_as4100.webs import buckling_alpha
from opencalcs_as4100.webs import run_webs as run


def test_web_buckling_reduction_against_standard_table():
    # Table 6.3.3(C), alpha_b=0.5; differences limited to published rounding.
    assert buckling_alpha(50, 250) == pytest.approx(0.808, abs=0.00051)
    assert buckling_alpha(100, 250) == pytest.approx(0.485, abs=0.00051)


def minimum_web_thickness(design_case="unstiffened", **changes):
    inputs = {
        "operation": "web_minimum_thickness",
        "design_case": design_case,
        "clear_web_depth_mm": 1000,
        "web_thickness_mm": 6,
        "web_yield_mpa": 250,
    }
    if design_case == "unstiffened":
        inputs.update({"edge_condition": "both_flange_bounded", "geometry_verified": True})
    elif design_case == "transversely_stiffened":
        inputs.update(
            {
                "stiffener_spacing_mm": 1000,
                "greatest_panel_depth_mm": 1000,
                "stiffener_layout_verified": True,
            }
        )
    elif design_case == "longitudinal_and_transverse":
        inputs.update(
            {
                "stiffener_spacing_mm": 1000,
                "d2_mm": 800,
                "neutral_axis_stiffener_set_present": False,
                "stiffener_layout_verified": True,
            }
        )
    else:
        inputs.update(
            {
                "hinge_zone_load_kn": 100,
                "design_web_shear_yield_capacity_kn": 1000,
                "bearing_or_shear_within_half_depth_of_hinge_verified": True,
                "load_bearing_stiffeners_provided": False,
                "stiffeners_within_half_depth_verified": False,
                "stiffener_design_5_14_verified": False,
            }
        )
    inputs.update(changes)
    return run(inputs)


@pytest.mark.parametrize(
    "edge_condition,denominator",
    [("both_flange_bounded", 180), ("one_longitudinal_edge_free", 90)],
)
def test_clause_5_10_1_unstiffened_web_minimum_thickness(edge_condition, denominator):
    out = minimum_web_thickness(
        edge_condition=edge_condition,
        web_thickness_mm=1000 / denominator,
    )
    assert out["values"]["required_web_thickness_mm"] == pytest.approx(1000 / denominator)
    assert out["checks"][0]["satisfied"]


@pytest.mark.parametrize(
    "ratio,expected",
    [(0.5, 1000 / 270), (0.74, 1000 / 270), (0.8, 4), (1, 5), (3, 5)],
)
def test_clause_5_10_4_transverse_stiffener_spacing_branches(ratio, expected):
    out = minimum_web_thickness(
        "transversely_stiffened",
        stiffener_spacing_mm=1000 * ratio,
    )
    assert out["values"]["required_web_thickness_mm"] == pytest.approx(expected)


def test_clause_5_10_4_long_panels_are_treated_as_unstiffened():
    out = minimum_web_thickness(
        "transversely_stiffened",
        stiffener_spacing_mm=1600,
        greatest_panel_depth_mm=500,
    )
    assert out["values"]["web_treated_as_unstiffened"]
    assert out["values"]["required_web_thickness_mm"] == pytest.approx(1000 / 180)
    assert out["clauses"] == ["5.10.1", "5.10.4"]


@pytest.mark.parametrize(
    "ratio,expected",
    [(0.73, 1000 / 340), (0.74, 0.74 * 1000 / 250), (1, 4), (2.4, 4)],
)
def test_clause_5_10_5_longitudinal_and_transverse_stiffener_branches(ratio, expected):
    out = minimum_web_thickness(
        "longitudinal_and_transverse",
        stiffener_spacing_mm=1000 * ratio,
    )
    assert out["values"]["required_web_thickness_mm"] == pytest.approx(expected)
    assert out["values"]["compression_flange_stiffener_target_distance_mm"] == pytest.approx(160)


def test_clause_5_10_5_additional_neutral_axis_stiffener_requirement():
    out = minimum_web_thickness(
        "longitudinal_and_transverse",
        stiffener_spacing_mm=800,
        neutral_axis_stiffener_set_present=True,
    )
    assert out["values"]["required_web_thickness_mm"] == pytest.approx(3.2)
    with pytest.raises(ValueError, match="thickness equation applies only"):
        minimum_web_thickness(
            "longitudinal_and_transverse",
            stiffener_spacing_mm=1600,
            neutral_axis_stiffener_set_present=True,
        )


def test_clause_5_10_6_plastic_hinge_thickness_and_stiffener_trigger():
    boundary = minimum_web_thickness(
        "plastic_hinge",
        clear_web_depth_mm=820,
        web_thickness_mm=10,
        hinge_zone_load_kn=100,
        design_web_shear_yield_capacity_kn=1000,
    )
    assert boundary["values"]["required_web_thickness_mm"] == 10
    assert not boundary["values"]["hinge_zone_stiffeners_required"]
    inputs = {
        "design_case": "plastic_hinge",
        "clear_web_depth_mm": 820,
        "web_thickness_mm": 10,
        "web_yield_mpa": 250,
        "hinge_zone_load_kn": 100.001,
        "design_web_shear_yield_capacity_kn": 1000,
        "bearing_or_shear_within_half_depth_of_hinge_verified": True,
        "load_bearing_stiffeners_provided": True,
        "stiffeners_within_half_depth_verified": True,
        "stiffener_design_5_14_verified": True,
    }
    assert run({"operation": "web_minimum_thickness", **inputs})["checked_conditions_satisfied"]
    inputs["stiffeners_within_half_depth_verified"] = False
    assert not run({"operation": "web_minimum_thickness", **inputs})["checked_conditions_satisfied"]


def test_clause_5_10_7_unstiffened_opening_geometry_and_spacing_boundaries():
    inputs = {
        "operation": "web_opening_geometry",
        "clear_web_depth_mm": 1000,
        "opening_internal_dimension_mm": 100,
        "longitudinal_stiffeners_present": False,
        "adjacent_openings_present": True,
        "adjacent_opening_boundary_spacing_mm": 300,
        "unstiffened_openings_at_cross_section": 1,
        "multiple_openings_rational_analysis_verified": False,
        "opening_geometry_verified": True,
    }
    assert run(inputs)["checked_conditions_satisfied"]
    inputs["opening_internal_dimension_mm"] = 101
    assert not run(inputs)["checked_conditions_satisfied"]
    inputs["opening_internal_dimension_mm"] = 100
    inputs["adjacent_opening_boundary_spacing_mm"] = 299.999
    assert not run(inputs)["checked_conditions_satisfied"]


def test_clause_5_10_7_longitudinally_stiffened_opening_limit_and_multiple_openings():
    out = run(
        {
            "operation": "web_opening_geometry",
            "clear_web_depth_mm": 1000,
            "opening_internal_dimension_mm": 330,
            "longitudinal_stiffeners_present": True,
            "adjacent_openings_present": False,
            "adjacent_opening_boundary_spacing_mm": 0,
            "unstiffened_openings_at_cross_section": 2,
            "multiple_openings_rational_analysis_verified": True,
            "opening_geometry_verified": True,
        }
    )
    assert out["checked_conditions_satisfied"]
    assert out["values"]["permitted_ratio"] == 0.33


def test_clause_5_10_2_load_bearing_stiffener_trigger_boundaries():
    inputs = {
        "operation": "load_bearing_stiffener_requirement",
        "design_compressive_bearing_force_kn": 100,
        "design_web_bearing_capacity_kn": 100,
        "end_post_required_under_5_15_2_2": False,
        "load_bearing_stiffeners_provided": False,
    }
    boundary = run(inputs)
    assert not boundary["values"]["stiffeners_required"]
    assert boundary["checked_conditions_satisfied"]

    inputs["design_compressive_bearing_force_kn"] = 100.001
    above = run(inputs)
    assert above["values"]["required_by_web_bearing_capacity"]
    assert not above["checked_conditions_satisfied"]

    inputs["load_bearing_stiffeners_provided"] = True
    assert run(inputs)["checked_conditions_satisfied"]

    inputs["design_compressive_bearing_force_kn"] = 0
    inputs["end_post_required_under_5_15_2_2"] = True
    out = run(inputs)
    assert out["values"]["required_to_form_end_post"]
    assert out["values"]["stiffeners_required"]


def test_clause_5_10_3_side_plate_shear_is_limited_by_each_force_path():
    inputs = {
        "operation": "web_side_reinforcement",
        "design_shear_share_kn": 40,
        "side_plate_design_shear_capacity_kn": 60,
        "fastener_design_shear_capacity_to_web_kn": 45,
        "fastener_design_shear_capacity_to_flanges_kn": 40,
        "symmetry_effects_accounted": True,
    }
    boundary = run(inputs)
    assert boundary["values"]["maximum_supported_shear_share_kn"] == 40
    assert boundary["checked_conditions_satisfied"]

    inputs["design_shear_share_kn"] = 40.001
    assert not run(inputs)["checked_conditions_satisfied"]

    inputs["design_shear_share_kn"] = 30
    inputs["symmetry_effects_accounted"] = False
    assert not run(inputs)["checked_conditions_satisfied"]


def test_open_section_web_yield_independent_arithmetic():
    r = run(
        {
            "operation": "web_bearing",
            "section_type": "i_or_channel",
            "web_thickness_mm": 10,
            "web_yield_mpa": 300,
            "clear_web_depth_mm": 200,
            "bearing_width_at_flange_mm": 100,
            "bearing_width_at_neutral_axis_mm": 200,
            "restrained_flange_count": 2,
            "bearing_action_kn": 100,
        }
    )
    assert r["values"]["bearing_yield_kn"] == 375
    assert r["values"]["geometric_slenderness"] == 50
    assert r["checks"][0]["design_capacity"] <= 337.5


def test_clause_5_13_1_calculates_i_section_bearing_dispersion_geometry():
    inputs = {
        "operation": "web_bearing",
        "section_type": "i_or_channel",
        "web_thickness_mm": 10,
        "web_yield_mpa": 300,
        "clear_web_depth_mm": 200,
        "stiff_bearing_length_mm": 20,
        "flange_thickness_mm": 12,
        "distance_flange_to_neutral_axis_mm": 90,
        "bearing_geometry_verified": True,
        "restrained_flange_count": 2,
        "bearing_action_kn": 100,
    }
    r = run(inputs)
    assert r["values"]["bearing_width_at_flange_mm"] == 80
    assert r["values"]["bearing_width_at_neutral_axis_mm"] == 260
    assert r["values"]["bearing_yield_kn"] == 300
    assert r["values"]["geometric_slenderness"] == 50
    assert r["checks"][1]["satisfied"]

    inputs["bearing_geometry_verified"] = False
    unverified = run(inputs)
    assert not unverified["checks"][1]["satisfied"]
    assert not unverified["checked_conditions_satisfied"]


def test_clause_5_13_1_rejects_ambiguous_or_out_of_range_dispersion_inputs():
    geometry = {
        "operation": "web_bearing",
        "section_type": "i_or_channel",
        "web_thickness_mm": 10,
        "web_yield_mpa": 300,
        "clear_web_depth_mm": 200,
        "stiff_bearing_length_mm": 20,
        "flange_thickness_mm": 12,
        "distance_flange_to_neutral_axis_mm": 90,
        "bearing_geometry_verified": True,
        "restrained_flange_count": 2,
        "bearing_action_kn": 100,
    }
    with pytest.raises(ValueError, match="Distance to the neutral axis"):
        run(geometry | {"distance_flange_to_neutral_axis_mm": 201})
    with pytest.raises(ValueError, match="Invalid input"):
        run(
            geometry
            | {
                "bearing_width_at_flange_mm": 80,
                "bearing_width_at_neutral_axis_mm": 260,
            }
        )


def test_rhs_bearing_bending_two_branches_and_individual_failure():
    d = {
        "operation": "rhs_bearing_bending",
        "bearing_action_kn": 50,
        "design_bearing_capacity_kn": 100,
        "moment_action_knm": 5,
        "design_moment_capacity_knm": 10,
        "stiff_bearing_length_mm": 200,
        "section_width_mm": 200,
        "clear_web_depth_mm": 200,
        "web_thickness_mm": 10,
    }
    assert run(d)["values"]["interaction"] == pytest.approx(1.1)
    d["stiff_bearing_length_mm"] = 199
    assert run(d)["values"]["interaction"] == pytest.approx(0.9)
    d["bearing_action_kn"] = 101
    assert not run(d)["checked_conditions_satisfied"]


def load_bearing_stiffener(**changes):
    return {
        "operation": "load_bearing_stiffener",
        "web_bearing_yield_kn": 100,
        "stiffener_area_mm2": 1000,
        "contact_stiffener_area_mm2": 1000,
        "web_yield_mpa": 250,
        "stiffener_yield_mpa": 250,
        "web_thickness_mm": 10,
        "clear_web_depth_mm": 200,
        "panel_spacing_mm": 300,
        "radius_of_gyration_mm": 50,
        "both_flanges_rotation_restrained": True,
        "available_web_width_left_mm": 200,
        "available_web_width_right_mm": 0,
        "stiffener_outstand_mm": 100,
        "stiffener_thickness_mm": 10,
        "outer_edge_continuously_stiffened": False,
        "bearing_action_kn": 100,
        **changes,
    }


def test_load_bearing_stiffener_effective_width():
    r = run(load_bearing_stiffener())
    assert r["values"]["effective_area_mm2"] == 2500
    assert r["values"]["effective_length_mm"] == 140
    assert r["values"]["bearing_yield_kn"] == 350


def test_clause_5_14_4_checks_fit_flange_provision_and_web_force_transfer():
    inputs = {
        "operation": "load_bearing_stiffener_attachment",
        "design_bearing_force_kn": 70,
        "design_force_share_to_web_kn": 40,
        "web_connection_design_capacity_kn": 40,
        "tight_uniform_bearing_against_loaded_flange_verified": True,
        "concentrated_force_directly_over_support": True,
        "both_flanges_fitted_or_connected_verified": True,
    }
    r = run(inputs)
    assert r["checked_conditions_satisfied"]
    assert r["values"]["maximum_supported_web_force_share_kn"] == 40

    inputs["both_flanges_fitted_or_connected_verified"] = False
    assert not run(inputs)["checks"][1]["satisfied"]
    inputs["both_flanges_fitted_or_connected_verified"] = True
    inputs["web_connection_design_capacity_kn"] = 39.999
    assert not run(inputs)["checks"][2]["satisfied"]
    inputs["web_connection_design_capacity_kn"] = 40
    inputs["tight_uniform_bearing_against_loaded_flange_verified"] = False
    inputs["flange_to_stiffener_connection_design_capacity_kn"] = 69.999
    assert not run(inputs)["checks"][0]["satisfied"]
    inputs["flange_to_stiffener_connection_design_capacity_kn"] = 70
    assert run(inputs)["checks"][0]["satisfied"]


def test_mixed_strength_stiffener_outstand_and_contact_area():
    full = run(
        load_bearing_stiffener(
            web_yield_mpa=250,
            stiffener_yield_mpa=450,
            stiffener_outstand_mm=150,
        )
    )
    reduced = run(
        load_bearing_stiffener(
            web_yield_mpa=250,
            stiffener_yield_mpa=450,
            stiffener_outstand_mm=150,
            contact_stiffener_area_mm2=500,
        )
    )
    assert reduced["values"]["effective_area_mm2"] == 2500
    assert reduced["values"]["bearing_buckling_kn"] == pytest.approx(
        full["values"]["bearing_buckling_kn"]
    )
    assert reduced["values"]["outstand_limit_mm"] == pytest.approx(150 / 1.8**0.5)
    assert reduced["values"]["outstand_limit_mm"] < 150
    assert not reduced["checks"][2]["satisfied"]
    assert not reduced["checked_conditions_satisfied"]
    assert full["values"]["bearing_yield_kn"] == 550
    assert reduced["values"]["bearing_yield_kn"] == 325


def test_clause_5_14_5_torsional_end_restraint_minimum_inertia():
    inputs = load_bearing_stiffener(
        torsional_end_restraint_required=True,
        critical_flange_centroid_spacing_mm=250,
        critical_flange_thickness_mm=10,
        total_design_load_between_supports_kn=1000,
        stiffener_pair_second_moment_about_web_centerline_mm4=62500,
    )
    r = run(inputs)
    assert r["values"]["torsional_restraint_factor"] == 4
    assert r["values"]["required_stiffener_pair_second_moment_mm4"] == 62500
    assert r["checks"][-1]["satisfied"]

    inputs["stiffener_pair_second_moment_about_web_centerline_mm4"] = 62499
    assert not run(inputs)["checks"][-1]["satisfied"]


def test_clause_5_14_5_inputs_are_conditional_and_complete():
    inputs = load_bearing_stiffener(torsional_end_restraint_required=True)
    with pytest.raises(ValueError, match="required"):
        run(inputs)


def test_clause_5_15_1_stiffener_termination_gaps_at_four_web_thicknesses():
    inputs = {
        "operation": "transverse_stiffener",
        "clear_web_depth_mm": 200,
        "web_panel_depth_mm": 200,
        "web_thickness_mm": 10,
        "panel_spacing_mm": 200,
        "web_area_mm2": 2000,
        "web_yield_mpa": 250,
        "shear_buckling_coefficient": 0.5,
        "stiffener_configuration": "pair",
        "shear_action_kn": 20,
        "nominal_web_shear_kn": 100,
        "nominal_web_buckling_no_tension_field_kn": 100,
        "nominal_stiffener_buckling_kn": 100,
        "stiffener_area_mm2": 1000,
        "stiffener_second_moment_mm4": 200000,
        "stiffener_outstand_mm": 100,
        "stiffener_thickness_mm": 10,
        "stiffener_yield_mpa": 250,
        "outer_edge_continuously_stiffened": False,
        "stiffener_top_flange_gap_mm": 40,
        "stiffener_bottom_flange_gap_mm": 40,
        "flange_termination_geometry_verified": True,
    }
    r = run(inputs)
    assert "5.15.1" in r["clauses"]
    assert r["values"]["maximum_flange_termination_gap_mm"] == 40
    assert all(check["satisfied"] for check in r["checks"][-3:])

    inputs["stiffener_bottom_flange_gap_mm"] = 40.001
    assert not run(inputs)["checks"][-2]["satisfied"]
    inputs["stiffener_bottom_flange_gap_mm"] = 40
    inputs["flange_termination_geometry_verified"] = False
    assert not run(inputs)["checks"][-1]["satisfied"]


def test_clause_5_15_9_end_post_minimum_area_with_kilonewton_conversion():
    inputs = {
        "operation": "end_post_area",
        "end_post_required_under_5_15_2_2": True,
        "clear_web_depth_mm": 1000,
        "design_shear_action_kn": 180,
        "capacity_factor": 0.9,
        "shear_buckling_coefficient": 0.5,
        "nominal_web_shear_yield_capacity_kn": 100,
        "end_plate_to_load_bearing_stiffener_distance_mm": 25,
        "end_plate_yield_mpa": 250,
        "end_plate_area_mm2": 3000,
    }
    r = run(inputs)
    assert r["values"]["residual_panel_shear_kn"] == 150
    assert r["values"]["minimum_end_plate_area_mm2"] == 3000
    assert r["checks"][0]["satisfied"]

    inputs["end_plate_area_mm2"] = 2999.999
    assert not run(inputs)["checks"][0]["satisfied"]


def test_clause_5_15_9_end_post_area_floors_nonpositive_residual_shear():
    r = run(
        {
            "operation": "end_post_area",
            "end_post_required_under_5_15_2_2": True,
            "clear_web_depth_mm": 1000,
            "design_shear_action_kn": 45,
            "capacity_factor": 0.9,
            "shear_buckling_coefficient": 0.5,
            "nominal_web_shear_yield_capacity_kn": 100,
            "end_plate_to_load_bearing_stiffener_distance_mm": 25,
            "end_plate_yield_mpa": 250,
            "end_plate_area_mm2": 0,
        }
    )
    assert r["values"]["residual_panel_shear_kn"] == 0
    assert r["values"]["minimum_end_plate_area_mm2"] == 0
    assert r["checked_conditions_satisfied"]


def test_clause_5_15_7_1_increases_transverse_stiffener_inertia_for_external_actions():
    inputs = {
        "operation": "transverse_stiffener",
        "clear_web_depth_mm": 200,
        "web_panel_depth_mm": 200,
        "web_thickness_mm": 10,
        "panel_spacing_mm": 200,
        "web_area_mm2": 2000,
        "web_yield_mpa": 250,
        "shear_buckling_coefficient": 0.5,
        "stiffener_configuration": "pair",
        "shear_action_kn": 20,
        "nominal_web_shear_kn": 100,
        "nominal_web_buckling_no_tension_field_kn": 100,
        "nominal_stiffener_buckling_kn": 100,
        "stiffener_area_mm2": 1000,
        "stiffener_second_moment_mm4": 350000,
        "stiffener_outstand_mm": 100,
        "stiffener_thickness_mm": 10,
        "stiffener_yield_mpa": 250,
        "outer_edge_continuously_stiffened": False,
        "external_normal_force_kn": 10,
        "external_moment_knm": 2,
        "external_parallel_force_kn": 5,
        "force_eccentricity_mm": 50,
        "capacity_factor": 0.9,
        "external_actions_verified": True,
    }
    r = run(inputs)
    assert r["values"]["external_action_term_kn"] == 31.25
    assert r["values"]["external_load_stiffness_increase_mm4"] == pytest.approx(138888.8888889)
    assert r["values"]["required_second_moment_with_external_actions_mm4"] == pytest.approx(
        288888.8888889
    )
    assert all(check["satisfied"] for check in r["checks"][-2:])

    inputs["stiffener_second_moment_mm4"] = 288888
    assert not run(inputs)["checks"][-2]["satisfied"]
    inputs["stiffener_second_moment_mm4"] = 350000
    inputs["external_actions_verified"] = False
    assert not run(inputs)["checks"][-1]["satisfied"]


def test_clause_5_15_7_1_requires_complete_external_action_inputs():
    with pytest.raises(ValueError, match="Invalid input"):
        run(
            {
                "operation": "transverse_stiffener",
                "clear_web_depth_mm": 200,
                "web_panel_depth_mm": 200,
                "web_thickness_mm": 10,
                "panel_spacing_mm": 200,
                "web_area_mm2": 2000,
                "web_yield_mpa": 250,
                "shear_buckling_coefficient": 0.5,
                "stiffener_configuration": "pair",
                "shear_action_kn": 20,
                "nominal_web_shear_kn": 100,
                "nominal_web_buckling_no_tension_field_kn": 100,
                "nominal_stiffener_buckling_kn": 100,
                "stiffener_area_mm2": 1000,
                "stiffener_second_moment_mm4": 350000,
                "stiffener_outstand_mm": 100,
                "stiffener_thickness_mm": 10,
                "stiffener_yield_mpa": 250,
                "outer_edge_continuously_stiffened": False,
                "external_normal_force_kn": 10,
            }
        )


def test_web_bearing_rejects_zero_restrained_flanges():
    with pytest.raises(ValueError, match="restrained_flange_count"):
        run(
            {
                "operation": "web_bearing",
                "section_type": "i_or_channel",
                "web_thickness_mm": 10,
                "web_yield_mpa": 300,
                "clear_web_depth_mm": 200,
                "bearing_width_at_flange_mm": 100,
                "bearing_width_at_neutral_axis_mm": 200,
                "restrained_flange_count": 0,
                "bearing_action_kn": 100,
            }
        )


def test_web_stiffener_rejects_yield_strength_above_as4100_scope():
    for field in ("web_yield_mpa", "stiffener_yield_mpa"):
        with pytest.raises(ValueError, match=field):
            run(load_bearing_stiffener(**{field: 690.1}))


@pytest.mark.parametrize("location,inertia", [("neutral_axis", 200000), ("0.2_depth", 3200000)])
def test_longitudinal_stiffener_minimum(location, inertia):
    d = {
        "operation": "longitudinal_stiffener",
        "web_depth_mm": 200,
        "web_thickness_mm": 10,
        "stiffener_area_mm2": 1000,
        "stiffener_second_moment_mm4": inertia,
        "location": location,
    }
    assert run(d)["values"]["minimum_second_moment_mm4"] == inertia
    assert run(d)["checked_conditions_satisfied"]


def test_clause_5_16_1_continuity_or_attached_transverse_ends():
    inputs = {
        "operation": "longitudinal_stiffener",
        "web_depth_mm": 200,
        "web_thickness_mm": 10,
        "stiffener_area_mm2": 1000,
        "stiffener_second_moment_mm4": 3200000,
        "location": "0.2_depth",
        "stiffener_continuous": True,
        "extends_between_transverse_stiffeners": False,
        "attached_to_transverse_stiffeners": False,
    }
    continuous = run(inputs)
    assert "5.16.1" in continuous["clauses"]
    assert continuous["checks"][0]["satisfied"]

    inputs["stiffener_continuous"] = False
    inputs["extends_between_transverse_stiffeners"] = True
    inputs["attached_to_transverse_stiffeners"] = True
    assert run(inputs)["checks"][0]["satisfied"]
    inputs["attached_to_transverse_stiffeners"] = False
    assert not run(inputs)["checks"][0]["satisfied"]


def test_clause_5_16_1_detail_inputs_must_be_complete():
    with pytest.raises(ValueError, match="Invalid input"):
        run(
            {
                "operation": "longitudinal_stiffener",
                "web_depth_mm": 200,
                "web_thickness_mm": 10,
                "stiffener_area_mm2": 1000,
                "stiffener_second_moment_mm4": 3200000,
                "location": "0.2_depth",
                "stiffener_continuous": False,
            }
        )
