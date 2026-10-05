"""Run independent AS 4100 regression cases and emit a machine-readable report."""

import json
import sys
from math import isclose, pi, sin, sqrt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from opencalcs_as4100.advanced_members import run_advanced_members  # noqa: E402
from opencalcs_as4100.connections import run_connections  # noqa: E402
from opencalcs_as4100.design_actions import run_design_actions  # noqa: E402
from opencalcs_as4100.durability import run_durability  # noqa: E402
from opencalcs_as4100.erection import run_erection  # noqa: E402
from opencalcs_as4100.fabrication import run_fabrication  # noqa: E402
from opencalcs_as4100.materials import run_materials  # noqa: E402
from opencalcs_as4100.members import run_members  # noqa: E402
from opencalcs_as4100.testing import run_testing  # noqa: E402
from opencalcs_as4100.webs import run_webs  # noqa: E402


def clause_10_3_design_service_temperature():
    result = run_durability(
        {
            "check_type": "design_service_temperature",
            "lodmat_temperature_c": 6,
            "lodmat_assessment_verified": True,
            "lodmat_evidence_reference": "BENCHMARK-FIGURE-10.3.2-SITE-01",
            "especially_low_local_ambient_conditions_verified": True,
            "special_local_temperature_evidence_reference": "BENCHMARK-LOW-TEMP-01",
            "record_based_low_temperature_c": -2,
            "critical_structure_and_temperature_records_verified": True,
            "recorded_temperature_evidence_reference": "BENCHMARK-TEMPERATURE-RECORD-01",
            "artificial_cooling_minimum_temperature_c": -25,
            "artificial_cooling_below_basic_temperature_verified": True,
            "artificial_cooling_evidence_reference": "BENCHMARK-COOLING-01",
        }
    )
    values = result["results"]
    expected = {
        "lodmat_temperature_c": 6,
        "special_local_ambient_adjustment_c": -5,
        "basic_design_service_temperature_c": -2,
        "design_service_temperature_c": -25,
    }
    for name, value in expected.items():
        expect_close(values[name], value)
    if result["clauses"] != ["10.3.2", "10.3.3"]:
        raise AssertionError("Clauses 10.3.2-10.3.3 were not reported for the applied adjustments")
    return expected


def clause_10_4_3_4_nonconforming_steel_impact_test():
    result = run_durability(
        {
            "check_type": "nonconforming_steel_impact_test",
            "plate_thickness_mm": 8,
            "specimen_thickness_mm": 7.5,
            "absorbed_energy_j": [15, 20.25, 25.5],
            "grade_standard_has_no_minimum_impact_properties_verified": True,
            "permissible_temperature_unknown_or_warmer_than_design_verified": True,
            "mock_up_grade_dimensions_and_strain_verified": True,
            "three_specimens_from_maximum_strain_region_verified": True,
            "tested_at_design_service_temperature_verified": True,
            "specimen_thickness_selection_verified": True,
            "evidence_reference": "BENCHMARK-CHARPY-REPORT-01",
        }
    )
    values = result["results"]
    expected = {
        "energy_reduction_factor": 0.75,
        "required_average_energy_j": 20.25,
        "required_minimum_single_energy_j": 15,
        "measured_average_energy_j": 20.25,
        "minimum_measured_energy_j": 15,
    }
    for name, value in expected.items():
        expect_close(values[name], value)
    if result["clauses"] != ["10.4.3.4(d)", "10.4.3.4(e)"] or not values["check_satisfied"]:
        raise AssertionError("Clause 10.4.3.4 Charpy energy thresholds failed")
    return expected


def clause_10_4_3_4_specified_impact_properties():
    result = run_durability(
        {
            "check_type": "specified_impact_properties_test",
            "plate_thickness_mm": 8,
            "specimen_thickness_mm": 7.5,
            "absorbed_energy_j": [13.5, 18, 22.5],
            "specified_minimum_average_energy_j": 24,
            "specified_minimum_single_energy_j": 18,
            "grade_standard_minimums_verified": True,
            "grade_standard_reference": "BENCHMARK-PRODUCT-STANDARD-CHARPY-01",
            "permissible_temperature_unknown_or_warmer_than_design_verified": True,
            "mock_up_grade_dimensions_and_strain_verified": True,
            "three_specimens_from_maximum_strain_region_verified": True,
            "tested_at_design_service_temperature_verified": True,
            "specimen_thickness_selection_verified": True,
            "evidence_reference": "BENCHMARK-CHARPY-REPORT-02",
        }
    )
    values = result["results"]
    expected = {
        "energy_reduction_factor": 0.75,
        "required_average_energy_j": 18,
        "required_minimum_single_energy_j": 13.5,
        "measured_average_energy_j": 18,
        "minimum_measured_energy_j": 13.5,
    }
    for name, value in expected.items():
        expect_close(values[name], value)
    expected_clauses = [
        "10.4.3.4(a)",
        "10.4.3.4(b)",
        "10.4.3.4(c)",
        "10.4.3.4(e)",
    ]
    if result["clauses"] != expected_clauses or not values["check_satisfied"]:
        raise AssertionError("Clause 10.4.3.4 specified grade minima failed")
    return expected


def table_10_4_4_grade_selection():
    result = run_durability(
        {
            "check_type": "steel_grade_selection",
            "product_standard": "AS 3597",
            "grade": "700",
            "required_steel_type": "10Q",
        }
    )
    if result["clauses"] != ["10.4.4"] or not result["results"]["grade_selection_satisfied"]:
        raise AssertionError("Table 10.4.4 AS 3597 grade 700 must match required type 10Q")
    return {"steel_type": result["results"]["steel_type"]}


def clause_10_5_fracture_assessment_evidence():
    result = run_durability(
        {
            "check_type": "fracture_assessment_evidence",
            "selected_steel_grade": "300L15",
            "selected_steel_type": "3",
            "assessment_method": "BS 7910",
            "assessment_report_reference": "BENCHMARK-FRACTURE-ASSESSMENT-01",
            "parent_steel_toughness_reference": "BENCHMARK-PARENT-TOUGHNESS-01",
            "weld_metal_toughness_reference": "BENCHMARK-WELD-TOUGHNESS-01",
            "heat_affected_zone_toughness_reference": "BENCHMARK-HAZ-TOUGHNESS-01",
            "weld_nondestructive_examination_reference": "BENCHMARK-WELD-NDE-01",
            "heat_affected_zone_nondestructive_examination_reference": "BENCHMARK-HAZ-NDE-01",
            "selected_grade_matches_assessed_material_verified": True,
            "all_relevant_welds_and_haz_zones_included_verified": True,
            "assessment_result": "acceptable",
        }
    )
    values = result["results"]
    if result["clauses"] != ["10.5"] or not values["check_satisfied"]:
        raise AssertionError("Clause 10.5 complete accepted evidence was not recorded")
    if values["fracture_mechanics_calculated_by_plugin"]:
        raise AssertionError("Clause 10.5 evidence operation must not claim fracture calculations")
    return {"evidence_complete": values["evidence_complete"], "check_satisfied": True}


def fillet(length):
    return run_connections(
        {
            "check_type": "fillet",
            "weld_strength_mpa": 490,
            "throat_mm": 4.2,
            "effective_length_mm": 100,
            "quality": "SP",
            "thin_rhs_longitudinal": False,
            "lap_length_mm": length,
            "action_kn": 50,
        }
    )["checks"]["weld"]["design_capacity_kn"]


def fatigue_welded_coped_splice():
    result = run_durability(
        {
            "check_type": "fatigue_welded_detail",
            "detail_number": 20,
            "detail_conditions_verified": True,
            "stress_direction_verified": True,
            "weld_quality_verified": True,
            "full_penetration_weld_verified": True,
            "weld_runoff_tabs_removed_verified": True,
            "weld_ends_ground_flush_in_stress_direction_verified": True,
            "welds_from_both_sides_verified": True,
            "cope_hole_present": True,
            "cope_hole_not_filled_verified": True,
            "weld_quality_basis": "AS/NZS 1554.1 SP",
            "detail_evidence_reference": "BENCHMARK-DRAWING-01",
            "stress_direction_evidence_reference": "BENCHMARK-STRESS-01",
            "weld_quality_evidence_reference": "BENCHMARK-WELD-01",
        }
    )["results"]
    if result["detail_category_mpa"] != 71:
        raise AssertionError("Table 11.5.1(B) cope-hole splice should use category 71")
    return {"detail_category_mpa": result["detail_category_mpa"]}


def clause_4_6_3_2_idealized_member_buckling():
    cases = {
        "braced_fixed_fixed": 0.7,
        "braced_top_pinned_bottom_fixed": 0.85,
        "braced_pinned_pinned": 1.0,
        "sway_top_fixed_bottom_fixed": 1.2,
        "sway_top_free_bottom_fixed": 2.2,
        "sway_top_fixed_bottom_pinned": 2.2,
    }
    factors = {}
    for case, expected_factor in cases.items():
        result = run_design_actions(
            {
                "operation": "idealized_member_buckling",
                "second_moment_mm4": 8e6,
                "member_length_mm": 4000,
                "idealized_end_restraint_case": case,
                "idealized_end_restraint_verified": True,
                "end_restraint_evidence_reference": "BENCHMARK-FIGURE-4-6-3-2",
                "member_length_centre_to_centre_verified": True,
                "member_length_evidence_reference": "BENCHMARK-MEMBER-LENGTH-01",
            }
        )
        if not result["checked_conditions_satisfied"]:
            raise AssertionError(f"Figure 4.6.3.2 restraint case {case} failed its evidence gates")
        factor = result["values"]["effective_length_factor"]
        if factor != expected_factor:
            raise AssertionError(f"Figure 4.6.3.2 case {case} should give k_e={expected_factor}")
        factors[case] = factor

    reference = run_design_actions(
        {
            "operation": "idealized_member_buckling",
            "second_moment_mm4": 8e6,
            "member_length_mm": 4000,
            "idealized_end_restraint_case": "braced_fixed_fixed",
            "idealized_end_restraint_verified": True,
            "end_restraint_evidence_reference": "BENCHMARK-FIGURE-4-6-3-2",
            "member_length_centre_to_centre_verified": True,
            "member_length_evidence_reference": "BENCHMARK-MEMBER-LENGTH-01",
        }
    )
    expected_load = 2014.2049798141545
    if not isclose(
        reference["values"]["elastic_buckling_load_kn"],
        expected_load,
        rel_tol=0,
        abs_tol=1e-9,
    ):
        raise AssertionError("Clauses 4.6.2/4.6.3.2 Euler load does not match the hand calculation")
    return {
        "effective_length_factors": factors,
        "elastic_buckling_load_kn": reference["values"]["elastic_buckling_load_kn"],
    }


def clause_4_6_3_3_chart_factor_buckling():
    result = run_design_actions(
        {
            "operation": "frame_chart_member_buckling",
            "member_id": "BENCHMARK-COL-CHART-01",
            "frame_type": "braced",
            "frame_type_verified": True,
            "rigid_jointed_frame_verified": True,
            "frame_classification_evidence_reference": "BENCHMARK-FRAME-CLASSIFICATION",
            "stiffness_ratio_at_end_1": 0.7,
            "stiffness_ratio_at_end_2": 1.2,
            "stiffness_ratios_verified": True,
            "stiffness_ratio_evidence_reference": "BENCHMARK-END-RATIOS",
            "effective_length_factor": 0.85,
            "effective_length_factor_chart_verified": True,
            "chart_evidence_reference": "BENCHMARK-FIGURE-4-6-3-3",
            "second_moment_mm4": 8e6,
            "second_moment_about_buckling_axis_verified": True,
            "section_evidence_reference": "BENCHMARK-SECTION-01",
            "member_length_mm": 4000,
            "member_length_centre_to_centre_verified": True,
            "member_length_evidence_reference": "BENCHMARK-MEMBER-LENGTH-01",
        }
    )
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Figure 4.6.3.3 chart factor inputs failed their evidence gates")
    values = result["values"]
    if values["effective_length_factor"] != 0.85:
        raise AssertionError("Figure 4.6.3.3 chart factor should be 0.85")
    expected_load = 1366.0352112234405
    if not isclose(values["elastic_buckling_load_kn"], expected_load, rel_tol=0, abs_tol=1e-9):
        raise AssertionError("Euler load using the Figure 4.6.3.3 factor failed hand arithmetic")
    return {
        "effective_length_factor": values["effective_length_factor"],
        "effective_length_mm": values["effective_length_mm"],
        "elastic_buckling_load_kn": values["elastic_buckling_load_kn"],
    }


def clause_4_6_3_3_alignment_equation_buckling():
    base = {
        "operation": "frame_chart_member_buckling",
        "member_id": "BENCHMARK-COL-ALIGNMENT-01",
        "frame_type_verified": True,
        "rigid_jointed_frame_verified": True,
        "frame_classification_evidence_reference": "BENCHMARK-FRAME-CLASSIFICATION",
        "stiffness_ratios_verified": True,
        "stiffness_ratio_evidence_reference": "BENCHMARK-END-RATIOS",
        "second_moment_mm4": 8e6,
        "second_moment_about_buckling_axis_verified": True,
        "section_evidence_reference": "BENCHMARK-SECTION-01",
        "member_length_mm": 4000,
        "member_length_centre_to_centre_verified": True,
        "member_length_evidence_reference": "BENCHMARK-MEMBER-LENGTH-01",
    }
    braced = run_design_actions(
        {
            **base,
            "frame_type": "braced",
            "stiffness_ratio_at_end_1": 0.1,
            "stiffness_ratio_at_end_2": 0.4,
        }
    )
    sway = run_design_actions(
        {
            **base,
            "frame_type": "sway",
            "stiffness_ratio_at_end_1": 1.0,
            "stiffness_ratio_at_end_2": 1.0,
        }
    )
    braced_factor = braced["values"]["effective_length_factor"]
    sway_factor = sway["values"]["effective_length_factor"]
    if not braced["checked_conditions_satisfied"] or not sway["checked_conditions_satisfied"]:
        raise AssertionError("Figure 4.6.3.3 alignment-equation evidence gates failed")
    if not isclose(braced_factor, 0.603, rel_tol=0, abs_tol=0.0005):
        raise AssertionError(
            "Braced factor does not match the published exact alignment-chart value"
        )
    if not isclose(sway_factor, 1.30, rel_tol=0, abs_tol=0.03):
        raise AssertionError("Sway factor does not match the Figure 4.6.3.3 contour reading")
    for result, factor in ((braced, braced_factor), (sway, sway_factor)):
        values = result["values"]
        expected_load = pi**2 * 200000 * 8e6 / (factor * 4000) ** 2 / 1000
        if not isclose(values["elastic_buckling_load_kn"], expected_load, rel_tol=0, abs_tol=1e-9):
            raise AssertionError("Euler load does not match independent hand arithmetic")
    return {"braced_factor": braced_factor, "sway_factor": sway_factor}


def clause_4_6_3_5_triangulated_member_buckling():
    result = run_design_actions(
        {
            "operation": "triangulated_member_buckling",
            "member_id": "BENCHMARK-TRUSS-MEMBER-01",
            "triangulated_structure_verified": True,
            "triangulated_structure_evidence_reference": "BENCHMARK-TRUSS-01",
            "second_moment_mm4": 4.5e6,
            "second_moment_about_buckling_axis_verified": True,
            "section_evidence_reference": "BENCHMARK-TRUSS-SECTION-01",
            "member_length_between_intersections_mm": 3000,
            "member_length_between_intersections_verified": True,
            "member_geometry_evidence_reference": "BENCHMARK-TRUSS-GEOMETRY-01",
            "effective_length_mm": 2400,
            "effective_length_assessment_verified": True,
            "effective_length_evidence_reference": "BENCHMARK-TRUSS-EFFECTIVE-LENGTH-01",
            "rational_buckling_analysis_consistent_with_appendix_g_verified": False,
        }
    )
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 4.6.3.5 triangulated-member evidence checks failed")
    values = result["values"]
    if not values["minimum_length_correction_applied"]:
        raise AssertionError("Clause 4.6.3.5 should apply the centre-to-centre minimum")
    if values["effective_length_mm"] != 3000:
        raise AssertionError("Clause 4.6.3.5 effective length should be at least 3000 mm")
    expected_load = 986.9604401089358
    if not isclose(values["elastic_buckling_load_kn"], expected_load, rel_tol=0, abs_tol=1e-9):
        raise AssertionError("Clause 4.6.2 Euler load failed triangulated-member hand arithmetic")
    return {
        "effective_length_mm": values["effective_length_mm"],
        "minimum_length_correction_applied": values["minimum_length_correction_applied"],
        "elastic_buckling_load_kn": values["elastic_buckling_load_kn"],
    }


