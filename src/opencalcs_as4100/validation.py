# SPDX-License-Identifier: AGPL-3.0-only
"""Strict shared validation for clause-specific design operations."""

from collections.abc import Mapping
from math import isfinite

from jsonschema import Draft202012Validator, ValidationError

POSITIVE = {"type": "number", "minimum": 1e-9, "maximum": 1e15}
NONNEGATIVE = {"type": "number", "minimum": 0, "maximum": 1e15}
SIGNED = {"type": "number", "minimum": -1e15, "maximum": 1e15}
YIELD_STRESS = {"type": "number", "minimum": 1e-9, "maximum": 690}


def object_schema(properties, required=None):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties) if required is None else required,
    }


def validate(inputs, schema):
    if not isinstance(inputs, Mapping):
        raise ValueError("Inputs must be an object.")
    data = dict(inputs)
    try:
        Draft202012Validator(schema).validate(data)
    except ValidationError as exc:
        path = ".".join(str(item) for item in exc.absolute_path) or "<root>"
        raise ValueError(f"Invalid input at {path}: {exc.message}") from exc

    def finite(value):
        if isinstance(value, Mapping):
            return all(finite(item) for item in value.values())
        if isinstance(value, list):
            return all(finite(item) for item in value)
        return not isinstance(value, (float, int)) or isfinite(value)

    if not finite(data):
        raise ValueError("All numeric inputs must be finite.")
    return data


def validate_standard_strengths(data):
    """AS 4100 clause 1.1 scope limits steel yield stress to 690 MPa."""
    if isinstance(data, Mapping):
        for name, value in data.items():
            if (
                "yield" in name
                and "mpa" in name
                and isinstance(value, (int, float))
                and value > 690
            ):
                raise ValueError("Steel yield stress exceeds AS 4100's 690 MPa scope.")
            validate_standard_strengths(value)
    elif isinstance(data, list):
        for item in data:
            validate_standard_strengths(item)


def capacity_check(clause, nominal, action, phi=0.9):
    design = nominal * phi
    if not isfinite(design) or design <= 0:
        raise ValueError("Calculated design capacity must be finite and positive.")
    utilisation = abs(action) / design
    if not isfinite(utilisation):
        raise ValueError("Calculated utilisation must be finite.")
    return {
        "clause": clause,
        "nominal_capacity": nominal,
        "capacity_factor": phi,
        "design_capacity": design,
        "action": action,
        "utilisation": utilisation,
        "satisfied": utilisation <= 1,
    }


def result(operation, clauses, values, checks=(), limitations=()):
    return {
        "standard": "AS 4100:2020",
        "operation": operation,
        "clauses": list(clauses),
        "values": values,
        "checks": list(checks),
        "checked_conditions_satisfied": all(check["satisfied"] for check in checks),
        "full_standard_compliance": False,
        "limitations": list(limitations),
    }
