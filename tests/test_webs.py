# SPDX-License-Identifier: AGPL-3.0-only
from math import sqrt

import pytest

from engcalcs_as4100.webs import buckling_alpha
from engcalcs_as4100.webs import run_webs as run


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
                "greatest_panel_longitudinal_dimension_mm": 1000,
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
    if (
        "greatest_panel_depth_mm" in changes
        and "greatest_panel_longitudinal_dimension_mm" not in changes
    ):
        inputs.pop("greatest_panel_longitudinal_dimension_mm")
    inputs.update(changes)
    return run(inputs)


def web_panel_geometry(**changes):
    inputs = {
        "operation": "web_panel_geometry",
        "web_longitudinal_extent_mm": 3000,
        "clear_web_depth_mm": 600,
        "web_length_panel_boundaries_mm": [600, 1800],
        "web_depth_panel_boundaries_mm": [200],
        "web_panel_geometry_verified": True,
        "web_panel_geometry_evidence_reference": "drawing WEB-01, revision C",
    }
    return run(inputs | changes)


def test_clause_5_9_2_derives_panel_dimensions_from_clear_boundary_stations():
    output = web_panel_geometry()
    values = output["values"]
    assert output["clauses"] == ["5.9.2"]
    assert values["longitudinal_panel_dimensions_mm"] == [600, 1200, 1200]
    assert values["clear_transverse_panel_dimensions_mm"] == [200, 400]
    assert values["maximum_d_p_mm"] == 1200
    assert values["greatest_panel_longitudinal_dimension_mm"] == 1200
    assert values["maximum_d_1_mm"] == 400
    assert values["maximum_d_p_panel_id"] == "WP-2-1"
    assert values["maximum_d_1_panel_id"] == "WP-1-2"
    assert values["panel_count"] == 6
    assert values["panels"][0] == {
        "panel_id": "WP-1-1",
        "web_length_start_mm": 0,
        "web_length_end_mm": 600,
        "clear_depth_start_mm": 0,
        "clear_depth_end_mm": 200,
        "d_p_mm": 600,
        "d_1_mm": 200,
    }
    assert output["checked_conditions_satisfied"]


def test_clause_5_9_2_accepts_one_panel_and_rejects_invalid_boundary_stations():
    one_panel = web_panel_geometry(
        web_length_panel_boundaries_mm=[],
        web_depth_panel_boundaries_mm=[],
    )
    assert one_panel["values"]["panel_count"] == 1
    assert one_panel["values"]["maximum_d_p_mm"] == 3000
    assert one_panel["values"]["maximum_d_1_mm"] == 600

    with pytest.raises(ValueError, match="strictly increasing"):
        web_panel_geometry(web_length_panel_boundaries_mm=[1800, 600])
    with pytest.raises(ValueError, match="internal to its web dimension"):
        web_panel_geometry(web_depth_panel_boundaries_mm=[600])
    with pytest.raises(ValueError, match="Invalid input"):
        web_panel_geometry(web_panel_geometry_verified=False)
    with pytest.raises(ValueError, match="must not be blank"):
        web_panel_geometry(web_panel_geometry_evidence_reference=" ")


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
    "design_case",
    ["unstiffened", "transversely_stiffened", "longitudinal_and_transverse", "plastic_hinge"],
)
def test_clause_5_9_3_is_traced_for_every_prescriptive_thickness_route(design_case):
    out = minimum_web_thickness(design_case)
    assert out["clauses"][0] == "5.9.3"
    assert out["checks"][0]["clause"].startswith("5.10.")


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
    assert out["clauses"] == ["5.9.3", "5.10.1", "5.10.4"]
    assert out["values"]["legacy_panel_dimension_alias_used"]


def test_clause_5_10_4_longitudinal_panel_dimension_can_exceed_clear_web_depth():
    out = minimum_web_thickness(
        "transversely_stiffened",
        clear_web_depth_mm=400,
        stiffener_spacing_mm=600,
        greatest_panel_longitudinal_dimension_mm=800,
    )
    values = out["values"]
    assert values["required_web_thickness_mm"] == pytest.approx(2)
    assert values["greatest_panel_longitudinal_dimension_mm"] == 800
    assert values["stiffener_spacing_to_clear_web_depth_ratio"] == pytest.approx(1.5)
    assert values[
        "stiffener_spacing_to_greatest_panel_longitudinal_dimension_ratio"
    ] == pytest.approx(0.75)
    assert not values["legacy_panel_dimension_alias_used"]
    assert not values["web_treated_as_unstiffened"]


@pytest.mark.parametrize(
    "spacing,treated_as_unstiffened,expected",
    [(1200, False, 5), (1200.4, True, 1000 / 180)],
)
def test_clause_5_10_4_uses_strict_greater_than_three_s_over_dp_boundary(
    spacing, treated_as_unstiffened, expected
):
    out = minimum_web_thickness(
        "transversely_stiffened",
        clear_web_depth_mm=1000,
        stiffener_spacing_mm=spacing,
        greatest_panel_longitudinal_dimension_mm=400,
    )
    values = out["values"]
    assert values["required_web_thickness_mm"] == pytest.approx(expected)
    assert values["web_treated_as_unstiffened"] is treated_as_unstiffened


def test_clause_5_10_4_rejects_conflicting_canonical_and_legacy_dimensions():
    with pytest.raises(ValueError, match="must match"):
        minimum_web_thickness(
            "transversely_stiffened",
            greatest_panel_longitudinal_dimension_mm=1000,
            greatest_panel_depth_mm=900,
        )


def test_clause_5_10_4_fails_closed_for_unlisted_s_over_d1_band():
    with pytest.raises(ValueError, match="does not give a thickness band"):
        minimum_web_thickness(
            "transversely_stiffened",
            clear_web_depth_mm=400,
            stiffener_spacing_mm=1201,
            greatest_panel_longitudinal_dimension_mm=800,
        )


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


@pytest.mark.parametrize(
    "residual,plasticity_limit,satisfied",
    [("SR", 10, True), ("HR", 9, True), ("CF", 8, False), ("LW", 8, False), ("HW", 8, False)],
)
def test_clause_5_10_6_checks_flat_stiffener_plates_under_clause_5_2_2(
    residual, plasticity_limit, satisfied
):
    out = minimum_web_thickness(
        "plastic_hinge",
        flat_stiffener_plates=[
            {
                "clear_outstand_mm": 80,
                "thickness_mm": 10,
                "yield_mpa": 250,
                "residual_stress_category": residual,
            }
        ],
    )
    assert "5.2.2" in out["clauses"]
    assert out["values"]["flat_stiffener_plate_checks"] == [
        {
            "plate_number": 1,
            "slenderness": 8,
            "plasticity_limit": plasticity_limit,
            "residual_stress_category": residual,
            "satisfied": satisfied,
        }
    ]
    classification_check = next(
        check
        for check in out["checks"]
        if check["clause"] == "5.10.6 flat-plate stiffener plasticity classification under 5.2.2"
    )
    assert classification_check["satisfied"] is satisfied


def test_clause_5_10_6_checks_every_supplied_flat_stiffener_plate_and_yield_stress():
    out = minimum_web_thickness(
        "plastic_hinge",
        flat_stiffener_plates=[
            {
                "clear_outstand_mm": 79,
                "thickness_mm": 10,
                "yield_mpa": 250,
                "residual_stress_category": "SR",
            },
            {
                "clear_outstand_mm": 80,
                "thickness_mm": 10,
                "yield_mpa": 350,
                "residual_stress_category": "HR",
            },
        ],
    )
    plate_checks = out["values"]["flat_stiffener_plate_checks"]
    assert plate_checks[0]["slenderness"] == pytest.approx(7.9)
    assert plate_checks[0]["satisfied"]
    assert plate_checks[1]["slenderness"] == pytest.approx(8 * (350 / 250) ** 0.5)
    assert not plate_checks[1]["satisfied"]
    assert not next(
        check
        for check in out["checks"]
        if check["clause"] == "5.10.6 flat-plate stiffener plasticity classification under 5.2.2"
    )["satisfied"]

    with pytest.raises(ValueError, match="Invalid input"):
        minimum_web_thickness("plastic_hinge", flat_stiffener_plates=[{"thickness_mm": 10}])


