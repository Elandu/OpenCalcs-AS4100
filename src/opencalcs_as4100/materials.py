# SPDX-License-Identifier: AGPL-3.0-only
"""Selected AS 4100:2020 material strengths, properties and quality checks."""

from collections.abc import Mapping

from jsonschema import Draft202012Validator, ValidationError

from .standards import (
    ELASTIC_MODULUS_MPA,
    POISSON_RATIO,
    SHEAR_MODULUS_MPA,
    THERMAL_EXPANSION_PER_C,
)
from .validation import object_schema, validate_standard_strengths

_P = {"type": "number", "exclusiveMinimum": 0, "maximum": 10000}
_APPENDIX_M_ZB = {
    "t_cruciform_or_corner_diagram_group": -25,
    "corner_joint_diagram_group_1": -10,
    "single_run_fillet_with_z_a_zero": -5,
    "fillet_welds_butting_low_strength_material": -5,
    "multi_run_fillet": 0,
    "penetration_weld_with_shrinkage_reducing_sequence": 3,
    "penetration_weld_without_shrinkage_reducing_sequence": 5,
    "corner_joint_diagram_group_2": 8,
}
TABLED_STRENGTH_SCHEMA = object_schema(
    {
        "operation": {"const": "tabulated_strength"},
        "product_standard": {
            "enum": [
                "AS/NZS 1163",
                "AS/NZS 1594",
                "AS/NZS 3678",
                "AS/NZS 3679.1",
                "AS/NZS 3679.2",
                "AS 3597",
            ]
        },
        "form": {
            "enum": [
                "hollow_sections",
                "plate_strip_floorplate",
                "plate_strip",
                "plate_floorplate",
                "flats_sections",
                "hexagons_rounds_squares",
                "welded_i_sections",
                "plate",
            ]
        },
        "grade": {"type": "string", "minLength": 1, "maxLength": 30},
        "material_thickness_mm": _P,
    }
)
STEEL_CASTING_CONFORMITY_SCHEMA = object_schema(
    {
        "operation": {"const": "steel_casting_conformity"},
        "casting_grade": {"type": "string", "minLength": 1, "maxLength": 60},
        "as_2074_conformity_verified": {"type": "boolean"},
        "conformity_evidence_reference": {"type": ["string", "null"], "maxLength": 2000},
    },
    required=[
        "operation",
        "casting_grade",
        "as_2074_conformity_verified",
        "conformity_evidence_reference",
    ],
)
FASTENER_PRODUCT_CONFORMITY_SCHEMA = object_schema(
    {
        "operation": {"const": "fastener_product_conformity"},
        "item_or_assembly_identifier": {"type": "string", "minLength": 1, "maxLength": 100},
        "component_type": {
            "enum": [
                "bolt_or_screw",
                "nut",
                "washer",
                "high_strength_bolting_assembly",
                "galvanized_tower_bolting_assembly",
            ]
        },
        "product_standard": {
            "enum": [
                "AS 1110",
                "AS 1111",
                "AS 1112",
                "AS 1237.1",
                "AS/NZS 1252.1",
                "AS/NZS 1559",
            ]
        },
        "product_standard_applicability_verified": {"type": "boolean"},
        "conformity_certificate_verified": {"type": "boolean"},
        "conformity_evidence_reference": {"type": ["string", "null"], "maxLength": 2000},
    },
    required=[
        "operation",
        "item_or_assembly_identifier",
        "component_type",
        "product_standard",
        "product_standard_applicability_verified",
        "conformity_certificate_verified",
        "conformity_evidence_reference",
    ],
)
DESIGN_PROPERTIES_SCHEMA = object_schema({"operation": {"const": "design_properties"}})
THROUGH_THICKNESS_SCHEMA = object_schema(
    {
        "operation": {"const": "through_thickness_deformation"},
        "product_standard": {"const": "AS/NZS 3678"},
        "material_thickness_mm": _P,
        "required_design_z_value": {
            "type": ["number", "null"],
            "minimum": -32,
            "maximum": 43,
        },
        "appendix_m_assessment_verified": {"type": "boolean"},
        "appendix_m_assessment_reference": {"type": ["string", "null"], "maxLength": 2000},
        "available_z_quality_class": {"enum": [None, "Z15", "Z25", "Z35"]},
        "material_certificate_verified": {"type": "boolean"},
        "material_certificate_reference": {"type": ["string", "null"], "maxLength": 2000},
    },
    required=[
        "operation",
        "product_standard",
        "material_thickness_mm",
        "available_z_quality_class",
        "material_certificate_verified",
        "material_certificate_reference",
    ],
)
APPENDIX_M_THROUGH_THICKNESS_SCHEMA = object_schema(
    {
        "operation": {"const": "appendix_m_through_thickness_design"},
        "product_standard": {"const": "AS/NZS 3678"},
        "material_thickness_mm": _P,
        "effective_weld_depth_mm": _P,
        "table_m2_b_case": {"enum": list(_APPENDIX_M_ZB)},
        "low_strength_weld_material_verified": {"type": "boolean"},
        "low_strength_weld_material_reference": {
            "type": ["string", "null"],
            "maxLength": 2000,
        },
        "remote_restraint": {"enum": ["low", "medium", "high"]},
        "preheating_condition": {"enum": ["without_preheating", "at_least_100_c"]},
        "compression_reduction_basis": {"enum": ["not_applicable", "verified_applicable"]},
        "effective_weld_depth_assessment_verified": {"const": True},
        "table_m2_weld_form_case_verified": {"const": True},
        "remote_restraint_classification_verified": {"const": True},
        "preheating_condition_verified": {"const": True},
        "compression_reduction_applicability_verified": {"const": True},
        "available_z_quality_class": {"enum": [None, "Z15", "Z25", "Z35"]},
        "material_certificate_verified": {"type": "boolean"},
        "material_certificate_reference": {"type": ["string", "null"], "maxLength": 2000},
    }
)
TABLED_STRENGTH_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["standard", "operation", "values", "clauses", "warnings"],
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "operation": {"const": "tabulated_strength"},
        "values": {
            "type": "object",
            "required": ["yield_strength_mpa", "tensile_strength_mpa"],
            "properties": {
                "yield_strength_mpa": {"type": "number", "maximum": 690},
                "tensile_strength_mpa": {"type": "number", "minimum": 1},
            },
            "additionalProperties": False,
        },
        "clauses": {"const": ["2.1.1", "2.1.2", "Table 2.1"]},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}
