"""Run independent AS 4100 regression cases and emit a machine-readable report."""

import json
import sys
from math import isclose
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from opencalcs_as4100.advanced_members import run_advanced_members  # noqa: E402
from opencalcs_as4100.connections import run_connections  # noqa: E402
from opencalcs_as4100.materials import run_materials  # noqa: E402
from opencalcs_as4100.members import run_members  # noqa: E402
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


def clause_5_6_1_1_a_iii_moment_factor():
    result = run_advanced_members(
        {
            "operation": "moment_modification_factor",
            "maximum_design_moment_knm": 100,
            "quarter_point_moment_2_knm": 80,
            "midpoint_moment_3_knm": 100,
            "quarter_point_moment_4_knm": 80,
            "moment_diagram_verified": True,
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
    return {
        "minimum_transverse_web_thickness_mm": thickness["values"]["required_web_thickness_mm"],
        "opening_ratio_at_limit": opening["values"]["opening_dimension_to_web_depth_ratio"],
    }


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
        "clause_5_2_5_internal_gradient_effective_modulus": clause_5_2_5_internal_gradient,
        "clause_5_2_6_net_gross_section_moduli": clause_5_2_6_hole_moduli,
        "clause_5_3_2_4_unequal_flange_restraint_boundary": (clause_5_3_2_4_lateral_restraint),
        "clause_5_3_2_1_member_capacity_restraint_route": (clause_5_3_2_1_capacity_restraint),
        "clause_5_3_3_critical_section": clause_5_3_3_critical_section,
        "clause_5_5_3_critical_flange": clause_5_5_3_critical_flange,
        "clause_5_6_1_1_a_iii_moment_factor": clause_5_6_1_1_a_iii_moment_factor,
        "clause_5_6_1_1_b_varying_section": clause_5_6_1_1_b_varying_section,
        "clause_5_10_web_geometry": clause_5_10_web_geometry,
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
