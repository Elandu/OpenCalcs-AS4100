"""Strict JSON schemas; input units are mm, MPa and kN."""

INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "gross_area_mm2",
        "net_area_mm2",
        "yield_strength_mpa",
        "ultimate_strength_mpa",
        "tension_distribution_factor",
        "compression_form_factor",
        "tension_action_kn",
        "compression_action_kn",
    ],
    "properties": {
        **{
            key: {"type": "number", "exclusiveMinimum": 0, "maximum": 1e12}
            for key in [
                "gross_area_mm2",
                "net_area_mm2",
                "yield_strength_mpa",
                "ultimate_strength_mpa",
            ]
        },
        **{
            key: {"type": "number", "exclusiveMinimum": 0, "maximum": 1}
            for key in ["tension_distribution_factor", "compression_form_factor"]
        },
        **{
            key: {"type": "number", "minimum": 0, "maximum": 1e12}
            for key in ["tension_action_kn", "compression_action_kn"]
        },
    },
}
_CHECK = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "nominal_capacity_kn",
        "design_capacity_kn",
        "action_kn",
        "utilisation",
        "section_capacity_satisfied",
        "governing_mode",
    ],
    "properties": {
        **{
            key: {"type": "number", "minimum": 0}
            for key in ["nominal_capacity_kn", "design_capacity_kn", "action_kn", "utilisation"]
        },
        "section_capacity_satisfied": {"type": "boolean"},
        "governing_mode": {"type": "string"},
    },
}
OUTPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "standard",
        "scope",
        "capacity_factor",
        "tension",
        "compression",
        "warnings",
        "tension_nominal_modes_kn",
    ],
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "scope": {"const": "section axial capacities only"},
        "capacity_factor": {"const": 0.9},
        "tension_nominal_modes_kn": {
            "type": "object",
            "additionalProperties": False,
            "required": ["gross_yielding", "net_fracture"],
            "properties": {
                key: {"type": "number", "exclusiveMinimum": 0}
                for key in ["gross_yielding", "net_fracture"]
            },
        },
        "tension": _CHECK,
        "compression": _CHECK,
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}