def test_clause_5_10_7_unstiffened_opening_geometry_and_spacing_boundaries():
    inputs = {
        "operation": "web_opening_geometry",
        "clear_web_depth_mm": 1000,
        "opening_internal_dimension_mm": 100,
        "longitudinal_stiffeners_present": False,
        "adjacent_openings_present": True,
        "adjacent_opening_boundary_spacing_mm": 300,
        "adjacent_opening_greatest_internal_dimension_mm": 100,
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

    inputs["adjacent_opening_greatest_internal_dimension_mm"] = 150
    inputs["adjacent_opening_boundary_spacing_mm"] = 449.999
    too_close_to_larger_neighbor = run(inputs)
    assert too_close_to_larger_neighbor["values"]["required_adjacent_opening_spacing_mm"] == 450
    assert not too_close_to_larger_neighbor["checked_conditions_satisfied"]

    inputs["adjacent_opening_boundary_spacing_mm"] = 450
    assert run(inputs)["checked_conditions_satisfied"]

    del inputs["adjacent_opening_greatest_internal_dimension_mm"]
    missing_neighbor_dimension = run(inputs)
    checks = {check["clause"]: check for check in missing_neighbor_dimension["checks"]}
    assert not checks["5.10.7 adjacent opening greatest internal dimension"]["satisfied"]
    assert not missing_neighbor_dimension["checked_conditions_satisfied"]


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


def web_opening_layout_geometry(**changes):
    inputs = {
        "operation": "web_opening_layout_geometry",
        "clear_web_depth_mm": 1500,
        "longitudinal_stiffeners_present": False,
        "openings": [
            {
                "opening_id": "left",
                "longitudinal_start_mm": 0,
                "longitudinal_end_mm": 100,
                "transverse_start_mm": 0,
                "transverse_end_mm": 100,
                "greatest_internal_dimension_mm": 100,
            },
            {
                "opening_id": "right",
                "longitudinal_start_mm": 550,
                "longitudinal_end_mm": 700,
                "transverse_start_mm": 0,
                "transverse_end_mm": 150,
                "greatest_internal_dimension_mm": 150,
            },
        ],
        "opening_geometry_verified": True,
        "opening_geometry_reference": "DRAWING-OPENINGS-01",
        "opening_layout_complete_verified": True,
        "all_openings_unstiffened_verified": True,
        "castellated_member_present": False,
        "multiple_openings_rational_analysis_shows_stiffeners_unnecessary_verified": False,
        "rational_analysis_reference": None,
    }
    inputs.update(changes)
    return run(inputs)


def test_clause_5_10_7_complete_opening_layout_checks_size_and_adjacent_spacing():
    out = web_opening_layout_geometry()
    values = out["values"]
    assert out["clauses"] == ["5.10.7"]
    assert values["opening_count"] == 2
    assert [item["opening_dimension_to_web_depth_ratio"] for item in values["openings"]] == [
        pytest.approx(100 / 1500),
        pytest.approx(150 / 1500),
    ]
    assert values["adjacent_opening_pair_count"] == 1
    pair = values["adjacent_opening_spacing_checks"][0]
    assert pair["left_opening_id"] == "left"
    assert pair["right_opening_id"] == "right"
    assert pair["provided_boundary_spacing_mm"] == 450
    assert pair["required_boundary_spacing_mm"] == 450
    assert pair["satisfied"]
    assert values["maximum_openings_at_any_cross_section"] == 1
    assert out["checked_conditions_satisfied"]
    assert out["full_standard_compliance"] is False

    too_close = web_opening_layout_geometry(
        openings=[
            {
                "opening_id": "left",
                "longitudinal_start_mm": 0,
                "longitudinal_end_mm": 100,
                "transverse_start_mm": 0,
                "transverse_end_mm": 100,
                "greatest_internal_dimension_mm": 100,
            },
            {
                "opening_id": "right",
                "longitudinal_start_mm": 549.999,
                "longitudinal_end_mm": 699.999,
                "transverse_start_mm": 0,
                "transverse_end_mm": 150,
                "greatest_internal_dimension_mm": 150,
            },
        ]
    )
    assert not too_close["values"]["adjacent_opening_spacing_checks"][0]["satisfied"]
    assert not too_close["checked_conditions_satisfied"]


def test_clause_5_10_7_layout_derives_neighbors_in_each_transverse_band():
    out = web_opening_layout_geometry(
        openings=[
            {
                "opening_id": "first",
                "longitudinal_start_mm": 0,
                "longitudinal_end_mm": 100,
                "transverse_start_mm": 0,
                "transverse_end_mm": 60,
                "greatest_internal_dimension_mm": 100,
            },
            {
                "opening_id": "middle",
                "longitudinal_start_mm": 550,
                "longitudinal_end_mm": 700,
                "transverse_start_mm": 0,
                "transverse_end_mm": 100,
                "greatest_internal_dimension_mm": 150,
            },
            {
                "opening_id": "last",
                "longitudinal_start_mm": 1150,
                "longitudinal_end_mm": 1300,
                "transverse_start_mm": 40,
                "transverse_end_mm": 100,
                "greatest_internal_dimension_mm": 150,
            },
        ]
    )
    pairs = {
        (item["left_opening_id"], item["right_opening_id"]): item
        for item in out["values"]["adjacent_opening_spacing_checks"]
    }
    assert set(pairs) == {("first", "middle"), ("middle", "last")}
    assert pairs[("first", "middle")]["vertical_overlap_start_mm"] == 0
    assert pairs[("first", "middle")]["vertical_overlap_end_mm"] == 60
    assert pairs[("middle", "last")]["vertical_overlap_start_mm"] == 40
    assert pairs[("middle", "last")]["vertical_overlap_end_mm"] == 100
    assert all(item["satisfied"] for item in pairs.values())
    assert out["checked_conditions_satisfied"]


def test_clause_5_10_7_layout_checks_each_opening_ratio_and_stiffened_limit():
    too_large = web_opening_layout_geometry(
        openings=[
            {
                "opening_id": "oversize",
                "longitudinal_start_mm": 0,
                "longitudinal_end_mm": 100,
                "transverse_start_mm": 0,
                "transverse_end_mm": 151,
                "greatest_internal_dimension_mm": 151,
            }
        ]
    )
    assert too_large["values"]["openings"][0][
        "opening_dimension_to_web_depth_ratio"
    ] == pytest.approx(151 / 1500)
    assert not too_large["checked_conditions_satisfied"]

    at_stiffened_limit = web_opening_layout_geometry(
        clear_web_depth_mm=1000,
        longitudinal_stiffeners_present=True,
        openings=[
            {
                "opening_id": "stiffened-limit",
                "longitudinal_start_mm": 0,
                "longitudinal_end_mm": 100,
                "transverse_start_mm": 0,
                "transverse_end_mm": 330,
                "greatest_internal_dimension_mm": 330,
            }
        ],
    )
    assert at_stiffened_limit["values"]["permitted_opening_dimension_ratio"] == 0.33
    assert at_stiffened_limit["checked_conditions_satisfied"]

    above_stiffened_limit = web_opening_layout_geometry(
        clear_web_depth_mm=1000,
        longitudinal_stiffeners_present=True,
        openings=[
            {
                "opening_id": "above-limit",
                "longitudinal_start_mm": 0,
                "longitudinal_end_mm": 100,
                "transverse_start_mm": 0,
                "transverse_end_mm": 331,
                "greatest_internal_dimension_mm": 331,
            }
        ],
    )
    assert not above_stiffened_limit["checked_conditions_satisfied"]


def test_clause_5_10_7_layout_is_order_independent_and_checks_stacked_openings():
    original = web_opening_layout_geometry()
    reversed_layout = web_opening_layout_geometry(
        openings=[
            {
                "opening_id": "right",
                "longitudinal_start_mm": 550,
                "longitudinal_end_mm": 700,
                "transverse_start_mm": 0,
                "transverse_end_mm": 150,
                "greatest_internal_dimension_mm": 150,
            },
            {
                "opening_id": "left",
                "longitudinal_start_mm": 0,
                "longitudinal_end_mm": 100,
                "transverse_start_mm": 0,
                "transverse_end_mm": 100,
                "greatest_internal_dimension_mm": 100,
            },
        ]
    )
    assert reversed_layout["values"]["openings"] == original["values"]["openings"]
    assert (
        reversed_layout["values"]["adjacent_opening_spacing_checks"]
        == original["values"]["adjacent_opening_spacing_checks"]
    )

    stacked = [
        {
            "opening_id": "lower",
            "longitudinal_start_mm": 0,
            "longitudinal_end_mm": 100,
            "transverse_start_mm": 0,
            "transverse_end_mm": 40,
            "greatest_internal_dimension_mm": 100,
        },
        {
            "opening_id": "upper",
            "longitudinal_start_mm": 0,
            "longitudinal_end_mm": 100,
            "transverse_start_mm": 60,
            "transverse_end_mm": 100,
            "greatest_internal_dimension_mm": 100,
        },
    ]
    without_analysis = web_opening_layout_geometry(openings=stacked)
    cross_section = without_analysis["checks"][-1]
    assert cross_section["maximum_openings_at_cross_section"] == 2
    assert not cross_section["satisfied"]
    assert without_analysis["values"]["adjacent_opening_pair_count"] == 0
    assert not without_analysis["checked_conditions_satisfied"]

    with_analysis = web_opening_layout_geometry(
        openings=stacked,
        multiple_openings_rational_analysis_shows_stiffeners_unnecessary_verified=True,
        rational_analysis_reference="ANALYSIS-OPENING-STACK-01",
    )
    assert with_analysis["checks"][-1]["satisfied"]
    assert with_analysis["checked_conditions_satisfied"]


def test_clause_5_10_7_layout_rejects_invalid_geometry_and_unreferenced_analysis():
    with pytest.raises(ValueError, match="positive longitudinal extent"):
        web_opening_layout_geometry(
            openings=[
                {
                    "opening_id": "invalid",
                    "longitudinal_start_mm": 100,
                    "longitudinal_end_mm": 100,
                    "transverse_start_mm": 0,
                    "transverse_end_mm": 100,
                    "greatest_internal_dimension_mm": 100,
                }
            ]
        )

    with pytest.raises(ValueError, match="requires a reference"):
        web_opening_layout_geometry(
            multiple_openings_rational_analysis_shows_stiffeners_unnecessary_verified=True,
            rational_analysis_reference="  ",
        )

    with pytest.raises(ValueError, match="identifiers must be unique"):
        web_opening_layout_geometry(
            openings=[
                {
                    "opening_id": "same",
                    "longitudinal_start_mm": 0,
                    "longitudinal_end_mm": 100,
                    "transverse_start_mm": 0,
                    "transverse_end_mm": 100,
                    "greatest_internal_dimension_mm": 100,
                },
                {
                    "opening_id": "SAME",
                    "longitudinal_start_mm": 500,
                    "longitudinal_end_mm": 600,
                    "transverse_start_mm": 0,
                    "transverse_end_mm": 100,
                    "greatest_internal_dimension_mm": 100,
                },
            ]
        )


def web_shear_stress_field_postprocess(**changes):
    inputs = {
        "operation": "web_shear_stress_field_postprocess",
        "member_reference": "MEMBER-WEB-01",
        "section_form": "flat_web",
        "section_station_mm": 1200,
        "load_combination_reference": "ULS-COMBINATION-01",
        "rational_analysis_reference": "ELASTIC-FE-RESULTS-01",
        "rational_analysis_verified": True,
        "stress_component": "longitudinal_transverse_web_shear",
        "stress_component_verified": True,
        "section_cut_orientation_verified": True,
        "web_area_at_cut_mm2": 2000,
        "web_area_at_cut_basis_verified": True,
        "web_area_at_cut_reference": "WEB-SECTION-GEOMETRY-01",
        "quadrature_coverage_verified": True,
        "quadrature_coverage_reference": "WEB-MESH-AREA-01",
        "stress_samples": [
            {
                "integration_point_id": "lower-gauss-point",
                "design_shear_stress_mpa": 2.4,
                "cross_section_area_weight_mm2": 5000 / 9,
            },
            {
                "integration_point_id": "middle-gauss-point",
                "design_shear_stress_mpa": 6,
                "cross_section_area_weight_mm2": 8000 / 9,
            },
            {
                "integration_point_id": "upper-gauss-point",
                "design_shear_stress_mpa": 2.4,
                "cross_section_area_weight_mm2": 5000 / 9,
            },
        ],
        "expected_web_shear_force_kn": 8,
        "expected_web_shear_force_basis_verified": True,
        "expected_web_shear_force_reference": "SECTION-CUT-SHEAR-01",
        "governing_section_cut_verified": True,
        "governing_section_cut_reference": "GOVERNING-STATION-REVIEW-01",
        "governing_peak_shear_stress_mpa": 6,
        "governing_peak_assessment_verified": True,
        "governing_peak_assessment_reference": "WEB-PEAK-ASSESSMENT-01",
        "mesh_peak_sensitivity_verified": True,
        "mesh_peak_sensitivity_reference": "WEB-MESH-CONVERGENCE-01",
    }
    inputs.update(changes)
    return run(inputs)


def test_clause_5_11_3_stress_field_postprocess_matches_parabolic_web_solution():
    out = web_shear_stress_field_postprocess()
    values = out["values"]
    assert out["clauses"] == ["5.11.3"]
    assert values["quadrature_web_area_mm2"] == pytest.approx(2000)
    assert values["signed_web_shear_resultant_kn"] == pytest.approx(8)
    assert values["average_design_shear_stress_mpa"] == pytest.approx(4)
    assert values["sampled_peak_shear_stress_mpa"] == pytest.approx(6)
    assert values["stress_max_average_ratio"] == pytest.approx(1.5)
    assert values["clause_5_11_3_capacity_reduction_factor"] == pytest.approx(5 / 6)
    assert out["checked_conditions_satisfied"]
    assert out["full_standard_compliance"] is False


def test_clause_5_11_3_stress_field_uses_unequal_area_weights_and_sign():
    out = web_shear_stress_field_postprocess(
        web_area_at_cut_mm2=1000,
        stress_samples=[
            {
                "integration_point_id": "low-stress-large-area",
                "design_shear_stress_mpa": 1,
                "cross_section_area_weight_mm2": 750,
            },
            {
                "integration_point_id": "peak-stress-small-area",
                "design_shear_stress_mpa": 13,
                "cross_section_area_weight_mm2": 250,
            },
        ],
        expected_web_shear_force_kn=4,
        governing_peak_shear_stress_mpa=13,
    )
    values = out["values"]
    assert values["signed_web_shear_resultant_kn"] == pytest.approx(4)
    assert values["average_design_shear_stress_mpa"] == pytest.approx(4)
    assert values["stress_max_average_ratio"] == pytest.approx(3.25)
    assert values["clause_5_11_3_capacity_reduction_factor"] == pytest.approx(40 / 83)
    assert out["checked_conditions_satisfied"]

    reversed_sign = web_shear_stress_field_postprocess(
        stress_samples=[
            {
                "integration_point_id": "lower",
                "design_shear_stress_mpa": -2.4,
                "cross_section_area_weight_mm2": 5000 / 9,
            },
            {
                "integration_point_id": "middle",
                "design_shear_stress_mpa": -6,
                "cross_section_area_weight_mm2": 8000 / 9,
            },
            {
                "integration_point_id": "upper",
                "design_shear_stress_mpa": -2.4,
                "cross_section_area_weight_mm2": 5000 / 9,
            },
        ],
        expected_web_shear_force_kn=-8,
        governing_peak_shear_stress_mpa=6,
    )
    assert reversed_sign["values"]["signed_web_shear_resultant_kn"] == pytest.approx(-8)
    assert reversed_sign["values"]["signed_area_average_shear_stress_mpa"] == pytest.approx(-4)
    assert reversed_sign["checked_conditions_satisfied"]


def test_clause_5_11_3_uniform_web_stress_caps_the_reduction_factor_at_one():
    out = web_shear_stress_field_postprocess(
        web_area_at_cut_mm2=1000,
        stress_samples=[
            {
                "integration_point_id": "uniform-stress",
                "design_shear_stress_mpa": 4,
                "cross_section_area_weight_mm2": 1000,
            }
        ],
        expected_web_shear_force_kn=4,
        governing_peak_shear_stress_mpa=4,
    )
    values = out["values"]
    assert values["stress_max_average_ratio"] == pytest.approx(1)
    assert values["clause_5_11_3_capacity_reduction_factor"] == pytest.approx(1)
    assert out["checked_conditions_satisfied"]


def test_clause_5_11_3_stress_field_checks_area_and_section_equilibrium():
    area_mismatch = web_shear_stress_field_postprocess(web_area_at_cut_mm2=2001)
    area_check = next(
        check for check in area_mismatch["checks"] if "area coverage" in check["clause"]
    )
    assert not area_check["satisfied"]
    assert not area_mismatch["checked_conditions_satisfied"]

    force_mismatch = web_shear_stress_field_postprocess(expected_web_shear_force_kn=7.5)
    equilibrium = next(
        check for check in force_mismatch["checks"] if "equilibrium" in check["clause"]
    )
    assert equilibrium["equilibrium_residual_kn"] == pytest.approx(0.5)
    assert equilibrium["software_quality_tolerance_kn"] == pytest.approx(0.075)
    assert not equilibrium["satisfied"]
    assert not force_mismatch["checked_conditions_satisfied"]


def test_clause_5_11_3_stress_field_rejects_ambiguous_or_unreferenced_inputs():
    with pytest.raises(ValueError, match="mixed-sign"):
        web_shear_stress_field_postprocess(
            stress_samples=[
                {
                    "integration_point_id": "positive",
                    "design_shear_stress_mpa": 2,
                    "cross_section_area_weight_mm2": 1000,
                },
                {
                    "integration_point_id": "negative",
                    "design_shear_stress_mpa": -2,
                    "cross_section_area_weight_mm2": 1000,
                },
            ]
        )

    with pytest.raises(ValueError, match="nonzero resultant"):
        web_shear_stress_field_postprocess(
            stress_samples=[
                {
                    "integration_point_id": "zero",
                    "design_shear_stress_mpa": 0,
                    "cross_section_area_weight_mm2": 2000,
                },
            ]
        )

    with pytest.raises(ValueError, match="largest sampled stress"):
        web_shear_stress_field_postprocess(governing_peak_shear_stress_mpa=5.9)

    with pytest.raises(ValueError, match="identifiers must be unique"):
        web_shear_stress_field_postprocess(
            stress_samples=[
                {
                    "integration_point_id": "same",
                    "design_shear_stress_mpa": 2.4,
                    "cross_section_area_weight_mm2": 1000,
                },
                {
                    "integration_point_id": "SAME",
                    "design_shear_stress_mpa": 2.4,
                    "cross_section_area_weight_mm2": 1000,
                },
            ]
        )

    with pytest.raises(ValueError, match="must not be blank"):
        web_shear_stress_field_postprocess(rational_analysis_reference="  ")

    with pytest.raises(ValueError, match="Invalid input"):
        web_shear_stress_field_postprocess(section_form="circular_hollow_section")


def web_opening_shear_design(**changes):
    inputs = {
        "operation": "web_opening_shear_design",
        "clear_web_depth_mm": 250,
        "opening_internal_dimension_mm": 25,
        "longitudinal_stiffeners_present": False,
        "adjacent_openings_present": False,
        "adjacent_opening_boundary_spacing_mm": 0,
        "unstiffened_openings_at_cross_section": 1,
        "multiple_openings_rational_analysis_verified": False,
        "opening_geometry_verified": True,
        "yield_strength_mpa": 250,
        "web_area_at_opening_mm2": 1000,
        "web_area_basis_verified": True,
        "panel_depth_mm": 250,
        "web_thickness_mm": 5,
        "maximum_design_shear_stress_mpa": 8,
        "average_design_shear_stress_mpa": 4,
        "rational_elastic_analysis_reference": "FEA-OPENING-01",
        "rational_elastic_analysis_verified": True,
        "action_kn": 90,
        "moment_action_knm": 50,
        "section_moment_capacity_knm": 100,
    }
    inputs.update(changes)
    return run(inputs)


def test_clause_5_10_7_opening_shear_capacity_and_5_12_3_interaction():
    out = web_opening_shear_design()
    values = out["values"]
    checks = {check["clause"]: check for check in out["checks"]}

    assert values["stress_max_average_ratio"] == pytest.approx(2)
    assert values["nominal_web_shear_yield_capacity_kn"] == pytest.approx(150)
    assert values["nominal_web_shear_capacity_kn"] == pytest.approx(150 * 2 / 2.9)
    assert values["design_web_shear_capacity_kn"] == pytest.approx(93.1034482759)
    assert checks["5.11.1"]["satisfied"]
    assert checks["5.12.3 shear and bending interaction"]["satisfied"]
    assert out["checked_conditions_satisfied"]
    assert out["clauses"] == ["5.10.7", "5.11.1", "5.11.2", "5.11.3", "5.11.4", "5.11.5", "5.12.3"]

    overloaded = web_opening_shear_design(action_kn=94)
    overloaded_checks = {check["clause"]: check for check in overloaded["checks"]}
    assert not overloaded_checks["5.11.1"]["satisfied"]
    assert not overloaded_checks["5.12.3 shear and bending interaction"]["satisfied"]


def test_clause_5_12_3_opening_shear_reduces_capacity_for_high_bending():
    out = web_opening_shear_design(action_kn=80, moment_action_knm=80)
    checks = {check["clause"]: check for check in out["checks"]}
    assert checks["5.11.1"]["satisfied"]
    assert not checks["5.12.3 shear and bending interaction"]["satisfied"]
    assert out["values"]["design_web_shear_capacity_with_bending_kn"] == pytest.approx(
        0.9 * (150 * 2 / 2.9) * (2.2 - 1.6 * (80 / 90))
    )


def test_clause_5_10_7_opening_shear_requires_geometry_and_analysis_evidence():
    unverified = web_opening_shear_design(
        web_area_basis_verified=False,
        rational_elastic_analysis_verified=False,
    )
    checks = {check["clause"]: check for check in unverified["checks"]}
    assert not checks["web area at opening evidence"]["satisfied"]
    assert not checks["5.11.3 rational elastic analysis evidence"]["satisfied"]
    assert not unverified["checked_conditions_satisfied"]

    oversized = web_opening_shear_design(opening_internal_dimension_mm=26)
    assert not oversized["checked_conditions_satisfied"]
    too_close = web_opening_shear_design(
        adjacent_openings_present=True,
        adjacent_opening_boundary_spacing_mm=89,
        adjacent_opening_greatest_internal_dimension_mm=30,
    )
    assert too_close["values"]["required_adjacent_opening_spacing_mm"] == 90
    assert not too_close["checked_conditions_satisfied"]
    multiple = web_opening_shear_design(
        unstiffened_openings_at_cross_section=2,
        multiple_openings_rational_analysis_verified=False,
    )
    assert not multiple["checked_conditions_satisfied"]


def test_clause_5_11_3_opening_shear_stress_ratio_requires_maximum_at_least_average():
    with pytest.raises(ValueError, match="Maximum design shear stress"):
        web_opening_shear_design(
            maximum_design_shear_stress_mpa=3,
            average_design_shear_stress_mpa=4,
        )

    with pytest.raises(ValueError, match="reference must not be blank"):
        web_opening_shear_design(rational_elastic_analysis_reference="   ")


def web_opening_layout_shear_design(**changes):
    design_inputs = {
        "yield_strength_mpa": 250,
        "web_area_at_opening_mm2": 1000,
        "web_area_basis_verified": True,
        "panel_depth_mm": 250,
        "web_thickness_mm": 5,
        "maximum_design_shear_stress_mpa": 8,
        "average_design_shear_stress_mpa": 4,
        "rational_elastic_analysis_reference": "FEA-OPENING-01",
        "rational_elastic_analysis_verified": True,
        "action_kn": 90,
        "moment_action_knm": 50,
        "section_moment_capacity_knm": 100,
    }
    inputs = {
        "operation": "web_opening_layout_shear_design",
        "clear_web_depth_mm": 250,
        "longitudinal_stiffeners_present": False,
        "openings": [
            {
                "opening_id": "left",
                "longitudinal_start_mm": 0,
                "longitudinal_end_mm": 25,
                "transverse_start_mm": 0,
                "transverse_end_mm": 25,
                "greatest_internal_dimension_mm": 25,
                "design_inputs": dict(design_inputs),
            },
            {
                "opening_id": "right",
                "longitudinal_start_mm": 115,
                "longitudinal_end_mm": 140,
                "transverse_start_mm": 0,
                "transverse_end_mm": 25,
                "greatest_internal_dimension_mm": 25,
                "design_inputs": dict(design_inputs),
            },
        ],
        "opening_geometry_verified": True,
        "opening_geometry_reference": "DRAWING-OPENING-LAYOUT-01",
        "opening_layout_complete_verified": True,
        "all_openings_unstiffened_verified": True,
        "castellated_member_present": False,
        "multiple_openings_rational_analysis_shows_stiffeners_unnecessary_verified": False,
        "rational_analysis_reference": None,
        "load_combination_reference": "ULS-COMBO-01",
    }
    inputs.update(changes)
    return run(inputs)


def test_clause_5_10_7_layout_shear_design_checks_every_opening():
    out = web_opening_layout_shear_design()
    values = out["values"]
    assert values["opening_count"] == 2
    assert [item["opening_id"] for item in values["design_results"]] == ["left", "right"]
    assert values["maximum_openings_at_any_cross_section"] == 1
    assert values["governing_opening_id"] == "left"
    assert values["maximum_design_utilisation"] == pytest.approx(90 / (0.9 * (150 * 2 / 2.9)))
    assert out["checked_conditions_satisfied"]
    assert out["full_standard_compliance"] is False
    assert "5.10.7" in out["clauses"]
    assert "5.11.3" in out["clauses"]
    assert "5.12.3" in out["clauses"]


def test_clause_5_10_7_layout_shear_design_returns_governing_failed_opening():
    out = web_opening_layout_shear_design(
        openings=[
            {
                "opening_id": "left",
                "longitudinal_start_mm": 0,
                "longitudinal_end_mm": 25,
                "transverse_start_mm": 0,
                "transverse_end_mm": 25,
                "greatest_internal_dimension_mm": 25,
                "design_inputs": {
                    "yield_strength_mpa": 250,
                    "web_area_at_opening_mm2": 1000,
                    "web_area_basis_verified": True,
                    "panel_depth_mm": 250,
                    "web_thickness_mm": 5,
                    "maximum_design_shear_stress_mpa": 8,
                    "average_design_shear_stress_mpa": 4,
                    "rational_elastic_analysis_reference": "FEA-OPENING-LEFT-01",
                    "rational_elastic_analysis_verified": True,
                    "action_kn": 90,
                    "moment_action_knm": 50,
                    "section_moment_capacity_knm": 100,
                },
            },
            {
                "opening_id": "right",
                "longitudinal_start_mm": 115,
                "longitudinal_end_mm": 140,
                "transverse_start_mm": 0,
                "transverse_end_mm": 25,
                "greatest_internal_dimension_mm": 25,
                "design_inputs": {
                    "yield_strength_mpa": 250,
                    "web_area_at_opening_mm2": 1000,
                    "web_area_basis_verified": True,
                    "panel_depth_mm": 250,
                    "web_thickness_mm": 5,
                    "maximum_design_shear_stress_mpa": 8,
                    "average_design_shear_stress_mpa": 4,
                    "rational_elastic_analysis_reference": "FEA-OPENING-RIGHT-01",
                    "rational_elastic_analysis_verified": True,
                    "action_kn": 94,
                    "moment_action_knm": 50,
                    "section_moment_capacity_knm": 100,
                },
            },
        ]
    )
    assert not out["checked_conditions_satisfied"]
    assert out["values"]["governing_opening_id"] == "right"
    right = next(item for item in out["values"]["design_results"] if item["opening_id"] == "right")
    assert not right["checked_conditions_satisfied"]


def test_clause_5_10_7_layout_shear_design_includes_layout_failures_and_multiple_openings():
    too_close = web_opening_layout_shear_design(
        openings=[
            {
                "opening_id": "left",
                "longitudinal_start_mm": 0,
                "longitudinal_end_mm": 25,
                "transverse_start_mm": 0,
                "transverse_end_mm": 25,
                "greatest_internal_dimension_mm": 25,
                "design_inputs": {
                    "yield_strength_mpa": 250,
                    "web_area_at_opening_mm2": 1000,
                    "web_area_basis_verified": True,
                    "panel_depth_mm": 250,
                    "web_thickness_mm": 5,
                    "maximum_design_shear_stress_mpa": 8,
                    "average_design_shear_stress_mpa": 4,
                    "rational_elastic_analysis_reference": "FEA-OPENING-LEFT-02",
                    "rational_elastic_analysis_verified": True,
                    "action_kn": 90,
                    "moment_action_knm": 50,
                    "section_moment_capacity_knm": 100,
                },
            },
            {
                "opening_id": "right",
                "longitudinal_start_mm": 99,
                "longitudinal_end_mm": 124,
                "transverse_start_mm": 0,
                "transverse_end_mm": 25,
                "greatest_internal_dimension_mm": 25,
                "design_inputs": {
                    "yield_strength_mpa": 250,
                    "web_area_at_opening_mm2": 1000,
                    "web_area_basis_verified": True,
                    "panel_depth_mm": 250,
                    "web_thickness_mm": 5,
                    "maximum_design_shear_stress_mpa": 8,
                    "average_design_shear_stress_mpa": 4,
                    "rational_elastic_analysis_reference": "FEA-OPENING-RIGHT-02",
                    "rational_elastic_analysis_verified": True,
                    "action_kn": 90,
                    "moment_action_knm": 50,
                    "section_moment_capacity_knm": 100,
                },
            },
        ]
    )
    assert not too_close["checked_conditions_satisfied"]
    assert not too_close["checks"][0]["satisfied"]

    stacked_openings = [
        {
            "opening_id": "lower",
            "longitudinal_start_mm": 0,
            "longitudinal_end_mm": 25,
            "transverse_start_mm": 0,
            "transverse_end_mm": 20,
            "greatest_internal_dimension_mm": 25,
            "design_inputs": {
                "yield_strength_mpa": 250,
                "web_area_at_opening_mm2": 1000,
                "web_area_basis_verified": True,
                "panel_depth_mm": 250,
                "web_thickness_mm": 5,
                "maximum_design_shear_stress_mpa": 8,
                "average_design_shear_stress_mpa": 4,
                "rational_elastic_analysis_reference": "FEA-OPENING-LOWER-01",
                "rational_elastic_analysis_verified": True,
                "action_kn": 90,
                "moment_action_knm": 50,
                "section_moment_capacity_knm": 100,
            },
        },
        {
            "opening_id": "upper",
            "longitudinal_start_mm": 0,
            "longitudinal_end_mm": 25,
            "transverse_start_mm": 230,
            "transverse_end_mm": 250,
            "greatest_internal_dimension_mm": 25,
            "design_inputs": {
                "yield_strength_mpa": 250,
                "web_area_at_opening_mm2": 1000,
                "web_area_basis_verified": True,
                "panel_depth_mm": 250,
                "web_thickness_mm": 5,
                "maximum_design_shear_stress_mpa": 8,
                "average_design_shear_stress_mpa": 4,
                "rational_elastic_analysis_reference": "FEA-OPENING-UPPER-01",
                "rational_elastic_analysis_verified": True,
                "action_kn": 90,
                "moment_action_knm": 50,
                "section_moment_capacity_knm": 100,
            },
        },
    ]
    stacked = web_opening_layout_shear_design(
        openings=stacked_openings,
        multiple_openings_rational_analysis_shows_stiffeners_unnecessary_verified=True,
        rational_analysis_reference="ANALYSIS-STACKED-OPENINGS-01",
    )
    assert stacked["values"]["maximum_openings_at_any_cross_section"] == 2
    assert stacked["checked_conditions_satisfied"]


def web_opening_rational_analysis_review(**changes):
    inputs = {
        "operation": "web_opening_rational_analysis_review",
        "opening_design_case": "stiffened_opening",
        "opening_geometry_reference": "OPENING-GEOMETRY-01",
        "opening_geometry_verified": True,
        "rational_analysis_reference": "OPENING-ANALYSIS-01",
        "rational_analysis_verified": True,
        "analysis_scope_verified": True,
        "equilibrium_verified": True,
        "convergence_or_sensitivity_verified": True,
        "all_openings_and_design_cases_included_verified": True,
        "limit_state_register_complete_verified": True,
        "limit_state_checks": [
            {
                "limit_state_id": "upper-tee-bending",
                "description": "Upper tee local bending interaction",
                "design_action": 46,
                "design_capacity": 50,
                "unit": "kN_m",
                "analysis_result_reference": "OPENING-ANALYSIS-01:upper-tee",
                "design_capacity_reference": "AS4100-CALC-TEE-01",
                "actions_and_capacity_basis_verified": True,
            },
            {
                "limit_state_id": "web-shear",
                "description": "Web shear at opening",
                "design_action": 84,
                "design_capacity": 100,
                "unit": "kN",
                "analysis_result_reference": "OPENING-ANALYSIS-01:web-shear",
                "design_capacity_reference": "AS4100-CALC-WEB-01",
                "actions_and_capacity_basis_verified": True,
            },
            {
                "limit_state_id": "opening-bearing",
                "description": "Local opening bearing interaction",
                "design_action": 70,
                "design_capacity": 80,
                "unit": "kN",
                "analysis_result_reference": "OPENING-ANALYSIS-01:bearing",
                "design_capacity_reference": "AS4100-CALC-BEARING-01",
                "actions_and_capacity_basis_verified": True,
            },
            {
                "limit_state_id": "combined-interaction",
                "description": "Externally calculated combined-action utilization",
                "design_action": 0.88,
                "design_capacity": 1,
                "unit": "unitless",
                "analysis_result_reference": "OPENING-ANALYSIS-01:interaction",
                "design_capacity_reference": "AS4100-CALC-INTERACTION-01",
                "actions_and_capacity_basis_verified": True,
            },
        ],
    }
    inputs.update(changes)
    return run(inputs)


def test_clause_5_10_7_rational_analysis_review_governs_and_checks_all_supplied_states():
    out = web_opening_rational_analysis_review()
    values = out["values"]
    checks = [
        check
        for check in out["checks"]
        if check["clause"] == "5.10.7 rational-analysis design-action/capacity comparison"
    ]

    assert out["clauses"] == ["5.10.7"]
    assert values["limit_state_count"] == 4
    assert values["governing_limit_state_id"] == "upper-tee-bending"
    assert values["governing_utilization_ratio"] == pytest.approx(0.92)
    assert [check["utilization_ratio"] for check in checks] == pytest.approx(
        [0.92, 0.84, 0.875, 0.88]
    )
    assert all(check["satisfied"] for check in checks)
    assert out["checked_conditions_satisfied"]
    assert not out["full_standard_compliance"]


def test_clause_5_10_7_rational_analysis_review_rejects_overload_and_missing_evidence():
    overloaded = web_opening_rational_analysis_review(
        limit_state_checks=[
            {
                "limit_state_id": "tee-bending",
                "description": "Tee bending interaction",
                "design_action": 101,
                "design_capacity": 100,
                "unit": "kN_m",
                "analysis_result_reference": "OPENING-ANALYSIS-01:tee",
                "design_capacity_reference": "AS4100-CALC-TEE-01",
                "actions_and_capacity_basis_verified": True,
            }
        ]
    )
    assert not overloaded["checked_conditions_satisfied"]
    assert not overloaded["checks"][-1]["satisfied"]

    incomplete = web_opening_rational_analysis_review(
        analysis_scope_verified=False,
        limit_state_register_complete_verified=False,
        limit_state_checks=[
            {
                "limit_state_id": "tee-bending",
                "description": "Tee bending interaction",
                "design_action": 50,
                "design_capacity": 100,
                "unit": "kN_m",
                "analysis_result_reference": "OPENING-ANALYSIS-01:tee",
                "design_capacity_reference": "AS4100-CALC-TEE-01",
                "actions_and_capacity_basis_verified": False,
            }
        ],
    )
    assert not incomplete["checked_conditions_satisfied"]
    assert not all(check["satisfied"] for check in incomplete["checks"])


def test_clause_5_10_7_rational_analysis_review_rejects_duplicate_or_blank_evidence():
    with pytest.raises(ValueError, match="Invalid input"):
        web_opening_rational_analysis_review(limit_state_checks=[])

    with pytest.raises(ValueError, match="identifiers must be unique"):
        web_opening_rational_analysis_review(
            limit_state_checks=[
                {
                    "limit_state_id": "same",
                    "description": "First state",
                    "design_action": 1,
                    "design_capacity": 2,
                    "unit": "kN",
                    "analysis_result_reference": "REPORT-1",
                    "design_capacity_reference": "CALC-1",
                    "actions_and_capacity_basis_verified": True,
                },
                {
                    "limit_state_id": "SAME",
                    "description": "Second state",
                    "design_action": 1,
                    "design_capacity": 2,
                    "unit": "kN",
                    "analysis_result_reference": "REPORT-2",
                    "design_capacity_reference": "CALC-2",
                    "actions_and_capacity_basis_verified": True,
                },
            ]
        )

    with pytest.raises(ValueError, match="references must not be blank"):
        web_opening_rational_analysis_review(rational_analysis_reference="   ")


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


def test_clause_5_10_2_can_calculate_the_web_only_bearing_capacity():
    bearing_inputs = {
        "operation": "web_bearing",
        "section_type": "i_or_channel",
        "web_thickness_mm": 10,
        "web_yield_mpa": 300,
        "clear_web_depth_mm": 200,
        "bearing_width_at_flange_mm": 100,
        "bearing_width_at_neutral_axis_mm": 200,
        "restrained_flange_count": 2,
        "bearing_action_kn": 337.5,
    }
    inputs = {
        "operation": "load_bearing_stiffener_requirement",
        "web_bearing_inputs": bearing_inputs,
        "end_post_required_under_5_15_2_2": False,
        "load_bearing_stiffeners_provided": False,
    }

    boundary = run(inputs)
    assert boundary["values"]["design_web_bearing_capacity_kn"] == pytest.approx(337.5)
    assert boundary["values"]["web_bearing_capacity_source"] == "calculated_from_web_bearing"
    assert not boundary["values"]["stiffeners_required"]
    assert boundary["clauses"] == ["5.10.2", "5.13.1", "5.13.2", "5.13.3", "5.13.4"]
    assert boundary["checked_conditions_satisfied"]

    overloaded_inputs = inputs | {
        "web_bearing_inputs": bearing_inputs | {"bearing_action_kn": 337.501}
    }
    required = run(overloaded_inputs)
    assert required["values"]["required_by_web_bearing_capacity"]
    assert not required["checked_conditions_satisfied"]

    provided = run(overloaded_inputs | {"load_bearing_stiffeners_provided": True})
    assert provided["values"]["stiffeners_required"]
    assert provided["checked_conditions_satisfied"]

    end_bearing_trigger = run(
        {
            "operation": "load_bearing_stiffener_requirement",
            "web_bearing_inputs": {
                "operation": "web_bearing",
                "section_type": "i_or_channel",
                "web_thickness_mm": 10,
                "web_yield_mpa": 300,
                "clear_web_depth_mm": 200,
                "stiff_bearing_length_mm": 400,
                "flange_thickness_mm": 12,
                "distance_flange_to_neutral_axis_mm": 90,
                "bearing_geometry_verified": True,
                "bearing_location": "end",
                "end_web_unspread_width_mm": 40,
                "restrained_flange_count": 2,
                "bearing_action_kn": 1300,
            },
            "end_post_required_under_5_15_2_2": False,
            "load_bearing_stiffeners_provided": True,
        }
    )
    assert end_bearing_trigger["values"]["required_by_web_bearing_capacity"]
    assert end_bearing_trigger["values"]["design_web_bearing_capacity_kn"] == pytest.approx(
        1241.1130800153537
    )
    assert end_bearing_trigger["checked_conditions_satisfied"]

    with pytest.raises(ValueError, match="Invalid input"):
        run(
            inputs
            | {
                "design_compressive_bearing_force_kn": 337.5,
                "design_web_bearing_capacity_kn": 337.5,
            }
        )


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
    assert r["values"]["dispersion_method"] == "assessed_bearing_widths"


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
        "bearing_location": "interior",
        "restrained_flange_count": 2,
        "bearing_action_kn": 100,
    }
    r = run(inputs)
    assert r["values"]["bearing_width_at_flange_mm"] == 80
    assert r["values"]["bearing_width_at_neutral_axis_mm"] == 260
    assert r["values"]["bearing_yield_kn"] == 300
    assert r["values"]["geometric_slenderness"] == 50
    assert r["values"]["bearing_location"] == "interior"
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
        "bearing_location": "interior",
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

    end_bearing = run(
        geometry
        | {
            "stiff_bearing_length_mm": 400,
            "bearing_location": "end",
            "end_web_unspread_width_mm": 40,
            "bearing_action_kn": 1300,
        }
    )
    assert end_bearing["values"]["bearing_width_at_flange_mm"] == 460
    assert end_bearing["values"]["bearing_width_at_neutral_axis_mm"] == 590
    assert end_bearing["values"]["bearing_buckling_kn"] == pytest.approx(1379.0145333503929)
    assert end_bearing["checks"][0]["design_capacity"] == pytest.approx(1241.1130800153537)
    assert not end_bearing["checks"][0]["satisfied"]

    interior_bearing = run(
        geometry
        | {
            "stiff_bearing_length_mm": 400,
            "bearing_location": "interior",
            "bearing_action_kn": 1300,
        }
    )
    assert interior_bearing["values"]["bearing_width_at_neutral_axis_mm"] == 640
    assert interior_bearing["checks"][0]["satisfied"]

    with pytest.raises(ValueError, match="Invalid input"):
        run(geometry | {"bearing_location": "end"})