def clause_4_7_2_rectangular_frame_buckling_factors():
    braced = run_design_actions(
        {
            "operation": "braced_frame_buckling_factor",
            "rectangular_frame_verified": True,
            "all_members_braced_verified": True,
            "regular_loading_verified": True,
            "beam_axial_forces_negligible_verified": True,
            "frame_assessment_evidence_reference": "BENCHMARK-BRACED-FRAME",
            "design_load_set_id": "BENCHMARK-ULS-BRACED",
            "design_load_set_actions_verified": True,
            "design_load_set_evidence_reference": "BENCHMARK-ULS-BRACED-ACTIONS",
            "columns": [
                {
                    "column_id": "BENCHMARK-BR-COL-01",
                    "elastic_member_buckling_load_n_omb_kn": 900,
                    "design_axial_force_n_star_kn": 300,
                    "member_buckling_load_verified": True,
                    "design_axial_force_verified": True,
                    "evidence_reference": "BENCHMARK-BR-COL-01-LOADS",
                },
                {
                    "column_id": "BENCHMARK-BR-COL-02",
                    "elastic_member_buckling_load_n_omb_kn": 1500,
                    "design_axial_force_n_star_kn": 300,
                    "member_buckling_load_verified": True,
                    "design_axial_force_verified": True,
                    "evidence_reference": "BENCHMARK-BR-COL-02-LOADS",
                },
            ],
            "all_columns_in_frame_listed_verified": True,
            "column_list_evidence_reference": "BENCHMARK-BRACED-COLUMNS",
        }
    )
    sway = run_design_actions(
        {
            "operation": "sway_frame_buckling_factor",
            "rectangular_frame_verified": True,
            "sway_member_classification_verified": True,
            "regular_loading_verified": True,
            "beam_axial_forces_negligible_verified": True,
            "frame_assessment_evidence_reference": "BENCHMARK-SWAY-FRAME",
            "design_load_set_id": "BENCHMARK-ULS-SWAY",
            "design_load_set_actions_verified": True,
            "design_load_set_evidence_reference": "BENCHMARK-ULS-SWAY-ACTIONS",
            "storeys": [
                {
                    "storey_id": "BENCHMARK-LEVEL-1",
                    "columns": [
                        {
                            "column_id": "BENCHMARK-SW-COL-1A",
                            "elastic_member_buckling_load_n_oms_kn": 900,
                            "design_axial_force_n_star_kn": 300,
                            "member_length_mm": 3000,
                            "member_buckling_load_verified": True,
                            "design_axial_force_verified": True,
                            "member_length_verified": True,
                            "evidence_reference": "BENCHMARK-SW-COL-1A-LOADS",
                        },
                        {
                            "column_id": "BENCHMARK-SW-COL-1B",
                            "elastic_member_buckling_load_n_oms_kn": 400,
                            "design_axial_force_n_star_kn": -100,
                            "member_length_mm": 3000,
                            "member_buckling_load_verified": True,
                            "design_axial_force_verified": True,
                            "member_length_verified": True,
                            "evidence_reference": "BENCHMARK-SW-COL-1B-LOADS",
                        },
                    ],
                    "all_columns_in_storey_listed_verified": True,
                    "column_list_evidence_reference": "BENCHMARK-LEVEL-1-COLUMNS",
                },
                {
                    "storey_id": "BENCHMARK-LEVEL-2",
                    "columns": [
                        {
                            "column_id": "BENCHMARK-SW-COL-2A",
                            "elastic_member_buckling_load_n_oms_kn": 1000,
                            "design_axial_force_n_star_kn": 400,
                            "member_length_mm": 3000,
                            "member_buckling_load_verified": True,
                            "design_axial_force_verified": True,
                            "member_length_verified": True,
                            "evidence_reference": "BENCHMARK-SW-COL-2A-LOADS",
                        }
                    ],
                    "all_columns_in_storey_listed_verified": True,
                    "column_list_evidence_reference": "BENCHMARK-LEVEL-2-COLUMNS",
                },
            ],
            "all_storeys_in_frame_listed_verified": True,
            "storey_list_evidence_reference": "BENCHMARK-SWAY-STOREYS",
        }
    )
    if not braced["checked_conditions_satisfied"] or not sway["checked_conditions_satisfied"]:
        raise AssertionError("Clause 4.7.2 rectangular-frame evidence checks failed")
    braced_values = braced["values"]
    sway_values = sway["values"]
    if braced_values["lambda_c"] != 3:
        raise AssertionError("Clause 4.7.2.1 lowest braced-column factor should be 3")
    expected_storey_factors = [6.5, 2.5]
    observed_storey_factors = [storey["lambda_ms"] for storey in sway_values["storeys"]]
    if len(observed_storey_factors) != len(expected_storey_factors) or any(
        not isclose(observed, expected, rel_tol=0, abs_tol=1e-12)
        for observed, expected in zip(observed_storey_factors, expected_storey_factors, strict=True)
    ):
        raise AssertionError("Clause 4.7.2.2 storey factors should be 6.5 and 2.5")
    if sway_values["lambda_c"] != 2.5:
        raise AssertionError("Clause 4.7.2.2 lowest sway-storey factor should be 2.5")
    return {
        "braced_frame_lambda_c": braced_values["lambda_c"],
        "sway_storey_factors": [storey["lambda_ms"] for storey in sway_values["storeys"]],
        "sway_frame_lambda_c": sway_values["lambda_c"],
    }


def clause_4_6_3_4_rectangular_frame_stiffness_ratio():
    result = run_design_actions(
        {
            "operation": "rectangular_frame_stiffness_ratio",
            "frame_type": "braced",
            "member_under_consideration_id": "COL-01",
            "compression_members": [
                {
                    "member_id": "COL-01",
                    "second_moment_mm4": 8e6,
                    "member_length_mm": 4000,
                    "rigid_connection_at_joint_verified": True,
                    "stiffness_evidence_reference": "BENCHMARK-COL-01",
                },
                {
                    "member_id": "COL-02",
                    "second_moment_mm4": 12e6,
                    "member_length_mm": 6000,
                    "rigid_connection_at_joint_verified": True,
                    "stiffness_evidence_reference": "BENCHMARK-COL-02",
                },
            ],
            "compression_members_at_joint_complete_verified": True,
            "compression_members_evidence_reference": "BENCHMARK-JOINT-COLUMNS",
            "beams": [
                {
                    "beam_id": "BEAM-01",
                    "second_moment_mm4": 10e6,
                    "member_length_mm": 5000,
                    "near_end_rigid_connection_verified": True,
                    "far_end_fixity": "pinned",
                    "far_end_fixity_verified": True,
                    "stiffness_evidence_reference": "BENCHMARK-BEAM-01",
                },
                {
                    "beam_id": "BEAM-02",
                    "second_moment_mm4": 6e6,
                    "member_length_mm": 3000,
                    "near_end_rigid_connection_verified": True,
                    "far_end_fixity": "rigidly_connected_to_column",
                    "far_end_fixity_verified": True,
                    "stiffness_evidence_reference": "BENCHMARK-BEAM-02",
                },
            ],
            "beams_at_joint_complete_verified": True,
            "beams_evidence_reference": "BENCHMARK-JOINT-BEAMS",
            "rectangular_frame_geometry_verified": True,
            "regular_loading_verified": True,
            "beam_axial_forces_negligible_verified": True,
            "frame_assessment_evidence_reference": "BENCHMARK-FRAME-BASIS",
            "column_base_condition": "not_column_base",
            "column_base_condition_verified": True,
            "column_base_evidence_reference": "BENCHMARK-COLUMN-BASE",
        }
    )
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 4.6.3.4 frame stiffness ratio benchmark failed")
    values = result["values"]
    if not isclose(values["compression_stiffness_sum_mm3"], 4000, rel_tol=0, abs_tol=1e-12):
        raise AssertionError("Clause 4.6.3.4 compression-member stiffness sum should be 4000")
    if not isclose(values["weighted_beam_stiffness_sum_mm3"], 5000, rel_tol=0, abs_tol=1e-12):
        raise AssertionError("Clause 4.6.3.4 beta-adjusted beam stiffness should be 5000")
    if not isclose(values["stiffness_ratio_at_end_gamma"], 0.8, rel_tol=0, abs_tol=1e-12):
        raise AssertionError("Clause 4.6.3.4 end stiffness ratio should be 0.8")
    return {
        "compression_stiffness_sum_mm3": values["compression_stiffness_sum_mm3"],
        "weighted_beam_stiffness_sum_mm3": values["weighted_beam_stiffness_sum_mm3"],
        "stiffness_ratio_at_end_gamma": values["stiffness_ratio_at_end_gamma"],
        "beta_e_values": [beam["beta_e"] for beam in values["beams"]],
    }


def clause_4_5_1_global_equilibrium():
    result = run_design_actions(
        {
            "operation": "plastic_global_equilibrium",
            "actions": [
                {
                    "action_id": "LOAD-01",
                    "action_type": "applied_load",
                    "force_kn": [1, 2, 3],
                    "moment_knm": [0, 0, 0],
                    "position_mm": [2000, -1000, 500],
                    "evidence_reference": "BENCHMARK-LOAD-01",
                },
                {
                    "action_id": "SUPPORT-01",
                    "action_type": "support_reaction",
                    "force_kn": [-1, -2, -3],
                    "moment_knm": [4, 5.5, -5],
                    "position_mm": [0, 0, 0],
                    "evidence_reference": "BENCHMARK-REACTION-01",
                },
            ],
            "force_tolerance_kn": 0,
            "moment_tolerance_knm": 0,
            "boundary_conditions_verified": True,
            "boundary_conditions_evidence_reference": "BENCHMARK-SUPPORTS-01",
        }
    )
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 4.5.1 global equilibrium benchmark failed")
    if result["values"]["force_resultant_kn"] != [0.0, 0.0, 0.0]:
        raise AssertionError("Clause 4.5.1 three-axis force resultants should balance")
    if result["values"]["moment_resultant_knm"] != [0.0, 0.0, 0.0]:
        raise AssertionError("Clause 4.5.1 moment and position cross force should balance")
    return {
        "force_resultant_kn": result["values"]["force_resultant_kn"],
        "moment_resultant_knm": result["values"]["moment_resultant_knm"],
        "boundary_conditions_satisfied": result["checks"][2]["satisfied"],
    }


def clause_4_5_1_joint_equilibrium():
    result = run_design_actions(
        {
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
                            "evidence_reference": "BENCHMARK-MEMBER-END-01",
                        },
                        {
                            "action_id": "MEMBER-END-02",
                            "action_type": "member_end_action",
                            "force_kn": [4, 0, -3],
                            "moment_knm": [0, 0, 0],
                            "position_offset_mm": [0, 1000, 0],
                            "evidence_reference": "BENCHMARK-MEMBER-END-02",
                        },
                        {
                            "action_id": "LOAD-01",
                            "action_type": "applied_load",
                            "force_kn": [-4, -2, 0],
                            "moment_knm": [3, 3, 2],
                            "position_offset_mm": [0, 0, 0],
                            "evidence_reference": "BENCHMARK-NODE-LOAD-01",
                        },
                    ],
                    "joint_actions_complete_verified": True,
                    "joint_actions_evidence_reference": "BENCHMARK-JOINT-ACTIONS-01",
                }
            ],
            "force_tolerance_kn": 0,
            "moment_tolerance_knm": 0,
        }
    )
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 4.5.1 joint equilibrium benchmark failed")
    joint = result["values"]["joints"][0]
    if joint["force_resultant_kn"] != [0.0, 0.0, 0.0]:
        raise AssertionError("Clause 4.5.1 joint force resultants should balance")
    if joint["moment_resultant_knm"] != [0.0, 0.0, 0.0]:
        raise AssertionError("Clause 4.5.1 joint moment resultants should balance")
    return {
        "force_resultant_kn": joint["force_resultant_kn"],
        "moment_resultant_knm": joint["moment_resultant_knm"],
        "actions_verified_complete": result["checks"][3]["satisfied"],
    }


def clause_4_5_1_member_span_equilibrium():
    result = run_design_actions(
        {
            "operation": "plastic_member_span_equilibrium",
            "members": [
                {
                    "member_id": "BEAM-01",
                    "member_vector_mm": [4000, 0, 0],
                    "member_geometry_verified": True,
                    "member_geometry_evidence_reference": "BENCHMARK-BEAM-GEOMETRY-01",
                    "start_end_force_kn": [0, 20, -7.5],
                    "start_end_moment_knm": [0, 0, 0],
                    "start_end_evidence_reference": "BENCHMARK-BEAM-START-01",
                    "end_end_force_kn": [0, 20, -7.5],
                    "end_end_moment_knm": [-1, 2, -3],
                    "end_end_evidence_reference": "BENCHMARK-BEAM-END-01",
                    "span_actions": [
                        {
                            "action_id": "UDL-01",
                            "force_kn": [0, -40, 15],
                            "moment_knm": [0, 0, 0],
                            "position_offset_mm": [2000, 0, 0],
                            "evidence_reference": "BENCHMARK-UDL-RESULTANT-01",
                        },
                        {
                            "action_id": "COUPLE-01",
                            "force_kn": [0, 0, 0],
                            "moment_knm": [1, -2, 3],
                            "position_offset_mm": [2000, 0, 0],
                            "evidence_reference": "BENCHMARK-SPAN-COUPLE-01",
                        },
                    ],
                    "span_actions_complete_verified": True,
                    "span_actions_evidence_reference": "BENCHMARK-BEAM-LOAD-LIST-01",
                }
            ],
            "force_tolerance_kn": 0,
            "moment_tolerance_knm": 0,
            "all_members_listed_verified": True,
            "member_list_evidence_reference": "BENCHMARK-MEMBER-LIST-01",
        }
    )
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 4.5.1 member-span equilibrium benchmark failed")
    member = result["values"]["members"][0]
    if member["force_resultant_kn"] != [0.0, 0.0, 0.0]:
        raise AssertionError("Clause 4.5.1 member force resultants should balance")
    if member["moment_resultant_about_start_knm"] != [0.0, 0.0, 0.0]:
        raise AssertionError("Clause 4.5.1 member moments should balance about the start end")
    return {
        "force_resultant_kn": member["force_resultant_kn"],
        "moment_resultant_about_start_knm": member["moment_resultant_about_start_knm"],
        "span_action_count": member["span_action_count"],
    }


def clause_4_5_1_support_boundary_conditions():
    result = run_design_actions(
        {
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
                            "analysis_result_evidence_reference": "BENCHMARK-SUPPORT-UX-01",
                        },
                        {
                            "dof": "uy",
                            "prescribed_translation_mm": 0,
                            "calculated_translation_mm": 0,
                            "tolerance_mm": 0,
                            "analysis_result_evidence_reference": "BENCHMARK-SUPPORT-UY-01",
                        },
                        {
                            "dof": "rz",
                            "prescribed_rotation_rad": 0,
                            "calculated_rotation_rad": 0.001,
                            "tolerance_rad": 0.001,
                            "analysis_result_evidence_reference": "BENCHMARK-SUPPORT-RZ-01",
                        },
                    ],
                    "support_restraint_verified": True,
                    "support_evidence_reference": "BENCHMARK-SUPPORT-DRAWING-01",
                }
            ],
            "all_supports_listed_verified": True,
            "support_list_evidence_reference": "BENCHMARK-SUPPORT-SCHEDULE-01",
        }
    )
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 4.5.1 support boundary benchmark failed")
    constraints = result["values"]["supports"][0]["constraints"]
    if not isclose(abs(constraints[0]["residual"]), 0.01, rel_tol=0, abs_tol=1e-12):
        raise AssertionError("Clause 4.5.1 support translation residual should be 0.01 mm")
    if not isclose(abs(constraints[2]["residual"]), 0.001, rel_tol=0, abs_tol=1e-12):
        raise AssertionError("Clause 4.5.1 support rotation residual should be 0.001 rad")
    return {
        "support_conditions_satisfied": result["values"]["all_support_conditions_satisfied"],
        "translation_residual_mm": constraints[0]["residual"],
        "rotation_residual_rad": constraints[2]["residual"],
    }


def clause_4_5_2_alternative_ductility_assessment():
    result = run_design_actions(
        {
            "operation": "plastic_alternative_ductility_assessment",
            "members": [
                {
                    "component_id": "MEMBER-01",
                    "rotation_demand_rad": 0.018,
                    "rotation_capacity_rad": 0.02,
                    "rotation_demand_assessment_verified": True,
                    "rotation_capacity_assessment_verified": True,
                    "evidence_reference": "BENCHMARK-MEMBER-ROTATION-01",
                }
            ],
            "connections": [
                {
                    "component_id": "CONNECTION-01",
                    "rotation_demand_rad": 0.015,
                    "rotation_capacity_rad": 0.015,
                    "rotation_demand_assessment_verified": True,
                    "rotation_capacity_assessment_verified": True,
                    "evidence_reference": "BENCHMARK-CONNECTION-ROTATION-01",
                }
            ],
            "all_members_listed_verified": True,
            "member_list_evidence_reference": "BENCHMARK-MEMBER-LIST-01",
            "all_connections_listed_verified": True,
            "connection_list_evidence_reference": "BENCHMARK-CONNECTION-LIST-01",
            "structure_ductility_assessment_verified": True,
            "structure_ductility_evidence_reference": "BENCHMARK-STRUCTURE-DUCTILITY-01",
            "analysis_under_design_loading_verified": True,
            "analysis_evidence_reference": "BENCHMARK-DESIGN-LOAD-ANALYSIS-01",
        }
    )
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 4.5.2 alternate ductility assessment benchmark failed")
    member_ratio = result["values"]["members"][0]["rotation_demand_to_capacity_ratio"]
    connection_ratio = result["values"]["connections"][0]["rotation_demand_to_capacity_ratio"]
    if not isclose(member_ratio, 0.9, rel_tol=0, abs_tol=1e-12):
        raise AssertionError("Clause 4.5.2 member rotation ratio should be 0.9")
    if not isclose(connection_ratio, 1, rel_tol=0, abs_tol=1e-12):
        raise AssertionError("Clause 4.5.2 connection rotation boundary should be 1")
    return {
        "member_rotation_demand_to_capacity_ratio": member_ratio,
        "connection_rotation_demand_to_capacity_ratio": connection_ratio,
        "external_ductility_and_analysis_gates_satisfied": result["checked_conditions_satisfied"],
    }


def clause_4_5_2_plastic_analysis_limits():
    result = run_design_actions(
        {
            "operation": "plastic_analysis_limits",
            "materials": [
                {
                    "material_id": "GRADE-350",
                    "material_standard": "AS/NZS 3678",
                    "material_standard_verified": True,
                    "specified_yield_strength_mpa": 450,
                    "specified_tensile_strength_mpa": 540,
                    "yield_plateau_extension_in_yield_strains": 6,
                    "elongation_percent": 15,
                    "elongation_test_to_as1391_verified": True,
                    "strain_hardening_capability_verified": True,
                    "stress_strain_data_verified": True,
                    "evidence_reference": "MATERIAL-TEST-4100-01",
                }
            ],
            "members": [
                {
                    "member_id": "PLASTIC-MEMBER-01",
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
                    "evidence_reference": "MEMBER-REVIEW-4100-01",
                }
            ],
        }
    )
    ratio = result["values"]["materials"][0]["tensile_to_yield_strength_ratio"]
    if not result["checked_conditions_satisfied"] or not isclose(ratio, 1.2):
        raise AssertionError("Clause 4.5.2 prescriptive boundary benchmark failed")
    return {"tensile_to_yield_ratio": ratio, "checks_satisfied": True}