_STEEL_CASTING_CONFORMITY_CHECK = {
    "type": "object",
    "required": ["clause", "requirement", "as_2074_conformity_verified", "satisfied"],
    "properties": {
        "clause": {"const": "2.4"},
        "requirement": {"const": "Steel castings conform to AS 2074"},
        "as_2074_conformity_verified": {"type": "boolean"},
        "evidence_reference": {"type": ["string", "null"]},
        "satisfied": {"type": "boolean"},
    },
    "additionalProperties": False,
}
STEEL_CASTING_CONFORMITY_OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "standard",
        "operation",
        "values",
        "clauses",
        "checks",
        "checked_conditions_satisfied",
        "full_standard_compliance",
        "warnings",
    ],
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "operation": {"const": "steel_casting_conformity"},
        "values": {
            "type": "object",
            "required": [
                "casting_grade",
                "product_standard",
                "as_2074_conformity_verified",
                "conformity_evidence_reference",
            ],
            "properties": {
                "casting_grade": {"type": "string", "minLength": 1},
                "product_standard": {"const": "AS 2074"},
                "as_2074_conformity_verified": {"type": "boolean"},
                "conformity_evidence_reference": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        "clauses": {"const": ["2.4"]},
        "checks": {
            "type": "array",
            "minItems": 1,
            "maxItems": 1,
            "items": _STEEL_CASTING_CONFORMITY_CHECK,
        },
        "checked_conditions_satisfied": {"type": "boolean"},
        "full_standard_compliance": {"const": False},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}
_FASTENER_PRODUCT_CONFORMITY_CHECK = {
    "type": "object",
    "required": [
        "clause",
        "component_type",
        "product_standard",
        "standard_listed_for_component",
        "product_standard_applicability_verified",
        "conformity_certificate_verified",
        "evidence_reference",
        "satisfied",
    ],
    "properties": {
        "clause": {"const": "2.3.1"},
        "component_type": {
            "enum": [
                "bolt_or_screw",
                "nut",
                "washer",
                "high_strength_bolting_assembly",
                "galvanized_tower_bolting_assembly",
            ]
        },
        "product_standard": {
            "enum": [
                "AS 1110",
                "AS 1111",
                "AS 1112",
                "AS 1237.1",
                "AS/NZS 1252.1",
                "AS/NZS 1559",
            ]
        },
        "standard_listed_for_component": {"type": "boolean"},
        "product_standard_applicability_verified": {"type": "boolean"},
        "conformity_certificate_verified": {"type": "boolean"},
        "evidence_reference": {"type": ["string", "null"]},
        "satisfied": {"type": "boolean"},
    },
    "additionalProperties": False,
}
FASTENER_PRODUCT_CONFORMITY_OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "standard",
        "operation",
        "values",
        "clauses",
        "checks",
        "checked_conditions_satisfied",
        "full_standard_compliance",
        "warnings",
    ],
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "operation": {"const": "fastener_product_conformity"},
        "values": {
            "type": "object",
            "required": [
                "item_or_assembly_identifier",
                "component_type",
                "product_standard",
                "product_standard_applicability_verified",
                "conformity_certificate_verified",
                "conformity_evidence_reference",
            ],
            "properties": {
                "item_or_assembly_identifier": {"type": "string", "minLength": 1},
                "component_type": {
                    "enum": [
                        "bolt_or_screw",
                        "nut",
                        "washer",
                        "high_strength_bolting_assembly",
                        "galvanized_tower_bolting_assembly",
                    ]
                },
                "product_standard": {
                    "enum": [
                        "AS 1110",
                        "AS 1111",
                        "AS 1112",
                        "AS 1237.1",
                        "AS/NZS 1252.1",
                        "AS/NZS 1559",
                    ]
                },
                "product_standard_applicability_verified": {"type": "boolean"},
                "conformity_certificate_verified": {"type": "boolean"},
                "conformity_evidence_reference": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        "clauses": {"const": ["2.3.1"]},
        "checks": {
            "type": "array",
            "minItems": 1,
            "maxItems": 1,
            "items": _FASTENER_PRODUCT_CONFORMITY_CHECK,
        },
        "checked_conditions_satisfied": {"type": "boolean"},
        "full_standard_compliance": {"const": False},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}
DESIGN_PROPERTIES_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["standard", "operation", "values", "clauses", "warnings"],
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "operation": {"const": "design_properties"},
        "values": {
            "type": "object",
            "required": [
                "elastic_modulus_mpa",
                "shear_modulus_mpa",
                "poisson_ratio",
                "thermal_expansion_per_c",
            ],
            "properties": {
                "elastic_modulus_mpa": {"const": ELASTIC_MODULUS_MPA},
                "shear_modulus_mpa": {"const": SHEAR_MODULUS_MPA},
                "poisson_ratio": {"const": POISSON_RATIO},
                "thermal_expansion_per_c": {"const": THERMAL_EXPANSION_PER_C},
            },
            "additionalProperties": False,
        },
        "clauses": {"const": ["2.2.4"]},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}
