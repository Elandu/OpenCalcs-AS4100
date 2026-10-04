# SPDX-License-Identifier: AGPL-3.0-only
"""Installed package discovery and real OpenCalcs HTTP integration."""

from importlib.metadata import entry_points

import pytest
from fastapi.testclient import TestClient
from opencalcs.api import create_app
from opencalcs.auth import AllowAllAuthenticator
from opencalcs.registry import CalculationRegistry

from opencalcs_as4100.plugin import CALCULATION_ID


@pytest.fixture
def axial_inputs():
    return {
        "gross_area_mm2": 1000,
        "net_area_mm2": 800,
        "yield_strength_mpa": 300,
        "ultimate_strength_mpa": 430,
        "tension_distribution_factor": 0.8,
        "compression_form_factor": 0.9,
        "tension_action_kn": 150,
        "compression_action_kn": 100,
    }


def test_installed_entry_point_and_host_provenance(axial_inputs):
    entry = next(item for item in entry_points(group="opencalcs.plugins") if item.name == "as4100")
    assert entry.load()().id == "structural.as4100"
    registry = CalculationRegistry()
    result = registry.run(CALCULATION_ID, axial_inputs)
    assert result["tension"]["design_capacity_kn"] == pytest.approx(210.528)
    assert result["compression"]["design_capacity_kn"] == pytest.approx(194.4)
    assert result["_provenance"]["engine"]["id"] == "structural.as4100"
    assert result["_provenance"]["calculation"]["id"] == CALCULATION_ID
    assert result["_provenance"]["standard"]["edition"] == "2020"


def test_host_catalog_and_http_run(axial_inputs):
    with TestClient(create_app(authenticator=AllowAllAuthenticator())) as client:
        descriptor = client.get(f"/api/v1/calculations/{CALCULATION_ID}")
        assert descriptor.status_code == 200
        assert descriptor.json()["plugin"]["id"] == "structural.as4100"
        response = client.post(
            f"/api/v1/calculations/{CALCULATION_ID}/run", json={"inputs": axial_inputs}
        )
        assert response.status_code == 200
        assert response.json()["tension"]["utilisation"] == pytest.approx(150 / 210.528)


def test_unidentified_steel_clause_2_2_3_runs_through_host():
    inputs = {
        "operation": "unidentified_steel",
        "design_yield_strength_mpa": 170,
        "design_tensile_strength_mpa": 300,
        "surface_imperfections_verified": True,
        "properties_and_weldability_verified": True,
        "full_test_to_as1391_verified": False,
    }
    with TestClient(create_app(authenticator=AllowAllAuthenticator())) as client:
        response = client.post(
            "/api/v1/calculations/structural.as4100.materials/run",
            json={"inputs": inputs},
        )
    assert response.status_code == 200
    assert response.json()["clauses"] == ["2.2.3"]
    assert [check["limit_mpa"] for check in response.json()["checks"]] == [170, 300]
    assert response.json()["checked_conditions_satisfied"]


def test_through_thickness_clause_2_2_5_runs_through_host():
    inputs = {
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
    with TestClient(create_app(authenticator=AllowAllAuthenticator())) as client:
        response = client.post(
            "/api/v1/calculations/structural.as4100.materials/run",
            json={"inputs": inputs},
        )
    assert response.status_code == 200
    assert response.json()["clauses"] == ["2.2.5"]
    assert response.json()["values"]["required_z_quality_class"] == "Z25"
    assert response.json()["checked_conditions_satisfied"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("net_area_mm2", 1001),
        ("tension_distribution_factor", 0),
        ("compression_form_factor", 1.01),
        ("yield_strength_mpa", "300"),
        ("compression_action_kn", -1),
        ("unexpected", 1),
    ],
)
def test_invalid_input_returns_http_422(axial_inputs, field, value):
    axial_inputs[field] = value
    with TestClient(create_app(authenticator=AllowAllAuthenticator())) as client:
        response = client.post(
            f"/api/v1/calculations/{CALCULATION_ID}/run", json={"inputs": axial_inputs}
        )
        assert response.status_code == 422


