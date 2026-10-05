import pytest
from jsonschema import Draft202012Validator

from opencalcs_as4100.durability import INPUT_SCHEMA, OUTPUT_SCHEMA, run_durability


def fatigue(kind="fatigue_constant", stress="normal"):
    values = {
        "check_type": kind,
        "stress_type": stress,
        "detail_category_mpa": 100,
        "plate_thickness_mm": 25,
        "transverse_weld": True,
        "capacity_factor": 1,
        "redundant_load_path": True,
        "reference_conditions_satisfied": True,
        "yield_strength_mpa": 350,
        "maximum_stress_magnitude_mpa": 200,
        "punched_holes": False,
    }
    values.update(
        {"stress_range_mpa": 100, "cycles": 2e6}
        if kind == "fatigue_constant"
        else {"events": [{"stress_range_mpa": 100, "cycles": 1e6}]}
    )
    return values


def result(d):
    output = run_durability(d)
    Draft202012Validator(OUTPUT_SCHEMA).validate(output)
    return output["results"]


def hollow_truss_range(**changes):
    return {
        "check_type": "hollow_section_truss_stress_range",
        "hollow_section_form": "CHS",
        "joint_type": "gap",
        "joint_configuration": "K",
        "member_role": "diagonal",
        "unadjusted_stress_range_mpa": 100,
        "fillet_weld_used": True,
        "fillet_weld_throat_mm": 6,
        "connected_member_wall_thickness_mm": 5,
        "clause_11_3_1_applicability_verified": True,
        "member_stress_range_source_verified": True,
        **changes,
    }


def hollow_fatigue_detail(detail, form, **changes):
    return {
        "check_type": "fatigue_hollow_section_detail",
        "detail_number": detail,
        "hollow_section_form": form,
        "detail_conditions_verified": True,
        "stress_direction_verified": True,
        "weld_quality_verified": True,
        "weld_quality_basis": "AS/NZS 1554.1 SP",
        "weld_quality_evidence_reference": "WELD-QUALITY-4100-01",
        "detail_evidence_reference": "DRAWING-4100-01",
        "stress_direction_evidence_reference": "STRESS-REVIEW-4100-01",
        **changes,
    }


def welded_fatigue_detail(detail, **changes):
    conditions = {
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
        "weld_quality_basis": "AS/NZS 1554.5" if detail in {8, 9} else "AS/NZS 1554.1 SP",
        "weld_process": "automatic",
        "transition_slope": 0.3 if detail == 22 else 0.2,
        "backing_weld_end_distance_mm": 10 if detail == 25 else 20,
        "intermediate_plate_thickness_mm": 10,
        "maximum_plate_misalignment_mm": 1,
        "stress_range_area_basis": "weld_throat_area" if detail == 28 else "plate_area",
        "lap_capacity_hierarchy": {
            30: "weld_and_main_gt_overlap",
            31: "main_and_overlap_gt_weld",
        }.get(detail, "weld_and_overlap_gt_main"),
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
        "failure_location": "base_material" if detail == 34 else "weld",
        "detail_conditions_verified": True,
        "stress_direction_verified": True,
        "weld_quality_verified": True,
        "detail_evidence_reference": "WELD-DETAIL-4100-01",
        "stress_direction_evidence_reference": "STRESS-REVIEW-4100-01",
        "weld_quality_evidence_reference": "WELD-QUALITY-4100-01",
    }
    conditions.update(changes)
    return {"check_type": "fatigue_welded_detail", "detail_number": detail, **conditions}


def group1_fatigue_detail(detail, **changes):
    return {
        "check_type": "fatigue_group1_detail",
        "detail_number": detail,
        "detail_conditions_verified": True,
        "stress_direction_verified": True,
        "detail_evidence_reference": "FABRICATION-4100-01",
        "stress_direction_evidence_reference": "STRESS-REVIEW-4100-01",
        **changes,
    }


def bolt_fatigue_detail(detail, **changes):
    return {
        "check_type": "fatigue_bolt_detail",
        "detail_number": detail,
        "detail_conditions_verified": True,
        "stress_direction_verified": True,
        "detail_evidence_reference": "BOLT-DETAIL-4100-01",
        "stress_direction_evidence_reference": "STRESS-REVIEW-4100-01",
        **changes,
    }


@pytest.mark.parametrize(
    "section_form,joint_type,configuration,factors",
    [
        ("CHS", "gap", "K", [1.5, 1.0, 1.3]),
        ("CHS", "gap", "N", [1.5, 1.8, 1.4]),
        ("CHS", "overlap", "K", [1.5, 1.0, 1.2]),
        ("CHS", "overlap", "N", [1.5, 1.65, 1.25]),
        ("RHS", "gap", "K", [1.5, 1.0, 1.5]),
        ("RHS", "gap", "N", [1.5, 2.2, 1.6]),
        ("RHS", "overlap", "K", [1.5, 1.0, 1.3]),
        ("RHS", "overlap", "N", [1.5, 2.0, 1.4]),
    ],
)
def test_clause_11_3_1_hollow_section_truss_table_factors(
    section_form, joint_type, configuration, factors
):
    roles = ["chord", "vertical", "diagonal"]
    for role, factor in zip(roles, factors, strict=True):
        values = result(
            hollow_truss_range(
                hollow_section_form=section_form,
                joint_type=joint_type,
                joint_configuration=configuration,
                member_role=role,
                unadjusted_stress_range_mpa=50,
            )
        )
        assert values["stress_range_factor"] == factor
        assert values["adjusted_stress_range_mpa"] == pytest.approx(50 * factor)


def test_clause_11_3_1_filleted_joint_throat_must_exceed_wall_thickness():
    inputs = hollow_truss_range(fillet_weld_throat_mm=5)
    values = result(inputs)
    assert not values["fillet_weld_throat_check"]["satisfied"]
    assert result(hollow_truss_range(fillet_weld_throat_mm=5.01))["fillet_weld_throat_check"][
        "satisfied"
    ]
    no_fillet = result(hollow_truss_range(fillet_weld_used=False))
    assert no_fillet["fillet_weld_throat_check"] is None
    missing_weld_dimensions = hollow_truss_range()
    missing_weld_dimensions.pop("fillet_weld_throat_mm")
    with pytest.raises(ValueError, match="design throat"):
        result(missing_weld_dimensions)


def test_d01_reference_normal_and_shear():
    for stress in ["normal", "shear"]:
        r = result(fatigue(stress=stress))
        assert r["design_fatigue_strength_mpa"] == pytest.approx(100)
        assert r["utilisation"] == pytest.approx(1)
        assert r["check_satisfied"]


def test_d02_normal_first_slope_and_knee():
    d = fatigue()
    d.update(cycles=250000, stress_range_mpa=200)
    assert result(d)["design_fatigue_strength_mpa"] == pytest.approx(200)
    d["cycles"] = 5e6
    assert result(d)["design_fatigue_strength_mpa"] == pytest.approx(73.6806299728)
    d["cycles"] = 1e8
    assert result(d)["design_fatigue_strength_mpa"] == pytest.approx(40.471316447)


def test_d03_thickness_and_punching():
    d = fatigue()
    d["plate_thickness_mm"] = 400
    r = result(d)
    assert r["thickness_factor"] == pytest.approx(0.5)
    assert r["design_fatigue_strength_mpa"] == pytest.approx(50)
    d.update(punched_holes=True, plate_thickness_mm=12)
    assert result(d)["punching_limit_satisfied"]
    d["plate_thickness_mm"] = 12.001
    assert not result(d)["check_satisfied"]


def test_d04_variable_normal_damage():
    d = fatigue("fatigue_variable")
    # At category100 reference stress100, 1e6 cycles consume half the life2e6.
    assert result(d)["damage"] == pytest.approx(0.5)
    d["events"] *= 2
    assert result(d)["damage"] == pytest.approx(1)
    assert result(d)["check_satisfied"]
    d["events"].append({"stress_range_mpa": 20, "cycles": 1e9})
    assert result(d)["damage"] == pytest.approx(1)