def test_rhs_bearing_bending_two_branches_and_individual_failure():
    d = {
        "operation": "rhs_bearing_bending",
        "bearing_action_kn": 50,
        "design_bearing_capacity_kn": 100,
        "bearing_capacity_5_13_2_verified": True,
        "bearing_capacity_5_13_2_reference": "Clause 5.13.2 independent capacity check",
        "moment_action_knm": 5,
        "design_moment_capacity_knm": 10,
        "moment_capacity_5_2_verified": True,
        "moment_capacity_5_2_reference": "Clause 5.2 independent capacity check",
        "stiff_bearing_length_mm": 200,
        "section_width_mm": 200,
        "clear_web_depth_mm": 200,
        "web_thickness_mm": 10,
        "section_form_to_as_nzs_1163_verified": True,
        "section_form_evidence_reference": "AS/NZS 1163 RHS member drawing",
        "section_geometry_verified": True,
        "section_geometry_evidence_reference": "RHS section dimensions from member drawing",
    }
    wide = run(d)
    assert wide["values"]["bearing_utilisation"] == pytest.approx(0.5)
    assert wide["values"]["moment_utilisation"] == pytest.approx(0.5)
    assert wide["values"]["interaction"] == pytest.approx(1.1)
    assert wide["values"]["limit"] == 1.5
    assert wide["values"]["equation_route"] == "wide_bearing_compact_web"
    assert wide["clauses"] == ["5.2", "5.13.2", "5.13.5"]
    assert wide["checked_conditions_satisfied"]

    # Both qualifying bounds are inclusive: bs/b = 1 and d1/tw = 30.
    boundary = run(d | {"clear_web_depth_mm": 300})
    assert boundary["values"]["equation_route"] == "wide_bearing_compact_web"
    assert boundary["values"]["interaction"] == pytest.approx(1.1)

    narrow_bearing = run(d | {"stiff_bearing_length_mm": 199})
    assert narrow_bearing["values"]["interaction"] == pytest.approx(0.9)
    assert narrow_bearing["values"]["limit"] == 1.0
    assert narrow_bearing["values"]["equation_route"] == "otherwise"

    wide_interaction_boundary = run(d | {"bearing_action_kn": 100, "moment_action_knm": 3})
    assert wide_interaction_boundary["values"]["interaction"] == pytest.approx(1.5)
    assert wide_interaction_boundary["checked_conditions_satisfied"]
    wide_interaction_failure = run(d | {"bearing_action_kn": 100, "moment_action_knm": 3.01})
    assert wide_interaction_failure["checks"][1]["satisfied"]
    assert wide_interaction_failure["checks"][2]["satisfied"]
    assert not wide_interaction_failure["checks"][3]["satisfied"]

    otherwise_interaction_boundary = run(
        d | {"stiff_bearing_length_mm": 199, "moment_action_knm": 6}
    )
    assert otherwise_interaction_boundary["values"]["interaction"] == pytest.approx(1.0)
    assert otherwise_interaction_boundary["checked_conditions_satisfied"]
    otherwise_interaction_failure = run(
        d | {"stiff_bearing_length_mm": 199, "moment_action_knm": 6.01}
    )
    assert not otherwise_interaction_failure["checks"][3]["satisfied"]

    slender_web = run(d | {"clear_web_depth_mm": 301})
    assert slender_web["values"]["equation_route"] == "otherwise"
    assert slender_web["values"]["interaction"] == pytest.approx(0.9)

    bearing_capacity_failure = run(d | {"bearing_action_kn": 101})
    assert not bearing_capacity_failure["checked_conditions_satisfied"]
    assert not bearing_capacity_failure["checks"][1]["satisfied"]
    moment_capacity_failure = run(d | {"moment_action_knm": 10.1})
    assert not moment_capacity_failure["checked_conditions_satisfied"]
    assert not moment_capacity_failure["checks"][2]["satisfied"]

    with pytest.raises(ValueError, match="Invalid input"):
        run(d | {"section_form_to_as_nzs_1163_verified": False})
    with pytest.raises(ValueError, match="must not be blank"):
        run(d | {"bearing_capacity_5_13_2_reference": "   "})
    with pytest.raises(ValueError, match="must not be blank"):
        run(d | {"section_geometry_evidence_reference": "   "})


