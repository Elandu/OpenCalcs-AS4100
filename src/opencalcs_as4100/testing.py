"""AS 4100:2020 structural proof/prototype testing and informative deflection limits."""

from collections.abc import Mapping
from math import isclose, isfinite

from jsonschema import Draft202012Validator, ValidationError


def _number(positive=False):
    return {"type": "number", "exclusiveMinimum" if positive else "minimum": 0, "maximum": 1e12}


_BOOL = {"type": "boolean"}
_NUM = _number()
_POS = _number(True)
_COUNT = {"enum": [1, 2, 3, 4, 5, 10]}


def _operation(name, props):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"check_type": {"const": name}, **props},
        "required": ["check_type", *props],
    }


_REPORT = {
    "calibrated_loading_without_artificial_restraints": _BOOL,
    "representative_force_distribution_and_duration": _BOOL,
    "loading_rate_as_uniform_as_practicable_verified": _BOOL,
    "deformations_recorded_before_during_after": _BOOL,
    "loading_method_recorded": _BOOL,
    "deflection_measurement_method_recorded": _BOOL,
    "other_relevant_test_data_recorded": _BOOL,
    "acceptance_statement_recorded": _BOOL,
    "test_report_complete": _BOOL,
}
_PROTOTYPE = {
    "number_similar_units": _COUNT,
    "materials_conform_section_2_verified": _BOOL,
    "fabrication_conforms_section_14_verified": _BOOL,
    "manufacturing_specification_requirements_met_verified": _BOOL,
    "erection_method_represents_production_verified": _BOOL,
    "production_units_similar": _BOOL,
}
INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "oneOf": [
        _operation(
            "test_scope_applicability",
            {
                "test_article": {
                    "enum": [
                        "complete_structure",
                        "substructure",
                        "individual_member",
                        "connection",
                        "structural_model",
                    ]
                },
                "test_type": {"enum": ["proof", "prototype"]},
                "test_purpose": {
                    "enum": [
                        "specific_unit_characteristics",
                        "nominally_identical_class_characteristics",
                        "general_design_criteria_or_data",
                    ]
                },
                "design_complies_with_as_4100_verified": _BOOL,
                "special_circumstances_require_test_verified": _BOOL,
                "test_used_as_alternative_to_calculation_verified": _BOOL,
            },
        ),
        _operation(
            "proof_strength",
            {
                **_REPORT,
                "design_load_kn": _POS,
                "sustained_load_kn": _NUM,
                "sustained_duration_min": _NUM,
                "post_test_damage_inspected": _BOOL,
                "damage_review_and_repairs_complete": _BOOL,
            },
        ),
        _operation(
            "prototype_strength",
            {
                **_REPORT,
                **_PROTOTYPE,
                "design_load_kn": _POS,
                "sustained_load_kn": _NUM,
                "sustained_duration_min": _NUM,
            },
        ),
        _operation(
            "proof_serviceability",
            {
                **_REPORT,
                "design_load_kn": _POS,
                "applied_load_kn": _NUM,
                "maximum_deformation_mm": _NUM,
                "applicable_deformation_limit_mm": _POS,
            },
        ),
        _operation(
            "prototype_serviceability",
            {
                **_REPORT,
                **_PROTOTYPE,
                "design_load_kn": _POS,
                "applied_load_kn": _NUM,
                "maximum_deformation_mm": _NUM,
                "applicable_deformation_limit_mm": _POS,
            },
        ),
        _operation(
            "existing_material_audit",
            {
                "base_metal_identified": _BOOL,
                "material_test_evidence_available": _BOOL,
                "modification_repair_procedures_reviewed": _BOOL,
                "as_nzs_5131_requirements_satisfied": _BOOL,
            },
        ),
        _operation(
            "existing_structure_modification_review",
            {
                "other_as4100_provisions_applied_unless_modified_verified": _BOOL,
                "site_modifications_during_erection_applicable": _BOOL,
                "site_modifications_conform_as_nzs_5131_verified": _BOOL,
                "existing_modification_or_repair_applicable": _BOOL,
                "existing_modification_or_repair_conforms_as_nzs_5131_verified": _BOOL,
                "strengthening_repair_or_welding_documents_prepared": _BOOL,
                "base_metal_types_determined_before_documents_verified": _BOOL,
            },
        ),
        _operation(
            "suggested_vertical_limit",
            {
                "span_or_cantilever_length_mm": _POS,
                "cantilever": _BOOL,
                "application": {"enum": ["all_beams", "masonry_partitions"]},
                "provision_minimises_partition_movement": _BOOL,
                "deflection_scope": {"enum": ["total", "after_partition_attachment"]},
                "support_rotation_included": _BOOL,
                "calculated_deflection_mm": _NUM,
            },
        ),
        _operation(
            "suggested_portal_horizontal_limit",
            {
                "deflection_type": {"enum": ["relative_adjacent_frames", "absolute_frame"]},
                "cladding": {"enum": ["steel_or_aluminium_sheet", "external_masonry"]},
                "gantry_cranes": _BOOL,
                "no_ceilings_or_internal_partitions_at_external_walls": _BOOL,
                "frame_spacing_mm": _POS,
                "eaves_height_mm": _POS,
                "crane_rail_height_mm": _POS,
                "calculated_deflection_mm": _NUM,
                "serviceability_wind_loading_confirmed": _BOOL,
                "masonry_supported_by_steelwork": _BOOL,
            },
        ),
    ],
}
_TEST_RESULT = {
    "test_load_factor": _NUM,
    "required_test_load_kn": _NUM,
    "load_satisfied": _BOOL,
    "conditions_and_report_satisfied": _BOOL,
    "check_satisfied": _BOOL,
}