_THROUGH_THICKNESS_CHECK = {
    "type": "object",
    "required": [
        "clause",
        "required_design_z_value",
        "exemption_applies",
        "required_z_quality_class",
        "available_z_quality_class",
        "required_reduction_of_area_percent",
        "class_sufficient",
        "certificate_evidence_satisfied",
        "satisfied",
    ],
    "properties": {
        "clause": {"const": "2.2.5"},
        "required_design_z_value": {"type": ["number", "null"]},
        "exemption_applies": {"type": "boolean"},
        "required_z_quality_class": {"enum": [None, "Z15", "Z25", "Z35"]},
        "available_z_quality_class": {"enum": [None, "Z15", "Z25", "Z35"]},
        "required_reduction_of_area_percent": {"type": ["number", "null"]},
        "class_sufficient": {"type": "boolean"},
        "certificate_evidence_satisfied": {"type": "boolean"},
        "satisfied": {"type": "boolean"},
    },
    "additionalProperties": False,
}
THROUGH_THICKNESS_OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "standard",
        "operation",
        "clauses",
        "values",
        "checks",
        "checked_conditions_satisfied",
        "full_standard_compliance",
        "warnings",
    ],
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "operation": {"const": "through_thickness_deformation"},
        "clauses": {"const": ["2.2.5"]},
        "values": {
            "type": "object",
            "required": [
                "product_standard",
                "material_thickness_mm",
                "required_design_z_value",
                "appendix_m_assessment_verified",
                "appendix_m_assessment_reference",
                "available_z_quality_class",
                "material_certificate_verified",
                "material_certificate_reference",
                "required_z_quality_class",
                "required_reduction_of_area_percent",
            ],
            "properties": {
                "product_standard": {"const": "AS/NZS 3678"},
                "material_thickness_mm": {"type": "number", "exclusiveMinimum": 0},
                "required_design_z_value": {"type": ["number", "null"]},
                "appendix_m_assessment_verified": {"type": "boolean"},
                "appendix_m_assessment_reference": {"type": ["string", "null"]},
                "available_z_quality_class": {"enum": [None, "Z15", "Z25", "Z35"]},
                "material_certificate_verified": {"type": "boolean"},
                "material_certificate_reference": {"type": ["string", "null"]},
                "required_z_quality_class": {"enum": [None, "Z15", "Z25", "Z35"]},
                "required_reduction_of_area_percent": {"type": ["number", "null"]},
            },
            "additionalProperties": False,
        },
        "checks": {
            "type": "array",
            "minItems": 1,
            "maxItems": 1,
            "items": _THROUGH_THICKNESS_CHECK,
        },
        "checked_conditions_satisfied": {"type": "boolean"},
        "full_standard_compliance": {"const": False},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}