def load_bearing_stiffener(**changes):
    return {
        "operation": "load_bearing_stiffener",
        "web_bearing_yield_kn": 100,
        "stiffener_area_mm2": 1000,
        "stiffener_configuration": "pair",
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

    inputs["design_force_share_to_web_kn"] = 70.001
    with pytest.raises(ValueError, match="cannot exceed"):
        run(inputs)
    inputs["design_force_share_to_web_kn"] = 40
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

    inputs["stiffener_configuration"] = "single_plate"
    with pytest.raises(ValueError, match="pair"):
        run(inputs)


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
        "greatest_panel_longitudinal_dimension_mm": 400,
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
        "stiffener_layout_verified": True,
        "longitudinal_stiffeners_present": False,
        "web_connection_design_shear_capacity_kn_per_mm": 0.2,
        "web_connection_capacity_verified": True,
        "stiffener_top_flange_gap_mm": 40,
        "stiffener_bottom_flange_gap_mm": 40,
        "flange_termination_geometry_verified": True,
    }
    missing_longitudinal_panel_dimension = dict(inputs)
    missing_longitudinal_panel_dimension.pop("greatest_panel_longitudinal_dimension_mm")
    with pytest.raises(ValueError, match="Invalid input"):
        run(missing_longitudinal_panel_dimension)
    r = run(inputs)
    assert "5.15.1" in r["clauses"]
    assert "5.15.2.1" in r["clauses"]
    assert r["values"]["maximum_flange_termination_gap_mm"] == 40
    web_thickness = r["values"]["clause_5_15_2_1_web_thickness_check"]
    assert "5.10.4" in web_thickness["clauses"]
    assert web_thickness["values"]["required_web_thickness_mm"] == 1
    assert web_thickness["values"]["greatest_panel_longitudinal_dimension_mm"] == 400
    connection_check = {check["clause"]: check for check in r["checks"]}[
        "5.15.8 web-connection shear per unit length"
    ]
    assert connection_check["required_kn_per_mm"] == pytest.approx(0.2)
    assert connection_check["satisfied"]
    assert all(check["satisfied"] for check in r["checks"][-3:])

    inputs["web_connection_design_shear_capacity_kn_per_mm"] = 0.199
    assert not {check["clause"]: check for check in run(inputs)["checks"]}[
        "5.15.8 web-connection shear per unit length"
    ]["satisfied"]
    inputs["web_connection_design_shear_capacity_kn_per_mm"] = 0.2
    inputs["web_connection_capacity_verified"] = False
    assert not {check["clause"]: check for check in run(inputs)["checks"]}[
        "5.15.8 web-connection shear per unit length"
    ]["satisfied"]
    inputs["web_connection_capacity_verified"] = True
    missing_connection_capacity = dict(inputs)
    missing_connection_capacity.pop("web_connection_design_shear_capacity_kn_per_mm")
    with pytest.raises(ValueError, match="Invalid input"):
        run(missing_connection_capacity)

    inputs["stiffener_bottom_flange_gap_mm"] = 40.001
    assert not run(inputs)["checks"][-2]["satisfied"]
    inputs["stiffener_bottom_flange_gap_mm"] = 40
    inputs["flange_termination_geometry_verified"] = False
    assert not run(inputs)["checks"][-1]["satisfied"]

    inputs["web_thickness_mm"] = 0.9
    checks = {check["clause"]: check for check in run(inputs)["checks"]}
    assert not checks["5.15.2.1 interior panel spacing via 5.10.4/5.10.5"]["satisfied"]


