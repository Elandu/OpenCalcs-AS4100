# SPDX-License-Identifier: AGPL-3.0-only
"""Selected AS 4100:2020 erection, bolt-tension and tolerance checks."""

from .validation import POSITIVE, SIGNED, object_schema, result, validate

_BOOL = {"type": "boolean"}
_TEXT = {"type": "string", "minLength": 1, "maxLength": 100}
_TENSION = {"type": "number", "minimum": 0, "maximum": 1e12}

# AS 4100:2020 Table 15.2.2.2, minimum bolt tension in kN.
MINIMUM_BOLT_TENSION_KN = {
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

_BOLT_MEASUREMENTS = {
    "type": "array",
    "minItems": 1,
    "maxItems": 1000,
    "items": object_schema({"bolt_id": _TEXT, "measured_tension_kn": _TENSION}),
}
_BOLTED_ASSEMBLY = object_schema(
    {
        "operation": {"const": "bolted_connection_assembly"},
        "connection_type": {"enum": ["snug_tight", "fully_tensioned"]},
        "assembly_per_as_nzs_5131_verified": _BOOL,
        "bolt_group_reference": _TEXT,
        "nominal_bolt_diameter_mm": {"enum": [16, 20, 24, 30, 36]},
        "bolt_grade": {"enum": ["8.8", "10.9"]},
        "bolt_tension_measurements": _BOLT_MEASUREMENTS,
        "homogeneous_bolt_group_verified": _BOOL,
        "all_bolts_in_group_listed_verified": _BOOL,
        "all_bolts_in_group_tightened_verified": _BOOL,
        "tensioning_method": {"enum": ["part_turn", "direct_tension_indicator"]},
        "tensioning_method_per_as_nzs_5131_verified": _BOOL,
    },
    required=[
        "operation",
        "connection_type",
        "assembly_per_as_nzs_5131_verified",
        "bolt_group_reference",
    ],
)
_BOLTED_ASSEMBLY["allOf"] = [
    {
        "if": {
            "properties": {"connection_type": {"const": "fully_tensioned"}},
            "required": ["connection_type"],
        },
        "then": {
            "required": [
                "nominal_bolt_diameter_mm",
                "bolt_grade",
                "bolt_tension_measurements",
                "homogeneous_bolt_group_verified",
                "all_bolts_in_group_listed_verified",
                "all_bolts_in_group_tightened_verified",
                "tensioning_method",
                "tensioning_method_per_as_nzs_5131_verified",
            ]
        },
    }
]

_ERECTION_PROCESS = object_schema(
    {
        "operation": {"const": "erection_safety_and_procedure"},
        "safe_against_erection_loads_including_equipment_and_wind_verified": _BOOL,
        "erection_procedure_per_as_nzs_5131_verified": _BOOL,
        "site_modifications_during_erection_per_as_nzs_5131_verified": _BOOL,
    }
)

_TOLERANCE = object_schema(
    {
        "operation": {"const": "geometric_tolerance"},
        "tolerance_type": {"enum": ["essential", "functional"]},
        "measured_deviation_mm": SIGNED,
        "permissible_deviation_mm": POSITIVE,
        "as_nzs_5131_tolerance_limit_verified": _BOOL,
        "measurement_after_erection_completed_verified": _BOOL,
        "functional_tolerance_class": {"enum": [1, 2]},
        "excess_deviation_in_revised_design_capacity_verified": _BOOL,
    },
    required=[
        "operation",
        "tolerance_type",
        "measured_deviation_mm",
        "permissible_deviation_mm",
        "as_nzs_5131_tolerance_limit_verified",
        "measurement_after_erection_completed_verified",
    ],
)
_TOLERANCE["allOf"] = [
    {
        "if": {
            "properties": {"tolerance_type": {"const": "essential"}},
            "required": ["tolerance_type"],
        },
        "then": {"not": {"required": ["functional_tolerance_class"]}},
    },
    {
        "if": {
            "properties": {"tolerance_type": {"const": "functional"}},
            "required": ["tolerance_type"],
        },
        "then": {"not": {"required": ["excess_deviation_in_revised_design_capacity_verified"]}},
    },
]

_ITEM_ACCEPTANCE = object_schema(
    {
        "operation": {"const": "erected_item_acceptance"},
        "clause_15_2_erection_requirements_satisfied": _BOOL,
        "clause_15_3_tolerances_satisfied": _BOOL,
        "bolt_hardware_conforms_clauses_14_3_3_and_15_2": _BOOL,
        "structural_adequacy_and_intended_use_unimpaired_demonstrated": _BOOL,
        "section_17_testing_passed": _BOOL,
    }
)

INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "oneOf": [_BOLTED_ASSEMBLY, _ERECTION_PROCESS, _TOLERANCE, _ITEM_ACCEPTANCE],
}
OUTPUT_SCHEMA = {"type": "object"}