def test_d05_shear_and_low_normal_branch():
    d = fatigue("fatigue_variable", "shear")
    assert result(d)["damage"] == pytest.approx(0.5)
    d["events"] = [{"stress_range_mpa": 50, "cycles": 64e6}]
    assert result(d)["damage"] == pytest.approx(1)
    d = fatigue("fatigue_variable")
    d["events"] = [{"stress_range_mpa": 50, "cycles": 5e6}]
    # 0.5**5 / (0.4**(5/3)) = 0.1439074804.
    assert result(d)["damage"] == pytest.approx(0.143907480416)


def test_d06_fatigue_phi_and_stress_domains():
    d = fatigue()
    d["redundant_load_path"] = False
    with pytest.raises(ValueError):
        result(d)
    d["capacity_factor"] = 0.7
    assert result(d)["design_fatigue_strength_mpa"] == pytest.approx(70)
    d.update(maximum_stress_magnitude_mpa=351)
    with pytest.raises(ValueError):
        result(d)


@pytest.mark.parametrize(
    "detail,form,thickness,expected",
    [
        (44, "CHS", 8, 90),
        (44, "CHS", 7.999, 71),
        (45, "RHS", 8, 71),
        (45, "RHS", 7.999, 56),
        (46, "CHS", 8, 56),
        (46, "CHS", 7.999, 50),
        (47, "RHS", 8, 50),
        (47, "RHS", 7.999, 41),
        (49, "CHS", 8, 45),
        (49, "CHS", 7.999, 40),
        (50, "RHS", 8, 40),
        (50, "RHS", 7.999, 36),
    ],
)
def test_durability_table_11_5_1_d_thickness_classification(detail, form, thickness, expected):
    data = hollow_fatigue_detail(detail, form, wall_thickness_mm=thickness)
    assert result(data)["detail_category_mpa"] == expected


def test_durability_table_11_5_1_d_automatic_weld_and_attachment_classification():
    automatic = hollow_fatigue_detail(43, "CHS", no_stop_starts_verified=True)
    assert result(automatic)["detail_category_mpa"] == 140

    attachment = hollow_fatigue_detail(
        48,
        "RHS",
        section_width_parallel_to_stress_mm=100,
        non_load_carrying_verified=True,
    )
    assert result(attachment)["detail_category_mpa"] == 71


def test_durability_table_11_5_1_d_rejects_unmet_or_unsupported_conditions():
    with pytest.raises(ValueError, match="without stop-starts"):
        result(hollow_fatigue_detail(43, "RHS"))
    with pytest.raises(ValueError, match="non-load-carrying"):
        result(hollow_fatigue_detail(48, "CHS", section_width_parallel_to_stress_mm=100))
    with pytest.raises(ValueError, match="at most 100 mm"):
        result(
            hollow_fatigue_detail(
                48,
                "CHS",
                section_width_parallel_to_stress_mm=100.001,
                non_load_carrying_verified=True,
            )
        )
    with pytest.raises(ValueError, match="applies to CHS only"):
        result(hollow_fatigue_detail(44, "RHS", wall_thickness_mm=8))
    with pytest.raises(ValueError, match="requires wall thickness"):
        result(hollow_fatigue_detail(50, "RHS"))
    with pytest.raises(ValueError, match="evidence reference is required"):
        result(
            hollow_fatigue_detail(
                43,
                "CHS",
                no_stop_starts_verified=True,
                detail_evidence_reference=" ",
            )
        )


@pytest.mark.parametrize(
    "detail,expected,conditions",
    [
        (1, 160, {"surface_and_rolling_flaws_removed_verified": True}),
        (2, 160, {"surface_and_rolling_flaws_removed_verified": True}),
        (3, 160, {"surface_and_rolling_flaws_removed_verified": True}),
        (4, 140, {"bolting_category": "8.8/TF", "one_sided_coverplate_connection": False}),
        (5, 140, {"bolting_category": "other", "one_sided_coverplate_connection": False}),
        (
            6,
            140,
            {
                "no_draglines_verified": True,
                "hardened_edge_material_removed_verified": True,
                "edge_discontinuities_removed_in_stress_direction_verified": True,
            },
        ),
        (
            7,
            125,
            {
                "machine_or_manual_gas_cut_verified": True,
                "edge_discontinuities_removed_in_stress_direction_verified": True,
            },
        ),
    ],
)
def test_durability_table_11_5_1_a_classification(detail, expected, conditions):
    assert result(group1_fatigue_detail(detail, **conditions))["detail_category_mpa"] == expected


def test_durability_table_11_5_1_a_bolt_section_area_and_coverplate_eccentricity():
    gross = result(
        group1_fatigue_detail(
            4,
            bolting_category="8.8/TF",
            one_sided_coverplate_connection=False,
        )
    )
    assert gross["stress_area_basis"] == "gross_section"
    net = result(
        group1_fatigue_detail(
            5,
            bolting_category="other",
            one_sided_coverplate_connection=True,
            eccentricity_effect_assessed=True,
        )
    )
    assert net["stress_area_basis"] == "net_section"


def test_durability_table_11_5_1_a_requires_edge_and_eccentricity_conditions():
    with pytest.raises(ValueError, match="sharp-edge"):
        result(group1_fatigue_detail(1))
    with pytest.raises(ValueError, match="one-sided coverplate"):
        result(group1_fatigue_detail(4, bolting_category="8.8/TF"))
    with pytest.raises(ValueError, match="eccentricity"):
        result(
            group1_fatigue_detail(
                5,
                bolting_category="other",
                one_sided_coverplate_connection=True,
            )
        )


def test_durability_table_11_5_1_c_bolt_category_stress_area_and_slip_note():
    in_slip = result(
        bolt_fatigue_detail(
            41,
            bolting_category="8.8/TB",
            joint_slip_assessment_verified=True,
            joint_shear_causes_slip=True,
            joint_slip_evidence_reference="SLIP-REVIEW-4100-01",
        )
    )
    assert in_slip["detail_category_mpa"] == 100
    assert in_slip["stress_type"] == "shear"
    assert in_slip["stress_area_basis"] == "minor_diameter_area"
    assert in_slip["fatigue_assessment_required"]

    no_slip = result(
        bolt_fatigue_detail(
            41,
            bolting_category="8.8/TB",
            joint_slip_assessment_verified=True,
            joint_shear_causes_slip=False,
            joint_slip_evidence_reference="SLIP-REVIEW-4100-01",
        )
    )
    assert not no_slip["fatigue_assessment_required"]

    tension = result(
        bolt_fatigue_detail(
            42,
            prying_effects_assessed=True,
            prying_assessment_reference="PRYING-REVIEW-4100-01",
        )
    )
    assert tension["detail_category_mpa"] == 36
    assert tension["stress_type"] == "normal"
    assert tension["stress_area_basis"] == "tensile_stress_area"


def test_durability_table_11_5_1_c_rejects_wrong_bolt_category_or_missing_prying_review():
    with pytest.raises(ValueError, match="8.8/TB bolting"):
        result(
            bolt_fatigue_detail(
                41,
                bolting_category="other",
                joint_slip_assessment_verified=True,
                joint_shear_causes_slip=True,
                joint_slip_evidence_reference="SLIP-REVIEW-4100-01",
            )
        )
    with pytest.raises(ValueError, match="prying effects"):
        result(bolt_fatigue_detail(42))


@pytest.mark.parametrize(
    "detail,expected",
    [
        (8, 125),
        (9, 125),
        (10, 112),
        (11, 112),
        (12, 112),
        (13, 90),
        (14, 80),
        (15, 71),
        (16, 112),
        (17, 112),
        (18, 112),
        (19, 90),
        (20, 90),
        (21, 90),
        (22, 80),
        (23, 71),
        (24, 71),
        (25, 50),
        (26, 71),
        (27, 56),
        (28, 36),
        (29, 63),
        (30, 56),
        (31, 45),
        (32, 80),
        (33, 90),
        (34, 80),
        (35, 80),
        (36, 71),
        (37, 71),
        (38, 50),
        (39, 80),
        (40, 80),
    ],
)
def test_durability_table_11_5_1_b_all_welded_details(detail, expected):
    assert result(welded_fatigue_detail(detail))["detail_category_mpa"] == expected


