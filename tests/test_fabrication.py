import pytest

from opencalcs_as4100.fabrication import run_fabrication


def plate(*, thickness=4, clearance=10, product=True, coverage=True, material=True):
    return {
        "type": "plate",
        "thickness_mm": thickness,
        "minimum_edge_clearance_mm": clearance,
        "coverage_geometry_verified": coverage,
        "product_verified": product,
        "material_as_nzs_3678_verified": material,
    }


def side(bears=False, washer=None):
    return {"bears_on_holed_ply": bears, "washer": washer}


def slot(hole_type="short_slot", **changes):
    return {
        "check_type": "bolt_hole",
        "hole_type": hole_type,
        "bolt_diameter_mm": 20,
        "hole_width_mm": 22,
        "hole_length_mm": 30 if hole_type == "short_slot" else 50,
        "not_base_plate_anchor_hole_verified": True,
        "connection_type": "friction_type",
        "subject_to_shear": True,
        "head_side": side(True, {"type": "hardened", "product_verified": True}),
        "nut_side": side(False),
        **({"alternate_plies_verified": True} if hole_type == "long_slot" else {}),
        **changes,
    }


def bolt_assembly(**changes):
    return {
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
        **changes,
    }


def fabrication_basis(**changes):
    return {
        "check_type": "fabrication_basis",
        "materials_conform_referenced_standards_verified": True,
        "surface_defects_removed_per_referenced_standards_verified": True,
        "steel_grade_identifiable_at_all_fabrication_stages_verified": True,
        "steel_classified_as_unidentified": False,
        "marking_does_not_damage_material_verified": True,
        "fabrication_per_as_nzs_5131_verified": True,
        "fabrication_methods_preserve_design_properties_verified": True,
        **changes,
    }


def tolerance(**changes):
    return {
        "check_type": "geometric_tolerance",
        "tolerance_type": "functional",
        "measured_deviation_mm": 1,
        "permissible_deviation_mm": 2,
        "as_nzs_5131_tolerance_limit_verified": True,
        "measurement_after_fabrication_and_corrosion_protection_verified": True,
        "coating_thickness_excluded_from_measurement_verified": True,
        **changes,
    }


def test_standard_hole_size_at_24_mm_boundary():
    at_24 = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "standard",
            "bolt_diameter_mm": 24,
            "hole_diameter_mm": 26,
        }
    )
    assert at_24["checked_conditions_satisfied"]
    assert at_24["values"]["maximum_hole_diameter_mm"] == 26

    above_24 = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "standard",
            "bolt_diameter_mm": 25,
            "hole_diameter_mm": 28,
        }
    )
    assert above_24["checked_conditions_satisfied"]
    assert above_24["values"]["maximum_hole_diameter_mm"] == 28
    too_large = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "standard",
            "bolt_diameter_mm": 25,
            "hole_diameter_mm": 28.001,
        }
    )
    assert not too_large["checked_conditions_satisfied"]


def test_base_plate_anchor_hole_requires_washer_at_three_mm_oversize():
    d = {
        "check_type": "bolt_hole",
        "hole_type": "base_plate_anchor",
        "bolt_diameter_mm": 14,
        "hole_diameter_mm": 20,
        "special_nut_washer": plate(thickness=4, clearance=10),
    }
    passed = run_fabrication(d)
    assert passed["checked_conditions_satisfied"]
    assert passed["values"]["special_nut_washer_required"]

    d["special_nut_washer"]["minimum_edge_clearance_mm"] = 9.99
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["special_nut_washer"] = plate(thickness=3.999, clearance=10)
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["special_nut_washer"] = None
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_base_plate_anchor_hole_maximum_and_washer_threshold():
    d = {
        "check_type": "bolt_hole",
        "hole_type": "base_plate_anchor",
        "bolt_diameter_mm": 14,
        "hole_diameter_mm": 16.999,
    }
    result = run_fabrication(d)
    assert result["checked_conditions_satisfied"]
    assert not result["values"]["special_nut_washer_required"]
    d["hole_diameter_mm"] = 20.001
    assert not run_fabrication(d)["checked_conditions_satisfied"]

    d["hole_diameter_mm"] = 17
    d["special_nut_washer"] = plate(clearance=8.5)
    result = run_fabrication(d)
    assert result["checked_conditions_satisfied"]
    assert result["values"]["special_nut_washer_required"]


