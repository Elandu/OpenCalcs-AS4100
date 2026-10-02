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