def test_durability_table_11_5_1_b_manual_longitudinal_weld_and_quality_categories():
    manual = result(welded_fatigue_detail(12, weld_process="manual"))
    assert manual["detail_category_mpa"] == 100
    assert manual["weld_quality_basis"] == "AS/NZS 1554.1 SP"

    with pytest.raises(ValueError, match="AS/NZS 1554.5"):
        result(welded_fatigue_detail(8, weld_quality_basis="AS/NZS 1554.1 SP"))
    with pytest.raises(ValueError, match="Category SP"):
        result(welded_fatigue_detail(13, weld_quality_basis="AS/NZS 1554.5"))
    with pytest.raises(ValueError):
        result(welded_fatigue_detail(12, weld_process="unknown"))


def test_durability_table_11_5_1_b_geometry_boundaries_and_stress_bases():
    assert result(welded_fatigue_detail(22, transition_slope=0.4))["detail_category_mpa"] == 80
    assert result(welded_fatigue_detail(24, transition_slope=0.399))["detail_category_mpa"] == 71
    assert (
        result(welded_fatigue_detail(25, backing_weld_end_distance_mm=10))["detail_category_mpa"]
        == 50
    )
    for detail in (23, 24):
        assert (
            result(welded_fatigue_detail(detail, backing_weld_end_distance_mm=10))[
                "detail_category_mpa"
            ]
            == 71
        )
    assert (
        result(welded_fatigue_detail(32, attachment_weld_length_mm=50))["detail_category_mpa"] == 80
    )
    assert (
        result(welded_fatigue_detail(32, attachment_weld_length_mm=100))["detail_category_mpa"]
        == 71
    )
    assert (
        result(welded_fatigue_detail(32, attachment_weld_length_mm=100.001))["detail_category_mpa"]
        == 50
    )
    assert (
        result(welded_fatigue_detail(33, transition_radius_mm=1, section_width_mm=6))[
            "detail_category_mpa"
        ]
        == 71
    )
    assert (
        result(welded_fatigue_detail(33, transition_radius_mm=0.9, section_width_mm=6))[
            "detail_category_mpa"
        ]
        == 45
    )
    assert result(welded_fatigue_detail(35, plate_thickness_mm=12))["detail_category_mpa"] == 80

    plate_area = result(welded_fatigue_detail(27))
    assert plate_area["stress_area_basis"] == "plate_area"
    throat_area = result(welded_fatigue_detail(28, stress_range_area_basis="weld_throat_area"))
    assert throat_area["stress_area_basis"] == "weld_throat_area"
    weld_shear = result(welded_fatigue_detail(39))
    assert weld_shear["stress_type"] == "shear"
    assert weld_shear["stress_area_basis"] == "weld_throat_area"
    stud_shear = result(welded_fatigue_detail(40))
    assert stud_shear["stress_type"] == "shear"
    assert stud_shear["stress_area_basis"] == "nominal_stud_section"


def test_durability_table_11_5_1_b_rejects_unmet_conditions_and_unsupported_geometry():
    with pytest.raises(ValueError):
        result(welded_fatigue_detail(8, no_unrepaired_stop_starts_verified=False))
    cope_hole = result(welded_fatigue_detail(20, cope_hole_present=True))
    assert cope_hole["detail_category_mpa"] == 71
    with pytest.raises(ValueError):
        result(
            welded_fatigue_detail(20, cope_hole_present=True, cope_hole_not_filled_verified=False)
        )
    with pytest.raises(ValueError, match="misalignment"):
        result(welded_fatigue_detail(26, maximum_plate_misalignment_mm=1.5))
    with pytest.raises(ValueError, match="at least 10 mm"):
        result(welded_fatigue_detail(23, backing_weld_end_distance_mm=9.999))
    with pytest.raises(ValueError, match="b < 8t"):
        result(welded_fatigue_detail(30, overlap_width_mm=80))
    with pytest.raises(ValueError, match="end weld"):
        result(
            welded_fatigue_detail(
                38,
                cover_plate_wider_than_flange=True,
                cover_plate_end_weld_present=False,
            )
        )
    with pytest.raises(ValueError, match="no listed category"):
        result(welded_fatigue_detail(38, flange_thickness_mm=25, cover_plate_thickness_mm=25.1))
    with pytest.raises(ValueError, match="base material"):
        result(welded_fatigue_detail(34, failure_location="weld"))


def test_d07_exemption_strict_boundary():
    d = {
        "check_type": "fatigue_exemption",
        "normal_stress_range_mpa": 27,
        "shear_stress_range_mpa": 27,
        "cycles": 1e9,
        "capacity_factor": 1,
        "redundant_load_path": True,
        "reference_conditions_satisfied": True,
    }
    assert not result(d)["assessment_exempt"]
    d["normal_stress_range_mpa"] = d["shear_stress_range_mpa"] = 26.999
    assert result(d)["assessment_exempt"]
    d.update(normal_stress_range_mpa=36, shear_stress_range_mpa=36, cycles=2e6)
    assert not result(d)["assessment_exempt"]
    d["cycles"] = 1999999
    assert result(d)["assessment_exempt"]


def test_d08_fire_yield_and_moduli():
    d = {
        "check_type": "fire_material",
        "temperature_c": 215,
        "yield_strength_20_mpa": 350,
        "elastic_modulus_20_mpa": 200000,
        "poisson_ratio": 0.25,
    }
    assert result(d)["yield_ratio"] == 1
    d["temperature_c"] = 560
    assert result(d)["yield_ratio"] == pytest.approx(0.5)
    d["temperature_c"] = 800
    r = result(d)
    assert r["elastic_ratio"] == pytest.approx(138 / 746.5)
    assert r["shear_modulus_mpa"] == pytest.approx(r["elastic_modulus_mpa"] / 2.5)
    d["temperature_c"] = 905
    assert result(d)["yield_strength_mpa"] == 0


def test_d09_fire_limiting_and_unprotected():
    assert result({"check_type": "fire_limiting_temperature", "fire_action_ratio": 0.5}) == {
        "limiting_temperature_c": 560
    }
    d = {
        "check_type": "fire_unprotected",
        "limiting_temperature_c": 500,
        "surface_mass_ratio_m2_per_tonne": 10,
        "exposure_sides": 3,
        "required_frl_min": 27.5,
    }
    assert result(d)["psa_min"] == pytest.approx(27.5)
    assert result(d)["check_satisfied"]
    d["exposure_sides"] = 4
    assert result(d)["psa_min"] == pytest.approx(19.1)
    d["limiting_temperature_c"] = 260
    assert result(d)["psa_min"] == pytest.approx(9.55)
    d["limiting_temperature_c"] = 20
    assert result(d)["psa_min"] == 0
    d["limiting_temperature_c"] = 751
    with pytest.raises(ValueError):
        result(d)


def test_d10_fire_prototype_gates():
    d = {
        "check_type": "fire_single_test",
        "prototype_psa_min": 60,
        "required_frl_min": 60,
        "protection_thickness_mm": 20,
        "prototype_protection_thickness_mm": 20,
        "surface_mass_ratio_m2_per_tonne": 10,
        "prototype_surface_mass_ratio_m2_per_tonne": 10,
        "fire_action_ratio": 0.5,
        "prototype_fire_action_ratio": 0.5,
        "same_protection_system": True,
        "same_exposure": True,
        "same_supports": True,
        "restraints_not_less_favourable": True,
    }
    assert result(d)["check_satisfied"]
    d["same_supports"] = False
    assert not result(d)["check_satisfied"]


def single_test_history(**changes):
    return {
        "check_type": "fire_single_test_history",
        "limiting_temperature_c": 500,
        "required_frl_min": 8.33,
        "protection_thickness_mm": 25,
        "prototype_protection_thickness_mm": 20,
        "surface_mass_ratio_m2_per_tonne": 10,
        "prototype_surface_mass_ratio_m2_per_tonne": 12,
        "same_protection_system": True,
        "same_exposure_condition": True,
        "prototype_was_unloaded": False,
        "stickability_demonstrated": False,
        "temperature_history": [
            {"time_min": 0, "steel_temperature_c": 20},
            {"time_min": 5, "steel_temperature_c": 300},
            {"time_min": 10, "steel_temperature_c": 600},
        ],
        **changes,
    }


