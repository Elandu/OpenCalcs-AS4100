"""Clause-traced member calculation primitives from AS 4100:2020.

Inputs are design actions (including required second-order effects), not solver loads.
Each operation is a calculation primitive, not a declaration of whole-member compliance.
"""

from collections.abc import Mapping
from math import isfinite, pi, sqrt
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

from .validation import validate_standard_strengths


def _number(minimum=0, *, positive=False, maximum=None):
    result = {"type": "number", "exclusiveMinimum" if positive else "minimum": minimum}
    if maximum is not None:
        result["maximum"] = maximum
    return result


def _variant(operation, properties, required):
    return {
        "type": "object",
        "properties": {"operation": {"const": operation}, **properties},
        "required": ["operation", *required],
        "additionalProperties": False,
    }


P = _number(positive=True)
N = _number()
R = {"type": "string", "enum": ["SR", "HR", "CF", "LW", "HW"]}
PLATE = {
    "type": "object",
    "properties": {
        "width_mm": P,
        "thickness_mm": P,
        "edges": {"type": "string", "enum": ["one", "both", "circular"]},
        "stress": {
            "type": "string",
            "enum": ["uniform", "outstand_gradient", "internal_gradient"],
        },
        "residual": R,
    },
    "required": ["width_mm", "thickness_mm", "edges", "stress", "residual"],
    "additionalProperties": False,
}
INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "oneOf": [
        _variant(
            "plate",
            {
                "yield_strength_mpa": P,
                "plate": PLATE,
                "elastic_modulus_mm3": P,
                "plastic_modulus_mm3": P,
            },
            ["yield_strength_mpa", "plate", "elastic_modulus_mm3", "plastic_modulus_mm3"],
        ),
        _variant(
            "compression",
            {
                "yield_strength_mpa": P,
                "gross_area_mm2": P,
                "net_area_mm2": P,
                "effective_area_mm2": P,
                "effective_length_x_mm": P,
                "effective_length_y_mm": P,
                "radius_x_mm": P,
                "radius_y_mm": P,
                "section_constant_x": {"enum": [-1, -0.5, 0, 0.5, 1]},
                "section_constant_y": {"enum": [-1, -0.5, 0, 0.5, 1]},
                "action_kn": N,
                "geometry": {"enum": ["doubly_symmetric", "chs", "rhs"]},
            },
            [
                "yield_strength_mpa",
                "gross_area_mm2",
                "net_area_mm2",
                "effective_area_mm2",
                "effective_length_x_mm",
                "effective_length_y_mm",
                "radius_x_mm",
                "radius_y_mm",
                "section_constant_x",
                "section_constant_y",
                "action_kn",
                "geometry",
            ],
        ),
        _variant(
            "bending",
            {
                "section_capacity_knm": P,
                "iy_mm4": P,
                "torsion_constant_mm4": P,
                "warping_constant_mm6": N,
                "effective_length_mm": P,
                "moment_factor": _number(positive=True, maximum=2.5),
                "action_knm": N,
                "geometry": {"const": "equal_flanged_open"},
            },
            [
                "section_capacity_knm",
                "iy_mm4",
                "torsion_constant_mm4",
                "warping_constant_mm6",
                "effective_length_mm",
                "moment_factor",
                "action_knm",
                "geometry",
            ],
        ),
        _variant(
            "shear",
            {
                "yield_strength_mpa": P,
                "web_area_mm2": P,
                "panel_depth_mm": P,
                "web_thickness_mm": P,
                "stiffener_spacing_mm": P,
                "tension_field": {"type": "boolean"},
                "stress_max_average_ratio": _number(1),
                "action_kn": N,
                "moment_action_knm": N,
                "section_moment_capacity_knm": P,
            },
            [
                "yield_strength_mpa",
                "web_area_mm2",
                "panel_depth_mm",
                "web_thickness_mm",
                "action_kn",
                "moment_action_knm",
                "section_moment_capacity_knm",
            ],
        ),
        _variant(
            "interaction",
            {
                "axial_mode": {"enum": ["compression", "tension"]},
                "section_axial_capacity_kn": P,
                "member_axial_x_kn": P,
                "member_axial_y_kn": P,
                "section_moment_x_knm": P,
                "section_moment_y_knm": P,
                "member_moment_x_knm": P,
                "axial_action_kn": N,
                "moment_x_knm": N,
                "moment_y_knm": N,
            },
            [
                "axial_mode",
                "section_axial_capacity_kn",
                "member_axial_x_kn",
                "member_axial_y_kn",
                "section_moment_x_knm",
                "section_moment_y_knm",
                "member_moment_x_knm",
                "axial_action_kn",
                "moment_x_knm",
                "moment_y_knm",
            ],
        ),
        _variant(
            "tension_distribution",
            {
                "configuration": {
                    "enum": [
                        "uniform",
                        "angle_short_leg",
                        "angle_other",
                        "channel_web",
                        "tee_flange",
                        "symmetric_paired",
                        "both_flanges",
                    ]
                },
                "connection_length_mm": P,
                "member_depth_mm": P,
                "connection_conditions_verified": {"const": True},
            },
            ["configuration", "connection_conditions_verified"],
        ),
    ],
}
OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "standard",
        "operation",
        "scope",
        "values",
        "checks",
        "trace",
        "manual_requirements",
    ],
    "properties": {
        "standard": {"const": "AS 4100:2020"},
        "operation": {"type": "string"},
        "scope": {"type": "string"},
        "values": {"type": "object"},
        "checks": {"type": "object"},
        "trace": {"type": "array"},
        "manual_requirements": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}


