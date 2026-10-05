# SPDX-License-Identifier: AGPL-3.0-only
import pytest

from opencalcs_as4100.erection import run_erection
from opencalcs_as4100.review import run_review


@pytest.mark.parametrize(
    ("diameter", "grade", "minimum"),
    [
        (16, "8.8", 95),
        (16, "10.9", 130),
        (20, "8.8", 145),
        (20, "10.9", 205),
        (24, "8.8", 210),
        (24, "10.9", 295),
        (30, "8.8", 335),
        (30, "10.9", 465),
        (36, "8.8", 490),
        (36, "10.9", 680),
    ],
)
@pytest.mark.parametrize(
    ("method", "method_clause"),
    [("part_turn", "15.2.2.3"), ("direct_tension_indicator", "15.2.2.4")],
)
def test_table_15_2_2_2_minimum_tension(diameter, grade, minimum, method, method_clause):
    output = run_erection(
        {
            "operation": "bolted_connection_assembly",
            "connection_type": "fully_tensioned",
            "assembly_per_as_nzs_5131_verified": True,
            "bolt_group_reference": "BG-01",
            "nominal_bolt_diameter_mm": diameter,
            "bolt_grade": grade,
            "bolt_tension_measurements": [{"bolt_id": "B1", "measured_tension_kn": minimum}],
            "homogeneous_bolt_group_verified": True,
            "all_bolts_in_group_listed_verified": True,
            "all_bolts_in_group_tightened_verified": True,
            "tensioning_method": method,
            "tensioning_method_per_as_nzs_5131_verified": True,
        }
    )
    assert output["checked_conditions_satisfied"]
    assert output["values"]["required_minimum_bolt_tension_kn"] == minimum
    assert output["clauses"] == ["15.2.2.1", "15.2.2.2", method_clause]


def test_bolt_tension_below_table_value_fails_and_records_bolt():
    inputs = {
        "operation": "bolted_connection_assembly",
        "connection_type": "fully_tensioned",
        "assembly_per_as_nzs_5131_verified": True,
        "bolt_group_reference": "BG-02",
        "nominal_bolt_diameter_mm": 24,
        "bolt_grade": "10.9",
        "bolt_tension_measurements": [
            {"bolt_id": "B1", "measured_tension_kn": 295},
            {"bolt_id": "B2", "measured_tension_kn": 294.9},
        ],
        "homogeneous_bolt_group_verified": True,
        "all_bolts_in_group_listed_verified": True,
        "all_bolts_in_group_tightened_verified": True,
        "tensioning_method": "part_turn",
        "tensioning_method_per_as_nzs_5131_verified": True,
    }
    output = run_erection(inputs)
    assert not output["checked_conditions_satisfied"]
    assert [check["satisfied"] for check in output["checks"][-2:]] == [True, False]
    assert [check["bolt_id"] for check in output["checks"][-2:]] == ["B1", "B2"]


def equivalent_high_strength_fastener(**changes):
    return {
        "operation": "equivalent_high_strength_fastener",
        "fastener_reference": "FASTENER-EQ-01",
        "reference_nominal_bolt_diameter_mm": 20,
        "equivalent_fastener_nominal_diameter_mm": 20,
        "bolt_grade": "8.8",
        "reference_bolt_dimensions_match_nominal_size_verified": True,
        "reference_bolt_body_diameter_mm": 20,
        "equivalent_fastener_body_diameter_mm": 20,
        "reference_head_bearing_area_mm2": 300,
        "equivalent_fastener_head_bearing_area_mm2": 300,
        "reference_nut_bearing_area_mm2": 200,
        "equivalent_fastener_nut_bearing_area_mm2": 200,
        "equivalent_fastener_minimum_tension_kn": 145,
        "chemical_composition_and_mechanical_properties_equivalent_verified": True,
        "tensioning_and_inspection_procedure_checkable_verified": True,
        "test_certificate_reference": "FASTENER-CERT-01",
        "installation_procedure_reference": "FASTENER-INSTALL-01",
        **changes,
    }


def test_clause_2_3_2_equivalent_fastener_meets_reference_comparisons():
    output = run_erection(equivalent_high_strength_fastener())
    assert output["clauses"] == ["2.3.2", "15.2.2.2"]
    assert output["values"]["table_15_2_2_2_reference_minimum_tension_kn"] == 145
    assert output["checked_conditions_satisfied"]
    assert all(check["satisfied"] for check in output["checks"])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reference_bolt_dimensions_match_nominal_size_verified", False),
        ("equivalent_fastener_nominal_diameter_mm", 19.9),
        ("equivalent_fastener_body_diameter_mm", 19.9),
        ("equivalent_fastener_head_bearing_area_mm2", 299.9),
        ("equivalent_fastener_nut_bearing_area_mm2", 199.9),
        ("equivalent_fastener_minimum_tension_kn", 144.9),
        ("chemical_composition_and_mechanical_properties_equivalent_verified", False),
        ("tensioning_and_inspection_procedure_checkable_verified", False),
    ],
)
def test_clause_2_3_2_rejects_equivalence_when_a_requirement_fails(field, value):
    output = run_erection(equivalent_high_strength_fastener(**{field: value}))
    assert not output["checked_conditions_satisfied"]
    assert any(not check["satisfied"] for check in output["checks"])


def test_clause_2_3_2_uses_reference_grade_and_diameter_minimum_tension():
    output = run_erection(
        equivalent_high_strength_fastener(
            reference_nominal_bolt_diameter_mm=24,
            equivalent_fastener_nominal_diameter_mm=24,
            bolt_grade="10.9",
            equivalent_fastener_minimum_tension_kn=294.9,
        )
    )
    assert output["values"]["table_15_2_2_2_reference_minimum_tension_kn"] == 295
    assert not output["checked_conditions_satisfied"]


