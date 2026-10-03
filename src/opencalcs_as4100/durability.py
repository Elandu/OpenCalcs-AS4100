"""AS 4100:2020 sections 10–13 bounded durability and fire operations."""

from collections.abc import Mapping
from math import copysign, fsum, isfinite, log, sqrt

from jsonschema import Draft202012Validator, ValidationError

from .standards import ELASTIC_MODULUS_MPA, POISSON_RATIO
from .validation import validate_standard_strengths


def _number(low=0, high=1e12, exclusive=False):
    return {"type": "number", "exclusiveMinimum" if exclusive else "minimum": low, "maximum": high}


def _operation(name, properties, required=None):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"check_type": {"const": name}, **properties},
        "required": ["check_type", *(required if required is not None else properties)],
    }


_BOOL = {"type": "boolean"}
_POS = _number(exclusive=True)
_FATIGUE = {
    "stress_type": {"enum": ["normal", "shear"]},
    "detail_category_mpa": _POS,
    "plate_thickness_mm": _POS,
    "transverse_weld": _BOOL,
    "capacity_factor": _number(0, 1, True),
    "redundant_load_path": _BOOL,
    "reference_conditions_satisfied": _BOOL,
    "yield_strength_mpa": _POS,
    "maximum_stress_magnitude_mpa": _number(),
    "punched_holes": _BOOL,
}
_EVENT = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"stress_range_mpa": _number(), "cycles": _number()},
    "required": ["stress_range_mpa", "cycles"],
}


def _fire_protected_regression_operation():
    schema = _operation(
        "fire_protected_regression",
        {
            "coefficients": {
                "type": "array",
                "minItems": 7,
                "maxItems": 7,
                "items": _number(-1e100, 1e100),
            },
            "temperature_c": _number(250, 1000, True),
            "protection_thickness_mm": _POS,
            "surface_mass_ratio_m2_per_tonne": _POS,
            "required_frl_min": _number(),
            "test_count": {"type": "integer", "minimum": 9},
            "test_series_conditions_satisfied": {"const": True},
            "inside_reviewed_interpolation_window": _BOOL,
            "application_conditions": _fire_regression_application_schema(),
            "test_temperature_range_c": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": _number(250, 1000, True),
            },
            "interpolation_window_points": {
                "type": "array",
                "minItems": 3,
                "maxItems": 1000,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "protection_thickness_mm": _POS,
                        "surface_mass_ratio_m2_per_tonne": _POS,
                    },
                    "required": [
                        "protection_thickness_mm",
                        "surface_mass_ratio_m2_per_tonne",
                    ],
                },
            },
        },
        required=[
            "coefficients",
            "temperature_c",
            "protection_thickness_mm",
            "surface_mass_ratio_m2_per_tonne",
            "required_frl_min",
            "test_count",
            "test_series_conditions_satisfied",
        ],
    )
    schema["anyOf"] = [
        {"required": ["inside_reviewed_interpolation_window"]},
        {"required": ["interpolation_window_points"]},
    ]
    schema["allOf"] = [
        {
            "if": {"required": ["interpolation_window_points"]},
            "then": {"required": ["test_temperature_range_c", "application_conditions"]},
        }
    ]
    return schema


def _fire_three_sided_group_members_schema():
    return {
        "type": "array",
        "minItems": 1,
        "maxItems": 1000,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "concrete_density_kg_m3": _POS,
                "concrete_area_excluding_voids_mm2": _POS,
                "tributary_width_mm": _POS,
                "rib_void_condition": {"enum": ["none", "open", "blocked"]},
            },
            "required": [
                "concrete_density_kg_m3",
                "concrete_area_excluding_voids_mm2",
                "tributary_width_mm",
                "rib_void_condition",
            ],
        },
    }


def _fire_three_sided_group_operation():
    return _operation(
        "fire_three_sided_group",
        {"members": _fire_three_sided_group_members_schema()},
    )


def _fire_regression_application_schema():
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "calibration_exposure_sides": {"enum": [3, 4]},
            "member_exposure_sides": {"enum": [3, 4]},
            "same_protection_system": _BOOL,
            "same_protection_material_verified": {"const": True},
            "stickability_demonstrated_for_member": _BOOL,
            "member_three_sided_grouping_verified": _BOOL,
            "member_three_sided_group_members": _fire_three_sided_group_members_schema(),
        },
        "required": [
            "calibration_exposure_sides",
            "member_exposure_sides",
            "same_protection_system",
            "same_protection_material_verified",
            "stickability_demonstrated_for_member",
        ],
        "allOf": [
            {
                "if": {
                    "properties": {"member_exposure_sides": {"const": 3}},
                    "required": ["member_exposure_sides"],
                },
                "then": {
                    "anyOf": [
                        {
                            "required": ["member_three_sided_grouping_verified"],
                            "properties": {"member_three_sided_grouping_verified": {"const": True}},
                        },
                        {"required": ["member_three_sided_group_members"]},
                    ]
                },
            }
        ],
    }


def _fire_protected_regression_fit_operation():
    schema = _operation(
        "fire_protected_regression_fit",
        {
            "protection_material_type": {
                "enum": ["low_density_insulation", "intumescent_or_ablative_coating"]
            },
            "protection_dry_density_kg_m3": _POS,
            "same_protection_system_and_exposure_verified": {"const": True},
            "exposure_sides": {"enum": [3, 4]},
            "three_sided_grouping_verified": _BOOL,
            "three_sided_group_members": _fire_three_sided_group_members_schema(),
            "test_series": {
                "type": "array",
                "minItems": 9,
                "maxItems": 100,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "protection_thickness_mm": _POS,
                        "surface_mass_ratio_m2_per_tonne": _POS,
                        "prototype_was_unloaded": _BOOL,
                        "stickability_demonstrated": _BOOL,
                        "temperature_time_points": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 300,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "temperature_c": _number(250, 1000, True),
                                    "time_min": _number(),
                                },
                                "required": ["temperature_c", "time_min"],
                            },
                        },
                    },
                    "required": [
                        "protection_thickness_mm",
                        "surface_mass_ratio_m2_per_tonne",
                        "prototype_was_unloaded",
                        "stickability_demonstrated",
                        "temperature_time_points",
                    ],
                },
            },
        },
        required=[
            "protection_material_type",
            "same_protection_system_and_exposure_verified",
            "exposure_sides",
            "test_series",
        ],
    )
    schema["allOf"] = [
        {
            "if": {
                "properties": {"protection_material_type": {"const": "low_density_insulation"}},
                "required": ["protection_material_type"],
            },
            "then": {
                "required": ["protection_dry_density_kg_m3"],
                "properties": {"protection_dry_density_kg_m3": _number(0, 1000, True)},
            },
        },
        {
            "if": {
                "properties": {"exposure_sides": {"const": 3}},
                "required": ["exposure_sides"],
            },
            "then": {
                "anyOf": [
                    {
                        "required": ["three_sided_grouping_verified"],
                        "properties": {"three_sided_grouping_verified": {"const": True}},
                    },
                    {"required": ["three_sided_group_members"]},
                ],
            },
        },
    ]
    return schema