def _result(properties):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }


_RESULTS = {
    "test_scope_applicability": _result(
        {
            "article_within_section_17_scope": _BOOL,
            "purpose_matches_proof_or_prototype_definition": _BOOL,
            "not_for_general_design_criteria_or_data": _BOOL,
            (
                "testing_not_required_for_standard_compliant_design_without_special_circumstances"
            ): _BOOL,
            "test_basis_documented": _BOOL,
            "check_satisfied": _BOOL,
            "manual_review_required": {"const": True},
        }
    ),
    **{
        op: _result({**_TEST_RESULT, "required_duration_min": _NUM, "duration_satisfied": _BOOL})
        for op in ["proof_strength", "prototype_strength"]
    },
    **{
        op: _result({**_TEST_RESULT, "deformation_satisfied": _BOOL})
        for op in ["proof_serviceability", "prototype_serviceability"]
    },
    "existing_material_audit": _result(
        {"prerequisites_satisfied": _BOOL, "manual_review_required": {"const": True}}
    ),
    "existing_structure_modification_review": _result(
        {
            "other_as4100_provisions_applied_unless_modified": _BOOL,
            "site_modification_requirements_satisfied": _BOOL,
            "existing_modification_or_repair_requirements_satisfied": _BOOL,
            "base_metal_determination_timing_satisfied": _BOOL,
            "check_satisfied": _BOOL,
            "manual_review_required": {"const": True},
        }
    ),
    "suggested_vertical_limit": _result(
        {
            "suggested_limit_mm": _NUM,
            "span_divisor": _NUM,
            "suggestion_satisfied": _BOOL,
            "informative_only": {"const": True},
        }
    ),
    "suggested_portal_horizontal_limit": _result(
        {
            "suggested_limit_mm": _NUM,
            "length_divisor": _NUM,
            "suggestion_satisfied": _BOOL,
            "informative_only": {"const": True},
        }
    ),
}
OUTPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["check_type", "standard", "clauses", "results", "warnings"],
    "properties": {
        "check_type": {"enum": list(_RESULTS)},
        "standard": {"const": "AS 4100:2020"},
        "clauses": {"type": "array", "items": {"type": "string"}},
        "results": {"type": "object"},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "allOf": [
        {
            "if": {"properties": {"check_type": {"const": op}}},
            "then": {"properties": {"results": schema}},
        }
        for op, schema in _RESULTS.items()
    ],
}
_FACTORS = {
    1: (1.5, 1.2),
    2: (1.4, 1.2),
    3: (1.3, 1.2),
    4: (1.3, 1.1),
    5: (1.3, 1.1),
    10: (1.2, 1.1),
}


def _finite(value):
    if isinstance(value, Mapping):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return not isinstance(value, float) or isfinite(value)