def test_single_test_history_crossing_and_lower_bound():
    values = result(single_test_history())
    assert values["test_applicable"]
    assert values["limiting_temperature_attained"]
    assert values["attained_time_min"] == pytest.approx(8.333333333333334)
    assert values["check_satisfied"]
    values = result(
        single_test_history(
            limiting_temperature_c=700,
            required_frl_min=10,
        )
    )
    assert not values["limiting_temperature_attained"]
    assert values["attained_time_min"] is None
    assert values["psa_min_lower_bound"] == 10
    assert values["check_satisfied"]


@pytest.mark.parametrize(
    "changes",
    [
        {"same_protection_system": False},
        {"same_exposure_condition": False},
        {"protection_thickness_mm": 19},
        {"surface_mass_ratio_m2_per_tonne": 13},
        {"prototype_was_unloaded": True, "stickability_demonstrated": False},
    ],
)
def test_single_test_history_applicability_conditions(changes):
    values = result(single_test_history(**changes))
    assert not values["test_applicable"]
    assert not values["check_satisfied"]


def test_single_test_history_requires_ordered_time_series():
    data = single_test_history()
    data["temperature_history"][2]["time_min"] = 4
    with pytest.raises(ValueError, match="start at zero"):
        run_durability(data)


def test_web_penetration_protection_greatest_thickness_and_extent():
    data = {
        "check_type": "web_penetration_protection",
        "required_thickness_above_mm": 25,
        "required_thickness_below_mm": 30,
        "required_thickness_whole_section_mm": 27,
        "provided_thickness_mm": 30,
        "beam_depth_mm": 450,
        "protected_depth_mm": 450,
        "left_extension_mm": 450,
        "right_extension_mm": 450,
    }
    values = result(data)
    assert values["required_thickness_mm"] == 30
    assert values["minimum_extension_each_side_mm"] == 450
    assert values["check_satisfied"]
    data["right_extension_mm"] = 449.999
    assert not result(data)["check_satisfied"]
    data.update(beam_depth_mm=250, protected_depth_mm=250, right_extension_mm=300)
    assert result(data)["minimum_extension_each_side_mm"] == 300
    data["provided_thickness_mm"] = 29.999
    assert not result(data)["thickness_satisfied"]