_STEEL_TYPES = ["1", "2", "2S", "3", "4", "5", "5S", "6", "7A", "7B", "7C", "8C", "8Q", "9Q", "10Q"]
_SEISMIC = {
    "special_moment": (4, 0.67),
    "intermediate_moment": (3, 0.67),
    "ordinary_moment": (2, 0.77),
    "moderate_concentric": (3, 0.67),
    "limited_concentric": (2, 0.77),
    "eccentric": (4, 0.67),
    "other": (2, 0.77),
}
INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "oneOf": [
        _operation(
            "fatigue_constant",
            {**_FATIGUE, "stress_range_mpa": _number(), "cycles": _number(0, 1e8, True)},
        ),
        _operation(
            "fatigue_variable",
            {
                **_FATIGUE,
                "events": {"type": "array", "minItems": 1, "maxItems": 10000, "items": _EVENT},
            },
        ),
        _operation(
            "fatigue_exemption",
            {
                "normal_stress_range_mpa": _number(),
                "shear_stress_range_mpa": _number(),
                "cycles": _number(),
                "capacity_factor": _number(0, 1, True),
                "redundant_load_path": _BOOL,
                "reference_conditions_satisfied": _BOOL,
            },
        ),
        _operation(
            "fire_material",
            {
                "temperature_c": _number(0, 905, True),
                "yield_strength_20_mpa": _POS,
                "elastic_modulus_20_mpa": {"const": ELASTIC_MODULUS_MPA},
                "poisson_ratio": {"const": POISSON_RATIO},
            },
        ),
        _operation(
            "fire_modulus",
            {
                "temperature_c": _number(0, 1000, True),
                "elastic_modulus_20_mpa": {"const": ELASTIC_MODULUS_MPA},
                "poisson_ratio": {"const": POISSON_RATIO},
            },
        ),
        _operation("fire_limiting_temperature", {"fire_action_ratio": _number(0, 1)}),
        _operation(
            "fire_unprotected",
            {
                "limiting_temperature_c": _number(20, 750),
                "surface_mass_ratio_m2_per_tonne": _number(2, 35),
                "exposure_sides": {"enum": [3, 4]},
                "required_frl_min": _number(),
            },
        ),
        _operation(
            "fire_single_test",
            {
                "prototype_psa_min": _POS,
                "required_frl_min": _number(),
                "protection_thickness_mm": _number(),
                "prototype_protection_thickness_mm": _number(),
                "surface_mass_ratio_m2_per_tonne": _POS,
                "prototype_surface_mass_ratio_m2_per_tonne": _POS,
                "fire_action_ratio": _number(0, 1),
                "prototype_fire_action_ratio": _number(0, 1),
                "same_protection_system": _BOOL,
                "same_exposure": _BOOL,
                "same_supports": _BOOL,
                "restraints_not_less_favourable": _BOOL,
            },
        ),
        _operation(
            "fire_single_test_history",
            {
                "limiting_temperature_c": _number(215, 905),
                "required_frl_min": _number(),
                "protection_thickness_mm": _POS,
                "prototype_protection_thickness_mm": _POS,
                "surface_mass_ratio_m2_per_tonne": _POS,
                "prototype_surface_mass_ratio_m2_per_tonne": _POS,
                "same_protection_system": _BOOL,
                "same_exposure_condition": _BOOL,
                "prototype_was_unloaded": _BOOL,
                "stickability_demonstrated": _BOOL,
                "temperature_history": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 10000,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "time_min": _number(0, 1e7),
                            "steel_temperature_c": _number(20, 1200),
                        },
                        "required": ["time_min", "steel_temperature_c"],
                    },
                },
            },
        ),
        _operation(
            "web_penetration_protection",
            {
                "required_thickness_above_mm": _POS,
                "required_thickness_below_mm": _POS,
                "required_thickness_whole_section_mm": _POS,
                "provided_thickness_mm": _POS,
                "beam_depth_mm": _POS,
                "protected_depth_mm": _POS,
                "left_extension_mm": _number(),
                "right_extension_mm": _number(),
            },
        ),
        _operation(
            "fire_connection_protection",
            {
                "framing_members": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 1000,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {"required_protection_thickness_mm": _POS},
                        "required": ["required_protection_thickness_mm"],
                    },
                },
                "connection_components": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 10000,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "component_id": {"type": "string", "minLength": 1, "maxLength": 100},
                            "component_type": {
                                "enum": ["bolt_head", "weld", "splice_plate", "other"]
                            },
                            "provided_protection_thickness_mm": _number(),
                            "protection_maintained_over_component": _BOOL,
                        },
                        "required": [
                            "component_id",
                            "component_type",
                            "provided_protection_thickness_mm",
                            "protection_maintained_over_component",
                        ],
                    },
                },
            },
        ),
        _operation(
            "concentric_tension_brace",
            {
                "bearing_wall_or_building_frame_system_verified": {"const": True},
                "design_tension_action_kn": _number(),
                "member_design_tensile_capacity_kn": _POS,
                "connection_design_tensile_capacity_kn": _POS,
            },
        ),
        _fire_protected_regression_fit_operation(),
        _fire_three_sided_group_operation(),
        _fire_protected_regression_operation(),
        _operation(
            "brittle_fracture",
            {
                "steel_type": {"enum": _STEEL_TYPES},
                "thickness_mm": _POS,
                "design_service_temperature_c": _number(-273, 1000),
                "outer_fibre_strain_percent": _number(0, 100),
                "post_weld_heat_treatment_c": _number(0, 2000),
                "impact_test_temperature_c": _number(-273, 1000),
                "fabrication_erection_requirements_satisfied": _BOOL,
            },
        ),
        _operation(
            "earthquake_audit",
            {
                "structural_system": {"enum": list(_SEISMIC)},
                "grade_minimum_yield_mpa": _POS,
                "design_storey_deflection_mm": _number(),
            },
        ),
    ],
}
OUTPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["check_type", "standard", "clauses", "results", "warnings"],
    "additionalProperties": False,
    "properties": {
        "check_type": {"type": "string"},
        "standard": {"const": "AS 4100:2020"},
        "clauses": {"type": "array", "items": {"type": "string"}},
        "results": {"type": "object"},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}


def _result_schema(properties, optional=()):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": [key for key in properties if key not in optional],
    }