APPENDIX_M_THROUGH_THICKNESS_OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "standard",
        "operation",
        "clauses",
        "values",
        "checks",
        "checked_conditions_satisfied",
        "full_standard_compliance",
        "warnings",
    ],
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "operation": {"const": "appendix_m_through_thickness_design"},
        "clauses": {"const": ["2.2.5", "3.8", "Appendix M.2", "Table M.2"]},
        "values": {
            "type": "object",
            "required": [
                "product_standard",
                "material_thickness_mm",
                "effective_weld_depth_mm",
                "table_m2_b_case",
                "low_strength_weld_material_verified",
                "low_strength_weld_material_reference",
                "table_m2_b_case_eligibility_satisfied",
                "remote_restraint",
                "preheating_condition",
                "compression_reduction_basis",
                "z_a",
                "z_b",
                "z_c_before_reduction",
                "z_c_after_reduction",
                "z_c_reduction_factor",
                "z_d",
                "z_e",
                "required_design_z_value",
                "effective_weld_depth_assessment_verified",
                "table_m2_weld_form_case_verified",
                "remote_restraint_classification_verified",
                "preheating_condition_verified",
                "compression_reduction_applicability_verified",
                "available_z_quality_class",
                "required_z_quality_class",
                "required_reduction_of_area_percent",
                "material_certificate_verified",
                "material_certificate_reference",
            ],
            "properties": {
                "product_standard": {"const": "AS/NZS 3678"},
                "material_thickness_mm": {"type": "number", "exclusiveMinimum": 0},
                "effective_weld_depth_mm": {"type": "number", "exclusiveMinimum": 0},
                "table_m2_b_case": {"enum": list(_APPENDIX_M_ZB)},
                "low_strength_weld_material_verified": {"type": "boolean"},
                "low_strength_weld_material_reference": {
                    "type": ["string", "null"],
                    "maxLength": 2000,
                },
                "table_m2_b_case_eligibility_satisfied": {"const": True},
                "remote_restraint": {"enum": ["low", "medium", "high"]},
                "preheating_condition": {"enum": ["without_preheating", "at_least_100_c"]},
                "compression_reduction_basis": {"enum": ["not_applicable", "verified_applicable"]},
                "z_a": {"type": "number"},
                "z_b": {"type": "number"},
                "z_c_before_reduction": {"type": "number"},
                "z_c_after_reduction": {"type": "number"},
                "z_c_reduction_factor": {"enum": [0.5, 1.0]},
                "z_d": {"type": "number"},
                "z_e": {"type": "number"},
                "required_design_z_value": {"type": "number", "minimum": -32, "maximum": 43},
                "effective_weld_depth_assessment_verified": {"const": True},
                "table_m2_weld_form_case_verified": {"const": True},
                "remote_restraint_classification_verified": {"const": True},
                "preheating_condition_verified": {"const": True},
                "compression_reduction_applicability_verified": {"const": True},
                "available_z_quality_class": {"enum": [None, "Z15", "Z25", "Z35"]},
                "required_z_quality_class": {"enum": [None, "Z15", "Z25", "Z35"]},
                "required_reduction_of_area_percent": {"type": ["number", "null"]},
                "material_certificate_verified": {"type": "boolean"},
                "material_certificate_reference": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        "checks": {
            "type": "array",
            "minItems": 1,
            "maxItems": 1,
            "items": _THROUGH_THICKNESS_CHECK,
        },
        "checked_conditions_satisfied": {"type": "boolean"},
        "full_standard_compliance": {"const": False},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}

_UNIDENTIFIED_BASE = {
    "design_yield_strength_mpa": {"type": "number", "exclusiveMinimum": 0, "maximum": 690},
    "design_tensile_strength_mpa": _P,
    "surface_imperfections_verified": {"const": True},
    "properties_and_weldability_verified": {"const": True},
}
_UNIDENTIFIED_NO_TEST_SCHEMA = object_schema(
    {
        "operation": {"const": "unidentified_steel"},
        **_UNIDENTIFIED_BASE,
        "full_test_to_as1391_verified": {"const": False},
    }
)
_UNIDENTIFIED_TESTED_SCHEMA = object_schema(
    {
        "operation": {"const": "unidentified_steel"},
        **_UNIDENTIFIED_BASE,
        "full_test_to_as1391_verified": {"const": True},
        "test_report_reference": {"type": "string", "minLength": 1, "maxLength": 2000},
    }
)
INPUT_SCHEMA = {
    "oneOf": [
        TABLED_STRENGTH_SCHEMA,
        STEEL_CASTING_CONFORMITY_SCHEMA,
        FASTENER_PRODUCT_CONFORMITY_SCHEMA,
        DESIGN_PROPERTIES_SCHEMA,
        THROUGH_THICKNESS_SCHEMA,
        APPENDIX_M_THROUGH_THICKNESS_SCHEMA,
        _UNIDENTIFIED_NO_TEST_SCHEMA,
        _UNIDENTIFIED_TESTED_SCHEMA,
    ]
}

_UNIDENTIFIED_CHECK = {
    "type": "object",
    "required": ["clause", "strength", "value_mpa", "limit_mpa", "basis", "satisfied"],
    "properties": {
        "clause": {"const": "2.2.3"},
        "strength": {"enum": ["yield", "tensile"]},
        "value_mpa": {"type": "number", "exclusiveMinimum": 0},
        "limit_mpa": {"type": ["number", "null"]},
        "basis": {"enum": ["maximum_design_strength", "full_test_to_as1391"]},
        "satisfied": {"type": "boolean"},
    },
    "additionalProperties": False,
}
UNIDENTIFIED_STEEL_OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "standard",
        "operation",
        "clauses",
        "values",
        "checks",
        "checked_conditions_satisfied",
        "full_standard_compliance",
        "warnings",
    ],
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "operation": {"const": "unidentified_steel"},
        "clauses": {"const": ["2.2.3"]},
        "values": {
            "type": "object",
            "required": [
                "design_yield_strength_mpa",
                "design_tensile_strength_mpa",
                "full_test_to_as1391_verified",
                "test_report_reference",
            ],
            "properties": {
                "design_yield_strength_mpa": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "maximum": 690,
                },
                "design_tensile_strength_mpa": {"type": "number", "exclusiveMinimum": 0},
                "full_test_to_as1391_verified": {"type": "boolean"},
                "test_report_reference": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        "checks": {"type": "array", "minItems": 2, "maxItems": 2, "items": _UNIDENTIFIED_CHECK},
        "checked_conditions_satisfied": {"type": "boolean"},
        "full_standard_compliance": {"const": False},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}
OUTPUT_SCHEMA = {
    "oneOf": [
        TABLED_STRENGTH_OUTPUT_SCHEMA,
        STEEL_CASTING_CONFORMITY_OUTPUT_SCHEMA,
        FASTENER_PRODUCT_CONFORMITY_OUTPUT_SCHEMA,
        DESIGN_PROPERTIES_OUTPUT_SCHEMA,
        THROUGH_THICKNESS_OUTPUT_SCHEMA,
        APPENDIX_M_THROUGH_THICKNESS_OUTPUT_SCHEMA,
        UNIDENTIFIED_STEEL_OUTPUT_SCHEMA,
    ]
}