def test_missing_required_factor_returns_http_422(axial_inputs):
    del axial_inputs["compression_form_factor"]
    with TestClient(create_app(authenticator=AllowAllAuthenticator())) as client:
        response = client.post(
            f"/api/v1/calculations/{CALCULATION_ID}/run", json={"inputs": axial_inputs}
        )
        assert response.status_code == 422


def test_all_calculation_families_discovered_with_schemas():
    registry = CalculationRegistry()
    plugin = next(p for p in registry.plugins if p.id == "structural.as4100")
    assert len(plugin.calculations) >= 8
    for calculation in plugin.calculations:
        assert registry.describe(calculation.id)["standard"]["edition"] == "2020"
        descriptor = calculation.descriptor()
        descriptor["input_schema"].clear()
        assert calculation.input_schema


@pytest.mark.parametrize(
    "suffix",
    [
        "materials",
        "member_design",
        "advanced_members",
        "connection_design",
        "durability",
        "design_actions",
        "webs",
        "testing",
        "design_review",
    ],
)
def test_family_http_validation(suffix):
    with TestClient(create_app(authenticator=AllowAllAuthenticator())) as client:
        response = client.post(
            f"/api/v1/calculations/structural.as4100.{suffix}/run",
            json={"inputs": {"unknown": True}},
        )
        assert response.status_code == 422