_NUM = {"type": "number", "minimum": 0}
_FATIGUE_RESULTS = {
    key: _NUM
    for key in [
        "thickness_factor",
        "corrected_reference_strength_mpa",
        "corrected_cutoff_strength_mpa",
        "corrected_constant_amplitude_limit_mpa",
    ]
}
_FATIGUE_RESULTS["punching_limit_satisfied"] = _BOOL
_RESULT_SCHEMAS = {
    "fatigue_constant": _result_schema(
        {
            **_FATIGUE_RESULTS,
            "design_fatigue_strength_mpa": _NUM,
            "utilisation": _NUM,
            "check_satisfied": _BOOL,
            "further_assessment_exempt": _BOOL,
        },
        ["corrected_constant_amplitude_limit_mpa"],
    ),
    "fatigue_variable": _result_schema(
        {
            **_FATIGUE_RESULTS,
            "damage": _NUM,
            "event_damage": {"type": "array", "items": _NUM},
            "check_satisfied": _BOOL,
            "further_assessment_exempt": _BOOL,
        },
        ["corrected_constant_amplitude_limit_mpa"],
    ),
    "fatigue_exemption": _result_schema({"assessment_exempt": _BOOL}),
    "fire_material": _result_schema(
        {
            key: _NUM
            for key in [
                "yield_ratio",
                "elastic_ratio",
                "yield_strength_mpa",
                "elastic_modulus_mpa",
                "shear_modulus_mpa",
            ]
        }
    ),
    "fire_modulus": _result_schema(
        {key: _NUM for key in ["elastic_ratio", "elastic_modulus_mpa", "shear_modulus_mpa"]}
    ),
    "fire_limiting_temperature": _result_schema({"limiting_temperature_c": _NUM}),
    "fire_unprotected": _result_schema({"psa_min": _NUM, "check_satisfied": _BOOL}),
    "fire_three_sided_group": _result_schema(
        {
            "concrete_density_ratio": _POS,
            "effective_thickness_ratio": _POS,
            "effective_thicknesses_mm": {"type": "array", "minItems": 1, "items": _POS},
            "rib_voids_state": {"enum": ["none", "open", "blocked", "mixed"]},
            "concrete_density_satisfied": _BOOL,
            "effective_thickness_satisfied": _BOOL,
            "rib_voids_consistent": _BOOL,
            "group_satisfied": _BOOL,
        }
    ),
    "fire_protected_regression_fit": _result_schema(
        {
            "coefficients": {
                "type": "array",
                "minItems": 7,
                "maxItems": 7,
                "items": _number(-1e100, 1e100),
            },
            "protection_material_type": {
                "enum": ["low_density_insulation", "intumescent_or_ablative_coating"]
            },
            "exposure_sides": {"enum": [3, 4]},
            "correlation_coefficient": _number(-1, 1),
            "root_mean_square_residual_min": _NUM,
            "test_count": {"type": "integer", "minimum": 9},
            "observation_count": {"type": "integer", "minimum": 9},
            "test_temperature_range_c": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": _number(250, 1000, True),
            },
            "interpolation_window_points": {
                "type": "array",
                "minItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "protection_thickness_mm": _POS,
                        "surface_mass_ratio_m2_per_tonne": _POS,
                    },
                    "required": [
                        "protection_thickness_mm",
                        "surface_mass_ratio_m2_per_tonne",
                    ],
                },
            },
            "calibration_eligible": _BOOL,
            "three_sided_group_qualification": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "concrete_density_ratio": _POS,
                    "effective_thickness_ratio": _POS,
                    "effective_thicknesses_mm": {
                        "type": "array",
                        "minItems": 1,
                        "items": _POS,
                    },
                    "rib_voids_state": {"enum": ["none", "open", "blocked", "mixed"]},
                    "concrete_density_satisfied": _BOOL,
                    "effective_thickness_satisfied": _BOOL,
                    "rib_voids_consistent": _BOOL,
                    "group_satisfied": _BOOL,
                },
                "required": [
                    "concrete_density_ratio",
                    "effective_thickness_ratio",
                    "effective_thicknesses_mm",
                    "rib_voids_state",
                    "concrete_density_satisfied",
                    "effective_thickness_satisfied",
                    "rib_voids_consistent",
                    "group_satisfied",
                ],
            },
        },
        optional=["three_sided_group_qualification"],
    ),
    "fire_protected_regression": _result_schema(
        {
            "psa_min": _NUM,
            "check_satisfied": _BOOL,
            "inside_interpolation_window": _BOOL,
            "within_test_temperature_range": _BOOL,
            "application_conditions": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "calibration_exposure_sides": {"enum": [3, 4]},
                    "member_exposure_sides": {"enum": [3, 4]},
                    "same_protection_system": _BOOL,
                    "same_protection_material_verified": _BOOL,
                    "stickability_demonstrated_for_member": _BOOL,
                    "member_three_sided_group_satisfied": {"type": ["boolean", "null"]},
                    "conditions_satisfied": _BOOL,
                },
                "required": [
                    "calibration_exposure_sides",
                    "member_exposure_sides",
                    "same_protection_system",
                    "same_protection_material_verified",
                    "stickability_demonstrated_for_member",
                    "member_three_sided_group_satisfied",
                    "conditions_satisfied",
                ],
            },
            "interpolation_window_points": {
                "type": "array",
                "minItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "protection_thickness_mm": _POS,
                        "surface_mass_ratio_m2_per_tonne": _POS,
                    },
                    "required": [
                        "protection_thickness_mm",
                        "surface_mass_ratio_m2_per_tonne",
                    ],
                },
            },
            "test_temperature_range_c": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": _number(250, 1000, True),
            },
        },
        optional=[
            "within_test_temperature_range",
            "application_conditions",
            "interpolation_window_points",
            "test_temperature_range_c",
        ],
    ),
    "fire_single_test": _result_schema(
        {"test_applicable": _BOOL, "prototype_psa_min": _NUM, "check_satisfied": _BOOL}
    ),
    "fire_single_test_history": _result_schema(
        {
            "test_applicable": _BOOL,
            "limiting_temperature_attained": _BOOL,
            "attained_time_min": {"type": ["number", "null"], "minimum": 0},
            "psa_min_lower_bound": _NUM,
            "check_satisfied": _BOOL,
        }
    ),
    "web_penetration_protection": _result_schema(
        {
            "required_thickness_mm": _NUM,
            "provided_thickness_mm": _NUM,
            "minimum_extension_each_side_mm": _NUM,
            "provided_left_extension_mm": _NUM,
            "provided_right_extension_mm": _NUM,
            "thickness_satisfied": _BOOL,
            "full_depth_satisfied": _BOOL,
            "left_extension_satisfied": _BOOL,
            "right_extension_satisfied": _BOOL,
            "check_satisfied": _BOOL,
        }
    ),
    "fire_connection_protection": _result_schema(
        {
            "required_protection_thickness_mm": _NUM,
            "framing_member_count": {"type": "integer", "minimum": 1},
            "component_checks": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "component_id": {"type": "string", "minLength": 1},
                        "component_type": {"enum": ["bolt_head", "weld", "splice_plate", "other"]},
                        "required_protection_thickness_mm": _NUM,
                        "provided_protection_thickness_mm": _NUM,
                        "thickness_satisfied": _BOOL,
                        "protection_maintained_over_component": _BOOL,
                        "component_satisfied": _BOOL,
                    },
                    "required": [
                        "component_id",
                        "component_type",
                        "required_protection_thickness_mm",
                        "provided_protection_thickness_mm",
                        "thickness_satisfied",
                        "protection_maintained_over_component",
                        "component_satisfied",
                    ],
                },
            },
            "check_satisfied": _BOOL,
        }
    ),
    "concentric_tension_brace": _result_schema(
        {
            "member_action_limit_kn": _NUM,
            "design_tension_action_kn": _NUM,
            "member_action_satisfied": _BOOL,
            "connection_required_capacity_kn": _NUM,
            "connection_design_tensile_capacity_kn": _NUM,
            "connection_capacity_satisfied": _BOOL,
            "check_satisfied": _BOOL,
        }
    ),
    "brittle_fracture": _result_schema(
        {
            "permissible_service_temperature_c": {"type": "number"},
            "strain_temperature_increase_c": _NUM,
            "check_satisfied": _BOOL,
        }
    ),
    "earthquake_audit": _result_schema(
        {
            "ductility_factor": _NUM,
            "structural_performance_factor": _NUM,
            "minimum_panel_movement_mm": _NUM,
            "yield_limit_satisfied": {"type": ["boolean", "null"]},
            "manual_review_required": _BOOL,
        }
    ),
}
OUTPUT_SCHEMA["properties"]["check_type"] = {"enum": list(_RESULT_SCHEMAS)}
OUTPUT_SCHEMA["allOf"] = [
    {
        "if": {"properties": {"check_type": {"const": operation}}},
        "then": {"properties": {"results": schema}},
    }
    for operation, schema in _RESULT_SCHEMAS.items()
]