def test_oversize_hole_maximum_and_bearing_surface_washers():
    d = {
        "check_type": "bolt_hole",
        "hole_type": "oversize",
        "bolt_diameter_mm": 20,
        "hole_diameter_mm": 28,
        "not_base_plate_anchor_hole_verified": True,
        "connection_type": "bearing_type",
        "subject_to_shear": True,
        "head_side": side(True, {"type": "hardened", "product_verified": True}),
        "nut_side": side(True, plate(clearance=14)),
    }
    assert run_fabrication(d)["checked_conditions_satisfied"]
    d["nut_side"]["washer"]["minimum_edge_clearance_mm"] = 13.99
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["nut_side"]["washer"]["minimum_edge_clearance_mm"] = 14
    d["hole_diameter_mm"] = 28.001
    assert not run_fabrication(d)["checked_conditions_satisfied"]

    d.update(
        bolt_diameter_mm=40,
        hole_diameter_mm=50,
        head_side=side(False),
        nut_side=side(False),
    )
    result = run_fabrication(d)
    assert result["checked_conditions_satisfied"]
    assert result["values"]["maximum_hole_diameter_mm"] == 50


def test_oversize_hole_requires_non_base_plate_applicability():
    d = {
        "check_type": "bolt_hole",
        "hole_type": "oversize",
        "bolt_diameter_mm": 20,
        "hole_diameter_mm": 28,
        "not_base_plate_anchor_hole_verified": False,
        "connection_type": "friction_type",
        "subject_to_shear": False,
        "head_side": side(False),
        "nut_side": side(False),
    }
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_short_slot_size_and_friction_shear_has_no_direction_restriction():
    result = run_fabrication(slot())
    assert result["checked_conditions_satisfied"]
    assert result["values"]["maximum_hole_width_mm"] == 22
    assert result["values"]["maximum_hole_length_mm"] == 30

    too_wide = slot(hole_width_mm=22.001)
    assert not run_fabrication(too_wide)["checked_conditions_satisfied"]
    too_long = slot(hole_length_mm=30.001)
    assert not run_fabrication(too_long)["checked_conditions_satisfied"]

    larger_bolt = slot(
        bolt_diameter_mm=40,
        hole_width_mm=43,
        hole_length_mm=53.2,
    )
    result = run_fabrication(larger_bolt)
    assert result["checked_conditions_satisfied"]
    assert result["values"]["maximum_hole_length_mm"] == pytest.approx(53.2)


def test_short_slot_bearing_shear_conditions_are_required_and_checked():
    d = slot(
        connection_type="bearing_type",
        eccentricity_absent_verified=True,
        uniform_bolt_bearing_verified=True,
        slot_normal_to_action_verified=True,
    )
    assert run_fabrication(d)["checked_conditions_satisfied"]
    d["slot_normal_to_action_verified"] = False
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    del d["slot_normal_to_action_verified"]
    with pytest.raises(ValueError):
        run_fabrication(d)