def clause_4_5_3_plastic_connections():
    result = run_design_actions(
        {
            "operation": "plastic_analysis_connections",
            "rigid_plastic_analysis_verified": True,
            "all_assumed_connections_listed_verified": True,
            "all_collapse_mechanism_hinges_listed_verified": True,
            "analysis_evidence_reference": "PLASTIC-ANALYSIS-4100-01",
            "connections": [
                {
                    "connection_id": "C-FULL",
                    "strength_type": "full_strength",
                    "connection_design_moment_capacity_knm": 100,
                    "connected_member_design_moment_capacity_knm": 100,
                    "connection_capacity_used_in_analysis_verified": True,
                    "all_required_plastic_hinges_develop_verified": True,
                    "evidence_reference": "CONNECTION-FULL-01",
                },
                {
                    "connection_id": "C-PARTIAL",
                    "strength_type": "partial_strength",
                    "connection_design_moment_capacity_knm": 80,
                    "connected_member_design_moment_capacity_knm": 100,
                    "connection_capacity_used_in_analysis_verified": True,
                    "all_required_plastic_hinges_develop_verified": True,
                    "evidence_reference": "CONNECTION-PARTIAL-01",
                },
            ],
            "plastic_hinges": [
                {
                    "hinge_id": "H-MEMBER",
                    "location_type": "member",
                    "rotation_demand_rad": 0.025,
                    "rotation_capacity_rad": 0.025,
                    "rotation_demand_assessment_verified": True,
                    "rotation_capacity_assessment_verified": True,
                    "evidence_reference": "HINGE-MEMBER-01",
                }
            ],
        }
    )
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 4.5.3 full/partial connection boundary benchmark failed")
    return {
        "full_strength_capacity_ratio": result["values"]["connections"][0]["capacity_ratio"],
        "partial_strength_capacity_ratio": result["values"]["connections"][1]["capacity_ratio"],
        "hinge_rotation_ratio": result["values"]["plastic_hinges"][0][
            "rotation_demand_to_capacity_ratio"
        ],
    }


def incomplete_butt_weld():
    result = run_connections(
        {
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
    )
    intermediate = result["intermediate"]
    strength = result["checks"]["weld_strength"]
    expected = {
        "design_throat_mm": 9,
        "effective_area_mm2": 1800,
        "nominal_capacity_kn": 529.2,
        "design_capacity_kn": 423.36,
    }
    for name, value in expected.items():
        observed = strength[name] if name.endswith("capacity_kn") else intermediate[name]
        expect_close(observed, value)
    if not strength["satisfied"]:
        raise AssertionError("Clause 9.6.2 incomplete butt weld benchmark failed")
    return expected


def combined_weld_types():
    result = run_connections(
        {
            "check_type": "combined_weld_types",
            "design_action_basis": "force_kn",
            "design_action": 40,
            "complete_nonoverlapping_weld_component_set_verified": True,
            "common_action_basis_and_direction_verified": True,
            "weld_components": [
                {
                    "component_id": "BENCHMARK-FILLET-01",
                    "weld_type": "fillet",
                    "design_capacity": 25,
                    "capacity_calculation_reference": "BENCHMARK-FILLET-CAPACITY-01",
                    "section_9_capacity_basis_verified": True,
                },
                {
                    "component_id": "BENCHMARK-BUTT-01",
                    "weld_type": "butt",
                    "design_capacity": 20,
                    "capacity_calculation_reference": "BENCHMARK-BUTT-CAPACITY-01",
                    "section_9_capacity_basis_verified": True,
                },
            ],
        }
    )
    check = result["checks"]["combined_weld_connection_capacity"]
    expected_capacity = 25 + 20
    expect_close(check["design_capacity_kn"], expected_capacity)
    expect_close(check["utilisation"], 40 / expected_capacity)
    if check["clause"] != "9.7.4" or not check["satisfied"]:
        raise AssertionError("Clause 9.7.4 combined weld design check failed")
    if result["intermediate"]["capacity_factor_applied_again"] is not False:
        raise AssertionError("Clause 9.7.4 must use supplied design capacities")
    return {"design_capacity_kn": expected_capacity, "utilisation": 40 / expected_capacity}


def incomplete_butt_macro_test_weld():
    result = run_connections(
        {
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
            "automatic_arc_welding_process_verified": True,
            "production_weld_macro_test_verified": True,
            "macro_test_required_penetration_achieved_verified": True,
            "macro_test_record_reference": "MACRO-TEST-BENCHMARK",
            "macro_test_penetration_beyond_preparation_mm": 4,
            "action_kn": 724.416,
        }
    )
    # Independent arithmetic: t_t = 12 + 0.85(4) = 15.4 mm;
    # area = 15.4(200) = 3080 mm²; phi Vw = 0.8(0.6)(490)(3080)/1000.
    expected = {
        "design_throat_mm": 15.4,
        "effective_area_mm2": 3080,
        "nominal_capacity_kn": 905.52,
        "design_capacity_kn": 724.416,
    }
    intermediate = result["intermediate"]
    strength = result["checks"]["weld_strength"]
    for name, value in expected.items():
        observed = strength[name] if name.endswith("capacity_kn") else intermediate[name]
        expect_close(observed, value)
    if not strength["satisfied"]:
        raise AssertionError("Clause 9.6.2.3(b)(iii) macro-test throat benchmark failed")
    if "9.6.3.4" not in strength["clause"]:
        raise AssertionError("Figure 9.6.3.4 was not reported for macro-test throat increase")
    return expected


def butt_weld_transition():
    result = run_connections(
        {
            "check_type": "butt_weld_transition",
            "dimension_change_mm": 10,
            "effective_transition_run_mm": 20,
            "transition_method": "slope_weld_surface",
            "tension_loaded_joint_verified": True,
            "smooth_transition_verified": True,
        }
    )
    check = result["checks"]["transition_geometry"]
    expected = {
        "slope_ratio": 0.5,
        "minimum_transition_run_mm": 10,
        "satisfied": True,
    }
    for name, value in expected.items():
        observed = check[name]
        if isinstance(value, bool):
            if observed is not value:
                raise AssertionError("Clause 9.6.2.6 transition boundary benchmark failed")
        else:
            expect_close(observed, value)
    return expected


def fillet_macro_test_throat():
    result = run_connections(
        {
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
            "automatic_arc_welding_process_verified": True,
            "production_weld_macro_test_verified": True,
            "macro_test_required_penetration_achieved_verified": True,
            "macro_test_record_reference": "FILLET-MACRO-BENCHMARK",
            "macro_test_additional_penetration_mm": 4,
            "action_kn": 0,
        }
    )
    # Independent arithmetic: t_t = 6/sqrt(2) + 0.85(4), then Clause 9.6.3.10.
    throat = 6 / (2**0.5) + 0.85 * 4
    area = throat * 100
    nominal = 0.6 * 490 * area / 1000
    expected = {
        "design_throat_mm": throat,
        "effective_area_mm2": area,
        "nominal_capacity_kn": nominal,
        "design_capacity_kn": 0.8 * nominal,
    }
    intermediate = result["intermediate"]
    strength = result["checks"]["weld_strength"]
    for name, value in expected.items():
        observed = strength[name] if name.endswith("capacity_kn") else intermediate[name]
        expect_close(observed, value)
    if "9.6.3.4" not in strength["clause"]:
        raise AssertionError("Figure 9.6.3.4 was not reported for fillet macro-test throat")
    return expected


def prequalified_incomplete_butt_capacity():
    result = run_connections(
        {
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
    )
    # Independent AS 4100 arithmetic using the externally established 8 mm throat.
    area = 8 * 200
    nominal = 0.6 * 490 * area / 1000
    expected = {
        "design_throat_mm": 8,
        "effective_area_mm2": area,
        "nominal_capacity_kn": nominal,
        "design_capacity_kn": 0.8 * nominal,
    }
    intermediate = result["intermediate"]
    weld = result["checks"]["weld_strength"]
    for name, value in expected.items():
        observed = weld[name] if name.endswith("capacity_kn") else intermediate[name]
        expect_close(observed, value)
    if "9.6.2.3(b)(i)" not in weld["clause"]:
        raise AssertionError("Prequalified preparation route was not reported")
    return expected


def prequalified_incomplete_butt_macro_throat():
    result = run_connections(
        {
            "check_type": "prequalified_incomplete_butt_design",
            "weld_strength_mpa": 490,
            "quality": "SP",
            "prequalified_design_throat_mm": 8,
            "prequalified_preparation_verified": True,
            "prequalified_preparation_reference": "AS/NZS 1554.1 project WPS 01",
            "welding_procedure_and_consumable_basis_verified": True,
            "continuous_full_size_weld_length_mm": 200,
            "thin_rhs_longitudinal": False,
            "preparation_depth_mm": 12,
            "automatic_arc_welding_process_verified": True,
            "production_weld_macro_test_verified": True,
            "macro_test_required_penetration_achieved_verified": True,
            "macro_test_record_reference": "PREQUALIFIED-MACRO-BENCHMARK",
            "macro_test_penetration_beyond_preparation_mm": 2,
            "action_kn": 0,
        }
    )
    # Figure 9.6.3.4: t_t = t_t1 + 0.85 t_t2, then Clause 9.6.3.10.
    throat = 12 + 0.85 * 2
    area = throat * 200
    nominal = 0.6 * 490 * area / 1000
    expected = {
        "design_throat_mm": throat,
        "effective_area_mm2": area,
        "nominal_capacity_kn": nominal,
        "design_capacity_kn": 0.8 * nominal,
    }
    intermediate = result["intermediate"]
    weld = result["checks"]["weld_strength"]
    for name, value in expected.items():
        observed = weld[name] if name.endswith("capacity_kn") else intermediate[name]
        expect_close(observed, value)
    if "Figure 9.6.3.4" not in weld["clause"]:
        raise AssertionError("Figure 9.6.3.4 was not reported for the prequalified throat increase")
    return expected


def plug_slot_benchmark(dimensions, expected_area):
    result = run_connections(
        {
            "check_type": "plug_slot",
            "weld_strength_mpa": 490,
            "quality": "SP",
            "permitted_shear_application": True,
            "action_kn": 0,
            "hole_geometry_verified": True,
            **dimensions,
        }
    )
    nominal = 0.6 * 490 * expected_area / 1000
    expected = {
        "effective_area_mm2": expected_area,
        "nominal_capacity_kn": nominal,
        "design_capacity_kn": 0.8 * nominal,
    }
    intermediate = result["intermediate"]
    weld = result["checks"]["weld"]
    expect_close(intermediate["effective_area_mm2"], expected_area)
    expect_close(weld["nominal_capacity_kn"], nominal)
    expect_close(weld["design_capacity_kn"], 0.8 * nominal)
    if not result["checks"]["application"]["satisfied"]:
        raise AssertionError("Clause 9.6.4.3 permitted application was not recorded")
    return expected


def plug_slot_circular_hole():
    return plug_slot_benchmark(
        {"hole_shape": "circular", "hole_diameter_mm": 40},
        400 * 3.141592653589793,
    )


def plug_slot_round_ended_slot():
    return plug_slot_benchmark(
        {"hole_shape": "round_ended_slot", "slot_length_mm": 50, "slot_width_mm": 20},
        600 + 100 * 3.141592653589793,
    )


def plug_slot_rectangular_slot():
    return plug_slot_benchmark(
        {"hole_shape": "rectangular_slot", "slot_length_mm": 50, "slot_width_mm": 20},
        1000,
    )


def plug_slot_external_area():
    result = run_connections(
        {
            "check_type": "plug_slot",
            "weld_strength_mpa": 490,
            "effective_area_mm2": 1000,
            "quality": "SP",
            "permitted_shear_application": True,
            "action_kn": 0,
        }
    )
    expected = {"effective_area_mm2": 1000, "nominal_capacity_kn": 294, "design_capacity_kn": 235.2}
    expect_close(result["intermediate"]["effective_area_mm2"], expected["effective_area_mm2"])
    expect_close(result["checks"]["weld"]["nominal_capacity_kn"], expected["nominal_capacity_kn"])
    expect_close(result["checks"]["weld"]["design_capacity_kn"], expected["design_capacity_kn"])
    return expected


def stiffener(**changes):
    return {
        "operation": "load_bearing_stiffener",
        "web_bearing_yield_kn": 100,
        "stiffener_area_mm2": 1000,
        "contact_stiffener_area_mm2": 500,
        "web_yield_mpa": 250,
        "stiffener_yield_mpa": 450,
        "web_thickness_mm": 10,
        "clear_web_depth_mm": 200,
        "panel_spacing_mm": 300,
        "radius_of_gyration_mm": 50,
        "both_flanges_rotation_restrained": True,
        "available_web_width_left_mm": 200,
        "available_web_width_right_mm": 0,
        "stiffener_outstand_mm": 150,
        "stiffener_thickness_mm": 10,
        "outer_edge_continuously_stiffened": False,
        "bearing_action_kn": 100,
        **changes,
    }


def expect_close(actual, expected):
    if not isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
        raise AssertionError(f"expected {expected}, observed {actual}")
    return actual


def expect_rejected(callback):
    try:
        callback()
    except ValueError:
        return "rejected"
    raise AssertionError("input was accepted")


def mixed_stiffener():
    result = run_webs(stiffener())
    values = result["values"]
    expect_close(values["bearing_yield_kn"], 325)
    expect_close(values["effective_area_mm2"], 2500)
    expect_close(values["outstand_limit_mm"], 111.80339887498948)
    if result["checks"][2]["satisfied"]:
        raise AssertionError("150 mm outstand was accepted")
    return {
        "bearing_yield_kn": values["bearing_yield_kn"],
        "outstand_limit_mm": values["outstand_limit_mm"],
        "outstand_satisfied": result["checks"][2]["satisfied"],
    }


def zero_restrained_flanges():
    return expect_rejected(
        lambda: run_webs(
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
    )


def over_scope_yield():
    return expect_rejected(lambda: run_webs(stiffener(stiffener_yield_mpa=690.1)))


def unidentified_steel_limits():
    boundary = run_materials(
        {
            "operation": "unidentified_steel",
            "design_yield_strength_mpa": 170,
            "design_tensile_strength_mpa": 300,
            "surface_imperfections_verified": True,
            "properties_and_weldability_verified": True,
            "full_test_to_as1391_verified": False,
        }
    )
    if not boundary["checked_conditions_satisfied"]:
        raise AssertionError("Clause 2.2.3 limit values were rejected")
    expect_close(boundary["checks"][0]["limit_mpa"], 170)
    expect_close(boundary["checks"][1]["limit_mpa"], 300)
    above = run_materials(
        {
            "operation": "unidentified_steel",
            "design_yield_strength_mpa": 170.001,
            "design_tensile_strength_mpa": 300.001,
            "surface_imperfections_verified": True,
            "properties_and_weldability_verified": True,
            "full_test_to_as1391_verified": False,
        }
    )
    if above["checked_conditions_satisfied"] or [
        check["satisfied"] for check in above["checks"]
    ] != [False, False]:
        raise AssertionError("Clause 2.2.3 over-limit values were not both rejected")
    return {"boundary_limits_mpa": [170, 300], "both_over_limit_values_rejected": True}


def clause_2_2_4_properties():
    values = run_materials({"operation": "design_properties"})["values"]
    expected = {
        "elastic_modulus_mpa": 200000,
        "shear_modulus_mpa": 80000,
        "poisson_ratio": 0.25,
        "thermal_expansion_per_c": 11.7e-6,
    }
    if values != expected:
        raise AssertionError(f"unexpected Clause 2.2.4 properties: {values}")
    return values


def clause_2_2_5_z_quality():
    result = run_materials(
        {
            "operation": "through_thickness_deformation",
            "product_standard": "AS/NZS 3678",
            "material_thickness_mm": 20,
            "required_design_z_value": 21,
            "appendix_m_assessment_verified": True,
            "appendix_m_assessment_reference": "WELD-DESIGN-4100-01",
            "available_z_quality_class": "Z25",
            "material_certificate_verified": True,
            "material_certificate_reference": "MILL-CERT-4100-01",
        }
    )
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 2.2.5 accepted evidence was rejected")
    check = result["checks"][0]
    if check["required_z_quality_class"] != "Z25":
        raise AssertionError("Clause 2.2.5 ZEd=21 did not require Z25")
    if check["required_reduction_of_area_percent"] != 25:
        raise AssertionError("Clause 2.2.5 Z25 reduction-of-area threshold is incorrect")
    insufficient = run_materials(
        {
            "operation": "through_thickness_deformation",
            "product_standard": "AS/NZS 3678",
            "material_thickness_mm": 20,
            "required_design_z_value": 21,
            "appendix_m_assessment_verified": True,
            "appendix_m_assessment_reference": "WELD-DESIGN-4100-01",
            "available_z_quality_class": "Z15",
            "material_certificate_verified": True,
            "material_certificate_reference": "MILL-CERT-4100-02",
        }
    )
    if insufficient["checked_conditions_satisfied"]:
        raise AssertionError("Clause 2.2.5 accepted an insufficient Z-quality class")
    return {"required_class_at_zed_21": check["required_z_quality_class"], "Z15_rejected": True}


def appendix_m_table_m2_z_quality():
    result = run_materials(
        {
            "operation": "appendix_m_through_thickness_design",
            "product_standard": "AS/NZS 3678",
            "material_thickness_mm": 45,
            "effective_weld_depth_mm": 25,
            "table_m2_b_case": "multi_run_fillet",
            "remote_restraint": "high",
            "preheating_condition": "without_preheating",
            "compression_reduction_basis": "not_applicable",
            "effective_weld_depth_assessment_verified": True,
            "table_m2_weld_form_case_verified": True,
            "remote_restraint_classification_verified": True,
            "preheating_condition_verified": True,
            "compression_reduction_applicability_verified": True,
            "available_z_quality_class": "Z25",
            "material_certificate_verified": True,
            "material_certificate_reference": "MILL-CERT-M2-01",
        }
    )
    values = result["values"]
    terms = {"z_a": 9, "z_b": 0, "z_c_after_reduction": 10, "z_d": 5, "z_e": 0}
    for name, expected in terms.items():
        expect_close(values[name], expected)
    expect_close(values["required_design_z_value"], 24)
    if values["required_z_quality_class"] != "Z25" or not result["checked_conditions_satisfied"]:
        raise AssertionError("Appendix M.2 ZEd=24 did not pass the supplied Z25 material class")
    return {**terms, "required_design_z_value": 24, "required_z_quality_class": "Z25"}


def clause_14_3_2_hole_sizes_and_use():
    standard = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "standard",
            "bolt_diameter_mm": 24,
            "hole_diameter_mm": 26,
        }
    )
    expect_close(standard["values"]["maximum_hole_diameter_mm"], 24 + 2)
    if not standard["checked_conditions_satisfied"]:
        raise AssertionError("Clause 14.3.2 rejected the 24 mm standard-hole boundary")

    oversize = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "oversize",
            "bolt_diameter_mm": 20,
            "hole_diameter_mm": 28,
            "not_base_plate_anchor_hole_verified": True,
            "connection_type": "friction_type",
            "subject_to_shear": False,
            "head_side": {"bears_on_holed_ply": False, "washer": None},
            "nut_side": {"bears_on_holed_ply": False, "washer": None},
        }
    )
    expect_close(oversize["values"]["maximum_hole_diameter_mm"], max(1.25 * 20, 20 + 8))
    beyond = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "oversize",
            "bolt_diameter_mm": 20,
            "hole_diameter_mm": 28.001,
            "not_base_plate_anchor_hole_verified": True,
            "connection_type": "friction_type",
            "subject_to_shear": False,
            "head_side": {"bears_on_holed_ply": False, "washer": None},
            "nut_side": {"bears_on_holed_ply": False, "washer": None},
        }
    )
    if (
        oversize["checked_conditions_satisfied"] is not True
        or beyond["checked_conditions_satisfied"]
    ):
        raise AssertionError("Clause 14.3.2 oversize-hole upper boundary failed")

    short_slot = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "short_slot",
            "bolt_diameter_mm": 20,
            "hole_width_mm": 22,
            "hole_length_mm": 30,
            "not_base_plate_anchor_hole_verified": True,
            "connection_type": "friction_type",
            "subject_to_shear": True,
            "head_side": {"bears_on_holed_ply": False, "washer": None},
            "nut_side": {"bears_on_holed_ply": False, "washer": None},
        }
    )
    expect_close(short_slot["values"]["maximum_hole_length_mm"], max(1.33 * 20, 20 + 10))
    if not short_slot["checked_conditions_satisfied"]:
        raise AssertionError("Clause 14.3.2 rejected the short-slot boundary")

    long_slot = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "long_slot",
            "bolt_diameter_mm": 20,
            "hole_width_mm": 22,
            "hole_length_mm": 50,
            "not_base_plate_anchor_hole_verified": True,
            "connection_type": "friction_type",
            "subject_to_shear": True,
            "alternate_plies_verified": True,
            "head_side": {
                "bears_on_holed_ply": True,
                "washer": {
                    "type": "plate",
                    "thickness_mm": 8,
                    "minimum_edge_clearance_mm": 11,
                    "coverage_geometry_verified": True,
                    "product_verified": True,
                    "material_as_nzs_3678_verified": True,
                },
            },
            "nut_side": {"bears_on_holed_ply": False, "washer": None},
        }
    )
    expect_close(long_slot["values"]["maximum_hole_length_mm"], 2.5 * 20)
    if not long_slot["checked_conditions_satisfied"]:
        raise AssertionError("Clause 14.3.2 long-slot conditions failed")
    return {
        "standard_24_mm_boundary": 26,
        "oversize_maximum_mm": 28,
        "oversize_over_limit_rejected": True,
        "short_slot_maximum_length_mm": 30,
        "long_slot_maximum_length_mm": 50,
        "long_slot_alternate_plies_and_washer_pass": True,
    }