def test_clause_5_15_5_inertia_branches_and_clause_5_15_6_outstand_limit():
    inputs = {
        "operation": "transverse_stiffener",
        "clear_web_depth_mm": 500,
        "web_panel_depth_mm": 500,
        "web_thickness_mm": 10,
        "panel_spacing_mm": 500,
        "greatest_panel_longitudinal_dimension_mm": 500,
        "web_area_mm2": 5000,
        "web_yield_mpa": 250,
        "shear_buckling_coefficient": 0.5,
        "stiffener_configuration": "pair",
        "shear_action_kn": 20,
        "nominal_web_shear_kn": 100,
        "nominal_web_buckling_no_tension_field_kn": 100,
        "nominal_stiffener_buckling_kn": 100,
        "stiffener_area_mm2": 1000,
        "stiffener_second_moment_mm4": 400000,
        "stiffener_outstand_mm": 100,
        "stiffener_thickness_mm": 12,
        "stiffener_yield_mpa": 300,
        "outer_edge_continuously_stiffened": False,
        "stiffener_layout_verified": True,
        "longitudinal_stiffeners_present": False,
        "web_connection_design_shear_capacity_kn_per_mm": 1,
        "web_connection_capacity_verified": True,
    }

    short_spacing = run(inputs)
    assert short_spacing["values"]["minimum_second_moment_mm4"] == pytest.approx(375000)
    assert short_spacing["values"]["minimum_second_moment_expression"] == "0.75*d1*tw^3"
    assert short_spacing["values"]["stiffener_spacing_to_depth_ratio"] == 1

    boundary = run({**inputs, "panel_spacing_mm": 500 * sqrt(2)})
    assert boundary["values"]["minimum_second_moment_mm4"] == pytest.approx(375000)
    assert boundary["values"]["minimum_second_moment_expression"] == "0.75*d1*tw^3"

    long_spacing = run({**inputs, "panel_spacing_mm": 1000})
    assert long_spacing["values"]["minimum_second_moment_mm4"] == pytest.approx(187500)
    assert long_spacing["values"]["minimum_second_moment_expression"] == "1.5*d1^3*tw^3/s^2"

    checks = {check["clause"]: check for check in short_spacing["checks"]}
    assert checks["5.15.5"]["satisfied"]
    assert checks["5.15.6"]["satisfied"]

    outstand_limit = 164.31676725154983
    at_limit = run({**inputs, "stiffener_outstand_mm": outstand_limit})
    assert at_limit["values"]["outstand_limit_mm"] == pytest.approx(outstand_limit)
    assert {check["clause"]: check for check in at_limit["checks"]}["5.15.6"]["satisfied"]

    over_limit_inputs = {**inputs, "stiffener_outstand_mm": outstand_limit + 0.001}
    over_limit = run(over_limit_inputs)
    assert not {check["clause"]: check for check in over_limit["checks"]}["5.15.6"]["satisfied"]
    continuously_stiffened = run(over_limit_inputs | {"outer_edge_continuously_stiffened": True})
    assert {check["clause"]: check for check in continuously_stiffened["checks"]}["5.15.6"][
        "satisfied"
    ]


