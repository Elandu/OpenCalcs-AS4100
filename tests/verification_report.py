"""Run independent AS 4100 regression cases and emit a machine-readable report."""

import json
import sys
from math import isclose
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from opencalcs_as4100.connections import run_connections  # noqa: E402
from opencalcs_as4100.webs import run_webs  # noqa: E402


def fillet(length):
    return run_connections(
        {
            "check_type": "fillet",
            "weld_strength_mpa": 490,
            "throat_mm": 4.2,
            "effective_length_mm": 100,
            "quality": "SP",
            "thin_rhs_longitudinal": False,
            "lap_length_mm": length,
            "action_kn": 50,
        }
    )["checks"]["weld"]["design_capacity_kn"]


def stiffener(**changes):
    return {
        "operation": "load_bearing_stiffener",
        "web_bearing_yield_kn": 100,
        "stiffener_area_mm2": 1000,
        "contact_stiffener_area_mm2": 500,
        "web_yield_mpa": 250,
        "stiffener_yield_mpa": 450,
        "web_thickness_mm": 10,
        "clear_web_depth_mm": 200,
        "panel_spacing_mm": 300,
        "radius_of_gyration_mm": 50,
        "both_flanges_rotation_restrained": True,
        "available_web_width_left_mm": 200,
        "available_web_width_right_mm": 0,
        "stiffener_outstand_mm": 150,
        "stiffener_thickness_mm": 10,
        "outer_edge_continuously_stiffened": False,
        "bearing_action_kn": 100,
        **changes,
    }


def expect_close(actual, expected):
    if not isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
        raise AssertionError(f"expected {expected}, observed {actual}")
    return actual


def expect_rejected(callback):
    try:
        callback()
    except ValueError:
        return "rejected"
    raise AssertionError("input was accepted")


def mixed_stiffener():
    result = run_webs(stiffener())
    values = result["values"]
    expect_close(values["bearing_yield_kn"], 325)
    expect_close(values["effective_area_mm2"], 2500)
    expect_close(values["outstand_limit_mm"], 111.80339887498948)
    if result["checks"][2]["satisfied"]:
        raise AssertionError("150 mm outstand was accepted")
    return {
        "bearing_yield_kn": values["bearing_yield_kn"],
        "outstand_limit_mm": values["outstand_limit_mm"],
        "outstand_satisfied": result["checks"][2]["satisfied"],
    }


def zero_restrained_flanges():
    return expect_rejected(
        lambda: run_webs(
            {
                "operation": "web_bearing",
                "section_type": "i_or_channel",
                "web_thickness_mm": 10,
                "web_yield_mpa": 300,
                "clear_web_depth_mm": 200,
                "bearing_width_at_flange_mm": 100,
                "bearing_width_at_neutral_axis_mm": 200,
                "restrained_flange_count": 0,
                "bearing_action_kn": 100,
            }
        )
    )


def over_scope_yield():
    return expect_rejected(lambda: run_webs(stiffener(stiffener_yield_mpa=690.1)))


def main():
    cases = {
        "fillet_lap_1700_mm": lambda: expect_close(fillet(1700), 98.784),
        "fillet_lap_8000_mm": lambda: expect_close(fillet(8000), 61.24608),
        "fillet_lap_8001_mm": lambda: expect_close(fillet(8001), 61.24608),
        "mixed_stiffener_contact_and_outstand": mixed_stiffener,
        "zero_restrained_flanges": zero_restrained_flanges,
        "yield_above_690_mpa": over_scope_yield,
    }
    results = []
    for name, check in cases.items():
        try:
            observed = check()
            results.append({"case": name, "status": "passed", "observed": observed})
        except (AssertionError, ValueError) as exc:
            results.append({"case": name, "status": "failed", "error": str(exc)})
    passed = sum(item["status"] == "passed" for item in results)
    print(json.dumps({"passed": passed, "total": len(results), "results": results}, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