def clause_14_fabrication_procedure_and_tolerances():
    basis = run_fabrication(
        {
            "check_type": "fabrication_basis",
            "materials_conform_referenced_standards_verified": True,
            "surface_defects_removed_per_referenced_standards_verified": True,
            "steel_grade_identifiable_at_all_fabrication_stages_verified": False,
            "steel_classified_as_unidentified": True,
            "clause_2_2_3_unidentified_steel_inputs": {
                "operation": "unidentified_steel",
                "design_yield_strength_mpa": 170,
                "design_tensile_strength_mpa": 300,
                "surface_imperfections_verified": True,
                "properties_and_weldability_verified": True,
                "full_test_to_as1391_verified": False,
            },
            "marking_does_not_damage_material_verified": True,
            "fabrication_per_as_nzs_5131_verified": True,
            "fabrication_methods_preserve_design_properties_verified": True,
        }
    )
    if basis["clauses"] != ["2.2.3", "14.2.1", "14.2.2", "14.3.1"]:
        raise AssertionError("Clause 14.2.2 did not evaluate the unidentified-steel route")
    if not basis["checked_conditions_satisfied"]:
        raise AssertionError("Clause 14.2.2/14.3.1 accepted fabrication evidence was rejected")

    assembly = run_fabrication(
        {
            "check_type": "bolt_assembly",
            "connection_type": "bearing_type",
            "bolts_nuts_washers_conform_clause_2_3_1_verified": True,
            "all_material_within_bolt_grip_is_steel_verified": True,
            "clear_threads_above_nut_count": 1,
            "thread_plus_runout_clear_beneath_nut_verified": True,
            "rotated_part": "nut",
            "washer_under_rotated_part_verified": True,
            "maximum_contact_surface_slope_ratio": 0.05,
            "contact_surface_slope_measurement_verified": True,
            "subject_to_vibration": False,
            "fully_tensioned_high_strength_bolt_installed_during_fabrication": False,
        }
    )
    if not assembly["checked_conditions_satisfied"]:
        raise AssertionError("Clause 14.3.3.1 bolt assembly boundary was rejected")

    tolerance_result = run_fabrication(
        {
            "check_type": "geometric_tolerance",
            "tolerance_type": "essential",
            "measured_deviation_mm": 3,
            "permissible_deviation_mm": 2,
            "as_nzs_5131_tolerance_limit_verified": True,
            "measurement_after_fabrication_and_corrosion_protection_verified": True,
            "coating_thickness_excluded_from_measurement_verified": True,
            "excess_deviation_in_revised_design_capacity_verified": True,
        }
    )
    if not tolerance_result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 14.4.2 revised-capacity route was rejected")
    acceptance = run_fabrication(
        {
            "check_type": "fabricated_item_acceptance",
            "clause_14_2_material_requirements_satisfied": False,
            "clause_14_3_fabrication_requirements_satisfied": True,
            "clause_14_4_tolerances_satisfied": True,
            "structural_adequacy_and_intended_use_unimpaired_demonstrated": False,
            "section_17_testing_passed": True,
        }
    )
    if not acceptance["values"]["fabricated_item_may_be_accepted"]:
        raise AssertionError("Clause 14.1 Section 17 acceptance route failed")
    return {
        "unidentified_steel_clause_2_2_3_route_passed": True,
        "bolt_assembly_thread_and_slope_checks_passed": True,
        "essential_tolerance_revised_design_route_passed": True,
        "clause_14_1_section_17_acceptance_route_passed": True,
    }


def clause_2_3_2_equivalent_high_strength_fastener():
    reference = {
        "operation": "equivalent_high_strength_fastener",
        "fastener_reference": "VERIFY-EQUIVALENT-FASTENER-01",
        "reference_nominal_bolt_diameter_mm": 20,
        "equivalent_fastener_nominal_diameter_mm": 20,
        "bolt_grade": "8.8",
        "reference_bolt_dimensions_match_nominal_size_verified": True,
        "reference_bolt_body_diameter_mm": 20,
        "equivalent_fastener_body_diameter_mm": 20,
        "reference_head_bearing_area_mm2": 300,
        "equivalent_fastener_head_bearing_area_mm2": 300,
        "reference_nut_bearing_area_mm2": 200,
        "equivalent_fastener_nut_bearing_area_mm2": 200,
        "equivalent_fastener_minimum_tension_kn": 145,
        "chemical_composition_and_mechanical_properties_equivalent_verified": True,
        "tensioning_and_inspection_procedure_checkable_verified": True,
        "test_certificate_reference": "VERIFY-EQUIVALENT-FASTENER-CERT-01",
        "installation_procedure_reference": "VERIFY-EQUIVALENT-FASTENER-INSTALL-01",
    }
    accepted = run_erection(reference)
    if accepted["clauses"] != ["2.3.2", "15.2.2.2"]:
        raise AssertionError("Equivalent-fastener clause trace was incomplete")
    if accepted["values"]["table_15_2_2_2_reference_minimum_tension_kn"] != 145:
        raise AssertionError("Equivalent-fastener reference tension was incorrect")
    if not accepted["checked_conditions_satisfied"]:
        raise AssertionError("Equivalent fastener at the reference minimum should pass")
    below = run_erection({**reference, "equivalent_fastener_minimum_tension_kn": 144.99})
    if below["checked_conditions_satisfied"]:
        raise AssertionError("Equivalent fastener below the reference tension should fail")
    return {
        "table_reference_minimum_tension_kn": 145,
        "equal_minimum_passes": True,
        "below_minimum_fails": True,
    }


def clause_15_erection_and_tensioning():
    # Independently transcribed from licensed AS 4100:2020 Table 15.2.2.2.
    expected_tensions = {
        (16, "8.8"): 95,
        (16, "10.9"): 130,
        (20, "8.8"): 145,
        (20, "10.9"): 205,
        (24, "8.8"): 210,
        (24, "10.9"): 295,
        (30, "8.8"): 335,
        (30, "10.9"): 465,
        (36, "8.8"): 490,
        (36, "10.9"): 680,
    }
    checked = []
    for (diameter, grade), minimum in expected_tensions.items():
        output = run_erection(
            {
                "operation": "bolted_connection_assembly",
                "connection_type": "fully_tensioned",
                "assembly_per_as_nzs_5131_verified": True,
                "bolt_group_reference": f"VERIFY-M{diameter}-{grade}",
                "nominal_bolt_diameter_mm": diameter,
                "bolt_grade": grade,
                "bolt_tension_measurements": [{"bolt_id": "B1", "measured_tension_kn": minimum}],
                "homogeneous_bolt_group_verified": True,
                "all_bolts_in_group_listed_verified": True,
                "all_bolts_in_group_tightened_verified": True,
                "tensioning_method": "direct_tension_indicator",
                "tensioning_method_per_as_nzs_5131_verified": True,
            }
        )
        expect_close(output["values"]["required_minimum_bolt_tension_kn"], minimum)
        if not output["checked_conditions_satisfied"]:
            raise AssertionError(f"Table 15.2.2.2 M{diameter} {grade} exact minimum failed")
        checked.append(minimum)

    below = run_erection(
        {
            "operation": "bolted_connection_assembly",
            "connection_type": "fully_tensioned",
            "assembly_per_as_nzs_5131_verified": True,
            "bolt_group_reference": "VERIFY-BELOW",
            "nominal_bolt_diameter_mm": 16,
            "bolt_grade": "8.8",
            "bolt_tension_measurements": [{"bolt_id": "B1", "measured_tension_kn": 94.99}],
            "homogeneous_bolt_group_verified": True,
            "all_bolts_in_group_listed_verified": True,
            "all_bolts_in_group_tightened_verified": True,
            "tensioning_method": "part_turn",
            "tensioning_method_per_as_nzs_5131_verified": True,
        }
    )
    if below["checked_conditions_satisfied"]:
        raise AssertionError("A bolt below Table 15.2.2.2 minimum tension passed")

    tolerance = run_erection(
        {
            "operation": "geometric_tolerance",
            "tolerance_type": "essential",
            "measured_deviation_mm": 3,
            "permissible_deviation_mm": 2,
            "as_nzs_5131_tolerance_limit_verified": True,
            "measurement_after_erection_completed_verified": True,
            "excess_deviation_in_revised_design_capacity_verified": True,
        }
    )
    if not tolerance["checked_conditions_satisfied"]:
        raise AssertionError("Clause 15.3.2 revised-capacity route failed")

    acceptance = run_erection(
        {
            "operation": "erected_item_acceptance",
            "clause_15_2_erection_requirements_satisfied": False,
            "clause_15_3_tolerances_satisfied": False,
            "bolt_hardware_conforms_clauses_14_3_3_and_15_2": True,
            "structural_adequacy_and_intended_use_unimpaired_demonstrated": False,
            "section_17_testing_passed": True,
        }
    )
    if not acceptance["values"]["erected_item_may_be_accepted"]:
        raise AssertionError("Clause 15.1.1 Section 17 acceptance route failed")
    return {
        "table_15_2_2_2_minimum_tensions_kn": checked,
        "below_table_minimum_rejected": True,
        "clause_15_3_2_revised_capacity_route_passed": True,
        "clause_15_1_1_section_17_acceptance_route_passed": True,
    }


def clause_17_test_scope_and_prototype():
    scope = run_testing(
        {
            "check_type": "test_scope_applicability",
            "test_article": "individual_member",
            "test_type": "proof",
            "test_purpose": "specific_unit_characteristics",
            "design_complies_with_as_4100_verified": True,
            "special_circumstances_require_test_verified": False,
            "test_used_as_alternative_to_calculation_verified": False,
        }
    )["results"]
    if (
        not scope["check_satisfied"]
        or not scope[
            "testing_not_required_for_standard_compliant_design_without_special_circumstances"
        ]
    ):
        raise AssertionError("Clauses 17.1.1–17.2 scope or applicability check failed")

    prototype = run_testing(
        {
            "check_type": "prototype_strength",
            "design_load_kn": 100,
            "sustained_load_kn": 140,
            "sustained_duration_min": 5,
            "number_similar_units": 2,
            "materials_conform_section_2_verified": True,
            "fabrication_conforms_section_14_verified": True,
            "manufacturing_specification_requirements_met_verified": True,
            "erection_method_represents_production_verified": True,
            "production_units_similar": True,
            "calibrated_loading_without_artificial_restraints": True,
            "representative_force_distribution_and_duration": True,
            "loading_rate_as_uniform_as_practicable_verified": True,
            "deformations_recorded_before_during_after": True,
            "loading_method_recorded": True,
            "deflection_measurement_method_recorded": True,
            "other_relevant_test_data_recorded": True,
            "acceptance_statement_recorded": True,
            "test_report_complete": True,
        }
    )["results"]
    expect_close(prototype["test_load_factor"], 1.4)
    expect_close(prototype["required_test_load_kn"], 140)
    if not prototype["check_satisfied"]:
        raise AssertionError("Clauses 17.5.1–17.5.4 prototype acceptance failed")
    return {
        "test_scope_and_proof_definition_passed": True,
        "standard_design_testing_default": "not_required",
        "two_unit_prototype_strength_factor": prototype["test_load_factor"],
        "prototype_conditions_passed": True,
    }


def clause_16_existing_structure_modification():
    result = run_testing(
        {
            "check_type": "existing_structure_modification_review",
            "other_as4100_provisions_applied_unless_modified_verified": True,
            "site_modifications_during_erection_applicable": True,
            "site_modifications_conform_as_nzs_5131_verified": True,
            "existing_modification_or_repair_applicable": True,
            "existing_modification_or_repair_conforms_as_nzs_5131_verified": True,
            "strengthening_repair_or_welding_documents_prepared": True,
            "base_metal_types_determined_before_documents_verified": True,
        }
    )["results"]
    if not result["check_satisfied"]:
        raise AssertionError("Clauses 16.1–16.2 accepted evidence was rejected")
    late_identification = run_testing(
        {
            "check_type": "existing_structure_modification_review",
            "other_as4100_provisions_applied_unless_modified_verified": True,
            "site_modifications_during_erection_applicable": False,
            "site_modifications_conform_as_nzs_5131_verified": False,
            "existing_modification_or_repair_applicable": True,
            "existing_modification_or_repair_conforms_as_nzs_5131_verified": True,
            "strengthening_repair_or_welding_documents_prepared": True,
            "base_metal_types_determined_before_documents_verified": False,
        }
    )["results"]
    if late_identification["check_satisfied"]:
        raise AssertionError("Clause 16.2 accepted late base-metal identification")
    return {
        "applicable_section_16_routes_passed": True,
        "late_base_metal_identification_rejected": True,
    }


def clause_8_4_6_amended_angle_interaction():
    passed = run_advanced_members(
        {
            "operation": "angle_combined_interaction",
            "design_compression_kn": 90,
            "design_moment_about_h_knm": 9,
            "nominal_member_compression_nch_kn": 200,
            "nominal_member_bending_mbx_knm": 40,
            "angle_between_x_and_h_deg": 60,
            "clause_8_3_interaction_satisfied": True,
            "single_angle_web_compression_member_in_truss_verified": True,
            "end_connection_at_least_two_bolts_or_welded_verified": True,
            "loaded_through_one_leg_figure_8_4_6_verified": True,
            "angle_axis_orientation_verified": True,
            "nominal_nch_mbx_calculations_verified": True,
        }
    )
    if not isclose(passed["values"]["interaction_utilisation"], 1.0, rel_tol=0, abs_tol=1e-12):
        raise AssertionError("Amended Clause 8.4.6 interaction boundary is incorrect")
    if not passed["checked_conditions_satisfied"]:
        raise AssertionError("Amended Clause 8.4.6 exact boundary was rejected")
    outside = run_advanced_members(
        {
            "operation": "angle_combined_interaction",
            "design_compression_kn": 90,
            "design_moment_about_h_knm": 9.001,
            "nominal_member_compression_nch_kn": 200,
            "nominal_member_bending_mbx_knm": 40,
            "angle_between_x_and_h_deg": 60,
            "clause_8_3_interaction_satisfied": True,
            "single_angle_web_compression_member_in_truss_verified": True,
            "end_connection_at_least_two_bolts_or_welded_verified": True,
            "loaded_through_one_leg_figure_8_4_6_verified": True,
            "angle_axis_orientation_verified": True,
            "nominal_nch_mbx_calculations_verified": True,
        }
    )
    if outside["checked_conditions_satisfied"]:
        raise AssertionError("Amended Clause 8.4.6 accepted an over-capacity interaction")
    return {
        "exact_interaction_boundary": passed["values"]["interaction_utilisation"],
        "boundary_accepted": True,
        "above_boundary_rejected": True,
    }


