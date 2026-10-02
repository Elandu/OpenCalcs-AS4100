# SPDX-License-Identifier: AGPL-3.0-only
"""Further member provisions with explicit external analysis prerequisites."""

from math import pi, sqrt

from .validation import (
    NONNEGATIVE as N,
)
from .validation import (
    POSITIVE as P,
)
from .validation import (
    YIELD_STRESS as FY,
)
from .validation import (
    capacity_check,
    object_schema,
    result,
    validate,
)


def _schema(operation, properties):
    return object_schema({"operation": {"const": operation}, **properties})


BOOL = {"type": "boolean"}
VERIFIED = {"const": True}
BETA = {"type": "number", "minimum": -1, "maximum": 1}
SCHEMAS = {
    "varying_compression": _schema(
        "varying_compression",
        {
            "minimum_section_capacity_kn": P,
            "elastic_buckling_load_kn": P,
            "section_constant": {"enum": [-1, -0.5, 0, 0.5, 1]},
            "action_kn": N,
            "flexural_mode_verified": VERIFIED,
        },
    ),
    "buckling_analysis_bending": _schema(
        "buckling_analysis_bending",
        {
            "section_capacity_knm": P,
            "elastic_buckling_moment_knm": P,
            "moment_factor": {"type": "number", "exclusiveMinimum": 0, "maximum": 2.5},
            "end_configuration": {"enum": ["both_restrained", "one_unrestrained"]},
            "restraint_and_load_model_verified": VERIFIED,
            "action_knm": N,
        },
    ),
    "one_unrestrained_table_bending": _schema(
        "one_unrestrained_table_bending",
        {
            "section_capacity_knm": P,
            "reference_buckling_moment_knm": P,
            "moment_distribution": {"enum": ["uniform_end_moment", "tip_force", "uniform_load"]},
            "action_knm": N,
            "one_end_restraint_and_continuity_verified": VERIFIED,
            "reference_buckling_moment_verified": VERIFIED,
        },
    ),
    "nonprincipal_bending": _schema(
        "nonprincipal_bending",
        {
            "section_axial_capacity_kn": P,
            "section_moment_x_knm": P,
            "section_moment_y_knm": P,
            "reduced_member_moment_x_knm": P,
            "reduced_member_moment_y_knm": P,
            "axial_action_kn": N,
            "moment_x_knm": N,
            "moment_y_knm": N,
            "deflections_constrained": BOOL,
            "rational_analysis_verified": VERIFIED,
        },
    ),
    "plastic_in_plane": _schema(
        "plastic_in_plane",
        {
            "compact_doubly_symmetric_i_verified": VERIFIED,
            "section_axial_capacity_kn": P,
            "section_moment_x_knm": P,
            "section_moment_y_knm": P,
            "axial_action_kn": N,
            "axial_mode": {"enum": ["compression", "tension"]},
            "moment_x_knm": N,
            "moment_y_knm": N,
            "elastic_buckling_load_actual_length_kn": P,
            "beta_m": BETA,
            "web_clear_depth_mm": P,
            "web_thickness_mm": P,
            "yield_mpa": FY,
        },
    ),
    "built_up_compression": _schema(
        "built_up_compression",
        {
            "construction": {"enum": ["laced", "battened", "back_to_back"]},
            "section_capacity_kn": P,
            "member_capacity_kn": P,
            "modified_member_slenderness": P,
            "axial_action_kn": N,
            "integral_slenderness_perpendicular": P,
            "integral_slenderness_parallel": P,
            "component_slenderness": P,
            "number_of_bays": {"type": "integer", "minimum": 1, "maximum": 1000000},
            "similar_symmetric_components_verified": VERIFIED,
        },
    ),
    "lacing": _schema(
        "lacing",
        {
            "mode": {"enum": ["single", "double_connected"]},
            "member_mode": {"enum": ["compression", "tension"]},
            "angle_degrees": {"type": "number", "minimum": 0, "maximum": 90},
            "inner_connection_distance_mm": P,
            "radius_mm": P,
            "tie_type": {"enum": ["end", "intermediate"]},
            "component_connection_centroid_distance_mm": P,
            "tie_width_mm": P,
            "tie_thickness_mm": P,
            "tie_inner_connection_distance_mm": P,
            "tie_edge_stiffened": BOOL,
            "tie_edge_stiffener_slenderness": N,
        },
    ),
    "batten": _schema(
        "batten",
        {
            "type": {"enum": ["end", "intermediate"]},
            "member_mode": {"enum": ["compression", "tension"]},
            "centroid_distance_mm": P,
            "narrower_component_width_mm": P,
            "radius_mm": P,
            "width_mm": P,
            "thickness_mm": P,
            "inner_connection_distance_mm": P,
            "edge_stiffened": BOOL,
            "edge_stiffener_slenderness": N,
            "transverse_shear_kn": N,
            "longitudinal_spacing_mm": P,
            "connection_centroid_distance_mm": P,
            "parallel_planes": {"type": "integer", "minimum": 1, "maximum": 1000000},
            "effective_end_width_mm": P,
        },
    ),
    "pin_tension_member": _schema(
        "pin_tension_member",
        {
            "thickness_mm": P,
            "hole_to_edge_distance_mm": P,
            "internal_nut_clamped_ply": BOOL,
            "net_area_beyond_hole_mm2": P,
            "net_area_perpendicular_mm2": P,
            "required_member_net_area_mm2": P,
            "pin_plates_distribute_load_without_eccentricity_verified": VERIFIED,
        },
    ),
    "restraint_action": _schema(
        "restraint_action",
        {
            "type": {"enum": ["lateral_flange", "twist", "compression"]},
            "connected_force_kn": N,
            "beyond_forces_kn": {"type": "array", "items": N, "maxItems": 6},
            "analysis_restraint_force_kn": N,
        },
    ),
    "separator_diaphragm": _schema(
        "separator_diaphragm",
        {
            "device_type": {"enum": ["separator", "diaphragm"]},
            "member_count": {"type": "integer", "minimum": 2, "maximum": 1000000},
            "device_count": {"type": "integer", "minimum": 1, "maximum": 1000000},
            "maximum_compression_flange_force_kn": N,
            "external_vertical_force_transfer_required": BOOL,
            "side_by_side_i_sections_or_channels_verified": VERIFIED,
        },
    ),
    "angle_eccentricity": _schema(
        "angle_eccentricity",
        {
            "arrangement": {"enum": ["same_side", "opposite_sides"]},
            "compression_centroid_offset_mm": N,
            "tension_centroid_offset_mm": N,
            "leg_thickness_mm": P,
            "axial_action_kn": N,
            "rational_analysis_moment_knm": N,
        },
    ),
}
INPUT_SCHEMA = {"oneOf": list(SCHEMAS.values())}
OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "standard",
        "operation",
        "clauses",
        "values",
        "checks",
        "checked_conditions_satisfied",
        "full_standard_compliance",
        "limitations",
    ],
    "properties": {"full_standard_compliance": {"const": False}},
}


