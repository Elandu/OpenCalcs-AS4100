# SPDX-License-Identifier: AGPL-3.0-only
"""Further member provisions with explicit external analysis prerequisites."""

from math import isfinite, pi, sqrt

from .standards import ELASTIC_MODULUS_MPA, SHEAR_MODULUS_MPA
from .validation import (
    NONNEGATIVE as N,
)
from .validation import (
    POSITIVE as P,
)
from .validation import (
    SIGNED as S,
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


def _full_lateral_restraint_schema():
    common = {
        "segment_length_mm": P,
        "yield_strength_mpa": FY,
        "section_properties_verified": VERIFIED,
        "both_ends_restrained_verified": VERIFIED,
    }
    sections = {
        "equal_flanged_i": (
            {"radius_of_gyration_y_mm": P},
            ["radius_of_gyration_y_mm"],
        ),
        "equal_flanged_channel": (
            {"radius_of_gyration_y_mm": P},
            ["radius_of_gyration_y_mm"],
        ),
        "unequal_flange_i": (
            {
                "radius_of_gyration_y_mm": P,
                "gross_area_mm2": P,
                "flange_centroid_spacing_mm": P,
                "compression_flange_minor_inertia_mm4": P,
                "section_minor_inertia_mm4": P,
                "effective_section_modulus_ex_mm3": P,
            },
            [
                "radius_of_gyration_y_mm",
                "gross_area_mm2",
                "flange_centroid_spacing_mm",
                "compression_flange_minor_inertia_mm4",
                "section_minor_inertia_mm4",
                "effective_section_modulus_ex_mm3",
            ],
        ),
        "rhs_or_shs": (
            {
                "radius_of_gyration_y_mm": P,
                "flange_width_mm": P,
                "web_depth_mm": P,
            },
            ["radius_of_gyration_y_mm", "flange_width_mm", "web_depth_mm"],
        ),
        "angle": (
            {
                "thickness_mm": P,
                "greater_leg_width_b1_mm": P,
                "lesser_leg_width_b2_mm": P,
            },
            ["thickness_mm", "greater_leg_width_b1_mm", "lesser_leg_width_b2_mm"],
        ),
    }
    beta_bases = {
        "conservative_minus_one": ({}, []),
        "transverse_loads": ({}, []),
        "end_moments": (
            {
                "end_moment_1_magnitude_knm": N,
                "end_moment_2_magnitude_knm": N,
                "curvature": {"enum": ["single", "reverse"]},
            },
            [
                "end_moment_1_magnitude_knm",
                "end_moment_2_magnitude_knm",
                "curvature",
            ],
        ),
    }
    variants = []
    for section, (geometry, geometry_required) in sections.items():
        for beta_basis, (beta_properties, beta_required) in beta_bases.items():
            properties = {
                "operation": {"const": "full_lateral_restraint_limit"},
                "section_type": {"const": section},
                "beta_m_basis": {"const": beta_basis},
                **common,
                **geometry,
                **beta_properties,
            }
            required = [
                "operation",
                "section_type",
                "beta_m_basis",
                *common,
                *geometry_required,
                *beta_required,
            ]
            variants.append(object_schema(properties, required))
    return {"oneOf": variants}


def _critical_flange_schema():
    common = {"segment_end_condition": {"const": "one_end_unrestrained"}}
    return {
        "oneOf": [
            object_schema(
                {
                    "operation": {"const": "critical_flange"},
                    "segment_end_condition": {"const": "both_ends_restrained"},
                    "compression_flange_position": {"enum": ["top", "bottom"]},
                }
            ),
            object_schema(
                {
                    "operation": {"const": "critical_flange"},
                    **common,
                    "dominant_load": {"const": "gravity"},
                }
            ),
            object_schema(
                {
                    "operation": {"const": "critical_flange"},
                    **common,
                    "dominant_load": {"const": "wind"},
                    "wind_case": {
                        "enum": [
                            "external_pressure",
                            "internal_suction",
                            "internal_pressure",
                            "external_suction",
                        ]
                    },
                    "exterior_flange_position": {"enum": ["top", "bottom"]},
                }
            ),
        ]
    }


def _unequal_flange_bending_schema():
    common = {
        "section_capacity_knm": P,
        "iy_mm4": P,
        "torsion_constant_mm4": P,
        "warping_constant_mm6": P,
        "effective_length_mm": P,
        "moment_factor": {"type": "number", "exclusiveMinimum": 0, "maximum": 2.5},
        "moment_factor_verified": VERIFIED,
        "action_knm": N,
        "section_properties_verified": VERIFIED,
        "constant_cross_section_verified": VERIFIED,
    }
    methods = {
        "compression_flange_inertia": {
            "flange_centroid_spacing_mm": P,
            "compression_flange_minor_inertia_mm4": P,
        },
        "section_integral": {
            "beta_x_mm": S,
            "beta_x_integral_verified": VERIFIED,
        },
    }
    variants = []
    for method, properties in methods.items():
        variant_properties = {
            "operation": {"const": "unequal_flange_bending"},
            "beta_x_method": {"const": method},
            **common,
            **properties,
        }
        variants.append(object_schema(variant_properties))
    return {"oneOf": variants}


def _moment_modification_factor_schema():
    return _schema(
        "moment_modification_factor",
        {
            "maximum_design_moment_knm": P,
            "quarter_point_moment_2_knm": N,
            "midpoint_moment_3_knm": N,
            "quarter_point_moment_4_knm": N,
            "moment_diagram_verified": VERIFIED,
        },
    )


def _varying_section_bending_schema():
    common = {
        "operation": {"const": "varying_section_bending"},
        "section_capacity_knm": P,
        "reference_buckling_moment_knm": P,
        "reference_buckling_moment_verified": VERIFIED,
        "moment_factor": {"type": "number", "exclusiveMinimum": 0, "maximum": 2.5},
        "moment_factor_verified": VERIFIED,
        "action_knm": N,
    }
    variants = [
        object_schema(
            {
                **common,
                "design_method": {"const": "minimum_section"},
                "minimum_section_values_verified": VERIFIED,
            }
        )
    ]
    critical_common = {
        **common,
        "design_method": {"const": "critical_section_reduced_reference"},
        "critical_section_values_verified": VERIFIED,
        "segment_length_mm": P,
        "minimum_flange_area_mm2": P,
        "critical_flange_area_mm2": P,
        "minimum_depth_mm": P,
        "critical_depth_mm": P,
    }
    variants.extend(
        [
            object_schema(
                {
                    **critical_common,
                    "variation_type": {"const": "stepped"},
                    "reduced_length_mm": P,
                }
            ),
            object_schema(
                {
                    **critical_common,
                    "variation_type": {"const": "tapered"},
                }
            ),
        ]
    )
    return {"oneOf": variants}


BOOL = {"type": "boolean"}
VERIFIED = {"const": True}
BETA = {"type": "number", "minimum": -1, "maximum": 1}
SCHEMAS = {
    "continuous_lateral_restraints": _schema(
        "continuous_lateral_restraints",
        {
            "both_ends_restrained_verified": VERIFIED,
            "continuous_restraints_at_critical_flange_verified": VERIFIED,
            "continuous_restraints_satisfy_5_4_3_1_verified": VERIFIED,
        },
    ),
    "full_lateral_restraint_limit": _full_lateral_restraint_schema(),
    "intermediate_lateral_restraints": _schema(
        "intermediate_lateral_restraints",
        {
            "both_ends_restrained_verified": VERIFIED,
            "intermediate_restraints_at_critical_flange_verified": VERIFIED,
            "intermediate_restraints_satisfy_5_4_3_1_verified": VERIFIED,
            "subsegment_checks": {
                "type": "array",
                "items": _full_lateral_restraint_schema(),
                "minItems": 1,
                "maxItems": 1000,
            },
        },
    ),
    "critical_section": _schema(
        "critical_section",
        {
            "sections": {
                "type": "array",
                "items": object_schema(
                    {
                        "section_id": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 128,
                        },
                        "design_moment_knm": N,
                        "section_moment_capacity_knm": P,
                    }
                ),
                "minItems": 1,
                "maxItems": 1000,
            },
        },
    ),
    "critical_flange": _critical_flange_schema(),
    "moment_modification_factor": _moment_modification_factor_schema(),
    "unequal_flange_bending": _unequal_flange_bending_schema(),
    "varying_section_bending": _varying_section_bending_schema(),
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
    "lateral_buckling_effective_length": _schema(
        "lateral_buckling_effective_length",
        {
            "segment_length_mm": P,
            "clear_flange_depth_mm": P,
            "critical_flange_thickness_mm": P,
            "web_thickness_mm": P,
            "number_of_webs": {"type": "integer", "minimum": 1, "maximum": 100},
            "restraint_arrangement": {"enum": ["FF", "FL", "LL", "FU", "FP", "PL", "PU", "PP"]},
            "gravity_load_position": {"enum": ["within_segment", "at_segment_end"]},
            "load_height_position": {"enum": ["shear_centre", "top_flange"]},
            "effective_rotation_restraint_count": {"type": "integer", "enum": [0, 1, 2]},
            "effective_rotation_restraints_verified": BOOL,
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
    if op == "continuous_lateral_restraints":
        return result(
            op,
            ["5.3.2.1", "5.3.2.2"],
            {
                "restraint_route": "continuous_lateral_restraints",
                "full_lateral_restraint_qualifies": True,
            },
            [
                {"clause": "5.3.2.2(a)", "satisfied": True},
                {"clause": "5.3.2.2(b)", "satisfied": True},
                {"clause": "5.4.3.1", "satisfied": True},
            ],
            [
                "Both ends must be fully or partially restrained under Clauses 5.4.2.1, "
                "5.4.2.2, 5.4.3.1 and 5.4.3.2.",
                "Continuous restraints must act at the critical flange and their "
                "effectiveness must be established under 5.4.3.1.",
                "This route records verified conditions; it does not design or independently "
                "validate the restraint system.",
            ],
        )
    if op == "intermediate_lateral_restraints":
        subsegments = []
        checks = [
            {"clause": "5.3.2.3(a)", "satisfied": True},
            {"clause": "5.3.2.3(c)", "satisfied": True},
            {"clause": "5.4.3.1", "satisfied": True},
        ]
        for index, subsegment in enumerate(d["subsegment_checks"], start=1):
            checked = run_advanced_members(subsegment)
            values = checked["values"]
            satisfied = values["full_lateral_restraint_qualifies"]
            checks.append(
                {
                    "clause": "5.3.2.3(b)",
                    "subsegment_number": index,
                    "actual_slenderness": values["segment_slenderness"],
                    "permitted_slenderness": values["permitted_slenderness"],
                    "satisfied": satisfied,
                }
            )
            subsegments.append(
                {
                    "subsegment_number": index,
                    "section_type": values["section_type"],
                    "beta_m": values["beta_m"],
                    "actual_slenderness": values["segment_slenderness"],
                    "permitted_slenderness": values["permitted_slenderness"],
                    "satisfied": satisfied,
                }
            )
        return result(
            op,
            ["5.3.2.1", "5.3.2.3", "5.3.2.4"],
            {
                "restraint_route": "intermediate_lateral_restraints",
                "subsegment_count": len(subsegments),
                "subsegments": subsegments,
                "full_lateral_restraint_qualifies": all(check["satisfied"] for check in checks),
            },
            checks,
            [
                "Both segment ends must be fully or partially restrained under Clauses "
                "5.4.2.1, 5.4.2.2, 5.4.3.1 and 5.4.3.2.",
                "Every subsegment is checked against Clause 5.3.2.4 using its own "
                "verified section properties and beta_m basis.",
                "Intermediate restraints must act at the critical flange and be effective "
                "under 5.4.3.1; their strength, stiffness and force path remain assessed.",
            ],
        )
    if op == "critical_flange":
        if d["segment_end_condition"] == "both_ends_restrained":
            position = d["compression_flange_position"]
            location = "compression"
            clauses = ["5.5.1", "5.5.2"]
            basis = "compression flange for a segment restrained at both ends"
        elif d["dominant_load"] == "gravity":
            position = "top"
            location = "top"
            clauses = ["5.5.1", "5.5.3"]
            basis = "top flange for a one-end-unrestrained segment with dominant gravity load"
        else:
            exterior_controls = d["wind_case"] in {
                "external_pressure",
                "internal_suction",
            }
            location = "exterior" if exterior_controls else "interior"
            exterior_position = d["exterior_flange_position"]
            position = (
                exterior_position
                if exterior_controls
                else ("bottom" if exterior_position == "top" else "top")
            )
            clauses = ["5.5.1", "5.5.3"]
            basis = (
                "exterior flange for external pressure or internal suction"
                if exterior_controls
                else "interior flange for internal pressure or external suction"
            )
        return result(
            op,
            clauses,
            {
                "critical_flange_position": position,
                "critical_flange_location": location,
                "selection_basis": basis,
                "wind_case": d.get("wind_case"),
            },
            [],
            [
                "Segment end conditions, gravity/wind load dominance, wind pressure/suction "
                "case and exterior-flange orientation must be assessed for the actual member.",
                "This selects the prescribed critical flange under Clauses 5.5.2–5.5.3; "
                "it does not determine restraint effectiveness or calculate buckling capacity.",
                "Clause 5.5.1 permits elastic buckling analysis for other configurations; "
                "those cases require a separately verified analysis.",
            ],
        )
    if op == "critical_section":
        candidates = d["sections"]
        identifiers = [candidate["section_id"] for candidate in candidates]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Section identifiers must be unique.")
        section_ratios = [
            {
                "section_id": candidate["section_id"],
                "design_moment_knm": candidate["design_moment_knm"],
                "section_moment_capacity_knm": candidate["section_moment_capacity_knm"],
                "moment_to_capacity_ratio": (
                    candidate["design_moment_knm"] / candidate["section_moment_capacity_knm"]
                ),
            }
            for candidate in candidates
        ]
        controlling_ratio = max(
            candidate["moment_to_capacity_ratio"] for candidate in section_ratios
        )
        controlling = [
            candidate
            for candidate in section_ratios
            if candidate["moment_to_capacity_ratio"] == controlling_ratio
        ]
        return result(
            op,
            ["5.3.3"],
            {
                "critical_section_id": controlling[0]["section_id"],
                "critical_section_ids": [candidate["section_id"] for candidate in controlling],
                "maximum_moment_to_capacity_ratio": controlling_ratio,
                "section_ratios": section_ratios,
            },
            [],
            [
                "Supply design moments and nominal section moment capacities at all "
                "candidate cross-sections in this segment.",
                "Use nonnegative design-moment magnitudes from the same bending axis and "
                "design action case.",
                "This operation selects the critical section only; it does not calculate "
                "actions, section capacities or member adequacy.",
                "Run separately for each applicable bending axis and design action case.",
            ],
        )
    if op == "full_lateral_restraint_limit":
        beta_basis = d["beta_m_basis"]
        if beta_basis == "conservative_minus_one":
            beta_m = -1.0
        elif beta_basis == "transverse_loads":
            beta_m = -0.8
        else:
            end_moments = sorted(
                [
                    d["end_moment_1_magnitude_knm"],
                    d["end_moment_2_magnitude_knm"],
                ]
            )
            if end_moments[1] == 0:
                raise ValueError("At least one end moment must be non-zero.")
            beta_m = end_moments[0] / end_moments[1]
            if d["curvature"] == "single":
                beta_m = -beta_m

        length = d["segment_length_mm"]
        fy = d["yield_strength_mpa"]
        section = d["section_type"]
        details = {}
        if section in {"equal_flanged_i", "equal_flanged_channel", "unequal_flange_i"}:
            slenderness = length / d["radius_of_gyration_y_mm"]
            coefficient = (
                60 + 40 * beta_m if section == "equal_flanged_channel" else 80 + 50 * beta_m
            )
            geometry_factor = 1.0
            if section == "unequal_flange_i":
                flange_inertia = d["compression_flange_minor_inertia_mm4"]
                section_inertia = d["section_minor_inertia_mm4"]
                if flange_inertia > section_inertia:
                    raise ValueError(
                        "Compression-flange minor inertia must not exceed section minor inertia."
                    )
                rho = flange_inertia / section_inertia
                geometry_factor = sqrt(
                    2
                    * rho
                    * d["gross_area_mm2"]
                    * d["flange_centroid_spacing_mm"]
                    / (2.5 * d["effective_section_modulus_ex_mm3"])
                )
                details["compression_flange_inertia_ratio"] = rho
                details["unequal_flange_geometry_factor"] = geometry_factor
            permitted = coefficient * geometry_factor * sqrt(250 / fy)
        elif section == "rhs_or_shs":
            slenderness = length / d["radius_of_gyration_y_mm"]
            permitted = (
                (1800 + 1500 * beta_m) * d["flange_width_mm"] / d["web_depth_mm"] * (250 / fy)
            )
        else:
            greater_leg = d["greater_leg_width_b1_mm"]
            lesser_leg = d["lesser_leg_width_b2_mm"]
            if lesser_leg > greater_leg:
                raise ValueError("b2 must not exceed b1 for an angle section.")
            slenderness = length / d["thickness_mm"]
            permitted = (210 + 175 * beta_m) * sqrt(lesser_leg / greater_leg) * (250 / fy)
        check = _limit("5.3.2.4", slenderness, permitted)
        return result(
            op,
            ["5.3.2.4"],
            {
                "section_type": section,
                "beta_m_basis": beta_basis,
                "beta_m": beta_m,
                "segment_slenderness": slenderness,
                "permitted_slenderness": permitted,
                "full_lateral_restraint_qualifies": check["satisfied"],
                **details,
            },
            [check],
            [
                "Applies only to a segment restrained at both ends as verified under "
                "Clauses 5.4.2.1, 5.4.2.2, 5.4.3.1 and 5.4.3.2.",
                "Verify section type and properties, including the effective Z_ex under "
                "Clause 5.2 for unequal-flange I-sections.",
                "Use end-moment beta_m only when there are no transverse loads in the "
                "segment; verify the signed curvature classification.",
                "This check establishes only the Clause 5.3.2.4 length criterion. "
                "Restraint stiffness, strength and force transfer remain separate checks.",
            ],
        )
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
    if op == "moment_modification_factor":
        moments = [
            d["quarter_point_moment_2_knm"],
            d["midpoint_moment_3_knm"],
            d["quarter_point_moment_4_knm"],
        ]
        if d["maximum_design_moment_knm"] < max(moments):
            raise ValueError("Maximum design moment must not be below a sampled segment moment.")
        denominator = sqrt(sum(moment**2 for moment in moments))
        if denominator == 0:
            raise ValueError("At least one quarter-point or midpoint moment must be non-zero.")
        uncapped = 1.7 * d["maximum_design_moment_knm"] / denominator
        factor = min(2.5, uncapped)
        return result(
            op,
            ["5.6.1.1(a)(iii)"],
            {
                "moment_factor": factor,
                "uncapped_moment_factor": uncapped,
                "maximum_moment_factor": 2.5,
                "upper_cap_applied": uncapped > 2.5,
            },
            [],
            [
                "The supplied moments are nonnegative design-moment magnitudes from the "
                "same segment; the maximum moment and quarter-point/midpoint values must "
                "represent the assessed moment diagram.",
                "Use this equation for the moment-modification-factor option in Clause "
                "5.6.1.1(a). Table 5.6.1 and elastic-buckling alternatives remain separate "
                "assessed paths.",
            ],
        )
    if op == "unequal_flange_bending":
        if d["beta_x_method"] == "compression_flange_inertia":
            iy = d["iy_mm4"]
            inertia_ratio = d["compression_flange_minor_inertia_mm4"] / iy
            if inertia_ratio > 1:
                raise ValueError(
                    "Compression-flange minor inertia must not exceed section minor inertia."
                )
            beta_x = 0.8 * d["flange_centroid_spacing_mm"] * (2 * inertia_ratio - 1)
        else:
            beta_x = d["beta_x_mm"]

        iy = d["iy_mm4"]
        length = d["effective_length_mm"]
        a = pi**2 * ELASTIC_MODULUS_MPA * iy / length**2
        stiffness = (
            SHEAR_MODULUS_MPA * d["torsion_constant_mm4"]
            + pi**2 * ELASTIC_MODULUS_MPA * d["warping_constant_mm6"] / length**2
            + (beta_x**2 / 4) * a
        )
        mo = sqrt(a) * (sqrt(stiffness) + (beta_x / 2) * sqrt(a)) / 1e6
        if not isfinite(mo) or mo <= 0:
            raise ValueError(
                "Clause 5.6.1.2 reference buckling moment must be positive and finite."
            )

        ms = d["section_capacity_knm"]
        alpha_m = d["moment_factor"]
        ratio = ms / mo
        alpha_s = 0.6 * (sqrt(ratio**2 + 3) - ratio)
        mb = min(ms, alpha_m * alpha_s * ms)
        return result(
            op,
            ["5.6.1.1(a)", "5.6.1.1(2)", "5.6.1.2"],
            {
                "beta_x_method": d["beta_x_method"],
                "beta_x_mm": beta_x,
                "elastic_modulus_mpa": ELASTIC_MODULUS_MPA,
                "shear_modulus_mpa": SHEAR_MODULUS_MPA,
                "reference_buckling_moment_knm": mo,
                "slenderness_reduction": alpha_s,
                "moment_factor": alpha_m,
                "member_capacity_knm": mb,
            },
            [capacity_check("5.6.1.2", mb, d["action_knm"])],
            [
                "Use gross-section Ms from Clause 5.2 and effective length including the "
                "applicable Clause 5.6.3 factors.",
                "Verify section properties and compression-flange selection. Clause "
                "5.6.1.2 defines beta_x as positive for the larger flange in compression "
                "and negative for the smaller flange in compression.",
                "The supplied moment factor must be independently selected under Clause "
                "5.6.1.1; the operation does not derive it from the member moment diagram.",
                "The section-integral beta_x route requires independent verification of "
                "the Clause 5.6.1.2 integral and shear-centre coordinate.",
                "The elastic buckling-analysis alternative under Clause 5.6.1.2(b) is "
                "available through the separate buckling-analysis operation.",
            ],
        )
    if op == "varying_section_bending":
        design_method = d["design_method"]
        alpha_st = 1.0
        if design_method == "critical_section_reduced_reference":
            if d["minimum_flange_area_mm2"] > d["critical_flange_area_mm2"]:
                raise ValueError(
                    "Minimum-section flange area must not exceed critical-section area."
                )
            if d["minimum_depth_mm"] > d["critical_depth_mm"]:
                raise ValueError("Minimum-section depth must not exceed critical-section depth.")
            if d["variation_type"] == "stepped":
                if d["reduced_length_mm"] > d["segment_length_mm"]:
                    raise ValueError("Reduced length must not exceed the segment length.")
                r_r = d["reduced_length_mm"] / d["segment_length_mm"]
            else:
                r_r = 0.5
            r_s = (d["minimum_flange_area_mm2"] / d["critical_flange_area_mm2"]) * (
                0.6 + 0.4 * d["minimum_depth_mm"] / d["critical_depth_mm"]
            )
            alpha_st = 1 - 1.2 * r_r * (1 - r_s)
            if not isfinite(alpha_st) or alpha_st <= 0:
                raise ValueError("Section variation reduction factor must be positive and finite.")

        moa = d["reference_buckling_moment_knm"] * alpha_st
        if not isfinite(moa) or moa <= 0:
            raise ValueError("Adjusted reference buckling moment must be positive and finite.")
        ms = d["section_capacity_knm"]
        ratio = ms / moa
        alpha_s = 0.6 * (sqrt(ratio**2 + 3) - ratio)
        alpha_m = d["moment_factor"]
        mb = min(ms, alpha_m * alpha_s * ms)
        if design_method == "minimum_section":
            clauses = ["5.6.1.1(a)", "5.6.1.1(b)(i)", "5.6.1.1(2)"]
        else:
            clauses = ["5.6.1.1(a)", "5.6.1.1(b)(ii)", "5.6.1.1(2)"]
        return result(
            op,
            clauses,
            {
                "design_method": design_method,
                "alpha_st": (
                    alpha_st if design_method == "critical_section_reduced_reference" else None
                ),
                "reference_buckling_moment_knm": d["reference_buckling_moment_knm"],
                "adjusted_reference_buckling_moment_knm": moa,
                "slenderness_reduction": alpha_s,
                "moment_factor": alpha_m,
                "member_capacity_knm": mb,
            },
            [capacity_check("5.6.1.1(b)", mb, d["action_knm"])],
            [
                "The supplied nominal section capacity and reference buckling moment must "
                "both use the verified minimum cross-section for method (i), or the "
                "verified critical cross-section for method (ii).",
                "Method (ii) reduces the critical-section reference moment by alpha_st; "
                "the operation calculates alpha_st from the stepped/tapered geometry.",
                "The moment factor must be independently selected under Clause 5.6.1.1. "
                "The buckling-analysis alternative under Clause 5.6.1.1(b)(iii) requires "
                "a separately verified analysis.",
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
        # Table 5.6.2 applies to the three illustrated one-end-unrestrained cases.
        factors = {"uniform_end_moment": 0.25, "tip_force": 1.25, "uniform_load": 2.25}
        am = factors[d["moment_distribution"]]
        ms, mo = d["section_capacity_knm"], d["reference_buckling_moment_knm"]
        ratio = ms / mo
        reduction = 1.8 / (sqrt(ratio * ratio + 3) + ratio)
        mb = min(ms, am * reduction * ms)
        return result(
            op,
            ["5.6.1.1(1)", "5.6.1.1(2)", "5.6.1.1(3)", "5.6.2", "Table 5.6.2"],
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
    if op == "lateral_buckling_effective_length":
        arrangement = d["restraint_arrangement"]
        if (
            d["effective_rotation_restraint_count"]
            and not d["effective_rotation_restraints_verified"]
        ):
            raise ValueError("Count only effective rotational restraints verified under 5.4.3.4.")
        kt = 1.0
        if arrangement in {"FP", "PL", "PU", "PP"}:
            ratio = (d["clear_flange_depth_mm"] / d["segment_length_mm"]) * (
                d["critical_flange_thickness_mm"] / (2 * d["web_thickness_mm"])
            ) ** 3
            kt += ratio * (2 if arrangement == "PP" else 1) / d["number_of_webs"]
        if d["gravity_load_position"] == "within_segment":
            kl = (
                1.0
                if d["load_height_position"] == "shear_centre"
                else (2.0 if arrangement in {"FU", "PU"} else 1.4)
            )
        else:
            kl = (
                1.0
                if d["load_height_position"] == "shear_centre"
                else (2.0 if arrangement in {"FU", "PU"} else 1.0)
            )
        rotation_count = d["effective_rotation_restraint_count"]
        kr = 1.0
        if arrangement in {"FF", "FP", "PP"}:
            kr = {0: 1.0, 1: 0.85, 2: 0.70}[rotation_count]
        factor = kt * kl * kr
        return result(
            op,
            ["5.6.3", "Table 5.6.3(A)", "Table 5.6.3(B)", "Table 5.6.3(C)"],
            {
                "twist_restraint_factor": kt,
                "load_height_factor": kl,
                "lateral_rotation_factor": kr,
                "effective_length_factor": factor,
                "effective_length_mm": factor * d["segment_length_mm"],
            },
            [],
            [
                "Tables 5.6.3(A) and (B) cover only the listed beam-end restraint "
                "and gravity-load cases.",
                "Only effective lateral-rotation restraints under 5.4.3.4 reduce kr.",
                "The segment length must use restraint spacing or a valid sub-segment length.",
                "Verify geometry, end labels, loading, intermediate restraint and "
                "applicability independently.",
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
                "For 5.4.3.1, use the maximum critical-flange force from adjacent segments "
                "or sub-segments at the restraint.",
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