def run_testing(inputs):
    """Compare prescribed checks with declared test evidence requiring external records."""
    if not isinstance(inputs, Mapping):
        raise ValueError("Inputs must be an object.")  # noqa: TRY004
    d = dict(inputs)
    try:
        Draft202012Validator(INPUT_SCHEMA).validate(d)
    except ValidationError as exc:
        raise ValueError(exc.message) from exc
    if not _finite(d):
        raise ValueError("All numeric inputs must be finite.")
    op = d["check_type"]
    if op == "test_scope_applicability":
        article_in_scope = d["test_article"] != "structural_model"
        expected_purpose = (
            "specific_unit_characteristics"
            if d["test_type"] == "proof"
            else "nominally_identical_class_characteristics"
        )
        purpose_matches = d["test_purpose"] == expected_purpose
        not_general_data = d["test_purpose"] != "general_design_criteria_or_data"
        no_test_required = (
            d["design_complies_with_as_4100_verified"]
            and not d["special_circumstances_require_test_verified"]
        )
        basis_documented = (
            no_test_required
            or d["test_used_as_alternative_to_calculation_verified"]
            or d["special_circumstances_require_test_verified"]
        )
        result = {
            "article_within_section_17_scope": article_in_scope,
            "purpose_matches_proof_or_prototype_definition": purpose_matches,
            "not_for_general_design_criteria_or_data": not_general_data,
            (
                "testing_not_required_for_standard_compliant_design_without_special_circumstances"
            ): no_test_required,
            "test_basis_documented": basis_documented,
            "check_satisfied": (
                article_in_scope and purpose_matches and not_general_data and basis_documented
            ),
            "manual_review_required": True,
        }
        clauses = ["17.1.1", "17.1.2", "17.2"]
        warnings = [
            "Section 17 test methods apply to actual structures, substructures, members or "
            "connections, not structural models or the establishment of general design "
            "criteria or data.",
            "Tests are not required for structures designed to AS 4100 unless special "
            "circumstances apply; a test may be considered as an alternative to calculation.",
            "Applicability and acceptance of an alternative test remain subject to "
            "engineering review.",
        ]
    elif op.startswith(("proof_", "prototype_")):
        strength = op.endswith("strength")
        prototype = op.startswith("prototype_")
        factor = _FACTORS[d["number_similar_units"]][0 if strength else 1] if prototype else 1
        required_load = factor * d["design_load_kn"]
        conditions = all(d[key] for key in _REPORT)
        if prototype:
            conditions = conditions and all(
                d[key]
                for key in [
                    "materials_conform_section_2_verified",
                    "fabrication_conforms_section_14_verified",
                    "manufacturing_specification_requirements_met_verified",
                    "erection_method_represents_production_verified",
                    "production_units_similar",
                ]
            )
        if strength:
            duration = 5 if prototype else 15
            load_ok = isclose(
                d["sustained_load_kn"],
                required_load,
                rel_tol=0,
                abs_tol=1e-9 * max(1.0, required_load),
            )
            duration_ok = d["sustained_duration_min"] >= duration
            if not prototype:
                conditions = (
                    conditions
                    and d["post_test_damage_inspected"]
                    and (d["damage_review_and_repairs_complete"])
                )
            result = {
                "required_duration_min": duration,
                "duration_satisfied": duration_ok,
                "check_satisfied": load_ok and duration_ok and conditions,
            }
        else:
            load_ok = isclose(
                d["applied_load_kn"],
                required_load,
                rel_tol=0,
                abs_tol=1e-9 * max(1.0, required_load),
            )
            deformation_ok = d["maximum_deformation_mm"] <= d["applicable_deformation_limit_mm"]
            result = {
                "deformation_satisfied": deformation_ok,
                "check_satisfied": load_ok and deformation_ok and conditions,
            }
        result.update(
            test_load_factor=factor,
            required_test_load_kn=required_load,
            load_satisfied=load_ok,
            conditions_and_report_satisfied=conditions,
        )
        clauses = (
            ["17.3", "17.5.1", "17.5.2", "17.5.3", "17.5.4", "17.6"]
            if prototype
            else ["17.3", "17.4.1", "17.4.2", "17.4.3", "17.6"]
        )
        warnings = [
            "Test results apply to the tested unit or the explicitly represented production class.",
            "Load calibration, restraints, measurements and complete test reports need evidence.",
            "Design load must come from the relevant limit-state combination in clause 3.2.3.",
        ]
    elif op == "existing_material_audit":
        result = {
            "prerequisites_satisfied": all(d[key] for key in d if key != "check_type"),
            "manual_review_required": True,
        }
        clauses = ["16.1", "16.2"]
        warnings = [
            "Identify unknown base metal before preparing repair or welding procedures.",
            "No assumed legacy material strength or invented material-test acceptance is supplied.",
        ]
    elif op == "existing_structure_modification_review":
        site_modification_ok = (
            not d["site_modifications_during_erection_applicable"]
            or d["site_modifications_conform_as_nzs_5131_verified"]
        )
        existing_work_ok = (
            not d["existing_modification_or_repair_applicable"]
            or d["existing_modification_or_repair_conforms_as_nzs_5131_verified"]
        )
        base_metal_timing_ok = (
            not d["strengthening_repair_or_welding_documents_prepared"]
            or d["base_metal_types_determined_before_documents_verified"]
        )
        result = {
            "other_as4100_provisions_applied_unless_modified": d[
                "other_as4100_provisions_applied_unless_modified_verified"
            ],
            "site_modification_requirements_satisfied": site_modification_ok,
            "existing_modification_or_repair_requirements_satisfied": existing_work_ok,
            "base_metal_determination_timing_satisfied": base_metal_timing_ok,
            "check_satisfied": (
                d["other_as4100_provisions_applied_unless_modified_verified"]
                and site_modification_ok
                and existing_work_ok
                and base_metal_timing_ok
            ),
            "manual_review_required": True,
        }
        clauses = ["16.1", "16.2"]
        warnings = [
            (
                "All other applicable AS 4100 provisions continue to apply unless modified "
                "by Section 16."
            ),
            (
                "AS/NZS 5131 compliance and base-metal identification timing require "
                "supporting evidence."
            ),
            (
                "This review does not reanalyse the existing structure or provide "
                "material-test acceptance criteria."
            ),
        ]
    elif op == "suggested_vertical_limit":
        masonry = d["application"] == "masonry_partitions"
        if d["deflection_scope"] != ("after_partition_attachment" if masonry else "total"):
            raise ValueError("Deflection scope does not match the selected Appendix B application.")
        if d["cantilever"] and not d["support_rotation_included"]:
            raise ValueError("Cantilever deflection must include support rotation.")
        divisor = (500 if d["provision_minimises_partition_movement"] else 1000) if masonry else 250
        if d["cantilever"]:
            divisor /= 2
        limit = d["span_or_cantilever_length_mm"] / divisor
        result = {
            "suggested_limit_mm": limit,
            "span_divisor": divisor,
            "suggestion_satisfied": d["calculated_deflection_mm"] <= limit,
            "informative_only": True,
        }
        clauses = ["B.1", "Table B.1"]
        warnings = [
            "Informative suggested limit; project serviceability requirements may differ.",
            "Suggested limits do not necessarily prevent ponding.",
        ]
    else:
        if not (
            d["no_ceilings_or_internal_partitions_at_external_walls"]
            and d["serviceability_wind_loading_confirmed"]
        ):
            raise ValueError(
                "Portal suggestion requires the stated building and wind-loading scope."
            )
        masonry = d["cladding"] == "external_masonry"
        if masonry and not d["masonry_supported_by_steelwork"]:
            raise ValueError("Masonry-clad portal scope requires masonry supported by steelwork.")
        if masonry and d["gantry_cranes"]:
            raise ValueError(
                "Combined masonry and gantry-crane scope requires a project-specific limit."
            )
        if d["deflection_type"] == "relative_adjacent_frames":
            length = d["frame_spacing_mm"]
            divisor = 250 if d["gantry_cranes"] else 200
        elif masonry:
            length, divisor = d["eaves_height_mm"], 250
        elif d["gantry_cranes"]:
            length, divisor = d["crane_rail_height_mm"], 250
        else:
            length, divisor = d["eaves_height_mm"], 150
        limit = length / divisor
        result = {
            "suggested_limit_mm": limit,
            "length_divisor": divisor,
            "suggestion_satisfied": d["calculated_deflection_mm"] <= limit,
            "informative_only": True,
        }
        clauses = ["B.2"]
        warnings = [
            "Industrial portal frames under serviceability wind only; informative suggestion.",
            "Equipment, cladding and project-specific compatibility need separate review.",
        ]
    output = {
        "check_type": op,
        "standard": "AS 4100:2020",
        "clauses": clauses,
        "results": result,
        "warnings": warnings,
    }
    if not _finite(output):
        raise ValueError("Calculated output must be finite.")
    Draft202012Validator(OUTPUT_SCHEMA).validate(output)
    return output