def _finite(value):
    if isinstance(value, Mapping):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return not isinstance(value, float) or isfinite(value)


def _phi(d):
    phi = d["capacity_factor"]
    if not d["redundant_load_path"] and phi > 0.70:
        raise ValueError("Non-redundant fatigue load paths require capacity factor <= 0.70.")
    if not d["reference_conditions_satisfied"] and phi >= 1:
        raise ValueError("Non-reference fatigue conditions require a reduced capacity factor.")
    return phi


def _fatigue(d):
    phi = _phi(d)
    normal_categories = {36, 40, 41, 45, 50, 56, 63, 71, 80, 90, 100, 112, 125, 140, 160, 180}
    categories = {80, 100} if d["stress_type"] == "shear" else normal_categories
    if d["detail_category_mpa"] not in categories:
        raise ValueError("Detail category is outside the supported fatigue curves.")
    beta = (
        (25 / d["plate_thickness_mm"]) ** 0.25
        if (d["transverse_weld"] and d["plate_thickness_mm"] > 25)
        else 1.0
    )
    reference = beta * d["detail_category_mpa"]
    shear = d["stress_type"] == "shear"
    f3 = reference * (2 / 5) ** (1 / 3) if not shear else None
    f5 = reference * (2 / 100) ** 0.2 if shear else f3 * (5 / 100) ** 0.2
    events = (
        d["events"]
        if d["check_type"] == "fatigue_variable"
        else [{"stress_range_mpa": d["stress_range_mpa"], "cycles": d["cycles"]}]
    )
    peak = max(e["stress_range_mpa"] for e in events)
    if peak > 2 * d["maximum_stress_magnitude_mpa"]:
        raise ValueError("Stress range is incompatible with the declared maximum stress magnitude.")
    if d["maximum_stress_magnitude_mpa"] > d["yield_strength_mpa"]:
        raise ValueError("Fatigue stress magnitude exceeds the clause 11.1.3 yield limit.")
    if peak > 1.5 * d["yield_strength_mpa"]:
        raise ValueError("Fatigue stress range exceeds 1.5 times yield strength.")
    warnings = [
        "Detail category, stress concentrations, weld quality and service spectrum need review.",
        "Corrosion, immersion, low-cycle, thermal fatigue and stress corrosion are excluded.",
    ]
    punched_ok = not d["punched_holes"] or d["plate_thickness_mm"] <= 12
    base = {
        "thickness_factor": beta,
        "corrected_reference_strength_mpa": reference,
        "corrected_cutoff_strength_mpa": f5,
        "punching_limit_satisfied": punched_ok,
    }
    if not shear:
        base["corrected_constant_amplitude_limit_mpa"] = f3
    if d["check_type"] == "fatigue_constant":
        n = d["cycles"]
        strength = (
            reference * (2e6 / n) ** (0.2 if shear else 1 / 3)
            if (shear or n <= 5e6)
            else f3 * (5e6 / n) ** 0.2
        )
        design = phi * strength
        base.update(
            design_fatigue_strength_mpa=design,
            utilisation=peak / design,
            check_satisfied=(peak <= design or (not shear and peak < phi * f3)) and punched_ok,
            further_assessment_exempt=(not shear and peak < phi * f3),
        )
    else:
        damages = []
        for e in events:
            stress, n = e["stress_range_mpa"], e["cycles"]
            if stress < phi * f5:
                damage = 0.0
            elif shear:
                damage = n / 2e6 * (stress / (phi * reference)) ** 5
            elif stress >= phi * f3:
                damage = n / 5e6 * (stress / (phi * f3)) ** 3
            else:
                damage = n / 5e6 * (stress / (phi * f3)) ** 5
            damages.append(damage)
        damage = sum(damages)
        exempt = not shear and peak < phi * f3
        base.update(
            damage=damage,
            event_damage=damages,
            further_assessment_exempt=exempt,
            check_satisfied=(damage <= 1 or exempt) and punched_ok,
        )
    return base, ["11.1.3", "11.1.5", "11.1.6", "11.6", "11.7", "11.8", "11.9"], warnings


_TEMPERATURES = {
    "1": [-20, -10, 0, 0, 0, 5],
    "2": [-30, -20, -10, -10, 0, 0],
    "2S": [0] * 6,
    "3": [-40, -30, -20, -15, -15, 10],
    "4": [-10, 0, 0, 0, 0, 5],
    "5": [-30, -20, -10, 0, 0, 0],
    "5S": [0] * 6,
    "6": [-40, -30, -20, -15, -15, -10],
    "7A": [-10, 0, 0, 0, 0, None],
    "7B": [-30, -20, -10, 0, 0, None],
    "7C": [-40, -30, -20, -15, -15, None],
    "8C": [-40, -30, None, None, None, None],
    "8Q": [-20] * 6,
    "9Q": [-20] * 6,
    "10Q": [-20] * 6,
}


def _fire_regression_features(thickness, temperature, surface_mass_ratio):
    return [
        1.0,
        thickness,
        thickness / surface_mass_ratio,
        temperature,
        thickness * temperature,
        thickness * temperature / surface_mass_ratio,
        temperature / surface_mass_ratio,
    ]