def _finite(value):
    if isinstance(value, Mapping):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return not isinstance(value, (int, float)) or isfinite(value)


def _check(action, capacity):
    if capacity < 0 or not isfinite(capacity):
        raise ValueError("Invalid design capacity.")
    return {
        "action": action,
        "design_capacity": capacity,
        "utilisation": action / capacity if capacity else None,
        "satisfied": action <= capacity,
    }


def _plate(d):
    p = d["plate"]
    b, t, fy = p["width_mm"], p["thickness_mm"], d["yield_strength_mpa"]
    edge, stress, residual = p["edges"], p["stress"], p["residual"]
    circular = edge == "circular"
    if circular and stress != "uniform":
        raise ValueError("Circular section requires uniform classification stress.")
    if (stress == "internal_gradient" and edge != "both") or (
        stress == "outstand_gradient" and edge != "one"
    ):
        raise ValueError("Plate stress pattern is incompatible with edge support.")
    if circular:
        lp, ly = (42 if residual in ("LW", "HW") else 50), 120
        compression_limit = 82
    elif stress == "internal_gradient":
        lp, ly = 82, 115
        compression_limit = {"SR": 45, "HR": 45, "LW": 40, "CF": 40, "HW": 35}[residual]
    elif edge == "both":
        lp, ly = 30, {"SR": 45, "HR": 45, "LW": 40, "CF": 40, "HW": 35}[residual]
        compression_limit = ly
    else:
        lp = {"SR": 10, "HR": 9, "CF": 8, "LW": 8, "HW": 8}[residual]
        compression_limit = {"SR": 16, "HR": 16, "CF": 15, "LW": 15, "HW": 14}[residual]
        ly = (
            {"SR": 25, "HR": 25, "CF": 22, "LW": 22, "HW": 22}[residual]
            if stress == "outstand_gradient"
            else compression_limit
        )
    slenderness = b / t * (fy / 250 if circular else sqrt(fy / 250))
    compression_slenderness = b / t * (fy / 250 if circular else sqrt(fy / 250))
    z, s = d["elastic_modulus_mm3"], d["plastic_modulus_mm3"]
    if s < z:
        raise ValueError("Plastic modulus must not be below elastic modulus.")
    compact = min(s, 1.5 * z)
    if slenderness <= lp:
        effective, category = compact, "compact"
    elif slenderness <= ly:
        effective = z + (ly - slenderness) / (ly - lp) * (compact - z)
        category = "non_compact"
    else:
        if stress == "internal_gradient":
            raise ValueError(
                "Slender internal-gradient plates require effective-section assessment."
            )
        ratio = ly / slenderness
        factor = (
            min(sqrt(ratio), (2 * ratio) ** 2)
            if circular
            else (ratio**2 if stress == "outstand_gradient" else ratio)
        )
        effective, category = z * factor, "slender"
    ratio_c = compression_limit / compression_slenderness
    effective_width = (
        b * min(1, sqrt(ratio_c), (3 * ratio_c) ** 2) if circular else (b * min(1, ratio_c))
    )
    return (
        {
            "element_slenderness": slenderness,
            "plasticity_limit": lp,
            "yield_limit": ly,
            "classification": category,
            "effective_modulus_mm3": effective,
            "section_capacity_knm": fy * effective / 1e6,
            "compression_yield_limit": compression_limit,
            "compression_effective_width_mm": effective_width,
        },
        {},
        ["5.2.2", "5.2.3", "5.2.4", "5.2.5", "6.2.3", "6.2.4"],
        [
            "Select the controlling plate by greatest element-slenderness/yield-limit ratio.",
            "Moduli must include applicable hole deductions under 5.2.6.",
            "Effective width is for uniform compression; assemble effective area under 6.2.2.",
        ],
    )


