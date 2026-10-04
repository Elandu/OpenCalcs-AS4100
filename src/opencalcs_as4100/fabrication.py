# SPDX-License-Identifier: AGPL-3.0-only
"""AS 4100:2020 Clause 14.3.2 bolt-hole geometry and use checks."""

from .validation import POSITIVE, SIGNED, object_schema, result, validate

_NUMBER = {"type": "number", "minimum": 0, "maximum": 1e12}
_BOOL = {"type": "boolean"}
_SLOPE = {"type": "number", "minimum": 0, "maximum": 1e6}


_BOLT_ASSEMBLY = object_schema(
    {
        "check_type": {"const": "bolt_assembly"},
        "connection_type": {"enum": ["bearing_type", "friction_type"]},
        "bolts_nuts_washers_conform_clause_2_3_1_verified": _BOOL,
        "all_material_within_bolt_grip_is_steel_verified": _BOOL,
        "clear_threads_above_nut_count": {
            "type": "integer",
            "minimum": 0,
            "maximum": 1000,
        },
        "thread_plus_runout_clear_beneath_nut_verified": _BOOL,
        "rotated_part": {"enum": ["bolt_head", "nut"]},
        "washer_under_rotated_part_verified": _BOOL,
        "maximum_contact_surface_slope_ratio": _SLOPE,
        "contact_surface_slope_measurement_verified": _BOOL,
        "tapered_washer_provided": _BOOL,
        "tapered_washer_against_sloped_surface_verified": _BOOL,
        "nonrotating_part_against_tapered_washer_verified": _BOOL,
        "subject_to_vibration": _BOOL,
        "nut_secured_to_prevent_loosening_verified": _BOOL,
        "fully_tensioned_high_strength_bolt_installed_during_fabrication": _BOOL,
        "installed_in_accordance_with_clause_15_2_verified": _BOOL,
        "friction_surfaces_prepared_per_as_nzs_5131_verified": _BOOL,
        "friction_surfaces_clean_as_rolled_or_equivalent_verified": _BOOL,
        "clause_9_2_3_2_alternative_route_verified": _BOOL,
    },
    required=[
        "check_type",
        "connection_type",
        "bolts_nuts_washers_conform_clause_2_3_1_verified",
        "all_material_within_bolt_grip_is_steel_verified",
        "clear_threads_above_nut_count",
        "thread_plus_runout_clear_beneath_nut_verified",
        "rotated_part",
        "washer_under_rotated_part_verified",
        "maximum_contact_surface_slope_ratio",
        "contact_surface_slope_measurement_verified",
        "subject_to_vibration",
        "fully_tensioned_high_strength_bolt_installed_during_fabrication",
    ],
)
_BOLT_ASSEMBLY["allOf"] = [
    {
        "if": {
            "properties": {"connection_type": {"const": "friction_type"}},
            "required": ["connection_type"],
        },
        "then": {
            "required": [
                "friction_surfaces_prepared_per_as_nzs_5131_verified",
                "friction_surfaces_clean_as_rolled_or_equivalent_verified",
                "clause_9_2_3_2_alternative_route_verified",
            ]
        },
    },
    {
        "if": {
            "properties": {"subject_to_vibration": {"const": True}},
            "required": ["subject_to_vibration"],
        },
        "then": {"required": ["nut_secured_to_prevent_loosening_verified"]},
    },
    {
        "if": {
            "properties": {
                "fully_tensioned_high_strength_bolt_installed_during_fabrication": {"const": True}
            },
            "required": ["fully_tensioned_high_strength_bolt_installed_during_fabrication"],
        },
        "then": {"required": ["installed_in_accordance_with_clause_15_2_verified"]},
    },
]

_FABRICATION_BASIS = object_schema(
    {
        "check_type": {"const": "fabrication_basis"},
        "materials_conform_referenced_standards_verified": _BOOL,
        "surface_defects_removed_per_referenced_standards_verified": _BOOL,
        "steel_grade_identifiable_at_all_fabrication_stages_verified": _BOOL,
        "steel_classified_as_unidentified": _BOOL,
        "clause_2_2_3_unidentified_steel_inputs": {"type": "object"},
        "marking_does_not_damage_material_verified": _BOOL,
        "fabrication_per_as_nzs_5131_verified": _BOOL,
        "fabrication_methods_preserve_design_properties_verified": _BOOL,
    },
    required=[
        "check_type",
        "materials_conform_referenced_standards_verified",
        "surface_defects_removed_per_referenced_standards_verified",
        "steel_grade_identifiable_at_all_fabrication_stages_verified",
        "steel_classified_as_unidentified",
        "marking_does_not_damage_material_verified",
        "fabrication_per_as_nzs_5131_verified",
        "fabrication_methods_preserve_design_properties_verified",
    ],
)
_FABRICATION_BASIS["allOf"] = [
    {
        "if": {
            "properties": {"steel_classified_as_unidentified": {"const": True}},
            "required": ["steel_classified_as_unidentified"],
        },
        "then": {"required": ["clause_2_2_3_unidentified_steel_inputs"]},
    }
]