def _fire_interpolation_hull(points):
    coordinates = sorted(
        {
            (
                point["surface_mass_ratio_m2_per_tonne"],
                point["protection_thickness_mm"],
            )
            for point in points
        }
    )
    if len(coordinates) < 3:
        raise ValueError("The interpolation window needs at least three distinct test geometries.")

    def cross(origin, first, second):
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (first[1] - origin[1]) * (
            second[0] - origin[0]
        )

    lower = []
    for point in coordinates:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(coordinates):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        raise ValueError("The interpolation window test geometries are collinear.")
    return [
        {
            "protection_thickness_mm": thickness,
            "surface_mass_ratio_m2_per_tonne": surface_mass_ratio,
        }
        for surface_mass_ratio, thickness in hull
    ]


def _qualify_fire_three_sided_group(members):
    densities = [member["concrete_density_kg_m3"] for member in members]
    effective_thicknesses = [
        member["concrete_area_excluding_voids_mm2"] / member["tributary_width_mm"]
        for member in members
    ]
    density_ratio = max(densities) / min(densities)
    thickness_ratio = max(effective_thicknesses) / min(effective_thicknesses)
    rib_void_states = {member["rib_void_condition"] for member in members}
    rib_voids_state = next(iter(rib_void_states)) if len(rib_void_states) == 1 else "mixed"
    density_satisfied = density_ratio <= 1.25
    thickness_satisfied = thickness_ratio <= 1.25
    voids_consistent = len(rib_void_states) == 1
    return {
        "concrete_density_ratio": density_ratio,
        "effective_thickness_ratio": thickness_ratio,
        "effective_thicknesses_mm": effective_thicknesses,
        "rib_voids_state": rib_voids_state,
        "concrete_density_satisfied": density_satisfied,
        "effective_thickness_satisfied": thickness_satisfied,
        "rib_voids_consistent": voids_consistent,
        "group_satisfied": density_satisfied and thickness_satisfied and voids_consistent,
    }


def _check_fire_regression_application_conditions(conditions):
    calibration_sides = conditions["calibration_exposure_sides"]
    member_sides = conditions["member_exposure_sides"]
    same_system = conditions["same_protection_system"]
    stickability = conditions["stickability_demonstrated_for_member"]
    if calibration_sides == 3 and member_sides == 4:
        raise ValueError("A three-sided regression series cannot qualify a four-sided member.")
    if calibration_sides != member_sides and not (calibration_sides == 4 and member_sides == 3):
        raise ValueError("The member fire exposure is outside the regression series conditions.")
    if calibration_sides == 4 and member_sides == 3 and not stickability:
        raise ValueError(
            "Applying a four-sided regression series to a three-sided member requires "
            "demonstrated stickability."
        )
    if not same_system and not stickability:
        raise ValueError(
            "Applying regression to another protection system requires demonstrated stickability."
        )

    member_group_satisfied = None
    if member_sides == 3:
        group_members = conditions.get("member_three_sided_group_members")
        if group_members is not None:
            group = _qualify_fire_three_sided_group(group_members)
            if not group["group_satisfied"]:
                raise ValueError("The three-sided member group does not satisfy Clause 12.9.")
            if conditions.get("member_three_sided_grouping_verified") is False:
                raise ValueError("Declared Clause 12.9 status conflicts with measured group data.")
        elif not conditions.get("member_three_sided_grouping_verified", False):
            raise ValueError("Three-sided members require a verified Clause 12.9 group.")
        member_group_satisfied = True

    return {
        "calibration_exposure_sides": calibration_sides,
        "member_exposure_sides": member_sides,
        "same_protection_system": same_system,
        "same_protection_material_verified": True,
        "stickability_demonstrated_for_member": stickability,
        "member_three_sided_group_satisfied": member_group_satisfied,
        "conditions_satisfied": True,
    }


def _fire_connection_protection(d):
    required_thickness = max(
        member["required_protection_thickness_mm"] for member in d["framing_members"]
    )
    seen_component_ids = set()
    component_checks = []
    for component in d["connection_components"]:
        component_id = component["component_id"]
        if component_id in seen_component_ids:
            raise ValueError("Connection component identifiers must be unique.")
        seen_component_ids.add(component_id)
        thickness_satisfied = component["provided_protection_thickness_mm"] >= required_thickness
        component_satisfied = (
            thickness_satisfied and component["protection_maintained_over_component"]
        )
        component_checks.append(
            {
                "component_id": component_id,
                "component_type": component["component_type"],
                "required_protection_thickness_mm": required_thickness,
                "provided_protection_thickness_mm": component["provided_protection_thickness_mm"],
                "thickness_satisfied": thickness_satisfied,
                "protection_maintained_over_component": component[
                    "protection_maintained_over_component"
                ],
                "component_satisfied": component_satisfied,
            }
        )
    return {
        "required_protection_thickness_mm": required_thickness,
        "framing_member_count": len(d["framing_members"]),
        "component_checks": component_checks,
        "check_satisfied": all(check["component_satisfied"] for check in component_checks),
    }


def _inside_fire_interpolation_hull(thickness, surface_mass_ratio, hull):
    coordinates = [
        (
            point["surface_mass_ratio_m2_per_tonne"],
            point["protection_thickness_mm"],
        )
        for point in hull
    ]
    min_x = min(point[0] for point in coordinates)
    max_x = max(point[0] for point in coordinates)
    min_y = min(point[1] for point in coordinates)
    max_y = max(point[1] for point in coordinates)
    if max_x == min_x or max_y == min_y:
        return False
    point_x = (surface_mass_ratio - min_x) / (max_x - min_x)
    point_y = (thickness - min_y) / (max_y - min_y)
    if not (-1e-12 <= point_x <= 1 + 1e-12 and -1e-12 <= point_y <= 1 + 1e-12):
        return False
    normalized = [
        ((x - min_x) / (max_x - min_x), (y - min_y) / (max_y - min_y)) for x, y in coordinates
    ]
    for index, origin in enumerate(normalized):
        following = normalized[(index + 1) % len(normalized)]
        cross = (following[0] - origin[0]) * (point_y - origin[1]) - (following[1] - origin[1]) * (
            point_x - origin[0]
        )
        if cross < -1e-12:
            return False
    return True


