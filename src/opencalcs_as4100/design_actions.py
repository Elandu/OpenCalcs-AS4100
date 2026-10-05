# SPDX-License-Identifier: AGPL-3.0-only
"""AS 4100 sections 3/4 numerical design-action checks, reviewed against scanned text."""

from math import isfinite, pi

from .standards import ELASTIC_MODULUS_MPA
from .validation import NONNEGATIVE, POSITIVE, SIGNED, object_schema, result, validate

_BOOL = {"type": "boolean"}
_REFERENCE = {"type": "string", "minLength": 1, "maxLength": 160}
_YIELD_STRESS = {"type": "number", "exclusiveMinimum": 0, "maximum": 690}
_VECTOR3 = {"type": "array", "minItems": 3, "maxItems": 3, "items": SIGNED}

_PLASTIC_MATERIAL = object_schema(
    {
        "material_id": _REFERENCE,
        "material_standard": {"enum": ["AS/NZS 3678", "AS/NZS 3679.1"]},
        "material_standard_verified": _BOOL,
        "specified_yield_strength_mpa": _YIELD_STRESS,
        "specified_tensile_strength_mpa": POSITIVE,
        "yield_plateau_extension_in_yield_strains": NONNEGATIVE,
        "elongation_percent": NONNEGATIVE,
        "elongation_test_to_as1391_verified": _BOOL,
        "strain_hardening_capability_verified": _BOOL,
        "stress_strain_data_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_PLASTIC_MEMBER = object_schema(
    {
        "member_id": _REFERENCE,
        "hot_formed": _BOOL,
        "hot_formed_status_verified": _BOOL,
        "section_form": {"enum": ["doubly_symmetric_i_section", "other"]},
        "section_form_verified": _BOOL,
        "compact_under_clause_5_2_3": _BOOL,
        "compactness_assessment_verified": _BOOL,
        "impact_loading_present": _BOOL,
        "impact_loading_assessment_verified": _BOOL,
        "fatigue_assessment_required": _BOOL,
        "fatigue_loading_assessment_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_PLASTIC_CONNECTION = object_schema(
    {
        "connection_id": _REFERENCE,
        "strength_type": {"enum": ["full_strength", "partial_strength"]},
        "connection_design_moment_capacity_knm": POSITIVE,
        "connected_member_design_moment_capacity_knm": POSITIVE,
        "connection_capacity_used_in_analysis_verified": _BOOL,
        "all_required_plastic_hinges_develop_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_PLASTIC_HINGE = object_schema(
    {
        "hinge_id": _REFERENCE,
        "location_type": {"enum": ["member", "connection"]},
        "rotation_demand_rad": NONNEGATIVE,
        "rotation_capacity_rad": POSITIVE,
        "rotation_demand_assessment_verified": _BOOL,
        "rotation_capacity_assessment_verified": _BOOL,
        "evidence_reference": _REFERENCE,
    }
)
_GLOBAL_ACTION = object_schema(
    {
        "action_id": _REFERENCE,
        "action_type": {"enum": ["applied_load", "support_reaction"]},
        "force_kn": _VECTOR3,
        "moment_knm": _VECTOR3,
        "position_mm": _VECTOR3,
        "evidence_reference": _REFERENCE,
    }
)

SCHEMAS = {
    "euler_buckling": object_schema(
        {
            "operation": {"const": "euler_buckling"},
            "elastic_modulus_mpa": {"const": ELASTIC_MODULUS_MPA},
            "second_moment_mm4": POSITIVE,
            "member_length_mm": POSITIVE,
            "effective_length_factor": POSITIVE,
        }
    ),
    "moment_amplification": object_schema(
        {
            "operation": {"const": "moment_amplification"},
            "compression_kn": NONNEGATIVE,
            "elastic_buckling_load_kn": POSITIVE,
            "beta_m": {"type": "number", "minimum": -1, "maximum": 1},
            "first_order_moment_knm": SIGNED,
            "sway_buckling_factor": {"type": "number", "exclusiveMinimum": 1, "maximum": 1e15},
        },
        [
            "operation",
            "compression_kn",
            "elastic_buckling_load_kn",
            "beta_m",
            "first_order_moment_knm",
        ],
    ),
    "storey_sway_amplification": object_schema(
        {
            "operation": {"const": "storey_sway_amplification"},
            "storey_displacement_mm": NONNEGATIVE,
            "storey_height_mm": POSITIVE,
            "total_compression_kn": NONNEGATIVE,
            "total_storey_shear_kn": POSITIVE,
        }
    ),
    "plastic_amplification": object_schema(
        {
            "operation": {"const": "plastic_amplification"},
            "frame_buckling_factor": POSITIVE,
            "first_order_action": SIGNED,
        }
    ),
    "plastic_analysis_limits": object_schema(
        {
            "operation": {"const": "plastic_analysis_limits"},
            "materials": {"type": "array", "minItems": 1, "items": _PLASTIC_MATERIAL},
            "members": {"type": "array", "minItems": 1, "items": _PLASTIC_MEMBER},
        }
    ),
    "plastic_analysis_connections": object_schema(
        {
            "operation": {"const": "plastic_analysis_connections"},
            "rigid_plastic_analysis_verified": _BOOL,
            "all_assumed_connections_listed_verified": _BOOL,
            "all_collapse_mechanism_hinges_listed_verified": _BOOL,
            "analysis_evidence_reference": _REFERENCE,
            "connections": {"type": "array", "minItems": 1, "items": _PLASTIC_CONNECTION},
            "plastic_hinges": {"type": "array", "minItems": 1, "items": _PLASTIC_HINGE},
        }
    ),
    "plastic_global_equilibrium": object_schema(
        {
            "operation": {"const": "plastic_global_equilibrium"},
            "actions": {"type": "array", "minItems": 1, "items": _GLOBAL_ACTION},
            "force_tolerance_kn": NONNEGATIVE,
            "moment_tolerance_knm": NONNEGATIVE,
            "boundary_conditions_verified": _BOOL,
            "boundary_conditions_evidence_reference": _REFERENCE,
        }
    ),
    "notional_horizontal_load": object_schema(
        {
            "operation": {"const": "notional_horizontal_load"},
            "floor_vertical_design_load_kn": NONNEGATIVE,
        }
    ),
    "stability": object_schema(
        {
            "operation": {"const": "stability"},
            "destabilising_design_effect": NONNEGATIVE,
            "stabilising_dead_effect": NONNEGATIVE,
            "resisting_design_capacity": NONNEGATIVE,
        }
    ),
    "serviceability": object_schema(
        {
            "operation": {"const": "serviceability"},
            "deflection_mm": SIGNED,
            "deflection_limit_mm": POSITIVE,
            "limit_basis": {"type": "string", "minLength": 1, "maxLength": 500},
        }
    ),
}
INPUT_SCHEMA = {"oneOf": list(SCHEMAS.values())}
OUTPUT_SCHEMA = {"type": "object"}


def run_design_actions(inputs):
    d = validate(inputs, INPUT_SCHEMA)
    op = d["operation"]
    if op == "euler_buckling":
        load = (
            pi**2
            * d["elastic_modulus_mpa"]
            * d["second_moment_mm4"]
            / (d["effective_length_factor"] * d["member_length_mm"]) ** 2
            / 1000
        )
        if not isfinite(load) or load <= 0:
            raise ValueError("Invalid elastic buckling load.")
        return result(
            op,
            ["4.6.2"],
            {"elastic_buckling_load_kn": load},
            limitations=[
                "Effective length factor requires restraint/frame assessment under 4.6.3.",
            ],
        )
    if op == "moment_amplification":
        ratio = d["compression_kn"] / d["elastic_buckling_load_kn"]
        if ratio >= 1:
            raise ValueError("Axial compression reaches elastic instability.")
        cm = min(1.0, 0.6 - 0.4 * d["beta_m"])
        db = max(1.0, cm / (1 - ratio)) if d["compression_kn"] else 1.0
        ds = 1.0
        if "sway_buckling_factor" in d:
            ds = 1 / (1 - 1 / d["sway_buckling_factor"])
        factor = max(db, ds)
        return result(
            op,
            ["4.4.1.2", "4.4.2.2", "4.4.2.3"],
            {
                "cm": cm,
                "braced_factor": db,
                "sway_factor": ds,
                "governing_factor": factor,
                "amplified_moment_knm": factor * d["first_order_moment_knm"],
                "second_order_analysis_required": factor > 1.4,
            },
            [{"clause": "4.4.1.2", "satisfied": factor <= 1.4}],
            limitations=[
                "Factors above 1.4 require second-order analysis; values are diagnostic only.",
                "Reverse curvature is positive beta_m; assess transverse loads under 4.4.2.2.",
            ],
        )
    if op == "storey_sway_amplification":
        ratio = (
            d["storey_displacement_mm"]
            * d["total_compression_kn"]
            / (d["storey_height_mm"] * d["total_storey_shear_kn"])
        )
        if ratio >= 1:
            raise ValueError("Storey sway expression reaches instability.")
        factor = 1 / (1 - ratio)
        return result(
            op,
            ["4.4.2.3(a)(i)"],
            {
                "sway_factor": factor,
                "second_order_analysis_required": factor > 1.4,
            },
            [{"clause": "4.4.1.2", "satisfied": factor <= 1.4}],
            limitations=["Rectangular frame storeys only; all column actions must be included."],
        )
    if op == "plastic_amplification":
        factor = d["frame_buckling_factor"]
        required = factor < 5
        amp = None if required else (1.0 if factor >= 10 else 0.9 / (1 - 1 / factor))
        return result(
            op,
            ["4.5.4"],
            {
                "amplification_factor": amp,
                "amplified_action": None if required else amp * d["first_order_action"],
                "second_order_plastic_analysis_required": required,
            },
            [{"clause": "4.5.4", "satisfied": not required}],
            limitations=[
                "Plastic analysis applicability under 4.5.2 must be separately established."
            ],
        )
    if op == "plastic_analysis_limits":
        checks = []
        material_results = []
        for material in d["materials"]:
            fy = material["specified_yield_strength_mpa"]
            fu = material["specified_tensile_strength_mpa"]
            yield_ratio = fu / fy
            plateau_ratio = material["yield_plateau_extension_in_yield_strains"]
            elongation = material["elongation_percent"]
            standard_verified = (
                material["material_standard_verified"] and material["stress_strain_data_verified"]
            )
            material_checks = [
                {
                    "clause": "4.5.2(a)",
                    "subject_id": material["material_id"],
                    "minimum_specified_yield_strength_mpa": fy,
                    "limit_mpa": 450,
                    "evidence_verified": material["material_standard_verified"],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": material["material_standard_verified"] and fy <= 450,
                },
                {
                    "clause": "4.5.2(b)",
                    "subject_id": material["material_id"],
                    "material_standard": material["material_standard"],
                    "stress_strain_data_verified": material["stress_strain_data_verified"],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": standard_verified,
                },
                {
                    "clause": "4.5.2(b)(i)",
                    "subject_id": material["material_id"],
                    "yield_plateau_extension_in_yield_strains": plateau_ratio,
                    "minimum_ratio": 6,
                    "evidence_verified": material["stress_strain_data_verified"],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": standard_verified and plateau_ratio >= 6,
                },
                {
                    "clause": "4.5.2(b)(ii)",
                    "subject_id": material["material_id"],
                    "tensile_to_yield_strength_ratio": yield_ratio,
                    "minimum_ratio": 1.2,
                    "evidence_verified": material["stress_strain_data_verified"],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": standard_verified and yield_ratio >= 1.2,
                },
                {
                    "clause": "4.5.2(b)(iii)",
                    "subject_id": material["material_id"],
                    "elongation_percent": elongation,
                    "minimum_percent": 15,
                    "as1391_test_verified": material["elongation_test_to_as1391_verified"],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": (
                        standard_verified
                        and elongation >= 15
                        and material["elongation_test_to_as1391_verified"]
                    ),
                },
                {
                    "clause": "4.5.2(b)(iv)",
                    "subject_id": material["material_id"],
                    "strain_hardening_capability_verified": material[
                        "strain_hardening_capability_verified"
                    ],
                    "evidence_reference": material["evidence_reference"],
                    "satisfied": (
                        standard_verified and material["strain_hardening_capability_verified"]
                    ),
                },
            ]
            checks.extend(material_checks)
            material_results.append(
                {
                    "material_id": material["material_id"],
                    "tensile_to_yield_strength_ratio": yield_ratio,
                    "checks_satisfied": all(check["satisfied"] for check in material_checks),
                }
            )

        member_results = []
        for member in d["members"]:
            section_verified = member["section_form_verified"]
            compactness_verified = member["compactness_assessment_verified"]
            loading_verified = (
                member["impact_loading_assessment_verified"]
                and member["fatigue_loading_assessment_verified"]
            )
            member_checks = [
                {
                    "clause": "4.5.2(c)",
                    "subject_id": member["member_id"],
                    "hot_formed": member["hot_formed"],
                    "status_verified": member["hot_formed_status_verified"],
                    "evidence_reference": member["evidence_reference"],
                    "satisfied": member["hot_formed"] and member["hot_formed_status_verified"],
                },
                {
                    "clause": "4.5.2(d)",
                    "subject_id": member["member_id"],
                    "section_form": member["section_form"],
                    "status_verified": section_verified,
                    "evidence_reference": member["evidence_reference"],
                    "satisfied": (
                        section_verified and member["section_form"] == "doubly_symmetric_i_section"
                    ),
                },
                {
                    "clause": "4.5.2(e)",
                    "subject_id": member["member_id"],
                    "compact_under_clause_5_2_3": member["compact_under_clause_5_2_3"],
                    "assessment_verified": compactness_verified,
                    "evidence_reference": member["evidence_reference"],
                    "satisfied": member["compact_under_clause_5_2_3"] and compactness_verified,
                },
                {
                    "clause": "4.5.2(f)",
                    "subject_id": member["member_id"],
                    "impact_loading_present": member["impact_loading_present"],
                    "fatigue_assessment_required": member["fatigue_assessment_required"],
                    "loading_assessment_verified": loading_verified,
                    "evidence_reference": member["evidence_reference"],
                    "satisfied": (
                        loading_verified
                        and not member["impact_loading_present"]
                        and not member["fatigue_assessment_required"]
                    ),
                },
            ]
            checks.extend(member_checks)
            member_results.append(
                {
                    "member_id": member["member_id"],
                    "checks_satisfied": all(check["satisfied"] for check in member_checks),
                }
            )

        return result(
            op,
            ["4.5.2(a)–(f)"],
            {
                "materials": material_results,
                "members": member_results,
                "prescriptive_4_5_2_conditions_satisfied": all(
                    check["satisfied"] for check in checks
                ),
            },
            checks,
            limitations=[
                "This checks the prescriptive Clause 4.5.2 route only; an alternative "
                "ductility assessment is not evaluated.",
                "Clause 4.5.1 equilibrium and boundary conditions and Clause 4.5.3 "
                "connection strength and plastic-rotation capacity remain separate assessments.",
                "No plastic frame analysis, hinge sequence or design action effects are "
                "calculated.",
            ],
        )
    if op == "plastic_analysis_connections":
        checks = [
            {
                "clause": "4.5.3",
                "condition": "rigid plastic analysis is used",
                "satisfied": d["rigid_plastic_analysis_verified"],
                "evidence_reference": d["analysis_evidence_reference"],
            },
            {
                "clause": "4.5.3",
                "condition": "all assumed full/partial-strength connections are listed",
                "satisfied": d["all_assumed_connections_listed_verified"],
                "evidence_reference": d["analysis_evidence_reference"],
            },
            {
                "clause": "4.5.3(a)/(b)",
                "condition": "all plastic hinges in the collapse mechanism are listed",
                "satisfied": d["all_collapse_mechanism_hinges_listed_verified"],
                "evidence_reference": d["analysis_evidence_reference"],
            },
        ]
        connection_results = []
        for connection in d["connections"]:
            connection_capacity = connection["connection_design_moment_capacity_knm"]
            member_capacity = connection["connected_member_design_moment_capacity_knm"]
            capacity_ratio = connection_capacity / member_capacity
            common_satisfied = connection["connection_capacity_used_in_analysis_verified"]
            if connection["strength_type"] == "full_strength":
                strength_clause = "4.5.3(a)"
                strength_condition = "connection capacity is at least the connected member capacity"
                strength_satisfied = connection_capacity >= member_capacity
            else:
                strength_clause = "4.5.3(b)"
                strength_condition = "all plastic hinges required by the mechanism can develop"
                strength_satisfied = connection["all_required_plastic_hinges_develop_verified"]
            connection_checks = [
                {
                    "clause": strength_clause,
                    "subject_id": connection["connection_id"],
                    "condition": strength_condition,
                    "connection_design_moment_capacity_knm": connection_capacity,
                    "connected_member_design_moment_capacity_knm": member_capacity,
                    "capacity_ratio": capacity_ratio,
                    "satisfied": strength_satisfied,
                    "evidence_reference": connection["evidence_reference"],
                },
                {
                    "clause": "4.5.3",
                    "subject_id": connection["connection_id"],
                    "condition": "connection capacity is included in the analysis",
                    "satisfied": common_satisfied,
                    "evidence_reference": connection["evidence_reference"],
                },
            ]
            checks.extend(connection_checks)
            connection_results.append(
                {
                    "connection_id": connection["connection_id"],
                    "strength_type": connection["strength_type"],
                    "capacity_ratio": capacity_ratio,
                    "checks_satisfied": all(check["satisfied"] for check in connection_checks),
                }
            )

        hinge_results = []
        for hinge in d["plastic_hinges"]:
            assessments_verified = (
                hinge["rotation_demand_assessment_verified"]
                and hinge["rotation_capacity_assessment_verified"]
            )
            rotation_satisfied = (
                assessments_verified
                and hinge["rotation_capacity_rad"] >= hinge["rotation_demand_rad"]
            )
            hinge_check = {
                "clause": "4.5.3(a)/(b)",
                "subject_id": hinge["hinge_id"],
                "location_type": hinge["location_type"],
                "rotation_demand_rad": hinge["rotation_demand_rad"],
                "rotation_capacity_rad": hinge["rotation_capacity_rad"],
                "assessments_verified": assessments_verified,
                "satisfied": rotation_satisfied,
                "evidence_reference": hinge["evidence_reference"],
            }
            checks.append(hinge_check)
            hinge_results.append(
                {
                    "hinge_id": hinge["hinge_id"],
                    "rotation_demand_to_capacity_ratio": (
                        hinge["rotation_demand_rad"] / hinge["rotation_capacity_rad"]
                    ),
                    "checks_satisfied": rotation_satisfied,
                }
            )

        return result(
            op,
            ["4.5.3", "4.5.3(a)", "4.5.3(b)"],
            {
                "connections": connection_results,
                "plastic_hinges": hinge_results,
                "connection_and_rotation_conditions_satisfied": all(
                    check["satisfied"] for check in checks
                ),
            },
            checks,
            limitations=[
                "Connection capacities, the completeness of the connection/hinge lists and "
                "rotation assessments are supplied evidence and are not authenticated here.",
                "This does not verify global equilibrium, boundary conditions, the collapse "
                "mechanism or the underlying plastic analysis results.",
            ],
        )
    if op == "plastic_global_equilibrium":
        force_resultant = [0.0, 0.0, 0.0]
        moment_resultant = [0.0, 0.0, 0.0]
        action_counts = {"applied_load": 0, "support_reaction": 0}
        for action in d["actions"]:
            action_counts[action["action_type"]] += 1
            force = action["force_kn"]
            position = [coordinate / 1000 for coordinate in action["position_mm"]]
            couple = action["moment_knm"]
            lever_moment = [
                position[1] * force[2] - position[2] * force[1],
                position[2] * force[0] - position[0] * force[2],
                position[0] * force[1] - position[1] * force[0],
            ]
            for axis in range(3):
                force_resultant[axis] += force[axis]
                moment_resultant[axis] += couple[axis] + lever_moment[axis]

        force_satisfied = all(
            abs(component) <= d["force_tolerance_kn"] for component in force_resultant
        )
        moment_satisfied = all(
            abs(component) <= d["moment_tolerance_knm"] for component in moment_resultant
        )
        action_types_satisfied = all(count > 0 for count in action_counts.values())
        checks = [
            {
                "clause": "4.5.1",
                "condition": "global force equilibrium",
                "resultant_force_kn": force_resultant,
                "maximum_component_residual_kn": max(abs(value) for value in force_resultant),
                "tolerance_kn": d["force_tolerance_kn"],
                "satisfied": force_satisfied,
            },
            {
                "clause": "4.5.1",
                "condition": "global moment equilibrium about the supplied origin",
                "resultant_moment_knm": moment_resultant,
                "maximum_component_residual_knm": max(abs(value) for value in moment_resultant),
                "tolerance_knm": d["moment_tolerance_knm"],
                "satisfied": moment_satisfied,
            },
            {
                "clause": "4.5.1",
                "condition": "boundary conditions are verified",
                "satisfied": d["boundary_conditions_verified"],
                "evidence_reference": d["boundary_conditions_evidence_reference"],
            },
            {
                "clause": "4.5.1",
                "condition": "applied loads and support reactions are both supplied",
                "action_counts": action_counts,
                "satisfied": action_types_satisfied,
            },
        ]
        return result(
            op,
            ["4.5.1"],
            {
                "force_resultant_kn": force_resultant,
                "moment_resultant_knm": moment_resultant,
                "action_counts": action_counts,
                "global_equilibrium_satisfied": (
                    force_satisfied and moment_satisfied and action_types_satisfied
                ),
            },
            checks,
            limitations=[
                "The global resultants are calculated from supplied action effects; include all "
                "applied loads and support reactions with consistent signs and coordinates.",
                "This does not check member/joint equilibrium, the plastic action distribution, or "
                "the underlying structural analysis. Boundary conditions remain supplied evidence.",
            ],
        )
    if op == "notional_horizontal_load":
        return result(
            op,
            ["3.2.4"],
            {
                "notional_horizontal_load_kn": 0.002 * d["floor_vertical_design_load_kn"],
            },
            limitations=[
                "Multi-storey dead/live combinations only; excludes stability limit state.",
            ],
        )
    if op == "stability":
        resistance = 0.9 * d["stabilising_dead_effect"] + d["resisting_design_capacity"]
        check = {
            "clause": "3.3",
            "resistance": resistance,
            "design_effect": d["destabilising_design_effect"],
            "satisfied": resistance >= d["destabilising_design_effect"],
        }
        return result(
            op,
            ["3.3"],
            {"design_resistance_effect": resistance},
            [check],
            [
                "Use matching effects and units; resistance already includes the appropriate phi.",
            ],
        )
    check = {
        "clause": "3.5.3",
        "utilisation": abs(d["deflection_mm"]) / d["deflection_limit_mm"],
        "satisfied": abs(d["deflection_mm"]) <= d["deflection_limit_mm"],
    }
    return result(
        op,
        ["3.5.2", "3.5.3"],
        {"limit_basis": d["limit_basis"]},
        [check],
        [
            "Use serviceability combinations and elastic deflections; check vibration separately.",
        ],
    )
