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
from .durability import run_durability
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

    truss_stress_range = run_durability(
        {
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
    )["results"]
    record(
        "Table 11.3.1(B) RHS gap N-joint vertical stress-range factor",
        truss_stress_range["stress_range_factor"],
        2.2,
    )
    record(
        "Clause 11.3.1 adjusted stress range, hand arithmetic",
        truss_stress_range["adjusted_stress_range_mpa"],
        110,
    )
    record(
        "Clause 11.3.1(c) fillet throat exceeds connected wall",
        int(truss_stress_range["fillet_weld_throat_check"]["satisfied"]),
        1,
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
    top_flange_holes = run_connections(
        {
            "check_type": "hole_deduction",
            "gross_area_mm2": 1000,
            "thickness_mm": 10,
            "straight_hole_width_sum_mm": 20,
            "zigzag_hole_width_sum_mm": 0,
            "stagger_pairs": [],
        }
    )
    net_i_section = run_members(
        {
            "operation": "section_moduli",
            "method": "net_section",
            "yield_strength_mpa": 300,
            "ultimate_strength_mpa": 400,
            "gross_area_mm2": 4800,
            "gross_web_area_mm2": 2800,
            "gross_flange_areas_mm2": [1000, 1000],
            "net_flange_areas_mm2": [top_flange_holes["intermediate"]["net_area_mm2"], 1000],
            "gross_elastic_modulus_mm3": 402400,
            "gross_plastic_modulus_mm3": 486000,
            "net_i_section_geometry": {
                "overall_depth_mm": 300,
                "flange_thickness_mm": 10,
                "web_thickness_mm": 10,
                "bending_axis": "major",
                "symmetric_sharp_corner_i_section_verified": True,
                "flange_only_holes_verified": True,
                "net_flange_areas_deducted_under_clause_9_1_10_verified": True,
            },
        }
    )
    net_properties = net_i_section["values"]["net_section_properties"]
    record(
        "Clause 9.1.10 single-hole flange net area",
        top_flange_holes["intermediate"]["net_area_mm2"],
        800,
    )
    record(
        "Clause 5.2.6(b) net I-section centroid from top",
        net_properties["centroid_from_top_mm"],
        156.30434782608697,
        1e-9,
    )
    record(
        "Clause 5.2.6(b) net I-section plastic neutral axis in web",
        net_properties["plastic_neutral_axis_from_top_mm"],
        160,
    )
    record(
        "Clause 5.2.6(b) net I-section second moment",
        net_properties["second_moment_of_area_mm4"],
        55970507.24637682,
        1e-6,
    )
    record(
        "Clause 5.2.6(b) top elastic modulus",
        net_properties["elastic_modulus_top_mm3"],
        358086.6944830784,
        1e-7,
    )
    record(
        "Clause 5.2.6(b) bottom elastic modulus",
        net_properties["elastic_modulus_bottom_mm3"],
        389507.3121533032,
        1e-7,
    )
    record("Clause 5.2.6(b) net plastic modulus", net_properties["plastic_modulus_mm3"], 456000)
    record(
        "Clause 5.2.6(b) selects the lower extreme-fibre elastic modulus",
        net_i_section["values"]["elastic_modulus_mm3"],
        358086.6944830784,
        1e-7,
    )
    plastic_axis_in_flange = run_members(
        {
            "operation": "section_moduli",
            "method": "net_section",
            "yield_strength_mpa": 300,
            "ultimate_strength_mpa": 400,
            "gross_area_mm2": 2560,
            "gross_web_area_mm2": 560,
            "gross_flange_areas_mm2": [1000, 1000],
            "net_flange_areas_mm2": [1000, 100],
            "gross_elastic_modulus_mm3": 304835.55555555556,
            "gross_plastic_modulus_mm3": 329200,
            "net_i_section_geometry": {
                "overall_depth_mm": 300,
                "flange_thickness_mm": 10,
                "web_thickness_mm": 2,
                "bending_axis": "major",
                "symmetric_sharp_corner_i_section_verified": True,
                "flange_only_holes_verified": True,
                "net_flange_areas_deducted_under_clause_9_1_10_verified": True,
            },
        }
    )["values"]["net_section_properties"]
    record(
        "Clause 5.2.6(b) plastic neutral axis within top flange",
        plastic_axis_in_flange["plastic_neutral_axis_from_top_mm"],
        8.3,
    )
    record(
        "Clause 5.2.6(b) flange-axis net plastic modulus, hand integration",
        plastic_axis_in_flange["plastic_modulus_mm3"],
        111611,
    )
    record(
        "Clause 5.2.6(b) flange-axis lower elastic modulus",
        plastic_axis_in_flange["elastic_modulus_bottom_mm3"],
        72332.02459376372,
        1e-7,
    )
    rhs_flange_holes = run_connections(
        {
            "check_type": "hole_deduction",
            "gross_area_mm2": 1500,
            "thickness_mm": 10,
            "straight_hole_width_sum_mm": 30,
            "zigzag_hole_width_sum_mm": 0,
            "stagger_pairs": [],
        }
    )
    net_rhs_section = run_members(
        {
            "operation": "section_moduli",
            "method": "net_section",
            "yield_strength_mpa": 300,
            "ultimate_strength_mpa": 400,
            "gross_area_mm2": 8600,
            "gross_web_area_mm2": 5600,
            "gross_flange_areas_mm2": [1500, 1500],
            "net_flange_areas_mm2": [rhs_flange_holes["intermediate"]["net_area_mm2"], 1500],
            "gross_elastic_modulus_mm3": 664577.7777777778,
            "gross_plastic_modulus_mm3": 827000,
            "net_rhs_geometry": {
                "overall_depth_mm": 300,
                "flange_thickness_mm": 10,
                "web_thickness_mm": 10,
                "bending_axis": "major",
                "symmetric_sharp_corner_rhs_section_verified": True,
                "flange_only_holes_verified": True,
                "net_flange_areas_deducted_under_clause_9_1_10_verified": True,
            },
        }
    )
    rhs_properties = net_rhs_section["values"]["net_section_properties"]
    record(
        "Clause 9.1.10 RHS single-hole flange net area",
        rhs_flange_holes["intermediate"]["net_area_mm2"],
        1200,
    )
    record(
        "Clause 5.2.6(b) net RHS centroid from top",
        rhs_properties["centroid_from_top_mm"],
        155.2409638554217,
        1e-9,
    )
    record(
        "Clause 5.2.6(b) net RHS second moment",
        rhs_properties["second_moment_of_area_mm4"],
        93148684.73895583,
        1e-6,
    )
    record(
        "Clause 5.2.6(b) net RHS plastic neutral axis",
        rhs_properties["plastic_neutral_axis_from_top_mm"],
        157.5,
    )
    record(
        "Clause 5.2.6(b) net RHS top elastic modulus",
        rhs_properties["elastic_modulus_top_mm3"],
        600026.4519467081,
        1e-7,
    )
    record(
        "Clause 5.2.6(b) net RHS bottom elastic modulus",
        rhs_properties["elastic_modulus_bottom_mm3"],
        643474.0602025246,
        1e-7,
    )
    record(
        "Clause 5.2.6(b) net RHS plastic modulus, hand integration",
        rhs_properties["plastic_modulus_mm3"],
        782375,
    )
    record(
        "Clause 5.2.6(b) selects lower net RHS extreme-fibre modulus",
        net_rhs_section["values"]["elastic_modulus_mm3"],
        600026.4519467081,
        1e-7,
    )

    compact_interaction = run_members(
        {
            "operation": "interaction",
            "axial_mode": "compression",
            "section_axial_capacity_kn": 1000,
            "member_axial_x_kn": 800,
            "member_axial_y_kn": 500,
            "section_moment_x_knm": 100,
            "section_moment_y_knm": 50,
            "member_moment_x_knm": 70,
            "axial_action_kn": 450,
            "moment_x_knm": 10,
            "moment_y_knm": 20,
            "compact_doubly_symmetric_i_verified": True,
        }
    )
    record(
        "Clause 8.3.3(a) compact I-section minor-axis capacity, hand arithmetic",
        compact_interaction["values"]["compact_section_reduced_y_knm"],
        44.625,
    )
    record(
        "Clause 8.3.4 compact biaxial exponent, hand arithmetic",
        compact_interaction["values"]["compact_section_biaxial_gamma"],
        1.9,
    )
    record(
        "Clause 8.3.4 compact biaxial interaction, hand arithmetic",
        compact_interaction["checks"]["compact_section_biaxial"]["utilisation"],
        0.32328522582491365,
        1e-12,
    )
    compact_kf_one_interaction = run_members(
        {
            "operation": "interaction",
            "axial_mode": "compression",
            "section_axial_capacity_kn": 1000,
            "member_axial_x_kn": 800,
            "member_axial_y_kn": 500,
            "section_moment_x_knm": 100,
            "section_moment_y_knm": 50,
            "member_moment_x_knm": 70,
            "axial_action_kn": 450,
            "moment_x_knm": 10,
            "moment_y_knm": 20,
            "compact_doubly_symmetric_i_verified": True,
            "compression_form_factor_one_verified": True,
        }
    )
    record(
        "Clause 8.3.2(a) compact major-axis capacity for kf=1.0, hand arithmetic",
        compact_kf_one_interaction["values"]["compact_section_reduced_x_knm"],
        59,
    )
    record(
        "Clause 8.3.4 powered interaction with Clause 8.3.2(a), hand arithmetic",
        compact_kf_one_interaction["checks"]["compact_section_biaxial"]["utilisation"],
        0.30779756197106134,
        1e-12,
    )
    compact_kf_below_one_interaction = run_members(
        {
            "operation": "interaction",
            "axial_mode": "compression",
            "section_axial_capacity_kn": 1000,
            "member_axial_x_kn": 800,
            "member_axial_y_kn": 500,
            "section_moment_x_knm": 100,
            "section_moment_y_knm": 50,
            "member_moment_x_knm": 70,
            "axial_action_kn": 450,
            "moment_x_knm": 10,
            "moment_y_knm": 20,
            "compact_doubly_symmetric_i_verified": True,
            "compression_form_factor_below_one_verified": True,
            "compression_form_factor": 0.8,
            "web_clear_width_mm": 65,
            "web_thickness_mm": 1,
            "web_yield_strength_mpa": 250,
            "web_residual_stress_category": "HR",
        }
    )
    record(
        "Clause 6.2.3 web element slenderness, hand arithmetic",
        compact_kf_below_one_interaction["values"]["compact_section_web_lambda_w"],
        65,
    )
    record(
        "Table 6.2.4 hot-rolled internal plate yield slenderness limit",
        compact_kf_below_one_interaction["values"]["compact_section_web_lambda_wy"],
        45,
    )
    record(
        "Clause 8.3.2(b) compact major-axis capacity, hand arithmetic",
        compact_kf_below_one_interaction["values"]["compact_section_reduced_x_knm"],
        54.13513513513514,
        1e-12,
    )
    record(
        "Clause 8.3.4 powered interaction with Clause 8.3.2(b), hand arithmetic",
        compact_kf_below_one_interaction["checks"]["compact_section_biaxial"]["utilisation"],
        0.3152420180103579,
        1e-12,
    )
    compact_rhs_interaction = run_members(
        {
            "operation": "interaction",
            "axial_mode": "compression",
            "section_axial_capacity_kn": 1000,
            "member_axial_x_kn": 800,
            "member_axial_y_kn": 500,
            "section_moment_x_knm": 100,
            "section_moment_y_knm": 50,
            "member_moment_x_knm": 70,
            "axial_action_kn": 450,
            "moment_x_knm": 10,
            "moment_y_knm": 20,
            "compact_rhs_shs_verified": True,
        }
    )
    record(
        "Clause 8.3.3(b) compact RHS/SHS minor-axis capacity, hand arithmetic",
        compact_rhs_interaction["values"]["compact_section_reduced_y_knm"],
        29.5,
    )
    record(
        "Clause 8.3.4 compact RHS/SHS biaxial interaction, hand arithmetic",
        compact_rhs_interaction["checks"]["compact_section_biaxial"]["utilisation"],
        0.6411580100977792,
        1e-12,
    )
    for slenderness, expected in [(50, 0.808), (100, 0.485)]:
        record(
            f"Table 6.3.3(C), alpha_b=0.5, lambda={slenderness}",
            buckling_alpha(slenderness, 250),
            expected,
            0.00051,
        )
    torsional_flexural = run_advanced_members(
        {
            "operation": "torsional_flexural_compression",
            "member_section_form": "fabricated_monosymmetric",
            "bracing_axis": "minor_principal",
            "section_and_axis_applicability_verified": True,
            "as_nzs_4600_nominal_member_capacity_kn": 400,
            "as_nzs_4600_calculation_verified": True,
            "as_nzs_4600_calculation_reference": "INDEPENDENT-HAND-CALC",
            "action_kn": 306,
        }
    )
    record(
        "Clause 6.3.3 AS 4100 flexural-torsional reduction",
        torsional_flexural["values"]["nominal_member_capacity_kn"],
        340,
    )
    record(
        "Clause 6.3.3 AS 4100 factored capacity",
        torsional_flexural["checks"][0]["design_capacity"],
        306,
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
    plastic_hinge_web = run_webs(
        {
            "operation": "web_minimum_thickness",
            "design_case": "plastic_hinge",
            "clear_web_depth_mm": 1000,
            "web_thickness_mm": 12,
            "web_yield_mpa": 250,
            "hinge_zone_load_kn": 100,
            "design_web_shear_yield_capacity_kn": 1000,
            "bearing_or_shear_within_half_depth_of_hinge_verified": True,
            "load_bearing_stiffeners_provided": True,
            "stiffeners_within_half_depth_verified": True,
            "stiffener_design_5_14_verified": True,
            "flat_stiffener_plates": [
                {
                    "clear_outstand_mm": 80,
                    "thickness_mm": 10,
                    "yield_mpa": 250,
                    "residual_stress_category": "SR",
                }
            ],
        }
    )
    record(
        "Clause 5.10.6 flat stiffener plate slenderness under 5.2.2 Table 5.2",
        plastic_hinge_web["values"]["flat_stiffener_plate_checks"][0]["slenderness"],
        8,
    )
    calculated_transverse_stiffener = run_webs(
        {
            "operation": "transverse_stiffener",
            "clear_web_depth_mm": 1000,
            "web_panel_depth_mm": 1000,
            "web_thickness_mm": 5,
            "panel_spacing_mm": 1000,
            "web_area_mm2": 5000,
            "web_yield_mpa": 250,
            "stiffener_configuration": "pair",
            "shear_action_kn": 50,
            "stiffener_area_mm2": 1000,
            "stiffener_second_moment_mm4": 200000,
            "stiffener_outstand_mm": 100,
            "stiffener_thickness_mm": 10,
            "stiffener_yield_mpa": 250,
            "outer_edge_continuously_stiffened": False,
            "stiffener_layout_verified": True,
            "longitudinal_stiffeners_present": False,
            "stiffener_buckling_geometry": {
                "radius_of_gyration_mm": 100,
                "available_web_width_left_mm": 500,
                "available_web_width_right_mm": 500,
            },
            "web_connection_design_shear_capacity_kn_per_mm": 0.05,
            "web_connection_capacity_verified": True,
        }
    )
    calculated_stiffener_values = calculated_transverse_stiffener["values"]
    calculated_capacity_basis = calculated_stiffener_values["capacity_basis"]
    record(
        "Clause 5.11.5.2 stiffened-web shear buckling coefficient from geometry",
        calculated_stiffener_values["shear_buckling_coefficient"],
        0.294175,
    )
    record(
        "Clause 5.11.2 nominal web shear capacity from geometry",
        calculated_stiffener_values["nominal_web_shear_capacity_kn"],
        220.63125,
    )
    record(
        "Clause 5.14.2 effective-section buckling capacity from geometry",
        calculated_stiffener_values["nominal_stiffener_buckling_kn"],
        468.75,
    )
    record(
        "Clause 5.15.4 effective length is the web depth d1",
        calculated_capacity_basis["clause_5_14_2"]["effective_length_mm"],
        1000,
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
            "stiffener_configuration": "pair",
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
    end_post_design = run_webs(
        {
            "operation": "end_post_design",
            "end_post_required_under_5_15_2_2": True,
            "clear_web_depth_mm": 1000,
            "design_shear_action_kn": 180,
            "capacity_factor": 0.9,
            "shear_buckling_coefficient": 0.5,
            "nominal_web_shear_yield_capacity_kn": 100,
            "end_plate_to_load_bearing_stiffener_distance_mm": 25,
            "end_plate_yield_mpa": 250,
            "end_plate_area_mm2": 3000,
            "design_bearing_force_kn": 20,
            "load_bearing_stiffener_inputs": {
                "web_bearing_yield_kn": 100,
                "contact_stiffener_area_mm2": 1000,
                "radius_of_gyration_mm": 50,
                "both_flanges_rotation_restrained": True,
                "available_web_width_left_mm": 200,
                "available_web_width_right_mm": 200,
                "stiffener_area_mm2": 2500,
                "stiffener_configuration": "pair",
                "web_yield_mpa": 250,
                "stiffener_yield_mpa": 250,
                "web_thickness_mm": 10,
                "clear_web_depth_mm": 1000,
                "panel_spacing_mm": 600,
                "stiffener_outstand_mm": 80,
                "stiffener_thickness_mm": 10,
                "outer_edge_continuously_stiffened": False,
                "load_bearing_stiffener_not_smaller_than_end_plate_verified": True,
            },
            "load_bearing_stiffener_attachment_inputs": {
                "design_force_share_to_web_kn": 10,
                "web_connection_design_capacity_kn": 10,
                "tight_uniform_bearing_against_loaded_flange_verified": True,
                "concentrated_force_directly_over_support": False,
            },
        }
    )
    record(
        "Clause 5.15.2.2 end-post route applies Clause 5.14 resistance and attachment checks",
        int(end_post_design["checked_conditions_satisfied"]),
        1,
    )
    record(
        "Clause 5.15.9 end-post route retains the hand-calculated end-plate area",
        end_post_design["values"]["minimum_end_plate_area_mm2"],
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
            "stiffener_layout_verified": True,
            "longitudinal_stiffeners_present": False,
            "stiffener_top_flange_gap_mm": 40,
            "stiffener_bottom_flange_gap_mm": 40,
            "flange_termination_geometry_verified": True,
            "external_normal_force_kn": 10,
            "external_moment_knm": 2,
            "external_parallel_force_kn": 5,
            "force_eccentricity_mm": 50,
            "capacity_factor": 0.9,
            "external_actions_verified": True,
            "load_bearing_stiffener_inputs": {
                "web_bearing_yield_kn": 100,
                "contact_stiffener_area_mm2": 1000,
                "radius_of_gyration_mm": 50,
                "both_flanges_rotation_restrained": True,
                "available_web_width_left_mm": 200,
                "available_web_width_right_mm": 0,
            },
            "load_bearing_stiffener_attachment_inputs": {
                "design_force_share_to_web_kn": 5,
                "web_connection_design_capacity_kn": 5,
                "tight_uniform_bearing_against_loaded_flange_verified": True,
                "concentrated_force_directly_over_support": False,
            },
        }
    )
    record(
        "Clause 5.15.2.1 applies the Clause 5.10.4 interior-panel thickness check",
        transverse_termination["values"]["clause_5_15_2_1_web_thickness_check"]["values"][
            "required_web_thickness_mm"
        ],
        1,
    )
    longitudinal_panel = run_webs(
        {
            "operation": "transverse_stiffener",
            "clear_web_depth_mm": 200,
            "web_panel_depth_mm": 200,
            "web_thickness_mm": 0.8,
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
            "stiffener_second_moment_mm4": 200000,
            "stiffener_outstand_mm": 100,
            "stiffener_thickness_mm": 10,
            "stiffener_yield_mpa": 250,
            "outer_edge_continuously_stiffened": False,
            "stiffener_layout_verified": True,
            "longitudinal_stiffeners_present": True,
            "web_connection_design_shear_capacity_kn_per_mm": 0.00128,
            "web_connection_capacity_verified": True,
            "longitudinal_stiffener_d2_mm": 500,
            "neutral_axis_stiffener_set_present": True,
        }
    )
    record(
        "Clause 5.15.2.1 selects Clause 5.10.5 with longitudinal stiffeners",
        longitudinal_panel["values"]["clause_5_15_2_1_web_thickness_check"]["values"][
            "required_web_thickness_mm"
        ],
        0.8,
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
    record(
        "Clause 5.15.8 intermediate stiffener web-connection shear per unit length",
        longitudinal_panel["values"]["connection_design_shear_kn_per_mm"],
        0.00128,
    )
    load_bearing_check = transverse_termination["values"]["clause_5_14_load_bearing_stiffener"]
    record(
        "Clause 5.15.7.2 parallel web force passed to Clause 5.14.1",
        load_bearing_check["checks"][0]["action"],
        5,
    )
    record(
        "Clause 5.15.7.2 uses the 5.14.1 nominal yield resistance",
        load_bearing_check["values"]["bearing_yield_kn"],
        350,
    )
    attachment_check = transverse_termination["values"][
        "clause_5_14_load_bearing_stiffener_attachment"
    ]
    record(
        "Clause 5.15.7.2 checks Clause 5.14.4 web force transfer",
        int(attachment_check["checks"][-1]["satisfied"]),
        1,
    )
    reduced_end_panel = run_webs(
        {
            "operation": "end_panel_design",
            "original_end_panel_spacing_mm": 400,
            "reduced_end_panel_spacing_mm": 200,
            "clear_web_depth_mm": 200,
            "panel_depth_mm": 200,
            "web_thickness_mm": 10,
            "web_area_mm2": 2000,
            "web_yield_mpa": 250,
            "design_shear_action_kn": 50,
            "design_moment_action_knm": 20,
            "section_moment_capacity_knm": 100,
            "stress_max_average_ratio": 1,
            "end_panel_geometry_verified": True,
        }
    )
    record(
        "Clause 5.15.2.2 reduced end-panel shear buckling with alpha_d = 1",
        reduced_end_panel["values"]["nominal_shear_buckling_capacity_kn"],
        300,
    )
    record(
        "Clause 5.15.2.2 reduced end-panel design shear capacity",
        reduced_end_panel["values"]["design_shear_buckling_capacity_kn"],
        270,
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
    rational_flange_restraint = run_members(
        {
            "operation": "shear_with_rational_flange_restraint",
            "yield_strength_mpa": 250,
            "web_area_mm2": 1000,
            "panel_depth_mm": 1000,
            "web_thickness_mm": 10,
            "stiffener_spacing_mm": 3000,
            "tension_field": False,
            "action_kn": 110,
            "moment_action_knm": 0,
            "section_moment_capacity_knm": 100,
            "alpha_f": 1.15,
            "rational_analysis_verified": True,
            "rational_analysis_reference": "INDEPENDENT-HAND-CALC",
            "no_longitudinal_stiffeners_verified": True,
        }
    )
    record(
        "Clause 5.11.5.2(c) stiffened panel aspect ratio",
        rational_flange_restraint["values"]["stiffener_spacing_to_panel_depth_ratio"],
        3,
    )
    record(
        "Clause 5.11.5.2(c) buckling reduction with s/dp=3",
        rational_flange_restraint["values"]["buckling_reduction"],
        (82 / 100) ** 2 * (1 + 0.75 / 3**2),
    )
    record(
        "Clause 5.11.5.2(c) rational alpha_f shear design capacity",
        rational_flange_restraint["checks"]["shear_bending"]["design_capacity"],
        113.089275,
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
            "prying_tension_kn": 0,
            "prying_force_assessment_verified": True,
        }
    )
    record(
        "9.3 bolt design shear, hand arithmetic",
        bolt["checks"]["shear"]["design_capacity_kn"],
        92.628,
    )
    bolt_prying = run_connections(
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
            "tension_action_kn": 20,
            "prying_tension_kn": 10,
            "prying_force_assessment_verified": True,
        }
    )
    record(
        "Clause 9.1.8 externally assessed prying added to bolt tension",
        bolt_prying["intermediate"]["total_bolt_tension_action_kn"],
        30,
    )
    joint_eccentricity = run_connections(
        {
            "check_type": "joint_eccentricity_action",
            "connection_detail_case": "general",
            "fatigue_loading": False,
            "fatigue_detail_eccentricity_assessment_verified": False,
            "centroidal_axes_meet_practicable_verified": False,
            "centroidal_axes_meet_at_joint_verified": False,
            "force_kn": [5, 2, 1],
            "eccentricity_vector_mm": [10, 20, 30],
            "joint_geometry_and_load_line_assessed_verified": True,
        }
    )
    record(
        "Clause 9.1.5 joint eccentricity x-moment, hand arithmetic",
        joint_eccentricity["intermediate"]["eccentricity_moment_vector_knm"][0],
        -0.04,
    )
    record(
        "Clause 9.1.5 joint eccentricity y-moment, hand arithmetic",
        joint_eccentricity["intermediate"]["eccentricity_moment_vector_knm"][1],
        0.14,
    )
    record(
        "Clause 9.1.5 joint eccentricity z-moment, hand arithmetic",
        joint_eccentricity["intermediate"]["eccentricity_moment_vector_knm"][2],
        -0.08,
    )
    fastener_selection = run_connections(
        {
            "check_type": "fastener_selection_suitability",
            "selected_fastener_system": "friction_type_8_8_TF",
            "serviceability_slip_to_be_avoided": True,
            "impact_or_vibration_present": True,
            "service_and_dynamic_action_assessment_verified": True,
        }
    )
    record(
        "Clause 9.1.6 friction-type fastener satisfies both selection conditions",
        int(fastener_selection["checks"]["fastener_selection"]["satisfied"]),
        1,
    )
    combined_connection = run_connections(
        {
            "check_type": "combined_connection_action_assignment",
            "component_groups": [
                {"group_id": "friction-bolts", "fastener_class": "non_slip"},
                {"group_id": "snug-bolts", "fastener_class": "slip_type"},
                {"group_id": "fitted-bolts", "fastener_class": "non_slip"},
            ],
            "load_cases": [
                {
                    "case_id": "service-load",
                    "stage": "non_weld_action",
                    "actions": {
                        "axial_kn": 0,
                        "shear_x_kn": 0,
                        "shear_y_kn": 100,
                        "moment_x_knm": 0,
                        "moment_y_knm": 0,
                        "moment_z_knm": 25,
                    },
                    "shares": [
                        {"group_id": "friction-bolts", "fraction": 0.6},
                        {"group_id": "fitted-bolts", "fraction": 0.4},
                    ],
                }
            ],
            "installation_sequence_assessed_verified": True,
        }
    )
    assigned = combined_connection["intermediate"]["load_case_assignments"][0][
        "component_group_assignments"
    ]
    by_group = {item["group_id"]: item for item in assigned}
    record(
        "Clause 9.1.7 60 percent non-slip shear share, hand arithmetic",
        by_group["friction-bolts"]["assigned_actions"]["shear_y_kn"],
        60,
    )
    record(
        "Clause 9.1.7 40 percent non-slip moment share, hand arithmetic",
        by_group["fitted-bolts"]["assigned_actions"]["moment_z_knm"],
        10,
    )
    bolt_group_oop = run_connections(
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
        }
    )
    record(
        "Clause 9.3.2 bolt-group action equilibrium, hand arithmetic",
        int(bolt_group_oop["checks"]["action_distribution_equilibrium"]["satisfied"]),
        1,
    )
    record(
        "Clause 9.3.2 eccentric bolt tension moment, hand arithmetic",
        bolt_group_oop["intermediate"]["actions_resolved_from_bolts"]["moment_y_knm"],
        -3,
    )
    record(
        "Clauses 9.1.8 and 9.2.2.2 bolt tension including prying",
        bolt_group_oop["checks"]["bolts"][0]["total_bolt_tension_action_kn"],
        85,
    )
    bolt_group_elastic_3d = run_connections(
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
        }
    )
    first_elastic_bolt = bolt_group_elastic_3d["intermediate"]["distributed_bolt_actions"][0]
    record(
        "Clause 9.1.3 rigid-plate elastic bolt B1 x-shear, hand arithmetic",
        first_elastic_bolt["shear_x_kn"],
        4,
    )
    record(
        "Clause 9.1.3 biaxial elastic bolt B1 tension, hand arithmetic",
        first_elastic_bolt["tension_action_kn"],
        45,
    )
    record(
        "Clause 9.1.3 and 9.3.2–3 elastic bolt-group six-resultant equilibrium",
        int(bolt_group_elastic_3d["checks"]["action_distribution_equilibrium"]["satisfied"]),
        1,
    )
    record(
        "Clauses 9.1.8 and 9.2.2.2 elastic bolt-group tension plus prying",
        bolt_group_elastic_3d["checks"]["bolts"][0]["total_bolt_tension_action_kn"],
        46,
    )
    beam_connection_shear = run_connections(
        {
            "check_type": "minimum_beam_shear_action",
            "actual_design_shear_kn": 10,
            "member_design_shear_capacity_kn": 200,
            "simple_construction_beam_connection_verified": True,
            "excluded_connection_arrangement_absent_verified": True,
            "reaction_shear_direction_unit_vector": [0, 1, 0],
            "reaction_shear_eccentricity_vector_mm": [40, 0, 0],
            "reaction_shear_eccentricity_assessment_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(ii) simple-beam minimum shear, 0.15 branch",
        beam_connection_shear["intermediate"]["minimum_design_shear_kn"],
        30,
    )
    record(
        "Clause 9.1.2.3 simple-beam eccentric reaction moment, hand arithmetic",
        beam_connection_shear["intermediate"]["clause_9_1_2_3_eccentricity_moment_vector_knm"][2],
        1.2,
    )
    beam_connection_shear_cap = run_connections(
        {
            "check_type": "minimum_beam_shear_action",
            "actual_design_shear_kn": 10,
            "member_design_shear_capacity_kn": 400,
            "simple_construction_beam_connection_verified": True,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(ii) simple-beam minimum shear, 40 kN cap",
        beam_connection_shear_cap["intermediate"]["minimum_design_shear_kn"],
        40,
    )
    beam_connection_governing_shear = run_connections(
        {
            "check_type": "minimum_beam_shear_action",
            "actual_design_shear_kn": 60,
            "member_design_shear_capacity_kn": 400,
            "simple_construction_beam_connection_verified": True,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4 actual member shear governs the minimum",
        beam_connection_governing_shear["intermediate"]["required_design_shear_kn"],
        60,
    )
    rigid_connection_action = run_connections(
        {
            "check_type": "minimum_rigid_connection_action",
            "rigid_construction_connection_verified": True,
            "actual_design_moment_knm": 20,
            "member_design_moment_capacity_knm": 100,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(i) rigid connection minimum moment",
        rigid_connection_action["intermediate"]["required_design_moment_knm"],
        50,
    )
    member_end_action = run_connections(
        {
            "check_type": "minimum_member_end_action",
            "connection_at_member_end_verified": True,
            "member_end_case": "tension_member_end",
            "actual_design_axial_action_kn": 20,
            "member_design_axial_capacity_kn": 200,
            "threaded_bracing_turnbuckle_arrangement_verified": False,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(iii) member-end axial action minimum",
        member_end_action["intermediate"]["required_design_axial_action_kn"],
        60,
    )
    threaded_bracing_action = run_connections(
        {
            "check_type": "minimum_member_end_action",
            "connection_at_member_end_verified": True,
            "member_end_case": "threaded_tension_bracing_with_turnbuckles",
            "actual_design_axial_action_kn": 20,
            "member_design_axial_capacity_kn": 200,
            "threaded_bracing_turnbuckle_arrangement_verified": True,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(iii) threaded bracing turnbuckle exception",
        threaded_bracing_action["intermediate"]["required_design_axial_action_kn"],
        200,
    )
    tension_splice_action = run_connections(
        {
            "check_type": "minimum_axial_splice_action",
            "axial_member_splice_verified": True,
            "splice_case": "axial_tension",
            "actual_design_axial_action_kn": 20,
            "member_design_axial_capacity_kn": 200,
            "full_contact_bearing_verified": False,
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": False,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(iv) axial tension splice minimum",
        tension_splice_action["intermediate"]["required_design_axial_action_kn"],
        60,
    )
    compression_full_contact_action = run_connections(
        {
            "check_type": "minimum_axial_splice_action",
            "axial_member_splice_verified": True,
            "splice_case": "compression_full_contact",
            "actual_design_axial_action_kn": 20,
            "member_design_axial_capacity_kn": 200,
            "full_contact_bearing_verified": True,
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": False,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(v) full-contact compression splice minimum",
        compression_full_contact_action["intermediate"]["required_design_axial_action_kn"],
        30,
    )
    compression_splice_action = run_connections(
        {
            "check_type": "minimum_axial_splice_action",
            "axial_member_splice_verified": True,
            "splice_case": "compression_not_full_contact",
            "actual_design_axial_action_kn": 20,
            "member_design_axial_capacity_kn": 200,
            "full_contact_bearing_verified": False,
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": True,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(v) non-full-contact compression splice minimum",
        compression_splice_action["intermediate"]["required_design_axial_action_kn"],
        60,
    )
    compression_splice_between_supports = run_connections(
        {
            "check_type": "minimum_compression_splice_between_supports",
            "compression_member_splice_verified": True,
            "actual_design_axial_action_kn": 50,
            "actual_design_moment_knm": 20,
            "member_design_axial_capacity_kn": 400,
            "full_contact_bearing_verified": True,
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": False,
            "splice_between_effective_lateral_supports_verified": True,
            "effective_lateral_support_distance_mm": 3000,
            "amplification_factor_type": "delta_s",
            "amplification_factor": 1.5,
            "amplification_factor_verified": True,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(v) compression splice amplified minimum moment",
        compression_splice_between_supports["intermediate"]["required_design_moment_knm"],
        270,
    )
    combined_tension_splice = run_connections(
        {
            "check_type": "minimum_combined_splice_actions",
            "combined_axial_bending_splice_verified": True,
            "splice_case": "axial_tension",
            "actual_design_axial_action_kn": 20,
            "member_design_axial_capacity_kn": 200,
            "full_contact_bearing_verified": False,
            "splice_parts_and_fasteners_hold_all_parts_in_line_verified": False,
            "actual_design_moment_knm": 20,
            "member_design_moment_capacity_knm": 200,
            "splice_between_effective_lateral_supports_verified": False,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(vii) combined axial tension splice force",
        combined_tension_splice["intermediate"]["required_design_axial_action_kn"],
        60,
    )
    record(
        "Clause 9.1.4(b)(vii) combined flexural splice moment",
        combined_tension_splice["intermediate"]["required_design_moment_knm"],
        60,
    )
    combined_compression_splice = run_connections(
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
        }
    )
    record(
        "Clause 9.1.4(b)(vii) combined compression splice axial force",
        combined_compression_splice["intermediate"]["required_design_axial_action_kn"],
        120,
    )
    record(
        "Clause 9.1.4(b)(vii) combined compression splice moment",
        combined_compression_splice["intermediate"]["required_design_moment_knm"],
        540,
    )
    flexural_splice_action = run_connections(
        {
            "check_type": "minimum_flexural_splice_action",
            "flexural_splice_not_shear_only_verified": True,
            "actual_design_moment_knm": 20,
            "member_design_moment_capacity_knm": 200,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(vi) flexural splice minimum moment",
        flexural_splice_action["intermediate"]["required_design_moment_knm"],
        60,
    )
    shear_only_splice_action = run_connections(
        {
            "check_type": "shear_only_splice_eccentric_action",
            "actual_design_shear_kn": 50,
            "force_eccentricity_mm": 100,
            "shear_only_splice_verified": True,
            "excluded_connection_arrangement_absent_verified": True,
        }
    )
    record(
        "Clause 9.1.4(b)(vi) shear-only splice eccentric moment",
        shear_only_splice_action["intermediate"]["required_design_moment_knm"],
        5,
    )
    fillet_weld = run_connections(
        {
            "check_type": "fillet_design",
            "weld_strength_mpa": 490,
            "quality": "SP",
            "leg_1_mm": 6,
            "leg_2_mm": 6,
            "included_angle_deg": 90,
            "root_gap_mm": 0,
            "thickest_part_mm": 10,
            "thinnest_part_mm": 6,
            "edge_material_thickness_mm": 10,
            "edge_built_out_verified": False,
            "reinforces_butt_weld": False,
            "overall_length_per_segment_mm": 100,
            "segment_count": 1,
            "intermittent_segment": False,
            "clear_spacing_mm": 0,
            "at_built_up_member_end": False,
            "member_force_type": "other",
            "forms_built_up_member": False,
            "parallel_weld_count": 1,
            "parallel_load_share_verified": False,
            "transverse_weld_spacing_mm": 0,
            "thin_rhs_longitudinal": False,
            "lap_length_mm": 0,
            "action_kn": 50,
        }
    )
    fillet_throat = 6 / 2**0.5
    record(
        "Clause 9.6.3.4 equal-leg fillet design throat",
        fillet_weld["intermediate"]["design_throat_mm"],
        fillet_throat,
    )
    record(
        "Clause 9.6.3.6 fillet effective area",
        fillet_weld["intermediate"]["effective_area_mm2"],
        fillet_throat * 100,
    )
    record(
        "Clause 9.6.3.10 fillet design capacity, hand arithmetic",
        fillet_weld["checks"]["weld_strength"]["design_capacity_kn"],
        0.8 * 0.6 * 490 * fillet_throat * 100 / 1000,
    )
    built_up_end_weld = run_connections(
        {
            "check_type": "built_up_component_end_weld",
            "connected_component_width_mm": 50,
            "weld_length_per_joint_line_mm": 90,
            "side_fillet_only": True,
            "tapered_component": True,
            "widest_component_width_mm": 80,
            "taper_length_mm": 90,
        }
    )
    record(
        "Clause 9.6.3.9(a) tapered built-up component end-weld length",
        int(built_up_end_weld["checks"]["built_up_termination"]["satisfied"]),
        1,
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
            "both_ends_restrained_verified": True,
        }
    )
    record(
        "Clause 5.6.1.1(a)(iii) moment factor, hand arithmetic",
        moment_factor["values"]["moment_factor"],
        1.1258525035052873,
        1e-12,
    )
    table_moment_cases = [
        ("end_moments", {"beta_m": 0.5}, 2.35),
        ("two_symmetric_point_loads", {"twice_a_over_length": 0.4}, 1.126),
        ("single_point_load", {"twice_a_over_length": 0.4}, 1.414),
        ("midspan_point_load_with_one_end_moment", {"beta_m": 0.9}, 1.5),
        ("midspan_point_load_with_equal_end_moments", {"beta_m": 0.5}, 1.53),
        ("uniform_load_with_one_end_moment", {"beta_m": 0.8}, 1.55),
        ("uniform_load_with_equal_end_moments", {"beta_m": 0.75}, 1.22),
        ("uniform_moment", {}, 1.0),
        ("point_load", {}, 1.75),
        ("uniform_load", {}, 2.5),
    ]
    for load_case, case_inputs, expected in table_moment_cases:
        table_moment = run_advanced_members(
            {
                "operation": "table_5_6_1_moment_factor",
                "load_case": load_case,
                "both_ends_restrained_verified": True,
                "table_5_6_1_diagram_verified": True,
                **case_inputs,
            }
        )
        record(
            f"Table 5.6.1 {load_case} moment factor, hand arithmetic",
            table_moment["values"]["moment_factor"],
            expected,
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
        "both_ends_restrained_verified": True,
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
    nonprincipal_bending = run_advanced_members(
        {
            "operation": "nonprincipal_bending",
            "section_axial_capacity_kn": 1000,
            "section_moment_x_knm": 100,
            "section_moment_y_knm": 50,
            "reduced_member_moment_x_knm": 80,
            "reduced_member_moment_y_knm": 40,
            "axial_action_kn": 90,
            "moment_x_knm": 45,
            "moment_y_knm": 22.5,
            "deflections_constrained": False,
            "rational_analysis_verified": True,
        }
    )
    record(
        "Clause 5.7.2/8.3.4 rational-analysis section interaction",
        nonprincipal_bending["values"]["section_interaction"],
        1.1,
    )
    record(
        "Clause 5.7.2/8.4.5 unconstrained biaxial member interaction",
        nonprincipal_bending["values"]["member_interaction"],
        2 * (0.625**1.4),
    )
    angle_shortcut = run_advanced_members(
        {
            "operation": "angle_bending_capacity",
            "member_length_mm": 2100,
            "angle_thickness_mm": 10,
            "angle_leg_a_width_mm": 100,
            "angle_leg_b_width_mm": 100,
            "yield_strength_mpa": 250,
            "beta_m": 0,
            "moment_gradient_factor_verified": True,
            "section_capacity_knm": 20,
            "section_properties_verified": True,
            "figure_8_4_6_connection_and_loading_verified": True,
            "without_full_lateral_support_verified": True,
        }
    )
    record(
        "Clause 8.4.6 equal-leg shortcut includes l/t boundary",
        int(angle_shortcut["values"]["equal_leg_shortcut_used"]),
        1,
    )
    record(
        "Clause 8.4.6 equal-leg shortcut uses Msx",
        angle_shortcut["values"]["member_moment_capacity_mbx_knm"],
        20,
    )
    angle_reduced = run_advanced_members(
        {
            "operation": "angle_bending_capacity",
            "member_length_mm": 5250,
            "angle_thickness_mm": 10,
            "angle_leg_a_width_mm": 100,
            "angle_leg_b_width_mm": 100,
            "yield_strength_mpa": 250,
            "beta_m": 0,
            "moment_gradient_factor_verified": True,
            "section_capacity_knm": 20,
            "section_properties_verified": True,
            "figure_8_4_6_connection_and_loading_verified": True,
            "without_full_lateral_support_verified": True,
            "moment_factor": 1,
            "moment_factor_verified": True,
        }
    )
    record(
        "Clause 8.4.6 equal-leg Mo equation, hand arithmetic",
        angle_reduced["values"]["reference_buckling_moment_mo_knm"],
        20,
    )
    record(
        "Clause 5.6.1.1 angle alpha_s, hand arithmetic",
        angle_reduced["values"]["slenderness_reduction_alpha_s"],
        0.6,
    )
    record(
        "Clause 8.4.6 equal-leg Mbx, hand arithmetic",
        angle_reduced["values"]["member_moment_capacity_mbx_knm"],
        12,
    )
    angle_scaled = run_advanced_members(
        {
            "operation": "angle_bending_capacity",
            "member_length_mm": 5000,
            "angle_thickness_mm": 10,
            "angle_leg_a_width_mm": 100,
            "angle_leg_b_width_mm": 100,
            "yield_strength_mpa": 350,
            "beta_m": 0,
            "moment_gradient_factor_verified": True,
            "section_capacity_knm": 20,
            "section_properties_verified": True,
            "figure_8_4_6_connection_and_loading_verified": True,
            "without_full_lateral_support_verified": True,
            "moment_factor": 1,
            "moment_factor_verified": True,
        }
    )
    record(
        "Clause 8.4.6 equal-leg Mo yield-strength scaling",
        angle_scaled["values"]["reference_buckling_moment_mo_knm"],
        15,
    )
    record(
        "Clause 8.4.6 equal-leg reduced Mbx yield-strength scaling",
        angle_scaled["values"]["member_moment_capacity_mbx_knm"],
        10.229754097208001,
        1e-12,
    )
    angle_compression = run_advanced_members(
        {
            "operation": "angle_compression_capacity",
            "gross_area_mm2": 2000,
            "net_area_mm2": 2000,
            "effective_area_mm2": 2000,
            "yield_strength_mpa": 250,
            "member_length_mm": 1500,
            "radius_about_loaded_leg_h_axis_mm": 10,
            "section_properties_verified": True,
            "figure_8_4_6_connection_and_loading_verified": True,
            "loaded_leg_h_axis_orientation_verified": True,
        }
    )
    record(
        "Clause 8.4.6 angle Nch with Table 6.3.3(A) alpha_b=0.5",
        angle_compression["values"]["nominal_member_capacity_nch_kn"],
        136.5214318742263,
        1e-12,
    )
    angle_compression_reduced_area = run_advanced_members(
        {
            "operation": "angle_compression_capacity",
            "gross_area_mm2": 2000,
            "net_area_mm2": 1800,
            "effective_area_mm2": 1600,
            "yield_strength_mpa": 350,
            "member_length_mm": 5000,
            "radius_about_loaded_leg_h_axis_mm": 15,
            "section_properties_verified": True,
            "figure_8_4_6_connection_and_loading_verified": True,
            "loaded_leg_h_axis_orientation_verified": True,
        }
    )
    record(
        "Clause 8.4.6 angle Nch with Table 6.3.3(B) alpha_b=1.0",
        angle_compression_reduced_area["values"]["nominal_member_capacity_nch_kn"],
        29.516096338384898,
        1e-12,
    )
    angle_section_bending = run_advanced_members(
        {
            "operation": "angle_section_bending_capacity",
            "section_capacity_knm": 100,
            "iy_mm4": 50_000_000,
            "torsion_constant_mm4": 200_000,
            "effective_length_mm": 15_000,
            "moment_factor": 1,
            "moment_factor_verified": True,
            "section_properties_verified": True,
            "angle_section_verified": True,
            "constant_cross_section_verified": True,
            "segment_without_full_lateral_restraint_verified": True,
            "both_ends_restrained_verified": True,
        }
    )
    record(
        "Clause 5.6.1.3 angle Mo with Iw=0, hand arithmetic",
        angle_section_bending["values"]["reference_buckling_moment_knm"],
        83.77580409572782,
        1e-12,
    )
    record(
        "Clause 5.6.1.3 angle alpha_s, hand arithmetic",
        angle_section_bending["values"]["slenderness_reduction_alpha_s"],
        0.5459194274720188,
        1e-12,
    )
    record(
        "Clause 5.6.1.3 angle Mb, hand arithmetic",
        angle_section_bending["values"]["nominal_member_moment_capacity_mb_knm"],
        54.591942747201884,
        1e-12,
    )
    angle_rational_moment = run_advanced_members(
        {
            "operation": "angle_eccentricity",
            "arrangement": "same_side",
            "compression_centroid_offset_mm": 20,
            "tension_centroid_offset_mm": 25,
            "leg_thickness_mm": 10,
            "axial_action_kn": 100,
            "moment_method": "rational_analysis",
            "rational_analysis_moment_knm": 0.5,
        }
    )
    record(
        "Clause 8.4.6 rational-analysis moment alternative",
        angle_rational_moment["values"]["design_moment_knm"],
        0.5,
    )
    angle_eccentricity_minimum = run_advanced_members(
        {
            "operation": "angle_eccentricity",
            "arrangement": "same_side",
            "compression_centroid_offset_mm": 20,
            "tension_centroid_offset_mm": 25,
            "leg_thickness_mm": 10,
            "axial_action_kn": 100,
            "moment_method": "minimum_eccentricity",
        }
    )
    record(
        "Clause 8.4.6 eccentricity minimum-moment route",
        angle_eccentricity_minimum["values"]["design_moment_knm"],
        1.5,
    )
    back_to_back = run_advanced_members(
        {
            "operation": "built_up_compression",
            "construction": "back_to_back",
            "section_capacity_kn": 1000,
            "member_capacity_kn": 500,
            "modified_member_slenderness": 100,
            "axial_action_kn": 100,
            "integral_slenderness_perpendicular": 40,
            "integral_slenderness_parallel": 100,
            "component_slenderness": 30,
            "number_of_bays": 3,
            "similar_symmetric_components_verified": True,
            "interconnection_design": {
                "design_capacity_kn": 7.5 * 3.141592653589793,
                "capacity_verified": True,
            },
        }
    )
    record(
        "Clause 6.5.1.5 back-to-back interconnection demand",
        back_to_back["checks"][-1]["design_demand_kn"],
        7.5 * 3.141592653589793,
    )
    for arrangement, clause in [
        ("separated_back_to_back", "7.4.3(a)(i)"),
        ("laced", "7.4.4(b)"),
        ("battened", "7.4.5(a)"),
    ]:
        slenderness = run_advanced_members(
            {
                "operation": "tension_component_slenderness",
                "arrangement": arrangement,
                "intervals_and_radii_verified": True,
                "component_intervals": [
                    {"unrestrained_length_mm": 3000, "minimum_radius_of_gyration_mm": 10}
                ],
            }
        )
        record(
            f"Clause {clause} component slenderness at limit",
            slenderness["values"]["maximum_component_slenderness"],
            300,
        )
    packing = run_connections(
        {
            "check_type": "packing_construction",
            "packing_thickness_mm": 5,
            "too_thin_for_adequate_welds": False,
            "too_thin_to_prevent_buckling": False,
            "required_edge_weld_sizes_mm": [4, 5],
            "provided_edge_weld_sizes_mm": [9, 10],
            "trimmed_flush_with_member_edges": True,
            "extends_beyond_member_edges": False,
            "welded_to_fitted_piece": False,
        }
    )
    record(
        "Clause 9.8 packing edge-weld increase",
        packing["checks"]["edge_weld_sizes"]["required_mm"][0],
        9,
    )
    single_test_history = run_durability(
        {
            "check_type": "fire_single_test_history",
            "limiting_temperature_c": 500,
            "required_frl_min": 8,
            "protection_thickness_mm": 25,
            "prototype_protection_thickness_mm": 20,
            "surface_mass_ratio_m2_per_tonne": 10,
            "prototype_surface_mass_ratio_m2_per_tonne": 12,
            "same_protection_system": True,
            "same_exposure_condition": True,
            "prototype_was_unloaded": True,
            "stickability_demonstrated": True,
            "temperature_history": [
                {"time_min": 0, "steel_temperature_c": 20},
                {"time_min": 5, "steel_temperature_c": 300},
                {"time_min": 10, "steel_temperature_c": 600},
            ],
        }
    )
    record(
        "Clause 12.6.3 single-test limiting temperature crossing",
        single_test_history["results"]["attained_time_min"],
        8.333333333333334,
    )
    web_protection = run_durability(
        {
            "check_type": "web_penetration_protection",
            "required_thickness_above_mm": 20,
            "required_thickness_below_mm": 25,
            "required_thickness_whole_section_mm": 30,
            "provided_thickness_mm": 30,
            "beam_depth_mm": 450,
            "protected_depth_mm": 450,
            "left_extension_mm": 450,
            "right_extension_mm": 450,
        }
    )
    record(
        "Clause 12.10.2 web-penetration protection extent",
        int(web_protection["results"]["check_satisfied"]),
        1,
    )
    tension_brace = run_durability(
        {
            "check_type": "concentric_tension_brace",
            "bearing_wall_or_building_frame_system_verified": True,
            "design_tension_action_kn": 85,
            "member_design_tensile_capacity_kn": 100,
            "connection_design_tensile_capacity_kn": 100,
        }
    )
    record(
        "Clause 13.3.6.2(a) brace and connection capacity boundaries",
        int(tension_brace["results"]["check_satisfied"]),
        1,
    )
    expected_regression_coefficients = [5, 0.4, 1.2, 0.06, 0.0008, 0.002, 0.1]
    regression_geometries = [
        (12, 7),
        (15, 10),
        (20, 15),
        (25, 22),
        (30, 30),
        (18, 35),
        (40, 12),
        (45, 25),
        (50, 40),
        (60, 18),
    ]
    regression_test_series = []
    for thickness, surface_mass_ratio in regression_geometries:
        temperature_time_points = []
        for temperature in [300, 400, 500, 600]:
            observation = (
                expected_regression_coefficients[0]
                + expected_regression_coefficients[1] * thickness
                + expected_regression_coefficients[2] * thickness / surface_mass_ratio
                + expected_regression_coefficients[3] * temperature
                + expected_regression_coefficients[4] * thickness * temperature
                + expected_regression_coefficients[5] * thickness * temperature / surface_mass_ratio
                + expected_regression_coefficients[6] * temperature / surface_mass_ratio
            )
            temperature_time_points.append({"temperature_c": temperature, "time_min": observation})
        regression_test_series.append(
            {
                "protection_thickness_mm": thickness,
                "surface_mass_ratio_m2_per_tonne": surface_mass_ratio,
                "prototype_was_unloaded": False,
                "stickability_demonstrated": False,
                "temperature_time_points": temperature_time_points,
            }
        )
    regression_fit = run_durability(
        {
            "check_type": "fire_protected_regression_fit",
            "protection_material_type": "low_density_insulation",
            "protection_dry_density_kg_m3": 450,
            "same_protection_system_and_exposure_verified": True,
            "exposure_sides": 4,
            "test_series": regression_test_series,
        }
    )["results"]
    for index, expected in enumerate(expected_regression_coefficients):
        record(
            f"Clause 12.6.2.2 fitted regression coefficient k{index}",
            regression_fit["coefficients"][index],
            expected,
            1e-9,
        )
    record(
        "Clause 12.6.2.2 exact-series correlation coefficient",
        regression_fit["correlation_coefficient"],
        1,
        1e-12,
    )
    record(
        "Clause 12.6.2.2 exact-series residual",
        regression_fit["root_mean_square_residual_min"],
        0,
        1e-9,
    )
    record(
        "Clause 12.6.2.2 measured test-temperature range",
        regression_fit["test_temperature_range_c"][1]
        - regression_fit["test_temperature_range_c"][0],
        300,
    )
    record(
        "Clause 12.6.2.3 interpolation-window convex-hull vertices",
        len(regression_fit["interpolation_window_points"]),
        5,
    )
    regression_check = run_durability(
        {
            "check_type": "fire_protected_regression",
            "coefficients": regression_fit["coefficients"],
            "temperature_c": 500,
            "protection_thickness_mm": 25,
            "surface_mass_ratio_m2_per_tonne": 22,
            "required_frl_min": 60,
            "test_count": regression_fit["test_count"],
            "test_series_conditions_satisfied": True,
            "test_temperature_range_c": regression_fit["test_temperature_range_c"],
            "interpolation_window_points": regression_fit["interpolation_window_points"],
            "application_conditions": {
                "calibration_exposure_sides": regression_fit["exposure_sides"],
                "member_exposure_sides": 4,
                "same_protection_system": True,
                "same_protection_material_verified": True,
                "stickability_demonstrated_for_member": False,
            },
        }
    )
    record(
        "Clause 12.6.2.3 interior test geometry accepted",
        int(regression_check["results"]["inside_interpolation_window"]),
        1,
    )
    record(
        "Clause 12.6.2.3 measured target temperature accepted",
        int(regression_check["results"]["within_test_temperature_range"]),
        1,
    )
    record(
        "Clause 12.6.2.3 protection-system reuse conditions accepted",
        int(regression_check["results"]["application_conditions"]["conditions_satisfied"]),
        1,
    )
    fire_group = run_durability(
        {
            "check_type": "fire_three_sided_group",
            "members": [
                {
                    "concrete_density_kg_m3": 2000,
                    "concrete_area_excluding_voids_mm2": 150000,
                    "tributary_width_mm": 1000,
                    "rib_void_condition": "open",
                },
                {
                    "concrete_density_kg_m3": 2500,
                    "concrete_area_excluding_voids_mm2": 187500,
                    "tributary_width_mm": 1000,
                    "rib_void_condition": "open",
                },
            ],
        }
    )["results"]
    record(
        "Clause 12.9(a)(i) concrete density ratio at limit",
        fire_group["concrete_density_ratio"],
        1.25,
    )
    record(
        "Clause 12.9(a)(ii) effective thickness ratio at limit",
        fire_group["effective_thickness_ratio"],
        1.25,
    )
    record("Clause 12.9(b) consistent open rib voids", int(fire_group["group_satisfied"]), 1)
    fire_connection = run_durability(
        {
            "check_type": "fire_connection_protection",
            "framing_members": [
                {"required_protection_thickness_mm": 25},
                {"required_protection_thickness_mm": 40},
                {"required_protection_thickness_mm": 35},
            ],
            "connection_components": [
                {
                    "component_id": "bolt-heads",
                    "component_type": "bolt_head",
                    "provided_protection_thickness_mm": 40,
                    "protection_maintained_over_component": True,
                },
                {
                    "component_id": "welds",
                    "component_type": "weld",
                    "provided_protection_thickness_mm": 40,
                    "protection_maintained_over_component": True,
                },
                {
                    "component_id": "splice-plates",
                    "component_type": "splice_plate",
                    "provided_protection_thickness_mm": 40,
                    "protection_maintained_over_component": True,
                },
            ],
        }
    )["results"]
    record(
        "Clause 12.10.1 maximum framing-member protection thickness",
        fire_connection["required_protection_thickness_mm"],
        40,
    )
    record(
        "Clause 12.10.1 protection maintained over connection components",
        int(fire_connection["check_satisfied"]),
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