def _least_squares_fire_coefficients(matrix, observations):
    column_count = 7
    row_count = len(matrix)
    if row_count < column_count or any(len(row) != column_count for row in matrix):
        raise ValueError("At least seven complete fire-test observations are required.")
    scales = [max(abs(row[column]) for row in matrix) for column in range(column_count)]
    if any(scale == 0 or not isfinite(scale) for scale in scales):
        raise ValueError("Fire-test observations do not span the regression variables.")
    values = [[value / scales[column] for column, value in enumerate(row)] for row in matrix]
    transformed = list(observations)
    permutation = list(range(column_count))
    first_pivot_norm = None
    for pivot_index in range(column_count):
        pivot_column = max(
            range(pivot_index, column_count),
            key=lambda column: fsum(
                values[row][column] ** 2 for row in range(pivot_index, row_count)
            ),
        )
        if pivot_column != pivot_index:
            for row in values:
                row[pivot_index], row[pivot_column] = row[pivot_column], row[pivot_index]
            scales[pivot_index], scales[pivot_column] = (
                scales[pivot_column],
                scales[pivot_index],
            )
            permutation[pivot_index], permutation[pivot_column] = (
                permutation[pivot_column],
                permutation[pivot_index],
            )
        norm = sqrt(fsum(values[row][pivot_index] ** 2 for row in range(pivot_index, row_count)))
        if first_pivot_norm is None:
            first_pivot_norm = norm
        if norm <= first_pivot_norm * 1e-12:
            raise ValueError("Fire-test data do not determine all seven regression coefficients.")
        alpha = -copysign(norm, values[pivot_index][pivot_index])
        reflector = [values[pivot_index][pivot_index] - alpha] + [
            values[row][pivot_index] for row in range(pivot_index + 1, row_count)
        ]
        reflector_norm_squared = fsum(value * value for value in reflector)
        if reflector_norm_squared == 0 or not isfinite(reflector_norm_squared):
            raise ValueError("Fire-test regression is numerically singular.")
        for column in range(pivot_index + 1, column_count):
            factor = (
                2
                * fsum(
                    reflector[row - pivot_index] * values[row][column]
                    for row in range(pivot_index, row_count)
                )
                / reflector_norm_squared
            )
            for row in range(pivot_index, row_count):
                values[row][column] -= reflector[row - pivot_index] * factor
        factor = (
            2
            * fsum(
                reflector[row - pivot_index] * transformed[row]
                for row in range(pivot_index, row_count)
            )
            / reflector_norm_squared
        )
        for row in range(pivot_index, row_count):
            transformed[row] -= reflector[row - pivot_index] * factor
        values[pivot_index][pivot_index] = alpha
        for row in range(pivot_index + 1, row_count):
            values[row][pivot_index] = 0.0
    solution = [0.0] * column_count
    for row in range(column_count - 1, -1, -1):
        remainder = transformed[row] - fsum(
            values[row][column] * solution[column] for column in range(row + 1, column_count)
        )
        solution[row] = remainder / values[row][row]
    coefficients = [0.0] * column_count
    for column, coefficient in enumerate(solution):
        coefficients[permutation[column]] = coefficient / scales[column]
    if not all(isfinite(coefficient) for coefficient in coefficients):
        raise ValueError("Fire-test regression produced nonfinite coefficients.")
    return coefficients


def _fit_fire_protected_regression(d):
    matrix = []
    observations = []
    geometry = []
    for test in d["test_series"]:
        if test["prototype_was_unloaded"] and not test["stickability_demonstrated"]:
            raise ValueError("Unloaded fire-test prototypes require demonstrated stickability.")
        geometry.append(
            {
                "protection_thickness_mm": test["protection_thickness_mm"],
                "surface_mass_ratio_m2_per_tonne": test["surface_mass_ratio_m2_per_tonne"],
            }
        )
        for point in test["temperature_time_points"]:
            matrix.append(
                _fire_regression_features(
                    test["protection_thickness_mm"],
                    point["temperature_c"],
                    test["surface_mass_ratio_m2_per_tonne"],
                )
            )
            observations.append(point["time_min"])
    if not all(isfinite(value) for row in matrix for value in row):
        raise ValueError("Fire-test regression features must be finite.")
    coefficients = _least_squares_fire_coefficients(matrix, observations)
    predictions = [
        fsum(coefficient * feature for coefficient, feature in zip(coefficients, row, strict=True))
        for row in matrix
    ]
    mean_observed = fsum(observations) / len(observations)
    mean_predicted = fsum(predictions) / len(predictions)
    observed_sum = fsum((value - mean_observed) ** 2 for value in observations)
    predicted_sum = fsum((value - mean_predicted) ** 2 for value in predictions)
    if observed_sum <= 0 or predicted_sum <= 0:
        raise ValueError("Fire-test observations need a varying time response.")
    correlation = fsum(
        (observed - mean_observed) * (predicted - mean_predicted)
        for observed, predicted in zip(observations, predictions, strict=True)
    ) / sqrt(observed_sum * predicted_sum)
    correlation = max(-1.0, min(1.0, correlation))
    residual = sqrt(
        fsum(
            (observed - predicted) ** 2
            for observed, predicted in zip(observations, predictions, strict=True)
        )
        / len(observations)
    )
    group_qualification = None
    if "three_sided_group_members" in d:
        group_qualification = _qualify_fire_three_sided_group(d["three_sided_group_members"])
        if not group_qualification["group_satisfied"]:
            raise ValueError("Fire-test members do not satisfy the Clause 12.9 group limits.")
        if d["exposure_sides"] == 3 and d.get("three_sided_grouping_verified") is False:
            raise ValueError("Declared Clause 12.9 status conflicts with measured group data.")
    elif d["exposure_sides"] == 3 and not d["three_sided_grouping_verified"]:
        raise ValueError("Three-sided fire-test series require a verified Clause 12.9 group.")
    if d["protection_material_type"] == "low_density_insulation":
        if d["protection_dry_density_kg_m3"] >= 1000:
            raise ValueError("Clause 12.6.2.3(a) requires dry density below 1000 kg/m3.")
    elif correlation <= 0.9:
        raise ValueError(
            "Intumescent or ablative coatings require a coefficient of correlation above 0.9."
        )
    result = {
        "coefficients": coefficients,
        "protection_material_type": d["protection_material_type"],
        "exposure_sides": d["exposure_sides"],
        "correlation_coefficient": correlation,
        "root_mean_square_residual_min": residual,
        "test_count": len(d["test_series"]),
        "observation_count": len(observations),
        "test_temperature_range_c": [
            min(
                point["temperature_c"]
                for test in d["test_series"]
                for point in test["temperature_time_points"]
            ),
            max(
                point["temperature_c"]
                for test in d["test_series"]
                for point in test["temperature_time_points"]
            ),
        ],
        "interpolation_window_points": _fire_interpolation_hull(geometry),
        "calibration_eligible": True,
    }
    if group_qualification is not None:
        result["three_sided_group_qualification"] = group_qualification
    return result


def _brittle(d):
    index = next(
        (i for i, bound in enumerate([6, 12, 20, 32, 70]) if d["thickness_mm"] <= bound), 5
    )
    temperature = _TEMPERATURES[d["steel_type"]][index]
    if temperature is None:
        raise ValueError("Steel type is unavailable at this thickness in Table 10.4.1.")
    temperature = min(temperature, d["impact_test_temperature_c"])
    strain = d["outer_fibre_strain_percent"]
    increase = 0 if strain < 1 else 20 + max(0, strain - 10)
    if 500 < d["post_weld_heat_treatment_c"] <= 620:
        increase = 0
    permissible = temperature + increase
    return (
        {
            "permissible_service_temperature_c": permissible,
            "strain_temperature_increase_c": increase,
            "check_satisfied": permissible < d["design_service_temperature_c"]
            and d["fabrication_erection_requirements_satisfied"],
        },
        ["10.3", "10.4.1", "10.4.2", "10.4.3"],
        [
            "Steel type must be selected from Table 10.4.4 using certified product grade.",
            "Design service temperature needs climate, erection and artificial-cooling review.",
            "Non-conforming conditions and fracture-mechanics assessment require separate review.",
        ],
    )


