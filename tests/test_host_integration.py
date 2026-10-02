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
    ],
)
def test_extended_family_successful_http_execution(suffix, inputs):
    with TestClient(create_app(authenticator=AllowAllAuthenticator())) as client:
        response = client.post(
            f"/api/v1/calculations/structural.as4100.{suffix}/run", json={"inputs": inputs}
        )
        assert response.status_code == 200, response.text
        assert response.json()["_provenance"]["standard"]["edition"] == "2020"
