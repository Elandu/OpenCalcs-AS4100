# SPDX-License-Identifier: AGPL-3.0-only
"""Optional independent corotational cantilever cross-check using OpenSeesPy 3.8.0."""

import json
from math import isclose

import openseespy.opensees as ops


def analyze(subdivisions, load_case):
    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 3)
    length_mm = 4000.0
    for index in range(subdivisions + 1):
        ops.node(index + 1, 0.0, length_mm * index / subdivisions)
    ops.fix(1, 1, 1, 1)
    ops.geomTransf("Corotational", 1)
    for index in range(subdivisions):
        ops.element(
            "elasticBeamColumn",
            index + 1,
            index + 1,
            index + 2,
            10_000.0,
            200_000.0,
            8e6,
            1,
        )

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    if load_case == "tip_force":
        ops.load(subdivisions + 1, 10_000.0, -50_000.0, 0.0)
    elif load_case == "uniform_member_load":
        ops.load(subdivisions + 1, 0.0, -50_000.0, 0.0)
        for tag in range(1, subdivisions + 1):
            ops.eleLoad("-ele", tag, "-type", "-beamUniform", 2.5, 0.0)
    else:
        raise ValueError(f"Unsupported reference load case: {load_case}")
    ops.constraints("Plain")
    ops.numberer("RCM")
    ops.system("BandGeneral")
    ops.test("NormDispIncr", 1e-10, 100, 0)
    ops.algorithm("Newton")
    ops.integrator("LoadControl", 0.1)
    ops.analysis("Static")
    status = ops.analyze(10)
    if status != 0:
        raise RuntimeError(f"OpenSees nonlinear analysis failed with status {status}.")

    ops.reactions()
    maximum_element_end_moment_knm = (
        max(
            abs(moment)
            for tag in range(1, subdivisions + 1)
            for moment in (
                ops.eleResponse(tag, "localForce")[2],
                ops.eleResponse(tag, "localForce")[5],
            )
        )
        / 1e6
    )
    return {
        "load_case": load_case,
        "subdivisions": subdivisions,
        "top_ux_mm": ops.nodeDisp(subdivisions + 1, 1),
        "top_uy_mm": ops.nodeDisp(subdivisions + 1, 2),
        "top_rz_rad": ops.nodeDisp(subdivisions + 1, 3),
        "base_reaction_fx_kn": ops.nodeReaction(1, 1) / 1000.0,
        "base_reaction_fy_kn": ops.nodeReaction(1, 2) / 1000.0,
        "base_reaction_moment_knm": ops.nodeReaction(1, 3) / 1e6,
        "maximum_element_end_moment_knm": maximum_element_end_moment_knm,
    }


def main():
    version = str(ops.version())
    if version != "3.8.0":
        raise RuntimeError(f"This recorded reference uses OpenSees 3.8.0, found {version}.")
    results = [
        analyze(subdivisions, load_case)
        for load_case in ("tip_force", "uniform_member_load")
        for subdivisions in (8, 16, 32)
    ]
    reference_cases = {
        "tip_force": (166.4040891604727, 48.27748141928913, 48.27748141928913),
        "uniform_member_load": (
            62.15323697933561,
            23.105265467937336,
            -23.105265467937336,
        ),
    }
    for load_case, expected in reference_cases.items():
        result = next(
            item
            for item in results
            if item["load_case"] == load_case and item["subdivisions"] == 16
        )
        actual = (
            abs(result["top_ux_mm"]),
            result["maximum_element_end_moment_knm"],
            result["base_reaction_moment_knm"],
        )
        if not all(
            isclose(value, reference, rel_tol=0.0, abs_tol=0.0001)
            for value, reference in zip(actual, expected, strict=True)
        ):
            raise AssertionError(f"OpenSees reference mismatch for {load_case}: {actual}")
    print(json.dumps({"opensees_version": version, "results": results}, indent=2))


if __name__ == "__main__":
    main()
