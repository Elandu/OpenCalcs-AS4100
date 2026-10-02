"""Axial section checks, AS 4100:2020 clauses 6.2.1 and 7.2."""

from collections.abc import Mapping
from math import isfinite
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

from .schemas import INPUT_SCHEMA, OUTPUT_SCHEMA


def run_analysis(inputs: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(inputs, Mapping):
        raise ValueError("Inputs must be an object.")  # noqa: TRY004 - host validation contract
    data = dict(inputs)
    try:
        Draft202012Validator(INPUT_SCHEMA).validate(data)
    except ValidationError as exc:
        raise ValueError(exc.message) from exc
    if any(not isfinite(value) for value in data.values()):
        raise ValueError("All values must be finite.")
    if data["net_area_mm2"] > data["gross_area_mm2"]:
        raise ValueError("Net area must not exceed gross area.")
    if data["ultimate_strength_mpa"] < data["yield_strength_mpa"]:
        raise ValueError("Ultimate strength must not be below yield strength.")
    fy, fu = data["yield_strength_mpa"], data["ultimate_strength_mpa"]
    ag, an = data["gross_area_mm2"], data["net_area_mm2"]
    yielding = ag * fy / 1000
    fracture = 0.85 * data["tension_distribution_factor"] * an * fu / 1000
    tension = min(yielding, fracture)
    compression = data["compression_form_factor"] * an * fy / 1000

    def check(capacity, action, mode):
        design = 0.9 * capacity
        if not isfinite(design) or design <= 0:
            raise ValueError("Calculated capacity must be finite and positive.")
        utilisation = action / design
        if not isfinite(utilisation):
            raise ValueError("Calculated utilisation must be finite.")
        return {
            "nominal_capacity_kn": capacity,
            "design_capacity_kn": design,
            "action_kn": action,
            "utilisation": utilisation,
            "section_capacity_satisfied": action <= design,
            "governing_mode": mode,
        }

    result = {
        "standard": "AS 4100:2020",
        "scope": "section axial capacities only",
        "capacity_factor": 0.9,
        "tension_nominal_modes_kn": {"gross_yielding": yielding, "net_fracture": fracture},
        "tension": check(
            tension,
            data["tension_action_kn"],
            "gross section yielding" if yielding <= fracture else "net section fracture",
        ),
        "compression": check(compression, data["compression_action_kn"], "section compression"),
        "warnings": [
            "Section capacity satisfaction does not establish member or structure compliance.",
            "Member buckling, bending, shear, interactions and connections are not checked.",
            "Net area and tension distribution/compression form factors need external assessment.",
        ],
    }
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result