def test_clause_5_15_2_1_uses_clause_5_10_5_with_longitudinal_stiffeners():
    inputs = {
        "operation": "transverse_stiffener",
        "clear_web_depth_mm": 200,
        "web_panel_depth_mm": 200,
        "web_thickness_mm": 0.8,
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
        "stiffener_layout_verified": True,
        "longitudinal_stiffeners_present": True,
        "web_connection_design_shear_capacity_kn_per_mm": 0.2,
        "web_connection_capacity_verified": True,
        "longitudinal_stiffener_d2_mm": 500,
        "neutral_axis_stiffener_set_present": True,
    }
    r = run(inputs)
    thickness_check = r["values"]["clause_5_15_2_1_web_thickness_check"]
    assert "5.10.5" in thickness_check["clauses"]
    assert thickness_check["values"]["required_web_thickness_mm"] == 0.8
    assert thickness_check["checks"][0]["satisfied"]

    without_layout_verification = dict(inputs)
    without_layout_verification.pop("stiffener_layout_verified")
    with pytest.raises(ValueError, match="Invalid input"):
        run(without_layout_verification)

    inputs.pop("longitudinal_stiffener_d2_mm")
    with pytest.raises(ValueError, match="Invalid input"):
        run(inputs)


def test_transverse_stiffener_derives_5_11_and_5_14_2_capacities_from_geometry():
    inputs = {
        "operation": "transverse_stiffener",
        "clear_web_depth_mm": 1000,
        "web_panel_depth_mm": 1000,
        "web_thickness_mm": 5,
        "panel_spacing_mm": 1000,
        "greatest_panel_longitudinal_dimension_mm": 1000,
        "web_area_mm2": 5000,
        "web_yield_mpa": 250,
        "stiffener_configuration": "pair",
        "shear_action_kn": 50,
        "stiffener_area_mm2": 1000,
        "stiffener_second_moment_mm4": 200000,
        "stiffener_outstand_mm": 100,
        "stiffener_thickness_mm": 10,
        "stiffener_yield_mpa": 250,
        "outer_edge_continuously_stiffened": False,
        "stiffener_layout_verified": True,
        "longitudinal_stiffeners_present": False,
        "stiffener_buckling_geometry": {
            "radius_of_gyration_mm": 100,
            "available_web_width_left_mm": 500,
            "available_web_width_right_mm": 500,
        },
        "web_connection_design_shear_capacity_kn_per_mm": 0.05,
        "web_connection_capacity_verified": True,
    }
    r = run(inputs)
    values = r["values"]
    assert values["shear_buckling_coefficient"] == pytest.approx(0.294175)
    assert values["nominal_web_shear_capacity_kn"] == pytest.approx(220.63125)
    assert values["nominal_web_buckling_no_tension_field_kn"] == pytest.approx(220.63125)
    assert values["nominal_stiffener_buckling_kn"] == pytest.approx(
        1875 * buckling_alpha(10, 250) * 250 / 1000
    )
    assert values["capacity_basis"]["clause_5_14_2"]["effective_length_mm"] == 1000
    assert values["capacity_basis"]["method"] == "calculated_from_geometry"
    assert {"5.11.2", "5.11.5.2", "5.14.2"}.issubset(set(r["clauses"]))
    assert r["checked_conditions_satisfied"]

    mismatched_panel_depth = {**inputs, "web_panel_depth_mm": 500}
    with pytest.raises(ValueError, match="web_panel_depth_mm"):
        run(mismatched_panel_depth)

    with_supplied_capacity = {**inputs, "nominal_web_shear_kn": 598.85625}
    with pytest.raises(ValueError, match="Invalid input"):
        run(with_supplied_capacity)