def clause_6_3_3_c_amended_lambda_20_row():
    expected = [(-1, 1.000), (-0.5, 0.989), (0, 0.978), (0.5, 0.967), (1, 0.956)]
    observed = []
    for constant, table_factor in expected:
        result = run_members(
            {
                "operation": "compression",
                "yield_strength_mpa": 250,
                "gross_area_mm2": 1000,
                "net_area_mm2": 1000,
                "effective_area_mm2": 1000,
                "effective_length_x_mm": 200,
                "effective_length_y_mm": 200,
                "radius_x_mm": 10,
                "radius_y_mm": 10,
                "section_constant_x": constant,
                "section_constant_y": constant,
                "action_kn": 100,
                "geometry": "doubly_symmetric",
            }
        )
        factor = result["values"]["reduction_x"]
        if not isclose(factor, table_factor, rel_tol=0, abs_tol=0.00051):
            raise AssertionError(
                f"Amd 1 Table 6.3.3(C) at lambda_n=20, alpha_b={constant}: "
                f"expected {table_factor}, observed {factor}"
            )
        observed.append(factor)
    return {"amended_lambda_20_reduction_factors": observed}


def appendix_h4_amended_closed_section_torsion_constant():
    result = run_advanced_members(
        {
            "operation": "closed_section_torsion_constant",
            "enclosed_median_line_area_mm2": 10_000,
            "wall_segments": [
                {"median_line_length_mm": 100, "thickness_mm": 5},
                {"median_line_length_mm": 100, "thickness_mm": 5},
                {"median_line_length_mm": 100, "thickness_mm": 5},
                {"median_line_length_mm": 100, "thickness_mm": 5},
            ],
            "single_cell_thin_walled_closed_section_verified": True,
            "median_line_geometry_verified": True,
        }
    )
    value = result["values"]["torsion_constant_j_mm4"]
    if not isclose(value, 5_000_000, rel_tol=0, abs_tol=1e-9):
        raise AssertionError(f"Amended Appendix H.4 expected J=5000000, observed {value}")
    return {"square_closed_section_torsion_constant_mm4": value}


def appendix_h4_open_section_torsion_constant():
    result = run_advanced_members(
        {
            "operation": "open_section_torsion_constant",
            "wall_segments": [
                {"median_line_length_mm": 1200, "thickness_mm": 3},
                {"median_line_length_mm": 600, "thickness_mm": 6},
            ],
            "all_wall_segments_and_thin_walled_open_geometry_verified": True,
        }
    )
    values = result["values"]
    expected_contributions = [10_800, 43_200]
    if values["wall_segment_contributions_mm4"] != expected_contributions:
        raise AssertionError(
            "Appendix H.4 open-section wall contributions differ from independent "
            "b*t^3/3 arithmetic"
        )
    value = values["torsion_constant_j_approx_mm4"]
    if not isclose(value, 54_000, rel_tol=0, abs_tol=1e-9):
        raise AssertionError(f"Appendix H.4 expected approximate J=54000, observed {value}")
    return {"open_section_torsion_constant_approx_mm4": value}


def clause_5_2_6_hole_moduli():
    result = run_members(
        {
            "operation": "section_moduli",
            "method": "area_ratio",
            "yield_strength_mpa": 300,
            "ultimate_strength_mpa": 400,
            "gross_area_mm2": 4000,
            "gross_web_area_mm2": 2000,
            "gross_flange_areas_mm2": [1000, 1000],
            "net_flange_areas_mm2": [800, 1000],
            "gross_elastic_modulus_mm3": 100000,
            "gross_plastic_modulus_mm3": 130000,
        }
    )
    values = result["values"]
    expect_close(values["net_area_mm2"], 3800)
    expect_close(values["net_to_gross_area_ratio"], 0.95)
    expect_close(values["elastic_modulus_mm3"], 95000)
    expect_close(values["plastic_modulus_mm3"], 123500)
    if values["selected_method"] != "area_ratio":
        raise AssertionError("Clause 5.2.6 did not select the area-ratio method")
    return {
        "net_to_gross_area_ratio": values["net_to_gross_area_ratio"],
        "elastic_modulus_mm3": values["elastic_modulus_mm3"],
        "plastic_modulus_mm3": values["plastic_modulus_mm3"],
    }


def clause_5_2_5_internal_gradient():
    values = run_members(
        {
            "operation": "plate",
            "yield_strength_mpa": 250,
            "elastic_modulus_mm3": 100000,
            "plastic_modulus_mm3": 130000,
            "plate": {
                "width_mm": 1200,
                "thickness_mm": 10,
                "edges": "both",
                "stress": "internal_gradient",
                "residual": "HR",
            },
        }
    )["values"]
    expected = 100000 * (115 / 120) ** 2
    expect_close(values["effective_modulus_mm3"], expected)
    if values["compression_effective_width_mm"] is not None:
        raise AssertionError("Internal-gradient bending returned a uniform-compression width")
    return {
        "yield_limit": values["yield_limit"],
        "effective_modulus_mm3": values["effective_modulus_mm3"],
        "uniform_compression_width_not_applied": True,
    }


def clause_5_2_section_moment_capacity():
    result = run_members(
        {
            "operation": "section_moment_capacity",
            "yield_strength_mpa": 250,
            "elastic_modulus_mm3": 100000,
            "plastic_modulus_mm3": 130000,
            "plate_elements": [
                {
                    "element_id": "web",
                    "width_mm": 1100,
                    "thickness_mm": 10,
                    "edges": "both",
                    "stress": "internal_gradient",
                    "residual": "HR",
                },
                {
                    "element_id": "compression_flange",
                    "width_mm": 250,
                    "thickness_mm": 10,
                    "edges": "one",
                    "stress": "uniform",
                    "residual": "HR",
                },
            ],
        }
    )
    values = result["values"]
    expect_close(values["governing_element_slenderness_to_yield_limit_ratio"], 25 / 16)
    expect_close(values["effective_section_modulus_mm3"], 64000)
    expect_close(values["nominal_section_moment_capacity_knm"], 16)
    if values["governing_element_id"] != "compression_flange":
        raise AssertionError("Clause 5.2.2 selected by raw slenderness instead of normalized ratio")
    return {
        "governing_element_id": values["governing_element_id"],
        "effective_section_modulus_mm3": values["effective_section_modulus_mm3"],
        "nominal_section_moment_capacity_knm": values["nominal_section_moment_capacity_knm"],
    }


def clause_5_1_bending_design_routes():
    major = run_members(
        {
            "operation": "bending_design",
            "method": "elastic_major_axis",
            "action_knm": 81,
            "nominal_section_capacity_knm": 100,
            "nominal_member_capacity_knm": 90,
        }
    )
    expect_close(major["values"]["design_section_moment_capacity_knm"], 90)
    expect_close(major["values"]["design_member_moment_capacity_knm"], 81)
    if not all(major["checks"][key]["satisfied"] for key in ("section_moment", "member_moment")):
        raise AssertionError("Clause 5.1 major-axis section/member checks failed at equality")

    minor = run_members(
        {
            "operation": "bending_design",
            "method": "elastic_minor_axis",
            "action_knm": 45,
            "nominal_section_capacity_knm": 50,
        }
    )
    expect_close(minor["values"]["design_section_moment_capacity_knm"], 45)
    if not minor["checks"]["section_moment"]["satisfied"]:
        raise AssertionError("Clause 5.1 minor-axis check failed at equality")

    plastic_inputs = {
        "operation": "bending_design",
        "method": "plastic",
        "action_knm": 90,
        "nominal_section_capacity_knm": 100,
        "hinge_sections_compact_verified": True,
        "full_lateral_restraint_verified": True,
        "web_clause_5_10_6_satisfied": True,
    }
    plastic = run_members(plastic_inputs)
    expect_close(plastic["values"]["design_section_moment_capacity_knm"], 90)
    if not plastic["values"]["plastic_method_prerequisites_satisfied"]:
        raise AssertionError("Clause 5.1 plastic route rejected complete eligibility evidence")
    ineligible = run_members({**plastic_inputs, "full_lateral_restraint_verified": False})
    if ineligible["values"]["plastic_method_prerequisites_satisfied"]:
        raise AssertionError("Clause 5.1 plastic route accepted missing lateral restraint")

    over_member = run_members(
        {
            "operation": "bending_design",
            "method": "elastic_major_axis",
            "action_knm": 81.001,
            "nominal_section_capacity_knm": 100,
            "nominal_member_capacity_knm": 90,
        }
    )
    if over_member["checks"]["member_moment"]["satisfied"]:
        raise AssertionError("Clause 5.1 major-axis member check accepted demand above capacity")
    return {
        "major_axis_section_design_capacity_knm": major["values"][
            "design_section_moment_capacity_knm"
        ],
        "major_axis_member_design_capacity_knm": major["values"][
            "design_member_moment_capacity_knm"
        ],
        "minor_axis_section_design_capacity_knm": minor["values"][
            "design_section_moment_capacity_knm"
        ],
        "plastic_method_prerequisites_satisfied": plastic["values"][
            "plastic_method_prerequisites_satisfied"
        ],
        "member_over_capacity_rejected": not over_member["checks"]["member_moment"]["satisfied"],
    }


def clause_5_3_2_4_lateral_restraint():
    result = run_advanced_members(
        {
            "operation": "full_lateral_restraint_limit",
            "section_type": "unequal_flange_i",
            "segment_length_mm": 268.3281572999747,
            "yield_strength_mpa": 250,
            "beta_m_basis": "conservative_minus_one",
            "section_properties_verified": True,
            "both_ends_restrained_verified": True,
            "radius_of_gyration_y_mm": 10,
            "gross_area_mm2": 10000,
            "flange_centroid_spacing_mm": 400,
            "compression_flange_minor_inertia_mm4": 1000000,
            "section_minor_inertia_mm4": 2000000,
            "effective_section_modulus_ex_mm3": 2000000,
        }
    )
    values = result["values"]
    expected_limit = 30 * (0.8**0.5)
    expect_close(values["beta_m"], -1)
    expect_close(values["compression_flange_inertia_ratio"], 0.5)
    expect_close(values["permitted_slenderness"], expected_limit)
    expect_close(values["segment_slenderness"], expected_limit)
    if not values["full_lateral_restraint_qualifies"]:
        raise AssertionError("Clause 5.3.2.4 rejected the equality boundary")
    return {
        "beta_m": values["beta_m"],
        "permitted_slenderness": values["permitted_slenderness"],
        "boundary_qualifies": values["full_lateral_restraint_qualifies"],
    }


def clause_5_4_2_restraint_classification():
    full_by_critical_flange = run_advanced_members(
        {
            "operation": "restraint_classification",
            "critical_flange_lateral_deflection_prevented_verified": True,
            "other_cross_section_point_lateral_deflection_prevented_verified": False,
            "twist_rotation_effectively_prevented_verified": False,
            "twist_rotation_partially_prevented_verified": True,
            "critical_flange_out_of_plane_rotation_significantly_restrained_verified": False,
        }
    )
    if not full_by_critical_flange["values"]["full_lateral_restraint_qualifies"]:
        raise AssertionError("Clause 5.4.2.1(a) critical-flange alternative was not recognized")

    full_by_other_point = run_advanced_members(
        {
            "operation": "restraint_classification",
            "critical_flange_lateral_deflection_prevented_verified": False,
            "other_cross_section_point_lateral_deflection_prevented_verified": True,
            "twist_rotation_effectively_prevented_verified": True,
            "twist_rotation_partially_prevented_verified": False,
            "critical_flange_out_of_plane_rotation_significantly_restrained_verified": False,
        }
    )
    if not full_by_other_point["values"]["full_lateral_restraint_qualifies"]:
        raise AssertionError("Clause 5.4.2.1(b) other-point alternative was not recognized")

    partial = run_advanced_members(
        {
            "operation": "restraint_classification",
            "critical_flange_lateral_deflection_prevented_verified": False,
            "other_cross_section_point_lateral_deflection_prevented_verified": True,
            "twist_rotation_effectively_prevented_verified": False,
            "twist_rotation_partially_prevented_verified": True,
            "critical_flange_out_of_plane_rotation_significantly_restrained_verified": False,
        }
    )
    if not partial["values"]["partial_lateral_restraint_qualifies"]:
        raise AssertionError("Clause 5.4.2.2 partial-restraint criteria were not recognized")
    return {
        "full_restraint_critical_flange_route": full_by_critical_flange["values"][
            "full_lateral_restraint_qualifies"
        ],
        "full_restraint_other_point_route": full_by_other_point["values"][
            "full_lateral_restraint_qualifies"
        ],
        "partial_restraint_route": partial["values"]["partial_lateral_restraint_qualifies"],
    }


def clause_5_4_3_4_lateral_rotation_restraint():
    comparable = run_advanced_members(
        {
            "operation": "lateral_rotation_restraint",
            "method": "comparable_stiffness",
            "cross_section_restraint_classification": "partially_restrained",
            "cross_section_restraint_classification_verified": True,
            "restraint_flexural_stiffness_comparable_to_member_verified": True,
            "stiffness_evidence_reference": "BENCHMARK-STIFFNESS-01",
        }
    )
    adjacent = run_advanced_members(
        {
            "operation": "lateral_rotation_restraint",
            "method": "adjacent_continuous_segment",
            "segment_full_lateral_restraint_verified": True,
            "adjacent_segment_laterally_continuous_verified": True,
            "restraint_evidence_reference": "BENCHMARK-RESTRAINT-01",
        }
    )
    buckling = run_advanced_members(
        {
            "operation": "lateral_rotation_restraint",
            "method": "buckling_analysis",
            "member_resistance_determined_by_buckling_analysis_verified": True,
            "buckling_analysis_reference": "BENCHMARK-BUCKLING-01",
        }
    )
    outcomes = [
        comparable["values"]["lateral_rotation_restraint_effective"],
        adjacent["values"]["lateral_rotation_restraint_effective"],
        buckling["values"]["lateral_rotation_restraint_effective"],
    ]
    if outcomes != [True, True, True]:
        raise AssertionError("Clause 5.4.3.4 did not accept all three evidenced routes")
    if any(result["full_standard_compliance"] for result in (comparable, adjacent, buckling)):
        raise AssertionError("Clause 5.4.3.4 route implied full-standard compliance")
    return {
        "comparable_stiffness_route": outcomes[0],
        "adjacent_continuous_segment_route": outcomes[1],
        "clause_5_6_4_buckling_analysis_route": outcomes[2],
    }


def clause_5_3_2_1_capacity_restraint():
    result = run_members(
        {
            "operation": "bending",
            "section_capacity_knm": 100,
            "iy_mm4": 10000000,
            "torsion_constant_mm4": 100000,
            "warping_constant_mm6": 0,
            "effective_length_mm": 1000,
            "moment_factor": 2,
            "action_knm": 10,
            "geometry": "equal_flanged_open",
        }
    )
    values = result["values"]
    expect_close(values["member_capacity_knm"], 100)
    if not values["full_lateral_restraint_qualifies"]:
        raise AssertionError("Clause 5.3.2.1 did not accept Mb equal to Ms")
    return {
        "member_capacity_knm": values["member_capacity_knm"],
        "full_lateral_restraint": values["full_lateral_restraint_qualifies"],
    }


def clause_5_3_3_critical_section():
    result = run_advanced_members(
        {
            "operation": "critical_section",
            "sections": [
                {
                    "section_id": "A",
                    "design_moment_knm": 20,
                    "section_moment_capacity_knm": 40,
                },
                {
                    "section_id": "B",
                    "design_moment_knm": 36,
                    "section_moment_capacity_knm": 60,
                },
                {
                    "section_id": "C",
                    "design_moment_knm": 30,
                    "section_moment_capacity_knm": 100,
                },
            ],
        }
    )
    values = result["values"]
    expect_close(values["maximum_moment_to_capacity_ratio"], 0.6)
    if values["critical_section_ids"] != ["B"]:
        raise AssertionError("Clause 5.3.3 selected the wrong critical section")
    return {
        "critical_section_id": values["critical_section_id"],
        "maximum_moment_to_capacity_ratio": values["maximum_moment_to_capacity_ratio"],
    }


def clause_5_5_3_critical_flange():
    result = run_advanced_members(
        {
            "operation": "critical_flange",
            "segment_end_condition": "one_end_unrestrained",
            "dominant_load": "wind",
            "wind_case": "internal_pressure",
            "exterior_flange_position": "top",
        }
    )
    values = result["values"]
    if values["critical_flange_position"] != "bottom":
        raise AssertionError("Clause 5.5.3 internal pressure did not select interior flange")
    return {
        "critical_flange_position": values["critical_flange_position"],
        "critical_flange_location": values["critical_flange_location"],
    }


def clause_5_6_1_1_b_varying_section():
    result = run_advanced_members(
        {
            "operation": "varying_section_bending",
            "design_method": "critical_section_reduced_reference",
            "section_capacity_knm": 120,
            "reference_buckling_moment_knm": 100,
            "reference_buckling_moment_verified": True,
            "moment_factor": 1.3,
            "moment_factor_verified": True,
            "both_ends_restrained_verified": True,
            "action_knm": 60,
            "variation_type": "stepped",
            "segment_length_mm": 6000,
            "reduced_length_mm": 3000,
            "minimum_flange_area_mm2": 10_000,
            "critical_flange_area_mm2": 15_000,
            "minimum_depth_mm": 300,
            "critical_depth_mm": 400,
            "critical_section_values_verified": True,
        }
    )
    values = result["values"]
    expect_close(values["alpha_st"], 0.76)
    expect_close(values["adjusted_reference_buckling_moment_knm"], 76)
    expect_close(values["member_capacity_knm"], 71.58374376007083)
    return {
        "alpha_st": values["alpha_st"],
        "adjusted_reference_buckling_moment_knm": (
            values["adjusted_reference_buckling_moment_knm"]
        ),
        "member_capacity_knm": values["member_capacity_knm"],
    }