def _minimum_bolt_tension(d):
    required = MINIMUM_BOLT_TENSION_KN[(d["nominal_bolt_diameter_mm"], d["bolt_grade"])]
    measurements = d["bolt_tension_measurements"]
    if len({bolt["bolt_id"] for bolt in measurements}) != len(measurements):
        raise ValueError("Bolt IDs in a measured group must be unique.")
    method_clause = "15.2.2.3" if d["tensioning_method"] == "part_turn" else "15.2.2.4"
    bolt_checks = [
        {
            "clause": "15.2.2.2",
            "bolt_id": bolt["bolt_id"],
            "required_tension_kn": required,
            "measured_tension_kn": bolt["measured_tension_kn"],
            "satisfied": bolt["measured_tension_kn"] >= required,
        }
        for bolt in measurements
    ]
    checks = [
        {
            "clause": "15.2.2.1",
            "check": "assembly_per_as_nzs_5131",
            "satisfied": d["assembly_per_as_nzs_5131_verified"],
        },
        {
            "clause": "15.2.2.2",
            "check": "homogeneous_bolt_group",
            "satisfied": d["homogeneous_bolt_group_verified"],
        },
        {
            "clause": "15.2.2.2",
            "check": "all_group_bolts_listed",
            "satisfied": d["all_bolts_in_group_listed_verified"],
        },
        {
            "clause": "15.2.2.2",
            "check": "all_group_bolts_tightened",
            "satisfied": d["all_bolts_in_group_tightened_verified"],
        },
        {
            "clause": method_clause,
            "check": "tensioning_method_per_as_nzs_5131",
            "satisfied": d["tensioning_method_per_as_nzs_5131_verified"],
        },
        *bolt_checks,
    ]
    return result(
        "bolted_connection_assembly",
        ["15.2.2.1", "15.2.2.2", method_clause],
        {
            "connection_type": d["connection_type"],
            "bolt_group_reference": d["bolt_group_reference"],
            "nominal_bolt_diameter_mm": d["nominal_bolt_diameter_mm"],
            "bolt_grade": d["bolt_grade"],
            "required_minimum_bolt_tension_kn": required,
            "tensioning_method": d["tensioning_method"],
            "measured_bolt_count": len(measurements),
        },
        checks,
        limitations=[
            "Tension readings, group completeness, homogeneity and installation records "
            "require independent verification.",
            "The table lookup supports M16, M20, M24, M30 and M36 bolts of grades "
            "8.8 and 10.9 only.",
            "AS/NZS 5131 installation requirements are represented by an evidence "
            "declaration; they are not reproduced here.",
        ],
    )


def _run_tolerance(d):
    deviation = abs(d["measured_deviation_mm"])
    limit = d["permissible_deviation_mm"]
    within_limit = deviation <= limit + 1e-9 * max(1.0, abs(limit))
    essential = d["tolerance_type"] == "essential"
    revised_route = d.get("excess_deviation_in_revised_design_capacity_verified", False)
    accepted_route = within_limit or (essential and revised_route)
    checks = [
        {
            "clause": "15.3.1",
            "check": "as_nzs_5131_erection_tolerance_limit_source",
            "satisfied": d["as_nzs_5131_tolerance_limit_verified"],
        },
        {
            "clause": "15.3.1",
            "check": "measured_after_erection_completed",
            "satisfied": d["measurement_after_erection_completed_verified"],
        },
        {
            "clause": "15.3.2",
            "check": "within_tolerance_or_essential_revised_design_route",
            "satisfied": accepted_route,
            "measured_absolute_deviation_mm": deviation,
            "permissible_deviation_mm": limit,
            "revised_design_route_required": essential and not within_limit,
            "revised_design_route_verified": (
                revised_route if essential and not within_limit else None
            ),
        },
    ]
    return result(
        "geometric_tolerance",
        ["15.3.1", "15.3.2"],
        {
            "tolerance_type": d["tolerance_type"],
            "functional_tolerance_class_applied": (
                d.get("functional_tolerance_class", 1) if not essential else None
            ),
            "measured_deviation_mm": d["measured_deviation_mm"],
            "permissible_deviation_mm": limit,
            "within_permissible_value": within_limit,
        },
        checks,
        limitations=[
            "The numerical tolerance limit and functional class applicability must be verified "
            "against AS/NZS 5131 and project specifications.",
            "Measurements, structural adequacy and any revised design-capacity calculation "
            "require independent engineering review.",
        ],
    )


