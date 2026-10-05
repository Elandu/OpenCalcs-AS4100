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
from .erection import run_erection
from .fabrication import run_fabrication
from .materials import run_materials
from .members import run_members
from .testing import run_testing
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

    design_service_temperature = run_durability(
        {
            "check_type": "design_service_temperature",
            "lodmat_temperature_c": 6,
            "lodmat_assessment_verified": True,
            "lodmat_evidence_reference": "BENCHMARK-FIGURE-10.3.2-SITE-01",
            "especially_low_local_ambient_conditions_verified": True,
            "special_local_temperature_evidence_reference": "BENCHMARK-LOW-TEMP-01",
            "record_based_low_temperature_c": -2,
            "critical_structure_and_temperature_records_verified": True,
            "recorded_temperature_evidence_reference": "BENCHMARK-TEMPERATURE-RECORD-01",
            "artificial_cooling_minimum_temperature_c": -25,
            "artificial_cooling_below_basic_temperature_verified": True,
            "artificial_cooling_evidence_reference": "BENCHMARK-COOLING-01",
        }
    )
    service_temperature = design_service_temperature["results"]
    record(
        "Clause 10.3.2(a) local ambient temperature adjustment",
        service_temperature["lodmat_temperature_c"]
        + service_temperature["special_local_ambient_adjustment_c"],
        1,
    )
    record(
        "Clause 10.3.2(b) verified colder record controls basic temperature",
        service_temperature["basic_design_service_temperature_c"],
        -2,
    )
    record(
        "Clause 10.3.3 artificial cooling sets part service temperature",
        service_temperature["design_service_temperature_c"],
        -25,
    )
    impact_test = run_durability(
        {
            "check_type": "nonconforming_steel_impact_test",
            "plate_thickness_mm": 8,
            "specimen_thickness_mm": 7.5,
            "absorbed_energy_j": [15, 20.25, 25.5],
            "grade_standard_has_no_minimum_impact_properties_verified": True,
            "permissible_temperature_unknown_or_warmer_than_design_verified": True,
            "mock_up_grade_dimensions_and_strain_verified": True,
            "three_specimens_from_maximum_strain_region_verified": True,
            "tested_at_design_service_temperature_verified": True,
            "specimen_thickness_selection_verified": True,
            "evidence_reference": "BENCHMARK-CHARPY-REPORT-01",
        }
    )["results"]
    record(
        "Clause 10.4.3.4(e) sub-size specimen energy factor",
        impact_test["energy_reduction_factor"],
        7.5 / 10,
    )
    record(
        "Clause 10.4.3.4(d)/(e) proportional average energy threshold",
        impact_test["required_average_energy_j"],
        27 * 7.5 / 10,
    )
    record(
        "Clause 10.4.3.4(d)/(e) proportional individual minimum threshold",
        impact_test["required_minimum_single_energy_j"],
        20 * 7.5 / 10,
    )
    record(
        "Clause 10.4.3.4 sub-size energy example acceptance",
        int(impact_test["check_satisfied"]),
        1,
    )
    specified_impact_test = run_durability(
        {
            "check_type": "specified_impact_properties_test",
            "plate_thickness_mm": 8,
            "specimen_thickness_mm": 7.5,
            "absorbed_energy_j": [13.5, 18, 22.5],
            "specified_minimum_average_energy_j": 24,
            "specified_minimum_single_energy_j": 18,
            "grade_standard_minimums_verified": True,
            "grade_standard_reference": "BENCHMARK-PRODUCT-STANDARD-CHARPY-01",
            "permissible_temperature_unknown_or_warmer_than_design_verified": True,
            "mock_up_grade_dimensions_and_strain_verified": True,
            "three_specimens_from_maximum_strain_region_verified": True,
            "tested_at_design_service_temperature_verified": True,
            "specimen_thickness_selection_verified": True,
            "evidence_reference": "BENCHMARK-CHARPY-REPORT-02",
        }
    )["results"]
    record(
        "Clause 10.4.3.4(c)/(e) supplied average minimum sub-size reduction",
        specified_impact_test["required_average_energy_j"],
        24 * 7.5 / 10,
    )
    record(
        "Clause 10.4.3.4(c)/(e) supplied individual minimum sub-size reduction",
        specified_impact_test["required_minimum_single_energy_j"],
        18 * 7.5 / 10,
    )
    record(
        "Clause 10.4.3.4(c) supplied product-standard minimum acceptance",
        int(specified_impact_test["check_satisfied"]),
        1,
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

    group1_evidence = {
        "detail_conditions_verified": True,
        "stress_direction_verified": True,
        "detail_evidence_reference": "VERIFY-FABRICATION-01",
        "stress_direction_evidence_reference": "VERIFY-STRESS-01",
    }
    rolled_detail = run_durability(
        {
            "check_type": "fatigue_group1_detail",
            "detail_number": 1,
            "surface_and_rolling_flaws_removed_verified": True,
            **group1_evidence,
        }
    )["results"]
    record(
        "Table 11.5.1(A) rolled and extruded products detail category",
        rolled_detail["detail_category_mpa"],
        160,
    )
    bolted_detail = run_durability(
        {
            "check_type": "fatigue_group1_detail",
            "detail_number": 4,
            "bolting_category": "8.8/TF",
            "one_sided_coverplate_connection": False,
            **group1_evidence,
        }
    )["results"]
    record(
        "Table 11.5.1(A) 8.8/TF bolted connection stress area",
        int(bolted_detail["stress_area_basis"] == "gross_section"),
        1,
    )
    gas_cut_detail = run_durability(
        {
            "check_type": "fatigue_group1_detail",
            "detail_number": 7,
            "machine_or_manual_gas_cut_verified": True,
            "edge_discontinuities_removed_in_stress_direction_verified": True,
            **group1_evidence,
        }
    )["results"]
    record(
        "Table 11.5.1(A) gas-cut edge detail category",
        gas_cut_detail["detail_category_mpa"],
        125,
    )

    bolt_slip_detail = run_durability(
        {
            "check_type": "fatigue_bolt_detail",
            "detail_number": 41,
            "bolting_category": "8.8/TB",
            "joint_slip_assessment_verified": True,
            "joint_shear_causes_slip": True,
            "joint_slip_evidence_reference": "VERIFY-SLIP-01",
            "detail_conditions_verified": True,
            "stress_direction_verified": True,
            "detail_evidence_reference": "VERIFY-BOLT-01",
            "stress_direction_evidence_reference": "VERIFY-STRESS-01",
        }
    )["results"]
    record(
        "Table 11.5.1(C) 8.8/TB shear-bolt category",
        bolt_slip_detail["detail_category_mpa"],
        100,
    )
    bolt_tension_detail = run_durability(
        {
            "check_type": "fatigue_bolt_detail",
            "detail_number": 42,
            "prying_effects_assessed": True,
            "prying_assessment_reference": "VERIFY-PRYING-01",
            "detail_conditions_verified": True,
            "stress_direction_verified": True,
            "detail_evidence_reference": "VERIFY-BOLT-01",
            "stress_direction_evidence_reference": "VERIFY-STRESS-01",
        }
    )["results"]
    record(
        "Table 11.5.1(C) tension-bolt category",
        bolt_tension_detail["detail_category_mpa"],
        36,
    )

    detail_evidence = {
        "detail_conditions_verified": True,
        "stress_direction_verified": True,
        "weld_quality_verified": True,
        "weld_quality_basis": "AS/NZS 1554.1 SP",
        "weld_quality_evidence_reference": "VERIFY-WELD-QUALITY-01",
        "detail_evidence_reference": "VERIFY-DRAWING-01",
        "stress_direction_evidence_reference": "VERIFY-STRESS-01",
    }
    automatic_weld = run_durability(
        {
            "check_type": "fatigue_hollow_section_detail",
            "detail_number": 43,
            "hollow_section_form": "CHS",
            "no_stop_starts_verified": True,
            **detail_evidence,
        }
    )["results"]
    record(
        "Table 11.5.1(D) continuous automatic longitudinal weld category",
        automatic_weld["detail_category_mpa"],
        140,
    )
    circular_butt = run_durability(
        {
            "check_type": "fatigue_hollow_section_detail",
            "detail_number": 44,
            "hollow_section_form": "CHS",
            "wall_thickness_mm": 8,
            **detail_evidence,
        }
    )["results"]
    record(
        "Table 11.5.1(D) CHS butt-weld thickness boundary at 8 mm",
        circular_butt["detail_category_mpa"],
        90,
    )
    rectangular_fillet = run_durability(
        {
            "check_type": "fatigue_hollow_section_detail",
            "detail_number": 50,
            "hollow_section_form": "RHS",
            "wall_thickness_mm": 7.999,
            **detail_evidence,
        }
    )["results"]
    record(
        "Table 11.5.1(D) RHS intermediate-plate fillet weld below 8 mm",
        rectangular_fillet["detail_category_mpa"],
        36,
    )
    attachment = run_durability(
        {
            "check_type": "fatigue_hollow_section_detail",
            "detail_number": 48,
            "hollow_section_form": "RHS",
            "section_width_parallel_to_stress_mm": 100,
            "non_load_carrying_verified": True,
            **detail_evidence,
        }
    )["results"]
    record(
        "Table 11.5.1(D) non-load-carrying attachment width limit",
        attachment["detail_category_mpa"],
        71,
    )

    welded_conditions = {
        "detail_conditions_verified": True,
        "stress_direction_verified": True,
        "weld_quality_verified": True,
        "continuous_automatic_weld_both_sides_verified": True,
        "no_unrepaired_stop_starts_verified": True,
        "continuous_automatic_backing_butt_weld_verified": True,
        "continuous_backing_bar_verified": True,
        "continuous_welds_both_sides_verified": True,
        "stop_start_positions_present": True,
        "continuous_weld_one_side_verified": True,
        "intermittent_longitudinal_weld_verified": True,
        "cope_hole_not_filled_verified": True,
        "cope_hole_present": False,
        "full_penetration_weld_verified": True,
        "weld_runoff_tabs_removed_verified": True,
        "weld_ends_ground_flush_in_stress_direction_verified": True,
        "reinforcement_ground_flush_verified": True,
        "ndt_100_percent_verified": True,
        "weld_free_of_exposed_porosity_verified": True,
        "welds_from_both_sides_verified": True,
        "plate_girder_welded_before_assembly_verified": True,
        "backing_bar_verified": True,
        "cruciform_ndt_and_defect_free_verified": True,
        "lap_weld_conditions_verified": True,
        "non_load_carrying_verified": True,
        "smooth_transition_verified": True,
        "failure_location_verified": True,
        "cover_plate_conditions_verified": True,
        "weld_quality_basis": "AS/NZS 1554.1 SP",
        "weld_process": "automatic",
        "transition_slope": 0.2,
        "backing_weld_end_distance_mm": 20,
        "intermediate_plate_thickness_mm": 10,
        "maximum_plate_misalignment_mm": 1,
        "stress_range_area_basis": "plate_area",
        "lap_capacity_hierarchy": "weld_and_overlap_gt_main",
        "lap_taper_slope": 0.5,
        "overlap_width_mm": 70,
        "main_plate_thickness_mm": 10,
        "weld_end_distance_mm": 20,
        "attachment_weld_length_mm": 40,
        "transition_radius_mm": 4,
        "section_width_mm": 12,
        "plate_thickness_mm": 12,
        "combined_web_bending_and_shear": False,
        "principal_stress_range_verified": True,
        "flange_thickness_mm": 25,
        "cover_plate_thickness_mm": 25,
        "cover_plate_wider_than_flange": False,
        "cover_plate_end_weld_present": False,
        "failure_location": "base_material",
        "detail_evidence_reference": "VERIFY-WELD-DETAIL-01",
        "stress_direction_evidence_reference": "VERIFY-STRESS-01",
        "weld_quality_evidence_reference": "VERIFY-WELD-QUALITY-01",
    }

    def welded_detail(detail, **changes):
        inputs = {
            "check_type": "fatigue_welded_detail",
            "detail_number": detail,
            **welded_conditions,
            **changes,
        }
        return run_durability(inputs)["results"]

    full_penetration_125 = welded_detail(
        8,
        continuous_automatic_weld_both_sides_verified=True,
        weld_quality_basis="AS/NZS 1554.5",
    )
    record(
        "Table 11.5.1(B) automatic two-sided longitudinal weld category",
        full_penetration_125["detail_category_mpa"],
        125,
    )
    manual_longitudinal = welded_detail(12, weld_process="manual")
    record(
        "Table 11.5.1(B) manual longitudinal weld category",
        manual_longitudinal["detail_category_mpa"],
        100,
    )
    cope_hole_splice = welded_detail(20, cope_hole_present=True)
    record(
        "Table 11.5.1(B) transverse splice with unfilled cope hole",
        cope_hole_splice["detail_category_mpa"],
        71,
    )
    taper_limit = welded_detail(22, transition_slope=0.4)
    record(
        "Table 11.5.1(B) butt-weld taper upper boundary",
        taper_limit["detail_category_mpa"],
        80,
    )
    cruciform = welded_detail(26, maximum_plate_misalignment_mm=1.49)
    record(
        "Table 11.5.1(B) cruciform misalignment below 0.15t",
        cruciform["detail_category_mpa"],
        71,
    )
    attachment_length = welded_detail(32, attachment_weld_length_mm=100)
    record(
        "Table 11.5.1(B) longitudinal attachment length at 100 mm",
        attachment_length["detail_category_mpa"],
        71,
    )
    gusset_transition = welded_detail(33, transition_radius_mm=1, section_width_mm=6)
    record(
        "Table 11.5.1(B) gusset transition radius ratio at 1/6",
        gusset_transition["detail_category_mpa"],
        71,
    )
    cover_plate = welded_detail(38)
    record(
        "Table 11.5.1(B) cover plate with flange and plate at 25 mm",
        cover_plate["detail_category_mpa"],
        50,
    )
    shear_weld = welded_detail(39)
    record(
        "Table 11.5.1(B) shear weld detail stress-area classification",
        int(
            shear_weld["stress_type"] == "shear"
            and shear_weld["stress_area_basis"] == "weld_throat_area"
        ),
        1,
    )
    shear_stud = welded_detail(40, failure_location="weld")
    record(
        "Table 11.5.1(B) welded stud shear stress-area classification",
        int(
            shear_stud["stress_type"] == "shear"
            and shear_stud["stress_area_basis"] == "nominal_stud_section"
        ),
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
    flat_plate_section = run_members(
        {
            "operation": "section_moment_capacity",
            "yield_strength_mpa": 250,
            "elastic_modulus_mm3": 100000,
            "plastic_modulus_mm3": 130000,
            "plate_elements": [
                {
                    "element_id": "web",
                    "width_mm": 1100,
                    "thickness_mm": 10,
                    "edges": "both",
                    "stress": "internal_gradient",
                    "residual": "HR",
                },
                {
                    "element_id": "compression_flange",
                    "width_mm": 250,
                    "thickness_mm": 10,
                    "edges": "one",
                    "stress": "uniform",
                    "residual": "HR",
                },
            ],
        }
    )
    record(
        "Clause 5.2.2 selects maximum plate slenderness/yield-limit ratio",
        flat_plate_section["values"]["governing_element_slenderness_to_yield_limit_ratio"],
        25 / 16,
    )
    record(
        "Clause 5.2.1 nominal section capacity from governing Ze",
        flat_plate_section["values"]["nominal_section_moment_capacity_knm"],
        16,
    )
    major_axis_bending_design = run_members(
        {
            "operation": "bending_design",
            "method": "elastic_major_axis",
            "action_knm": 81,
            "nominal_section_capacity_knm": 100,
            "nominal_member_capacity_knm": 90,
        }
    )
    record(
        "Clause 5.1 elastic major-axis design section capacity",
        major_axis_bending_design["values"]["design_section_moment_capacity_knm"],
        90,
    )
    record(
        "Clause 5.1 elastic major-axis design member capacity",
        major_axis_bending_design["values"]["design_member_moment_capacity_knm"],
        81,
    )
    minor_axis_bending_design = run_members(
        {
            "operation": "bending_design",
            "method": "elastic_minor_axis",
            "action_knm": 45,
            "nominal_section_capacity_knm": 50,
        }
    )
    record(
        "Clause 5.1 elastic minor-axis design section capacity",
        minor_axis_bending_design["values"]["design_section_moment_capacity_knm"],
        45,
    )
    plastic_bending_design = run_members(
        {
            "operation": "bending_design",
            "method": "plastic",
            "action_knm": 90,
            "nominal_section_capacity_knm": 100,
            "hinge_sections_compact_verified": True,
            "full_lateral_restraint_verified": True,
            "web_clause_5_10_6_satisfied": True,
        }
    )
    record(
        "Clause 5.1 plastic-method design section capacity",
        plastic_bending_design["values"]["design_section_moment_capacity_knm"],
        90,
    )
    record(
        "Clause 5.1 plastic-method eligibility gates",
        int(plastic_bending_design["values"]["plastic_method_prerequisites_satisfied"]),
        1,
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
    layout_holes = run_connections(
        {
            "check_type": "hole_deduction_layout",
            "plate_width_mm": 200,
            "thickness_mm": 10,
            "flat_uniform_plate_and_complete_hole_layout_verified": True,
            "design_action_axis_verified": True,
            "holes": [
                {
                    "hole_id": "A",
                    "longitudinal_mm": 0,
                    "transverse_mm": 50,
                    "gross_hole_width_mm": 22,
                },
                {
                    "hole_id": "B",
                    "longitudinal_mm": 40,
                    "transverse_mm": 100,
                    "gross_hole_width_mm": 22,
                },
                {
                    "hole_id": "C",
                    "longitudinal_mm": 0,
                    "transverse_mm": 150,
                    "gross_hole_width_mm": 22,
                },
            ],
        }
    )
    record(
        "Clause 9.1.10.3 maximum progressive zig-zag deduction width",
        layout_holes["intermediate"]["zigzag_path"]["net_deduction_width_mm"],
        50,
    )
    record(
        "Clause 9.1.10.2 straight-versus-zig-zag net area",
        layout_holes["intermediate"]["net_area_mm2"],
        1500,
    )
    angle_holes = run_connections(
        {
            "check_type": "angle_hole_deduction",
            "gross_area_mm2": 4000,
            "thickness_mm": 10,
            "straight_hole_width_sum_mm": 25,
            "straight_hole_width_sum_verified": True,
            "angle_geometry_and_back_marks_verified": True,
            "candidate_paths_complete_and_ordered_verified": True,
            "candidate_paths": [
                {
                    "path_id": "opposite-legs",
                    "holes": [
                        {
                            "hole_id": "A",
                            "angle_leg_id": "leg_1",
                            "longitudinal_mm": 0,
                            "back_mark_mm": 20,
                            "gross_hole_width_mm": 20,
                        },
                        {
                            "hole_id": "B",
                            "angle_leg_id": "leg_2",
                            "longitudinal_mm": 40,
                            "back_mark_mm": 30,
                            "gross_hole_width_mm": 20,
                        },
                    ],
                }
            ],
        }
    )["intermediate"]
    angle_pair = angle_holes["candidate_paths"][0]["stagger_pairs"][0]
    record(
        "Figure 9.1.10.3(B) opposite-leg gauge from back marks",
        angle_pair["gauge_mm"],
        20 + 30 - 10,
    )
    record(
        "Clause 9.1.10.3(B) stagger-corrected angle net width",
        angle_holes["governing_deduction_width_mm"],
        40 - 40**2 / (4 * 40),
    )
    record(
        "Clause 9.1.10 angle net area after cross-leg deduction",
        angle_holes["net_area_mm2"],
        4000 - 30 * 10,
    )
    angle_layout = run_connections(
        {
            "check_type": "angle_hole_deduction_layout",
            "gross_area_mm2": 1900,
            "thickness_mm": 10,
            "leg_1_width_mm": 100,
            "leg_2_width_mm": 100,
            "angle_geometry_and_back_marks_verified": True,
            "complete_angle_hole_layout_and_action_axis_verified": True,
            "holes": [
                {
                    "hole_id": "A",
                    "angle_leg_id": "leg_1",
                    "longitudinal_mm": 0,
                    "back_mark_mm": 70,
                    "gross_hole_width_mm": 20,
                },
                {
                    "hole_id": "B",
                    "angle_leg_id": "leg_1",
                    "longitudinal_mm": 30,
                    "back_mark_mm": 40,
                    "gross_hole_width_mm": 20,
                },
                {
                    "hole_id": "C",
                    "angle_leg_id": "leg_2",
                    "longitudinal_mm": 60,
                    "back_mark_mm": 30,
                    "gross_hole_width_mm": 18,
                },
                {
                    "hole_id": "D",
                    "angle_leg_id": "leg_2",
                    "longitudinal_mm": 90,
                    "back_mark_mm": 60,
                    "gross_hole_width_mm": 18,
                },
            ],
        }
    )["intermediate"]
    record(
        "Clause 9.1.10.3(B) complete two-leg angle path deduction width",
        angle_layout["zigzag_path"]["net_deduction_width_mm"],
        76 - (30**2 / (4 * 30) + 30**2 / (4 * 60) + 30**2 / (4 * 30)),
    )
    record(
        "Clause 9.1.10 two-leg angle net area",
        angle_layout["net_area_mm2"],
        1900 - 57.25 * 10,
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
                "net_hole_layout_preserves_major_axis_verified": True,
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
                "net_hole_layout_preserves_major_axis_verified": True,
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
                "net_hole_layout_preserves_major_axis_verified": True,
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
    compact_i_out_of_plane = run_members(
        {
            "operation": "interaction",
            "axial_mode": "compression",
            "section_axial_capacity_kn": 1000,
            "member_axial_x_kn": 800,
            "member_axial_y_kn": 1000,
            "section_moment_x_knm": 100,
            "section_moment_y_knm": 50,
            "member_moment_x_knm": 70,
            "axial_action_kn": 300,
            "moment_x_knm": 45,
            "moment_y_knm": 0,
            "compact_doubly_symmetric_i_verified": True,
            "compression_form_factor_one_verified": True,
            "compact_i_out_of_plane_alternative": True,
            "uniform_moment_member_capacity_knm": 25,
            "uniform_moment_member_capacity_verified": True,
            "uniform_moment_member_capacity_reference": "Clause 5.6 independent check",
            "torsion_constant_j_mm4": 200000,
            "warping_constant_iw_mm6": 100_000_000_000,
            "section_second_moment_x_mm4": 100_000_000,
            "section_second_moment_y_mm4": 20_000_000,
            "gross_area_mm2": 2000,
            "torsional_restraint_spacing_mm": 2000,
            "torsional_section_properties_verified": True,
            "beta_m": 1,
            "no_transverse_loads_verified": True,
            "both_end_lateral_restraints_verified": True,
        }
    )
    record(
        "Clause 8.4.4.1 compact-I alpha_bc, hand arithmetic",
        compact_i_out_of_plane["values"]["alpha_bc"],
        300 / 97,
        1e-12,
    )
    record(
        "Clause 8.4.4.1 elastic torsional buckling capacity, hand arithmetic",
        compact_i_out_of_plane["values"]["elastic_torsional_buckling_capacity_kn"],
        1089.13370009078,
        1e-9,
    )
    record(
        "Clause 8.4.4.1 compact-I nominal out-of-plane moment, hand arithmetic",
        compact_i_out_of_plane["values"]["out_of_plane_x_knm"],
        52.590445603195036,
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
    for constant, expected in [
        (-1, 1.000),
        (-0.5, 0.989),
        (0, 0.978),
        (0.5, 0.967),
        (1, 0.956),
    ]:
        amended_row = run_members(
            {
                "operation": "compression",
                "yield_strength_mpa": 250,
                "gross_area_mm2": 1000,
                "net_area_mm2": 1000,
                "effective_area_mm2": 1000,
                "effective_length_x_mm": 200,
                "effective_length_y_mm": 200,
                "radius_x_mm": 10,
                "radius_y_mm": 10,
                "section_constant_x": constant,
                "section_constant_y": constant,
                "action_kn": 100,
                "geometry": "doubly_symmetric",
            }
        )
        record(
            f"Amd 1 Table 6.3.3(C), lambda=20, alpha_b={constant}",
            amended_row["values"]["reduction_x"],
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
    idealized_restraint_cases = {
        "braced_fixed_fixed": 0.7,
        "braced_top_pinned_bottom_fixed": 0.85,
        "braced_pinned_pinned": 1.0,
        "sway_top_fixed_bottom_fixed": 1.2,
        "sway_top_free_bottom_fixed": 2.2,
        "sway_top_fixed_bottom_pinned": 2.2,
    }
    idealized_fixed_fixed = None
    for case, expected_factor in idealized_restraint_cases.items():
        idealized_result = run_design_actions(
            {
                "operation": "idealized_member_buckling",
                "second_moment_mm4": 8e6,
                "member_length_mm": 4000,
                "idealized_end_restraint_case": case,
                "idealized_end_restraint_verified": True,
                "end_restraint_evidence_reference": "VERIFY-FIGURE-4-6-3-2",
                "member_length_centre_to_centre_verified": True,
                "member_length_evidence_reference": "VERIFY-MEMBER-LENGTH-01",
            }
        )
        record(
            f"Figure 4.6.3.2 idealized restraint factor: {case}",
            idealized_result["values"]["effective_length_factor"],
            expected_factor,
        )
        if case == "braced_fixed_fixed":
            idealized_fixed_fixed = idealized_result
    record(
        "Clauses 4.6.2/4.6.3.2 fixed-fixed Euler load, hand arithmetic",
        idealized_fixed_fixed["values"]["elastic_buckling_load_kn"],
        2014.2049798141545,
        1e-8,
    )

    chart_buckling = run_design_actions(
        {
            "operation": "frame_chart_member_buckling",
            "member_id": "VERIFY-COL-CHART-01",
            "frame_type": "braced",
            "frame_type_verified": True,
            "rigid_jointed_frame_verified": True,
            "frame_classification_evidence_reference": "VERIFY-FRAME-CLASSIFICATION",
            "stiffness_ratio_at_end_1": 0.7,
            "stiffness_ratio_at_end_2": 1.2,
            "stiffness_ratios_verified": True,
            "stiffness_ratio_evidence_reference": "VERIFY-END-RATIOS",
            "effective_length_factor": 0.85,
            "effective_length_factor_chart_verified": True,
            "chart_evidence_reference": "VERIFY-FIGURE-4-6-3-3",
            "second_moment_mm4": 8e6,
            "second_moment_about_buckling_axis_verified": True,
            "section_evidence_reference": "VERIFY-SECTION-01",
            "member_length_mm": 4000,
            "member_length_centre_to_centre_verified": True,
            "member_length_evidence_reference": "VERIFY-MEMBER-LENGTH-01",
        }
    )
    chart_buckling_values = chart_buckling["values"]
    record(
        "Clause 4.6.3.3 braced chart factor branch range",
        int(chart_buckling["checks"][4]["satisfied"]),
        1,
    )
    record(
        "Clause 4.6.2 Euler load using assessed Figure 4.6.3.3 factor",
        chart_buckling_values["elastic_buckling_load_kn"],
        1366.0352112234405,
        1e-9,
    )

    triangulated_buckling = run_design_actions(
        {
            "operation": "triangulated_member_buckling",
            "member_id": "VERIFY-TRUSS-MEMBER-01",
            "triangulated_structure_verified": True,
            "triangulated_structure_evidence_reference": "VERIFY-TRUSS-01",
            "second_moment_mm4": 4.5e6,
            "second_moment_about_buckling_axis_verified": True,
            "section_evidence_reference": "VERIFY-TRUSS-SECTION-01",
            "member_length_between_intersections_mm": 3000,
            "member_length_between_intersections_verified": True,
            "member_geometry_evidence_reference": "VERIFY-TRUSS-GEOMETRY-01",
            "effective_length_mm": 2400,
            "effective_length_assessment_verified": True,
            "effective_length_evidence_reference": "VERIFY-TRUSS-EFFECTIVE-LENGTH-01",
            "rational_buckling_analysis_consistent_with_appendix_g_verified": False,
        }
    )
    triangulated_values = triangulated_buckling["values"]
    record(
        "Clause 4.6.3.5 triangulated member effective-length minimum",
        triangulated_values["effective_length_mm"],
        3000,
    )
    record(
        "Clause 4.6.2 Euler load at triangulated member length minimum",
        triangulated_values["elastic_buckling_load_kn"],
        986.9604401089358,
        1e-9,
    )

    braced_frame_factor = run_design_actions(
        {
            "operation": "braced_frame_buckling_factor",
            "rectangular_frame_verified": True,
            "all_members_braced_verified": True,
            "regular_loading_verified": True,
            "beam_axial_forces_negligible_verified": True,
            "frame_assessment_evidence_reference": "VERIFY-BRACED-FRAME",
            "design_load_set_id": "VERIFY-ULS-BRACED",
            "design_load_set_actions_verified": True,
            "design_load_set_evidence_reference": "VERIFY-ULS-BRACED-ACTIONS",
            "columns": [
                {
                    "column_id": "VERIFY-BR-COL-01",
                    "elastic_member_buckling_load_n_omb_kn": 1500,
                    "design_axial_force_n_star_kn": 300,
                    "member_buckling_load_verified": True,
                    "design_axial_force_verified": True,
                    "evidence_reference": "VERIFY-BR-COL-01-LOADS",
                },
                {
                    "column_id": "VERIFY-BR-COL-02",
                    "elastic_member_buckling_load_n_omb_kn": 800,
                    "design_axial_force_n_star_kn": 400,
                    "member_buckling_load_verified": True,
                    "design_axial_force_verified": True,
                    "evidence_reference": "VERIFY-BR-COL-02-LOADS",
                },
            ],
            "all_columns_in_frame_listed_verified": True,
            "column_list_evidence_reference": "VERIFY-BRACED-COLUMNS",
        }
    )
    record(
        "Clause 4.7.2.1 braced-frame lowest column load factor",
        braced_frame_factor["values"]["lambda_c"],
        2.0,
    )

    sway_frame_factor = run_design_actions(
        {
            "operation": "sway_frame_buckling_factor",
            "rectangular_frame_verified": True,
            "sway_member_classification_verified": True,
            "regular_loading_verified": True,
            "beam_axial_forces_negligible_verified": True,
            "frame_assessment_evidence_reference": "VERIFY-SWAY-FRAME",
            "design_load_set_id": "VERIFY-ULS-SWAY",
            "design_load_set_actions_verified": True,
            "design_load_set_evidence_reference": "VERIFY-ULS-SWAY-ACTIONS",
            "storeys": [
                {
                    "storey_id": "VERIFY-LEVEL-1",
                    "columns": [
                        {
                            "column_id": "VERIFY-SW-COL-1A",
                            "elastic_member_buckling_load_n_oms_kn": 1000,
                            "design_axial_force_n_star_kn": 400,
                            "member_length_mm": 4000,
                            "member_buckling_load_verified": True,
                            "design_axial_force_verified": True,
                            "member_length_verified": True,
                            "evidence_reference": "VERIFY-SW-COL-1A-LOADS",
                        },
                        {
                            "column_id": "VERIFY-SW-COL-1B",
                            "elastic_member_buckling_load_n_oms_kn": 600,
                            "design_axial_force_n_star_kn": -200,
                            "member_length_mm": 4000,
                            "member_buckling_load_verified": True,
                            "design_axial_force_verified": True,
                            "member_length_verified": True,
                            "evidence_reference": "VERIFY-SW-COL-1B-LOADS",
                        },
                    ],
                    "all_columns_in_storey_listed_verified": True,
                    "column_list_evidence_reference": "VERIFY-LEVEL-1-COLUMNS",
                },
                {
                    "storey_id": "VERIFY-LEVEL-2",
                    "columns": [
                        {
                            "column_id": "VERIFY-SW-COL-2A",
                            "elastic_member_buckling_load_n_oms_kn": 900,
                            "design_axial_force_n_star_kn": 300,
                            "member_length_mm": 3000,
                            "member_buckling_load_verified": True,
                            "design_axial_force_verified": True,
                            "member_length_verified": True,
                            "evidence_reference": "VERIFY-SW-COL-2A-LOADS",
                        }
                    ],
                    "all_columns_in_storey_listed_verified": True,
                    "column_list_evidence_reference": "VERIFY-LEVEL-2-COLUMNS",
                },
            ],
            "all_storeys_in_frame_listed_verified": True,
            "storey_list_evidence_reference": "VERIFY-SWAY-STOREYS",
        }
    )
    sway_values = sway_frame_factor["values"]
    record(
        "Clause 4.7.2.2 sway-storey factor with tension column",
        sway_values["storeys"][0]["lambda_ms"],
        8.0,
    )
    record(
        "Clause 4.7.2.2 whole-frame lowest storey factor",
        sway_values["lambda_c"],
        3.0,
    )

    def frame_stiffness_inputs(frame_type="braced", column_base_condition="not_column_base"):
        return {
            "operation": "rectangular_frame_stiffness_ratio",
            "frame_type": frame_type,
            "member_under_consideration_id": "COL-01",
            "compression_members": [
                {
                    "member_id": "COL-01",
                    "second_moment_mm4": 8e6,
                    "member_length_mm": 4000,
                    "rigid_connection_at_joint_verified": True,
                    "stiffness_evidence_reference": "VERIFY-COL-01",
                },
                {
                    "member_id": "COL-02",
                    "second_moment_mm4": 12e6,
                    "member_length_mm": 6000,
                    "rigid_connection_at_joint_verified": True,
                    "stiffness_evidence_reference": "VERIFY-COL-02",
                },
            ],
            "compression_members_at_joint_complete_verified": True,
            "compression_members_evidence_reference": "VERIFY-JOINT-COLUMNS",
            "beams": [
                {
                    "beam_id": "BEAM-01",
                    "second_moment_mm4": 10e6,
                    "member_length_mm": 5000,
                    "near_end_rigid_connection_verified": True,
                    "far_end_fixity": "pinned",
                    "far_end_fixity_verified": True,
                    "stiffness_evidence_reference": "VERIFY-BEAM-01",
                },
                {
                    "beam_id": "BEAM-02",
                    "second_moment_mm4": 6e6,
                    "member_length_mm": 3000,
                    "near_end_rigid_connection_verified": True,
                    "far_end_fixity": "rigidly_connected_to_column",
                    "far_end_fixity_verified": True,
                    "stiffness_evidence_reference": "VERIFY-BEAM-02",
                },
            ],
            "beams_at_joint_complete_verified": True,
            "beams_evidence_reference": "VERIFY-JOINT-BEAMS",
            "rectangular_frame_geometry_verified": True,
            "regular_loading_verified": True,
            "beam_axial_forces_negligible_verified": True,
            "frame_assessment_evidence_reference": "VERIFY-FRAME-BASIS",
            "column_base_condition": column_base_condition,
            "column_base_condition_verified": True,
            "column_base_evidence_reference": "VERIFY-COLUMN-BASE",
        }

    stiffness_modifiers = {
        "braced": {"pinned": 1.5, "rigidly_connected_to_column": 1.0, "fixed": 2.0},
        "sway": {"pinned": 0.5, "rigidly_connected_to_column": 1.0, "fixed": 0.67},
    }
    for frame_type, fixity_factors in stiffness_modifiers.items():
        for far_end_fixity, expected_beta in fixity_factors.items():
            stiffness_inputs = frame_stiffness_inputs(frame_type)
            stiffness_inputs["beams"][0]["far_end_fixity"] = far_end_fixity
            stiffness_result = run_design_actions(stiffness_inputs)
            record(
                f"Table 4.6.3.4 {frame_type} beam modifier: {far_end_fixity}",
                stiffness_result["values"]["beams"][0]["beta_e"],
                expected_beta,
            )

    frame_stiffness = run_design_actions(frame_stiffness_inputs())
    frame_stiffness_values = frame_stiffness["values"]
    record(
        "Clause 4.6.3.4 connected compression-member stiffness sum",
        frame_stiffness_values["compression_stiffness_sum_mm3"],
        4000,
        1e-12,
    )
    record(
        "Clause 4.6.3.4 beta-adjusted beam stiffness sum",
        frame_stiffness_values["weighted_beam_stiffness_sum_mm3"],
        5000,
        1e-12,
    )
    record(
        "Clause 4.6.3.4 rectangular-frame end stiffness ratio",
        frame_stiffness_values["stiffness_ratio_at_end_gamma"],
        0.8,
        1e-12,
    )
    rigid_base_gamma = run_design_actions(
        frame_stiffness_inputs(column_base_condition="rigidly_connected_to_footing")
    )
    record(
        "Clause 4.6.3.4 rigid-base minimum gamma check",
        int(rigid_base_gamma["values"]["minimum_gamma_satisfied"]),
        1,
    )
    unrestrained_base_gamma = run_design_actions(
        frame_stiffness_inputs(column_base_condition="not_rigidly_connected_to_footing")
    )
    record(
        "Clause 4.6.3.4 unrestrained-base minimum gamma boundary",
        int(unrestrained_base_gamma["values"]["minimum_gamma_satisfied"]),
        0,
    )
    plastic_equilibrium = run_design_actions(
        {
            "operation": "plastic_global_equilibrium",
            "actions": [
                {
                    "action_id": "LOAD-01",
                    "action_type": "applied_load",
                    "force_kn": [1, 2, 3],
                    "moment_knm": [0, 0, 0],
                    "position_mm": [2000, -1000, 500],
                    "evidence_reference": "VERIFY-LOAD-01",
                },
                {
                    "action_id": "SUPPORT-01",
                    "action_type": "support_reaction",
                    "force_kn": [-1, -2, -3],
                    "moment_knm": [4, 5.5, -5],
                    "position_mm": [0, 0, 0],
                    "evidence_reference": "VERIFY-REACTION-01",
                },
            ],
            "force_tolerance_kn": 0,
            "moment_tolerance_knm": 0,
            "boundary_conditions_verified": True,
            "boundary_conditions_evidence_reference": "VERIFY-SUPPORTS-01",
        }
    )
    record(
        "Clause 4.5.1 global force equilibrium, three axes",
        max(abs(component) for component in plastic_equilibrium["values"]["force_resultant_kn"]),
        0,
    )
    record(
        "Clause 4.5.1 global moment equilibrium with position cross force",
        max(abs(component) for component in plastic_equilibrium["values"]["moment_resultant_knm"]),
        0,
    )
    record(
        "Clause 4.5.1 boundary-condition evidence gate",
        int(plastic_equilibrium["checks"][2]["satisfied"]),
        1,
    )
    plastic_joint_equilibrium = run_design_actions(
        {
            "operation": "plastic_joint_equilibrium",
            "joints": [
                {
                    "joint_id": "JOINT-01",
                    "actions": [
                        {
                            "action_id": "MEMBER-END-01",
                            "action_type": "member_end_action",
                            "force_kn": [0, 2, 3],
                            "moment_knm": [0, 0, 0],
                            "position_offset_mm": [1000, 0, 0],
                            "evidence_reference": "VERIFY-MEMBER-END-01",
                        },
                        {
                            "action_id": "MEMBER-END-02",
                            "action_type": "member_end_action",
                            "force_kn": [4, 0, -3],
                            "moment_knm": [0, 0, 0],
                            "position_offset_mm": [0, 1000, 0],
                            "evidence_reference": "VERIFY-MEMBER-END-02",
                        },
                        {
                            "action_id": "LOAD-01",
                            "action_type": "applied_load",
                            "force_kn": [-4, -2, 0],
                            "moment_knm": [3, 3, 2],
                            "position_offset_mm": [0, 0, 0],
                            "evidence_reference": "VERIFY-NODE-LOAD-01",
                        },
                    ],
                    "joint_actions_complete_verified": True,
                    "joint_actions_evidence_reference": "VERIFY-JOINT-ACTIONS-01",
                }
            ],
            "force_tolerance_kn": 0,
            "moment_tolerance_knm": 0,
        }
    )
    joint_values = plastic_joint_equilibrium["values"]["joints"][0]
    record(
        "Clause 4.5.1 joint force equilibrium, three axes",
        max(abs(component) for component in joint_values["force_resultant_kn"]),
        0,
    )
    record(
        "Clause 4.5.1 joint moment equilibrium including position offsets",
        max(abs(component) for component in joint_values["moment_resultant_knm"]),
        0,
    )
    record(
        "Clause 4.5.1 member-end and action-completeness evidence gates",
        int(
            plastic_joint_equilibrium["checks"][2]["satisfied"]
            and plastic_joint_equilibrium["checks"][3]["satisfied"]
        ),
        1,
    )
    plastic_member_span = run_design_actions(
        {
            "operation": "plastic_member_span_equilibrium",
            "members": [
                {
                    "member_id": "BEAM-01",
                    "member_vector_mm": [4000, 0, 0],
                    "member_geometry_verified": True,
                    "member_geometry_evidence_reference": "VERIFY-BEAM-GEOMETRY-01",
                    "start_end_force_kn": [0, 20, -7.5],
                    "start_end_moment_knm": [0, 0, 0],
                    "start_end_evidence_reference": "VERIFY-BEAM-START-01",
                    "end_end_force_kn": [0, 20, -7.5],
                    "end_end_moment_knm": [-1, 2, -3],
                    "end_end_evidence_reference": "VERIFY-BEAM-END-01",
                    "span_actions": [
                        {
                            "action_id": "UDL-01",
                            "force_kn": [0, -40, 15],
                            "moment_knm": [0, 0, 0],
                            "position_offset_mm": [2000, 0, 0],
                            "evidence_reference": "VERIFY-UDL-RESULTANT-01",
                        },
                        {
                            "action_id": "COUPLE-01",
                            "force_kn": [0, 0, 0],
                            "moment_knm": [1, -2, 3],
                            "position_offset_mm": [2000, 0, 0],
                            "evidence_reference": "VERIFY-SPAN-COUPLE-01",
                        },
                    ],
                    "span_actions_complete_verified": True,
                    "span_actions_evidence_reference": "VERIFY-BEAM-LOAD-LIST-01",
                }
            ],
            "force_tolerance_kn": 0,
            "moment_tolerance_knm": 0,
            "all_members_listed_verified": True,
            "member_list_evidence_reference": "VERIFY-MEMBER-LIST-01",
        }
    )
    member_span_values = plastic_member_span["values"]["members"][0]
    record(
        "Clause 4.5.1 member span force equilibrium, three axes",
        max(abs(component) for component in member_span_values["force_resultant_kn"]),
        0,
    )
    record(
        "Clause 4.5.1 member span moment equilibrium with position cross force",
        max(abs(component) for component in member_span_values["moment_resultant_about_start_knm"]),
        0,
    )
    record(
        "Clause 4.5.1 member geometry and complete-list evidence gates",
        int(
            plastic_member_span["checks"][2]["satisfied"]
            and plastic_member_span["checks"][3]["satisfied"]
            and plastic_member_span["checks"][-1]["satisfied"]
        ),
        1,
    )
    plastic_support_conditions = run_design_actions(
        {
            "operation": "plastic_support_boundary_conditions",
            "supports": [
                {
                    "support_id": "SUPPORT-01",
                    "constraints": [
                        {
                            "dof": "ux",
                            "prescribed_translation_mm": 0,
                            "calculated_translation_mm": 0.01,
                            "tolerance_mm": 0.01,
                            "analysis_result_evidence_reference": "VERIFY-SUPPORT-UX-01",
                        },
                        {
                            "dof": "uy",
                            "prescribed_translation_mm": 0,
                            "calculated_translation_mm": 0,
                            "tolerance_mm": 0,
                            "analysis_result_evidence_reference": "VERIFY-SUPPORT-UY-01",
                        },
                        {
                            "dof": "rz",
                            "prescribed_rotation_rad": 0,
                            "calculated_rotation_rad": 0.001,
                            "tolerance_rad": 0.001,
                            "analysis_result_evidence_reference": "VERIFY-SUPPORT-RZ-01",
                        },
                    ],
                    "support_restraint_verified": True,
                    "support_evidence_reference": "VERIFY-SUPPORT-DRAWING-01",
                }
            ],
            "all_supports_listed_verified": True,
            "support_list_evidence_reference": "VERIFY-SUPPORT-SCHEDULE-01",
        }
    )
    support_constraints = plastic_support_conditions["values"]["supports"][0]["constraints"]
    record(
        "Clause 4.5.1 support translation residual at inclusive tolerance",
        abs(support_constraints[0]["residual"]),
        0.01,
    )
    record(
        "Clause 4.5.1 support rotation residual at inclusive tolerance",
        abs(support_constraints[2]["residual"]),
        0.001,
    )
    record(
        "Clause 4.5.1 support and restrained-DOF evidence gates",
        int(
            plastic_support_conditions["values"]["all_support_conditions_satisfied"]
            and plastic_support_conditions["checks"][3]["satisfied"]
        ),
        1,
    )
    alternative_ductility = run_design_actions(
        {
            "operation": "plastic_alternative_ductility_assessment",
            "members": [
                {
                    "component_id": "MEMBER-01",
                    "rotation_demand_rad": 0.018,
                    "rotation_capacity_rad": 0.02,
                    "rotation_demand_assessment_verified": True,
                    "rotation_capacity_assessment_verified": True,
                    "evidence_reference": "VERIFY-MEMBER-ROTATION-01",
                }
            ],
            "connections": [
                {
                    "component_id": "CONNECTION-01",
                    "rotation_demand_rad": 0.015,
                    "rotation_capacity_rad": 0.015,
                    "rotation_demand_assessment_verified": True,
                    "rotation_capacity_assessment_verified": True,
                    "evidence_reference": "VERIFY-CONNECTION-ROTATION-01",
                }
            ],
            "all_members_listed_verified": True,
            "member_list_evidence_reference": "VERIFY-MEMBER-LIST-01",
            "all_connections_listed_verified": True,
            "connection_list_evidence_reference": "VERIFY-CONNECTION-LIST-01",
            "structure_ductility_assessment_verified": True,
            "structure_ductility_evidence_reference": "VERIFY-STRUCTURE-DUCTILITY-01",
            "analysis_under_design_loading_verified": True,
            "analysis_evidence_reference": "VERIFY-DESIGN-LOAD-ANALYSIS-01",
        }
    )
    record(
        "Clause 4.5.2 alternative-route member rotation demand ratio",
        alternative_ductility["values"]["members"][0]["rotation_demand_to_capacity_ratio"],
        0.9,
    )
    record(
        "Clause 4.5.2 alternative-route connection rotation boundary",
        alternative_ductility["values"]["connections"][0]["rotation_demand_to_capacity_ratio"],
        1,
    )
    record(
        "Clause 4.5.2 alternative-route analysis and evidence gates",
        int(alternative_ductility["checked_conditions_satisfied"]),
        1,
    )
    plastic_limits = run_design_actions(
        {
            "operation": "plastic_analysis_limits",
            "materials": [
                {
                    "material_id": "GRADE-350",
                    "material_standard": "AS/NZS 3678",
                    "material_standard_verified": True,
                    "specified_yield_strength_mpa": 450,
                    "specified_tensile_strength_mpa": 540,
                    "yield_plateau_extension_in_yield_strains": 6,
                    "elongation_percent": 15,
                    "elongation_test_to_as1391_verified": True,
                    "strain_hardening_capability_verified": True,
                    "stress_strain_data_verified": True,
                    "evidence_reference": "VERIFY-MATERIAL-01",
                }
            ],
            "members": [
                {
                    "member_id": "PLASTIC-MEMBER-01",
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
                    "evidence_reference": "VERIFY-MEMBER-01",
                }
            ],
        }
    )
    record(
        "Clause 4.5.2(b)(ii) tensile-to-yield strength ratio boundary",
        plastic_limits["values"]["materials"][0]["tensile_to_yield_strength_ratio"],
        1.2,
    )
    record(
        "Clause 4.5.2 prescriptive limits at table boundaries",
        int(plastic_limits["checked_conditions_satisfied"]),
        1,
    )
    plastic_connections = run_design_actions(
        {
            "operation": "plastic_analysis_connections",
            "rigid_plastic_analysis_verified": True,
            "all_assumed_connections_listed_verified": True,
            "all_collapse_mechanism_hinges_listed_verified": True,
            "analysis_evidence_reference": "VERIFY-PLASTIC-ANALYSIS-01",
            "connections": [
                {
                    "connection_id": "C-FULL",
                    "strength_type": "full_strength",
                    "connection_design_moment_capacity_knm": 100,
                    "connected_member_design_moment_capacity_knm": 100,
                    "connection_capacity_used_in_analysis_verified": True,
                    "all_required_plastic_hinges_develop_verified": True,
                    "evidence_reference": "VERIFY-CONNECTION-FULL-01",
                },
                {
                    "connection_id": "C-PARTIAL",
                    "strength_type": "partial_strength",
                    "connection_design_moment_capacity_knm": 80,
                    "connected_member_design_moment_capacity_knm": 100,
                    "connection_capacity_used_in_analysis_verified": True,
                    "all_required_plastic_hinges_develop_verified": True,
                    "evidence_reference": "VERIFY-CONNECTION-PARTIAL-01",
                },
            ],
            "plastic_hinges": [
                {
                    "hinge_id": "H-MEMBER",
                    "location_type": "member",
                    "rotation_demand_rad": 0.025,
                    "rotation_capacity_rad": 0.025,
                    "rotation_demand_assessment_verified": True,
                    "rotation_capacity_assessment_verified": True,
                    "evidence_reference": "VERIFY-HINGE-01",
                }
            ],
        }
    )
    record(
        "Clause 4.5.3 full-strength connection capacity boundary",
        plastic_connections["values"]["connections"][0]["capacity_ratio"],
        1,
    )
    record(
        "Clause 4.5.3 hinge rotation capacity boundary",
        plastic_connections["values"]["plastic_hinges"][0]["rotation_demand_to_capacity_ratio"],
        1,
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
    record(
        "Clause 5.9.3 parent minimum-thickness provision is traced",
        int("5.9.3" in web_thickness["clauses"]),
        1,
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
    appendix_j_prerequisites = {
        "check_type": "slip_factor_test",
        "nominal_bolt_diameter_mm": 16,
        "bolt_grade": "8.8",
        "symmetrical_double_cover_butt_specimen_verified": True,
        "bolts_clear_of_bearing_in_loading_direction_verified": True,
        "specimen_geometry": {
            "bolt_centre_spacing_mm": 96,
            "left_bolt_to_test_section_end_mm": 32,
            "right_bolt_to_test_section_end_mm": 32,
            "upper_bolt_edge_distance_mm": 48,
            "lower_bolt_edge_distance_mm": 48,
            "inner_plate_thicknesses_mm": [21, 21],
            "cover_plate_thicknesses_mm": [10, 10],
            "cover_plate_hole_diameter_mm": 18,
            "inner_plate_hole_diameter_mm": 19,
            "butt_gap_mm": 8,
        },
        "friction_surface_condition_matches_field_verified": True,
        "machining_oil_contamination_absent_if_used_verified": True,
        "specimen_bolt_tensioning_matches_field_verified": True,
        "initial_snug_condition_finger_tight_verified": True,
        "extension_measurement_immediately_before_test_verified": True,
        "extension_instrument_resolution_mm": 0.003,
        "instrumentation_layout_per_appendix_j_verified": True,
        "instrumentation_deformation_reduction_per_appendix_j_verified": True,
        "tensile_loading_only_verified": True,
        "slip_load_identification_per_appendix_j_verified": True,
        "appendix_j_test_report_reference": "VERIFY-APPENDIX-J",
    }

    def appendix_j_loading_increments(bolts, tension_kn):
        predicted_slip_kn = min(0.7 * tension_kn for _ in bolts)
        increment_limit_kn = min(25.0, 0.25 * predicted_slip_kn)
        final_load_kn = max(bolt["slip_load_kn"] for bolt in bolts)
        increments = []
        load_kn = 0.0
        while load_kn < final_load_kn - 1e-9:
            next_load_kn = min(load_kn + increment_limit_kn, final_load_kn)
            increment = {
                "load_before_kn": load_kn,
                "load_after_kn": next_load_kn,
                "maximum_rate_kn_per_min": 40,
                "loading_rate_approximately_uniform_verified": True,
            }
            if increments:
                increment["preceding_load_creep_effectively_ceased_verified"] = True
            increments.append(increment)
            load_kn = next_load_kn
        return increments

    def appendix_j_specimens(estimates, tension_kn=100):
        specimens = []
        for i in range(0, len(estimates), 2):
            bolts = [
                {
                    "bolt_id": f"B{j % 2 + 1}",
                    "slip_load_kn": 2 * tension_kn * estimates[j],
                    "slip_load_method": "clear_observed_slip",
                    "bolt_extension_mm": 0.1,
                    "calibrated_bolt_tension_kn": tension_kn,
                }
                for j in (i, i + 1)
            ]
            specimens.append(
                {
                    "specimen_id": f"S{i // 2 + 1}",
                    "bolts": bolts,
                    "loading_increments": appendix_j_loading_increments(bolts, tension_kn),
                }
            )
        return specimens

    def appendix_j_equation_specimens():
        specimens = []
        for specimen_number in (1, 2, 3):
            bolts = [
                {
                    "bolt_id": f"B{position}",
                    "slip_load_kn": 70,
                    "slip_load_method": "clear_observed_slip",
                    "bolt_extension_mm": 0.14,
                    "unthreaded_grip_length_mm": 20,
                    "unthreaded_shank_area_mm2": 201,
                    "threaded_grip_length_mm": 20,
                    "nut_thickness_mm": 16,
                    "tensile_stress_area_mm2": 157,
                }
                for position in (1, 2)
            ]
            specimens.append(
                {
                    "specimen_id": f"S{specimen_number}",
                    "bolts": bolts,
                    "loading_increments": appendix_j_loading_increments(bolts, 100),
                }
            )
        return specimens

    appendix_j_three = run_connections(
        {
            **appendix_j_prerequisites,
            "bolt_tension_method": "calibration_curve",
            "calibration_test_bolt_count": 3,
            "calibration_curve_reference": "VERIFY-CAL-CURVE",
            "calibration_test_bolts_from_test_batch_verified": True,
            "calibration_grip_and_measurement_method_match_verified": True,
            "calibration_curve_based_on_mean_result_verified": True,
            "specimens": appendix_j_specimens([0.35, 0.36, 0.40, 0.41, 0.45, 0.46]),
        }
    )
    record(
        "Appendix J.5 three-specimen arithmetic mean",
        appendix_j_three["checks"]["slip_factor"]["mean_of_individual_estimates"],
        0.405,
    )
    record(
        "Appendix J.5 three-specimen sample standard deviation",
        appendix_j_three["checks"]["slip_factor"]["sample_standard_deviation"],
        0.04505552130427524,
    )
    record(
        "Appendix J.5 lowest-estimate fallback",
        appendix_j_three["checks"]["slip_factor"]["slip_factor_for_design"],
        0.35,
    )
    appendix_j_loading = appendix_j_three["checks"]["loading_protocol"]["specimens"][0]
    record(
        "Appendix J.3 predicted connection slip load from 0.35 factor",
        appendix_j_loading["predicted_connection_slip_load_kn"],
        70,
    )
    record(
        "Appendix J.3 maximum load increment, one-quarter connection slip load",
        appendix_j_loading["maximum_permitted_increment_kn"],
        17.5,
    )
    appendix_j_unclear_specimens = appendix_j_specimens([0.35, 0.36, 0.40, 0.41, 0.45, 0.46])
    unclear_bolt = appendix_j_unclear_specimens[0]["bolts"][0]
    unclear_bolt.pop("slip_load_kn")
    unclear_bolt["slip_load_method"] = "0.13_mm_deformation"
    unclear_bolt["deformation_readings"] = [
        {"load_kn": 0, "left_edge_deformation_mm": 0, "right_edge_deformation_mm": 0},
        {
            "load_kn": 60,
            "left_edge_deformation_mm": 0.08,
            "right_edge_deformation_mm": 0.12,
        },
        {
            "load_kn": 80,
            "left_edge_deformation_mm": 0.15,
            "right_edge_deformation_mm": 0.17,
        },
    ]
    appendix_j_unclear = run_connections(
        {
            **appendix_j_prerequisites,
            "bolt_tension_method": "calibration_curve",
            "calibration_test_bolt_count": 3,
            "calibration_curve_reference": "VERIFY-CAL-CURVE",
            "calibration_test_bolts_from_test_batch_verified": True,
            "calibration_grip_and_measurement_method_match_verified": True,
            "calibration_curve_based_on_mean_result_verified": True,
            "specimens": appendix_j_unclear_specimens,
        }
    )
    appendix_j_unclear_bolt = appendix_j_unclear["intermediate"]["specimens"][0]["bolts"][0]
    record(
        "Appendix J.4 load at mean edge deformation 0.13 mm",
        appendix_j_unclear_bolt["slip_load_kn"],
        70,
    )
    record(
        "Appendix J.4 derived individual slip-factor estimate",
        appendix_j_unclear_bolt["individual_slip_factor_estimate"],
        0.35,
    )
    record(
        "Appendix J Figure J.1 M16 specimen test-section length",
        appendix_j_three["checks"]["specimen_geometry"]["test_section_length_mm"],
        160,
    )
    record(
        "Appendix J Figure J.1 M16 specimen width",
        appendix_j_three["checks"]["specimen_geometry"]["specimen_width_mm"],
        96,
    )
    appendix_j_five = run_connections(
        {
            **appendix_j_prerequisites,
            "bolt_tension_method": "calibration_curve",
            "calibration_test_bolt_count": 3,
            "calibration_curve_reference": "VERIFY-CAL-CURVE",
            "calibration_test_bolts_from_test_batch_verified": True,
            "calibration_grip_and_measurement_method_match_verified": True,
            "calibration_curve_based_on_mean_result_verified": True,
            "specimens": appendix_j_specimens([0.1, *([0.5] * 9)]),
        }
    )
    record(
        "Appendix J.5 five-specimen k=0.90 factor without fallback",
        appendix_j_five["checks"]["slip_factor"]["slip_factor_for_design"],
        0.22729912694365897,
    )
    appendix_j_equation = run_connections(
        {
            **appendix_j_prerequisites,
            "bolt_tension_method": "equation_j1",
            "specified_bolt_proof_load_kn": 120,
            "proof_load_reference": "VERIFY-BOLT-PROOF",
            "bolt_proof_load_specification_verified": True,
            "bolt_geometry_source_reference": "VERIFY-BOLT-GEOMETRY",
            "bolt_geometry_matches_tested_assembly_verified": True,
            "specimens": appendix_j_equation_specimens(),
        }
    )
    record(
        "Equation J.1 bolt tension, independently evaluated geometry",
        appendix_j_equation["intermediate"]["specimens"][0]["bolts"][0]["bolt_tension_kn"],
        100.77509124087591,
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
    block_shear_paths = run_connections(
        {
            "check_type": "block_shear_paths",
            "yield_strength_mpa": 300,
            "ultimate_strength_mpa": 440,
            "thickness_mm": 10,
            "candidate_paths": [
                {
                    "path_id": "path-a",
                    "gross_shear_length_mm": 200,
                    "net_shear_length_mm": 150,
                    "net_tension_length_mm": 50,
                    "uniform_tension": False,
                },
                {
                    "path_id": "path-b",
                    "gross_shear_length_mm": 180,
                    "net_shear_length_mm": 130,
                    "net_tension_length_mm": 60,
                    "uniform_tension": False,
                },
                {
                    "path_id": "path-c",
                    "gross_shear_length_mm": 200,
                    "net_shear_length_mm": 150,
                    "net_tension_length_mm": 50,
                    "uniform_tension": True,
                },
            ],
            "rupture_paths_complete_and_net_lengths_verified": True,
            "action_kn": 250,
        }
    )
    block_shear_path_b = block_shear_paths["checks"]["block_shear_path_set"]["paths"][1]
    record(
        "Clause 9.1.9(e) path set, path B net shear area from dimensions",
        block_shear_path_b["net_shear_area_mm2"],
        1300,
    )
    record(
        "Clause 9.1.9(e) path B yielding mode, independent arithmetic",
        block_shear_path_b["nominal_shear_yielding_mode_capacity_kn"],
        456,
    )
    record(
        "Clause 9.1.9(e) minimum across candidate paths, phi=0.75",
        block_shear_paths["checks"]["block_shear_path_set"]["design_capacity_kn"],
        342,
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
    combined_weld_types = run_connections(
        {
            "check_type": "combined_weld_types",
            "design_action_basis": "force_kn",
            "design_action": 40,
            "complete_nonoverlapping_weld_component_set_verified": True,
            "common_action_basis_and_direction_verified": True,
            "weld_components": [
                {
                    "component_id": "BENCHMARK-FILLET-01",
                    "weld_type": "fillet",
                    "design_capacity": 25,
                    "capacity_calculation_reference": "BENCHMARK-FILLET-CAPACITY-01",
                    "section_9_capacity_basis_verified": True,
                },
                {
                    "component_id": "BENCHMARK-BUTT-01",
                    "weld_type": "butt",
                    "design_capacity": 20,
                    "capacity_calculation_reference": "BENCHMARK-BUTT-CAPACITY-01",
                    "section_9_capacity_basis_verified": True,
                },
            ],
        }
    )
    combined_weld_check = combined_weld_types["checks"]["combined_weld_connection_capacity"]
    record(
        "Clause 9.7.4 combined fillet and butt weld design capacity",
        combined_weld_check["design_capacity_kn"],
        45,
    )
    record(
        "Clause 9.7.4 combined weld utilisation from hand arithmetic",
        combined_weld_check["utilisation"],
        40 / (25 + 20),
    )
    record(
        "Clause 9.7.4 does not apply a second capacity factor",
        int(combined_weld_types["intermediate"]["capacity_factor_applied_again"] is False),
        1,
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
    varying_buckling = run_advanced_members(
        {
            "operation": "buckling_analysis_bending",
            "analysis_scope": "varying_section",
            "section_capacity_knm": 120,
            "elastic_buckling_moment_knm": 100,
            "moment_factor": 1.3,
            "end_configuration": "both_restrained",
            "restraint_and_load_model_verified": True,
            "critical_section_capacity_verified": True,
            "varying_section_buckling_model_verified": True,
            "buckling_analysis_reference": "VERIFY-VARYING-BUCKLING-01",
            "action_knm": 60,
        }
    )
    record(
        "Clause 5.6.1.1(b)(iii) reference analysis moment, hand arithmetic",
        varying_buckling["values"]["reference_analysis_moment_knm"],
        76.92307692307692,
        1e-12,
    )
    record(
        "Clause 5.6.1.1(b)(iii) varying-section member moment capacity, hand arithmetic",
        varying_buckling["values"]["member_capacity_knm"],
        72.16638301017798,
        1e-10,
    )
    unequal_flange_buckling = run_advanced_members(
        {
            "operation": "buckling_analysis_bending",
            "analysis_scope": "unequal_flange_i",
            "section_capacity_knm": 100,
            "elastic_buckling_moment_knm": 125,
            "moment_factor": 1.25,
            "end_configuration": "both_restrained",
            "restraint_and_load_model_verified": True,
            "unequal_flange_i_applicability_verified": True,
            "constant_cross_section_verified": True,
            "unequal_flange_buckling_model_verified": True,
            "buckling_analysis_reference": "VERIFY-UNEQUAL-FLANGE-01",
            "action_knm": 60,
        }
    )
    record(
        "Clause 5.6.1.2(b) reference analysis moment, hand arithmetic",
        unequal_flange_buckling["values"]["reference_analysis_moment_knm"],
        100,
    )
    record(
        "Clause 5.6.1.2(b) unequal-flange member moment capacity, hand arithmetic",
        unequal_flange_buckling["values"]["member_capacity_knm"],
        75,
    )
    hollow_bending = run_advanced_members(
        {
            "operation": "hollow_section_bending_capacity",
            "section_type": "rhs",
            "section_capacity_knm": 100,
            "iy_mm4": 50_000_000,
            "torsion_constant_mm4": 200_000,
            "effective_length_mm": 15_000,
            "moment_factor": 1,
            "action_knm": 45,
            "hollow_section_applicability_verified": True,
            "section_properties_verified": True,
            "section_capacity_verified": True,
            "constant_cross_section_verified": True,
            "effective_length_verified": True,
            "moment_factor_verified": True,
            "segment_without_full_lateral_restraint_verified": True,
            "both_ends_restrained_verified": True,
        }
    )
    record(
        "Clause 5.6.1.4 RHS reference buckling moment with Iw=0, hand arithmetic",
        hollow_bending["values"]["reference_buckling_moment_knm"],
        83.77580409572782,
        1e-12,
    )
    record(
        "Clause 5.6.1.4 RHS slenderness reduction, hand arithmetic",
        hollow_bending["values"]["slenderness_reduction_alpha_s"],
        0.5459194274720188,
        1e-12,
    )
    record(
        "Clause 5.6.1.4 RHS nominal member moment capacity, hand arithmetic",
        hollow_bending["values"]["nominal_member_moment_capacity_mb_knm"],
        54.591942747201884,
        1e-12,
    )
    record(
        "Clause 5.6.1.4 RHS design moment capacity at phi=0.9, hand arithmetic",
        hollow_bending["checks"][0]["design_capacity"],
        49.1327484724817,
        1e-12,
    )
    record(
        "Clause 5.6.1.4 sets warping constant to zero",
        hollow_bending["values"]["warping_constant_used_mm6"],
        0,
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
        "Amd 1 Clause 8.4.5.1 powered biaxial member interaction",
        nonprincipal_bending["values"]["member_interaction"],
        2 * (0.625**1.4),
    )
    amended_8452 = run_members(
        {
            "operation": "interaction",
            "axial_mode": "tension",
            "section_axial_capacity_kn": 1000,
            "member_axial_x_kn": 800,
            "member_axial_y_kn": 500,
            "section_moment_x_knm": 100,
            "section_moment_y_knm": 50,
            "member_moment_x_knm": 70,
            "axial_action_kn": 90,
            "moment_x_knm": 45,
            "moment_y_knm": 22.5,
        }
    )
    record(
        "Amd 1 Clause 8.4.5.2 powered biaxial member interaction",
        amended_8452["checks"]["member_combined"]["utilisation"],
        (45 / (0.9 * 77)) ** 1.4 + (22.5 / (0.9 * 45)) ** 1.4,
        1e-12,
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
    angle_interaction = run_advanced_members(
        {
            "operation": "angle_combined_interaction",
            "design_compression_kn": 90,
            "design_moment_about_h_knm": 9,
            "nominal_member_compression_nch_kn": 200,
            "nominal_member_bending_mbx_knm": 40,
            "angle_between_x_and_h_deg": 60,
            "clause_8_3_interaction_satisfied": True,
            "single_angle_web_compression_member_in_truss_verified": True,
            "end_connection_at_least_two_bolts_or_welded_verified": True,
            "loaded_through_one_leg_figure_8_4_6_verified": True,
            "angle_axis_orientation_verified": True,
            "nominal_nch_mbx_calculations_verified": True,
        }
    )
    angle_interaction_values = angle_interaction["values"]
    record(
        "Amd 1:2021 Clause 8.4.6 axial interaction term",
        angle_interaction_values["axial_utilisation"],
        0.5,
    )
    record(
        "Amd 1:2021 Clause 8.4.6 moment term with cos alpha",
        angle_interaction_values["moment_utilisation"],
        0.5,
    )
    record(
        "Amd 1:2021 Clause 8.4.6 exact interaction boundary",
        angle_interaction_values["interaction_utilisation"],
        1.0,
    )
    record(
        "Amd 1:2021 Clause 8.4.6 exact interaction boundary accepted",
        int(angle_interaction["checked_conditions_satisfied"]),
        1,
    )
    closed_section_j = run_advanced_members(
        {
            "operation": "closed_section_torsion_constant",
            "enclosed_median_line_area_mm2": 10_000,
            "wall_segments": [
                {"median_line_length_mm": 100, "thickness_mm": 5},
                {"median_line_length_mm": 100, "thickness_mm": 5},
                {"median_line_length_mm": 100, "thickness_mm": 5},
                {"median_line_length_mm": 100, "thickness_mm": 5},
            ],
            "single_cell_thin_walled_closed_section_verified": True,
            "median_line_geometry_verified": True,
        }
    )
    record(
        "Amd 1 Appendix H.4 square closed-section torsion constant, hand arithmetic",
        closed_section_j["values"]["torsion_constant_j_mm4"],
        5_000_000,
        1e-9,
    )
    open_section_j = run_advanced_members(
        {
            "operation": "open_section_torsion_constant",
            "wall_segments": [
                {"median_line_length_mm": 1200, "thickness_mm": 3},
                {"median_line_length_mm": 600, "thickness_mm": 6},
            ],
            "all_wall_segments_and_thin_walled_open_geometry_verified": True,
        }
    )
    record(
        "Appendix H.4 informative open-section torsion constant, hand arithmetic",
        open_section_j["values"]["torsion_constant_j_approx_mm4"],
        54_000,
        1e-9,
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
    limited_ductile_brace = run_durability(
        {
            "check_type": "concentric_brace_yielding_connection",
            "limited_ductility_concentric_braced_frame_verified": True,
            "all_applicable_brace_connections_listed_verified": True,
            "brace_connections": [
                {
                    "connection_id": "BR-1",
                    "member_design_capacity_kn": 200,
                    "connection_design_capacity_kn": 200,
                }
            ],
        }
    )["results"]
    record(
        "Clause 13.3.5(b) brace connection full member design capacity",
        limited_ductile_brace["connection_checks"][0]["required_connection_capacity_kn"],
        200,
    )
    record(
        "Clause 13.3.5(b) brace connection at full member capacity",
        int(limited_ductile_brace["check_satisfied"]),
        1,
    )
    intermediate_stiffeners = run_durability(
        {
            "check_type": "intermediate_moment_frame_stiffeners",
            "intermediate_moment_frame_applicability_verified": True,
            "all_applicable_web_stiffeners_listed_verified": True,
            "web_stiffeners": [
                {
                    "stiffener_id": "ST-1",
                    "extends_full_depth_between_flanges": True,
                    "butt_welded_to_both_flanges": True,
                }
            ],
        }
    )["results"]
    record(
        "Clause 13.3.6.3(b) intermediate-frame stiffener details",
        int(intermediate_stiffeners["check_satisfied"]),
        1,
    )
    plastic_region_fabrication = run_durability(
        {
            "check_type": "seismic_plastic_region_fabrication",
            "moderately_ductile_plastic_regions_verified": True,
            "all_plastic_region_edges_and_holes_listed_verified": True,
            "sheared_edges": [
                {
                    "edge_id": "E-1",
                    "sheared_oversize_and_machined_to_remove_all_sheared_surface": True,
                }
            ],
            "gas_cut_edges": [{"edge_id": "E-2", "surface_roughness_um": 12}],
            "fastener_holes": [
                {"hole_id": "H-1", "hole_making_method": "drilled"},
                {
                    "hole_id": "H-2",
                    "hole_making_method": "undersize_punched_then_reamed_or_drilled",
                },
            ],
        }
    )["results"]
    record(
        "Clause 13.3.6.4(a) maximum gas-cut edge roughness",
        plastic_region_fabrication["gas_cut_edge_checks"][0]["maximum_surface_roughness_um"],
        12,
    )
    record(
        "Clause 13.3.6.4(a)-(b) acceptable plastic-region fabrication methods",
        int(plastic_region_fabrication["check_satisfied"]),
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
    seismic_detailing = run_durability(
        {
            "check_type": "concentric_brace_connection_detailing",
            "bearing_wall_or_building_frame_system_verified": True,
            "all_concentric_braced_frame_welds_and_stiffeners_listed_verified": True,
            "web_stiffeners": [
                {
                    "stiffener_id": "ST-1",
                    "extends_full_depth_between_flanges": True,
                    "butt_welded_to_both_flanges": True,
                }
            ],
            "weld_groups": [
                {
                    "weld_group_id": "BW-T-1",
                    "weld_population": "butt_in_tension",
                    "weld_category": "SP",
                    "visual_scanning_percent": 100,
                    "visual_examination_percent": 100,
                    "magnetic_particle_or_dye_penetrant_percent": 100,
                    "ultrasonics_or_radiography_percent": 10,
                },
                {
                    "weld_group_id": "BW-N-1",
                    "weld_population": "butt_not_in_tension",
                    "weld_category": "SP",
                    "visual_scanning_percent": 100,
                    "visual_examination_percent": 50,
                    "magnetic_particle_or_dye_penetrant_percent": 10,
                    "ultrasonics_or_radiography_percent": 2,
                },
                {
                    "weld_group_id": "OW-1",
                    "weld_population": "other_welds",
                    "weld_category": "SP",
                    "visual_scanning_percent": 100,
                    "visual_examination_percent": 20,
                    "magnetic_particle_or_dye_penetrant_percent": 5,
                    "ultrasonics_or_radiography_percent": 2,
                },
            ],
        }
    )["results"]
    record(
        "Clause 13.3.6.2(b) full-depth butt-welded stiffener condition",
        int(seismic_detailing["stiffeners_satisfied"]),
        1,
    )
    record(
        "Table 13.3.6.2 tension butt weld ultrasonics/radiography percentage",
        seismic_detailing["weld_group_checks"][0]["required_ultrasonics_or_radiography_percent"],
        10,
    )
    record(
        "Table 13.3.6.2 non-tension butt weld visual examination percentage",
        seismic_detailing["weld_group_checks"][1]["required_visual_examination_percent"],
        50,
    )
    record(
        "Table 13.3.6.2 other welds magnetic particle/dye penetrant percentage",
        seismic_detailing["weld_group_checks"][2][
            "required_magnetic_particle_or_dye_penetrant_percent"
        ],
        5,
    )
    record(
        "Clause 13.3.6.2(c) SP category and NDE coverage limits",
        int(seismic_detailing["check_satisfied"]),
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
    standard_hole = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "standard",
            "bolt_diameter_mm": 24,
            "hole_diameter_mm": 26,
        }
    )
    record(
        "Clause 14.3.2 standard hole at 24 mm bolt boundary",
        standard_hole["values"]["maximum_hole_diameter_mm"],
        26,
    )
    base_plate_hole = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "base_plate_anchor",
            "bolt_diameter_mm": 14,
            "hole_diameter_mm": 20,
            "special_nut_washer": {
                "type": "plate",
                "thickness_mm": 4,
                "minimum_edge_clearance_mm": 10,
                "coverage_geometry_verified": True,
                "product_verified": True,
                "material_as_nzs_3678_verified": True,
            },
        }
    )
    record(
        "Clause 14.3.2 base-plate anchor-hole maximum diameter",
        base_plate_hole["values"]["maximum_hole_diameter_mm"],
        20,
    )
    record(
        "Clause 14.3.2 base-plate special washer minimum thickness",
        int(base_plate_hole["checks"][1]["satisfied"]),
        1,
    )
    oversize_hole = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "oversize",
            "bolt_diameter_mm": 20,
            "hole_diameter_mm": 28,
            "not_base_plate_anchor_hole_verified": True,
            "connection_type": "friction_type",
            "subject_to_shear": False,
            "head_side": {"bears_on_holed_ply": False, "washer": None},
            "nut_side": {"bears_on_holed_ply": False, "washer": None},
        }
    )
    record(
        "Clause 14.3.2 oversize-hole diameter max(1.25d, d+8)",
        oversize_hole["values"]["maximum_hole_diameter_mm"],
        28,
    )
    governing_oversize_hole = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "oversize",
            "bolt_diameter_mm": 40,
            "hole_diameter_mm": 50,
            "not_base_plate_anchor_hole_verified": True,
            "connection_type": "friction_type",
            "subject_to_shear": False,
            "head_side": {"bears_on_holed_ply": False, "washer": None},
            "nut_side": {"bears_on_holed_ply": False, "washer": None},
        }
    )
    record(
        "Clause 14.3.2 oversize-hole factor limit 1.25d",
        governing_oversize_hole["values"]["maximum_hole_diameter_mm"],
        1.25 * 40,
    )
    short_slot = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "short_slot",
            "bolt_diameter_mm": 20,
            "hole_width_mm": 22,
            "hole_length_mm": 30,
            "not_base_plate_anchor_hole_verified": True,
            "connection_type": "friction_type",
            "subject_to_shear": True,
            "head_side": {"bears_on_holed_ply": False, "washer": None},
            "nut_side": {"bears_on_holed_ply": False, "washer": None},
        }
    )
    record(
        "Clause 14.3.2 short-slot length max(1.33d, d+10)",
        short_slot["values"]["maximum_hole_length_mm"],
        30,
    )
    governing_short_slot = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "short_slot",
            "bolt_diameter_mm": 40,
            "hole_width_mm": 43,
            "hole_length_mm": 53.2,
            "not_base_plate_anchor_hole_verified": True,
            "connection_type": "friction_type",
            "subject_to_shear": False,
            "head_side": {"bears_on_holed_ply": False, "washer": None},
            "nut_side": {"bears_on_holed_ply": False, "washer": None},
        }
    )
    record(
        "Clause 14.3.2 short-slot factor limit 1.33d",
        governing_short_slot["values"]["maximum_hole_length_mm"],
        1.33 * 40,
    )
    long_slot = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "long_slot",
            "bolt_diameter_mm": 20,
            "hole_width_mm": 22,
            "hole_length_mm": 50,
            "not_base_plate_anchor_hole_verified": True,
            "connection_type": "friction_type",
            "subject_to_shear": True,
            "alternate_plies_verified": True,
            "head_side": {
                "bears_on_holed_ply": True,
                "washer": {
                    "type": "plate",
                    "thickness_mm": 8,
                    "minimum_edge_clearance_mm": 11,
                    "coverage_geometry_verified": True,
                    "product_verified": True,
                    "material_as_nzs_3678_verified": True,
                },
            },
            "nut_side": {"bears_on_holed_ply": False, "washer": None},
        }
    )
    record(
        "Clause 14.3.2 long-slot total length 2.5d",
        long_slot["values"]["maximum_hole_length_mm"],
        50,
    )
    record(
        "Clause 14.3.2 long-slot washer minimum thickness and alternate plies",
        int(long_slot["checked_conditions_satisfied"]),
        1,
    )
    material_identification = run_fabrication(
        {
            "check_type": "fabrication_basis",
            "materials_conform_referenced_standards_verified": True,
            "surface_defects_removed_per_referenced_standards_verified": True,
            "steel_grade_identifiable_at_all_fabrication_stages_verified": False,
            "steel_classified_as_unidentified": True,
            "clause_2_2_3_unidentified_steel_inputs": {
                "operation": "unidentified_steel",
                "design_yield_strength_mpa": 170,
                "design_tensile_strength_mpa": 300,
                "surface_imperfections_verified": True,
                "properties_and_weldability_verified": True,
                "full_test_to_as1391_verified": False,
            },
            "marking_does_not_damage_material_verified": True,
            "fabrication_per_as_nzs_5131_verified": True,
            "fabrication_methods_preserve_design_properties_verified": True,
        }
    )
    record(
        "Clause 14.2.2 unidentified steel Clause 2.2.3 route",
        int(material_identification["checked_conditions_satisfied"]),
        1,
    )
    bolt_assembly = run_fabrication(
        {
            "check_type": "bolt_assembly",
            "connection_type": "bearing_type",
            "bolts_nuts_washers_conform_clause_2_3_1_verified": True,
            "all_material_within_bolt_grip_is_steel_verified": True,
            "clear_threads_above_nut_count": 1,
            "thread_plus_runout_clear_beneath_nut_verified": True,
            "rotated_part": "nut",
            "washer_under_rotated_part_verified": True,
            "maximum_contact_surface_slope_ratio": 0.05,
            "contact_surface_slope_measurement_verified": True,
            "subject_to_vibration": False,
            "fully_tensioned_high_strength_bolt_installed_during_fabrication": False,
        }
    )
    record(
        "Clause 14.3.3.1 thread projection and 1:20 slope boundary",
        int(
            bolt_assembly["checked_conditions_satisfied"]
            and not bolt_assembly["values"]["tapered_washer_required"]
        ),
        1,
    )
    friction_assembly = run_fabrication(
        {
            "check_type": "bolt_assembly",
            "connection_type": "friction_type",
            "bolts_nuts_washers_conform_clause_2_3_1_verified": True,
            "all_material_within_bolt_grip_is_steel_verified": True,
            "clear_threads_above_nut_count": 1,
            "thread_plus_runout_clear_beneath_nut_verified": True,
            "rotated_part": "nut",
            "washer_under_rotated_part_verified": True,
            "maximum_contact_surface_slope_ratio": 0.05,
            "contact_surface_slope_measurement_verified": True,
            "subject_to_vibration": False,
            "fully_tensioned_high_strength_bolt_installed_during_fabrication": False,
            "friction_surfaces_prepared_per_as_nzs_5131_verified": True,
            "friction_surfaces_clean_as_rolled_or_equivalent_verified": False,
            "clause_9_2_3_2_alternative_route_verified": True,
        }
    )
    record(
        "Clause 14.3.3.2 friction surface alternative design route",
        int(friction_assembly["checked_conditions_satisfied"]),
        1,
    )
    essential_tolerance = run_fabrication(
        {
            "check_type": "geometric_tolerance",
            "tolerance_type": "essential",
            "measured_deviation_mm": 3,
            "permissible_deviation_mm": 2,
            "as_nzs_5131_tolerance_limit_verified": True,
            "measurement_after_fabrication_and_corrosion_protection_verified": True,
            "coating_thickness_excluded_from_measurement_verified": True,
            "excess_deviation_in_revised_design_capacity_verified": True,
        }
    )
    record(
        "Clause 14.4.2 essential tolerance revised-capacity route",
        int(essential_tolerance["checked_conditions_satisfied"]),
        1,
    )
    functional_tolerance = run_fabrication(
        {
            "check_type": "geometric_tolerance",
            "tolerance_type": "functional",
            "measured_deviation_mm": 1,
            "permissible_deviation_mm": 2,
            "as_nzs_5131_tolerance_limit_verified": True,
            "measurement_after_fabrication_and_corrosion_protection_verified": True,
            "coating_thickness_excluded_from_measurement_verified": True,
        }
    )
    record(
        "Clause 14.4.1 unspecified functional class defaults to Class 1",
        functional_tolerance["values"]["functional_tolerance_class_applied"],
        1,
    )
    fabricated_acceptance = run_fabrication(
        {
            "check_type": "fabricated_item_acceptance",
            "clause_14_2_material_requirements_satisfied": False,
            "clause_14_3_fabrication_requirements_satisfied": True,
            "clause_14_4_tolerances_satisfied": True,
            "structural_adequacy_and_intended_use_unimpaired_demonstrated": False,
            "section_17_testing_passed": True,
        }
    )
    record(
        "Clause 14.1 Section 17 test alternative acceptance route",
        int(fabricated_acceptance["values"]["fabricated_item_may_be_accepted"]),
        1,
    )
    table_15_2_2_2 = {
        (16, "8.8"): 95,
        (16, "10.9"): 130,
        (20, "8.8"): 145,
        (20, "10.9"): 205,
        (24, "8.8"): 210,
        (24, "10.9"): 295,
        (30, "8.8"): 335,
        (30, "10.9"): 465,
        (36, "8.8"): 490,
        (36, "10.9"): 680,
    }
    for (diameter, grade), expected in table_15_2_2_2.items():
        tension_result = run_erection(
            {
                "operation": "bolted_connection_assembly",
                "connection_type": "fully_tensioned",
                "assembly_per_as_nzs_5131_verified": True,
                "bolt_group_reference": f"BG-M{diameter}-{grade}",
                "nominal_bolt_diameter_mm": diameter,
                "bolt_grade": grade,
                "bolt_tension_measurements": [{"bolt_id": "B1", "measured_tension_kn": expected}],
                "homogeneous_bolt_group_verified": True,
                "all_bolts_in_group_listed_verified": True,
                "all_bolts_in_group_tightened_verified": True,
                "tensioning_method": "part_turn",
                "tensioning_method_per_as_nzs_5131_verified": True,
            }
        )
        record(
            f"Table 15.2.2.2 M{diameter} grade {grade} minimum bolt tension (kN)",
            tension_result["values"]["required_minimum_bolt_tension_kn"],
            expected,
        )
        record(
            f"Table 15.2.2.2 M{diameter} grade {grade} exact minimum is accepted",
            int(tension_result["checked_conditions_satisfied"]),
            1,
        )
    erection_tolerance = run_erection(
        {
            "operation": "geometric_tolerance",
            "tolerance_type": "essential",
            "measured_deviation_mm": 3,
            "permissible_deviation_mm": 2,
            "as_nzs_5131_tolerance_limit_verified": True,
            "measurement_after_erection_completed_verified": True,
            "excess_deviation_in_revised_design_capacity_verified": True,
        }
    )
    record(
        "Clause 15.3.2 essential erection deviation revised-capacity route",
        int(erection_tolerance["checked_conditions_satisfied"]),
        1,
    )
    erection_acceptance = run_erection(
        {
            "operation": "erected_item_acceptance",
            "clause_15_2_erection_requirements_satisfied": False,
            "clause_15_3_tolerances_satisfied": False,
            "bolt_hardware_conforms_clauses_14_3_3_and_15_2": True,
            "structural_adequacy_and_intended_use_unimpaired_demonstrated": False,
            "section_17_testing_passed": True,
        }
    )
    record(
        "Clause 15.1.1 Section 17 testing acceptance route",
        int(erection_acceptance["values"]["erected_item_may_be_accepted"]),
        1,
    )
    test_scope = run_testing(
        {
            "check_type": "test_scope_applicability",
            "test_article": "individual_member",
            "test_type": "proof",
            "test_purpose": "specific_unit_characteristics",
            "design_complies_with_as_4100_verified": True,
            "special_circumstances_require_test_verified": False,
            "test_used_as_alternative_to_calculation_verified": False,
        }
    )["results"]
    record(
        "Clauses 17.1.1-17.2 in-scope proof test and definition",
        int(test_scope["check_satisfied"]),
        1,
    )
    record(
        "Clause 17.1.2 standard-compliant design not required to be tested",
        int(
            test_scope[
                "testing_not_required_for_standard_compliant_design_without_special_circumstances"
            ]
        ),
        1,
    )
    prototype_test = run_testing(
        {
            "check_type": "prototype_strength",
            "design_load_kn": 100,
            "sustained_load_kn": 140,
            "sustained_duration_min": 5,
            "number_similar_units": 2,
            "materials_conform_section_2_verified": True,
            "fabrication_conforms_section_14_verified": True,
            "manufacturing_specification_requirements_met_verified": True,
            "erection_method_represents_production_verified": True,
            "production_units_similar": True,
            "calibrated_loading_without_artificial_restraints": True,
            "representative_force_distribution_and_duration": True,
            "loading_rate_as_uniform_as_practicable_verified": True,
            "deformations_recorded_before_during_after": True,
            "loading_method_recorded": True,
            "deflection_measurement_method_recorded": True,
            "other_relevant_test_data_recorded": True,
            "acceptance_statement_recorded": True,
            "test_report_complete": True,
        }
    )["results"]
    record(
        "Table 17.5.2 two-unit prototype strength factor",
        prototype_test["test_load_factor"],
        1.4,
    )
    record(
        "Clauses 17.5.1 and 17.5.4 prototype evidence gates",
        int(prototype_test["check_satisfied"]),
        1,
    )
    modification_review = run_testing(
        {
            "check_type": "existing_structure_modification_review",
            "other_as4100_provisions_applied_unless_modified_verified": True,
            "site_modifications_during_erection_applicable": True,
            "site_modifications_conform_as_nzs_5131_verified": True,
            "existing_modification_or_repair_applicable": True,
            "existing_modification_or_repair_conforms_as_nzs_5131_verified": True,
            "strengthening_repair_or_welding_documents_prepared": True,
            "base_metal_types_determined_before_documents_verified": True,
        }
    )["results"]
    record(
        "Clause 16.1 separate erection and existing-work AS/NZS 5131 routes",
        int(
            modification_review["site_modification_requirements_satisfied"]
            and modification_review["existing_modification_or_repair_requirements_satisfied"]
        ),
        1,
    )
    record(
        "Clause 16.2 base-metal determination before related documents",
        int(modification_review["base_metal_determination_timing_satisfied"]),
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