def test_long_slot_limits_alternate_plies_and_eight_mm_plate_washer():
    d = slot(
        "long_slot",
        head_side=side(True, plate(thickness=8, clearance=11)),
    )
    result = run_fabrication(d)
    assert result["checked_conditions_satisfied"]
    assert result["values"]["maximum_hole_length_mm"] == 50

    d["alternate_plies_verified"] = False
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["alternate_plies_verified"] = True
    d["head_side"]["washer"]["thickness_mm"] = 7.999
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["head_side"]["washer"]["thickness_mm"] = 8
    d["hole_length_mm"] = 50.001
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_long_slot_bearing_shear_requires_unbiased_uniform_normal_loading():
    d = slot(
        "long_slot",
        connection_type="bearing_type",
        head_side=side(True, plate(thickness=8, clearance=11)),
        eccentricity_absent_verified=True,
        uniform_bolt_bearing_verified=True,
        slot_normal_to_action_verified=True,
    )
    assert run_fabrication(d)["checked_conditions_satisfied"]
    d["uniform_bolt_bearing_verified"] = False
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_plate_washer_requires_coverage_and_as_nzs_3678_evidence():
    d = slot(head_side=side(True, plate(clearance=11, coverage=False)))
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["head_side"]["washer"]["coverage_geometry_verified"] = True
    d["head_side"]["washer"]["material_as_nzs_3678_verified"] = False
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_standard_hole_rejects_unexpected_fields():
    with pytest.raises(ValueError):
        run_fabrication(
            {
                "check_type": "bolt_hole",
                "hole_type": "standard",
                "bolt_diameter_mm": 20,
                "hole_diameter_mm": 22,
                "unexpected": True,
            }
        )


def test_bolt_assembly_thread_washer_and_material_conditions():
    result = run_fabrication(bolt_assembly())
    assert result["checked_conditions_satisfied"]
    assert result["values"]["tapered_washer_required"] is False
    assert "14.3.3.3" in result["clauses"]

    d = bolt_assembly(clear_threads_above_nut_count=0)
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d = bolt_assembly(all_material_within_bolt_grip_is_steel_verified=False)
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d = bolt_assembly(washer_under_rotated_part_verified=False)
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_material_identification_and_fabrication_procedure_checks():
    result = run_fabrication(fabrication_basis())
    assert result["checked_conditions_satisfied"]
    assert result["clauses"] == ["14.2.1", "14.2.2", "14.3.1"]

    unknown = fabrication_basis(
        steel_grade_identifiable_at_all_fabrication_stages_verified=False,
        steel_classified_as_unidentified=True,
        clause_2_2_3_unidentified_steel_inputs={
            "operation": "unidentified_steel",
            "design_yield_strength_mpa": 170,
            "design_tensile_strength_mpa": 300,
            "surface_imperfections_verified": True,
            "properties_and_weldability_verified": True,
            "full_test_to_as1391_verified": False,
        },
    )
    result = run_fabrication(unknown)
    assert result["checked_conditions_satisfied"]
    assert result["clauses"] == ["2.2.3", "14.2.1", "14.2.2", "14.3.1"]

    unknown["clause_2_2_3_unidentified_steel_inputs"]["design_yield_strength_mpa"] = 170.001
    assert not run_fabrication(unknown)["checked_conditions_satisfied"]

    unclassified = fabrication_basis(
        steel_grade_identifiable_at_all_fabrication_stages_verified=False
    )
    assert not run_fabrication(unclassified)["checked_conditions_satisfied"]
    assert not run_fabrication(
        fabrication_basis(fabrication_methods_preserve_design_properties_verified=False)
    )["checked_conditions_satisfied"]
    assert not run_fabrication(fabrication_basis(marking_does_not_damage_material_verified=False))[
        "checked_conditions_satisfied"
    ]
    assert not run_fabrication(fabrication_basis(fabrication_per_as_nzs_5131_verified=False))[
        "checked_conditions_satisfied"
    ]
    assert not run_fabrication(
        fabrication_basis(materials_conform_referenced_standards_verified=False)
    )["checked_conditions_satisfied"]


def test_bolt_assembly_tapered_washer_uses_strict_one_in_twenty_threshold():
    at_limit = run_fabrication(bolt_assembly(maximum_contact_surface_slope_ratio=0.05))
    assert at_limit["checked_conditions_satisfied"]
    assert not at_limit["values"]["tapered_washer_required"]

    over_limit = bolt_assembly(maximum_contact_surface_slope_ratio=0.050001)
    assert not run_fabrication(over_limit)["checked_conditions_satisfied"]
    over_limit.update(
        tapered_washer_provided=True,
        tapered_washer_against_sloped_surface_verified=True,
        nonrotating_part_against_tapered_washer_verified=True,
    )
    assert run_fabrication(over_limit)["checked_conditions_satisfied"]


