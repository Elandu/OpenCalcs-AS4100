"""Run fixed independent arithmetic/table benchmarks and emit a JSON report."""

import argparse
import json
from math import isclose
from pathlib import Path

from . import __version__
from .advanced_members import run_advanced_members
from .analysis import run_analysis
from .connections import run_connections
from .design_actions import run_design_actions
from .webs import buckling_alpha, run_webs


def verify():
    cases = []

    def record(name, actual, expected, tolerance=1e-9):
        cases.append(
            {
                "name": name,
                "actual": actual,
                "expected": expected,
                "absolute_tolerance": tolerance,
                "passed": isclose(actual, expected, rel_tol=0, abs_tol=tolerance),
            }
        )

    axial = run_analysis(
        {
            "gross_area_mm2": 2000,
            "net_area_mm2": 1500,
            "yield_strength_mpa": 250,
            "ultimate_strength_mpa": 400,
            "tension_distribution_factor": 0.8,
            "compression_form_factor": 0.8,
            "tension_action_kn": 200,
            "compression_action_kn": 135,
        }
    )
    record("7.2 axial tension, hand arithmetic", axial["tension"]["design_capacity_kn"], 367.2)
    record(
        "6.2.1 axial section compression, hand arithmetic",
        axial["compression"]["design_capacity_kn"],
        270,
    )
    for slenderness, expected in [(50, 0.808), (100, 0.485)]:
        record(
            f"Table 6.3.3(C), alpha_b=0.5, lambda={slenderness}",
            buckling_alpha(slenderness, 250),
            expected,
            0.00051,
        )
    euler = run_design_actions(
        {
            "operation": "euler_buckling",
            "elastic_modulus_mpa": 200000,
            "second_moment_mm4": 8e6,
            "member_length_mm": 4000,
            "effective_length_factor": 1,
        }
    )
    record(
        "Pin-ended Euler analytical benchmark",
        euler["values"]["elastic_buckling_load_kn"],
        986.9604401089358,
        1e-8,
    )
    stiffener = run_webs(
        {
            "operation": "longitudinal_stiffener",
            "web_depth_mm": 200,
            "web_thickness_mm": 10,
            "stiffener_area_mm2": 1000,
            "stiffener_second_moment_mm4": 3200000,
            "location": "0.2_depth",
        }
    )
    record(
        "5.16.2 longitudinal stiffener, hand arithmetic",
        stiffener["values"]["minimum_second_moment_mm4"],
        3200000,
    )
    bolt = run_connections(
        {
            "check_type": "bolt",
            "ultimate_strength_mpa": 830,
            "minor_area_mm2": 225,
            "shank_area_mm2": 314,
            "tensile_area_mm2": 245,
            "threaded_planes": 1,
            "plain_planes": 0,
            "grade": "8.8",
            "lap_length_mm": 0,
            "filler_thickness_mm": 0,
            "shear_action_kn": 50,
            "tension_action_kn": 80,
        }
    )
    record(
        "9.3 bolt design shear, hand arithmetic",
        bolt["checks"]["shear"]["design_capacity_kn"],
        92.628,
    )
    bending = run_advanced_members(
        {
            "operation": "buckling_analysis_bending",
            "section_capacity_knm": 100,
            "elastic_buckling_moment_knm": 100,
            "moment_factor": 1,
            "end_configuration": "both_restrained",
            "restraint_and_load_model_verified": True,
            "action_knm": 10,
        }
    )
    record(
        "5.6.4 external buckling moment, hand arithmetic",
        bending["values"]["member_capacity_knm"],
        60,
    )
    return {
        "package_version": __version__,
        "standard": "AS 4100:2020",
        "passed": all(case["passed"] for case in cases),
        "cases": cases,
        "limitations": [
            "Fixed benchmarks verify selected arithmetic and table values.",
            "This report does not establish complete standard coverage.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify()
    rendered = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
