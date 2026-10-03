"""Run fixed independent arithmetic/table benchmarks and emit a JSON report."""

import argparse
import json
from math import isclose
from pathlib import Path

from . import __version__
from .advanced_members import run_advanced_members
from .analysis import run_analysis
from .connections import run_connections
from .design_actions import run_design_actions
from .materials import run_materials
from .members import run_members
from .webs import buckling_alpha, run_webs


def verify():
    cases = []

    def record(name, actual, expected, tolerance=1e-9):
        cases.append(
            {
                "name": name,
                "actual": actual,
                "expected": expected,
                "absolute_tolerance": tolerance,
                "passed": isclose(actual, expected, rel_tol=0, abs_tol=tolerance),
            }
        )

    axial = run_analysis(
        {
            "gross_area_mm2": 2000,
            "net_area_mm2": 1500,
            "yield_strength_mpa": 250,
            "ultimate_strength_mpa": 400,
            "tension_distribution_factor": 0.8,
            "compression_form_factor": 0.8,
            "tension_action_kn": 200,
            "compression_action_kn": 135,
        }
    )
    record("7.2 axial tension, hand arithmetic", axial["tension"]["design_capacity_kn"], 367.2)
    record(
        "6.2.1 axial section compression, hand arithmetic",
        axial["compression"]["design_capacity_kn"],
        270,
    )
    material = run_materials(
        {
            "operation": "tabulated_strength",
            "product_standard": "AS/NZS 3678",
            "form": "plate_floorplate",
            "grade": "350",
            "material_thickness_mm": 16,
        }
    )
    record(
        "Table 2.1 grade 350 plate at 16 mm, yield strength",
        material["values"]["yield_strength_mpa"],
        350,
    )
    record(
        "Table 2.1 grade 350 plate at 16 mm, tensile strength",
        material["values"]["tensile_strength_mpa"],
        450,
    )
    through_thickness = run_materials(
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
    record(
        "Clause 2.2.5 ZEd=21 minimum reduction of area",
        through_thickness["checks"][0]["required_reduction_of_area_percent"],
        25,
    )
    slender_gradient = run_members(
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
    )
    record(
        "Clause 5.2.5 slender internal-gradient effective modulus",
        slender_gradient["values"]["effective_modulus_mm3"],
        100000 * (115 / 120) ** 2,
    )
    for slenderness, expected in [(50, 0.808), (100, 0.485)]:
        record(
            f"Table 6.3.3(C), alpha_b=0.5, lambda={slenderness}",
            buckling_alpha(slenderness, 250),
            expected,
            0.00051,
        )
    euler = run_design_actions(
        {
            "operation": "euler_buckling",
            "elastic_modulus_mpa": 200000,
            "second_moment_mm4": 8e6,
            "member_length_mm": 4000,
            "effective_length_factor": 1,
        }
    )
    record(
        "Pin-ended Euler analytical benchmark",
        euler["values"]["elastic_buckling_load_kn"],
        986.9604401089358,
        1e-8,
    )
    stiffener = run_webs(
        {
            "operation": "longitudinal_stiffener",
            "web_depth_mm": 200,
            "web_thickness_mm": 10,
            "stiffener_area_mm2": 1000,
            "stiffener_second_moment_mm4": 3200000,
            "location": "0.2_depth",
        }
    )
    record(
        "5.16.2 longitudinal stiffener, hand arithmetic",
        stiffener["values"]["minimum_second_moment_mm4"],
        3200000,
    )
    web_thickness = run_webs(
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
    record(
        "Clause 5.10.4 transverse web minimum thickness, hand arithmetic",
        web_thickness["values"]["required_web_thickness_mm"],
        5,
    )
    bearing_dispersion = run_webs(
        {
            "operation": "web_bearing",
            "section_type": "i_or_channel",
            "web_thickness_mm": 10,
            "web_yield_mpa": 300,
            "clear_web_depth_mm": 200,
            "stiff_bearing_length_mm": 20,
            "flange_thickness_mm": 12,
            "distance_flange_to_neutral_axis_mm": 90,
            "bearing_geometry_verified": True,
            "restrained_flange_count": 2,
            "bearing_action_kn": 100,
        }
    )
    record(
        "Clause 5.13.1 flange bearing dispersion, Figure 5.13.1.1",
        bearing_dispersion["values"]["bearing_width_at_flange_mm"],
        80,
    )
    record(
        "Clause 5.13.1 web bearing dispersion to neutral axis, slope 1:1",
        bearing_dispersion["values"]["bearing_width_at_neutral_axis_mm"],
        260,
    )
    torsional_stiffener = run_webs(
        {
            "operation": "load_bearing_stiffener",
            "web_bearing_yield_kn": 100,
            "stiffener_area_mm2": 1000,
            "web_yield_mpa": 250,
            "stiffener_yield_mpa": 250,
            "contact_stiffener_area_mm2": 1000,
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
            "torsional_end_restraint_required": True,
            "critical_flange_centroid_spacing_mm": 250,
            "critical_flange_thickness_mm": 10,
            "total_design_load_between_supports_kn": 1000,
            "stiffener_pair_second_moment_about_web_centerline_mm4": 62500,
        }
    )
    record(
        "Clause 5.14.5 stiffener-pair minimum inertia, bounded factor and hand arithmetic",
        torsional_stiffener["values"]["required_stiffener_pair_second_moment_mm4"],
        62500,
    )
    stiffener_attachment = run_webs(
        {
            "operation": "load_bearing_stiffener_attachment",
            "design_bearing_force_kn": 70,
            "design_force_share_to_web_kn": 40,
            "web_connection_design_capacity_kn": 40,
            "tight_uniform_bearing_against_loaded_flange_verified": True,
            "concentrated_force_directly_over_support": True,
            "both_flanges_fitted_or_connected_verified": True,
        }
    )
    record(
        "Clause 5.14.4 connection transfer equality boundary",
        stiffener_attachment["values"]["maximum_supported_web_force_share_kn"],
        40,
    )
    end_post = run_webs(
        {
            "operation": "end_post_area",
            "end_post_required_under_5_15_2_2": True,
            "clear_web_depth_mm": 1000,
            "design_shear_action_kn": 180,
            "capacity_factor": 0.9,
            "shear_buckling_coefficient": 0.5,
            "nominal_web_shear_yield_capacity_kn": 100,
            "end_plate_to_load_bearing_stiffener_distance_mm": 25,
            "end_plate_yield_mpa": 250,
            "end_plate_area_mm2": 3000,
        }
    )
    record(
        "Clause 5.15.9 end-plate minimum area, kN to N hand arithmetic",
        end_post["values"]["minimum_end_plate_area_mm2"],
        3000,
    )
    transverse_termination = run_webs(
        {
            "operation": "transverse_stiffener",
            "clear_web_depth_mm": 200,
            "web_panel_depth_mm": 200,
            "web_thickness_mm": 10,
            "panel_spacing_mm": 200,
            "web_area_mm2": 2000,
            "web_yield_mpa": 250,
            "shear_buckling_coefficient": 0.5,
            "stiffener_configuration": "pair",
            "shear_action_kn": 20,
            "nominal_web_shear_kn": 100,
            "nominal_web_buckling_no_tension_field_kn": 100,
            "nominal_stiffener_buckling_kn": 100,
            "stiffener_area_mm2": 1000,
            "stiffener_second_moment_mm4": 350000,
            "stiffener_outstand_mm": 100,
            "stiffener_thickness_mm": 10,
            "stiffener_yield_mpa": 250,
            "outer_edge_continuously_stiffened": False,
            "stiffener_top_flange_gap_mm": 40,
            "stiffener_bottom_flange_gap_mm": 40,
            "flange_termination_geometry_verified": True,
            "external_normal_force_kn": 10,
            "external_moment_knm": 2,
            "external_parallel_force_kn": 5,
            "force_eccentricity_mm": 50,
            "capacity_factor": 0.9,
            "external_actions_verified": True,
        }
    )
    record(
        "Clause 5.15.1 maximum flange termination gap",
        transverse_termination["values"]["maximum_flange_termination_gap_mm"],
        40,
    )
    record(
        "Clause 5.15.7.1 external-action inertia increase, hand arithmetic",
        transverse_termination["values"]["external_load_stiffness_increase_mm4"],
        138888.8888888889,
        1e-7,
    )
    longitudinal_detail = run_webs(
        {
            "operation": "longitudinal_stiffener",
            "web_depth_mm": 200,
            "web_thickness_mm": 10,
            "stiffener_area_mm2": 1000,
            "stiffener_second_moment_mm4": 3200000,
            "location": "0.2_depth",
            "stiffener_continuous": False,
            "extends_between_transverse_stiffeners": True,
            "attached_to_transverse_stiffeners": True,
        }
    )
    record(
        "Clause 5.16.1 longitudinal stiffener between attached transverse stiffeners",
        int(longitudinal_detail["checks"][0]["satisfied"]),
        1,
    )
    stiffener_trigger = run_webs(
        {
            "operation": "load_bearing_stiffener_requirement",
            "design_compressive_bearing_force_kn": 100,
            "design_web_bearing_capacity_kn": 100,
            "end_post_required_under_5_15_2_2": False,
            "load_bearing_stiffeners_provided": False,
        }
    )
    record(
        "Clause 5.10.2 equality does not trigger load-bearing stiffeners",
        int(not stiffener_trigger["values"]["stiffeners_required"]),
        1,
    )
    side_plate = run_webs(
        {
            "operation": "web_side_reinforcement",
            "design_shear_share_kn": 40,
            "side_plate_design_shear_capacity_kn": 60,
            "fastener_design_shear_capacity_to_web_kn": 45,
            "fastener_design_shear_capacity_to_flanges_kn": 40,
            "symmetry_effects_accounted": True,
        }
    )
    record(
        "Clause 5.10.3 side-plate share limited by weakest transfer path",
        side_plate["values"]["maximum_supported_shear_share_kn"],
        40,
    )
    chs_shear = run_members(
        {
            "operation": "chs_shear",
            "yield_strength_mpa": 250,
            "gross_area_mm2": 3000,
            "net_area_mm2": 2500,
            "oversized_fastener_holes_present": True,
            "action_kn": 202.5,
            "moment_action_knm": 0,
            "section_moment_capacity_knm": 100,
        }
    )
    record(
        "Clause 5.11.4 CHS net effective shear area",
        chs_shear["values"]["effective_shear_area_mm2"],
        2500,
    )
    record(
        "Clause 5.11.4 CHS nominal shear yield capacity",
        chs_shear["values"]["nominal_shear_yield_capacity_kn"],
        225,
    )
    chs_shear_gross_route = run_members(
        {
            "operation": "chs_shear",
            "yield_strength_mpa": 250,
            "gross_area_mm2": 3000,
            "net_area_mm2": 2701,
            "oversized_fastener_holes_present": True,
            "action_kn": 0,
            "moment_action_knm": 0,
            "section_moment_capacity_knm": 100,
        }
    )
    record(
        "Clause 5.11.4 net area greater than 90 percent selects gross area",
        chs_shear_gross_route["values"]["effective_shear_area_mm2"],
        3000,
    )
    chs_shear_at_moment_limit = run_members(
        {
            "operation": "chs_shear",
            "yield_strength_mpa": 250,
            "gross_area_mm2": 3000,
            "net_area_mm2": 2500,
            "oversized_fastener_holes_present": True,
            "action_kn": 0,
            "moment_action_knm": 90,
            "section_moment_capacity_knm": 100,
        }
    )
    record(
        "Clause 5.12.3 shear reduction at design moment capacity",
        chs_shear_at_moment_limit["values"]["nominal_shear_capacity_with_bending_kn"],
        135,
    )
    flange_restraint = run_members(
        {
            "operation": "shear_with_flange_restraint",
            "yield_strength_mpa": 250,
            "web_area_mm2": 1000,
            "panel_depth_mm": 1000,
            "web_thickness_mm": 10,
            "action_kn": 0,
            "moment_action_knm": 0,
            "section_moment_capacity_knm": 100,
            "flange_thickness_mm": 10,
            "clear_web_depth_mm": 200,
            "flange_outstand_from_web_midplane_mm": 20,
            "number_of_webs": 1,
            "no_longitudinal_stiffeners_verified": True,
        }
    )
    record(
        "Clause 5.11.5.2 flange restraint factor, hand arithmetic",
        flange_restraint["values"]["flange_restraint_factor"],
        1.6 - 0.6 / (1.2**0.5),
    )
    record(
        "Clause 5.11.5.2 effective flange outstand",
        flange_restraint["values"]["effective_flange_outstand_mm"],
        20,
    )
    shear_proportioning = run_members(
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
        }
    )
    record(
        "Clause 5.12.2 tension flange effective area",
        shear_proportioning["values"]["effective_tension_flange_area_mm2"],
        1360,
    )
    record(
        "Clause 5.12.2 flange moment capacity, hand arithmetic",
        shear_proportioning["values"]["nominal_flange_moment_capacity_knm"],
        85,
    )
    record(
        "Clause 5.12.2 design web shear capacity",
        shear_proportioning["values"]["design_web_shear_capacity_kn"],
        90,
    )
    web_opening = run_webs(
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
    record(
        "Clause 5.10.7(a) unstiffened opening ratio at limit",
        web_opening["values"]["opening_dimension_to_web_depth_ratio"],
        0.1,
        1e-12,
    )
    bolt = run_connections(
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
            "shear_action_kn": 50,
            "tension_action_kn": 80,
        }
    )
    record(
        "9.3 bolt design shear, hand arithmetic",
        bolt["checks"]["shear"]["design_capacity_kn"],
        92.628,
    )
    bending = run_advanced_members(
        {
            "operation": "buckling_analysis_bending",
            "section_capacity_knm": 100,
            "elastic_buckling_moment_knm": 100,
            "moment_factor": 1,
            "end_configuration": "both_restrained",
            "restraint_and_load_model_verified": True,
            "action_knm": 10,
        }
    )
    record(
        "5.6.4 external buckling moment, hand arithmetic",
        bending["values"]["member_capacity_knm"],
        60,
    )
    moment_factor = run_advanced_members(
        {
            "operation": "moment_modification_factor",
            "maximum_design_moment_knm": 100,
            "quarter_point_moment_2_knm": 80,
            "midpoint_moment_3_knm": 100,
            "quarter_point_moment_4_knm": 80,
            "moment_diagram_verified": True,
        }
    )
    record(
        "Clause 5.6.1.1(a)(iii) moment factor, hand arithmetic",
        moment_factor["values"]["moment_factor"],
        1.1258525035052873,
        1e-12,
    )
    unequal_flange_inputs = {
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
    }
    unequal_flange = run_advanced_members(unequal_flange_inputs)
    record(
        "Clause 5.6.1.2 inertia method beta_x, larger flange in compression",
        unequal_flange["values"]["beta_x_mm"],
        64,
    )
    record(
        "Clause 5.6.1.2 positive-beta reference buckling moment, hand arithmetic",
        unequal_flange["values"]["reference_buckling_moment_knm"],
        208.97650338006295,
        1e-10,
    )
    record(
        "Clause 5.6.1 unequal-flange member moment capacity, hand arithmetic",
        unequal_flange["values"]["member_capacity_knm"],
        147.1430856197119,
        1e-10,
    )
    unequal_flange_inputs.pop("flange_centroid_spacing_mm")
    unequal_flange_inputs.pop("compression_flange_minor_inertia_mm4")
    unequal_flange_inputs["beta_x_method"] = "section_integral"
    unequal_flange_inputs["beta_x_mm"] = -64
    unequal_flange_inputs["beta_x_integral_verified"] = True
    unequal_flange_integral = run_advanced_members(unequal_flange_inputs)
    record(
        "Clause 5.6.1.2 section-integral beta_x, smaller flange in compression",
        unequal_flange_integral["values"]["beta_x_mm"],
        -64,
    )
    record(
        "Clause 5.6.1.2 negative-beta reference buckling moment, hand arithmetic",
        unequal_flange_integral["values"]["reference_buckling_moment_knm"],
        180.90296197251985,
        1e-10,
    )
    varying_bending = run_advanced_members(
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
    record(
        "Clause 5.6.1.1(b)(ii) stepped-section alpha_st, hand arithmetic",
        varying_bending["values"]["alpha_st"],
        0.76,
    )
    record(
        "Clause 5.6.1.1(b)(ii) adjusted reference moment, hand arithmetic",
        varying_bending["values"]["adjusted_reference_buckling_moment_knm"],
        76,
    )
    record(
        "Clause 5.6.1.1(b)(ii) member moment capacity, hand arithmetic",
        varying_bending["values"]["member_capacity_knm"],
        71.58374376007083,
        1e-10,
    )
    effective_length = run_advanced_members(
        {
            "operation": "lateral_buckling_effective_length",
            "segment_length_mm": 1000,
            "clear_flange_depth_mm": 200,
            "critical_flange_thickness_mm": 20,
            "web_thickness_mm": 10,
            "number_of_webs": 2,
            "restraint_arrangement": "PP",
            "gravity_load_position": "within_segment",
            "load_height_position": "top_flange",
            "effective_rotation_restraint_count": 2,
            "effective_rotation_restraints_verified": True,
        }
    )
    for key, expected in [
        ("twist_restraint_factor", 1.2),
        ("load_height_factor", 1.4),
        ("lateral_rotation_factor", 0.7),
        ("effective_length_factor", 1.176),
        ("effective_length_mm", 1176),
    ]:
        record(f"Table 5.6.3 {key}", effective_length["values"][key], expected)
    restraint_cases = [
        ("equal_flanged_i", {"radius_of_gyration_y_mm": 10}, 300, 30),
        ("equal_flanged_channel", {"radius_of_gyration_y_mm": 10}, 200, 20),
        (
            "unequal_flange_i",
            {
                "radius_of_gyration_y_mm": 10,
                "gross_area_mm2": 10000,
                "flange_centroid_spacing_mm": 400,
                "compression_flange_minor_inertia_mm4": 1000000,
                "section_minor_inertia_mm4": 2000000,
                "effective_section_modulus_ex_mm3": 2000000,
            },
            268.3281572999747,
            30 * (0.8**0.5),
        ),
        (
            "rhs_or_shs",
            {
                "radius_of_gyration_y_mm": 10,
                "flange_width_mm": 100,
                "web_depth_mm": 200,
            },
            1500,
            150,
        ),
        (
            "angle",
            {
                "thickness_mm": 10,
                "greater_leg_width_b1_mm": 100,
                "lesser_leg_width_b2_mm": 50,
            },
            247.48737341529164,
            35 * (0.5**0.5),
        ),
    ]
    for section, properties, length, expected_limit in restraint_cases:
        restraint = run_advanced_members(
            {
                "operation": "full_lateral_restraint_limit",
                "section_type": section,
                "segment_length_mm": length,
                "yield_strength_mpa": 250,
                "beta_m_basis": "conservative_minus_one",
                "section_properties_verified": True,
                "both_ends_restrained_verified": True,
                **properties,
            }
        )
        record(
            f"Clause 5.3.2.4 {section} slenderness limit",
            restraint["values"]["permitted_slenderness"],
            expected_limit,
            1e-12,
        )
    capacity_restraint = run_members(
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
    record(
        "Clause 5.3.2.1 member moment capacity reaches section capacity",
        capacity_restraint["values"]["member_capacity_knm"],
        100,
        1e-12,
    )
    record(
        "Clause 5.3.2.1 full-restraint classification",
        int(capacity_restraint["values"]["full_lateral_restraint_qualifies"]),
        1,
    )
    critical_section = run_advanced_members(
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
    record(
        "Clause 5.3.3 critical section moment-to-capacity ratio",
        critical_section["values"]["maximum_moment_to_capacity_ratio"],
        0.6,
        1e-12,
    )
    critical_flange = run_advanced_members(
        {
            "operation": "critical_flange",
            "segment_end_condition": "one_end_unrestrained",
            "dominant_load": "wind",
            "wind_case": "internal_pressure",
            "exterior_flange_position": "top",
        }
    )
    record(
        "Clause 5.5.3 internal pressure selects interior flange",
        int(critical_flange["values"]["critical_flange_position"] == "bottom"),
        1,
    )
    return {
        "package_version": __version__,
        "standard": "AS 4100:2020",
        "passed": all(case["passed"] for case in cases),
        "cases": cases,
        "limitations": [
            "Fixed benchmarks verify selected arithmetic and table values.",
            "This report does not establish complete standard coverage.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify()
    rendered = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