# Rows: standard, form, grade, lower t, lower inclusive, upper t, upper inclusive, fy, fu.
# Numerical lookup values only; product certification and Table 2.1 notes remain applicable.
_ROWS = [
    ("AS/NZS 1163", "hollow_sections", g, 0, True, 0, False, fy, fu)
    for g, fy, fu in (("C450", 450, 500), ("C350", 350, 430), ("C250", 250, 320))
]
_ROWS += [
    ("AS/NZS 1594", "plate_strip_floorplate", g, 0, True, 0, False, fy, fu)
    for g, fy, fu in (
        ("HA400", 380, 460),
        ("HW350", 340, 450),
        ("HA350", 350, 430),
        ("HA300/1", 300, 430),
        ("HU300/1", 300, 430),
        ("HA300", 300, 400),
        ("HU300", 300, 400),
        ("HA250", 250, 350),
        ("HU250", 250, 350),
        ("HA200", 200, 300),
    )
]
_ROWS += [
    ("AS/NZS 1594", "plate_strip", g, 0, True, upper, True, fy, fu)
    for g, upper, fy, fu in (("XF500", 8, 480, 570), ("XF400", 8, 380, 460))
]
_ROWS.append(("AS/NZS 1594", "plate_strip", "XF300", 0, True, 0, False, 300, 440))

_ROWS += [
    ("AS/NZS 3678", "plate_floorplate", grade, lo, lo_inc, hi, hi_inc, fy, fu)
    for grade, lo, lo_inc, hi, hi_inc, fy, fu in [
        ("450", 0, True, 20, True, 450, 520),
        ("450", 20, False, 32, True, 420, 500),
        ("450", 32, False, 50, True, 400, 500),
        ("400", 0, True, 12, True, 400, 480),
        ("400", 12, False, 20, True, 380, 480),
        ("400", 20, False, 80, True, 360, 480),
        ("350", 0, True, 12, True, 360, 450),
        ("350", 12, False, 20, True, 350, 450),
        ("350", 20, False, 80, True, 340, 450),
        ("350", 80, False, 150, True, 330, 450),
        ("WR350", 0, True, 50, True, 340, 450),
        ("300", 0, True, 8, True, 320, 430),
        ("300", 8, False, 12, True, 310, 430),
        ("300", 12, False, 20, True, 300, 430),
        ("300", 20, False, 50, True, 280, 430),
        ("300", 50, False, 80, True, 270, 430),
        ("300", 80, False, 150, True, 260, 430),
        ("250", 0, True, 8, True, 280, 410),
        ("250", 8, False, 12, True, 260, 410),
        ("250", 12, False, 50, True, 250, 410),
        ("250", 50, False, 80, True, 240, 410),
        ("250", 80, False, 150, True, 230, 410),
        ("200", 0, True, 12, True, 200, 300),
    ]
]

_ROWS += [
    (
        "AS/NZS 3679.1",
        "flats_sections",
        grade,
        lo,
        lo_inc,
        hi,
        hi_inc,
        fy,
        480 if grade == "350" else 440,
    )
    for grade, lo, lo_inc, hi, hi_inc, fy in [
        ("350", 0, True, 11, True, 360),
        ("350", 11, False, 40, False, 340),
        ("350", 40, True, 0, False, 330),
        ("300", 0, True, 11, False, 320),
        ("300", 11, True, 17, True, 300),
        ("300", 17, False, 0, False, 280),
    ]
]
_ROWS += [
    ("AS/NZS 3679.1", "hexagons_rounds_squares", grade, lo, lo_inc, hi, hi_inc, fy, fu)
    for grade, lo, lo_inc, hi, hi_inc, fy, fu in [
        ("350", 0, True, 50, True, 340, 480),
        ("350", 50, False, 100, False, 330, 480),
        ("350", 100, True, 0, False, 320, 480),
        ("300", 0, True, 50, True, 300, 440),
        ("300", 50, False, 100, False, 290, 440),
        ("300", 100, True, 0, False, 280, 440),
    ]
]
_ROWS += [
    ("AS 3597", "plate", grade, lo, lo_inc, hi, True, fy, fu)
    for grade, lo, lo_inc, hi, fy, fu in [
        ("500", 5, True, 110, 500, 590),
        ("600", 5, True, 110, 600, 690),
        ("700", 0, True, 5, 650, 750),
        ("700", 5, False, 65, 690, 790),
        ("700", 65, False, 110, 620, 720),
    ]
]


def _contains(t, lower, lower_inclusive, upper, upper_inclusive):
    if t < lower or (t == lower and not lower_inclusive):
        return False
    return not upper or t < upper or (t == upper and upper_inclusive)