def test_limited_ductile_brace_connections_match_full_member_capacity():
    data = {
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
    values = result(data)
    assert values["connection_checks"][0]["required_connection_capacity_kn"] == 200
    assert values["check_satisfied"]
    data["brace_connections"][0]["connection_design_capacity_kn"] = 199.999
    assert not result(data)["check_satisfied"]


def seismic_plastic_region_fabrication_data():
    return {
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


def test_seismic_checks_require_complete_input_schedule_attestations():
    limited_brace = {
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
    intermediate_frame = {
        "check_type": "intermediate_moment_frame_stiffeners",
        "intermediate_moment_frame_applicability_verified": True,
        "all_applicable_web_stiffeners_listed_verified": True,
        "web_stiffeners": [],
    }
    cases = [
        (limited_brace, "all_applicable_brace_connections_listed_verified"),
        (intermediate_frame, "all_applicable_web_stiffeners_listed_verified"),
        (
            seismic_plastic_region_fabrication_data(),
            "all_plastic_region_edges_and_holes_listed_verified",
        ),
        (
            concentric_brace_connection_detailing_data(),
            "all_concentric_braced_frame_welds_and_stiffeners_listed_verified",
        ),
    ]
    for data, attestation in cases:
        del data[attestation]
        with pytest.raises(ValueError):
            result(data)


def test_seismic_plastic_region_fabrication_accepts_clause_boundaries():
    values = result(seismic_plastic_region_fabrication_data())
    assert values["gas_cut_edge_checks"][0]["maximum_surface_roughness_um"] == 12
    assert values["check_satisfied"]


@pytest.mark.parametrize(
    ("collection", "update"),
    [
        ("sheared_edges", {"sheared_oversize_and_machined_to_remove_all_sheared_surface": False}),
        ("gas_cut_edges", {"surface_roughness_um": 12.001}),
        ("fastener_holes", {"hole_making_method": "punched_full_size"}),
    ],
)
def test_seismic_plastic_region_fabrication_rejects_noncompliant_records(collection, update):
    data = seismic_plastic_region_fabrication_data()
    data[collection][0].update(update)
    assert not result(data)["check_satisfied"]


def test_intermediate_moment_frame_stiffeners_check_both_clause_conditions():
    data = {
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
    assert result(data)["check_satisfied"]
    data["web_stiffeners"][0]["butt_welded_to_both_flanges"] = False
    assert not result(data)["check_satisfied"]


def test_concentric_tension_brace_member_and_connection_limits():
    data = {
        "check_type": "concentric_tension_brace",
        "bearing_wall_or_building_frame_system_verified": True,
        "design_tension_action_kn": 85,
        "member_design_tensile_capacity_kn": 100,
        "connection_design_tensile_capacity_kn": 100,
    }
    values = result(data)
    assert values["member_action_limit_kn"] == 85
    assert values["check_satisfied"]
    data["design_tension_action_kn"] = 85.001
    assert not result(data)["member_action_satisfied"]
    data.update(design_tension_action_kn=80, connection_design_tensile_capacity_kn=99.999)
    assert not result(data)["connection_capacity_satisfied"]


def concentric_brace_connection_detailing_data():
    return {
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
            }
        ],
    }


@pytest.mark.parametrize(
    ("population", "requirements"),
    [
        ("butt_in_tension", (100, 100, 100, 10)),
        ("butt_not_in_tension", (100, 50, 10, 2)),
        ("other_welds", (100, 20, 5, 2)),
    ],
)
def test_concentric_brace_detailing_table_minima_at_exact_limits(population, requirements):
    data = concentric_brace_connection_detailing_data()
    group = data["weld_groups"][0]
    group["weld_population"] = population
    (
        group["visual_scanning_percent"],
        group["visual_examination_percent"],
        group["magnetic_particle_or_dye_penetrant_percent"],
        group["ultrasonics_or_radiography_percent"],
    ) = requirements
    values = result(data)
    check = values["weld_group_checks"][0]
    assert values["check_satisfied"]
    assert check["required_visual_scanning_percent"] == requirements[0]
    assert check["required_visual_examination_percent"] == requirements[1]
    assert check["required_magnetic_particle_or_dye_penetrant_percent"] == requirements[2]
    assert check["required_ultrasonics_or_radiography_percent"] == requirements[3]


@pytest.mark.parametrize(
    ("population", "field", "minimum"),
    [
        ("butt_in_tension", "visual_scanning_percent", 100),
        ("butt_in_tension", "visual_examination_percent", 100),
        ("butt_in_tension", "magnetic_particle_or_dye_penetrant_percent", 100),
        ("butt_in_tension", "ultrasonics_or_radiography_percent", 10),
        ("butt_not_in_tension", "visual_scanning_percent", 100),
        ("butt_not_in_tension", "visual_examination_percent", 50),
        ("butt_not_in_tension", "magnetic_particle_or_dye_penetrant_percent", 10),
        ("butt_not_in_tension", "ultrasonics_or_radiography_percent", 2),
        ("other_welds", "visual_scanning_percent", 100),
        ("other_welds", "visual_examination_percent", 20),
        ("other_welds", "magnetic_particle_or_dye_penetrant_percent", 5),
        ("other_welds", "ultrasonics_or_radiography_percent", 2),
    ],
)
def test_concentric_brace_detailing_rejects_each_short_inspection(population, field, minimum):
    data = concentric_brace_connection_detailing_data()
    group = data["weld_groups"][0]
    group["weld_population"] = population
    group[field] = minimum - 0.001
    values = result(data)
    assert not values["check_satisfied"]
    assert not values["weld_group_checks"][0][field.replace("_percent", "_satisfied")]


@pytest.mark.parametrize(
    "condition",
    ["extends_full_depth_between_flanges", "butt_welded_to_both_flanges"],
)
def test_concentric_brace_detailing_rejects_noncompliant_stiffener(condition):
    data = concentric_brace_connection_detailing_data()
    data["web_stiffeners"][0][condition] = False
    assert not result(data)["check_satisfied"]


def test_concentric_brace_detailing_rejects_non_sp_weld_category():
    data = concentric_brace_connection_detailing_data()
    data["weld_groups"][0]["weld_category"] = "GP"
    values = result(data)
    assert not values["all_welds_special_purpose_satisfied"]
    assert not values["check_satisfied"]


def test_concentric_brace_detailing_allows_no_applicable_web_stiffeners():
    data = concentric_brace_connection_detailing_data()
    data["web_stiffeners"] = []
    assert result(data)["stiffeners_satisfied"]


def test_d11_protected_regression():
    # Synthetic coefficient evaluation, not a qualifying fire test calibration.
    d = {
        "check_type": "fire_protected_regression",
        "coefficients": [1, 1, 1, 1, 1, 1, 1],
        "temperature_c": 500,
        "protection_thickness_mm": 20,
        "surface_mass_ratio_m2_per_tonne": 10,
        "required_frl_min": 60,
        "test_count": 9,
        "test_series_conditions_satisfied": True,
        "inside_reviewed_interpolation_window": True,
    }
    assert result(d)["psa_min"] == pytest.approx(11573)
    d["inside_reviewed_interpolation_window"] = False
    with pytest.raises(ValueError):
        result(d)


def _protected_regression_fit_input():
    coefficients = [5, 0.4, 1.2, 0.06, 0.0008, 0.002, 0.1]
    geometries = [
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
    test_series = []
    for thickness, surface_mass_ratio in geometries:
        temperature_time_points = []
        for temperature in [300, 400, 500, 600]:
            features = [
                1,
                thickness,
                thickness / surface_mass_ratio,
                temperature,
                thickness * temperature,
                thickness * temperature / surface_mass_ratio,
                temperature / surface_mass_ratio,
            ]
            temperature_time_points.append(
                {
                    "temperature_c": temperature,
                    "time_min": sum(c * x for c, x in zip(coefficients, features, strict=True)),
                }
            )
        test_series.append(
            {
                "protection_thickness_mm": thickness,
                "surface_mass_ratio_m2_per_tonne": surface_mass_ratio,
                "prototype_was_unloaded": False,
                "stickability_demonstrated": False,
                "temperature_time_points": temperature_time_points,
            }
        )
    return {
        "check_type": "fire_protected_regression_fit",
        "protection_material_type": "low_density_insulation",
        "protection_dry_density_kg_m3": 450,
        "same_protection_system_and_exposure_verified": True,
        "exposure_sides": 4,
        "test_series": test_series,
    }, coefficients


def test_d11a_fit_qualifying_series_and_build_interpolation_window():
    data, expected_coefficients = _protected_regression_fit_input()
    fitted = result(data)
    assert fitted["coefficients"] == pytest.approx(expected_coefficients, abs=1e-10)
    assert fitted["correlation_coefficient"] == pytest.approx(1)
    assert fitted["root_mean_square_residual_min"] == pytest.approx(0, abs=1e-10)
    assert fitted["test_count"] == 10
    assert fitted["observation_count"] == 40
    assert fitted["test_temperature_range_c"] == [300, 600]
    assert len(fitted["interpolation_window_points"]) == 5
    assert fitted["calibration_eligible"]


def test_d11b_fit_rejects_rank_deficiency_and_unloaded_tests_without_stickability():
    data, _ = _protected_regression_fit_input()
    repeated = [dict(data["test_series"][0]) for _ in range(9)]
    data["test_series"] = repeated
    with pytest.raises(ValueError, match="determine all seven"):
        result(data)

    data, _ = _protected_regression_fit_input()
    data["test_series"][0]["prototype_was_unloaded"] = True
    with pytest.raises(ValueError, match="stickability"):
        result(data)


def test_d11c_fit_enforces_density_and_three_sided_group_prerequisites():
    data, _ = _protected_regression_fit_input()
    data["protection_dry_density_kg_m3"] = 1000
    with pytest.raises(ValueError):
        result(data)

    data, _ = _protected_regression_fit_input()
    del data["protection_dry_density_kg_m3"]
    with pytest.raises(ValueError):
        result(data)

    data, _ = _protected_regression_fit_input()
    data["exposure_sides"] = 3
    data["three_sided_grouping_verified"] = False
    with pytest.raises(ValueError):
        result(data)

    data["three_sided_grouping_verified"] = True
    assert result(data)["calibration_eligible"]

    data, _ = _protected_regression_fit_input()
    data["exposure_sides"] = 3
    data["three_sided_group_members"] = _three_sided_group_members()
    fitted = result(data)
    assert fitted["three_sided_group_qualification"]["group_satisfied"]
    assert fitted["three_sided_group_qualification"]["concrete_density_ratio"] == pytest.approx(
        1.25
    )

    data, _ = _protected_regression_fit_input()
    data["protection_material_type"] = "intumescent_or_ablative_coating"
    del data["protection_dry_density_kg_m3"]
    assert result(data)["correlation_coefficient"] > 0.9


def test_d11d_regression_uses_calculated_test_geometry_window():
    fitted_input, _ = _protected_regression_fit_input()
    fitted = result(fitted_input)
    data = {
        "check_type": "fire_protected_regression",
        "coefficients": fitted["coefficients"],
        "temperature_c": 500,
        "protection_thickness_mm": 25,
        "surface_mass_ratio_m2_per_tonne": 22,
        "required_frl_min": 60,
        "test_count": fitted["test_count"],
        "test_series_conditions_satisfied": True,
        "test_temperature_range_c": fitted["test_temperature_range_c"],
        "interpolation_window_points": fitted["interpolation_window_points"],
        "application_conditions": {
            "calibration_exposure_sides": fitted["exposure_sides"],
            "member_exposure_sides": 4,
            "same_protection_system": True,
            "same_protection_material_verified": True,
            "stickability_demonstrated_for_member": False,
        },
    }
    evaluated = result(data)
    assert evaluated["inside_interpolation_window"]
    assert evaluated["application_conditions"]["conditions_satisfied"]
    assert len(evaluated["interpolation_window_points"]) == 5

    data["protection_thickness_mm"] = 100
    with pytest.raises(ValueError, match="interpolation inside"):
        result(data)

    data["protection_thickness_mm"] = 25
    data["temperature_c"] = 601
    with pytest.raises(ValueError, match="temperature range"):
        result(data)

    data["temperature_c"] = 500
    data["inside_reviewed_interpolation_window"] = False
    with pytest.raises(ValueError, match="conflicts"):
        result(data)


def test_d11f_regression_reuse_checks_exposure_system_and_stickability():
    fitted_input, _ = _protected_regression_fit_input()
    fitted = result(fitted_input)
    data = {
        "check_type": "fire_protected_regression",
        "coefficients": fitted["coefficients"],
        "temperature_c": 500,
        "protection_thickness_mm": 25,
        "surface_mass_ratio_m2_per_tonne": 22,
        "required_frl_min": 60,
        "test_count": fitted["test_count"],
        "test_series_conditions_satisfied": True,
        "test_temperature_range_c": fitted["test_temperature_range_c"],
        "interpolation_window_points": fitted["interpolation_window_points"],
        "application_conditions": {
            "calibration_exposure_sides": 4,
            "member_exposure_sides": 3,
            "same_protection_system": True,
            "same_protection_material_verified": True,
            "stickability_demonstrated_for_member": True,
            "member_three_sided_group_members": _three_sided_group_members(),
        },
    }
    values = result(data)
    assert values["application_conditions"]["member_three_sided_group_satisfied"]

    data["application_conditions"]["stickability_demonstrated_for_member"] = False
    with pytest.raises(ValueError, match="requires demonstrated stickability"):
        result(data)

    data["application_conditions"].update(
        calibration_exposure_sides=3,
        member_exposure_sides=4,
        stickability_demonstrated_for_member=True,
    )
    del data["application_conditions"]["member_three_sided_group_members"]
    with pytest.raises(ValueError, match="cannot qualify a four-sided"):
        result(data)

    data["application_conditions"].update(
        calibration_exposure_sides=4,
        member_exposure_sides=4,
        same_protection_system=False,
        stickability_demonstrated_for_member=False,
    )
    with pytest.raises(ValueError, match="another protection system"):
        result(data)

    data["application_conditions"]["stickability_demonstrated_for_member"] = True
    assert result(data)["application_conditions"]["conditions_satisfied"]


def test_d11e_regression_rejects_collinear_test_geometry_window():
    data = {
        "check_type": "fire_protected_regression",
        "coefficients": [1, 1, 1, 1, 1, 1, 1],
        "temperature_c": 500,
        "protection_thickness_mm": 20,
        "surface_mass_ratio_m2_per_tonne": 20,
        "required_frl_min": 60,
        "test_count": 9,
        "test_series_conditions_satisfied": True,
        "test_temperature_range_c": [300, 600],
        "application_conditions": {
            "calibration_exposure_sides": 4,
            "member_exposure_sides": 4,
            "same_protection_system": True,
            "same_protection_material_verified": True,
            "stickability_demonstrated_for_member": False,
        },
        "interpolation_window_points": [
            {"protection_thickness_mm": 10, "surface_mass_ratio_m2_per_tonne": 10},
            {"protection_thickness_mm": 20, "surface_mass_ratio_m2_per_tonne": 20},
            {"protection_thickness_mm": 30, "surface_mass_ratio_m2_per_tonne": 30},
        ],
    }
    with pytest.raises(ValueError, match="collinear"):
        result(data)


def _three_sided_group_members():
    return [
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
    ]


def test_three_sided_group_checks_density_thickness_and_rib_void_limits():
    members = _three_sided_group_members()
    data = {"check_type": "fire_three_sided_group", "members": members}
    values = result(data)
    assert values["concrete_density_ratio"] == pytest.approx(1.25)
    assert values["effective_thickness_ratio"] == pytest.approx(1.25)
    assert values["effective_thicknesses_mm"] == pytest.approx([150, 187.5])
    assert values["rib_voids_state"] == "open"
    assert values["group_satisfied"]

    members[1]["concrete_density_kg_m3"] = 2501
    assert not result(data)["concrete_density_satisfied"]

    members = _three_sided_group_members()
    members[1]["concrete_area_excluding_voids_mm2"] = 188000
    data["members"] = members
    assert not result(data)["effective_thickness_satisfied"]

    members = _three_sided_group_members()
    members[1]["rib_void_condition"] = "blocked"
    data["members"] = members
    values = result(data)
    assert values["rib_voids_state"] == "mixed"
    assert not values["rib_voids_consistent"]
    assert not values["group_satisfied"]


def test_connection_fire_protection_uses_maximum_framing_thickness_on_every_component():
    data = {
        "check_type": "fire_connection_protection",
        "framing_members": [
            {"required_protection_thickness_mm": 25},
            {"required_protection_thickness_mm": 40},
            {"required_protection_thickness_mm": 35},
        ],
        "connection_components": [
            {
                "component_id": "bolts-1",
                "component_type": "bolt_head",
                "provided_protection_thickness_mm": 40,
                "protection_maintained_over_component": True,
            },
            {
                "component_id": "weld-1",
                "component_type": "weld",
                "provided_protection_thickness_mm": 40,
                "protection_maintained_over_component": True,
            },
            {
                "component_id": "splice-1",
                "component_type": "splice_plate",
                "provided_protection_thickness_mm": 40,
                "protection_maintained_over_component": True,
            },
        ],
    }
    values = result(data)
    assert values["required_protection_thickness_mm"] == 40
    assert values["framing_member_count"] == 3
    assert values["check_satisfied"]
    assert all(component["component_satisfied"] for component in values["component_checks"])

    data["connection_components"][2]["provided_protection_thickness_mm"] = 39.999
    values = result(data)
    assert not values["component_checks"][2]["thickness_satisfied"]
    assert not values["check_satisfied"]

    data["connection_components"][2]["provided_protection_thickness_mm"] = 40
    data["connection_components"][1]["protection_maintained_over_component"] = False
    values = result(data)
    assert not values["component_checks"][1]["component_satisfied"]
    assert not values["check_satisfied"]

    data["connection_components"][2]["component_id"] = "weld-1"
    with pytest.raises(ValueError, match="identifiers must be unique"):
        result(data)


def brittle():
    return {
        "check_type": "brittle_fracture",
        "steel_type": "1",
        "thickness_mm": 6,
        "design_service_temperature_c": -19,
        "outer_fibre_strain_percent": 0,
        "post_weld_heat_treatment_c": 0,
        "impact_test_temperature_c": 100,
        "fabrication_erection_requirements_satisfied": True,
    }


def design_service_temperature(**changes):
    return {
        "check_type": "design_service_temperature",
        "lodmat_temperature_c": 6,
        "lodmat_assessment_verified": True,
        "lodmat_evidence_reference": "AS4100-FIGURE-10.3.2-SITE-01",
        "especially_low_local_ambient_conditions_verified": False,
        **changes,
    }


def test_clause_10_3_design_service_temperature_adjustments():
    ordinary = run_durability(design_service_temperature())
    assert ordinary["clauses"] == ["10.3.2"]
    assert ordinary["results"]["basic_design_service_temperature_c"] == 6
    assert ordinary["results"]["design_service_temperature_c"] == 6

    local = run_durability(
        design_service_temperature(
            especially_low_local_ambient_conditions_verified=True,
            special_local_temperature_evidence_reference="SITE-LOW-TEMP-ASSESSMENT-01",
        )
    )
    assert local["results"]["special_local_ambient_adjustment_c"] == -5
    assert local["results"]["basic_design_service_temperature_c"] == 1

    record = run_durability(
        design_service_temperature(
            record_based_low_temperature_c=-2,
            critical_structure_and_temperature_records_verified=True,
            recorded_temperature_evidence_reference="BOM-RECORD-01",
        )
    )
    assert record["results"]["basic_design_service_temperature_c"] == -2
    assert record["results"]["record_based_temperature_controls"]

    cooled = run_durability(
        design_service_temperature(
            artificial_cooling_minimum_temperature_c=-25,
            artificial_cooling_below_basic_temperature_verified=True,
            artificial_cooling_evidence_reference="REFRIGERATED-SPACE-01",
        )
    )
    assert cooled["clauses"] == ["10.3.2", "10.3.3"]
    assert cooled["results"]["design_service_temperature_c"] == -25
    assert cooled["results"]["artificial_cooling_controls"]


@pytest.mark.parametrize(("lodmat", "expected"), [(0, 0), (20, 20)])
def test_clause_10_3_lodmat_figure_temperature_boundaries(lodmat, expected):
    values = run_durability(design_service_temperature(lodmat_temperature_c=lodmat))["results"]
    assert values["basic_design_service_temperature_c"] == expected
    assert values["design_service_temperature_c"] == expected


@pytest.mark.parametrize("lodmat", [-0.1, 20.1])
def test_clause_10_3_rejects_lodmat_outside_figure_range(lodmat):
    with pytest.raises(ValueError):
        run_durability(design_service_temperature(lodmat_temperature_c=lodmat))


def test_clause_10_3_design_service_temperature_uses_coldest_verified_basis():
    result = run_durability(
        design_service_temperature(
            especially_low_local_ambient_conditions_verified=True,
            special_local_temperature_evidence_reference="SITE-LOW-TEMP-ASSESSMENT-01",
            record_based_low_temperature_c=-2,
            critical_structure_and_temperature_records_verified=True,
            recorded_temperature_evidence_reference="BOM-RECORD-01",
            artificial_cooling_minimum_temperature_c=-25,
            artificial_cooling_below_basic_temperature_verified=True,
            artificial_cooling_evidence_reference="REFRIGERATED-SPACE-01",
        )
    )
    values = result["results"]
    assert values["basic_design_service_temperature_c"] == -2
    assert values["record_based_temperature_controls"]
    assert values["design_service_temperature_c"] == -25


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {
                "record_based_low_temperature_c": 6,
                "critical_structure_and_temperature_records_verified": True,
                "recorded_temperature_evidence_reference": "BOM-RECORD-01",
            },
            "colder than LODMAT",
        ),
        (
            {
                "artificial_cooling_minimum_temperature_c": 6,
                "artificial_cooling_below_basic_temperature_verified": True,
                "artificial_cooling_evidence_reference": "REFRIGERATED-SPACE-01",
            },
            "below the basic design temperature",
        ),
        (
            {"especially_low_local_ambient_conditions_verified": True},
            None,
        ),
        (
            {"record_based_low_temperature_c": -12},
            None,
        ),
        (
            {"artificial_cooling_minimum_temperature_c": -25},
            None,
        ),
    ],
)
def test_clause_10_3_rejects_unverified_or_inconsistent_temperature_adjustments(changes, message):
    with pytest.raises(ValueError) as exc_info:
        run_durability(design_service_temperature(**changes))
    if message is not None:
        assert message in str(exc_info.value)


