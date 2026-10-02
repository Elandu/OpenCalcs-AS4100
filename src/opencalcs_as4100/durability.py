"""AS 4100:2020 sections 10–13 bounded durability and fire operations."""

from collections.abc import Mapping
from math import isfinite, log

from jsonschema import Draft202012Validator, ValidationError

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
                "elastic_modulus_20_mpa": _POS,
                "poisson_ratio": _number(0, 0.5),
            },
        ),
        _operation(
            "fire_modulus",
            {
                "temperature_c": _number(0, 1000, True),
                "elastic_modulus_20_mpa": _POS,
                "poisson_ratio": _number(0, 0.5),
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
            "fire_protected_regression",
            {
                "coefficients": {
                    "type": "array",
                    "minItems": 7,
                    "maxItems": 7,
                    "items": _number(-1e12, 1e12),
                },
                "temperature_c": _number(250, 1000, True),
                "protection_thickness_mm": _POS,
                "surface_mass_ratio_m2_per_tonne": _POS,
                "required_frl_min": _number(),
                "test_count": {"type": "integer", "minimum": 9},
                "test_series_conditions_satisfied": _BOOL,
                "inside_reviewed_interpolation_window": _BOOL,
            },
        ),
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
    "fire_protected_regression": _result_schema({"psa_min": _NUM, "check_satisfied": _BOOL}),
    "fire_single_test": _result_schema(
        {"test_applicable": _BOOL, "prototype_psa_min": _NUM, "check_satisfied": _BOOL}
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
    elif op == "fire_protected_regression":
        if not (
            d["test_series_conditions_satisfied"] and d["inside_reviewed_interpolation_window"]
        ):
            raise ValueError(
                "Regression requires reviewed test conditions and interpolation window."
            )
        k0, k1, k2, k3, k4, k5, k6 = d["coefficients"]
        h, t, k = (
            d["protection_thickness_mm"],
            d["temperature_c"],
            d["surface_mass_ratio_m2_per_tonne"],
        )
        time = k0 + k1 * h + k2 * h / k + k3 * t + k4 * h * t + k5 * h * t / k + k6 * t / k
        if time < 0:
            raise ValueError("Regression predicted negative time.")
        result = {"psa_min": time, "check_satisfied": time >= d["required_frl_min"]}
        clauses = ["12.6.1", "12.6.2"]
        warnings = [
            "Coefficients need least-squares fit to at least nine qualifying fire tests.",
            "No extrapolation; material, exposure, stickability and grouping need review.",
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