def test_clause_5_15_2_2_reduced_end_panel_uses_alpha_d_one_and_checks_shear_and_bending():
    inputs = {
        "operation": "end_panel_design",
        "original_end_panel_spacing_mm": 400,
        "reduced_end_panel_spacing_mm": 200,
        "clear_web_depth_mm": 200,
        "panel_depth_mm": 200,
        "web_thickness_mm": 10,
        "web_area_mm2": 2000,
        "web_yield_mpa": 250,
        "design_shear_action_kn": 50,
        "design_moment_action_knm": 20,
        "section_moment_capacity_knm": 100,
        "stress_max_average_ratio": 1,
        "end_panel_geometry_verified": True,
    }
    r = run(inputs)
    assert r["values"]["alpha_d"] == 1
    assert r["values"]["nominal_shear_buckling_capacity_kn"] == 300
    assert r["values"]["design_shear_buckling_capacity_kn"] == 270
    checks = {check["clause"]: check for check in r["checks"]}
    assert checks["5.15.2.2 reduced end-panel spacing"]["satisfied"]
    assert checks["5.11.1 end-panel shear buckling with alpha_d = 1.0"]["satisfied"]
    assert checks["5.12 end-panel shear and bending interaction"]["satisfied"]

    inputs["design_shear_action_kn"] = 300
    overloaded = {check["clause"]: check for check in run(inputs)["checks"]}
    assert not overloaded["5.11.1 end-panel shear buckling with alpha_d = 1.0"]["satisfied"]
    assert not overloaded["5.12 end-panel shear and bending interaction"]["satisfied"]

    inputs["design_shear_action_kn"] = 50
    inputs["original_end_panel_spacing_mm"] = 200
    not_reduced = {check["clause"]: check for check in run(inputs)["checks"]}
    assert not not_reduced["5.15.2.2 reduced end-panel spacing"]["satisfied"]


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