def test_d12_brittle_table_boundaries_and_strain():
    d = brittle()
    assert result(d)["permissible_service_temperature_c"] == -20
    assert result(d)["check_satisfied"]
    d["thickness_mm"] = 6.001
    assert result(d)["permissible_service_temperature_c"] == -10
    assert not result(d)["check_satisfied"]
    d.update(thickness_mm=6, outer_fibre_strain_percent=11)
    assert result(d)["permissible_service_temperature_c"] == 1
    d["post_weld_heat_treatment_c"] = 500
    assert result(d)["permissible_service_temperature_c"] == 1
    d["post_weld_heat_treatment_c"] = 620
    assert result(d)["permissible_service_temperature_c"] == -20
    d["impact_test_temperature_c"] = -40
    assert result(d)["permissible_service_temperature_c"] == -40


@pytest.mark.parametrize(
    ("product_standard", "grade", "expected_steel_type"),
    [
        ("AS/NZS 1163", "C250", "1"),
        ("AS/NZS 1163", "C250L0", "2"),
        ("AS/NZS 3679.1", "300S0", "2S"),
        ("AS/NZS 1594", "XF300", "3"),
        ("AS/NZS 1594", "HA350", "4"),
        ("AS/NZS 1163", "C350L0", "5"),
        ("AS/NZS 3679.1", "350S0", "5S"),
        ("AS/NZS 1594", "XF400", "6"),
        ("AS/NZS 1163", "C450", "7A"),
        ("AS/NZS 1163", "C450L0", "7B"),
        ("AS/NZS 3678", "450Y40", "7C"),
        ("AS/NZS 1594", "XF500", "8C"),
        ("AS 3597", "500", "8Q"),
        ("AS 3597", "600", "9Q"),
        ("AS 3597", "700", "10Q"),
        ("AS/NZS 1594", "HA300/1", "1"),
        ("AS/NZS 3678", "WR350L0", "5"),
        ("AS/NZS 3679.2", "400L40", "6"),
    ],
)
def test_clause_10_4_4_grade_selects_table_steel_type(product_standard, grade, expected_steel_type):
    response = run_durability(
        {
            "check_type": "steel_grade_selection",
            "product_standard": product_standard,
            "grade": grade,
            "required_steel_type": expected_steel_type,
        }
    )
    assert response["clauses"] == ["10.4.4"]
    assert response["results"]["steel_type"] == expected_steel_type
    assert response["results"]["grade_selection_satisfied"]