def _alpha(length, radius, kf, fy, constant):
    ln = length / radius * sqrt(kf * fy / 250)
    aa = 2100 * (ln - 13.5) / (ln * ln - 15.3 * ln + 2050)
    modified = max(0, ln + aa * constant)
    q = (modified / 90) ** 2
    eta = max(0, 0.00326 * (modified - 13.5))
    a = q + 1 + eta
    alpha = min(1, 2 / (a + sqrt(max(0, a * a - 4 * q))))
    return ln, modified, alpha


def _compression(d):
    ag, an, ae = d["gross_area_mm2"], d["net_area_mm2"], d["effective_area_mm2"]
    if max(an, ae) > ag:
        raise ValueError("Net and effective areas must not exceed gross area.")
    kf, fy = ae / ag, d["yield_strength_mpa"]
    if kf < 1 and min(d["section_constant_x"], d["section_constant_y"]) < -0.5:
        raise ValueError("Section constant -1 is unavailable for form factor below 1.")
    ns = kf * an * fy / 1000
    values = {"form_factor": kf, "section_capacity_kn": ns}
    checks = {"section": _check(d["action_kn"], 0.9 * ns)}
    for axis in "xy":
        ln, modified, alpha = _alpha(
            d[f"effective_length_{axis}_mm"],
            d[f"radius_{axis}_mm"],
            kf,
            fy,
            d[f"section_constant_{axis}"],
        )
        values.update(
            {
                f"modified_slenderness_{axis}": ln,
                f"imperfection_slenderness_{axis}": modified,
                f"reduction_{axis}": alpha,
                f"member_capacity_{axis}_kn": alpha * ns,
            }
        )
        checks[axis] = _check(d["action_kn"], 0.9 * alpha * ns)
    return (
        values,
        checks,
        ["6.2.1", "6.2.2", "6.3.2", "6.3.3"],
        [
            "Effective lengths require structural restraint/analysis assessment under 4.6.3.",
            "Select section constants from Table 6.3.3(A/B) for fabrication and form factor.",
            "Limited to constant-section members whose governing mode is flexural buckling.",
        ],
    )


def _bending(d):
    ms, le = d["section_capacity_knm"], d["effective_length_mm"]
    # E and G in MPa, dimensions in mm: result N.mm converted to kN.m.
    mo = (
        sqrt(
            (pi**2 * 200000 * d["iy_mm4"] / le**2)
            * (
                80000 * d["torsion_constant_mm4"]
                + pi**2 * 200000 * d["warping_constant_mm6"] / le**2
            )
        )
        / 1e6
    )
    ratio = ms / mo
    reduction = 1.8 / (sqrt(ratio * ratio + 3) + ratio)
    mb = min(ms, d["moment_factor"] * reduction * ms)
    return (
        {
            "reference_buckling_moment_knm": mo,
            "slenderness_reduction": reduction,
            "member_capacity_knm": mb,
        },
        {"bending": _check(d["action_knm"], 0.9 * mb)},
        ["5.6.1.1"],
        [
            "Constant equal-flanged open section with full/partial restraint at both ends only.",
            "Effective length must include twist/load-height/lateral-rotation factors under 5.6.3.",
            "Moment factor must be derived under 5.6.1.1; default conservative selection is 1.",
            "Restraints and critical section/critical flange require 5.3–5.5 assessment.",
        ],
    )