def clause_5_6_1_1_b_iii_varying_section_buckling():
    result = run_advanced_members(
        {
            "operation": "buckling_analysis_bending",
            "analysis_scope": "varying_section",
            "section_capacity_knm": 120,
            "elastic_buckling_moment_knm": 100,
            "moment_factor": 1.3,
            "end_configuration": "both_restrained",
            "restraint_and_load_model_verified": True,
            "critical_section_capacity_verified": True,
            "varying_section_buckling_model_verified": True,
            "buckling_analysis_reference": "BENCHMARK-VARYING-BUCKLING-01",
            "action_knm": 60,
        }
    )
    values = result["values"]
    reference_moment = 100 / 1.3
    ratio = 120 / reference_moment
    expected_capacity = 1.3 * (1.8 / ((ratio**2 + 3) ** 0.5 + ratio)) * 120
    expect_close(values["reference_analysis_moment_knm"], reference_moment)
    expect_close(values["member_capacity_knm"], expected_capacity)
    if result["clauses"] != ["5.6.1.1(b)(iii)", "5.6.4"]:
        raise AssertionError(
            "Varying-section buckling route did not identify Clause 5.6.1.1(b)(iii)"
        )
    return {
        "reference_analysis_moment_knm": values["reference_analysis_moment_knm"],
        "member_capacity_knm": values["member_capacity_knm"],
        "critical_section_and_varying_model_verified": all(
            check["satisfied"] for check in result["checks"][:2]
        ),
    }


def clause_5_6_1_2_b_unequal_flange_buckling():
    result = run_advanced_members(
        {
            "operation": "buckling_analysis_bending",
            "analysis_scope": "unequal_flange_i",
            "section_capacity_knm": 100,
            "elastic_buckling_moment_knm": 125,
            "moment_factor": 1.25,
            "end_configuration": "both_restrained",
            "restraint_and_load_model_verified": True,
            "unequal_flange_i_applicability_verified": True,
            "constant_cross_section_verified": True,
            "unequal_flange_buckling_model_verified": True,
            "buckling_analysis_reference": "BENCHMARK-UNEQUAL-FLANGE-01",
            "action_knm": 60,
        }
    )
    values = result["values"]
    expect_close(values["reference_analysis_moment_knm"], 100)
    expect_close(values["reduction"], 0.6)
    expect_close(values["member_capacity_knm"], 75)
    if result["clauses"] != ["5.6.1.2(b)", "5.6.1.1(a)", "5.6.4"]:
        raise AssertionError("Unequal-flange buckling route reported incorrect clauses")
    return {
        "reference_analysis_moment_knm": values["reference_analysis_moment_knm"],
        "reduction": values["reduction"],
        "member_capacity_knm": values["member_capacity_knm"],
    }


def clause_5_6_1_4_hollow_section_bending():
    result = run_advanced_members(
        {
            "operation": "hollow_section_bending_capacity",
            "section_type": "rhs",
            "section_capacity_knm": 100,
            "iy_mm4": 50_000_000,
            "torsion_constant_mm4": 200_000,
            "effective_length_mm": 15_000,
            "moment_factor": 1,
            "action_knm": 45,
            "hollow_section_applicability_verified": True,
            "section_properties_verified": True,
            "section_capacity_verified": True,
            "constant_cross_section_verified": True,
            "effective_length_verified": True,
            "moment_factor_verified": True,
            "segment_without_full_lateral_restraint_verified": True,
            "both_ends_restrained_verified": True,
        }
    )
    values = result["values"]
    expect_close(values["reference_buckling_moment_knm"], 83.77580409572782)
    expect_close(values["slenderness_reduction_alpha_s"], 0.5459194274720188)
    expect_close(values["nominal_member_moment_capacity_mb_knm"], 54.591942747201884)
    expect_close(result["checks"][0]["design_capacity"], 49.1327484724817)
    if not result["checks"][0]["satisfied"] or values["warping_constant_used_mm6"] != 0:
        raise AssertionError("Clause 5.6.1.4 hollow-section capacity check failed")
    return {
        "reference_buckling_moment_knm": values["reference_buckling_moment_knm"],
        "nominal_member_moment_capacity_knm": values["nominal_member_moment_capacity_mb_knm"],
        "design_capacity_knm": result["checks"][0]["design_capacity"],
        "capacity_check_satisfied": result["checks"][0]["satisfied"],
    }


def clause_5_6_1_1_a_iii_moment_factor():
    result = run_advanced_members(
        {
            "operation": "moment_modification_factor",
            "maximum_design_moment_knm": 100,
            "quarter_point_moment_2_knm": 80,
            "midpoint_moment_3_knm": 100,
            "quarter_point_moment_4_knm": 80,
            "moment_diagram_verified": True,
            "both_ends_restrained_verified": True,
        }
    )
    factor = result["values"]["moment_factor"]
    expect_close(factor, 1.1258525035052873)
    return {"moment_factor": factor}