@pytest.mark.parametrize(
    ("product_standard", "grade"),
    [("AS/NZS 1163", "C500"), ("AS/NZS 3678", "300L0"), ("AS 3597", "800")],
)
def test_clause_10_4_4_rejects_unlisted_standard_grade_pairs(product_standard, grade):
    with pytest.raises(ValueError, match="no steel-type entry in Table 10.4.4"):
        run_durability(
            {
                "check_type": "steel_grade_selection",
                "product_standard": product_standard,
                "grade": grade,
                "required_steel_type": "1",
            }
        )


def test_clause_10_4_4_grade_that_maps_to_another_type_fails_selection():
    response = run_durability(
        {
            "check_type": "steel_grade_selection",
            "product_standard": "AS/NZS 1163",
            "grade": "C250",
            "required_steel_type": "2",
        }
    )
    assert response["clauses"] == ["10.4.4"]
    assert response["results"]["steel_type"] == "1"
    assert not response["results"]["grade_selection_satisfied"]


def fracture_assessment_evidence(**changes):
    return {
        "check_type": "fracture_assessment_evidence",
        "selected_steel_grade": "300L15",
        "selected_steel_type": "3",
        "assessment_method": "BS 7910",
        "assessment_report_reference": "FRACTURE-ANALYSIS-REPORT-01",
        "parent_steel_toughness_reference": "PARENT-STEEL-TOUGHNESS-01",
        "weld_metal_toughness_reference": "WELD-METAL-TOUGHNESS-01",
        "heat_affected_zone_toughness_reference": "HAZ-TOUGHNESS-01",
        "weld_nondestructive_examination_reference": "WELD-NDE-REPORT-01",
        "heat_affected_zone_nondestructive_examination_reference": "HAZ-NDE-REPORT-01",
        "selected_grade_matches_assessed_material_verified": True,
        "all_relevant_welds_and_haz_zones_included_verified": True,
        "assessment_result": "acceptable",
        **changes,
    }


def test_clause_10_5_records_complete_fracture_assessment_evidence():
    response = run_durability(fracture_assessment_evidence())
    values = response["results"]
    assert response["clauses"] == ["10.5"]
    assert values["selected_steel_grade"] == "300L15"
    assert values["parent_steel_toughness_reference"] == "PARENT-STEEL-TOUGHNESS-01"
    assert values["weld_metal_toughness_reference"] == "WELD-METAL-TOUGHNESS-01"
    assert values["heat_affected_zone_toughness_reference"] == "HAZ-TOUGHNESS-01"
    assert values["weld_nondestructive_examination_reference"] == "WELD-NDE-REPORT-01"
    assert values["heat_affected_zone_nondestructive_examination_reference"] == "HAZ-NDE-REPORT-01"
    assert values["evidence_complete"]
    assert values["check_satisfied"]
    assert not values["fracture_mechanics_calculated_by_plugin"]


@pytest.mark.parametrize("assessment_result", ["unacceptable", "inconclusive"])
def test_clause_10_5_external_nonacceptable_result_does_not_pass(assessment_result):
    values = run_durability(fracture_assessment_evidence(assessment_result=assessment_result))[
        "results"
    ]
    assert values["evidence_complete"]
    assert not values["check_satisfied"]


def test_clause_10_5_requires_nde_evidence_for_weld_and_heat_affected_zone():
    with pytest.raises(ValueError):
        run_durability(
            fracture_assessment_evidence(
                heat_affected_zone_nondestructive_examination_reference=None
            )
        )


def nonconforming_steel_impact_test(**changes):
    return {
        "check_type": "nonconforming_steel_impact_test",
        "plate_thickness_mm": 12,
        "specimen_thickness_mm": 10,
        "absorbed_energy_j": [20, 27, 34],
        "grade_standard_has_no_minimum_impact_properties_verified": True,
        "permissible_temperature_unknown_or_warmer_than_design_verified": True,
        "mock_up_grade_dimensions_and_strain_verified": True,
        "three_specimens_from_maximum_strain_region_verified": True,
        "tested_at_design_service_temperature_verified": True,
        "specimen_thickness_selection_verified": True,
        "evidence_reference": "CHARPY-MOCKUP-REPORT-01",
        **changes,
    }