def _shear(d):
    fy = d["yield_strength_mpa"]
    slenderness = d["panel_depth_mm"] / d["web_thickness_mm"] * sqrt(fy / 250)
    vw = 0.6 * fy * d["web_area_mm2"] / 1000
    av = min(1, (82 / slenderness) ** 2)
    ad = 1
    if "stiffener_spacing_mm" in d:
        aspect = d["stiffener_spacing_mm"] / d["panel_depth_mm"]
        if aspect <= 3:
            av = min(
                1,
                (82 / slenderness) ** 2
                * (0.75 / aspect**2 + 1 if aspect >= 1 else 1 / aspect**2 + 0.75),
            )
            if d.get("tension_field", False):
                ad = 1 + (1 - av) / (1.15 * av * sqrt(1 + aspect**2))
        elif d.get("tension_field", False):
            raise ValueError("Tension field requires stiffener spacing/panel depth <= 3.")
    elif d.get("tension_field", False):
        raise ValueError("Tension field requires transverse stiffeners.")
    vu = min(vw, av * ad * vw)
    vv = vu * min(1, 2 / (0.9 + d.get("stress_max_average_ratio", 1)))
    moment_ratio = d["moment_action_knm"] / (0.9 * d["section_moment_capacity_knm"])
    vm = vv * (
        1
        if moment_ratio <= 0.75
        else (max(0, 2.2 - 1.6 * moment_ratio) if moment_ratio <= 1 else 0)
    )
    checks = {
        "shear_bending": _check(d["action_kn"], 0.9 * vm),
        "bending": _check(d["moment_action_knm"], 0.9 * d["section_moment_capacity_knm"]),
    }
    return (
        {
            "web_slenderness": slenderness,
            "shear_yield_capacity_kn": vw,
            "buckling_reduction": av,
            "tension_field_factor": ad,
            "shear_capacity_kn": vv,
            "shear_bending_capacity_kn": vm,
        },
        checks,
        ["5.11.2", "5.11.3", "5.11.4", "5.11.5", "5.12.3"],
        [
            "Flat webs only; web layout/thickness/openings require 5.9–5.10 assessment.",
            "Flange restraint factor taken conservatively as 1 under 5.11.5.2.",
            "Tension-field credit requires verified stiffener/end-post provisions in 5.15.",
            "Stress maximum/average ratio requires rational elastic stress analysis.",
        ],
    )


