# SPDX-License-Identifier: AGPL-3.0-only
"""Concentrated bearing and stiffener checks, clauses 5.13 to 5.16."""

from math import sqrt

from .validation import (
    NONNEGATIVE,
    POSITIVE,
    YIELD_STRESS,
    capacity_check,
    object_schema,
    result,
    validate,
)

_BEARING = {
    "operation": {"const": "web_bearing"},
    "section_type": {"enum": ["i_or_channel", "rhs_shs"]},
    "web_thickness_mm": {"type": "number", "minimum": 3, "maximum": 1e6},
    "web_yield_mpa": YIELD_STRESS,
    "clear_web_depth_mm": POSITIVE,
    "bearing_width_at_flange_mm": POSITIVE,
    "bearing_width_at_neutral_axis_mm": POSITIVE,
    "restrained_flange_count": {"type": "integer", "enum": [1, 2]},
    "bearing_action_kn": NONNEGATIVE,
    "outside_radius_mm": POSITIVE,
    "stiff_bearing_length_mm": POSITIVE,
    "distance_to_member_end_mm": NONNEGATIVE,
}
SCHEMAS = {
    "web_bearing": object_schema(
        _BEARING,
        [
            "operation",
            "section_type",
            "web_thickness_mm",
            "web_yield_mpa",
            "clear_web_depth_mm",
            "bearing_action_kn",
            "restrained_flange_count",
        ],
    ),
    "load_bearing_stiffener": object_schema(
        {
            "operation": {"const": "load_bearing_stiffener"},
            "web_bearing_yield_kn": POSITIVE,
            "stiffener_area_mm2": POSITIVE,
            "web_yield_mpa": YIELD_STRESS,
            "stiffener_yield_mpa": YIELD_STRESS,
            "contact_stiffener_area_mm2": POSITIVE,
            "web_thickness_mm": POSITIVE,
            "clear_web_depth_mm": POSITIVE,
            "panel_spacing_mm": POSITIVE,
            "radius_of_gyration_mm": POSITIVE,
            "both_flanges_rotation_restrained": {"type": "boolean"},
            "available_web_width_left_mm": NONNEGATIVE,
            "available_web_width_right_mm": NONNEGATIVE,
            "stiffener_outstand_mm": POSITIVE,
            "stiffener_thickness_mm": POSITIVE,
            "outer_edge_continuously_stiffened": {"type": "boolean"},
            "bearing_action_kn": NONNEGATIVE,
        }
    ),
    "transverse_stiffener": object_schema(
        {
            "operation": {"const": "transverse_stiffener"},
            "clear_web_depth_mm": POSITIVE,
            "web_panel_depth_mm": POSITIVE,
            "web_thickness_mm": POSITIVE,
            "panel_spacing_mm": POSITIVE,
            "web_area_mm2": POSITIVE,
            "web_yield_mpa": YIELD_STRESS,
            "shear_buckling_coefficient": {"type": "number", "minimum": 0, "maximum": 1},
            "stiffener_configuration": {"enum": ["pair", "single_angle", "single_plate"]},
            "shear_action_kn": NONNEGATIVE,
            "nominal_web_shear_kn": POSITIVE,
            "nominal_web_buckling_no_tension_field_kn": POSITIVE,
            "nominal_stiffener_buckling_kn": POSITIVE,
            "stiffener_area_mm2": POSITIVE,
            "stiffener_second_moment_mm4": POSITIVE,
            "stiffener_outstand_mm": POSITIVE,
            "stiffener_thickness_mm": POSITIVE,
            "stiffener_yield_mpa": YIELD_STRESS,
            "outer_edge_continuously_stiffened": {"type": "boolean"},
        }
    ),
    "longitudinal_stiffener": object_schema(
        {
            "operation": {"const": "longitudinal_stiffener"},
            "web_depth_mm": POSITIVE,
            "web_thickness_mm": POSITIVE,
            "stiffener_area_mm2": POSITIVE,
            "stiffener_second_moment_mm4": POSITIVE,
            "location": {"enum": ["0.2_depth", "neutral_axis"]},
        }
    ),
    "rhs_bearing_bending": object_schema(
        {
            "operation": {"const": "rhs_bearing_bending"},
            "bearing_action_kn": NONNEGATIVE,
            "design_bearing_capacity_kn": POSITIVE,
            "moment_action_knm": NONNEGATIVE,
            "design_moment_capacity_knm": POSITIVE,
            "stiff_bearing_length_mm": POSITIVE,
            "section_width_mm": POSITIVE,
            "clear_web_depth_mm": POSITIVE,
            "web_thickness_mm": POSITIVE,
        }
    ),
}
INPUT_SCHEMA = {"oneOf": list(SCHEMAS.values())}
OUTPUT_SCHEMA = {"type": "object"}