_TOLERANCE = object_schema(
    {
        "check_type": {"const": "geometric_tolerance"},
        "tolerance_type": {"enum": ["essential", "functional"]},
        "measured_deviation_mm": SIGNED,
        "permissible_deviation_mm": POSITIVE,
        "as_nzs_5131_tolerance_limit_verified": _BOOL,
        "measurement_after_fabrication_and_corrosion_protection_verified": _BOOL,
        "coating_thickness_excluded_from_measurement_verified": _BOOL,
        "functional_tolerance_class": {"enum": [1, 2]},
        "excess_deviation_in_revised_design_capacity_verified": _BOOL,
    },
    required=[
        "check_type",
        "tolerance_type",
        "measured_deviation_mm",
        "permissible_deviation_mm",
        "as_nzs_5131_tolerance_limit_verified",
        "measurement_after_fabrication_and_corrosion_protection_verified",
        "coating_thickness_excluded_from_measurement_verified",
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
        _BOLT_ASSEMBLY,
        _FABRICATION_BASIS,
        _TOLERANCE,
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


def _run_bolt_assembly(d):
    checks = [
        {
            "clause": "14.3.3.1",
            "check": "bolt_nut_washer_material_standard",
            "satisfied": d["bolts_nuts_washers_conform_clause_2_3_1_verified"],
        },
        {
            "clause": "14.3.3.1",
            "check": "steel_within_bolt_grip",
            "satisfied": d["all_material_within_bolt_grip_is_steel_verified"],
        },
        {
            "clause": "14.3.3.1",
            "check": "clear_thread_above_nut",
            "satisfied": d["clear_threads_above_nut_count"] >= 1,
            "required_clear_threads": 1,
            "provided_clear_threads": d["clear_threads_above_nut_count"],
        },
        {
            "clause": "14.3.3.1",
            "check": "thread_and_runout_clear_beneath_nut",
            "satisfied": d["thread_plus_runout_clear_beneath_nut_verified"],
        },
        {
            "clause": "14.3.3.1",
            "check": "washer_under_rotated_part",
            "satisfied": d["washer_under_rotated_part_verified"],
        },
    ]
    values = {
        "rotated_part": d["rotated_part"],
        "maximum_contact_surface_slope_ratio": d["maximum_contact_surface_slope_ratio"],
        "tapered_washer_required": d["maximum_contact_surface_slope_ratio"] > 1 / 20,
    }
    if not d["contact_surface_slope_measurement_verified"]:
        checks.append(
            {
                "clause": "14.3.3.1",
                "check": "contact_surface_slope_measurement",
                "satisfied": False,
            }
        )
    if values["tapered_washer_required"]:
        for key, label in (
            ("tapered_washer_provided", "tapered_washer_provided"),
            (
                "tapered_washer_against_sloped_surface_verified",
                "tapered_washer_against_sloped_surface",
            ),
            (
                "nonrotating_part_against_tapered_washer_verified",
                "nonrotating_part_against_tapered_washer",
            ),
        ):
            checks.append(
                {
                    "clause": "14.3.3.1",
                    "check": label,
                    "satisfied": d.get(key) is True,
                }
            )
    if d["subject_to_vibration"]:
        checks.append(
            {
                "clause": "14.3.3.1",
                "check": "nut_secured_against_vibration_looseness",
                "satisfied": d["nut_secured_to_prevent_loosening_verified"],
            }
        )

    clauses = ["14.3.3.1"]
    if d["connection_type"] == "friction_type":
        clauses.append("14.3.3.2")
        prepared = d["friction_surfaces_prepared_per_as_nzs_5131_verified"]
        clean = d["friction_surfaces_clean_as_rolled_or_equivalent_verified"]
        alternative = d["clause_9_2_3_2_alternative_route_verified"]
        checks.extend(
            [
                {
                    "clause": "14.3.3.2",
                    "check": "friction_surface_preparation_per_as_nzs_5131",
                    "satisfied": prepared,
                },
                {
                    "clause": "14.3.3.2",
                    "check": "clean_as_rolled_or_clause_9_2_3_2_route",
                    "satisfied": clean or alternative,
                },
            ]
        )
        values["clause_9_2_3_2_route_required"] = not clean
    else:
        clauses.append("14.3.3.3")
        values["applied_finish_on_bearing_connection_contact_surfaces_permitted"] = True

    if d["fully_tensioned_high_strength_bolt_installed_during_fabrication"]:
        clauses.append("14.3.3.4")
        checks.append(
            {
                "clause": "14.3.3.4",
                "check": "fully_tensioned_bolt_installed_per_clause_15_2",
                "satisfied": d["installed_in_accordance_with_clause_15_2_verified"],
            }
        )
    else:
        values["clause_15_2_installation_requirement_applicable"] = False
    return result(
        "bolt_assembly",
        clauses,
        values,
        checks,
        limitations=[
            "Material conformity, installation records, slope measurements and the cited "
            "connection assessments require independent verification.",
            "Clause 15.2 bolt-tensioning methods are represented only by a supplied evidence "
            "declaration here.",
        ],
    )


def _run_fabrication_basis(d):
    grade_identifiable = d["steel_grade_identifiable_at_all_fabrication_stages_verified"]
    unidentified_route = None
    unidentified_route_passes = False
    if d["steel_classified_as_unidentified"]:
        from .materials import run_materials

        unidentified_route = run_materials(d["clause_2_2_3_unidentified_steel_inputs"])
        unidentified_route_passes = (
            unidentified_route["clauses"] == ["2.2.3"]
            and unidentified_route["checked_conditions_satisfied"]
        )
    checks = [
        {
            "clause": "14.2.1",
            "check": "materials_conform_referenced_standards",
            "satisfied": d["materials_conform_referenced_standards_verified"],
        },
        {
            "clause": "14.2.1",
            "check": "surface_defects_removed_per_referenced_standards",
            "satisfied": d["surface_defects_removed_per_referenced_standards_verified"],
        },
        {
            "clause": "14.2.2",
            "check": "grade_identifiable_or_clause_2_2_3_unidentified_steel_route",
            "satisfied": grade_identifiable or unidentified_route_passes,
        },
        {
            "clause": "14.2.2",
            "check": "marking_does_not_damage_material",
            "satisfied": d["marking_does_not_damage_material_verified"],
        },
        {
            "clause": "14.3.1",
            "check": "fabrication_per_as_nzs_5131",
            "satisfied": d["fabrication_per_as_nzs_5131_verified"],
        },
        {
            "clause": "14.3.1",
            "check": "fabrication_methods_preserve_design_properties",
            "satisfied": d["fabrication_methods_preserve_design_properties_verified"],
        },
    ]
    values = {
        "steel_grade_identifiable_at_all_fabrication_stages": grade_identifiable,
        "unidentified_steel_route_used": bool(d["steel_classified_as_unidentified"]),
    }
    clauses = ["14.2.1", "14.2.2", "14.3.1"]
    if unidentified_route is not None:
        clauses.insert(0, "2.2.3")
        values["clause_2_2_3_result"] = unidentified_route
    return result(
        "fabrication_basis",
        clauses,
        values,
        checks,
        limitations=[
            "Identification, marking, fabrication procedure and material-property preservation "
            "declarations require supporting project records.",
            "The Clause 2.2.3 route uses its bounded calculation; product conformity and test "
            "evidence remain externally assessed.",
        ],
    )


def _run_geometric_tolerance(d):
    deviation = abs(d["measured_deviation_mm"])
    limit = d["permissible_deviation_mm"]
    within_limit = _within_maximum(deviation, limit)
    essential = d["tolerance_type"] == "essential"
    revised_route = d.get("excess_deviation_in_revised_design_capacity_verified", False)
    accepted_route = within_limit or (essential and revised_route)
    tolerance_class = d.get("functional_tolerance_class", 1) if not essential else None
    checks = [
        {
            "clause": "14.4.1",
            "check": "as_nzs_5131_tolerance_limit_source",
            "satisfied": d["as_nzs_5131_tolerance_limit_verified"],
        },
        {
            "clause": "14.4.1",
            "check": "measured_after_fabrication_and_corrosion_protection",
            "satisfied": d["measurement_after_fabrication_and_corrosion_protection_verified"],
        },
        {
            "clause": "14.4.1",
            "check": "coating_thickness_excluded_from_measurement",
            "satisfied": d["coating_thickness_excluded_from_measurement_verified"],
        },
        {
            "clause": "14.4.2",
            "check": "deviation_within_permissible_value_or_essential_revised_design_route",
            "satisfied": accepted_route,
            "measured_absolute_deviation_mm": deviation,
            "permissible_deviation_mm": limit,
            "revised_design_route_required": essential and not within_limit,
            "revised_design_route_verified": revised_route
            if essential and not within_limit
            else None,
        },
    ]
    values = {
        "tolerance_type": d["tolerance_type"],
        "functional_tolerance_class_applied": tolerance_class,
        "measured_deviation_mm": d["measured_deviation_mm"],
        "permissible_deviation_mm": limit,
        "within_permissible_value": within_limit,
    }
    return result(
        "geometric_tolerance",
        ["14.4.1", "14.4.2"],
        values,
        checks,
        limitations=[
            "Permissible tolerance values must be taken from AS/NZS 5131 for the applicable "
            "feature and class.",
            "An essential-tolerance revised-capacity route requires an engineering calculation "
            "and approval; this operation checks only the declared route evidence.",
        ],
    )


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
    if d["check_type"] == "bolt_assembly":
        return _run_bolt_assembly(d)
    if d["check_type"] == "fabrication_basis":
        return _run_fabrication_basis(d)
    if d["check_type"] == "geometric_tolerance":
        return _run_geometric_tolerance(d)
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