def _interaction(d):
    phi = 0.9
    n, mx, my = d["axial_action_kn"], d["moment_x_knm"], d["moment_y_knm"]
    ns, msx, msy = (
        d["section_axial_capacity_kn"],
        d["section_moment_x_knm"],
        d["section_moment_y_knm"],
    )
    mb = d["member_moment_x_knm"]
    if mb > msx:
        raise ValueError("Member moment capacity must not exceed section capacity.")
    ratio = n / (phi * ns)
    mrx, mry = msx * max(0, 1 - ratio), msy * max(0, 1 - ratio)
    if d["axial_mode"] == "compression":
        ncx, ncy = d["member_axial_x_kn"], d["member_axial_y_kn"]
        if max(ncx, ncy) > ns:
            raise ValueError("Member axial capacity must not exceed section capacity.")
        mix = msx * max(0, 1 - n / (phi * ncx))
        miy = msy * max(0, 1 - n / (phi * ncy))
        mox = mb * max(0, 1 - n / (phi * ncy))
        mcx = min(mix, mox)
    else:
        mix, miy = mrx, mry
        mox = min(mb * (1 + ratio), mrx)
        mcx = min(mrx, mox)
    section_util = ratio + mx / (phi * msx) + my / (phi * msy)
    if (mx and mcx == 0) or (my and miy == 0):
        member_util = None
        member_satisfied = False
    else:
        member_util = (mx / (phi * mcx) if mcx else 0) ** 1.4 + (
            my / (phi * miy) if miy else 0
        ) ** 1.4
        member_satisfied = member_util <= 1 and ratio <= 1
    checks = {
        "section_combined": {"utilisation": section_util, "satisfied": section_util <= 1},
        "member_combined": {"utilisation": member_util, "satisfied": member_satisfied},
        "in_plane_x": _check(mx, phi * mix),
        "in_plane_y": _check(my, phi * miy),
        "out_of_plane_x": _check(mx, phi * mox),
    }
    if d["axial_mode"] == "compression":
        checks["member_axial_x"] = _check(n, phi * d["member_axial_x_kn"])
        checks["member_axial_y"] = _check(n, phi * d["member_axial_y_kn"])
        checks["member_combined"]["satisfied"] &= all(
            checks[key]["satisfied"] for key in ("member_axial_x", "member_axial_y")
        )
    return (
        {
            "section_reduced_x_knm": mrx,
            "section_reduced_y_knm": mry,
            "in_plane_x_knm": mix,
            "in_plane_y_knm": miy,
            "out_of_plane_x_knm": mox,
        },
        checks,
        ["8.3.2", "8.3.3", "8.3.4", "8.4.2", "8.4.4", "8.4.5"],
        [
            "Elastic analysis only; moments must satisfy 8.2 second-order requirements.",
            "Section general linear paths used; optional compact-section enhancements omitted.",
            "Compression in-plane effective-length assumptions must satisfy 8.4.2.2.",
            "Special eccentrically connected angle and plastic-analysis paths excluded.",
        ],
    )


def _distribution(d):
    configuration = d["configuration"]
    factors = {
        "uniform": 1,
        "angle_short_leg": 0.75,
        "angle_other": 0.85,
        "channel_web": 0.85,
        "tee_flange": 0.9,
        "symmetric_paired": 1,
        "both_flanges": 0.85,
    }
    if configuration == "both_flanges":
        if "connection_length_mm" not in d or "member_depth_mm" not in d:
            raise ValueError("Both-flange connection requires length and depth.")
        if d["connection_length_mm"] < d["member_depth_mm"]:
            raise ValueError("Both-flange connection length must be at least member depth.")
    return (
        {"tension_distribution_factor": factors[configuration]},
        {},
        ["7.3.1", "7.3.2"],
        [
            "Connection conditions must be assessed against 7.3 and Table 7.3.2 diagrams.",
            "Short-leg case applies only to unequal angles; paired arrangements must be symmetric.",
            "Each flange in both-flange case must transfer at least half the maximum design force.",
        ],
    )


def run_members(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and calculate one documented member-design operation."""
    if not isinstance(inputs, Mapping):
        raise ValueError("Inputs must be an object.")
    data = dict(inputs)
    validate_standard_strengths(data)
    try:
        Draft202012Validator(INPUT_SCHEMA).validate(data)
    except ValidationError as exc:
        raise ValueError(exc.message) from exc
    if not _finite(data):
        raise ValueError("All numerical values must be finite.")
    functions = {
        "plate": _plate,
        "compression": _compression,
        "bending": _bending,
        "shear": _shear,
        "interaction": _interaction,
        "tension_distribution": _distribution,
    }
    try:
        values, checks, clauses, manual = functions[data["operation"]](data)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Input magnitudes exceed the numerical calculation range.") from exc
    result = {
        "standard": "AS 4100:2020",
        "operation": data["operation"],
        "scope": "Calculation primitive; manual applicability and restraint checks required",
        "values": values,
        "checks": checks,
        "trace": [{"clause": clause} for clause in clauses],
        "manual_requirements": manual,
    }
    if not _finite(result):
        raise ValueError("Calculated values must be finite.")
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    return result
