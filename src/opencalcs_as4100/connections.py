"""Connection component calculations reviewed against AS 4100:2020 Section 9."""

from collections.abc import Mapping
from math import cos, hypot, isfinite, pi, radians, sin, sqrt
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
    "fillet_design": {
        "weld_strength_mpa": P,
        "quality": QUALITY,
        "leg_1_mm": P,
        "leg_2_mm": P,
        "included_angle_deg": {"type": "number", "minimum": 5, "maximum": 175},
        "root_gap_mm": N,
        "thickest_part_mm": P,
        "thinnest_part_mm": P,
        "edge_material_thickness_mm": P,
        "edge_built_out_verified": BOOL,
        "reinforces_butt_weld": BOOL,
        "overall_length_per_segment_mm": P,
        "segment_count": {"type": "integer", "minimum": 1, "maximum": 10000},
        "intermittent_segment": BOOL,
        "clear_spacing_mm": N,
        "at_built_up_member_end": BOOL,
        "member_force_type": {"enum": ["compression", "tension", "other"]},
        "forms_built_up_member": BOOL,
        "parallel_weld_count": {"type": "integer", "enum": [1, 2]},
        "parallel_load_share_verified": BOOL,
        "transverse_weld_spacing_mm": N,
        "thin_rhs_longitudinal": BOOL,
        "lap_length_mm": N,
        "action_kn": N,
    },
    "built_up_component_end_weld": {
        "connected_component_width_mm": P,
        "weld_length_per_joint_line_mm": P,
        "side_fillet_only": BOOL,
        "tapered_component": BOOL,
        "widest_component_width_mm": P,
        "taper_length_mm": N,
    },
    "cap_plate_weld": {
        "member_width_at_contact_face_mm": P,
        "weld_length_per_joint_line_mm": P,
    },
    "beam_compression_member_weld": {
        "beam_depth_mm": P,
        "compression_member_max_dimension_mm": P,
        "connection_restraint": {"enum": ["unrestrained", "restrained"]},
        "weld_length_between_beam_faces_mm": P,
        "weld_extension_above_top_mm": N,
        "weld_extension_below_bottom_mm": N,
    },
    "packing_construction": {
        "packing_thickness_mm": P,
        "too_thin_for_adequate_welds": BOOL,
        "too_thin_to_prevent_buckling": BOOL,
        "required_edge_weld_sizes_mm": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": P,
        },
        "provided_edge_weld_sizes_mm": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "items": N,
        },
        "trimmed_flush_with_member_edges": BOOL,
        "extends_beyond_member_edges": BOOL,
        "welded_to_fitted_piece": BOOL,
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


