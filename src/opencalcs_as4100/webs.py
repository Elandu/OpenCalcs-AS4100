# SPDX-License-Identifier: AGPL-3.0-only
"""Web geometry, bearing and stiffener checks, clauses 5.10 and 5.13 to 5.16."""

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

_WEB_THICKNESS_COMMON = {
    "operation": {"const": "web_minimum_thickness"},
    "clear_web_depth_mm": POSITIVE,
    "web_thickness_mm": POSITIVE,
    "web_yield_mpa": YIELD_STRESS,
}


def _web_minimum_thickness_schema():
    variants = [
        object_schema(
            {
                **_WEB_THICKNESS_COMMON,
                "design_case": {"const": "unstiffened"},
                "edge_condition": {"enum": ["both_flange_bounded", "one_longitudinal_edge_free"]},
                "geometry_verified": {"const": True},
            }
        ),
        object_schema(
            {
                **_WEB_THICKNESS_COMMON,
                "design_case": {"const": "transversely_stiffened"},
                "stiffener_spacing_mm": POSITIVE,
                "greatest_panel_depth_mm": POSITIVE,
                "stiffener_layout_verified": {"const": True},
            }
        ),
        object_schema(
            {
                **_WEB_THICKNESS_COMMON,
                "design_case": {"const": "longitudinal_and_transverse"},
                "stiffener_spacing_mm": POSITIVE,
                "d2_mm": POSITIVE,
                "neutral_axis_stiffener_set_present": {"type": "boolean"},
                "stiffener_layout_verified": {"const": True},
            }
        ),
        object_schema(
            {
                **_WEB_THICKNESS_COMMON,
                "design_case": {"const": "plastic_hinge"},
                "hinge_zone_load_kn": NONNEGATIVE,
                "design_web_shear_yield_capacity_kn": POSITIVE,
                "bearing_or_shear_within_half_depth_of_hinge_verified": {"type": "boolean"},
                "load_bearing_stiffeners_provided": {"type": "boolean"},
                "stiffeners_within_half_depth_verified": {"type": "boolean"},
                "stiffener_design_5_14_verified": {"type": "boolean"},
            }
        ),
    ]
    return {"oneOf": variants}


