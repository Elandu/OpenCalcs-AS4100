"""Connection component calculations reviewed against AS 4100:2020 Section 9."""

from collections.abc import Mapping
from math import hypot, isfinite, pi
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

from .validation import validate_standard_strengths


def _number(minimum=0, positive=False):
    return {"type": "number", "exclusiveMinimum" if positive else "minimum": minimum}


def _schema(kind, fields):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["check_type", *fields],
        "properties": {"check_type": {"const": kind}, **fields},
    }


P = _number(positive=True)
N = _number()
SIGNED = {"type": "number"}
QUALITY = {"enum": ["SP", "GP"]}
BOOL = {"type": "boolean"}
POINT = {"type": "array", "minItems": 2, "maxItems": 2, "items": SIGNED}
FIELDS = {
    "bolt": {
        "ultimate_strength_mpa": P,
        "minor_area_mm2": P,
        "shank_area_mm2": P,
        "tensile_area_mm2": P,
        "threaded_planes": {"type": "integer", "minimum": 0},
        "plain_planes": {"type": "integer", "minimum": 0},
        "grade": {"enum": ["4.6", "8.8", "10.9"]},
        "lap_length_mm": N,
        "filler_thickness_mm": {"type": "number", "minimum": 0, "exclusiveMaximum": 20},
        "shear_action_kn": N,
        "tension_action_kn": N,
    },
    "bearing": {
        "diameter_mm": P,
        "ply_thickness_mm": P,
        "ultimate_strength_mpa": P,
        "effective_edge_distance_mm": P,
        "action_kn": N,
    },
    "slip": {
        "slip_factor": P,
        "interfaces": {"type": "integer", "minimum": 1},
        "installation_tension_kn": P,
        "hole_type": {"enum": ["standard", "short_slot", "oversize", "long_slot"]},
        "shear_action_kn": N,
        "tension_action_kn": N,
    },
    "block_shear": {
        "yield_strength_mpa": P,
        "ultimate_strength_mpa": P,
        "gross_shear_area_mm2": P,
        "net_shear_area_mm2": P,
        "net_tension_area_mm2": P,
        "uniform_tension": BOOL,
        "action_kn": N,
    },
    "pin": {
        "yield_strength_mpa": P,
        "diameter_mm": P,
        "shear_planes": {"type": "integer", "minimum": 1},
        "ply_thickness_mm": P,
        "rotates": BOOL,
        "shear_action_kn": N,
        "bearing_action_kn": N,
        "moment_action_knm": N,
    },
    "fillet": {
        "weld_strength_mpa": P,
        "throat_mm": P,
        "effective_length_mm": P,
        "quality": QUALITY,
        "thin_rhs_longitudinal": BOOL,
        "lap_length_mm": N,
        "action_kn": N,
    },
    "complete_butt": {
        "weaker_part_nominal_capacity_kn": P,
        "quality": QUALITY,
        "qualified_matching_consumable": {"const": True},
        "action_kn": N,
    },
    "plug_slot": {
        "weld_strength_mpa": P,
        "effective_area_mm2": P,
        "quality": QUALITY,
        "permitted_shear_application": {"const": True},
        "action_kn": N,
    },
    "layout": {
        "diameter_mm": P,
        "thinnest_ply_mm": P,
        "pitch_mm": P,
        "edge_distance_mm": P,
        "edge_type": {"enum": ["sheared", "machined", "rolled"]},
        "pitch_case": {"enum": ["general", "outside_line", "non_load_noncorrosive"]},
    },
    "hole_deduction": {
        "gross_area_mm2": P,
        "thickness_mm": P,
        "straight_hole_width_sum_mm": N,
        "zigzag_hole_width_sum_mm": N,
        "stagger_pairs": {
            "type": "array",
            "items": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "prefixItems": [N, P],
                "items": False,
            },
        },
    },
}
FIELDS["bolt_group"] = {
    **FIELDS["bolt"],
    "points_mm": {"type": "array", "minItems": 2, "items": POINT},
    "force_x_kn": SIGNED,
    "force_y_kn": SIGNED,
    "moment_z_knm": SIGNED,
}
FIELDS["weld_group"] = {
    "weld_strength_mpa": P,
    "throat_mm": P,
    "quality": QUALITY,
    "segments_mm": {
        "type": "array",
        "minItems": 1,
        "items": {"type": "array", "minItems": 2, "maxItems": 2, "items": POINT},
    },
    **{f"force_{a}_kn": SIGNED for a in "xyz"},
    **{f"moment_{a}_knm": SIGNED for a in "xyz"},
}
INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "oneOf": [_schema(k, v) for k, v in FIELDS.items()],
}
OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["standard", "check_type", "checks", "scope"],
    "additionalProperties": False,
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "check_type": {"enum": list(FIELDS)},
        "checks": {"type": "object"},
        "intermediate": {"type": "object"},
        "scope": {"type": "string"},
    },
}


