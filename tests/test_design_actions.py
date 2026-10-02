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