_BEARING = {
    "operation": {"const": "web_bearing"},
    "section_type": {"enum": ["i_or_channel", "rhs_shs"]},
    "web_thickness_mm": {"type": "number", "minimum": 3, "maximum": 1e6},
    "web_yield_mpa": YIELD_STRESS,
    "clear_web_depth_mm": POSITIVE,
    "bearing_width_at_flange_mm": POSITIVE,
    "bearing_width_at_neutral_axis_mm": POSITIVE,
    "flange_thickness_mm": POSITIVE,
    "distance_flange_to_neutral_axis_mm": POSITIVE,
    "bearing_geometry_verified": {"type": "boolean"},
    "restrained_flange_count": {"type": "integer", "enum": [1, 2]},
    "bearing_action_kn": NONNEGATIVE,
    "outside_radius_mm": POSITIVE,
    "stiff_bearing_length_mm": POSITIVE,
    "distance_to_member_end_mm": NONNEGATIVE,
}
SCHEMAS = {
    "web_minimum_thickness": _web_minimum_thickness_schema(),
    "web_opening_geometry": object_schema(
        {
            "operation": {"const": "web_opening_geometry"},
            "clear_web_depth_mm": POSITIVE,
            "opening_internal_dimension_mm": POSITIVE,
            "longitudinal_stiffeners_present": {"type": "boolean"},
            "adjacent_openings_present": {"type": "boolean"},
            "adjacent_opening_boundary_spacing_mm": NONNEGATIVE,
            "unstiffened_openings_at_cross_section": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10000,
            },
            "multiple_openings_rational_analysis_verified": {"type": "boolean"},
            "opening_geometry_verified": {"const": True},
        }
    ),
    "load_bearing_stiffener_requirement": object_schema(
        {
            "operation": {"const": "load_bearing_stiffener_requirement"},
            "design_compressive_bearing_force_kn": NONNEGATIVE,
            "design_web_bearing_capacity_kn": POSITIVE,
            "end_post_required_under_5_15_2_2": {"type": "boolean"},
            "load_bearing_stiffeners_provided": {"type": "boolean"},
        }
    ),
    "load_bearing_stiffener_attachment": object_schema(
        {
            "operation": {"const": "load_bearing_stiffener_attachment"},
            "design_bearing_force_kn": NONNEGATIVE,
            "design_force_share_to_web_kn": NONNEGATIVE,
            "web_connection_design_capacity_kn": POSITIVE,
            "tight_uniform_bearing_against_loaded_flange_verified": {"type": "boolean"},
            "flange_to_stiffener_connection_design_capacity_kn": POSITIVE,
            "concentrated_force_directly_over_support": {"type": "boolean"},
            "both_flanges_fitted_or_connected_verified": {"type": "boolean"},
        },
        [
            "operation",
            "design_bearing_force_kn",
            "design_force_share_to_web_kn",
            "web_connection_design_capacity_kn",
            "tight_uniform_bearing_against_loaded_flange_verified",
            "concentrated_force_directly_over_support",
        ],
    )
    | {
        "allOf": [
            {
                "if": {
                    "required": ["tight_uniform_bearing_against_loaded_flange_verified"],
                    "properties": {
                        "tight_uniform_bearing_against_loaded_flange_verified": {"const": False}
                    },
                },
                "then": {"required": ["flange_to_stiffener_connection_design_capacity_kn"]},
            },
            {
                "if": {
                    "required": ["concentrated_force_directly_over_support"],
                    "properties": {"concentrated_force_directly_over_support": {"const": True}},
                },
                "then": {"required": ["both_flanges_fitted_or_connected_verified"]},
            },
        ]
    },
    "web_side_reinforcement": object_schema(
        {
            "operation": {"const": "web_side_reinforcement"},
            "design_shear_share_kn": NONNEGATIVE,
            "side_plate_design_shear_capacity_kn": POSITIVE,
            "fastener_design_shear_capacity_to_web_kn": POSITIVE,
            "fastener_design_shear_capacity_to_flanges_kn": POSITIVE,
            "symmetry_effects_accounted": {"type": "boolean"},
        }
    ),
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
    )
    | {
        "allOf": [
            {
                "if": {
                    "required": ["section_type"],
                    "properties": {"section_type": {"const": "i_or_channel"}},
                },
                "then": {
                    "oneOf": [
                        {
                            "required": [
                                "bearing_width_at_flange_mm",
                                "bearing_width_at_neutral_axis_mm",
                            ]
                        },
                        {
                            "required": [
                                "stiff_bearing_length_mm",
                                "flange_thickness_mm",
                                "distance_flange_to_neutral_axis_mm",
                                "bearing_geometry_verified",
                            ]
                        },
                    ]
                },
            }
        ]
    },
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
            "torsional_end_restraint_required": {"type": "boolean"},
            "critical_flange_centroid_spacing_mm": POSITIVE,
            "critical_flange_thickness_mm": POSITIVE,
            "total_design_load_between_supports_kn": POSITIVE,
            "stiffener_pair_second_moment_about_web_centerline_mm4": POSITIVE,
        },
        [
            "operation",
            "web_bearing_yield_kn",
            "stiffener_area_mm2",
            "web_yield_mpa",
            "stiffener_yield_mpa",
            "contact_stiffener_area_mm2",
            "web_thickness_mm",
            "clear_web_depth_mm",
            "panel_spacing_mm",
            "radius_of_gyration_mm",
            "both_flanges_rotation_restrained",
            "available_web_width_left_mm",
            "available_web_width_right_mm",
            "stiffener_outstand_mm",
            "stiffener_thickness_mm",
            "outer_edge_continuously_stiffened",
            "bearing_action_kn",
        ],
    )
    | {
        "allOf": [
            {
                "if": {
                    "required": ["torsional_end_restraint_required"],
                    "properties": {"torsional_end_restraint_required": {"const": True}},
                },
                "then": {
                    "required": [
                        "critical_flange_centroid_spacing_mm",
                        "critical_flange_thickness_mm",
                        "total_design_load_between_supports_kn",
                        "stiffener_pair_second_moment_about_web_centerline_mm4",
                    ]
                },
                "else": {
                    "not": {
                        "anyOf": [
                            {"required": ["critical_flange_centroid_spacing_mm"]},
                            {"required": ["critical_flange_thickness_mm"]},
                            {"required": ["total_design_load_between_supports_kn"]},
                            {"required": ["stiffener_pair_second_moment_about_web_centerline_mm4"]},
                        ]
                    }
                },
            }
        ]
    },
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
    if op == "web_minimum_thickness":
        depth, fy, actual = (
            d["clear_web_depth_mm"],
            d["web_yield_mpa"],
            d["web_thickness_mm"],
        )
        factor = sqrt(fy / 250)
        if d["design_case"] == "unstiffened":
            denominator = 90 if d["edge_condition"] == "one_longitudinal_edge_free" else 180
            required = depth / denominator * factor
            clauses = ["5.10.1"]
            details = {"edge_condition": d["edge_condition"]}
        elif d["design_case"] == "transversely_stiffened":
            spacing = d["stiffener_spacing_mm"]
            panel_depth = d["greatest_panel_depth_mm"]
            if panel_depth > depth:
                raise ValueError("Greatest panel depth must not exceed the clear web depth.")
            ratio = spacing / depth
            if spacing / panel_depth > 3:
                required = depth / 180 * factor
                clauses = ["5.10.1", "5.10.4"]
                details = {
                    "stiffener_spacing_to_panel_depth_ratio": spacing / panel_depth,
                    "web_treated_as_unstiffened": True,
                }
            else:
                if ratio > 3:
                    raise ValueError(
                        "Transverse stiffener spacing is outside Clause 5.10.4 limits."
                    )
                if ratio <= 0.74:
                    required = depth / 270 * factor
                elif ratio < 1:
                    required = spacing / 200 * factor
                else:
                    required = depth / 200 * factor
                clauses = ["5.10.4"]
                details = {
                    "stiffener_spacing_to_web_depth_ratio": ratio,
                    "stiffener_spacing_to_panel_depth_ratio": spacing / panel_depth,
                    "web_treated_as_unstiffened": False,
                }
        elif d["design_case"] == "longitudinal_and_transverse":
            spacing = d["stiffener_spacing_mm"]
            ratio = spacing / depth
            if ratio > 2.4:
                raise ValueError(
                    "Longitudinal/transverse stiffener spacing exceeds Clause 5.10.5 limits."
                )
            if ratio < 0.74:
                required = depth / 340 * factor
            elif ratio < 1:
                required = spacing / 250 * factor
            else:
                required = depth / 250 * factor
            if d["neutral_axis_stiffener_set_present"]:
                if ratio > 1.5:
                    raise ValueError(
                        "The Clause 5.10.5 neutral-axis thickness equation applies only "
                        "when s/d1 is no greater than 1.5."
                    )
                required = max(required, depth / 400 * factor)
            clauses = ["5.10.5"]
            details = {
                "stiffener_spacing_to_web_depth_ratio": ratio,
                "compression_flange_stiffener_target_distance_mm": 0.2 * d["d2_mm"],
                "neutral_axis_stiffener_set_present": d["neutral_axis_stiffener_set_present"],
            }
        else:
            required = depth / 82 * factor
            trigger = (
                d["bearing_or_shear_within_half_depth_of_hinge_verified"]
                and d["hinge_zone_load_kn"] > 0.1 * d["design_web_shear_yield_capacity_kn"]
            )
            stiffener_condition = not trigger or (
                d["load_bearing_stiffeners_provided"]
                and d["stiffeners_within_half_depth_verified"]
                and d["stiffener_design_5_14_verified"]
            )
            clauses = ["5.10.6"]
            details = {"hinge_zone_stiffeners_required": trigger}

        thickness_check = {
            "clause": clauses[0],
            "required_thickness_mm": required,
            "provided_thickness_mm": actual,
            "satisfied": actual >= required,
        }
        checks = [thickness_check]
        if d["design_case"] == "plastic_hinge":
            checks.append(
                {
                    "clause": "5.10.6 load-bearing stiffener trigger",
                    "satisfied": stiffener_condition,
                }
            )
        return result(
            op,
            clauses,
            {
                "design_case": d["design_case"],
                "required_web_thickness_mm": required,
                "provided_web_thickness_mm": actual,
                "web_thickness_adequate": actual >= required,
                **details,
            },
            checks,
            [
                "This is a web thickness/arrangement check only; verify shear, bearing, "
                "stiffener resistance and load transfer under the applicable clauses.",
                "A lower thickness justified by rational analysis under 5.10.1 requires "
                "a separate verified analysis.",
            ],
        )
    if op == "web_opening_geometry":
        dimension, depth = d["opening_internal_dimension_mm"], d["clear_web_depth_mm"]
        ratio = dimension / depth
        permitted = 0.33 if d["longitudinal_stiffeners_present"] else 0.10
        stiffener_condition = (
            d["unstiffened_openings_at_cross_section"] <= 1
            or d["multiple_openings_rational_analysis_verified"]
        )
        checks = [
            {
                "clause": "5.10.7(b)" if d["longitudinal_stiffeners_present"] else "5.10.7(a)",
                "opening_dimension_to_web_depth_ratio": ratio,
                "permitted_ratio": permitted,
                "satisfied": ratio <= permitted,
            },
            {
                "clause": "5.10.7 multiple openings at one cross-section",
                "satisfied": stiffener_condition,
            },
        ]
        if d["adjacent_openings_present"]:
            required_spacing = 3 * dimension
            checks.append(
                {
                    "clause": "5.10.7 adjacent opening spacing",
                    "required_boundary_spacing_mm": required_spacing,
                    "provided_boundary_spacing_mm": d["adjacent_opening_boundary_spacing_mm"],
                    "satisfied": d["adjacent_opening_boundary_spacing_mm"] >= required_spacing,
                }
            )
        return result(
            op,
            ["5.10.7"],
            {
                "opening_dimension_to_web_depth_ratio": ratio,
                "permitted_ratio": permitted,
                "required_adjacent_opening_spacing_mm": (
                    3 * dimension if d["adjacent_openings_present"] else None
                ),
            },
            checks,
            [
                "Applies only to unstiffened web openings meeting the geometric limits. "
                "Stiffened openings and castellated members require rational analysis.",
                "For adjacent openings of different sizes, use the greater internal "
                "dimension when checking their boundary spacing.",
                "This geometry check does not calculate the member's reduced section or "
                "web capacity at an opening.",
            ],
        )
    if op == "load_bearing_stiffener_requirement":
        force = d["design_compressive_bearing_force_kn"]
        web_capacity = d["design_web_bearing_capacity_kn"]
        required_by_bearing = force > web_capacity
        required_by_end_post = d["end_post_required_under_5_15_2_2"]
        required = required_by_bearing or required_by_end_post
        return result(
            op,
            ["5.10.2"],
            {
                "stiffeners_required": required,
                "required_by_web_bearing_capacity": required_by_bearing,
                "required_to_form_end_post": required_by_end_post,
                "design_compressive_bearing_force_kn": force,
                "design_web_bearing_capacity_kn": web_capacity,
            },
            [
                {
                    "clause": "5.10.2 load-bearing stiffener provision",
                    "satisfied": not required or d["load_bearing_stiffeners_provided"],
                }
            ],
            [
                "Use the design bearing capacity of the web alone from Clause 5.13.2; "
                "the end-post requirement under Clause 5.15.2.2 is an assessed input.",
                "This trigger does not calculate load-bearing stiffener resistance, "
                "detailing or force transfer under Clause 5.14.",
            ],
        )
    if op == "web_side_reinforcement":
        share = d["design_shear_share_kn"]
        plate_capacity = d["side_plate_design_shear_capacity_kn"]
        web_transfer = d["fastener_design_shear_capacity_to_web_kn"]
        flange_transfer = d["fastener_design_shear_capacity_to_flanges_kn"]
        available = min(plate_capacity, web_transfer, flange_transfer)
        return result(
            op,
            ["5.10.3"],
            {
                "design_shear_share_kn": share,
                "maximum_supported_shear_share_kn": available,
                "side_plate_design_shear_capacity_kn": plate_capacity,
                "fastener_design_shear_capacity_to_web_kn": web_transfer,
                "fastener_design_shear_capacity_to_flanges_kn": flange_transfer,
            },
            [
                {
                    "clause": "5.10.3 side-plate shear resistance",
                    "satisfied": share <= plate_capacity,
                },
                {
                    "clause": "5.10.3 fastener transfer to web",
                    "satisfied": share <= web_transfer,
                },
                {
                    "clause": "5.10.3 fastener transfer to flanges",
                    "satisfied": share <= flange_transfer,
                },
                {
                    "clause": "5.10.3 symmetry effects",
                    "satisfied": d["symmetry_effects_accounted"],
                },
            ],
            [
                "Enter the design shear assigned to the side plates after accounting "
                "for any lack of symmetry.",
                "Plate and fastener design capacities are supplied inputs; their "
                "resistance and connection design are not calculated here.",
            ],
        )
    if op == "load_bearing_stiffener_attachment":
        bearing_force = d["design_bearing_force_kn"]
        web_share = d["design_force_share_to_web_kn"]
        web_capacity = d["web_connection_design_capacity_kn"]
        tight_fit = d["tight_uniform_bearing_against_loaded_flange_verified"]
        flange_capacity = d.get("flange_to_stiffener_connection_design_capacity_kn")
        flange_transfer_ok = tight_fit or (
            flange_capacity is not None and flange_capacity >= bearing_force
        )
        both_flanges_ok = not d["concentrated_force_directly_over_support"] or d.get(
            "both_flanges_fitted_or_connected_verified", False
        )
        return result(
            op,
            ["5.14.4"],
            {
                "maximum_supported_web_force_share_kn": web_capacity,
                "design_force_share_to_web_kn": web_share,
                "flange_to_stiffener_connection_capacity_kn": flange_capacity,
            },
            [
                {
                    "clause": "5.14.4 tight flange fit or concentrated-force connection",
                    "satisfied": flange_transfer_ok,
                },
                {
                    "clause": "5.14.4 both-flange provision at support",
                    "satisfied": both_flanges_ok,
                },
                {
                    "clause": "5.14.4 connection force transfer to web",
                    "design_capacity_kn": web_capacity,
                    "action_kn": web_share,
                    "utilisation": web_share / web_capacity,
                    "satisfied": web_share <= web_capacity,
                },
            ],
            [
                "Weld and bolt design capacities are supplied from the applicable Clause 9 checks.",
                "Verify the stated flange fit and connection arrangement against actual details.",
            ],
        )
    if op == "web_bearing":
        t, fy, depth = d["web_thickness_mm"], d["web_yield_mpa"], d["clear_web_depth_mm"]
        if d["section_type"] == "i_or_channel":
            manual_widths = (
                "bearing_width_at_flange_mm" in d,
                "bearing_width_at_neutral_axis_mm" in d,
            )
            geometry_inputs = (
                "flange_thickness_mm" in d,
                "distance_flange_to_neutral_axis_mm" in d,
                "bearing_geometry_verified" in d,
            )
            if all(manual_widths) and not any(geometry_inputs):
                bbf, bb = d["bearing_width_at_flange_mm"], d["bearing_width_at_neutral_axis_mm"]
                geometry_check = None
            elif not any(manual_widths) and all(geometry_inputs):
                tf = d["flange_thickness_mm"]
                distance_to_na = d["distance_flange_to_neutral_axis_mm"]
                if "stiff_bearing_length_mm" not in d:
                    raise ValueError("Geometric dispersion requires stiff_bearing_length_mm.")
                if distance_to_na > depth:
                    raise ValueError(
                        "Distance to the neutral axis must not exceed the clear web depth."
                    )
                bbf = d["stiff_bearing_length_mm"] + 5 * tf
                bb = bbf + 2 * distance_to_na
                geometry_check = {
                    "clause": "5.13.1 bearing-dispersion geometry verified",
                    "satisfied": d["bearing_geometry_verified"],
                }
            else:
                raise ValueError(
                    "I/channel bearing requires both assessed widths or the complete "
                    "Clause 5.13.1 geometry input set."
                )
            if any(
                name in d
                for name in [
                    "outside_radius_mm",
                    "distance_to_member_end_mm",
                ]
            ):
                raise ValueError("Hollow-section inputs cannot be used with an I/channel section.")
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
                **(
                    {
                        "bearing_width_at_flange_mm": bbf,
                        "bearing_width_at_neutral_axis_mm": bb,
                        "dispersion_method": "clause_5_13_1_geometry",
                    }
                    if d["section_type"] == "i_or_channel"
                    else {}
                ),
            },
            [
                capacity_check("5.13.2", nominal, d["bearing_action_kn"]),
                *(
                    [geometry_check]
                    if d["section_type"] == "i_or_channel" and geometry_check
                    else []
                ),
            ],
            [
                "No transverse stiffeners; limit end widths to available web (Figure 5.13.1.1).",
                "Clause 5.13.1 automatic dispersion uses b_bf = b_s + 5 t_f and adds "
                "twice the flange-to-neutral-axis distance; confirm the figure geometry applies.",
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
        checks = [
            capacity_check("5.14.1", yield_capacity, d["bearing_action_kn"]),
            capacity_check("5.14.2", buckling_capacity, d["bearing_action_kn"]),
            {"clause": "5.14.3", "satisfied": outstand_ok},
        ]
        clauses = ["5.14.1", "5.14.2", "5.14.3"]
        values = {
            "effective_area_mm2": area,
            "effective_length_mm": length,
            "alpha_c": alpha,
            "bearing_yield_kn": yield_capacity,
            "bearing_buckling_kn": buckling_capacity,
            "outstand_limit_mm": outstand_limit,
        }
        if d.get("torsional_end_restraint_required", False):
            slenderness = length / d["radius_of_gyration_mm"]
            alpha_t_raw = 230 / slenderness - 0.60
            alpha_t = min(4, max(0, alpha_t_raw))
            required_inertia = (
                (alpha_t / 1000)
                * d["critical_flange_centroid_spacing_mm"] ** 3
                * d["critical_flange_thickness_mm"]
                * d["bearing_action_kn"]
                / d["total_design_load_between_supports_kn"]
            )
            supplied_inertia = d["stiffener_pair_second_moment_about_web_centerline_mm4"]
            values.update(
                {
                    "stiffener_slenderness": slenderness,
                    "torsional_restraint_factor_raw": alpha_t_raw,
                    "torsional_restraint_factor": alpha_t,
                    "required_stiffener_pair_second_moment_mm4": required_inertia,
                }
            )
            checks.append(
                {
                    "clause": "5.14.5 torsional end restraint",
                    "satisfied": supplied_inertia >= required_inertia,
                }
            )
            clauses.append("5.14.5")
        return result(
            op,
            clauses,
            values,
            checks,
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
