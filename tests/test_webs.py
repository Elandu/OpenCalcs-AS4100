# SPDX-License-Identifier: AGPL-3.0-only
import pytest

from opencalcs_as4100.webs import buckling_alpha
from opencalcs_as4100.webs import run_webs as run


def test_web_buckling_reduction_against_standard_table():
    # Table 6.3.3(C), alpha_b=0.5; differences limited to published rounding.
    assert buckling_alpha(50, 250) == pytest.approx(0.808, abs=0.00051)
    assert buckling_alpha(100, 250) == pytest.approx(0.485, abs=0.00051)


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