def _finite(value):
    if isinstance(value, Mapping):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return not isinstance(value, (int, float)) or isinstance(value, bool) or isfinite(value)


def _check(capacity, phi, action, clause, unit="kn"):
    design = capacity * phi
    if design <= 0 or not isfinite(design):
        raise ValueError("Calculated capacity must be finite and positive.")
    return {
        f"nominal_capacity_{unit}": capacity,
        f"design_capacity_{unit}": design,
        "capacity_factor": phi,
        "utilisation": action / design,
        "satisfied": action <= design,
        "clause": clause,
    }


def _bolt(d):
    nn, nx = d["threaded_planes"], d["plain_planes"]
    if nn + nx == 0:
        raise ValueError("At least one shear plane is required.")
    if d["minor_area_mm2"] > d["tensile_area_mm2"] or d["tensile_area_mm2"] > d["shank_area_mm2"]:
        raise ValueError("Bolt areas must satisfy minor <= tensile <= shank.")
    length = d["lap_length_mm"]
    kr = 1 if length < 300 else (1.075 - length / 4000 if length <= 1300 else 0.75)
    krd = 0.83 if d["grade"] == "10.9" and nn else 1
    filler = d["filler_thickness_mm"]
    kf = 1 - 0.0154 * (filler - 6) if filler > 6 else 1
    shear = (
        0.62
        * d["ultimate_strength_mpa"]
        * kr
        * krd
        * kf
        * (nn * d["minor_area_mm2"] + nx * d["shank_area_mm2"])
        / 1000
    )
    tension = d["tensile_area_mm2"] * d["ultimate_strength_mpa"] / 1000
    return shear, tension, {"lap_factor": kr, "ductility_factor": krd, "filler_factor": kf}


