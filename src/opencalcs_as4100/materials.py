# SPDX-License-Identifier: AGPL-3.0-only
"""Material strength limits tabulated by AS 4100:2020 Table 2.1."""

from collections.abc import Mapping

from jsonschema import Draft202012Validator, ValidationError

from .validation import object_schema

_P = {"type": "number", "exclusiveMinimum": 0, "maximum": 10000}
INPUT_SCHEMA = object_schema(
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
OUTPUT_SCHEMA = {
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