def clause_5_10_web_geometry():
    thickness = run_webs(
        {
            "operation": "web_minimum_thickness",
            "design_case": "transversely_stiffened",
            "clear_web_depth_mm": 1000,
            "web_thickness_mm": 5,
            "web_yield_mpa": 250,
            "stiffener_spacing_mm": 1000,
            "greatest_panel_depth_mm": 1000,
            "stiffener_layout_verified": True,
        }
    )
    expect_close(thickness["values"]["required_web_thickness_mm"], 5)
    if "5.9.3" not in thickness["clauses"]:
        raise AssertionError("Clause 5.9.3 is missing from the web thickness result.")
    opening = run_webs(
        {
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
    )
    expect_close(opening["values"]["opening_dimension_to_web_depth_ratio"], 0.1)
    if not opening["checked_conditions_satisfied"]:
        raise AssertionError("Clause 5.10.7 rejected an opening at the boundary.")
    opening_shear_inputs = {
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
        "rational_elastic_analysis_reference": "INDEPENDENT-OPENING-ANALYSIS-01",
        "rational_elastic_analysis_verified": True,
        "action_kn": 90,
        "moment_action_knm": 50,
        "section_moment_capacity_knm": 100,
    }
    opening_shear = run_webs(opening_shear_inputs)
    shear_values = opening_shear["values"]
    expect_close(shear_values["stress_max_average_ratio"], 2)
    expect_close(shear_values["nominal_web_shear_yield_capacity_kn"], 150)
    expect_close(shear_values["nominal_web_shear_capacity_kn"], 150 * 2 / 2.9)
    expect_close(shear_values["design_web_shear_capacity_kn"], 0.9 * 150 * 2 / 2.9)
    checks = {check["clause"]: check for check in opening_shear["checks"]}
    if not opening_shear["checked_conditions_satisfied"] or not checks["5.11.1"]["satisfied"]:
        raise AssertionError("Clause 5.11.1 opening shear hand example failed")
    if not checks["5.12.3 shear and bending interaction"]["satisfied"]:
        raise AssertionError("Clause 5.12.3 opening shear/bending hand example failed")
    above_capacity = run_webs({**opening_shear_inputs, "action_kn": 94})
    if above_capacity["checked_conditions_satisfied"]:
        raise AssertionError("Clause 5.11.1 opening shear did not reject overload")
    high_moment = run_webs({**opening_shear_inputs, "action_kn": 80, "moment_action_knm": 80})
    if high_moment["checked_conditions_satisfied"]:
        raise AssertionError("Clause 5.12.3 opening interaction did not reject high bending")
    return {
        "minimum_transverse_web_thickness_mm": thickness["values"]["required_web_thickness_mm"],
        "opening_ratio_at_limit": opening["values"]["opening_dimension_to_web_depth_ratio"],
        "opening_design_shear_capacity_kn": shear_values["design_web_shear_capacity_kn"],
        "opening_shear_check_passes": checks["5.11.1"]["satisfied"],
        "opening_shear_bending_check_passes": checks["5.12.3 shear and bending interaction"][
            "satisfied"
        ],
    }


def clause_5_11_5_2_tension_field_evidence():
    inputs = {
        "operation": "shear",
        "yield_strength_mpa": 250,
        "web_area_mm2": 1000,
        "panel_depth_mm": 1200,
        "web_thickness_mm": 10,
        "stiffener_spacing_mm": 1200,
        "tension_field": True,
        "action_kn": 0,
        "moment_action_knm": 0,
        "section_moment_capacity_knm": 100,
    }
    try:
        run_members(inputs)
    except ValueError:
        pass
    else:
        raise AssertionError("Tension-field credit did not require Clause 5.15 evidence")

    inputs.update(
        tension_field_clause_5_15_verified=True,
        tension_field_clause_5_15_reference="INDEPENDENT-STIFFENER-DESIGN-15-01",
    )
    result = run_members(inputs)
    alpha_v = (82 / 120) ** 2 * 1.75
    alpha_d = 1 + (1 - alpha_v) / (1.15 * alpha_v * sqrt(2))
    expected_capacity = 150 * min(1, alpha_v * alpha_d)
    expect_close(result["values"]["shear_capacity_kn"], expected_capacity)
    check = result["checks"]["tension_field_prerequisites"]
    if (
        check["clause"] != "5.15 tension-field stiffener/end-post prerequisite"
        or not check["satisfied"]
    ):
        raise AssertionError("Clause 5.15 tension-field evidence was not reported")
    return {
        "tension_field_shear_capacity_kn": result["values"]["shear_capacity_kn"],
        "clause_5_15_evidence_check_passes": check["satisfied"],
    }


def clause_6_5_1_5_interconnection():
    connection_capacity = 7.5 * 3.141592653589793
    result = run_advanced_members(
        {
            "operation": "built_up_compression",
            "construction": "back_to_back",
            "section_capacity_kn": 1000,
            "member_capacity_kn": 500,
            "modified_member_slenderness": 100,
            "axial_action_kn": 100,
            "integral_slenderness_perpendicular": 40,
            "integral_slenderness_parallel": 100,
            "component_slenderness": 30,
            "number_of_bays": 3,
            "similar_symmetric_components_verified": True,
            "interconnection_design": {
                "design_capacity_kn": connection_capacity,
                "capacity_verified": True,
            },
        }
    )
    check = result["checks"][-1]
    expect_close(check["design_demand_kn"], 7.5 * 3.141592653589793)
    if check["clause"] != "6.5.1.5" or not check["satisfied"]:
        raise AssertionError("Clause 6.5.1.5 interconnection equality boundary failed")
    return {"interconnection_design_demand_kn": check["design_demand_kn"]}


def clause_7_3_1_uniform_connection_capacity():
    result = run_members(
        {
            "operation": "tension_distribution",
            "configuration": "uniform",
            "connection_conditions_verified": True,
            "member_part_count": 2,
            "member_part_connections": [
                {
                    "member_part_id": "web",
                    "maximum_part_design_force_kn": 40,
                    "part_connection_design_capacity_kn": 40,
                },
                {
                    "member_part_id": "flanges",
                    "maximum_part_design_force_kn": 60,
                    "part_connection_design_capacity_kn": 60,
                },
            ],
        }
    )
    check = result["checks"]["uniform_connection_part_capacity"]
    if not check["satisfied"] or result["values"]["tension_distribution_factor"] != 1:
        raise AssertionError("Clause 7.3.1(b) exact part-capacity boundary failed")
    return {
        "part_count": len(check["parts"]),
        "tension_distribution_factor": result["values"]["tension_distribution_factor"],
    }


def clause_7_3_2_both_flange_force_transfer():
    result = run_members(
        {
            "operation": "tension_distribution",
            "configuration": "both_flanges",
            "connection_conditions_verified": True,
            "connection_length_mm": 250,
            "member_depth_mm": 200,
            "maximum_member_design_force_kn": 100,
            "top_flange_connection_design_capacity_kn": 50,
            "bottom_flange_connection_design_capacity_kn": 50,
        }
    )
    check = result["checks"]["both_flange_force_transfer"]
    expect_close(check["minimum_design_capacity_each_flange_kn"], 50)
    if not check["satisfied"] or result["values"]["tension_distribution_factor"] != 0.85:
        raise AssertionError("Clause 7.3.2(b)(ii) half-force boundary failed")
    return {
        "minimum_design_capacity_each_flange_kn": check["minimum_design_capacity_each_flange_kn"],
        "tension_distribution_factor": result["values"]["tension_distribution_factor"],
    }


def clause_7_3_2_table_factor_lookup():
    factors = []
    cases = [
        ("a", True, 0.75),
        ("a", False, 0.85),
        ("b", True, 0.75),
        ("b", False, 0.85),
        ("c", None, 0.85),
        ("d", None, 0.90),
        ("e", None, 1.0),
        ("f", None, 1.0),
        ("g", None, 1.0),
    ]
    for case, short_leg, expected in cases:
        inputs = {
            "operation": "tension_distribution",
            "configuration": f"table_7_3_2_{case}",
            "connection_conditions_verified": True,
        }
        if short_leg is not None:
            inputs["unequal_angle_connected_by_short_leg"] = short_leg
        result = run_members(inputs)
        check = result["checks"]["table_7_3_2_correction_factor"]
        expect_close(result["values"]["tension_distribution_factor"], expected)
        if check["case"] != f"({case})" or not check["satisfied"]:
            raise AssertionError(f"Table 7.3.2 case ({case}) selection failed")
        factors.append(result["values"]["tension_distribution_factor"])
    return {"table_7_3_2_case_factors": factors}


def clause_7_5_pin_member_design():
    result = run_advanced_members(
        {
            "operation": "pin_tension_member",
            "design_tension_kn": 306,
            "yield_strength_mpa": 300,
            "ultimate_strength_mpa": 400,
            "gross_area_mm2": 2000,
            "member_net_area_mm2": 1500,
            "tension_distribution_factor": 0.85,
            "member_net_area_assessed_verified": True,
            "tension_distribution_factor_assessed_verified": True,
            "thickness_mm": 10,
            "hole_to_edge_distance_mm": 40,
            "internal_nut_clamped_ply": False,
            "net_area_beyond_hole_planes_mm2": [1200, 1190],
            "net_area_perpendicular_mm2": 1600,
            "all_beyond_hole_planes_assessed_verified": True,
            "pin_plates_distribute_load_without_eccentricity_verified": True,
        }
    )
    expected_net_area = 306000 / (0.9 * 0.85 * 0.85 * 400)
    expect_close(result["values"]["required_member_net_area_mm2"], expected_net_area)
    expect_close(result["values"]["gross_yield_nominal_capacity_kn"], 600)
    expect_close(result["values"]["net_fracture_nominal_capacity_kn"], 433.5)
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 7.1/7.2/7.5 pin-member benchmark failed")
    return {
        "required_net_area_mm2": result["values"]["required_member_net_area_mm2"],
        "nominal_section_capacity_kn": result["values"]["nominal_section_tension_capacity_kn"],
    }


def clause_7_4_2_tension_interconnection():
    result = run_advanced_members(
        {
            "operation": "tension_built_up_interconnection",
            "connection_arrangement": "separated",
            "parallel_connection_planes": 2,
            "connection_plane_count_verified": True,
            "all_interconnections_assessed_verified": True,
            "interconnections": [
                {
                    "local_design_transverse_shear_kn": 40,
                    "transverse_shear_verified": True,
                    "component_length_between_connections_mm": 600,
                    "minimum_radius_of_gyration_mm": 20,
                    "geometry_verified": True,
                    "design_capacity_by_plane_kn": [150, 150],
                    "capacity_verified": True,
                }
            ],
        }
    )
    values = result["values"]["interconnections"][0]
    expect_close(values["component_slenderness"], 30)
    expect_close(values["total_design_longitudinal_shear_kn"], 300)
    expect_close(values["local_design_transverse_shear_kn"], 40)
    expect_close(values["design_shear_per_plane_kn"], 150)
    if result["clauses"] != ["7.4.2", "7.4.3(a)(ii)", "6.5.1.5"]:
        raise AssertionError("Tension-member interconnection clause route was misreported")
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Tension-member interconnection capacity boundary failed")
    return {
        "component_slenderness": values["component_slenderness"],
        "local_design_transverse_shear_kn": values["local_design_transverse_shear_kn"],
        "design_shear_per_plane_kn": values["design_shear_per_plane_kn"],
    }


def clause_7_4_component_slenderness():
    clauses = {
        "separated_back_to_back": "7.4.3(a)(i)",
        "laced": "7.4.4(b)",
        "battened": "7.4.5(a)",
    }
    maximum = []
    for arrangement, clause in clauses.items():
        result = run_advanced_members(
            {
                "operation": "tension_component_slenderness",
                "arrangement": arrangement,
                "intervals_and_radii_verified": True,
                "component_intervals": [
                    {"unrestrained_length_mm": 3000, "minimum_radius_of_gyration_mm": 10}
                ],
            }
        )
        value = result["values"]["maximum_component_slenderness"]
        expect_close(value, 300)
        if result["clauses"] != [clause] or not result["checked_conditions_satisfied"]:
            raise AssertionError(f"{clause} rejected its slenderness limit")
        maximum.append(value)
    return {"component_slenderness_at_limit": maximum}


def clause_7_4_5_tension_batten_geometry():
    result = run_advanced_members(
        {
            "operation": "batten",
            "type": "intermediate",
            "member_mode": "tension",
            "centroid_distance_mm": 200,
            "narrower_component_width_mm": 60,
            "radius_mm": 2,
            "width_mm": 120,
            "thickness_mm": 3.4,
            "inner_connection_distance_mm": 200,
            "edge_stiffened": False,
            "edge_stiffener_slenderness": 0,
            "transverse_shear_kn": 10,
            "longitudinal_spacing_mm": 1000,
            "connection_centroid_distance_mm": 200,
            "parallel_planes": 2,
            "effective_end_width_mm": 200,
            "connection_type": "bolted",
            "bolts_per_component_connection": 2,
        }
    )
    checks = {check["clause"]: check for check in result["checks"]}
    expect_close(result["values"]["minimum_thickness_mm"], 3.4)
    if not all(checks[clause]["satisfied"] for clause in ("7.4.5(b)", "7.4.5(c)", "7.4.5(d)")):
        raise AssertionError("Clause 7.4.5(b)-(d) inclusive geometry boundaries failed")
    if "6.4.3.7" in result["clauses"]:
        raise AssertionError("Clause 6.4.3.7 was applied to a bolted tension batten")
    return {
        "minimum_thickness_mm": result["values"]["minimum_thickness_mm"],
        "intermediate_batten_minimum_width_mm": result["values"]["minimum_width_mm"],
        "bolt_count_per_component_connection": checks["7.4.5(b)"]["bolts_per_component_connection"],
    }


def clause_7_4_4_tension_lacing_tie_thickness():
    inputs = {
        "operation": "lacing",
        "mode": "double_connected",
        "member_mode": "tension",
        "angle_degrees": 45,
        "inner_connection_distance_mm": 1000,
        "radius_mm": 5,
        "tie_type": "intermediate",
        "component_connection_centroid_distance_mm": 200,
        "tie_width_mm": 150,
        "tie_thickness_mm": 3.4,
        "tie_inner_connection_distance_mm": 200,
        "tie_edge_stiffened": True,
        "tie_edge_stiffener_slenderness": 100,
    }
    at_limit = run_advanced_members(inputs)
    checks = {check.get("clause"): check for check in at_limit["checks"]}
    expect_close(at_limit["values"]["required_tie_thickness_mm"], 3.4)
    if not checks["7.4.4"]["satisfied"] or not at_limit["checked_conditions_satisfied"]:
        raise AssertionError("Clause 7.4.4 tension tie-plate thickness boundary failed")
    inputs["tie_thickness_mm"] = 3.39
    below_limit = run_advanced_members(inputs)
    below_checks = {check.get("clause"): check for check in below_limit["checks"]}
    if below_checks["7.4.4"]["satisfied"] or below_limit["checked_conditions_satisfied"]:
        raise AssertionError("An edge-stiffened tension tie plate passed below 0.017d")
    return {
        "minimum_tie_thickness_mm": at_limit["values"]["required_tie_thickness_mm"],
        "edge_stiffened_plate_below_minimum_rejected": True,
    }


def clause_7_4_2_connection_plane_distribution():
    result = run_advanced_members(
        {
            "operation": "tension_connection_plane_distribution",
            "connection_type": "batten",
            "parallel_connection_planes": 3,
            "total_design_force_kn": 120,
            "total_design_moment_knm": -6,
        }
    )
    expect_close(result["values"]["design_force_per_plane_kn"], 40)
    expect_close(result["values"]["design_moment_per_plane_knm"], -2)
    if result["clauses"] != ["7.4.2"] or not result["checked_conditions_satisfied"]:
        raise AssertionError("Clause 7.4.2 equal batten force/moment distribution failed")
    return {
        "design_force_per_connection_plane_kn": result["values"]["design_force_per_plane_kn"],
        "design_moment_per_connection_plane_knm": result["values"]["design_moment_per_plane_knm"],
    }


def clause_6_4_built_up_compression_member_actions():
    common = {
        "section_capacity_kn": 1000,
        "member_capacity_kn": 500,
        "modified_member_slenderness": 100,
        "axial_action_kn": 100,
        "parallel_connection_planes": 2,
        "connection_plane_count_verified": True,
        "equal_connection_plane_participation_verified": True,
        "member_action_envelope_verified": True,
        "all_connection_bays_assessed_verified": True,
        "action_analysis_reference": "independent built-up compression member example",
    }
    lacing = run_advanced_members(
        {
            "operation": "compression_built_up_member_actions",
            "connection_type": "lacing",
            **common,
            "lacing_arrangement": "double",
            "lacing_force_path_verified": True,
            "bays": [
                {
                    "start_station_mm": 0,
                    "end_station_mm": 1000,
                    "transverse_connection_spacing_mm": 1000,
                    "bay_geometry_verified": True,
                }
            ],
        }
    )
    lacing_action = lacing["values"]["action_intervals"][0]
    expected_shear = pi
    expected_bar_force_per_plane = expected_shear / (2 * sin(pi / 4))
    expect_close(lacing["values"]["transverse_design_shear_kn"], expected_shear)
    expect_close(lacing_action["lacing_angle_degrees"], 45)
    expect_close(
        lacing_action["design_lacing_bar_force_per_plane_kn"], expected_bar_force_per_plane
    )
    expect_close(
        expected_bar_force_per_plane * sin(pi / 4) * 2,
        expected_shear,
    )
    if lacing["clauses"] != ["6.4.1", "6.4.2.3"] or not lacing["checked_conditions_satisfied"]:
        raise AssertionError("Clause 6.4.1 compression lacing action route failed")

    batten = run_advanced_members(
        {
            "operation": "compression_built_up_member_actions",
            "connection_type": "batten",
            **common,
            "bays": [
                {
                    "start_station_mm": 0,
                    "end_station_mm": 1200,
                    "connection_group_centroid_spacing_mm": 300,
                    "bay_geometry_verified": True,
                }
            ],
        }
    )
    batten_action = batten["values"]["action_intervals"][0]
    expect_close(batten_action["design_batten_longitudinal_shear_per_plane_kn"], 2 * pi)
    expect_close(batten_action["design_batten_moment_per_plane_knm"], 0.3 * pi)
    if batten["clauses"] != ["6.4.1", "6.4.3.7"] or not batten["checked_conditions_satisfied"]:
        raise AssertionError("Clause 6.4.3.7 compression batten action route failed")
    return {
        "clause_6_4_1_design_transverse_shear_kn": lacing["values"]["transverse_design_shear_kn"],
        "clause_6_4_2_3_lacing_force_per_plane_kn": lacing_action[
            "design_lacing_bar_force_per_plane_kn"
        ],
        "clause_6_4_3_7_batten_shear_per_plane_kn": batten_action[
            "design_batten_longitudinal_shear_per_plane_kn"
        ],
        "clause_6_4_3_7_batten_moment_per_plane_knm": batten_action[
            "design_batten_moment_per_plane_knm"
        ],
    }


def clause_6_5_compression_built_up_connection_layout():
    common = {
        "eligible_component_forms_verified": True,
        "similar_sections_verified": True,
        "symmetrical_arrangement_verified": True,
        "rectangular_axes_aligned_verified": True,
        "member_length_mm": 3600,
        "bay_lengths_mm": [1200, 1200, 1200],
        "all_connection_bays_assessed_verified": True,
        "approximately_equal_bays_verified": True,
        "all_end_connection_lines_assessed_verified": True,
        "layout_evidence_reference": "independent compression layout example",
    }
    separated = run_advanced_members(
        {
            "operation": "compression_built_up_connection_layout",
            "connection_arrangement": "separated",
            "separated_within_end_gusset_spacing_verified": True,
            "components_interconnected_by_fasteners_verified": True,
            "end_connection_method": "fasteners",
            "fasteners_per_end_connection_line": 2,
            **common,
        }
    )
    if separated["clauses"] != ["6.5.1.1", "6.5.1.2", "6.5.1.4"]:
        raise AssertionError("Separated compression member clauses were not traced correctly")
    if separated["values"]["maximum_to_minimum_bay_length_ratio"] != 1:
        raise AssertionError("Three equal compression-member bays returned a non-unity ratio")
    if not separated["checked_conditions_satisfied"]:
        raise AssertionError("Clause 6.5.1.4 fastener and bay-layout conditions failed")

    in_contact = run_advanced_members(
        {
            "operation": "compression_built_up_connection_layout",
            "connection_arrangement": "in_contact",
            "components_in_contact_or_continuously_packed_verified": True,
            "end_connection_method": "welds",
            "equivalent_end_welds_verified": True,
            **common,
        }
    )
    if in_contact["clauses"] != ["6.5.2.1", "6.5.2.2", "6.5.2.4"]:
        raise AssertionError("In-contact compression member clauses were not traced correctly")
    if not in_contact["checked_conditions_satisfied"]:
        raise AssertionError("Clause 6.5.2.4 equivalent end-weld route failed")
    return {
        "separated_bay_count": separated["values"]["bay_count"],
        "separated_minimum_fasteners_per_line": separated["checks"][-1][
            "minimum_fasteners_per_end_connection_line"
        ],
        "in_contact_equivalent_weld_route_satisfied": in_contact["checks"][-1]["satisfied"],
    }


def clause_7_4_2_member_actions_from_member_analysis():
    batten = run_advanced_members(
        {
            "operation": "tension_built_up_member_actions",
            "connection_type": "batten",
            "bending_axis": "major_x",
            "parallel_connection_planes": 2,
            "connection_plane_count_verified": True,
            "member_action_analysis_verified": True,
            "all_connection_bays_assessed_verified": True,
            "member_action_analysis_reference": "independent two-component beam example",
            "batten_connection_centroid_distance_mm": 300,
            "bays": [
                {
                    "start_station_mm": 0,
                    "end_station_mm": 1200,
                    "start_design_moment_knm": 2,
                    "end_design_moment_knm": 14,
                    "linear_moment_distribution_verified": True,
                }
            ],
        }
    )
    batten_action = batten["values"]["action_intervals"][0]
    expect_close(batten_action["local_design_transverse_shear_kn"], 10)
    expect_close(batten_action["design_transverse_shear_per_plane_kn"], 5)
    expect_close(batten_action["design_batten_longitudinal_shear_per_plane_kn"], 20)
    expect_close(batten_action["design_batten_moment_per_plane_knm"], 3)
    if batten["clauses"] != ["7.4.2"] or not batten["checked_conditions_satisfied"]:
        raise AssertionError("Batten actions from the verified moment gradient failed")

    lacing = run_advanced_members(
        {
            "operation": "tension_built_up_member_actions",
            "connection_type": "lacing",
            "bending_axis": "minor_y",
            "parallel_connection_planes": 2,
            "connection_plane_count_verified": True,
            "member_action_analysis_verified": True,
            "all_connection_bays_assessed_verified": True,
            "member_action_analysis_reference": "independent two-plane lacing example",
            "lacing_arrangement": "double",
            "lacing_connection_spacing_mm": 1200,
            "bays": [
                {
                    "start_station_mm": 0,
                    "end_station_mm": 1200,
                    "start_design_moment_knm": 0,
                    "end_design_moment_knm": 15,
                    "linear_moment_distribution_verified": True,
                }
            ],
        }
    )
    lacing_action = lacing["values"]["action_intervals"][0]
    expect_close(lacing_action["local_design_transverse_shear_kn"], 12.5)
    expect_close(lacing_action["lacing_angle_degrees"], 45)
    expect_close(lacing_action["design_lacing_bar_force_per_plane_kn"], 12.5 / sqrt(2))
    expect_close(
        lacing_action["design_lacing_bar_force_per_plane_kn"]
        * sin(pi / 4)
        * lacing["values"]["parallel_connection_planes"],
        lacing_action["local_design_transverse_shear_kn"],
    )
    if lacing["clauses"] != ["7.4.2", "7.4.4", "6.4.2.3"]:
        raise AssertionError("Lacing action clause route was mislabeled")
    if not lacing["checked_conditions_satisfied"]:
        raise AssertionError("Lacing actions from the verified moment gradient failed")
    return {
        "batten_shear_per_plane_kn": batten_action["design_batten_longitudinal_shear_per_plane_kn"],
        "batten_moment_per_plane_knm": batten_action["design_batten_moment_per_plane_knm"],
        "lacing_bar_force_per_plane_kn": lacing_action["design_lacing_bar_force_per_plane_kn"],
    }


def clause_7_4_3_back_to_back_connection_layout():
    result = run_advanced_members(
        {
            "operation": "tension_built_up_connection_layout",
            "connection_arrangement": "separated",
            "two_eligible_components_verified": True,
            "discontinuous_back_to_back_connection_verified": True,
            "separated_within_end_gusset_spacing_verified": True,
            "member_length_mm": 3000,
            "bay_lengths_mm": [1000, 1000, 1000],
            "approximately_equal_bays_verified": True,
            "end_connection_method": "fasteners",
            "fasteners_per_connection_line_at_each_end": 2,
        }
    )
    if result["clauses"] != ["7.4.3(a)(ii)", "6.5.1.4"]:
        raise AssertionError("Separated back-to-back connection route was mislabeled")
    if not result["checked_conditions_satisfied"]:
        raise AssertionError("Three-bay, two-fastener end-connection layout failed")
    return {
        "bay_count": result["values"]["bay_count"],
        "fasteners_per_connection_line_at_each_end": result["values"]["end_connection"][
            "fasteners_per_connection_line_at_each_end"
        ],
    }


def clause_9_4_4_pin_ply_bearing():
    result = run_connections(
        {
            "check_type": "pin",
            "yield_strength_mpa": 300,
            "diameter_mm": 30,
            "shear_planes": 2,
            "ply_thickness_mm": 22,
            "connected_plies": [
                {
                    "ply_id": "centre",
                    "thickness_mm": 10,
                    "ultimate_strength_mpa": 440,
                    "bearing_action_kn": 118.8,
                    "force_towards_ply_edge": True,
                    "effective_edge_distance_mm": 30,
                },
                {
                    "ply_id": "outer",
                    "thickness_mm": 12,
                    "ultimate_strength_mpa": 400,
                    "bearing_action_kn": 20,
                    "force_towards_ply_edge": False,
                },
            ],
            "connected_plies_complete_and_force_distribution_verified": True,
            "rotates": True,
            "shear_action_kn": 100,
            "bearing_action_kn": 40,
            "moment_action_knm": 1,
        }
    )
    checks = result["checks"]["ply_bearing"]["plies"]
    expected_centre = 0.9 * min(3.2 * 30 * 10 * 440 / 1000, 30 * 10 * 440 / 1000)
    expected_outer = 0.9 * (3.2 * 30 * 12 * 400 / 1000)
    if not isclose(checks[0]["design_capacity_kn"], expected_centre, rel_tol=0, abs_tol=1e-9):
        raise AssertionError("Clause 9.4.4 edge-limited ply capacity differs from hand arithmetic")
    if not isclose(checks[1]["design_capacity_kn"], expected_outer, rel_tol=0, abs_tol=1e-9):
        raise AssertionError(
            "Clause 9.4.4 material-limited ply capacity differs from hand arithmetic"
        )
    if checks[0]["utilisation"] != 1 or not result["checks"]["ply_bearing"]["satisfied"]:
        raise AssertionError("Clause 9.4.4 exact design-capacity boundary failed")
    return {
        "ply_ids": [check["ply_id"] for check in checks],
        "design_capacities_kn": [check["design_capacity_kn"] for check in checks],
        "edge_limited_nominal_capacity_kn": checks[0]["edge_limit_nominal_capacity_kn"],
    }


def clause_9_8_packing():
    result = run_connections(
        {
            "check_type": "packing_construction",
            "packing_thickness_mm": 5,
            "too_thin_for_adequate_welds": False,
            "too_thin_to_prevent_buckling": False,
            "required_edge_weld_sizes_mm": [4, 5],
            "provided_edge_weld_sizes_mm": [9, 10],
            "trimmed_flush_with_member_edges": True,
            "extends_beyond_member_edges": False,
            "welded_to_fitted_piece": False,
        }
    )
    if not all(check["satisfied"] for check in result["checks"].values()):
        raise AssertionError("Clause 9.8 thin packing boundary was not satisfied")
    return {"required_edge_weld_sizes_mm": result["checks"]["edge_weld_sizes"]["required_mm"]}


def clause_9_1_9e_block_shear_path_set():
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
            ],
            "rupture_paths_complete_and_net_lengths_verified": True,
            "action_kn": 250,
        }
    )
    summary = result["checks"]["block_shear_path_set"]
    if summary["controlling_path_id"] != "path-b":
        raise AssertionError("The lowest block-shear path capacity was not selected")
    if summary["design_capacity_kn"] != 342 or not summary["satisfied"]:
        raise AssertionError("Clause 9.1.9(e) block-shear path check failed")
    return {
        "controlling_path_id": summary["controlling_path_id"],
        "design_capacity_kn": summary["design_capacity_kn"],
        "path_count": len(summary["paths"]),
    }


def clause_9_1_10_coordinate_hole_deduction():
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
    )["intermediate"]
    expected_deduction_width_mm = max(2 * 22, 3 * 22 - 2 * (40**2 / (4 * 50)))
    expected_net_area_mm2 = 200 * 10 - expected_deduction_width_mm * 10
    if result["governing_path_type"] != "zigzag":
        raise AssertionError("Clause 9.1.10 did not select the governing zig-zag path")
    if result["zigzag_path"]["hole_ids"] != ["A", "B", "C"]:
        raise AssertionError("Clause 9.1.10 did not preserve the progressive hole path")
    if result["net_area_mm2"] != expected_net_area_mm2:
        raise AssertionError("Clause 9.1.10 net area differs from independent hand arithmetic")
    return {
        "governing_path_type": result["governing_path_type"],
        "net_area_mm2": result["net_area_mm2"],
    }


def figure_9_1_10_3b_angle_back_mark_gauge():
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
                }
            ],
        }
    )["intermediate"]
    pair = result["candidate_paths"][0]["stagger_pairs"][0]
    expected_gauge_mm = 20 + 30 - 10
    expected_correction_mm = 40**2 / (4 * expected_gauge_mm)
    expected_deduction_width_mm = max(25, 2 * 20 - expected_correction_mm)
    expected_net_area_mm2 = 4000 - 10 * expected_deduction_width_mm
    if pair["gauge_mm"] != expected_gauge_mm:
        raise AssertionError(
            "Figure 9.1.10.3(B) opposite-leg gauge differs from its back-mark formula"
        )
    if result["governing_deduction_width_mm"] != expected_deduction_width_mm:
        raise AssertionError("Clause 9.1.10.3(B) angle deduction differs from hand arithmetic")
    if result["net_area_mm2"] != expected_net_area_mm2:
        raise AssertionError("Clause 9.1.10 angle net area differs from hand arithmetic")
    return {
        "opposite_leg_gauge_mm": pair["gauge_mm"],
        "net_area_mm2": result["net_area_mm2"],
    }