def run_connections(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Reject numerically unrepresentable calculations as invalid input domains."""
    try:
        return _run_connections(inputs)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Connection calculation exceeds the finite numeric domain.") from exc


def _run_connections(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate the tagged component check; actions include externally assessed prying."""
    if not isinstance(inputs, Mapping):
        raise ValueError("Inputs must be an object.")
    d = dict(inputs)
    validate_standard_strengths(d)
    try:
        Draft202012Validator(INPUT_SCHEMA).validate(d)
    except ValidationError as exc:
        raise ValueError(exc.message) from exc
    if not _finite(d):
        raise ValueError("All numeric inputs must be finite.")
    k = d["check_type"]
    c, intermediate = {}, {}
    if k in {"bolt", "bolt_group"}:
        v, n, intermediate = _bolt(d)
        actions = [(d["shear_action_kn"], d["tension_action_kn"])]
        if k == "bolt_group":
            if d["shear_action_kn"] or d["tension_action_kn"]:
                raise ValueError(
                    "Group uses signed in-plane actions only; component actions must be zero."
                )
            points = d["points_mm"]
            if len({tuple(p) for p in points}) != len(points):
                raise ValueError("Bolt positions must be distinct.")
            count = len(points)
            cx, cy = (sum(p[i] for p in points) / count for i in (0, 1))
            j = sum((x - cx) ** 2 + (y - cy) ** 2 for x, y in points)
            if not isfinite(j) or j <= 0:
                raise ValueError("Bolt group polar sum must be finite and positive.")
            mz = d["moment_z_knm"] * 1000
            forces = [
                [
                    d["force_x_kn"] / count - mz * (y - cy) / j,
                    d["force_y_kn"] / count + mz * (x - cx) / j,
                ]
                for x, y in points
            ]
            actions = [(hypot(*f), 0) for f in forces]
            intermediate.update(centroid_mm=[cx, cy], polar_sum_mm2=j, bolt_forces_kn=forces)
        for i, (va, na) in enumerate(actions):
            prefix = f"bolt_{i}_" if k == "bolt_group" else ""
            c[prefix + "shear"] = _check(v, 0.8, va, "9.2.2.1")
            c[prefix + "tension"] = _check(n, 0.8, na, "9.2.2.2")
            u = (va / (0.8 * v)) ** 2 + (na / (0.8 * n)) ** 2
            c[prefix + "interaction"] = {"utilisation": u, "satisfied": u <= 1, "clause": "9.2.2.3"}
    elif k == "bearing":
        a = 3.2 * d["diameter_mm"] * d["ply_thickness_mm"] * d["ultimate_strength_mpa"] / 1000
        b = (
            d["effective_edge_distance_mm"]
            * d["ply_thickness_mm"]
            * d["ultimate_strength_mpa"]
            / 1000
        )
        c["bearing"] = _check(min(a, b), 0.9, d["action_kn"], "9.2.2.4")
        intermediate = {"bearing_kn": a, "edge_kn": b}
    elif k == "slip":
        kh = {"standard": 1, "short_slot": 0.85, "oversize": 0.85, "long_slot": 0.7}[d["hole_type"]]
        v = d["slip_factor"] * d["interfaces"] * d["installation_tension_kn"] * kh
        u = d["shear_action_kn"] / (0.7 * v) + d["tension_action_kn"] / (
            0.7 * d["installation_tension_kn"]
        )
        c["slip"] = _check(v, 0.7, d["shear_action_kn"], "9.2.3.1; 3.5.5")
        c["interaction"] = {"utilisation": u, "satisfied": u <= 1, "clause": "9.2.3.3"}
        intermediate = {"hole_factor": kh}
    elif k == "block_shear":
        if d["net_shear_area_mm2"] > d["gross_shear_area_mm2"]:
            raise ValueError("Net shear area cannot exceed gross shear area.")
        fy, fu = d["yield_strength_mpa"], d["ultimate_strength_mpa"]
        if fu < fy:
            raise ValueError("Ultimate strength cannot be below yield strength.")
        kb = 1 if d["uniform_tension"] else 0.5
        t = kb * fu * d["net_tension_area_mm2"]
        modes = [
            (0.6 * fu * d["net_shear_area_mm2"] + t) / 1000,
            (0.6 * fy * d["gross_shear_area_mm2"] + t) / 1000,
        ]
        c["block_shear"] = _check(min(modes), 0.75, d["action_kn"], "9.1.9(e)")
        intermediate = {"eccentricity_factor": kb, "nominal_modes_kn": modes}
    elif k == "pin":
        fy, dia = d["yield_strength_mpa"], d["diameter_mm"]
        c["shear"] = _check(
            0.62 * fy * d["shear_planes"] * pi * dia**2 / 4000, 0.8, d["shear_action_kn"], "9.4.1"
        )
        c["bearing"] = _check(
            1.4 * fy * dia * d["ply_thickness_mm"] * (0.5 if d["rotates"] else 1) / 1000,
            0.8,
            d["bearing_action_kn"],
            "9.4.2",
        )
        c["bending"] = _check(fy * dia**3 / 6e6, 0.8, d["moment_action_knm"], "9.4.3", "knm")
    elif k in {"fillet", "complete_butt", "plug_slot"}:
        phi = 0.8 if d["quality"] == "SP" else 0.6
        if k == "fillet":
            lap_m = d["lap_length_mm"] / 1000
            lap_factor = 1 if lap_m <= 1.7 else (1.10 - 0.06 * lap_m if lap_m <= 8 else 0.62)
            if d["thin_rhs_longitudinal"]:
                if d["quality"] != "SP":
                    raise ValueError("Thin RHS longitudinal fillet requires SP quality.")
                phi = 0.7
            capacity = (
                0.6
                * d["weld_strength_mpa"]
                * d["throat_mm"]
                * d["effective_length_mm"]
                * lap_factor
                / 1000
            )
            clause = "9.6.3.10; 9.6.2.7(c) for incomplete butt"
        elif k == "complete_butt":
            phi = 0.9 if d["quality"] == "SP" else 0.6
            capacity = d["weaker_part_nominal_capacity_kn"]
            clause = "9.6.2.7(a)"
        else:
            capacity = 0.6 * d["weld_strength_mpa"] * d["effective_area_mm2"] / 1000
            clause = "9.6.4.2"
        c["weld"] = _check(capacity, phi, d["action_kn"], clause)
    elif k == "layout":
        dia, t = d["diameter_mm"], d["thinnest_ply_mm"]
        min_edge = {"sheared": 1.75, "machined": 1.5, "rolled": 1.25}[d["edge_type"]] * dia
        max_pitch = {
            "general": min(15 * t, 200),
            "outside_line": min(4 * t + 100, 200),
            "non_load_noncorrosive": min(32 * t, 300),
        }[d["pitch_case"]]
        c["pitch"] = {
            "satisfied": 2.5 * dia <= d["pitch_mm"] <= max_pitch,
            "clause": "9.5.1; 9.5.3",
        }
        c["edge"] = {
            "satisfied": min_edge <= d["edge_distance_mm"] <= min(12 * t, 150),
            "clause": "9.5.2; 9.5.4",
        }
        intermediate = {
            "minimum_pitch_mm": 2.5 * dia,
            "maximum_pitch_mm": max_pitch,
            "minimum_edge_mm": min_edge,
            "maximum_edge_mm": min(12 * t, 150),
        }
    elif k == "hole_deduction":
        correction = sum(s * s / (4 * g) for s, g in d["stagger_pairs"])
        deduction = d["thickness_mm"] * max(
            d["straight_hole_width_sum_mm"], d["zigzag_hole_width_sum_mm"] - correction
        )
        if deduction >= d["gross_area_mm2"]:
            raise ValueError("Hole deductions must leave positive net area.")
        intermediate = {"deduction_mm2": deduction, "net_area_mm2": d["gross_area_mm2"] - deduction}
        c["net_area"] = {"satisfied": True, "clause": "9.1.10"}
    else:
        c, intermediate = _weld_group(d)
    result = {
        "standard": "AS 4100:2020",
        "check_type": k,
        "checks": c,
        "intermediate": intermediate,
        "scope": (
            "Selected connection component checks; detailing, fabrication, prying, "
            "local effects and complete connection compliance require separate assessment."
        ),
    }
    if not _finite(result):
        raise ValueError("Calculated results must be finite.")
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result


def _weld_group(d):
    segments = d["segments_mm"]
    lengths = [hypot(b[0] - a[0], b[1] - a[1]) for a, b in segments]
    if any(length == 0 for length in lengths):
        raise ValueError("Weld segments must have positive length.")
    for i, (a, b) in enumerate(segments):
        dx, dy = b[0] - a[0], b[1] - a[1]
        denominator = dx * dx + dy * dy
        for c, e in segments[i + 1 :]:
            cross_c = dx * (c[1] - a[1]) - dy * (c[0] - a[0])
            cross_e = dx * (e[1] - a[1]) - dy * (e[0] - a[0])
            if abs(cross_c) <= 1e-12 * denominator and abs(cross_e) <= 1e-12 * denominator:
                tc = ((c[0] - a[0]) * dx + (c[1] - a[1]) * dy) / denominator
                te = ((e[0] - a[0]) * dx + (e[1] - a[1]) * dy) / denominator
                if min(1, max(tc, te)) > max(0, min(tc, te)):
                    raise ValueError("Weld segments must not overlap or repeat.")
    total = sum(lengths)
    cx, cy = (
        sum(length * (a[i] + b[i]) / 2 for (a, b), length in zip(segments, lengths, strict=True))
        / total
        for i in (0, 1)
    )
    ix = iy = ixy = 0
    for (a, b), length in zip(segments, lengths, strict=True):
        x1, y1, x2, y2 = a[0] - cx, a[1] - cy, b[0] - cx, b[1] - cy
        ix += length * (y1 * y1 + y1 * y2 + y2 * y2) / 3
        iy += length * (x1 * x1 + x1 * x2 + x2 * x2) / 3
        ixy += length * (2 * x1 * y1 + x1 * y2 + x2 * y1 + 2 * x2 * y2) / 6
    determinant = ix * iy - ixy * ixy
    mx, my, mz = (d[f"moment_{a}_knm"] * 1000 for a in "xyz")
    if (mx or my) and determinant <= 1e-12 * max(ix * iy, 1):
        raise ValueError("Weld geometry cannot support both-axis out-of-plane moment analysis.")
    aa = (-my * ix - mx * ixy) / determinant if mx or my else 0
    bb = (mx * iy + my * ixy) / determinant if mx or my else 0
    j = ix + iy
    if mz and j <= 0:
        raise ValueError("Weld polar inertia must be positive.")
    forces = []
    for a, b in segments:
        for x, y in (a, b):
            x, y = x - cx, y - cy
            forces.append(
                [
                    d["force_x_kn"] / total - mz * y / j,
                    d["force_y_kn"] / total + mz * x / j,
                    d["force_z_kn"] / total + aa * x + bb * y,
                ]
            )
    action = max(hypot(*f) for f in forces)
    phi = 0.8 if d["quality"] == "SP" else 0.6
    capacity = 0.6 * d["weld_strength_mpa"] * d["throat_mm"] / 1000
    return {
        "weld_group": _check(capacity, phi, action, "9.7.1.1; 9.7.2.1; 9.7.3.1", "kn_per_mm")
    }, {
        "centroid_mm": [cx, cy],
        "length_mm": total,
        "ix_mm3": ix,
        "iy_mm3": iy,
        "ixy_mm3": ixy,
        "endpoint_forces_kn_per_mm": forces,
    }