def test_duplicate_bolt_ids_are_rejected():
    inputs = {
        "operation": "bolted_connection_assembly",
        "connection_type": "fully_tensioned",
        "assembly_per_as_nzs_5131_verified": True,
        "bolt_group_reference": "BG-03",
        "nominal_bolt_diameter_mm": 20,
        "bolt_grade": "8.8",
        "bolt_tension_measurements": [
            {"bolt_id": "B1", "measured_tension_kn": 145},
            {"bolt_id": "B1", "measured_tension_kn": 150},
        ],
        "homogeneous_bolt_group_verified": True,
        "all_bolts_in_group_listed_verified": True,
        "all_bolts_in_group_tightened_verified": True,
        "tensioning_method": "part_turn",
        "tensioning_method_per_as_nzs_5131_verified": True,
    }
    with pytest.raises(ValueError, match="unique"):
        run_erection(inputs)


def test_snug_tight_connection_does_not_use_minimum_tension_table():
    output = run_erection(
        {
            "operation": "bolted_connection_assembly",
            "connection_type": "snug_tight",
            "assembly_per_as_nzs_5131_verified": True,
            "bolt_group_reference": "BG-04",
        }
    )
    assert output["clauses"] == ["15.2.2.1"]
    assert output["values"]["minimum_bolt_tension_table_applies"] is False


def test_erection_process_checks_temporary_safety_procedure_and_modifications():
    output = run_erection(
        {
            "operation": "erection_safety_and_procedure",
            "safe_against_erection_loads_including_equipment_and_wind_verified": True,
            "erection_procedure_per_as_nzs_5131_verified": True,
            "site_modifications_during_erection_per_as_nzs_5131_verified": False,
        }
    )
    assert output["clauses"] == ["15.1.2", "15.2.1"]
    assert not output["checked_conditions_satisfied"]
    assert output["checks"][-1]["clause"] == "15.2.1"


def test_erection_tolerance_defaults_functional_class_and_requires_completed_erection():
    output = run_erection(
        {
            "operation": "geometric_tolerance",
            "tolerance_type": "functional",
            "measured_deviation_mm": -1.5,
            "permissible_deviation_mm": 2,
            "as_nzs_5131_tolerance_limit_verified": True,
            "measurement_after_erection_completed_verified": True,
        }
    )
    assert output["clauses"] == ["15.3.1", "15.3.2"]
    assert output["values"]["functional_tolerance_class_applied"] == 1
    assert output["checked_conditions_satisfied"]


def test_essential_erection_tolerance_requires_revised_design_above_limit():
    base = {
        "operation": "geometric_tolerance",
        "tolerance_type": "essential",
        "measured_deviation_mm": 2.1,
        "permissible_deviation_mm": 2,
        "as_nzs_5131_tolerance_limit_verified": True,
        "measurement_after_erection_completed_verified": True,
    }
    failed = run_erection(base)
    assert not failed["checked_conditions_satisfied"]
    base["excess_deviation_in_revised_design_capacity_verified"] = True
    accepted_route = run_erection(base)
    assert accepted_route["checked_conditions_satisfied"]


def test_functional_erection_tolerance_outside_limit_cannot_use_essential_route():
    with pytest.raises(ValueError):
        run_erection(
            {
                "operation": "geometric_tolerance",
                "tolerance_type": "functional",
                "measured_deviation_mm": 3,
                "permissible_deviation_mm": 2,
                "as_nzs_5131_tolerance_limit_verified": True,
                "measurement_after_erection_completed_verified": True,
                "excess_deviation_in_revised_design_capacity_verified": True,
            }
        )


def test_nonconforming_erected_item_can_use_section_17_acceptance_route():
    output = run_erection(
        {
            "operation": "erected_item_acceptance",
            "clause_15_2_erection_requirements_satisfied": False,
            "clause_15_3_tolerances_satisfied": True,
            "bolt_hardware_conforms_clauses_14_3_3_and_15_2": True,
            "structural_adequacy_and_intended_use_unimpaired_demonstrated": False,
            "section_17_testing_passed": True,
        }
    )
    assert output["values"]["erected_item_may_be_accepted"]
    assert output["values"]["bolt_hardware_may_be_accepted"]
    assert output["checked_conditions_satisfied"]


def test_nonconforming_bolt_hardware_still_needs_adequacy_route():
    output = run_erection(
        {
            "operation": "erected_item_acceptance",
            "clause_15_2_erection_requirements_satisfied": False,
            "clause_15_3_tolerances_satisfied": True,
            "bolt_hardware_conforms_clauses_14_3_3_and_15_2": False,
            "structural_adequacy_and_intended_use_unimpaired_demonstrated": False,
            "section_17_testing_passed": True,
        }
    )
    assert output["values"]["erected_item_may_be_accepted"]
    assert not output["values"]["bolt_hardware_may_be_accepted"]
    assert not output["checked_conditions_satisfied"]


def test_review_schedule_runs_erection_family():
    output = run_review(
        {
            "project_reference": "ERECTION-01",
            "engineering_evidence": [],
            "tasks": [
                {
                    "id": "ERECT-1",
                    "family": "erection",
                    "entity_reference": "frame-1",
                    "combination_reference": "erection-stage-1",
                    "inputs": {
                        "operation": "erection_safety_and_procedure",
                        "safe_against_erection_loads_including_equipment_and_wind_verified": True,
                        "erection_procedure_per_as_nzs_5131_verified": True,
                        "site_modifications_during_erection_per_as_nzs_5131_verified": True,
                    },
                }
            ],
        }
    )
    assert output["calculation_results"][0]["family"] == "erection"
    assert output["calculation_results"][0]["result"]["checked_conditions_satisfied"]