def clause_9_1_10_two_leg_angle_layout():
    holes = [
        ("A", "leg_1", 0, 70, 20),
        ("B", "leg_1", 30, 40, 20),
        ("C", "leg_2", 60, 30, 18),
        ("D", "leg_2", 90, 60, 18),
    ]
    result = run_connections(
        {
            "check_type": "angle_hole_deduction_layout",
            "gross_area_mm2": 1900,
            "thickness_mm": 10,
            "leg_1_width_mm": 100,
            "leg_2_width_mm": 100,
            "angle_geometry_and_back_marks_verified": True,
            "complete_angle_hole_layout_and_action_axis_verified": True,
            "holes": [
                {
                    "hole_id": hole_id,
                    "angle_leg_id": leg,
                    "longitudinal_mm": longitudinal,
                    "back_mark_mm": back_mark,
                    "gross_hole_width_mm": width,
                }
                for hole_id, leg, longitudinal, back_mark, width in holes
            ],
        }
    )["intermediate"]
    expected_corrections_mm = [30**2 / (4 * 30), 30**2 / (4 * 60), 30**2 / (4 * 30)]
    expected_deduction_width_mm = 20 + 20 + 18 + 18 - sum(expected_corrections_mm)
    expected_net_area_mm2 = 1900 - 10 * expected_deduction_width_mm
    if result["zigzag_path"]["hole_ids"] != ["A", "B", "C", "D"]:
        raise AssertionError("Clause 9.1.10 did not select the full progressive angle path")
    if result["zigzag_path"]["net_deduction_width_mm"] != expected_deduction_width_mm:
        raise AssertionError("Clause 9.1.10 angle stagger deductions differ from hand arithmetic")
    if result["net_area_mm2"] != expected_net_area_mm2:
        raise AssertionError("Clause 9.1.10 angle net area differs from hand arithmetic")
    return {
        "hole_ids": result["zigzag_path"]["hole_ids"],
        "deduction_width_mm": result["governing_deduction_width_mm"],
        "net_area_mm2": result["net_area_mm2"],
    }


def clause_12_6_3_single_test_history():
    result = run_durability(
        {
            "check_type": "fire_single_test_history",
            "limiting_temperature_c": 500,
            "required_frl_min": 8,
            "protection_thickness_mm": 25,
            "prototype_protection_thickness_mm": 20,
            "surface_mass_ratio_m2_per_tonne": 10,
            "prototype_surface_mass_ratio_m2_per_tonne": 12,
            "same_protection_system": True,
            "same_exposure_condition": True,
            "prototype_was_unloaded": True,
            "stickability_demonstrated": True,
            "temperature_history": [
                {"time_min": 0, "steel_temperature_c": 20},
                {"time_min": 5, "steel_temperature_c": 300},
                {"time_min": 10, "steel_temperature_c": 600},
            ],
        }
    )
    values = result["results"]
    expect_close(values["attained_time_min"], 8.333333333333334)
    if not values["check_satisfied"]:
        raise AssertionError("Clause 12.6.3 qualifying single-test history failed")
    return {"limiting_temperature_time_min": values["attained_time_min"]}


def clause_12_10_2_web_protection():
    values = run_durability(
        {
            "check_type": "web_penetration_protection",
            "required_thickness_above_mm": 20,
            "required_thickness_below_mm": 25,
            "required_thickness_whole_section_mm": 30,
            "provided_thickness_mm": 30,
            "beam_depth_mm": 450,
            "protected_depth_mm": 450,
            "left_extension_mm": 450,
            "right_extension_mm": 450,
        }
    )["results"]
    if values["required_thickness_mm"] != 30 or not values["check_satisfied"]:
        raise AssertionError("Clause 12.10.2 thickness/extent boundary failed")
    return {
        "required_thickness_mm": values["required_thickness_mm"],
        "minimum_extension_each_side_mm": values["minimum_extension_each_side_mm"],
    }


def clause_13_3_5_brace_connection():
    values = run_durability(
        {
            "check_type": "concentric_brace_yielding_connection",
            "limited_ductility_concentric_braced_frame_verified": True,
            "all_applicable_brace_connections_listed_verified": True,
            "brace_connections": [
                {
                    "connection_id": "BR-1",
                    "member_design_capacity_kn": 200,
                    "connection_design_capacity_kn": 200,
                }
            ],
        }
    )["results"]
    if not values["check_satisfied"]:
        raise AssertionError("Clause 13.3.5(b) full member-capacity limit failed")
    return {"required_connection_capacity_kn": 200, "check_satisfied": True}


def clause_13_3_6_3_frame_stiffeners():
    values = run_durability(
        {
            "check_type": "intermediate_moment_frame_stiffeners",
            "intermediate_moment_frame_applicability_verified": True,
            "all_applicable_web_stiffeners_listed_verified": True,
            "web_stiffeners": [
                {
                    "stiffener_id": "ST-1",
                    "extends_full_depth_between_flanges": True,
                    "butt_welded_to_both_flanges": True,
                }
            ],
        }
    )["results"]
    if not values["check_satisfied"]:
        raise AssertionError("Clause 13.3.6.3(b) stiffener boundary failed")
    return {"stiffeners_satisfied": values["stiffeners_satisfied"]}


def clause_13_3_6_4_plastic_fabrication():
    values = run_durability(
        {
            "check_type": "seismic_plastic_region_fabrication",
            "moderately_ductile_plastic_regions_verified": True,
            "all_plastic_region_edges_and_holes_listed_verified": True,
            "sheared_edges": [
                {
                    "edge_id": "E-1",
                    "sheared_oversize_and_machined_to_remove_all_sheared_surface": True,
                }
            ],
            "gas_cut_edges": [{"edge_id": "E-2", "surface_roughness_um": 12}],
            "fastener_holes": [
                {"hole_id": "H-1", "hole_making_method": "drilled"},
                {
                    "hole_id": "H-2",
                    "hole_making_method": "undersize_punched_then_reamed_or_drilled",
                },
            ],
        }
    )["results"]
    if not values["check_satisfied"]:
        raise AssertionError("Clause 13.3.6.4 fabrication limits failed")
    return {
        "gas_cut_maximum_roughness_um": values["gas_cut_edge_checks"][0][
            "maximum_surface_roughness_um"
        ],
        "check_satisfied": True,
    }


def clause_13_3_6_2_tension_brace():
    values = run_durability(
        {
            "check_type": "concentric_tension_brace",
            "bearing_wall_or_building_frame_system_verified": True,
            "design_tension_action_kn": 85,
            "member_design_tensile_capacity_kn": 100,
            "connection_design_tensile_capacity_kn": 100,
        }
    )["results"]
    if values["member_action_limit_kn"] != 85 or not values["check_satisfied"]:
        raise AssertionError("Clause 13.3.6.2(a) exact limits were rejected")
    return {
        "member_design_force_limit_kn": values["member_action_limit_kn"],
        "connection_capacity_kn": values["connection_design_tensile_capacity_kn"],
    }


def clause_13_3_6_2_connection_detailing():
    data = {
        "check_type": "concentric_brace_connection_detailing",
        "bearing_wall_or_building_frame_system_verified": True,
        "all_concentric_braced_frame_welds_and_stiffeners_listed_verified": True,
        "web_stiffeners": [
            {
                "stiffener_id": "ST-1",
                "extends_full_depth_between_flanges": True,
                "butt_welded_to_both_flanges": True,
            }
        ],
        "weld_groups": [
            {
                "weld_group_id": "BW-T-1",
                "weld_population": "butt_in_tension",
                "weld_category": "SP",
                "visual_scanning_percent": 100,
                "visual_examination_percent": 100,
                "magnetic_particle_or_dye_penetrant_percent": 100,
                "ultrasonics_or_radiography_percent": 10,
            },
            {
                "weld_group_id": "BW-N-1",
                "weld_population": "butt_not_in_tension",
                "weld_category": "SP",
                "visual_scanning_percent": 100,
                "visual_examination_percent": 50,
                "magnetic_particle_or_dye_penetrant_percent": 10,
                "ultrasonics_or_radiography_percent": 2,
            },
            {
                "weld_group_id": "OW-1",
                "weld_population": "other_welds",
                "weld_category": "SP",
                "visual_scanning_percent": 100,
                "visual_examination_percent": 20,
                "magnetic_particle_or_dye_penetrant_percent": 5,
                "ultrasonics_or_radiography_percent": 2,
            },
        ],
    }
    values = run_durability(data)["results"]
    requirements = [
        [100, 100, 100, 10],
        [100, 50, 10, 2],
        [100, 20, 5, 2],
    ]
    observed = [
        [
            group["required_visual_scanning_percent"],
            group["required_visual_examination_percent"],
            group["required_magnetic_particle_or_dye_penetrant_percent"],
            group["required_ultrasonics_or_radiography_percent"],
        ]
        for group in values["weld_group_checks"]
    ]
    if observed != requirements or not values["check_satisfied"]:
        raise AssertionError("Clause 13.3.6.2(b)/(c) geometry or NDE table boundaries failed")
    return {"required_inspection_percentages": observed, "check_satisfied": True}


def main():
    cases = {
        "clauses_10_3_2_10_3_3_design_service_temperature": (
            clause_10_3_design_service_temperature
        ),
        "clause_10_4_3_4_subsize_charpy_energy": (clause_10_4_3_4_nonconforming_steel_impact_test),
        "clause_10_4_3_4_specified_impact_properties": (
            clause_10_4_3_4_specified_impact_properties
        ),
        "table_10_4_4_grade_selection": table_10_4_4_grade_selection,
        "clause_10_5_fracture_assessment_evidence": clause_10_5_fracture_assessment_evidence,
        "fillet_lap_1700_mm": lambda: expect_close(fillet(1700), 98.784),
        "fillet_lap_8000_mm": lambda: expect_close(fillet(8000), 61.24608),
        "fillet_lap_8001_mm": lambda: expect_close(fillet(8001), 61.24608),
        "table_11_5_1_b_coped_transverse_splice": fatigue_welded_coped_splice,
        "clause_9_6_2_single_v_incomplete_butt_weld": incomplete_butt_weld,
        "clause_9_7_4_combined_weld_types": combined_weld_types,
        "clause_4_6_3_2_idealized_member_buckling": (clause_4_6_3_2_idealized_member_buckling),
        "clause_4_6_3_3_chart_factor_buckling": clause_4_6_3_3_chart_factor_buckling,
        "clause_4_6_3_3_alignment_equation_buckling": (clause_4_6_3_3_alignment_equation_buckling),
        "clause_4_6_3_5_triangulated_member_buckling": (
            clause_4_6_3_5_triangulated_member_buckling
        ),
        "clause_4_7_2_rectangular_frame_buckling_factors": (
            clause_4_7_2_rectangular_frame_buckling_factors
        ),
        "clause_4_6_3_4_rectangular_frame_stiffness_ratio": (
            clause_4_6_3_4_rectangular_frame_stiffness_ratio
        ),
        "clause_4_5_1_global_equilibrium": clause_4_5_1_global_equilibrium,
        "clause_4_5_1_joint_equilibrium": clause_4_5_1_joint_equilibrium,
        "clause_4_5_1_member_span_equilibrium": clause_4_5_1_member_span_equilibrium,
        "clause_4_5_1_support_boundary_conditions": clause_4_5_1_support_boundary_conditions,
        "clause_4_5_2_alternative_ductility_assessment": (
            clause_4_5_2_alternative_ductility_assessment
        ),
        "clause_4_5_2_plastic_analysis_limits": clause_4_5_2_plastic_analysis_limits,
        "clause_4_5_3_plastic_connections": clause_4_5_3_plastic_connections,
        "clause_9_6_2_macro_test_throat_increase": incomplete_butt_macro_test_weld,
        "clause_9_6_2_6_butt_weld_transition": butt_weld_transition,
        "clause_9_6_2_prequalified_butt_weld_capacity": prequalified_incomplete_butt_capacity,
        "clause_9_6_2_prequalified_butt_macro_throat": prequalified_incomplete_butt_macro_throat,
        "clause_9_6_3_4_fillet_macro_test_throat": fillet_macro_test_throat,
        "clause_9_6_4_2_circular_plug_weld_area": plug_slot_circular_hole,
        "clause_9_6_4_2_round_ended_slot_weld_area": plug_slot_round_ended_slot,
        "clause_9_6_4_2_rectangular_slot_weld_area": plug_slot_rectangular_slot,
        "clause_9_6_4_externally_assessed_area": plug_slot_external_area,
        "mixed_stiffener_contact_and_outstand": mixed_stiffener,
        "zero_restrained_flanges": zero_restrained_flanges,
        "yield_above_690_mpa": over_scope_yield,
        "clause_2_2_3_unidentified_steel_limits": unidentified_steel_limits,
        "clause_2_2_4_standard_properties": clause_2_2_4_properties,
        "clause_2_2_5_through_thickness_quality": clause_2_2_5_z_quality,
        "clause_2_3_2_equivalent_high_strength_fastener": (
            clause_2_3_2_equivalent_high_strength_fastener
        ),
        "appendix_m_table_m2_z_quality": appendix_m_table_m2_z_quality,
        "clause_14_3_2_hole_sizes_and_use": clause_14_3_2_hole_sizes_and_use,
        "clause_14_fabrication_procedure_and_tolerances": (
            clause_14_fabrication_procedure_and_tolerances
        ),
        "clause_15_erection_and_tensioning": clause_15_erection_and_tensioning,
        "clause_17_test_scope_and_prototype": clause_17_test_scope_and_prototype,
        "clause_16_existing_structure_modification": clause_16_existing_structure_modification,
        "clause_8_4_6_amended_angle_interaction": clause_8_4_6_amended_angle_interaction,
        "clause_6_3_3_c_amended_lambda_20_row": clause_6_3_3_c_amended_lambda_20_row,
        "appendix_h4_amended_closed_section_torsion_constant": (
            appendix_h4_amended_closed_section_torsion_constant
        ),
        "appendix_h4_open_section_torsion_constant": appendix_h4_open_section_torsion_constant,
        "clause_5_2_5_internal_gradient_effective_modulus": clause_5_2_5_internal_gradient,
        "clause_5_2_section_moment_capacity": clause_5_2_section_moment_capacity,
        "clause_5_2_6_net_gross_section_moduli": clause_5_2_6_hole_moduli,
        "clause_5_1_bending_design_routes": clause_5_1_bending_design_routes,
        "clause_5_4_2_restraint_classification": clause_5_4_2_restraint_classification,
        "clause_5_4_3_4_lateral_rotation_restraint": (clause_5_4_3_4_lateral_rotation_restraint),
        "clause_5_3_2_4_unequal_flange_restraint_boundary": (clause_5_3_2_4_lateral_restraint),
        "clause_5_3_2_1_member_capacity_restraint_route": (clause_5_3_2_1_capacity_restraint),
        "clause_5_3_3_critical_section": clause_5_3_3_critical_section,
        "clause_5_5_3_critical_flange": clause_5_5_3_critical_flange,
        "clause_5_6_1_1_a_iii_moment_factor": clause_5_6_1_1_a_iii_moment_factor,
        "clause_5_6_1_1_b_varying_section": clause_5_6_1_1_b_varying_section,
        "clause_5_6_1_1_b_iii_varying_section_buckling": (
            clause_5_6_1_1_b_iii_varying_section_buckling
        ),
        "clause_5_6_1_2_b_unequal_flange_buckling": (clause_5_6_1_2_b_unequal_flange_buckling),
        "clause_5_6_1_4_hollow_section_bending": clause_5_6_1_4_hollow_section_bending,
        "clause_5_10_web_geometry": clause_5_10_web_geometry,
        "clause_5_11_5_2_tension_field_evidence": clause_5_11_5_2_tension_field_evidence,
        "clause_6_5_1_5_interconnection": clause_6_5_1_5_interconnection,
        "clause_7_3_1_uniform_connection_capacity": clause_7_3_1_uniform_connection_capacity,
        "clause_7_3_2_both_flange_force_transfer": clause_7_3_2_both_flange_force_transfer,
        "clause_7_3_2_table_factor_lookup": clause_7_3_2_table_factor_lookup,
        "clause_7_1_7_2_7_5_pin_member_design": clause_7_5_pin_member_design,
        "clause_7_4_2_6_5_tension_interconnection": clause_7_4_2_tension_interconnection,
        "clause_7_4_component_slenderness": clause_7_4_component_slenderness,
        "clause_7_4_4_tension_lacing_tie_thickness": clause_7_4_4_tension_lacing_tie_thickness,
        "clause_7_4_5_tension_batten_geometry": clause_7_4_5_tension_batten_geometry,
        "clause_7_4_2_connection_plane_distribution": clause_7_4_2_connection_plane_distribution,
        "clause_6_4_built_up_compression_member_actions": (
            clause_6_4_built_up_compression_member_actions
        ),
        "clause_6_5_compression_built_up_connection_layout": (
            clause_6_5_compression_built_up_connection_layout
        ),
        "clause_7_4_2_member_actions_from_member_analysis": (
            clause_7_4_2_member_actions_from_member_analysis
        ),
        "clause_7_4_3_back_to_back_connection_layout": clause_7_4_3_back_to_back_connection_layout,
        "clause_9_1_9e_block_shear_path_set": clause_9_1_9e_block_shear_path_set,
        "clause_9_4_4_pin_ply_bearing": clause_9_4_4_pin_ply_bearing,
        "clause_9_1_10_coordinate_hole_deduction": clause_9_1_10_coordinate_hole_deduction,
        "figure_9_1_10_3b_angle_back_mark_gauge": figure_9_1_10_3b_angle_back_mark_gauge,
        "clause_9_1_10_two_leg_angle_layout": clause_9_1_10_two_leg_angle_layout,
        "clause_9_8_packing": clause_9_8_packing,
        "clause_12_6_3_single_test_history": clause_12_6_3_single_test_history,
        "clause_12_10_2_web_protection": clause_12_10_2_web_protection,
        "clause_13_3_5_brace_connection": clause_13_3_5_brace_connection,
        "clause_13_3_6_2_tension_brace": clause_13_3_6_2_tension_brace,
        "clause_13_3_6_3_frame_stiffeners": clause_13_3_6_3_frame_stiffeners,
        "clause_13_3_6_4_plastic_fabrication": clause_13_3_6_4_plastic_fabrication,
        "clause_13_3_6_2_connection_detailing": clause_13_3_6_2_connection_detailing,
    }
    results = []
    for name, check in cases.items():
        try:
            observed = check()
            results.append({"case": name, "status": "passed", "observed": observed})
        except (AssertionError, ValueError) as exc:
            results.append({"case": name, "status": "failed", "error": str(exc)})
    passed = sum(item["status"] == "passed" for item in results)
    print(json.dumps({"passed": passed, "total": len(results), "results": results}, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