@pytest.mark.parametrize(
    "suffix,inputs",
    [
        (
            "design_actions",
            {"operation": "notional_horizontal_load", "floor_vertical_design_load_kn": 1000},
        ),
        (
            "connection_design",
            {
                "check_type": "minimum_beam_shear_action",
                "actual_design_shear_kn": 10,
                "member_design_shear_capacity_kn": 200,
                "simple_construction_beam_connection_verified": True,
                "excluded_connection_arrangement_absent_verified": True,
                "reaction_shear_direction_unit_vector": [0, 1, 0],
                "reaction_shear_eccentricity_vector_mm": [40, 0, 0],
                "reaction_shear_eccentricity_assessment_verified": True,
                "connection_design_shear_capacity_kn": 30,
            },
        ),
        (
            "connection_design",
            {
                "check_type": "minimum_rigid_connection_action",
                "rigid_construction_connection_verified": True,
                "actual_design_moment_knm": 20,
                "member_design_moment_capacity_knm": 100,
                "excluded_connection_arrangement_absent_verified": True,
            },
        ),
        (
            "connection_design",
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
            },
        ),
        (
            "connection_design",
            {
                "check_type": "joint_eccentricity_action",
                "connection_detail_case": "general",
                "fatigue_loading": False,
                "fatigue_detail_eccentricity_assessment_verified": False,
                "centroidal_axes_meet_practicable_verified": False,
                "centroidal_axes_meet_at_joint_verified": False,
                "force_kn": [0, 10, 0],
                "eccentricity_vector_mm": [25, 0, 0],
                "joint_geometry_and_load_line_assessed_verified": True,
            },
        ),
        (
            "connection_design",
            {
                "check_type": "fastener_selection_suitability",
                "selected_fastener_system": "friction_type_8_8_TF",
                "serviceability_slip_to_be_avoided": True,
                "impact_or_vibration_present": True,
                "service_and_dynamic_action_assessment_verified": True,
            },
        ),
        (
            "connection_design",
            {
                "check_type": "combined_connection_action_assignment",
                "component_groups": [
                    {"group_id": "friction-bolts", "fastener_class": "non_slip"},
                    {"group_id": "snug-bolts", "fastener_class": "slip_type"},
                ],
                "load_cases": [
                    {
                        "case_id": "service-load",
                        "stage": "non_weld_action",
                        "actions": {
                            "axial_kn": 0,
                            "shear_x_kn": 0,
                            "shear_y_kn": 80,
                            "moment_x_knm": 0,
                            "moment_y_knm": 0,
                            "moment_z_knm": 16,
                        },
                        "shares": [{"group_id": "friction-bolts", "fraction": 1}],
                    }
                ],
                "installation_sequence_assessed_verified": True,
            },
        ),
        (
            "connection_design",
            {
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
                "shear_action_kn": 0,
                "tension_action_kn": 40,
                "prying_tension_kn": 15,
                "prying_force_assessment_verified": True,
            },
        ),
        (
            "connection_design",
            {
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
            },
        ),
        (
            "connection_design",
            {
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
            },
        ),
        (
            "webs",
            {
                "operation": "longitudinal_stiffener",
                "web_depth_mm": 200,
                "web_thickness_mm": 10,
                "stiffener_area_mm2": 1000,
                "stiffener_second_moment_mm4": 3200000,
                "location": "0.2_depth",
            },
        ),
        (
            "webs",
            {
                "operation": "web_minimum_thickness",
                "design_case": "transversely_stiffened",
                "clear_web_depth_mm": 1000,
                "web_thickness_mm": 5,
                "web_yield_mpa": 250,
                "stiffener_spacing_mm": 1000,
                "greatest_panel_depth_mm": 1000,
                "stiffener_layout_verified": True,
            },
        ),
        (
            "webs",
            {
                "operation": "web_opening_geometry",
                "clear_web_depth_mm": 1000,
                "opening_internal_dimension_mm": 100,
                "longitudinal_stiffeners_present": False,
                "adjacent_openings_present": False,
                "adjacent_opening_boundary_spacing_mm": 0,
                "unstiffened_openings_at_cross_section": 1,
                "multiple_openings_rational_analysis_verified": False,
                "opening_geometry_verified": True,
            },
        ),
        (
            "webs",
            {
                "operation": "load_bearing_stiffener_requirement",
                "design_compressive_bearing_force_kn": 120,
                "design_web_bearing_capacity_kn": 100,
                "end_post_required_under_5_15_2_2": False,
                "load_bearing_stiffeners_provided": True,
            },
        ),
        (
            "webs",
            {
                "operation": "web_side_reinforcement",
                "design_shear_share_kn": 40,
                "side_plate_design_shear_capacity_kn": 60,
                "fastener_design_shear_capacity_to_web_kn": 45,
                "fastener_design_shear_capacity_to_flanges_kn": 40,
                "symmetry_effects_accounted": True,
            },
        ),
        (
            "advanced_members",
            {
                "operation": "varying_compression",
                "minimum_section_capacity_kn": 1000,
                "elastic_buckling_load_kn": 1000,
                "section_constant": 0,
                "action_kn": 500,
                "flexural_mode_verified": True,
            },
        ),
        (
            "materials",
            {
                "operation": "tabulated_strength",
                "product_standard": "AS/NZS 3678",
                "form": "plate_floorplate",
                "grade": "350",
                "material_thickness_mm": 16,
            },
        ),
        (
            "member_design",
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
            },
        ),
        (
            "member_design",
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
            },
        ),
        (
            "member_design",
            {
                "operation": "chs_shear",
                "yield_strength_mpa": 250,
                "gross_area_mm2": 3000,
                "net_area_mm2": 2500,
                "oversized_fastener_holes_present": True,
                "action_kn": 202.5,
                "moment_action_knm": 0,
                "section_moment_capacity_knm": 100,
            },
        ),
        (
            "member_design",
            {
                "operation": "shear_with_flange_restraint",
                "yield_strength_mpa": 250,
                "web_area_mm2": 1000,
                "panel_depth_mm": 1000,
                "web_thickness_mm": 10,
                "action_kn": 50,
                "moment_action_knm": 0,
                "section_moment_capacity_knm": 100,
                "flange_thickness_mm": 10,
                "clear_web_depth_mm": 200,
                "flange_outstand_from_web_midplane_mm": 20,
                "number_of_webs": 1,
                "no_longitudinal_stiffeners_verified": True,
            },
        ),
        (
            "member_design",
            {
                "operation": "shear_proportioning",
                "yield_strength_mpa": 250,
                "compression_flange_gross_area_mm2": 1800,
                "compression_flange_effective_area_mm2": 1500,
                "tension_flange_gross_area_mm2": 1600,
                "tension_flange_net_area_mm2": 1000,
                "tension_flange_ultimate_strength_mpa": 400,
                "flange_centroid_spacing_mm": 250,
                "nominal_web_shear_capacity_kn": 100,
                "action_kn": 90,
                "moment_action_knm": 76.5,
            },
        ),
        (
            "advanced_members",
            {
                "operation": "full_lateral_restraint_limit",
                "section_type": "rhs_or_shs",
                "segment_length_mm": 1500,
                "yield_strength_mpa": 250,
                "beta_m_basis": "conservative_minus_one",
                "section_properties_verified": True,
                "both_ends_restrained_verified": True,
                "radius_of_gyration_y_mm": 10,
                "flange_width_mm": 100,
                "web_depth_mm": 200,
            },
        ),
        (
            "advanced_members",
            {
                "operation": "continuous_lateral_restraints",
                "both_ends_restrained_verified": True,
                "continuous_restraints_at_critical_flange_verified": True,
                "continuous_restraints_satisfy_5_4_3_1_verified": True,
            },
        ),
        (
            "advanced_members",
            {
                "operation": "intermediate_lateral_restraints",
                "both_ends_restrained_verified": True,
                "intermediate_restraints_at_critical_flange_verified": True,
                "intermediate_restraints_satisfy_5_4_3_1_verified": True,
                "subsegment_checks": [
                    {
                        "operation": "full_lateral_restraint_limit",
                        "section_type": "equal_flanged_i",
                        "segment_length_mm": 300,
                        "yield_strength_mpa": 250,
                        "beta_m_basis": "conservative_minus_one",
                        "section_properties_verified": True,
                        "both_ends_restrained_verified": True,
                        "radius_of_gyration_y_mm": 10,
                    }
                ],
            },
        ),
        (
            "advanced_members",
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
                ],
            },
        ),
        (
            "advanced_members",
            {
                "operation": "critical_flange",
                "segment_end_condition": "one_end_unrestrained",
                "dominant_load": "wind",
                "wind_case": "external_suction",
                "exterior_flange_position": "top",
            },
        ),
        (
            "advanced_members",
            {
                "operation": "moment_modification_factor",
                "maximum_design_moment_knm": 100,
                "quarter_point_moment_2_knm": 80,
                "midpoint_moment_3_knm": 100,
                "quarter_point_moment_4_knm": 80,
                "moment_diagram_verified": True,
                "both_ends_restrained_verified": True,
            },
        ),
        (
            "advanced_members",
            {
                "operation": "unequal_flange_bending",
                "section_capacity_knm": 200,
                "iy_mm4": 50_000_000,
                "torsion_constant_mm4": 200_000,
                "warping_constant_mm6": 8_000_000_000_000,
                "effective_length_mm": 15_000,
                "moment_factor": 1.2,
                "moment_factor_verified": True,
                "both_ends_restrained_verified": True,
                "action_knm": 120,
                "section_properties_verified": True,
                "constant_cross_section_verified": True,
                "beta_x_method": "compression_flange_inertia",
                "flange_centroid_spacing_mm": 400,
                "compression_flange_minor_inertia_mm4": 30_000_000,
            },
        ),
        (
            "advanced_members",
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
            },
        ),
    ],
)
def test_extended_family_successful_http_execution(suffix, inputs):
    with TestClient(create_app(authenticator=AllowAllAuthenticator())) as client:
        response = client.post(
            f"/api/v1/calculations/structural.as4100.{suffix}/run", json={"inputs": inputs}
        )
        assert response.status_code == 200, response.text
        assert response.json()["_provenance"]["standard"]["edition"] == "2020"
        if inputs.get("operation") == "full_lateral_restraint_limit":
            assert response.json()["clauses"] == ["5.3.2.4"]
            assert response.json()["values"]["permitted_slenderness"] == pytest.approx(150)
        if inputs.get("operation") == "critical_section":
            assert response.json()["values"]["critical_section_id"] == "B"
        if inputs.get("operation") == "critical_flange":
            assert response.json()["values"]["critical_flange_position"] == "bottom"
        if inputs.get("operation") == "moment_modification_factor":
            assert response.json()["values"]["moment_factor"] == pytest.approx(1.1258525035052873)
        if inputs.get("operation") == "unequal_flange_bending":
            assert response.json()["values"]["beta_x_mm"] == pytest.approx(64)
            assert response.json()["clauses"][-1] == "5.6.1.2"
        if inputs.get("operation") == "varying_section_bending":
            assert response.json()["values"]["alpha_st"] == pytest.approx(0.76)
        if inputs.get("operation") == "web_minimum_thickness":
            assert response.json()["values"]["required_web_thickness_mm"] == pytest.approx(5)
        if inputs.get("operation") == "web_opening_geometry":
            assert response.json()["checked_conditions_satisfied"]
        if inputs.get("check_type") == "minimum_beam_shear_action":
            assert response.json()["intermediate"]["required_design_shear_kn"] == pytest.approx(30)
            assert response.json()["checks"]["connection_shear_capacity"]["satisfied"]
            assert response.json()["intermediate"][
                "clause_9_1_2_3_eccentricity_moment_vector_knm"
            ] == [0, 0, 1.2]
        if inputs.get("check_type") == "minimum_rigid_connection_action":
            assert response.json()["intermediate"]["required_design_moment_knm"] == pytest.approx(
                50
            )
        if inputs.get("check_type") == "minimum_combined_splice_actions":
            assert response.json()["intermediate"]["required_design_moment_knm"] == pytest.approx(
                540
            )
        if inputs.get("check_type") == "joint_eccentricity_action":
            assert response.json()["intermediate"]["eccentricity_moment_vector_knm"] == [
                0,
                0,
                0.25,
            ]
        if inputs.get("check_type") == "fastener_selection_suitability":
            assert response.json()["checks"]["fastener_selection"]["satisfied"]
        if inputs.get("check_type") == "combined_connection_action_assignment":
            assignments = response.json()["intermediate"]["load_case_assignments"][0][
                "component_group_assignments"
            ]
            assert assignments[0]["assigned_actions"]["shear_y_kn"] == 80
            assert assignments[1]["assigned_actions"]["shear_y_kn"] == 0
        if inputs.get("check_type") == "bolt":
            assert response.json()["intermediate"]["total_bolt_tension_action_kn"] == 55
        if inputs.get("check_type") == "bolt_group_out_of_plane":
            assert response.json()["checks"]["action_distribution_equilibrium"]["satisfied"]
            assert response.json()["checks"]["bolts"][0]["total_bolt_tension_action_kn"] == 85
        if inputs.get("check_type") == "bolt_group_elastic_3d":
            assert response.json()["checks"]["action_distribution_equilibrium"]["satisfied"]
            assert response.json()["intermediate"]["distributed_bolt_actions"][0][
                "tension_action_kn"
            ] == pytest.approx(45)
        if inputs.get("operation") == "chs_shear":
            assert response.json()["values"]["effective_shear_area_mm2"] == pytest.approx(2500)
            assert response.json()["checks"]["shear_bending"]["satisfied"]
        if inputs.get("operation") == "shear_with_flange_restraint":
            assert response.json()["values"]["effective_flange_outstand_mm"] == pytest.approx(20)
            assert {"clause": "5.11.5.2"} in response.json()["trace"]
        if inputs.get("operation") == "shear_proportioning":
            assert response.json()["values"]["nominal_flange_moment_capacity_knm"] == pytest.approx(
                85
            )
            assert {"clause": "5.12.2"} in response.json()["trace"]
        if inputs.get("operation") == "plate" and inputs["plate"]["stress"] == "internal_gradient":
            assert response.json()["values"]["effective_modulus_mm3"] == pytest.approx(
                100000 * (115 / 120) ** 2
            )


def test_hollow_section_truss_stress_range_http_execution():
    with TestClient(create_app(authenticator=AllowAllAuthenticator())) as client:
        response = client.post(
            "/api/v1/calculations/structural.as4100.durability/run",
            json={
                "inputs": {
                    "check_type": "hollow_section_truss_stress_range",
                    "hollow_section_form": "RHS",
                    "joint_type": "gap",
                    "joint_configuration": "N",
                    "member_role": "vertical",
                    "unadjusted_stress_range_mpa": 50,
                    "fillet_weld_used": True,
                    "fillet_weld_throat_mm": 6,
                    "connected_member_wall_thickness_mm": 5,
                    "clause_11_3_1_applicability_verified": True,
                    "member_stress_range_source_verified": True,
                }
            },
        )
    assert response.status_code == 200, response.text
    assert response.json()["results"]["stress_range_factor"] == 2.2
    assert response.json()["results"]["adjusted_stress_range_mpa"] == pytest.approx(110)
    assert response.json()["results"]["fillet_weld_throat_check"]["satisfied"]
