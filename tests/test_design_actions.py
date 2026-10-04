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