def buckling_alpha(slenderness, fy):
    """Clause 6.3.3 with kf=1 and alpha_b=0.5, prescribed for web/stiffener buckling."""
    ln = slenderness * sqrt(fy / 250)
    aa = 2100 * (ln - 13.5) / (ln**2 - 15.3 * ln + 2050)
    lam = ln + 0.5 * aa
    eta = max(0.0, 0.00326 * (lam - 13.5))
    q = (lam / 90) ** 2
    s = 1 + eta + q
    alpha = 2 / (s + sqrt(max(0.0, s * s - 4 * q)))
    return min(1.0, alpha)


def run_webs(inputs):
    d = validate(inputs, INPUT_SCHEMA)
    op = d["operation"]
    if op == "web_bearing":
        t, fy, depth = d["web_thickness_mm"], d["web_yield_mpa"], d["clear_web_depth_mm"]
        if d["section_type"] == "i_or_channel":
            required = ["bearing_width_at_flange_mm", "bearing_width_at_neutral_axis_mm"]
            if any(name not in d for name in required):
                raise ValueError("I/channel bearing requires assessed dispersed bearing widths.")
            if any(
                name in d
                for name in [
                    "outside_radius_mm",
                    "stiff_bearing_length_mm",
                    "distance_to_member_end_mm",
                ]
            ):
                raise ValueError("Hollow-section inputs cannot be used with an I/channel section.")
            bbf, bb = d[required[0]], d[required[1]]
            if bb < bbf:
                raise ValueError("Neutral-axis dispersed width must not be below flange width.")
            yield_capacity = 1.25 * bbf * t * fy / 1000
            geometric_slenderness = (2.5 if d["restrained_flange_count"] == 2 else 5) * depth / t
            ap = None
        else:
            if d["restrained_flange_count"] != 2:
                raise ValueError(
                    "RHS/SHS bearing requires the hollow section's integral flange restraint."
                )
            required = ["outside_radius_mm", "stiff_bearing_length_mm", "distance_to_member_end_mm"]
            if any(name not in d for name in required):
                raise ValueError(
                    "RHS/SHS bearing requires radius, bearing length and end distance."
                )
            if any(
                name in d
                for name in ["bearing_width_at_flange_mm", "bearing_width_at_neutral_axis_mm"]
            ):
                raise ValueError("RHS/SHS dispersed widths are derived, not supplied.")
            radius, bs, bd = (d[name] for name in required)
            if radius < t or depth / t <= 1:
                raise ValueError("Invalid hollow-section radius or flat web depth.")
            ks, kv = 2 * radius / t - 1, depth / t
            interior = bd >= 1.5 * depth
            if interior:
                apm = 1 / ks + 0.5 / kv
                ap = 0.5 / ks * (1 + (1 - apm**2) * (1 + ks / kv - (1 - apm**2) * 0.25 / kv**2))
                bb = bs + 5 * radius + depth
                geometric_slenderness = 3.5 * depth / t
            else:
                ap = sqrt(2 + ks**2) - ks
                bb = bs + 2.5 * radius + depth / 2
                geometric_slenderness = 3.8 * depth / t
            if ap <= 0:
                raise ValueError("Hollow-section bearing coefficient outside the supported domain.")
            yield_capacity = 2 * bb * t * fy * ap / 1000
        alpha = buckling_alpha(geometric_slenderness, fy)
        buckling_capacity = alpha * t * bb * fy / 1000
        nominal = min(yield_capacity, buckling_capacity)
        return result(
            op,
            ["5.13.1", "5.13.2", "5.13.3", "5.13.4"],
            {
                "bearing_yield_kn": yield_capacity,
                "bearing_buckling_kn": buckling_capacity,
                "alpha_c": alpha,
                "alpha_p": ap,
                "dispersed_width_mm": bb,
                "geometric_slenderness": geometric_slenderness,
            },
            [capacity_check("5.13.2", nominal, d["bearing_action_kn"])],
            [
                "No transverse stiffeners; limit end widths to available web (Figure 5.13.1.1).",
                "RHS/SHS to AS/NZS 1163; combined bearing/bending needs separate 5.13.5 check.",
            ],
        )
    if op == "rhs_bearing_bending":
        rr = d["bearing_action_kn"] / d["design_bearing_capacity_kn"]
        mr = d["moment_action_knm"] / d["design_moment_capacity_knm"]
        wide = d["stiff_bearing_length_mm"] >= d["section_width_mm"] and (
            d["clear_web_depth_mm"] / d["web_thickness_mm"] <= 30
        )
        value, limit = (1.2 * rr + mr, 1.5) if wide else (0.8 * rr + mr, 1.0)
        return result(
            op,
            ["5.13.5"],
            {"interaction": value, "limit": limit},
            [
                {
                    "clause": "5.13.5",
                    "satisfied": rr <= 1 and mr <= 1 and value <= limit,
                    "utilisation": max(rr, mr, value / limit),
                },
            ],
            ["AS/NZS 1163 RHS/SHS only; separate section moment and bearing capacities required."],
        )
    if op == "load_bearing_stiffener":
        fy = min(d["web_yield_mpa"], d["stiffener_yield_mpa"])
        t, depth = d["web_thickness_mm"], d["clear_web_depth_mm"]
        if d["contact_stiffener_area_mm2"] > d["stiffener_area_mm2"]:
            raise ValueError("Contact stiffener area must not exceed the section area.")
        width_limit = min(17.5 * t / sqrt(d["web_yield_mpa"] / 250), d["panel_spacing_mm"] / 2)
        web_width = sum(
            min(width_limit, d[name])
            for name in ("available_web_width_left_mm", "available_web_width_right_mm")
        )
        area = d["stiffener_area_mm2"] + t * web_width
        length = (0.7 if d["both_flanges_rotation_restrained"] else 1) * depth
        alpha = buckling_alpha(length / d["radius_of_gyration_mm"], fy)
        yield_capacity = (
            d["web_bearing_yield_kn"]
            + d["contact_stiffener_area_mm2"] * d["stiffener_yield_mpa"] / 1000
        )
        buckling_capacity = alpha * area * fy / 1000
        outstand_limit = 15 * d["stiffener_thickness_mm"] / sqrt(d["stiffener_yield_mpa"] / 250)
        outstand_ok = (
            d["outer_edge_continuously_stiffened"] or d["stiffener_outstand_mm"] <= outstand_limit
        )
        return result(
            op,
            ["5.14.1", "5.14.2", "5.14.3"],
            {
                "effective_area_mm2": area,
                "effective_length_mm": length,
                "alpha_c": alpha,
                "bearing_yield_kn": yield_capacity,
                "bearing_buckling_kn": buckling_capacity,
                "outstand_limit_mm": outstand_limit,
            },
            [
                capacity_check("5.14.1", yield_capacity, d["bearing_action_kn"]),
                capacity_check("5.14.2", buckling_capacity, d["bearing_action_kn"]),
                {"clause": "5.14.3", "satisfied": outstand_ok},
            ],
            [
                "Effective-section buckling uses the lower web/stiffener yield stress.",
                "Radius must be calculated for the effective section parallel to web.",
                "Check fitting, fastener force transfer and torsional restraint under 5.14.4/5.",
            ],
        )
    if op == "transverse_stiffener":
        depth, spacing, t = d["clear_web_depth_mm"], d["panel_spacing_mm"], d["web_thickness_mm"]
        ratio = spacing / d["web_panel_depth_mm"]
        gamma = {"pair": 1, "single_angle": 1.8, "single_plate": 2.4}[d["stiffener_configuration"]]
        area_min = (
            0.5
            * gamma
            * d["web_area_mm2"]
            * (1 - d["shear_buckling_coefficient"])
            * (d["shear_action_kn"] / (0.9 * d["nominal_web_shear_kn"]))
            * (ratio / (sqrt(1 + ratio**2) * (sqrt(1 + ratio**2) + ratio)))
        )
        inertia_min = (
            0.75 * depth * t**3 if spacing / depth < sqrt(2) else 1.5 * depth**3 * t**3 / spacing**2
        )
        outstand_limit = 15 * d["stiffener_thickness_mm"] / sqrt(d["stiffener_yield_mpa"] / 250)
        shear_per_length = 0.0008 * t * t * d["web_yield_mpa"] / d["stiffener_outstand_mm"]
        nominal = d["nominal_stiffener_buckling_kn"] + d["nominal_web_buckling_no_tension_field_kn"]
        return result(
            op,
            ["5.15.3", "5.15.4", "5.15.5", "5.15.6", "5.15.8"],
            {
                "minimum_area_mm2": area_min,
                "minimum_second_moment_mm4": inertia_min,
                "outstand_limit_mm": outstand_limit,
                "connection_design_shear_kn_per_mm": shear_per_length,
            },
            [
                {"clause": "5.15.3", "satisfied": d["stiffener_area_mm2"] >= area_min},
                {"clause": "5.15.5", "satisfied": d["stiffener_second_moment_mm4"] >= inertia_min},
                {
                    "clause": "5.15.6",
                    "satisfied": d["outer_edge_continuously_stiffened"]
                    or d["stiffener_outstand_mm"] <= outstand_limit,
                },
                capacity_check("5.15.4", nominal, d["shear_action_kn"]),
            ],
            ["No external stiffener loads/moments; check end posts, geometry and fasteners."],
        )
    depth, t = d["web_depth_mm"], d["web_thickness_mm"]
    if d["location"] == "neutral_axis":
        minimum = depth * t**3
    else:
        ratio = d["stiffener_area_mm2"] / (depth * t)
        minimum = 4 * depth * t**3 * (1 + 4 * ratio * (1 + ratio))
    return result(
        op,
        ["5.16.2"],
        {"minimum_second_moment_mm4": minimum},
        [
            {"clause": "5.16.2", "satisfied": d["stiffener_second_moment_mm4"] >= minimum},
        ],
        ["Inertia about web face; assess location and continuous attachment under 5.16.1."],
    )
