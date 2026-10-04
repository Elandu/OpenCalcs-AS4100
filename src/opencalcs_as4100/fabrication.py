# SPDX-License-Identifier: AGPL-3.0-only
"""AS 4100:2020 Clause 14.3.2 bolt-hole geometry and use checks."""

from .validation import POSITIVE, object_schema, result, validate

_NUMBER = {"type": "number", "minimum": 0, "maximum": 1e12}
_BOOL = {"type": "boolean"}


def _plate_washer_schema():
    return object_schema(
        {
            "type": {"const": "plate"},
            "thickness_mm": POSITIVE,
            "minimum_edge_clearance_mm": _NUMBER,
            "coverage_geometry_verified": _BOOL,
            "product_verified": _BOOL,
            "material_as_nzs_3678_verified": _BOOL,
        }
    )


_HARDENED_WASHER = object_schema({"type": {"const": "hardened"}, "product_verified": _BOOL})
_PLATE_WASHER = _plate_washer_schema()
_SIDE = object_schema(
    {
        "bears_on_holed_ply": _BOOL,
        "washer": {
            "oneOf": [
                {"type": "null"},
                _HARDENED_WASHER,
                _PLATE_WASHER,
            ]
        },
    }
)


def _hole_schema(hole_type, properties, required=None, conditions=()):
    schema = object_schema(
        {
            "check_type": {"const": "bolt_hole"},
            "hole_type": {"const": hole_type},
            "bolt_diameter_mm": POSITIVE,
            **properties,
        },
        required=[
            "check_type",
            "hole_type",
            "bolt_diameter_mm",
            *(required if required is not None else properties),
        ],
    )
    if conditions:
        schema["allOf"] = list(conditions)
    return schema


_CONNECTION_PROPERTIES = {
    "not_base_plate_anchor_hole_verified": _BOOL,
    "connection_type": {"enum": ["bearing_type", "friction_type"]},
    "subject_to_shear": _BOOL,
    "head_side": _SIDE,
    "nut_side": _SIDE,
}
_CONNECTION_REQUIRED = [
    "not_base_plate_anchor_hole_verified",
    "connection_type",
    "subject_to_shear",
    "head_side",
    "nut_side",
]
_BEARING_SHEAR = {
    "if": {
        "properties": {
            "connection_type": {"const": "bearing_type"},
            "subject_to_shear": {"const": True},
        },
        "required": ["connection_type", "subject_to_shear"],
    },
    "then": {
        "required": [
            "eccentricity_absent_verified",
            "uniform_bolt_bearing_verified",
            "slot_normal_to_action_verified",
        ]
    },
}

INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "oneOf": [
        _hole_schema("standard", {"hole_diameter_mm": POSITIVE}),
        _hole_schema(
            "base_plate_anchor",
            {
                "hole_diameter_mm": POSITIVE,
                "special_nut_washer": {"oneOf": [{"type": "null"}, _PLATE_WASHER]},
            },
            required=["hole_diameter_mm"],
        ),
        _hole_schema(
            "oversize",
            {"hole_diameter_mm": POSITIVE, **_CONNECTION_PROPERTIES},
            required=["hole_diameter_mm", *_CONNECTION_REQUIRED],
        ),
        _hole_schema(
            "short_slot",
            {
                "hole_width_mm": POSITIVE,
                "hole_length_mm": POSITIVE,
                **_CONNECTION_PROPERTIES,
                "eccentricity_absent_verified": _BOOL,
                "uniform_bolt_bearing_verified": _BOOL,
                "slot_normal_to_action_verified": _BOOL,
            },
            required=["hole_width_mm", "hole_length_mm", *_CONNECTION_REQUIRED],
            conditions=[_BEARING_SHEAR],
        ),
        _hole_schema(
            "long_slot",
            {
                "hole_width_mm": POSITIVE,
                "hole_length_mm": POSITIVE,
                **_CONNECTION_PROPERTIES,
                "alternate_plies_verified": _BOOL,
                "eccentricity_absent_verified": _BOOL,
                "uniform_bolt_bearing_verified": _BOOL,
                "slot_normal_to_action_verified": _BOOL,
            },
            required=[
                "hole_width_mm",
                "hole_length_mm",
                *_CONNECTION_REQUIRED,
                "alternate_plies_verified",
            ],
            conditions=[_BEARING_SHEAR],
        ),
    ],
}
OUTPUT_SCHEMA = {"type": "object"}


def _within_maximum(value, maximum):
    return value <= maximum + 1e-9 * max(1.0, abs(maximum))


def _washer_check(name, side, required, minimum_clearance, minimum_thickness=0, clause="14.3.2"):
    washer = side["washer"]
    if not required:
        return {"clause": clause, "check": name, "satisfied": True, "required": False}
    if washer is None:
        return {"clause": clause, "check": name, "satisfied": False, "required": True}
    kind = washer["type"]
    satisfied = washer["product_verified"]
    if minimum_thickness:
        satisfied = (
            satisfied and kind == "plate" and washer.get("thickness_mm", 0) >= minimum_thickness
        )
    if kind == "plate":
        satisfied = (
            satisfied
            and washer["coverage_geometry_verified"]
            and washer["material_as_nzs_3678_verified"]
            and _within_maximum(minimum_clearance, washer["minimum_edge_clearance_mm"])
        )
    elif minimum_thickness:
        satisfied = False
    return {
        "clause": clause,
        "check": name,
        "satisfied": bool(satisfied),
        "required": True,
        "washer_type": kind,
        "required_edge_clearance_mm": minimum_clearance if kind == "plate" else None,
        "provided_edge_clearance_mm": (
            washer["minimum_edge_clearance_mm"] if kind == "plate" else None
        ),
        "minimum_thickness_mm": minimum_thickness or None,
        "provided_thickness_mm": washer.get("thickness_mm") if kind == "plate" else None,
    }