def specified_impact_properties_test(**changes):
    inputs = {
        "check_type": "specified_impact_properties_test",
        "plate_thickness_mm": 8,
        "specimen_thickness_mm": 7.5,
        "absorbed_energy_j": [13.5, 18, 22.5],
        "specified_minimum_average_energy_j": 24,
        "specified_minimum_single_energy_j": 18,
        "grade_standard_minimums_verified": True,
        "grade_standard_reference": "PRODUCT-STANDARD-CHARPY-REQ-01",
        "permissible_temperature_unknown_or_warmer_than_design_verified": True,
        "mock_up_grade_dimensions_and_strain_verified": True,
        "three_specimens_from_maximum_strain_region_verified": True,
        "tested_at_design_service_temperature_verified": True,
        "specimen_thickness_selection_verified": True,
        "evidence_reference": "CHARPY-MOCKUP-REPORT-02",
        **changes,
    }
    return {key: value for key, value in inputs.items() if value is not None}


def test_clause_10_4_3_4_full_size_charpy_thresholds():
    result = run_durability(nonconforming_steel_impact_test())
    values = result["results"]
    assert result["clauses"] == ["10.4.3.4(d)"]
    assert values["energy_reduction_factor"] == 1
    assert values["required_average_energy_j"] == 27
    assert values["required_minimum_single_energy_j"] == 20
    assert values["measured_average_energy_j"] == 27
    assert values["minimum_measured_energy_j"] == 20
    assert values["check_satisfied"]


def test_clause_10_4_3_4_subsize_charpy_energy_thresholds_scale_proportionally():
    result = run_durability(
        nonconforming_steel_impact_test(
            plate_thickness_mm=8,
            specimen_thickness_mm=7.5,
            absorbed_energy_j=[15, 20.25, 25.5],
        )
    )
    values = result["results"]
    assert result["clauses"] == ["10.4.3.4(d)", "10.4.3.4(e)"]
    assert values["energy_reduction_factor"] == pytest.approx(0.75)
    assert values["required_average_energy_j"] == pytest.approx(20.25)
    assert values["required_minimum_single_energy_j"] == pytest.approx(15)
    assert values["measured_average_energy_j"] == pytest.approx(20.25)
    assert values["check_satisfied"]


@pytest.mark.parametrize(
    ("energies", "expected_average_satisfied", "expected_minimum_satisfied"),
    [([20, 25, 30], False, True), ([19, 31, 31], True, False)],
)
def test_clause_10_4_3_4_requires_average_and_each_specimen_threshold(
    energies, expected_average_satisfied, expected_minimum_satisfied
):
    values = run_durability(nonconforming_steel_impact_test(absorbed_energy_j=energies))["results"]
    assert values["average_energy_satisfied"] is expected_average_satisfied
    assert values["minimum_single_energy_satisfied"] is expected_minimum_satisfied
    assert not values["check_satisfied"]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {"permissible_temperature_unknown_or_warmer_than_design_verified": False},
            None,
        ),
        (
            {"plate_thickness_mm": 12, "specimen_thickness_mm": 7.5},
            "Use a 10 mm specimen",
        ),
        (
            {"plate_thickness_mm": 7, "specimen_thickness_mm": 7.5},
            "must not exceed the plate thickness",
        ),
        (
            {"grade_standard_has_no_minimum_impact_properties_verified": False},
            None,
        ),
    ],
)
def test_clause_10_4_3_4_rejects_inapplicable_or_invalid_specimens(changes, message):
    with pytest.raises(ValueError) as exc_info:
        run_durability(nonconforming_steel_impact_test(**changes))
    if message is not None:
        assert message in str(exc_info.value)


def test_clause_10_4_3_4_specified_grade_minima_and_subsize_reduction():
    result = run_durability(specified_impact_properties_test())
    values = result["results"]
    assert result["clauses"] == [
        "10.4.3.4(a)",
        "10.4.3.4(b)",
        "10.4.3.4(c)",
        "10.4.3.4(e)",
    ]
    assert values["energy_reduction_factor"] == pytest.approx(0.75)
    assert values["required_average_energy_j"] == pytest.approx(18)
    assert values["required_minimum_single_energy_j"] == pytest.approx(13.5)
    assert values["measured_average_energy_j"] == pytest.approx(18)
    assert values["minimum_measured_energy_j"] == pytest.approx(13.5)
    assert values["average_energy_satisfied"]
    assert values["minimum_single_energy_satisfied"]
    assert values["check_satisfied"]


@pytest.mark.parametrize(
    ("changes", "expected_average", "expected_single", "expected_check"),
    [
        ({"specified_minimum_average_energy_j": 25}, False, True, False),
        ({"specified_minimum_single_energy_j": 19}, True, False, False),
        ({"specified_minimum_single_energy_j": None}, True, None, True),
        ({"specified_minimum_average_energy_j": None}, None, True, True),
    ],
)
def test_clause_10_4_3_4_specified_minima_are_checked_independently(
    changes, expected_average, expected_single, expected_check
):
    values = run_durability(specified_impact_properties_test(**changes))["results"]
    assert values["average_energy_satisfied"] is expected_average
    assert values["minimum_single_energy_satisfied"] is expected_single
    assert values["check_satisfied"] is expected_check


def test_clause_10_4_3_4_specified_minimum_route_requires_a_product_standard_threshold():
    with pytest.raises(ValueError):
        run_durability(
            specified_impact_properties_test(
                specified_minimum_average_energy_j=None,
                specified_minimum_single_energy_j=None,
            )
        )


def test_d13_unavailable_steel_and_seismic_audit():
    d = brittle()
    d.update(steel_type="8C", thickness_mm=13)
    with pytest.raises(ValueError):
        result(d)
    d = {
        "check_type": "earthquake_audit",
        "structural_system": "intermediate_moment",
        "grade_minimum_yield_mpa": 350,
        "design_storey_deflection_mm": 4,
    }
    r = result(d)
    assert r["ductility_factor"] == 3
    assert r["structural_performance_factor"] == 0.67
    assert r["minimum_panel_movement_mm"] == 6
    assert r["manual_review_required"]


@pytest.mark.parametrize("value", [None, [], {"check_type": "unknown"}])
def test_d14_input_shape(value):
    with pytest.raises(ValueError):
        result(value)


def test_d15_schema_and_nonfinite():
    Draft202012Validator.check_schema(INPUT_SCHEMA)
    Draft202012Validator.check_schema(OUTPUT_SCHEMA)
    d = fatigue()
    d["cycles"] = float("nan")
    with pytest.raises(ValueError):
        result(d)


def test_d16_modulus_upper_domain():
    d = {
        "check_type": "fire_modulus",
        "temperature_c": 1000,
        "elastic_modulus_20_mpa": 200000,
        "poisson_ratio": 0.25,
    }
    assert result(d)["elastic_ratio"] == 0
    d["poisson_ratio"] = 0.3
    with pytest.raises(ValueError, match="poisson_ratio"):
        result(d)
    d["poisson_ratio"] = 0.25
    d["elastic_modulus_20_mpa"] = 199999
    with pytest.raises(ValueError, match="elastic_modulus_20_mpa"):
        result(d)
    d["temperature_c"] = 1000.001
    with pytest.raises(ValueError):
        result(d)


def test_d17_exemption_overrides_normal_damage_only():
    d = fatigue("fatigue_variable")
    d["events"] = [{"stress_range_mpa": 50, "cycles": 1e10}]
    r = result(d)
    assert r["damage"] > 1
    assert r["further_assessment_exempt"]
    assert r["check_satisfied"]
    d["stress_type"] = "shear"
    assert not result(d)["check_satisfied"]


def test_d18_result_schema_rejects_wrong_result_fields():
    output = run_durability({"check_type": "fire_limiting_temperature", "fire_action_ratio": 1})
    output["results"]["made_up_value"] = 1
    assert not Draft202012Validator(OUTPUT_SCHEMA).is_valid(output)


def test_d19_impossible_stress_history_and_unsupported_category():
    d = fatigue()
    d["maximum_stress_magnitude_mpa"] = 49
    with pytest.raises(ValueError):
        result(d)
    d = fatigue()
    d["detail_category_mpa"] = 1000
    with pytest.raises(ValueError):
        result(d)