def _run_item_acceptance(d):
    procedure_ok = d["clause_15_2_erection_requirements_satisfied"]
    tolerance_ok = d["clause_15_3_tolerances_satisfied"]
    hardware_ok = d["bolt_hardware_conforms_clauses_14_3_3_and_15_2"]
    adequacy = d["structural_adequacy_and_intended_use_unimpaired_demonstrated"]
    testing = d["section_17_testing_passed"]
    item_route = (procedure_ok and tolerance_ok) or adequacy or testing
    hardware_route = hardware_ok or adequacy
    checks = [
        {
            "clause": "15.1.1",
            "check": "erected_item_conforms_or_has_documented_acceptance_route",
            "satisfied": item_route,
            "clause_15_2_satisfied": procedure_ok,
            "clause_15_3_satisfied": tolerance_ok,
            "structural_adequacy_route_used": not (procedure_ok and tolerance_ok) and adequacy,
            "section_17_test_route_used": not (procedure_ok and tolerance_ok) and testing,
        },
        {
            "clause": "15.1.1",
            "check": "bolt_hardware_conforms_or_structural_adequacy_is_demonstrated",
            "satisfied": hardware_route,
            "clauses_14_3_3_and_15_2_conform": hardware_ok,
            "structural_adequacy_route_used": not hardware_ok and adequacy,
        },
    ]
    return result(
        "erected_item_acceptance",
        ["15.1.1", "14.3.3", "15.2", "15.3"],
        {
            "erected_item_may_be_accepted": item_route,
            "bolt_hardware_may_be_accepted": hardware_route,
            "structural_adequacy_and_intended_use_unimpaired_demonstrated": adequacy,
            "section_17_testing_passed": testing,
        },
        checks,
        limitations=[
            "Acceptance routes depend on project-specific evidence and an engineer's "
            "decision; this calculation does not approve or reject an erected item.",
            "Section 17 testing is represented only by a supplied result declaration.",
        ],
    )


def run_erection(inputs):
    """Check selected AS 4100 erection-safety, procedure and acceptance provisions."""
    d = validate(inputs, INPUT_SCHEMA)
    operation = d["operation"]
    if operation == "bolted_connection_assembly":
        if d["connection_type"] == "fully_tensioned":
            return _minimum_bolt_tension(d)
        return result(
            "bolted_connection_assembly",
            ["15.2.2.1"],
            {
                "connection_type": d["connection_type"],
                "bolt_group_reference": d["bolt_group_reference"],
                "minimum_bolt_tension_table_applies": False,
            },
            [
                {
                    "clause": "15.2.2.1",
                    "check": "assembly_per_as_nzs_5131",
                    "satisfied": d["assembly_per_as_nzs_5131_verified"],
                }
            ],
            limitations=[
                "The snug-tight declaration requires verified assembly records; it does "
                "not assess bolt capacity or connection design.",
            ],
        )
    if operation == "erection_safety_and_procedure":
        return result(
            operation,
            ["15.1.2", "15.2.1"],
            {},
            [
                {
                    "clause": "15.1.2",
                    "check": "safe_against_erection_loads_equipment_and_wind",
                    "satisfied": d[
                        "safe_against_erection_loads_including_equipment_and_wind_verified"
                    ],
                },
                {
                    "clause": "15.2.1",
                    "check": "erection_procedure_per_as_nzs_5131",
                    "satisfied": d["erection_procedure_per_as_nzs_5131_verified"],
                },
                {
                    "clause": "15.2.1",
                    "check": "site_modifications_per_as_nzs_5131",
                    "satisfied": d["site_modifications_during_erection_per_as_nzs_5131_verified"],
                },
            ],
            limitations=[
                "Temporary stability, erection loading, equipment, wind and site procedures "
                "require project-specific engineering records.",
            ],
        )
    if operation == "geometric_tolerance":
        return _run_tolerance(d)
    return _run_item_acceptance(d)
