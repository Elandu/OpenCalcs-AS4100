"""Run independent AS 4100 regression cases and emit a machine-readable report."""

import json
import sys
from math import isclose
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from opencalcs_as4100.connections import run_connections  # noqa: E402
from opencalcs_as4100.materials import run_materials  # noqa: E402
from opencalcs_as4100.webs import run_webs  # noqa: E402


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


def main():
    cases = {
        "fillet_lap_1700_mm": lambda: expect_close(fillet(1700), 98.784),
        "fillet_lap_8000_mm": lambda: expect_close(fillet(8000), 61.24608),
        "fillet_lap_8001_mm": lambda: expect_close(fillet(8001), 61.24608),
        "mixed_stiffener_contact_and_outstand": mixed_stiffener,
        "zero_restrained_flanges": zero_restrained_flanges,
        "yield_above_690_mpa": over_scope_yield,
        "clause_2_2_3_unidentified_steel_limits": unidentified_steel_limits,
        "clause_2_2_4_standard_properties": clause_2_2_4_properties,
        "clause_2_2_5_through_thickness_quality": clause_2_2_5_z_quality,
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
