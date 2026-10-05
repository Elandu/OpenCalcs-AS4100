# SPDX-License-Identifier: AGPL-3.0-only
"""Selected AS 4100:2020 erection, bolt-tension and tolerance checks."""

from .validation import POSITIVE, SIGNED, object_schema, result, validate

_BOOL = {"type": "boolean"}
_TEXT = {"type": "string", "minLength": 1, "maxLength": 100}
_REFERENCE = {"type": "string", "minLength": 1, "maxLength": 200}
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

_EQUIVALENT_FASTENER = object_schema(
    {
        "operation": {"const": "equivalent_high_strength_fastener"},
        "fastener_reference": _TEXT,
        "reference_nominal_bolt_diameter_mm": {"enum": [16, 20, 24, 30, 36]},
        "equivalent_fastener_nominal_diameter_mm": POSITIVE,
        "bolt_grade": {"enum": ["8.8", "10.9"]},
        "reference_bolt_dimensions_match_nominal_size_verified": _BOOL,
        "reference_bolt_body_diameter_mm": POSITIVE,
        "equivalent_fastener_body_diameter_mm": POSITIVE,
        "reference_head_bearing_area_mm2": POSITIVE,
        "equivalent_fastener_head_bearing_area_mm2": POSITIVE,
        "reference_nut_bearing_area_mm2": POSITIVE,
        "equivalent_fastener_nut_bearing_area_mm2": POSITIVE,
        "equivalent_fastener_minimum_tension_kn": _TENSION,
        "chemical_composition_and_mechanical_properties_equivalent_verified": _BOOL,
        "tensioning_and_inspection_procedure_checkable_verified": _BOOL,
        "test_certificate_reference": _REFERENCE,
        "installation_procedure_reference": _REFERENCE,
    }
)

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
    "oneOf": [
        _BOLTED_ASSEMBLY,
        _EQUIVALENT_FASTENER,
        _ERECTION_PROCESS,
        _TOLERANCE,
        _ITEM_ACCEPTANCE,
    ],
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


def _equivalent_high_strength_fastener(d):
    reference_tension = MINIMUM_BOLT_TENSION_KN[
        (d["reference_nominal_bolt_diameter_mm"], d["bolt_grade"])
    ]
    checks = [
        {
            "clause": "2.3.2(a)",
            "check": "chemical_composition_and_mechanical_properties_equivalent",
            "satisfied": d["chemical_composition_and_mechanical_properties_equivalent_verified"],
        },
        {
            "clause": "2.3.2(b)",
            "check": "reference_bolt_dimensions_match_nominal_size",
            "satisfied": d["reference_bolt_dimensions_match_nominal_size_verified"],
        },
        {
            "clause": "2.3.2(b)",
            "check": "equivalent_fastener_has_same_nominal_diameter",
            "reference_mm": d["reference_nominal_bolt_diameter_mm"],
            "equivalent_mm": d["equivalent_fastener_nominal_diameter_mm"],
            "satisfied": (
                d["equivalent_fastener_nominal_diameter_mm"]
                == d["reference_nominal_bolt_diameter_mm"]
            ),
        },
        {
            "clause": "2.3.2(b)",
            "check": "body_diameter_not_less_than_reference_bolt",
            "reference_mm": d["reference_bolt_body_diameter_mm"],
            "equivalent_mm": d["equivalent_fastener_body_diameter_mm"],
            "satisfied": (
                d["equivalent_fastener_body_diameter_mm"] >= d["reference_bolt_body_diameter_mm"]
            ),
        },
        {
            "clause": "2.3.2(b)",
            "check": "head_bearing_area_not_less_than_reference_bolt",
            "reference_mm2": d["reference_head_bearing_area_mm2"],
            "equivalent_mm2": d["equivalent_fastener_head_bearing_area_mm2"],
            "satisfied": (
                d["equivalent_fastener_head_bearing_area_mm2"]
                >= d["reference_head_bearing_area_mm2"]
            ),
        },
        {
            "clause": "2.3.2(b)",
            "check": "nut_bearing_area_not_less_than_reference_bolt",
            "reference_mm2": d["reference_nut_bearing_area_mm2"],
            "equivalent_mm2": d["equivalent_fastener_nut_bearing_area_mm2"],
            "satisfied": (
                d["equivalent_fastener_nut_bearing_area_mm2"] >= d["reference_nut_bearing_area_mm2"]
            ),
        },
        {
            "clause": "2.3.2(c)",
            "check": "minimum_tension_not_less_than_table_15_2_2_2",
            "required_kn": reference_tension,
            "provided_kn": d["equivalent_fastener_minimum_tension_kn"],
            "satisfied": d["equivalent_fastener_minimum_tension_kn"] >= reference_tension,
        },
        {
            "clause": "2.3.2(c)",
            "check": "tensioning_and_inspection_procedure_can_be_checked",
            "satisfied": d["tensioning_and_inspection_procedure_checkable_verified"],
        },
    ]
    return result(
        "equivalent_high_strength_fastener",
        ["2.3.2", "15.2.2.2"],
        {
            "fastener_reference": d["fastener_reference"],
            "reference_nominal_bolt_diameter_mm": d["reference_nominal_bolt_diameter_mm"],
            "equivalent_fastener_nominal_diameter_mm": d["equivalent_fastener_nominal_diameter_mm"],
            "bolt_grade": d["bolt_grade"],
            "table_15_2_2_2_reference_minimum_tension_kn": reference_tension,
            "equivalent_fastener_minimum_tension_kn": d["equivalent_fastener_minimum_tension_kn"],
            "test_certificate_reference": d["test_certificate_reference"],
            "installation_procedure_reference": d["installation_procedure_reference"],
        },
        checks,
        limitations=[
            "Product identity, certificates, dimensional measurements and tensioning records "
            "must be independently verified.",
            "Chemical composition and mechanical properties are represented by an evidence "
            "declaration; this operation does not test or authenticate the fastener.",
            "This comparison does not calculate fastener or connection design capacity.",
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
    """Check selected AS 4100 fastener, erection, bolt-tension and tolerance provisions."""
    d = validate(inputs, INPUT_SCHEMA)
    operation = d["operation"]
    if operation == "equivalent_high_strength_fastener":
        return _equivalent_high_strength_fastener(d)
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