def run_fabrication(inputs):
    """Check one declared hole against Clause 14.3.2 and its use limitations."""
    d = validate(inputs, INPUT_SCHEMA)
    bolt = d["bolt_diameter_mm"]
    hole_type = d["hole_type"]
    checks = []
    values = {"bolt_diameter_mm": bolt, "hole_type": hole_type}

    if hole_type == "standard":
        diameter = d["hole_diameter_mm"]
        limit = bolt + (2 if bolt <= 24 else 3)
        exact_small_hole = abs(diameter - limit) <= 1e-9 * max(1.0, limit)
        satisfied = (
            exact_small_hole
            if bolt <= 24
            else diameter >= bolt and _within_maximum(diameter, limit)
        )
        values.update({"hole_diameter_mm": diameter, "maximum_hole_diameter_mm": limit})
        checks.append({"clause": "14.3.2", "check": "standard_hole_size", "satisfied": satisfied})
    elif hole_type == "base_plate_anchor":
        diameter = d["hole_diameter_mm"]
        limit = bolt + 6
        washer_required = diameter >= bolt + 3 - 1e-9 * max(1.0, bolt)
        values.update(
            {
                "hole_diameter_mm": diameter,
                "maximum_hole_diameter_mm": limit,
                "special_nut_washer_required": washer_required,
            }
        )
        checks.append(
            {
                "clause": "14.3.2",
                "check": "base_plate_anchor_hole_size",
                "satisfied": diameter >= bolt and _within_maximum(diameter, limit),
            }
        )
        washer = d.get("special_nut_washer")
        if washer_required:
            checks.append(
                _washer_check(
                    "base_plate_special_nut_washer",
                    {"washer": washer},
                    True,
                    0.5 * diameter,
                    minimum_thickness=4,
                )
            )
    elif hole_type == "oversize":
        diameter = d["hole_diameter_mm"]
        limit = max(1.25 * bolt, bolt + 8)
        values.update({"hole_diameter_mm": diameter, "maximum_hole_diameter_mm": limit})
        checks.append(
            {
                "clause": "14.3.2(a)(i)",
                "check": "oversize_hole_diameter",
                "satisfied": diameter >= bolt and _within_maximum(diameter, limit),
            }
        )
        checks.append(
            {
                "clause": "14.3.2(b)(i)",
                "check": "not_a_base_plate_anchor_hole",
                "satisfied": d["not_base_plate_anchor_hole_verified"],
            }
        )
        for side_name in ("head_side", "nut_side"):
            side = d[side_name]
            checks.append(
                _washer_check(
                    f"{side_name}_washer",
                    side,
                    side["bears_on_holed_ply"],
                    0.5 * diameter,
                    clause="14.3.2(b)(i)",
                )
            )
    else:
        width = d["hole_width_mm"]
        length = d["hole_length_mm"]
        width_limit = bolt + (2 if bolt <= 24 else 3)
        length_limit = max(1.33 * bolt, bolt + 10) if hole_type == "short_slot" else 2.5 * bolt
        geometry_clause = "14.3.2(a)(ii)" if hole_type == "short_slot" else "14.3.2(a)(iii)"
        use_clause = "14.3.2(b)(ii)" if hole_type == "short_slot" else "14.3.2(b)(iii)"
        values.update(
            {
                "hole_width_mm": width,
                "hole_length_mm": length,
                "maximum_hole_width_mm": width_limit,
                "maximum_hole_length_mm": length_limit,
                "washer_minimum_edge_clearance_mm": 0.5 * width,
            }
        )
        checks.extend(
            [
                {
                    "clause": geometry_clause,
                    "check": "slot_width",
                    "satisfied": width >= bolt and _within_maximum(width, width_limit),
                },
                {
                    "clause": geometry_clause,
                    "check": "slot_length",
                    "satisfied": length >= width and _within_maximum(length, length_limit),
                },
            ]
        )
        checks.append(
            {
                "clause": use_clause,
                "check": "not_a_base_plate_anchor_hole",
                "satisfied": d["not_base_plate_anchor_hole_verified"],
            }
        )
        minimum_thickness = 8 if hole_type == "long_slot" else 0
        for side_name in ("head_side", "nut_side"):
            side = d[side_name]
            checks.append(
                _washer_check(
                    f"{side_name}_washer",
                    side,
                    side["bears_on_holed_ply"],
                    0.5 * width,
                    minimum_thickness,
                    use_clause,
                )
            )
        if hole_type == "long_slot":
            checks.append(
                {
                    "clause": use_clause,
                    "check": "alternate_plies",
                    "satisfied": d["alternate_plies_verified"],
                }
            )
        if d["connection_type"] == "bearing_type" and d["subject_to_shear"]:
            checks.extend(
                [
                    {
                        "clause": use_clause,
                        "check": "bearing_connection_not_eccentrically_loaded",
                        "satisfied": d["eccentricity_absent_verified"],
                    },
                    {
                        "clause": use_clause,
                        "check": "uniform_bolt_bearing",
                        "satisfied": d["uniform_bolt_bearing_verified"],
                    },
                    {
                        "clause": use_clause,
                        "check": "slot_normal_to_design_action",
                        "satisfied": d["slot_normal_to_action_verified"],
                    },
                ]
            )
    return result(
        "bolt_hole",
        ["14.3.2"],
        values,
        checks,
        limitations=[
            "Verify measured hole and washer dimensions, ply arrangement, washer product and "
            "connection actions from project records.",
            "Plate washer material is assessed against AS/NZS 3678; this check does not "
            "establish fabrication acceptance under Section 14.",
        ],
    )