def test_bolt_assembly_vibration_and_fully_tensioned_fabrication_requirements():
    d = bolt_assembly(subject_to_vibration=True)
    with pytest.raises(ValueError):
        run_fabrication(d)
    d["nut_secured_to_prevent_loosening_verified"] = False
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["nut_secured_to_prevent_loosening_verified"] = True
    d["fully_tensioned_high_strength_bolt_installed_during_fabrication"] = True
    with pytest.raises(ValueError):
        run_fabrication(d)
    d["installed_in_accordance_with_clause_15_2_verified"] = True
    result = run_fabrication(d)
    assert result["checked_conditions_satisfied"]
    assert "14.3.3.4" in result["clauses"]


def test_friction_bolt_assembly_surface_preparation_and_alternative_route():
    d = bolt_assembly(
        connection_type="friction_type",
        friction_surfaces_prepared_per_as_nzs_5131_verified=True,
        friction_surfaces_clean_as_rolled_or_equivalent_verified=False,
        clause_9_2_3_2_alternative_route_verified=True,
    )
    result = run_fabrication(d)
    assert result["checked_conditions_satisfied"]
    assert "14.3.3.2" in result["clauses"]
    assert result["values"]["clause_9_2_3_2_route_required"]
    d["clause_9_2_3_2_alternative_route_verified"] = False
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_geometric_tolerance_class_default_and_limit_comparison():
    result = run_fabrication(tolerance())
    assert result["checked_conditions_satisfied"]
    assert result["values"]["functional_tolerance_class_applied"] == 1

    class_two = run_fabrication(tolerance(functional_tolerance_class=2))
    assert class_two["checked_conditions_satisfied"]
    assert class_two["values"]["functional_tolerance_class_applied"] == 2
    assert not run_fabrication(tolerance(measured_deviation_mm=-2.001))[
        "checked_conditions_satisfied"
    ]


def test_essential_tolerance_exceedance_requires_revised_capacity_route():
    d = tolerance(
        tolerance_type="essential",
        measured_deviation_mm=-3,
        permissible_deviation_mm=2,
    )
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["excess_deviation_in_revised_design_capacity_verified"] = True
    assert run_fabrication(d)["checked_conditions_satisfied"]


def test_tolerance_measurement_stage_and_coating_exclusion_are_required():
    d = tolerance(measurement_after_fabrication_and_corrosion_protection_verified=False)
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d = tolerance(coating_thickness_excluded_from_measurement_verified=False)
    assert not run_fabrication(d)["checked_conditions_satisfied"]


@pytest.mark.parametrize(
    ("material_ok", "fabrication_ok", "tolerance_ok", "adequacy", "testing", "accepted"),
    [
        (True, True, True, False, False, True),
        (False, True, True, True, False, True),
        (True, False, False, False, True, True),
        (False, True, True, False, False, False),
    ],
)
def test_clause_14_1_fabricated_item_acceptance_routes(
    material_ok, fabrication_ok, tolerance_ok, adequacy, testing, accepted
):
    output = run_fabrication(
        {
            "check_type": "fabricated_item_acceptance",
            "clause_14_2_material_requirements_satisfied": material_ok,
            "clause_14_3_fabrication_requirements_satisfied": fabrication_ok,
            "clause_14_4_tolerances_satisfied": tolerance_ok,
            "structural_adequacy_and_intended_use_unimpaired_demonstrated": adequacy,
            "section_17_testing_passed": testing,
        }
    )
    assert output["clauses"] == ["14.1", "14.2", "14.3", "14.4"]
    assert output["values"]["fabricated_item_may_be_accepted"] is accepted
    assert output["values"]["rejection_required"] is (not accepted)
    assert output["checked_conditions_satisfied"] is accepted