def _fillet_strength_check(d, throat_mm, effective_length_mm, clause="9.6.3.10"):
    lap_m = d["lap_length_mm"] / 1000
    lap_factor = 1 if lap_m <= 1.7 else (1.10 - 0.06 * lap_m if lap_m <= 8 else 0.62)
    if d["thin_rhs_longitudinal"]:
        if d["quality"] != "SP":
            raise ValueError("Thin RHS longitudinal fillet requires SP quality.")
        phi = 0.7
    else:
        phi = 0.8 if d["quality"] == "SP" else 0.6
    nominal_capacity = (
        0.6 * d["weld_strength_mpa"] * throat_mm * effective_length_mm * lap_factor / 1000
    )
    return (
        _check(nominal_capacity, phi, d["action_kn"], clause),
        {"lap_factor": lap_factor, "capacity_factor": phi},
    )


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
    elif k == "built_up_component_end_weld":
        applicable = d["side_fillet_only"]
        minimum_length = None
        if applicable:
            minimum_length = d["connected_component_width_mm"]
            if d["tapered_component"]:
                minimum_length = max(minimum_length, d["widest_component_width_mm"])
                minimum_length = max(minimum_length, d["taper_length_mm"])
        weld_length = d["weld_length_per_joint_line_mm"]
        c["built_up_termination"] = {
            "clause": "9.6.3.9(a)",
            "applicable": applicable,
            "minimum_length_mm": minimum_length,
            "provided_length_per_joint_line_mm": weld_length,
            "satisfied": not applicable or weld_length >= minimum_length,
        }
        intermediate = {
            "connected_component_width_mm": d["connected_component_width_mm"],
            "widest_component_width_mm": d["widest_component_width_mm"],
            "taper_length_mm": d["taper_length_mm"],
        }
    elif k == "cap_plate_weld":
        minimum_length = d["member_width_at_contact_face_mm"]
        weld_length = d["weld_length_per_joint_line_mm"]
        c["built_up_termination"] = {
            "clause": "9.6.3.9(b)",
            "minimum_length_per_joint_line_mm": minimum_length,
            "provided_length_per_joint_line_mm": weld_length,
            "satisfied": weld_length >= minimum_length,
        }
        intermediate = {"member_width_at_contact_face_mm": d["member_width_at_contact_face_mm"]}
    elif k == "beam_compression_member_weld":
        required_extension = d["compression_member_max_dimension_mm"]
        checks = {
            "between_beam_faces": {
                "clause": "9.6.3.9(c)",
                "required_mm": d["beam_depth_mm"],
                "provided_mm": d["weld_length_between_beam_faces_mm"],
                "satisfied": d["weld_length_between_beam_faces_mm"] >= d["beam_depth_mm"],
            },
            "below_beam": {
                "clause": "9.6.3.9(c)(i)/(ii)",
                "required_mm": required_extension,
                "provided_mm": d["weld_extension_below_bottom_mm"],
                "satisfied": d["weld_extension_below_bottom_mm"] >= required_extension,
            },
        }
        if d["connection_restraint"] == "restrained":
            checks["above_beam"] = {
                "clause": "9.6.3.9(c)(ii)",
                "required_mm": required_extension,
                "provided_mm": d["weld_extension_above_top_mm"],
                "satisfied": d["weld_extension_above_top_mm"] >= required_extension,
            }
        c["built_up_termination"] = {
            "clause": "9.6.3.9(c)",
            "connection_restraint": d["connection_restraint"],
            "checks": checks,
            "satisfied": all(check["satisfied"] for check in checks.values()),
        }
        intermediate = {
            "beam_depth_mm": d["beam_depth_mm"],
            "compression_member_max_dimension_mm": required_extension,
        }
    elif k == "fillet_design":
        if d["thinnest_part_mm"] > d["thickest_part_mm"]:
            raise ValueError("Thinnest part cannot be thicker than the thickest part.")
        if d["parallel_weld_count"] == 2 and not d["parallel_load_share_verified"]:
            raise ValueError("Load sharing between the two parallel welds must be verified.")
        leg_1 = d["leg_1_mm"] - d["root_gap_mm"]
        leg_2 = d["leg_2_mm"] - d["root_gap_mm"]
        if min(leg_1, leg_2) <= 0:
            raise ValueError("Root gap must leave a positive inscribed fillet triangle.")
        thickness = d["thickest_part_mm"]
        minimum_table_size = (
            3 if thickness <= 7 else 4 if thickness <= 10 else 5 if thickness <= 15 else 6
        )
        minimum_size = (
            0 if d["reinforces_butt_weld"] else min(minimum_table_size, d["thinnest_part_mm"])
        )
        edge_thickness = d["edge_material_thickness_mm"]
        maximum_edge_size = (
            edge_thickness
            if edge_thickness < 6 or d["edge_built_out_verified"]
            else edge_thickness - 1
        )
        size_checks = {
            "minimum_size": {
                "required_mm": minimum_size,
                "provided_leg_1_mm": leg_1,
                "provided_leg_2_mm": leg_2,
                "satisfied": min(leg_1, leg_2) >= minimum_size,
            },
            "maximum_size_along_edge": {
                "maximum_mm": maximum_edge_size,
                "largest_provided_leg_mm": max(leg_1, leg_2),
                "built_out_verified": d["edge_built_out_verified"],
                "satisfied": max(leg_1, leg_2) <= maximum_edge_size,
            },
        }
        theta = radians(d["included_angle_deg"])
        opposite_side = sqrt(leg_1**2 + leg_2**2 - 2 * leg_1 * leg_2 * cos(theta))
        geometric_throat = leg_1 * leg_2 * sin(theta) / opposite_side
        nominal_size = max(leg_1, leg_2)
        segment_length = d["overall_length_per_segment_mm"]
        length_reduction_factor = min(1, segment_length / (4 * nominal_size))
        design_throat = geometric_throat * length_reduction_factor
        intermittent_minimum_length = max(40, 4 * nominal_size)
        total_effective_length = segment_length * d["segment_count"] * d["parallel_weld_count"]
        effective_area = design_throat * total_effective_length
        length_checks = {
            "overall_length_per_segment_mm": segment_length,
            "segment_count_per_weld_line": d["segment_count"],
            "parallel_weld_count": d["parallel_weld_count"],
            "total_effective_length_mm": total_effective_length,
            "length_based_size_reduction_factor": length_reduction_factor,
            "design_throat_mm": design_throat,
            "effective_area_mm2": effective_area,
            "intermittent_minimum_length_mm": intermittent_minimum_length,
            "satisfied": not d["intermittent_segment"]
            or segment_length >= intermittent_minimum_length,
        }
        c["weld_size"] = {
            "clause": "9.6.3.2; 9.6.3.3",
            "checks": size_checks,
            "satisfied": all(check["satisfied"] for check in size_checks.values()),
        }
        c["weld_length_and_area"] = {
            "clause": "9.6.3.5; 9.6.3.6",
            **length_checks,
        }
        clauses = ["9.6.3.1", "9.6.3.2", "9.6.3.3", "9.6.3.4", "9.6.3.5", "9.6.3.6"]
        if d["parallel_weld_count"] == 2 and d["forms_built_up_member"]:
            transverse_limit = (
                min(16 * d["thinnest_part_mm"], 200)
                if d["member_force_type"] == "tension"
                else 32 * d["thinnest_part_mm"]
            )
            c["parallel_weld_spacing"] = {
                "clause": "9.6.3.7",
                "provided_mm": d["transverse_weld_spacing_mm"],
                "maximum_mm": transverse_limit,
                "satisfied": d["transverse_weld_spacing_mm"] <= transverse_limit,
            }
            clauses.append("9.6.3.7")
            if d["intermittent_segment"] and d["member_force_type"] != "other":
                clear_spacing_limit = (
                    min(24 * d["thinnest_part_mm"], 300)
                    if d["member_force_type"] == "tension"
                    else min(16 * d["thinnest_part_mm"], 300)
                )
                c["intermittent_clear_spacing"] = {
                    "clause": "9.6.3.8",
                    "provided_mm": d["clear_spacing_mm"],
                    "maximum_mm": clear_spacing_limit,
                    "at_built_up_member_end": d["at_built_up_member_end"],
                    "satisfied": d["at_built_up_member_end"]
                    or d["clear_spacing_mm"] <= clear_spacing_limit,
                }
                clauses.append("9.6.3.8")
        strength_check, strength_intermediate = _fillet_strength_check(
            d, design_throat, total_effective_length
        )
        c["weld_strength"] = {"clause": "9.6.3.10", **strength_check}
        clauses.append("9.6.3.10")
        intermediate = {
            "provided_leg_lengths_after_root_gap_mm": [leg_1, leg_2],
            "geometric_throat_before_length_reduction_mm": geometric_throat,
            "design_throat_mm": design_throat,
            "total_effective_length_mm": total_effective_length,
            "effective_area_mm2": effective_area,
            **strength_intermediate,
        }
    elif k in {"fillet", "complete_butt", "plug_slot"}:
        phi = 0.8 if d["quality"] == "SP" else 0.6
        if k == "fillet":
            clause = "9.6.3.10; 9.6.2.7(c) for incomplete butt"
            c["weld"], intermediate = _fillet_strength_check(
                d, d["throat_mm"], d["effective_length_mm"], clause
            )
        elif k == "complete_butt":
            phi = 0.9 if d["quality"] == "SP" else 0.6
            capacity = d["weaker_part_nominal_capacity_kn"]
            clause = "9.6.2.7(a)"
        else:
            capacity = 0.6 * d["weld_strength_mpa"] * d["effective_area_mm2"] / 1000
            clause = "9.6.4.2"
        if k != "fillet":
            c["weld"] = _check(capacity, phi, d["action_kn"], clause)
    elif k == "packing_construction":
        if len(d["required_edge_weld_sizes_mm"]) != len(d["provided_edge_weld_sizes_mm"]):
            raise ValueError("Provide one actual weld size for every required edge weld.")
        flush_required = (
            d["packing_thickness_mm"] < 6
            or d["too_thin_for_adequate_welds"]
            or d["too_thin_to_prevent_buckling"]
        )
        if flush_required:
            required_sizes = [
                size + d["packing_thickness_mm"] for size in d["required_edge_weld_sizes_mm"]
            ]
            c["trimmed_flush"] = {
                "required": True,
                "provided": d["trimmed_flush_with_member_edges"],
                "satisfied": d["trimmed_flush_with_member_edges"],
                "clause": "9.8",
            }
            c["edge_weld_sizes"] = {
                "required_mm": required_sizes,
                "provided_mm": d["provided_edge_weld_sizes_mm"],
                "satisfied": all(
                    provided >= required
                    for provided, required in zip(
                        d["provided_edge_weld_sizes_mm"], required_sizes, strict=True
                    )
                ),
                "clause": "9.8",
            }
            intermediate = {
                "flush_required": True,
                "edge_weld_size_increase_mm": d["packing_thickness_mm"],
            }
        else:
            c["extends_beyond_edges"] = {
                "required": True,
                "provided": d["extends_beyond_member_edges"],
                "satisfied": d["extends_beyond_member_edges"],
                "clause": "9.8",
            }
            c["welded_to_fitted_piece"] = {
                "required": True,
                "provided": d["welded_to_fitted_piece"],
                "satisfied": d["welded_to_fitted_piece"],
                "clause": "9.8",
            }
            intermediate = {"flush_required": False}
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
