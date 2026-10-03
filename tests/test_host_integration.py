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