def _run_durability(inputs):
    """Run one explicitly tagged check; no operation certifies whole-standard compliance."""
    if not isinstance(inputs, Mapping):
        raise ValueError("Inputs must be an object.")  # noqa: TRY004
    d = dict(inputs)
    validate_standard_strengths(d)
    try:
        Draft202012Validator(INPUT_SCHEMA).validate(d)
    except ValidationError as exc:
        raise ValueError(exc.message) from exc
    if not _finite(d):
        raise ValueError("All numerical inputs must be finite.")
    op = d["check_type"]
    warnings = []
    if op in {"fatigue_constant", "fatigue_variable"}:
        result, clauses, warnings = _fatigue(d)
    elif op == "fatigue_exemption":
        phi = _phi(d)
        ranges = [d["normal_stress_range_mpa"], d["shear_stress_range_mpa"]]
        exempt = all(
            s < phi * 27 or (s > 0 and d["cycles"] < 2e6 * (phi * 36 / s) ** 3) for s in ranges
        )
        result, clauses = {"assessment_exempt": exempt}, ["11.1.5", "11.4"]
    elif op in {"fire_material", "fire_modulus"}:
        t = d["temperature_c"]
        elastic_ratio = (
            1 + t / (2000 * log(t / 1100)) if t <= 600 else (690 * (1 - t / 1000) / (t - 53.5))
        )
        result = {
            "elastic_ratio": elastic_ratio,
            "elastic_modulus_mpa": d["elastic_modulus_20_mpa"] * elastic_ratio,
            "shear_modulus_mpa": d["elastic_modulus_20_mpa"]
            * elastic_ratio
            / (2 * (1 + d["poisson_ratio"])),
        }
        clauses = ["12.4.2", "12.4.3"]
        if op == "fire_material":
            yield_ratio = 1 if t <= 215 else (905 - t) / 690
            result.update(
                yield_ratio=yield_ratio, yield_strength_mpa=d["yield_strength_20_mpa"] * yield_ratio
            )
            clauses.insert(0, "12.4.1")
        warnings = ["Slenderness terms specified in 12.4.3 retain room-temperature yield strength."]
    elif op == "fire_limiting_temperature":
        result = {"limiting_temperature_c": 905 - 690 * d["fire_action_ratio"]}
        clauses = ["12.5"]
        warnings = [
            "Ratio must use fire-design actions and room-temperature member design capacity."
        ]
    elif op == "fire_unprotected":
        t, k = d["limiting_temperature_c"], d["surface_mass_ratio_m2_per_tonne"]
        target = max(t, 500)
        time = (
            (-5.2 + 0.0221 * target + 0.433 * target / k)
            if d["exposure_sides"] == 3
            else (-4.7 + 0.0263 * target + 0.213 * target / k)
        )
        if t < 500:
            time *= (t - 20) / 480
        result = {"psa_min": time, "check_satisfied": time >= d["required_frl_min"]}
        clauses = ["12.3", "12.7"]
        warnings = ["Standard fire only; connection and penetration provisions require review."]
    elif op == "fire_single_test":
        applicable = all(
            d[key]
            for key in [
                "same_protection_system",
                "same_exposure",
                "same_supports",
                "restraints_not_less_favourable",
            ]
        )
        applicable = applicable and (
            d["protection_thickness_mm"] >= d["prototype_protection_thickness_mm"]
            and d["surface_mass_ratio_m2_per_tonne"]
            <= d["prototype_surface_mass_ratio_m2_per_tonne"]
            and d["fire_action_ratio"] <= d["prototype_fire_action_ratio"]
        )
        result = {
            "test_applicable": applicable,
            "prototype_psa_min": d["prototype_psa_min"],
            "check_satisfied": applicable and d["prototype_psa_min"] >= d["required_frl_min"],
        }
        clauses = ["12.8"]
        warnings = [
            "Requires AS 1530.4 test evidence; supplied declarations are not verified here."
        ]
    elif op == "fire_single_test_history":
        history = d["temperature_history"]
        times = [point["time_min"] for point in history]
        temperatures = [point["steel_temperature_c"] for point in history]
        if times[0] != 0 or any(
            current <= previous for previous, current in zip(times[:-1], times[1:], strict=True)
        ):
            raise ValueError(
                "Temperature history must start at zero and increase strictly in time."
            )
        applicable = (
            d["same_protection_system"]
            and d["same_exposure_condition"]
            and d["protection_thickness_mm"] >= d["prototype_protection_thickness_mm"]
            and d["surface_mass_ratio_m2_per_tonne"]
            <= d["prototype_surface_mass_ratio_m2_per_tonne"]
            and (not d["prototype_was_unloaded"] or d["stickability_demonstrated"])
        )
        limit = d["limiting_temperature_c"]
        attained_time = None
        if temperatures[0] >= limit:
            attained_time = times[0]
        else:
            for index in range(1, len(history)):
                if temperatures[index] >= limit:
                    previous_temperature = temperatures[index - 1]
                    current_temperature = temperatures[index]
                    fraction = (limit - previous_temperature) / (
                        current_temperature - previous_temperature
                    )
                    attained_time = times[index - 1] + fraction * (times[index] - times[index - 1])
                    break
        psa_lower_bound = times[-1] if attained_time is None else attained_time
        result = {
            "test_applicable": applicable,
            "limiting_temperature_attained": attained_time is not None,
            "attained_time_min": attained_time,
            "psa_min_lower_bound": psa_lower_bound,
            "check_satisfied": applicable and psa_lower_bound >= d["required_frl_min"],
        }
        clauses = ["12.6.1", "12.6.3"]
        warnings = [
            "Supply the representative steel-temperature history selected under 12.6.1 "
            "and evidence from a standard fire test to AS 1530.4.",
            "Linear interpolation between measured readings estimates the limiting-temperature "
            "crossing; an un-crossed limit reports only the test-duration lower bound.",
        ]
    elif op == "web_penetration_protection":
        required_thickness = max(
            d["required_thickness_above_mm"],
            d["required_thickness_below_mm"],
            d["required_thickness_whole_section_mm"],
        )
        minimum_extension = max(d["beam_depth_mm"], 300)
        thickness_ok = d["provided_thickness_mm"] >= required_thickness
        depth_ok = d["protected_depth_mm"] >= d["beam_depth_mm"]
        left_ok = d["left_extension_mm"] >= minimum_extension
        right_ok = d["right_extension_mm"] >= minimum_extension
        result = {
            "required_thickness_mm": required_thickness,
            "provided_thickness_mm": d["provided_thickness_mm"],
            "minimum_extension_each_side_mm": minimum_extension,
            "provided_left_extension_mm": d["left_extension_mm"],
            "provided_right_extension_mm": d["right_extension_mm"],
            "thickness_satisfied": thickness_ok,
            "full_depth_satisfied": depth_ok,
            "left_extension_satisfied": left_ok,
            "right_extension_satisfied": right_ok,
            "check_satisfied": thickness_ok and depth_ok and left_ok and right_ok,
        }
        clauses = ["12.10.2"]
        warnings = [
            "The three area-specific required protection thicknesses must be established "
            "separately under the applicable fire-test and grouping provisions."
        ]
    elif op == "fire_connection_protection":
        result = _fire_connection_protection(d)
        clauses = ["12.10.1"]
        warnings = [
            "Provide all framing-member fire-protection thicknesses and identify every "
            "connection component, including bolt heads, welds and splice plates.",
            "The supplied protection-continuity declarations require drawing and installation "
            "verification.",
        ]
    elif op == "concentric_tension_brace":
        action_limit = 0.85 * d["member_design_tensile_capacity_kn"]
        member_ok = d["design_tension_action_kn"] <= action_limit
        connection_ok = (
            d["connection_design_tensile_capacity_kn"] >= d["member_design_tensile_capacity_kn"]
        )
        result = {
            "member_action_limit_kn": action_limit,
            "design_tension_action_kn": d["design_tension_action_kn"],
            "member_action_satisfied": member_ok,
            "connection_required_capacity_kn": d["member_design_tensile_capacity_kn"],
            "connection_design_tensile_capacity_kn": d["connection_design_tensile_capacity_kn"],
            "connection_capacity_satisfied": connection_ok,
            "check_satisfied": member_ok and connection_ok,
        }
        clauses = ["13.3.6.2(a)"]
        warnings = [
            "Applies only to concentric braced frames in bearing-wall or building-frame "
            "systems; verify member and connection capacities and seismic applicability."
        ]
    elif op == "fire_protected_regression_fit":
        result = _fit_fire_protected_regression(d)
        clauses = ["12.6.2.1", "12.6.2.2", "12.6.2.3"]
        warnings = [
            "Calibration uses the supplied AS 1530.4 fire-test observations and declared "
            "test-series conditions; verify source reports and protection-system identity.",
            "Three-sided group dimensions, concrete properties and rib void conditions need "
            "verification under Clause 12.9.",
            "For intumescent or ablative coatings, the fitted correlation coefficient must "
            "exceed 0.9.",
        ]
    elif op == "fire_three_sided_group":
        result = _qualify_fire_three_sided_group(d["members"])
        clauses = ["12.9(a)(i)", "12.9(a)(ii)", "12.9(b)"]
        warnings = [
            "Verify that each supplied concrete density, concrete area excluding voids, "
            "tributary width and rib void condition represents the member geometry "
            "and construction."
        ]
    elif op == "fire_protected_regression":
        if not d["test_series_conditions_satisfied"]:
            raise ValueError("Regression requires verified Clause 12.6.2 test-series conditions.")
        application_conditions = None
        if "application_conditions" in d:
            application_conditions = _check_fire_regression_application_conditions(
                d["application_conditions"]
            )
        within_test_temperature_range = None
        if "test_temperature_range_c" in d:
            temperature_min, temperature_max = d["test_temperature_range_c"]
            if temperature_min > temperature_max:
                raise ValueError("The test-temperature range must be ordered from low to high.")
            within_test_temperature_range = temperature_min <= d["temperature_c"] <= temperature_max
            if not within_test_temperature_range:
                raise ValueError(
                    "Regression is limited to the temperature range measured in the test series."
                )
        interpolation_hull = None
        if "interpolation_window_points" in d:
            interpolation_hull = _fire_interpolation_hull(d["interpolation_window_points"])
            inside_interpolation_window = _inside_fire_interpolation_hull(
                d["protection_thickness_mm"],
                d["surface_mass_ratio_m2_per_tonne"],
                interpolation_hull,
            )
            if (
                "inside_reviewed_interpolation_window" in d
                and d["inside_reviewed_interpolation_window"] != inside_interpolation_window
            ):
                raise ValueError(
                    "Reviewed interpolation status conflicts with the calculated test window."
                )
        else:
            inside_interpolation_window = d["inside_reviewed_interpolation_window"]
        if not inside_interpolation_window:
            raise ValueError("Regression is limited to interpolation inside the test-data window.")
        k0, k1, k2, k3, k4, k5, k6 = d["coefficients"]
        h, t, k = (
            d["protection_thickness_mm"],
            d["temperature_c"],
            d["surface_mass_ratio_m2_per_tonne"],
        )
        time = k0 + k1 * h + k2 * h / k + k3 * t + k4 * h * t + k5 * h * t / k + k6 * t / k
        if time < 0:
            raise ValueError("Regression predicted negative time.")
        result = {
            "psa_min": time,
            "check_satisfied": time >= d["required_frl_min"],
            "inside_interpolation_window": inside_interpolation_window,
        }
        if within_test_temperature_range is not None:
            result["within_test_temperature_range"] = within_test_temperature_range
            result["test_temperature_range_c"] = d["test_temperature_range_c"]
        if application_conditions is not None:
            result["application_conditions"] = application_conditions
        if interpolation_hull is not None:
            result["interpolation_window_points"] = interpolation_hull
            warnings = [
                "No extrapolation: geometry is checked against the test-data hull and temperature "
                "against the measured test range.",
                "Protection-system identity, same-material declarations and stickability evidence "
                "must be verified for Clause 12.6.2.3 application conditions.",
            ]
        clauses = ["12.6.1", "12.6.2"]
        if interpolation_hull is None:
            warnings = [
                "Coefficients must come from least-squares regression of at least nine qualifying "
                "fire tests.",
                "The caller-supplied interpolation declaration cannot be independently checked; "
                "assess geometry and temperature limits plus the Clause 12.6.2.3 reuse conditions.",
            ]
    elif op == "brittle_fracture":
        result, clauses, warnings = _brittle(d)
    else:
        mu, sp = _SEISMIC[d["structural_system"]]
        result = {
            "ductility_factor": mu,
            "structural_performance_factor": sp,
            "minimum_panel_movement_mm": max(6, d["design_storey_deflection_mm"]),
            "yield_limit_satisfied": d["grade_minimum_yield_mpa"] <= 350 if mu <= 3 else None,
            "manual_review_required": True,
        }
        clauses = ["13.1", "13.3"]
        warnings = [
            "AS 1170.4 category, system, load paths and detailing require structural review.",
            "Stiff elements, panel connections, brace connections, weld examination, plastic "
            "hinges and fabrication remain manual checks.",
        ]
        if mu > 3:
            warnings.append("Fully ductile structures require NZS 1170.5 and NZS 3404 design.")
    output = {
        "check_type": op,
        "standard": "AS 4100:2020",
        "clauses": clauses,
        "results": result,
        "warnings": warnings,
    }
    if not _finite(output):
        raise ValueError("Calculated outputs must be finite.")
    Draft202012Validator(OUTPUT_SCHEMA).validate(output)
    return output


def run_durability(inputs):
    """Validate input and convert numerical domain failures to host validation errors."""
    try:
        return _run_durability(inputs)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Inputs exceed a stable numerical domain.") from exc