def run_materials(inputs: Mapping) -> dict:
    if not isinstance(inputs, Mapping):
        raise ValueError("Inputs must be an object.")
    data = dict(inputs)
    try:
        Draft202012Validator(INPUT_SCHEMA).validate(data)
    except ValidationError as exc:
        raise ValueError(exc.message) from exc
    validate_standard_strengths(data)
    if data["operation"] == "steel_casting_conformity":
        return _steel_casting_conformity(data)
    if data["operation"] == "fastener_product_conformity":
        return _fastener_product_conformity(data)
    if data["operation"] == "design_properties":
        return _design_properties()
    if data["operation"] == "through_thickness_deformation":
        return _through_thickness_deformation(data)
    if data["operation"] == "appendix_m_through_thickness_design":
        return _appendix_m_through_thickness_design(data)
    if data["operation"] == "unidentified_steel":
        return _unidentified_steel(data)

    lookup_standard = data["product_standard"]
    lookup_form = data["form"]
    welded_i = lookup_standard == "AS/NZS 3679.2" and lookup_form == "welded_i_sections"
    if welded_i:
        lookup_standard = "AS/NZS 3678"
        lookup_form = "plate_floorplate"
    matches = [
        row
        for row in _ROWS
        if row[:3] == (lookup_standard, lookup_form, data["grade"])
        and _contains(data["material_thickness_mm"], *row[3:7])
    ]
    if len(matches) != 1:
        raise ValueError(
            "No unique Table 2.1 strength row matches this product, grade and thickness."
        )
    row = matches[0]
    warnings = [
        "Confirm the certified product standard, grade, product form and material thickness.",
        "Assess Table 2.1 notes and clauses 2.2–2.5, including heat treatment "
        "and lamellar tearing.",
    ]
    if welded_i:
        warnings.append("Table 2.1 uses the AS/NZS 3678 parent plate grade for welded I-sections.")
    result = {
        "standard": "AS 4100:2020",
        "operation": "tabulated_strength",
        "values": {"yield_strength_mpa": row[7], "tensile_strength_mpa": row[8]},
        "clauses": ["2.1.1", "2.1.2", "Table 2.1"],
        "warnings": warnings,
    }
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result


def _steel_casting_conformity(data: Mapping) -> dict:
    """Record the assessed AS 2074 conformity required by Clause 2.4."""
    grade = data["casting_grade"].strip()
    reference = (data["conformity_evidence_reference"] or "").strip()
    verified = data["as_2074_conformity_verified"]
    if not grade:
        raise ValueError("Steel casting grade must not be blank.")
    if verified and not reference:
        raise ValueError("Verified AS 2074 conformity requires an evidence reference.")

    result = {
        "standard": "AS 4100:2020",
        "operation": "steel_casting_conformity",
        "values": {
            "casting_grade": grade,
            "product_standard": "AS 2074",
            "as_2074_conformity_verified": verified,
            "conformity_evidence_reference": reference or None,
        },
        "clauses": ["2.4"],
        "checks": [
            {
                "clause": "2.4",
                "requirement": "Steel castings conform to AS 2074",
                "as_2074_conformity_verified": verified,
                "evidence_reference": reference or None,
                "satisfied": verified,
            }
        ],
        "checked_conditions_satisfied": verified,
        "full_standard_compliance": False,
        "warnings": [
            "This operation records the supplied Clause 2.4 conformity assessment; it does not "
            "authenticate the evidence reference or confirm the casting grade or properties "
            "against AS 2074.",
            "Obtain and independently verify the design strengths and other properties used "
            "for the casting; this operation does not calculate them.",
        ],
    }
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result


_FASTENER_COMPONENT_STANDARDS = {
    "bolt_or_screw": {"AS 1110", "AS 1111"},
    "nut": {"AS 1112"},
    "washer": {"AS 1237.1"},
    "high_strength_bolting_assembly": {"AS/NZS 1252.1"},
    "galvanized_tower_bolting_assembly": {"AS/NZS 1559"},
}


def _fastener_product_conformity(data: Mapping) -> dict:
    """Record the assessed product-standard evidence required by Clause 2.3.1."""
    identifier = data["item_or_assembly_identifier"].strip()
    reference = (data["conformity_evidence_reference"] or "").strip()
    if not identifier:
        raise ValueError("Fastener item or assembly identifier must not be blank.")
    if data["conformity_certificate_verified"] and not reference:
        raise ValueError("Verified fastener conformity requires an evidence reference.")

    component_type = data["component_type"]
    product_standard = data["product_standard"]
    listed = product_standard in _FASTENER_COMPONENT_STANDARDS[component_type]
    applicable = data["product_standard_applicability_verified"]
    certificate_verified = data["conformity_certificate_verified"]
    satisfied = listed and applicable and certificate_verified and bool(reference)
    result = {
        "standard": "AS 4100:2020",
        "operation": "fastener_product_conformity",
        "values": {
            "item_or_assembly_identifier": identifier,
            "component_type": component_type,
            "product_standard": product_standard,
            "product_standard_applicability_verified": applicable,
            "conformity_certificate_verified": certificate_verified,
            "conformity_evidence_reference": reference or None,
        },
        "clauses": ["2.3.1"],
        "checks": [
            {
                "clause": "2.3.1",
                "component_type": component_type,
                "product_standard": product_standard,
                "standard_listed_for_component": listed,
                "product_standard_applicability_verified": applicable,
                "conformity_certificate_verified": certificate_verified,
                "evidence_reference": reference or None,
                "satisfied": satisfied,
            }
        ],
        "checked_conditions_satisfied": satisfied,
        "full_standard_compliance": False,
        "warnings": [
            "This operation records the supplied Clause 2.3.1 assessment; it does not "
            "authenticate the item, certificate or test report, or determine whether the "
            "product standard is suitable for the project.",
            "Verify the applicable product-standard certificate requirements and any "
            "laboratory qualification requirements separately; this operation does not "
            "assess laboratory accreditation.",
        ],
    }
    if product_standard == "AS/NZS 1559":
        result["warnings"].append(
            "AS/NZS 1559 is specific to tower construction; verify its suitability for this "
            "structure independently."
        )
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result