def test_clause_5_15_2_2_end_post_composes_5_14_and_5_15_9_design_checks():
    inputs = {
        "operation": "end_post_design",
        "end_post_required_under_5_15_2_2": True,
        "clear_web_depth_mm": 1000,
        "design_shear_action_kn": 180,
        "capacity_factor": 0.9,
        "shear_buckling_coefficient": 0.5,
        "nominal_web_shear_yield_capacity_kn": 100,
        "end_plate_to_load_bearing_stiffener_distance_mm": 25,
        "end_plate_yield_mpa": 250,
        "end_plate_area_mm2": 3000,
        "design_bearing_force_kn": 20,
        "load_bearing_stiffener_inputs": {
            "web_bearing_yield_kn": 100,
            "contact_stiffener_area_mm2": 1000,
            "radius_of_gyration_mm": 50,
            "both_flanges_rotation_restrained": True,
            "available_web_width_left_mm": 200,
            "available_web_width_right_mm": 200,
            "stiffener_area_mm2": 2500,
            "stiffener_configuration": "pair",
            "web_yield_mpa": 250,
            "stiffener_yield_mpa": 250,
            "web_thickness_mm": 10,
            "clear_web_depth_mm": 1000,
            "panel_spacing_mm": 600,
            "stiffener_outstand_mm": 80,
            "stiffener_thickness_mm": 10,
            "outer_edge_continuously_stiffened": False,
            "load_bearing_stiffener_not_smaller_than_end_plate_verified": True,
        },
        "load_bearing_stiffener_attachment_inputs": {
            "design_force_share_to_web_kn": 10,
            "web_connection_design_capacity_kn": 10,
            "tight_uniform_bearing_against_loaded_flange_verified": True,
            "concentrated_force_directly_over_support": False,
        },
    }
    r = run(inputs)
    assert {"5.15.2.2", "5.14.1", "5.14.2", "5.14.3", "5.14.4", "5.15.9"}.issubset(
        set(r["clauses"])
    )
    assert r["values"]["minimum_end_plate_area_mm2"] == 3000
    assert r["checked_conditions_satisfied"]

    mismatched_depth = {
        **inputs,
        "load_bearing_stiffener_inputs": {
            **inputs["load_bearing_stiffener_inputs"],
            "clear_web_depth_mm": 999,
        },
    }
    with pytest.raises(ValueError, match="clear web depths must match"):
        run(mismatched_depth)

    inputs["load_bearing_stiffener_inputs"][
        "load_bearing_stiffener_not_smaller_than_end_plate_verified"
    ] = False
    undersized = run(inputs)
    assert not undersized["checked_conditions_satisfied"]
    assert not undersized["checks"][-1]["satisfied"]

    inputs["load_bearing_stiffener_inputs"][
        "load_bearing_stiffener_not_smaller_than_end_plate_verified"
    ] = True
    inputs["load_bearing_stiffener_inputs"]["torsional_end_restraint_required"] = True
    with pytest.raises(ValueError, match="required"):
        run(inputs)


def test_clause_5_15_7_1_increases_transverse_stiffener_inertia_for_external_actions():
    inputs = {
        "operation": "transverse_stiffener",
        "clear_web_depth_mm": 200,
        "web_panel_depth_mm": 200,
        "web_thickness_mm": 10,
        "panel_spacing_mm": 200,
        "greatest_panel_longitudinal_dimension_mm": 200,
        "web_area_mm2": 2000,
        "web_yield_mpa": 250,
        "stiffener_configuration": "pair",
        "shear_action_kn": 20,
        "stiffener_buckling_geometry": {
            "radius_of_gyration_mm": 50,
            "available_web_width_left_mm": 200,
            "available_web_width_right_mm": 0,
        },
        "stiffener_area_mm2": 1000,
        "stiffener_second_moment_mm4": 350000,
        "stiffener_outstand_mm": 100,
        "stiffener_thickness_mm": 10,
        "stiffener_yield_mpa": 250,
        "outer_edge_continuously_stiffened": False,
        "stiffener_layout_verified": True,
        "longitudinal_stiffeners_present": False,
        "external_normal_force_kn": 10,
        "external_moment_knm": 2,
        "external_parallel_force_kn": 5,
        "force_eccentricity_mm": 50,
        "capacity_factor": 0.9,
        "external_actions_verified": True,
    }
    with pytest.raises(ValueError, match="Invalid input"):
        run(inputs)
    inputs.update(
        {
            "load_bearing_stiffener_inputs": {
                "web_bearing_yield_kn": 100,
                "contact_stiffener_area_mm2": 1000,
                "radius_of_gyration_mm": 50,
                "both_flanges_rotation_restrained": True,
                "available_web_width_left_mm": 200,
                "available_web_width_right_mm": 0,
            },
            "load_bearing_stiffener_attachment_inputs": {
                "design_force_share_to_web_kn": 5,
                "web_connection_design_capacity_kn": 5,
                "tight_uniform_bearing_against_loaded_flange_verified": True,
                "concentrated_force_directly_over_support": False,
            },
        }
    )
    r = run(inputs)
    assert r["values"]["external_action_term_kn"] == 31.25
    assert r["values"]["external_load_stiffness_increase_mm4"] == pytest.approx(138888.8888889)
    assert r["values"]["required_second_moment_with_external_actions_mm4"] == pytest.approx(
        288888.8888889
    )
    checks = {check["clause"]: check for check in r["checks"]}
    assert checks["5.15.7.1 minimum inertia increase"]["satisfied"]
    assert checks["5.15.7.1 external actions verified"]["satisfied"]
    assert checks["5.15.7.2 -> 5.14.1"]["action"] == 5
    assert checks["5.15.7.2 -> 5.14.4 connection force transfer to web"]["satisfied"]
    assert r["checked_conditions_satisfied"]

    negative_force_inputs = dict(inputs)
    negative_force_inputs["external_parallel_force_kn"] = -5
    negative_force = run(negative_force_inputs)
    assert negative_force["values"]["parallel_web_force_kn"] == 5
    assert negative_force["values"]["external_action_term_kn"] == 28.75
    negative_checks = {check["clause"]: check for check in negative_force["checks"]}
    assert negative_checks["5.15.7.2 -> 5.14.1"]["action"] == 5

    zero_actions = {
        **inputs,
        "external_normal_force_kn": 0,
        "external_moment_knm": 0,
        "external_parallel_force_kn": 0,
        "force_eccentricity_mm": 0,
        "web_connection_design_shear_capacity_kn_per_mm": 0.2,
        "web_connection_capacity_verified": True,
    }
    zero_action_result = run(zero_actions)
    zero_action_clauses = {check["clause"] for check in zero_action_result["checks"]}
    assert "5.15.8 web-connection shear per unit length" in zero_action_clauses
    assert "5.15.7.1 minimum inertia increase" not in zero_action_clauses
    assert "5.15.7.2 -> 5.14.1" not in zero_action_clauses

    missing_zero_action_connection_capacity = dict(zero_actions)
    missing_zero_action_connection_capacity.pop("web_connection_design_shear_capacity_kn_per_mm")
    with pytest.raises(ValueError, match="Invalid input"):
        run(missing_zero_action_connection_capacity)

    inconsistent_geometry = {
        **inputs,
        "load_bearing_stiffener_inputs": {
            **inputs["load_bearing_stiffener_inputs"],
            "radius_of_gyration_mm": 1000,
        },
    }
    with pytest.raises(ValueError, match="effective-section geometry must match"):
        run(inconsistent_geometry)

    with_torsional_restraint = {
        **inputs,
        "load_bearing_stiffener_inputs": {
            **inputs["load_bearing_stiffener_inputs"],
            "torsional_end_restraint_required": True,
            "critical_flange_centroid_spacing_mm": 200,
            "critical_flange_thickness_mm": 10,
            "total_design_load_between_supports_kn": 100,
            "stiffener_pair_second_moment_about_web_centerline_mm4": 350000,
        },
    }
    assert run(with_torsional_restraint)["checked_conditions_satisfied"]
    with_torsional_restraint["load_bearing_stiffener_inputs"][
        "stiffener_pair_second_moment_about_web_centerline_mm4"
    ] = 349999
    with pytest.raises(ValueError, match="pair inertia must match"):
        run(with_torsional_restraint)

    inputs["stiffener_second_moment_mm4"] = 288888
    below_inertia = {check["clause"]: check for check in run(inputs)["checks"]}
    assert not below_inertia["5.15.7.1 minimum inertia increase"]["satisfied"]
    inputs["stiffener_second_moment_mm4"] = 350000
    inputs["external_actions_verified"] = False
    unverified_actions = {check["clause"]: check for check in run(inputs)["checks"]}
    assert not unverified_actions["5.15.7.1 external actions verified"]["satisfied"]
    inputs["external_actions_verified"] = True
    inputs["load_bearing_stiffener_attachment_inputs"]["web_connection_design_capacity_kn"] = 4.9
    failed_attachment = run(inputs)
    assert not failed_attachment["checked_conditions_satisfied"]
    assert not {check["clause"]: check for check in failed_attachment["checks"]}[
        "5.15.7.2 -> 5.14.4 connection force transfer to web"
    ]["satisfied"]


def test_clause_5_15_7_1_requires_complete_external_action_inputs():
    with pytest.raises(ValueError, match="Invalid input"):
        run(
            {
                "operation": "transverse_stiffener",
                "clear_web_depth_mm": 200,
                "web_panel_depth_mm": 200,
                "web_thickness_mm": 10,
                "panel_spacing_mm": 200,
                "greatest_panel_longitudinal_dimension_mm": 200,
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
                "stiffener_layout_verified": True,
                "longitudinal_stiffeners_present": False,
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