def _limit(clause, value, limit):
    return {
        "clause": clause,
        "value": value,
        "limit": limit,
        "utilisation": value / limit if limit > 0 else None,
        "satisfied": value <= limit,
    }


def _minimum(clause, actual, minimum):
    return {
        "clause": clause,
        "actual": actual,
        "required_minimum": minimum,
        "satisfied": actual >= minimum,
    }


def _reduced_check(clause, moment, nominal):
    if nominal <= 0:
        return {
            "clause": clause,
            "design_capacity": 0,
            "action": moment,
            "utilisation": None,
            "satisfied": moment == 0,
        }
    return capacity_check(clause, nominal, moment)


def run_advanced_members(inputs):
    d = validate(inputs, INPUT_SCHEMA)
    op = d["operation"]
    if op == "varying_compression":
        ns, nom = d["minimum_section_capacity_kn"], d["elastic_buckling_load_kn"]
        ln = 90 * sqrt(ns / nom)
        aa = 2100 * (ln - 13.5) / (ln * ln - 15.3 * ln + 2050)
        lam = max(0, ln + aa * d["section_constant"])
        q, eta = (lam / 90) ** 2, max(0, 0.00326 * (lam - 13.5))
        a = 1 + q + eta
        alpha = min(1, 2 / (a + sqrt(max(0, a * a - 4 * q))))
        nc = alpha * ns
        return result(
            op,
            ["6.3.3", "6.3.4"],
            {
                "modified_slenderness": ln,
                "reduction": alpha,
                "member_capacity_kn": nc,
            },
            [capacity_check("6.3.4", nc, d["action_kn"])],
            [
                "Minimum section capacity must include every cross-section and hole deduction.",
                "Elastic flexural buckling load requires rational analysis of actual "
                "varying section.",
                "Assess both axes separately and select applicable Table 6.3.3(A/B) "
                "section constant.",
            ],
        )
    if op == "buckling_analysis_bending":
        ms, mob = d["section_capacity_knm"], d["elastic_buckling_moment_knm"]
        am = d["moment_factor"]
        # For 5.6.2(ii), no moment-factor enhancement multiplies alpha_s.
        if d["end_configuration"] == "one_unrestrained":
            if am != 1:
                raise ValueError("5.6.2(ii) uses elastic buckling moment directly and factor 1.")
            moa = mob
        else:
            moa = mob / am
        ratio = ms / moa
        reduction = 1.8 / (sqrt(ratio * ratio + 3) + ratio)
        mb = min(ms, am * reduction * ms)
        return result(
            op,
            ["5.6.2", "5.6.4"],
            {
                "reference_analysis_moment_knm": moa,
                "reduction": reduction,
                "member_capacity_knm": mb,
            },
            [capacity_check("5.6", mb, d["action_knm"])],
            [
                "External elastic flexural-torsional buckling analysis must model "
                "supports, restraints and loading.",
                "One-unrestrained-end segment requires other end full/partial restraint"
                " and lateral continuity/rotation restraint.",
                "Both-restrained path uses Moa=Mob/alpha_m under 5.6.4; moment factor "
                "needs 5.6.1.1 assessment.",
            ],
        )
    if op == "one_unrestrained_table_bending":
        factors = {"uniform_end_moment": 0.25, "tip_force": 1.25, "uniform_load": 2.25}
        am = factors[d["moment_distribution"]]
        ms, mo = d["section_capacity_knm"], d["reference_buckling_moment_knm"]
        ratio = ms / mo
        reduction = 1.8 / (sqrt(ratio * ratio + 3) + ratio)
        mb = min(ms, am * reduction * ms)
        return result(
            op,
            ["5.6.1.1", "5.6.2", "Table 5.6.2"],
            {
                "moment_factor": am,
                "reduction": reduction,
                "member_capacity_knm": mb,
            },
            [capacity_check("5.6.2(i)", mb, d["action_knm"])],
            [
                "Only the three Table 5.6.2 loading and moment-distribution cases "
                "are represented; combined or different cases need separate assessment.",
                "One end must be fully or partially restrained and laterally continuous "
                "or restrained against lateral rotation; the opposite end is unrestrained.",
                "Reference buckling moment Mo must be determined from 5.6.1.1(3) "
                "using effective length from 5.6.3 and eligible section properties.",
            ],
        )
    if op == "nonprincipal_bending":
        n = d["axial_action_kn"]
        mx, my = d["moment_x_knm"], d["moment_y_knm"]
        section = n / (0.9 * d["section_axial_capacity_kn"]) + (
            mx / (0.9 * d["section_moment_x_knm"]) + my / (0.9 * d["section_moment_y_knm"])
        )
        member = (mx / (0.9 * d["reduced_member_moment_x_knm"])) ** 1.4 + (
            my / (0.9 * d["reduced_member_moment_y_knm"])
        ) ** 1.4
        checks = [_limit("8.3.4", section, 1)]
        if not d["deflections_constrained"]:
            checks.append(_limit("8.4.5", member, 1))
        return result(
            op,
            ["5.7", "8.3.4", "8.4.5"],
            {
                "section_interaction": section,
                "member_interaction": member,
            },
            checks,
            [
                "Principal-axis moments and restraint forces must come from rational analysis.",
                "Reduced member capacities must already include axial and lateral-"
                "buckling reductions.",
                "Constrained path requires continuous restraints preventing lateral "
                "deflection under 5.7.1.",
            ],
        )
    if op == "plastic_in_plane":
        ns, n = d["section_axial_capacity_kn"], d["axial_action_kn"]
        ratio, beta = n / (0.9 * ns), d["beta_m"]
        web_lambda = d["web_clear_depth_mm"] / d["web_thickness_mm"] * sqrt(d["yield_mpa"] / 250)
        buckling_ratio = sqrt(ns / d["elastic_buckling_load_actual_length_kn"])
        if ratio <= 0.15:
            member_limit = ((0.6 + 0.4 * beta) / buckling_ratio) ** 2
        else:
            member_limit = (1 + beta - buckling_ratio) / (1 + beta + buckling_ratio)
        web_limit = (
            1
            if web_lambda <= 25
            else min(1, 1.91 - web_lambda / 27.4)
            if web_lambda < 45
            else 0.6 - web_lambda / 137
        )
        mrx = min(d["section_moment_x_knm"], 1.18 * d["section_moment_x_knm"] * max(0, 1 - ratio))
        mry = min(
            d["section_moment_y_knm"], 1.19 * d["section_moment_y_knm"] * max(0, 1 - ratio**2)
        )
        checks = [
            _limit("8.4.3.4 axial", ratio, 1),
            _reduced_check("8.4.3.4 x", d["moment_x_knm"], mrx),
            _reduced_check("8.4.3.4 y", d["moment_y_knm"], mry),
        ]
        if d["moment_x_knm"] and d["moment_y_knm"]:
            raise ValueError("Plastic in-plane operation is uniaxial only.")
        if d["axial_mode"] == "compression":
            checks.extend(
                [
                    _limit("8.4.3.2", ratio, member_limit),
                    _limit("8.4.3.3", ratio, web_limit),
                    _limit("8.4.3.3 plastic hinge eligibility", web_lambda, 82),
                ]
            )
        return result(
            op,
            ["8.4.3"],
            {
                "axial_ratio": ratio,
                "member_ratio_limit": member_limit,
                "web_slenderness": web_lambda,
                "web_ratio_limit": web_limit,
                "reduced_moment_x_knm": mrx,
                "reduced_moment_y_knm": mry,
            },
            checks,
            [
                "Compact doubly symmetric I-sections only; structure must satisfy "
                "plastic analysis provisions 4.5.",
                "No1 uses actual member length and inertia about bending axis.",
                "beta_m is positive for reverse curvature; lateral plastic-hinge "
                "restraints need 4.5.5.",
            ],
        )
    if op == "built_up_compression":
        ns, nc, n = d["section_capacity_kn"], d["member_capacity_kn"], d["axial_action_kn"]
        if nc > ns:
            raise ValueError("Member capacity cannot exceed section capacity.")
        ln, component = d["modified_member_slenderness"], d["component_slenderness"]
        transverse = max(0.01 * n, pi * (ns / nc - 1) * n / ln)
        perpendicular, parallel = (
            d["integral_slenderness_perpendicular"],
            d["integral_slenderness_parallel"],
        )
        if d["construction"] == "laced":
            effective_perpendicular = max(perpendicular, 1.4 * component)
            effective_parallel = max(parallel, 1.4 * component)
            limit = min(50, 0.6 * min(effective_perpendicular, effective_parallel))
        else:
            effective_perpendicular = sqrt(perpendicular**2 + component**2)
            effective_parallel = max(parallel, 1.4 * component)
            limit = min(50, 0.6 * min(effective_perpendicular, effective_parallel))
        checks = [_limit("6.4 main component", component, limit)]
        if d["construction"] == "back_to_back":
            checks.append(_minimum("6.5 minimum bays", d["number_of_bays"], 3))
        return result(
            op,
            ["6.4.1", "6.4.2", "6.4.3", "6.5"],
            {
                "transverse_design_shear_kn": transverse,
                "effective_slenderness_perpendicular": effective_perpendicular,
                "effective_slenderness_parallel": effective_parallel,
                "component_slenderness_limit": limit,
                "back_to_back_connection_longitudinal_shear_kn": 0.25 * transverse * component,
            },
            checks,
            [
                "Recalculate member capacity and lambda_n from reported effective "
                "slenderness before design-force use.",
                "Back-to-back path limited to similar symmetric angle/channel/tee pairs"
                " and eligible spacing/packing.",
                "Approximately equal bays, end fasteners, tie plates and torsional "
                "effects need separate assessment.",
            ],
        )
    if op == "lacing":
        double = d["mode"] == "double_connected"
        le = d["inner_connection_distance_mm"] * (0.7 if double else 1)
        slenderness = le / d["radius_mm"]
        compression = d["member_mode"] == "compression"
        limits = (40, 50) if double else (50, 70)
        required_width = d["component_connection_centroid_distance_mm"] * (
            1 if d["tie_type"] == "end" else 0.75
        )
        thickness = (0.02 if compression else 0.017) * d["tie_inner_connection_distance_mm"]
        thickness_ok = d["tie_edge_stiffened"] and d["tie_edge_stiffener_slenderness"] < 170
        return result(
            op,
            ["6.4.2.3", "6.4.2.4", "6.4.2.5", "6.4.2.7", "7.4.4"],
            {
                "effective_length_mm": le,
                "slenderness": slenderness,
                "required_tie_width_mm": required_width,
                "required_tie_thickness_mm": thickness,
            },
            [
                _limit("lacing slenderness", slenderness, 140 if compression else 210),
                {"clause": "6.4.2.3", "satisfied": limits[0] <= d["angle_degrees"] <= limits[1]},
                _minimum("tie width", d["tie_width_mm"], required_width),
                {
                    "clause": "tie thickness",
                    "satisfied": thickness_ok or d["tie_thickness_mm"] >= thickness,
                },
            ],
            [
                "Double lacing length reduction requires crossing weld/fastener connection.",
                "Tie plates require end/interruption/member-connection placement and "
                "batten force assessment.",
                "Opposed lacing and transverse members require 6.4.2.6 torsional-effect"
                " assessment.",
            ],
        )
    if op == "batten":
        end = d["type"] == "end"
        compression = d["member_mode"] == "compression"
        le = d["centroid_distance_mm"] * (1 if end else 0.7)
        width = max(
            d["centroid_distance_mm"] * (1 if end else 0.5),
            d["narrower_component_width_mm"] * (1 if end else 2),
        )
        if not compression and not end:
            width = 0.5 * d["effective_end_width_mm"]
        thickness = (0.02 if compression else 0.017) * d["inner_connection_distance_mm"]
        thickness_ok = d["edge_stiffened"] and d["edge_stiffener_slenderness"] <= 170
        shear = (
            d["transverse_shear_kn"]
            * d["longitudinal_spacing_mm"]
            / (d["parallel_planes"] * d["connection_centroid_distance_mm"])
        )
        moment = (
            d["transverse_shear_kn"]
            * d["longitudinal_spacing_mm"]
            / (2 * d["parallel_planes"] * 1000)
        )
        return result(
            op,
            ["6.4.3.3", "6.4.3.4", "6.4.3.5", "6.4.3.6", "6.4.3.7", "7.4.5"],
            {
                "effective_length_mm": le,
                "slenderness": le / d["radius_mm"],
                "minimum_width_mm": width,
                "minimum_thickness_mm": thickness,
                "connection_longitudinal_shear_kn": shear if compression else None,
                "connection_moment_knm": moment if compression else None,
            },
            [
                _limit("6.4.3.4", le / d["radius_mm"], 180),
                _minimum("batten width", d["width_mm"], width),
                {
                    "clause": "batten thickness",
                    "satisfied": thickness_ok or d["thickness_mm"] >= thickness,
                },
            ],
            [
                "Simultaneous connection shear and moment require section and connection design.",
                "Tension-member bolted battens need at least two bolts; 6.4.3.7 "
                "compression-force formula does not apply.",
            ],
        )
    if op == "pin_tension_member":
        required = d["required_member_net_area_mm2"]
        thickness = 0.25 * d["hole_to_edge_distance_mm"]
        return result(
            op,
            ["7.5"],
            {
                "minimum_thickness_mm": thickness,
                "minimum_net_area_beyond_mm2": required,
                "minimum_net_area_perpendicular_mm2": 1.33 * required,
            },
            [
                {
                    "clause": "7.5(a)",
                    "satisfied": d["internal_nut_clamped_ply"] or d["thickness_mm"] >= thickness,
                },
                _minimum("7.5(b)", d["net_area_beyond_hole_mm2"], required),
                _minimum("7.5(c)", d["net_area_perpendicular_mm2"], 1.33 * required),
            ],
            [
                "Pin capacity is assessed separately under 9.4.",
                "Beyond-hole net area must be checked for all planes parallel to or "
                "within 45 degrees of member axis.",
            ],
        )
    if op == "restraint_action":
        beyond = d["beyond_forces_kn"]
        if d["type"] == "twist" and beyond:
            raise ValueError("Twist restraint operation applies to one member's critical flange.")
        minimum = 0.025 * d["connected_force_kn"] + 0.0125 * sum(beyond)
        force = max(minimum, d["analysis_restraint_force_kn"])
        return result(
            op,
            ["5.4.3", "6.6"],
            {"minimum_transverse_force_kn": minimum, "design_restraint_force_kn": force},
            [],
            [
                "Connected force is critical flange force for bending or local maximum "
                "compression force for compression.",
                "Parallel sequence includes connected member plus at most six connected"
                " members beyond.",
                "Analysis force includes design loads/notional loads and the full route"
                " to anchorage/reaction points.",
                "Grouping closer restraints, stiffness, rotational slip and force "
                "transfer remain engineering assessments.",
            ],
        )
    if op == "separator_diaphragm":
        if d["device_type"] == "separator" and d["external_vertical_force_transfer_required"]:
            raise ValueError("5.8 requires diaphragms for external vertical force transfer.")
        transverse_force = 0.025 * d["maximum_compression_flange_force_kn"]
        return result(
            op,
            ["5.8"],
            {
                "minimum_total_transverse_force_kn": transverse_force,
                "minimum_transverse_force_per_device_kn": transverse_force / d["device_count"],
            },
            [],
            [
                "Applies to two or more side-by-side I-sections or channels acting "
                "together in external-load distribution.",
                "Separators must comprise spacers and through bolts; assess any "
                "external transverse forces in addition to the stated minimum.",
                "Diaphragms and fastenings must distribute applied external vertical "
                "and transverse forces and resist resulting shear in addition to the "
                "stated minimum.",
                "Only the 5.8 minimum transverse force is shared equally. External "
                "force distribution, resulting shear and device capacities require "
                "separate design.",
            ],
        )
    # Geometry-only primitive: does not invent the ambiguous interaction printed in 8.4.6.
    if d["arrangement"] == "same_side":
        eccentricity = d["compression_centroid_offset_mm"] - d["leg_thickness_mm"] / 2
        if eccentricity < 0:
            raise ValueError("Same-side centroid offset must be at least half leg thickness.")
    else:
        eccentricity = d["compression_centroid_offset_mm"] + d["tension_centroid_offset_mm"]
    minimum_moment = d["axial_action_kn"] * eccentricity / 1000
    return result(
        op,
        ["8.4.6"],
        {
            "eccentricity_mm": eccentricity,
            "minimum_design_moment_knm": minimum_moment,
            "design_moment_knm": max(minimum_moment, d["rational_analysis_moment_knm"]),
        },
        [],
        [
            "Only the Figure 8.4.6 eccentricity and minimum moment requirement is calculated.",
            "Special angle interaction requires separately verified interpretation "
            "of 8.4.6; no capacity assessment is produced.",
            "Angles must be double-bolted or welded and loading through one leg "
            "must match the figure.",
        ],
    )