def _design_properties() -> dict:
    result = {
        "standard": "AS 4100:2020",
        "operation": "design_properties",
        "values": {
            "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
            "shear_modulus_mpa": SHEAR_MODULUS_MPA,
            "poisson_ratio": POISSON_RATIO,
            "thermal_expansion_per_c": THERMAL_EXPANSION_PER_C,
        },
        "clauses": ["2.2.4"],
        "warnings": [
            "These are the Clause 2.2.4 design properties for steel; they do not "
            "establish material certification or project applicability."
        ],
    }
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result


def _unidentified_steel(data: Mapping) -> dict:
    """Compare unidentified-steel design strengths with the Clause 2.2.3 limits."""
    tested = data["full_test_to_as1391_verified"]
    report = data.get("test_report_reference")
    limits = {"yield": 170, "tensile": 300}
    checks = []
    for strength, key in (
        ("yield", "design_yield_strength_mpa"),
        ("tensile", "design_tensile_strength_mpa"),
    ):
        value = data[key]
        limit = None if tested else limits[strength]
        checks.append(
            {
                "clause": "2.2.3",
                "strength": strength,
                "value_mpa": value,
                "limit_mpa": limit,
                "basis": "full_test_to_as1391" if tested else "maximum_design_strength",
                "satisfied": tested or value <= limit,
            }
        )
    result = {
        "standard": "AS 4100:2020",
        "operation": "unidentified_steel",
        "clauses": ["2.2.3"],
        "values": {
            "design_yield_strength_mpa": data["design_yield_strength_mpa"],
            "design_tensile_strength_mpa": data["design_tensile_strength_mpa"],
            "full_test_to_as1391_verified": tested,
            "test_report_reference": report,
        },
        "checks": checks,
        "checked_conditions_satisfied": all(item["satisfied"] for item in checks),
        "full_standard_compliance": False,
        "warnings": [
            "Verify unidentified steel is free from surface imperfections and its "
            "physical properties and weldability do not adversely affect "
            "strength or serviceability.",
            "Prerequisite attestations and any AS 1391 test report are not "
            "authenticated by this check.",
        ],
    }
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result


def _through_thickness_deformation(data: Mapping) -> dict:
    """Compare an assessed Appendix M demand with Clause 2.2.5 Z-quality limits."""
    thickness = data["material_thickness_mm"]
    z_ed = data.get("required_design_z_value")
    exempt = thickness <= 16 or (z_ed is not None and z_ed <= 10)
    required_class = None
    required_reduction = None
    if not exempt and z_ed is not None:
        if z_ed <= 20:
            required_class, required_reduction = "Z15", 15
        elif z_ed <= 30:
            required_class, required_reduction = "Z25", 25
        else:
            required_class, required_reduction = "Z35", 35

    available_class = data["available_z_quality_class"]
    class_rank = {"Z15": 15, "Z25": 25, "Z35": 35}
    class_sufficient = required_class is None or (
        available_class is not None and class_rank[available_class] >= class_rank[required_class]
    )
    assessment_evidence_satisfied = thickness <= 16 or (
        z_ed is not None
        and data.get("appendix_m_assessment_verified", False)
        and bool(data.get("appendix_m_assessment_reference"))
    )
    certificate_evidence_satisfied = required_class is None or (
        data["material_certificate_verified"] and bool(data["material_certificate_reference"])
    )
    satisfied = (
        assessment_evidence_satisfied and class_sufficient and certificate_evidence_satisfied
    )
    result = {
        "standard": "AS 4100:2020",
        "operation": "through_thickness_deformation",
        "clauses": ["2.2.5"],
        "values": {
            "product_standard": data["product_standard"],
            "material_thickness_mm": thickness,
            "required_design_z_value": z_ed,
            "appendix_m_assessment_verified": data.get("appendix_m_assessment_verified", False),
            "appendix_m_assessment_reference": data.get("appendix_m_assessment_reference"),
            "available_z_quality_class": available_class,
            "material_certificate_verified": data["material_certificate_verified"],
            "material_certificate_reference": data["material_certificate_reference"],
            "required_z_quality_class": required_class,
            "required_reduction_of_area_percent": required_reduction,
        },
        "checks": [
            {
                "clause": "2.2.5",
                "required_design_z_value": z_ed,
                "exemption_applies": exempt,
                "required_z_quality_class": required_class,
                "available_z_quality_class": available_class,
                "required_reduction_of_area_percent": required_reduction,
                "class_sufficient": class_sufficient,
                "certificate_evidence_satisfied": certificate_evidence_satisfied,
                "satisfied": satisfied,
            }
        ],
        "checked_conditions_satisfied": satisfied,
        "full_standard_compliance": False,
        "warnings": [
            (
                "The thickness exemption to the Clause 2.2.5 Z-quality requirement applies."
                if thickness <= 16
                else (
                    "The required Appendix M design Z-value is missing for material "
                    "thicker than 16 mm."
                    if z_ed is None
                    else "The design Z-value is supplied from an external Appendix M assessment; "
                    "the plugin does not interpret weld-layout diagrams or calculate ZEd."
                )
            ),
            "Assessment references and material certificates are recorded but not authenticated.",
            "Clause 3.8 joint detailing, through-thickness stress and weld-size requirements "
            "still require engineering assessment.",
        ],
    }
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result


