# SPDX-License-Identifier: AGPL-3.0-only
"""AS 4100 sections 3/4 numerical design-action checks, reviewed against scanned text."""

from math import isfinite, pi

from .validation import NONNEGATIVE, POSITIVE, SIGNED, object_schema, result, validate

SCHEMAS = {
    "euler_buckling": object_schema(
        {
            "operation": {"const": "euler_buckling"},
            "elastic_modulus_mpa": POSITIVE,
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