def _appendix_m_through_thickness_design(data: Mapping) -> dict:
    """Calculate selected Table M.2 terms and apply the Clause 2.2.5 class check."""
    depth = data["effective_weld_depth_mm"]
    thickness = data["material_thickness_mm"]
    z_a = (
        0
        if depth <= 7
        else 3
        if depth <= 10
        else 6
        if depth <= 20
        else 9
        if depth <= 30
        else 12
        if depth <= 40
        else 15
    )
    b_case = data["table_m2_b_case"]
    low_strength_verified = data["low_strength_weld_material_verified"]
    low_strength_reference = (data["low_strength_weld_material_reference"] or "").strip()
    if b_case == "single_run_fillet_with_z_a_zero":
        if z_a != 0:
            raise ValueError("Table M.2(b) single-run fillet case requires Za = 0.")
        if low_strength_verified or low_strength_reference:
            raise ValueError(
                "Low-strength weld-material evidence applies only to the butting fillet case."
            )
    elif b_case == "fillet_welds_butting_low_strength_material":
        if z_a <= 1:
            raise ValueError("Table M.2(b) low-strength butting fillet case requires Za > 1.")
        if not low_strength_verified or not low_strength_reference:
            raise ValueError(
                "The low-strength butting fillet case requires verified weld-material evidence "
                "and a reference."
            )
    elif low_strength_verified or low_strength_reference:
        raise ValueError(
            "Low-strength weld-material evidence applies only to the butting fillet case."
        )
    z_b = _APPENDIX_M_ZB[b_case]
    z_c = (
        2
        if thickness <= 10
        else 4
        if thickness <= 20
        else 6
        if thickness <= 30
        else 8
        if thickness <= 40
        else 10
        if thickness <= 50
        else 12
        if thickness <= 60
        else 15
    )
    z_c_factor = 0.5 if data["compression_reduction_basis"] == "verified_applicable" else 1.0
    z_c_adjusted = z_c * z_c_factor
    z_d = {"low": 0, "medium": 3, "high": 5}[data["remote_restraint"]]
    z_e = {"without_preheating": 0, "at_least_100_c": -8}[data["preheating_condition"]]
    z_ed = z_a + z_b + z_c_adjusted + z_d + z_e
    quality_result = _through_thickness_deformation(
        {
            "product_standard": data["product_standard"],
            "material_thickness_mm": thickness,
            "required_design_z_value": z_ed,
            "appendix_m_assessment_verified": True,
            "appendix_m_assessment_reference": "Calculated from AS 4100:2020 Table M.2",
            "available_z_quality_class": data["available_z_quality_class"],
            "material_certificate_verified": data["material_certificate_verified"],
            "material_certificate_reference": data["material_certificate_reference"],
        }
    )
    quality_values = quality_result["values"]
    values = {
        "product_standard": data["product_standard"],
        "material_thickness_mm": thickness,
        "effective_weld_depth_mm": depth,
        "table_m2_b_case": data["table_m2_b_case"],
        "low_strength_weld_material_verified": low_strength_verified,
        "low_strength_weld_material_reference": low_strength_reference or None,
        "table_m2_b_case_eligibility_satisfied": True,
        "remote_restraint": data["remote_restraint"],
        "preheating_condition": data["preheating_condition"],
        "compression_reduction_basis": data["compression_reduction_basis"],
        "z_a": z_a,
        "z_b": z_b,
        "z_c_before_reduction": z_c,
        "z_c_after_reduction": z_c_adjusted,
        "z_c_reduction_factor": z_c_factor,
        "z_d": z_d,
        "z_e": z_e,
        "required_design_z_value": z_ed,
        "effective_weld_depth_assessment_verified": data[
            "effective_weld_depth_assessment_verified"
        ],
        "table_m2_weld_form_case_verified": data["table_m2_weld_form_case_verified"],
        "remote_restraint_classification_verified": data[
            "remote_restraint_classification_verified"
        ],
        "preheating_condition_verified": data["preheating_condition_verified"],
        "compression_reduction_applicability_verified": data[
            "compression_reduction_applicability_verified"
        ],
        "available_z_quality_class": data["available_z_quality_class"],
        "required_z_quality_class": quality_values["required_z_quality_class"],
        "required_reduction_of_area_percent": quality_values["required_reduction_of_area_percent"],
        "material_certificate_verified": data["material_certificate_verified"],
        "material_certificate_reference": data["material_certificate_reference"],
    }
    result = {
        "standard": "AS 4100:2020",
        "operation": "appendix_m_through_thickness_design",
        "clauses": ["2.2.5", "3.8", "Appendix M.2", "Table M.2"],
        "values": values,
        "checks": quality_result["checks"],
        "checked_conditions_satisfied": quality_result["checked_conditions_satisfied"],
        "full_standard_compliance": False,
        "warnings": [
            "Appendix M is informative guidance; this operation calculates the listed Table M.2 "
            "terms from the supplied effective depth and verified classifications.",
            "The effective depth, weld-form/sequence case, restraint, preheat and compression "
            "reduction assessments are declarations and are not authenticated.",
            "Clause 3.8 joint geometry, through-thickness stress, welding, fabrication and "
            "inspection still require project engineering assessment.",
            "Material certificate evidence is recorded but not authenticated.",
        ],
    }
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result
