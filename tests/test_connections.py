"""Independent numeric benchmarks and connection domain boundaries."""

from math import pi

import pytest

from opencalcs_as4100.connections import run_connections


def bolt(**changes):
    return {
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
        **changes,
    }


def test_bolt_hand_benchmark():
    r = run_connections(bolt())
    # 0.8 * 0.62 * 830 * 225 / 1000 = 92.628 kN
    assert r["checks"]["shear"]["design_capacity_kn"] == pytest.approx(92.628)
    assert r["checks"]["tension"]["design_capacity_kn"] == pytest.approx(162.68)
    assert r["checks"]["interaction"]["utilisation"] == pytest.approx(
        (50 / 92.628) ** 2 + (80 / 162.68) ** 2
    )


@pytest.mark.parametrize(
    "length,expected", [(299, 1), (300, 1), (800, 0.875), (1300, 0.75), (1301, 0.75)]
)
def test_lap_boundaries(length, expected):
    assert run_connections(bolt(lap_length_mm=length))["intermediate"][
        "lap_factor"
    ] == pytest.approx(expected)


def test_grade_filler_and_plain_planes():
    r = run_connections(bolt(grade="10.9", filler_thickness_mm=10))
    assert r["checks"]["shear"]["design_capacity_kn"] == pytest.approx(92.628 * 0.83 * 0.9384)
    r = run_connections(bolt(grade="10.9", threaded_planes=0, plain_planes=2))
    assert r["intermediate"]["ductility_factor"] == 1
    assert r["checks"]["shear"]["design_capacity_kn"] == pytest.approx(
        0.8 * 0.62 * 830 * 628 / 1000
    )


def test_bearing_edge_governs():
    r = run_connections(
        {
            "check_type": "bearing",
            "diameter_mm": 20,
            "ply_thickness_mm": 10,
            "ultimate_strength_mpa": 440,
            "effective_edge_distance_mm": 30,
            "action_kn": 100,
        }
    )
    assert r["checks"]["bearing"]["design_capacity_kn"] == pytest.approx(118.8)


@pytest.mark.parametrize(
    "hole,capacity",
    [("standard", 49), ("short_slot", 41.65), ("oversize", 41.65), ("long_slot", 34.3)],
)
def test_slip_service_phi_and_interaction(hole, capacity):
    r = run_connections(
        {
            "check_type": "slip",
            "slip_factor": 0.35,
            "interfaces": 1,
            "installation_tension_kn": 200,
            "hole_type": hole,
            "shear_action_kn": capacity / 2,
            "tension_action_kn": 70,
        }
    )
    assert r["checks"]["slip"]["design_capacity_kn"] == pytest.approx(capacity)
    assert r["checks"]["interaction"]["utilisation"] == pytest.approx(1)


def test_block_shear_hand_benchmark():
    r = run_connections(
        {
            "check_type": "block_shear",
            "yield_strength_mpa": 300,
            "ultimate_strength_mpa": 440,
            "gross_shear_area_mm2": 2000,
            "net_shear_area_mm2": 1500,
            "net_tension_area_mm2": 500,
            "uniform_tension": False,
            "action_kn": 200,
        }
    )
    # Ru=min(396+110,360+110)=470kN; phi=0.75
    assert r["checks"]["block_shear"]["design_capacity_kn"] == pytest.approx(352.5)


def test_pin_hand_benchmark():
    r = run_connections(
        {
            "check_type": "pin",
            "yield_strength_mpa": 300,
            "diameter_mm": 30,
            "shear_planes": 2,
            "ply_thickness_mm": 10,
            "rotates": True,
            "shear_action_kn": 100,
            "bearing_action_kn": 40,
            "moment_action_knm": 1,
        }
    )
    assert r["checks"]["shear"]["design_capacity_kn"] == pytest.approx(
        0.8 * 0.62 * 300 * 2 * pi * 225 / 1000
    )
    assert r["checks"]["bearing"]["design_capacity_kn"] == pytest.approx(50.4)
    assert r["checks"]["bending"]["design_capacity_knm"] == pytest.approx(1.08)


@pytest.mark.parametrize(
    "quality,thin,phi", [("SP", False, 0.8), ("SP", True, 0.7), ("GP", False, 0.6)]
)
def test_fillet_hand_benchmark(quality, thin, phi):
    r = run_connections(
        {
            "check_type": "fillet",
            "weld_strength_mpa": 490,
            "throat_mm": 4.2,
            "effective_length_mm": 100,
            "quality": quality,
            "thin_rhs_longitudinal": thin,
            "lap_length_mm": 0,
            "action_kn": 50,
        }
    )
    assert r["checks"]["weld"]["design_capacity_kn"] == pytest.approx(123.48 * phi)


@pytest.mark.parametrize(
    "lap_length_mm,lap_factor",
    [(1700, 1), (1701, 1.10 - 0.06 * 1.701), (8000, 0.62), (8001, 0.62)],
)
def test_fillet_lap_length_boundaries(lap_length_mm, lap_factor):
    r = run_connections(
        {
            "check_type": "fillet",
            "weld_strength_mpa": 490,
            "throat_mm": 4.2,
            "effective_length_mm": 100,
            "quality": "SP",
            "thin_rhs_longitudinal": False,
            "lap_length_mm": lap_length_mm,
            "action_kn": 50,
        }
    )
    assert r["checks"]["weld"]["design_capacity_kn"] == pytest.approx(
        0.8 * 0.6 * 490 * 4.2 * 100 * lap_factor / 1000
    )


@pytest.mark.parametrize("quality,expected", [("SP", 270), ("GP", 180)])
def test_complete_butt(quality, expected):
    r = run_connections(
        {
            "check_type": "complete_butt",
            "weaker_part_nominal_capacity_kn": 300,
            "quality": quality,
            "qualified_matching_consumable": True,
            "action_kn": 100,
        }
    )
    assert r["checks"]["weld"]["design_capacity_kn"] == expected


def test_plug_slot():
    r = run_connections(
        {
            "check_type": "plug_slot",
            "weld_strength_mpa": 490,
            "effective_area_mm2": 1000,
            "quality": "SP",
            "permitted_shear_application": True,
            "action_kn": 200,
        }
    )
    assert r["checks"]["weld"]["design_capacity_kn"] == pytest.approx(235.2)


def test_layout_and_hole_deduction():
    r = run_connections(
        {
            "check_type": "layout",
            "diameter_mm": 20,
            "thinnest_ply_mm": 10,
            "pitch_mm": 50,
            "edge_distance_mm": 35,
            "edge_type": "sheared",
            "pitch_case": "general",
        }
    )
    assert all(c["satisfied"] for c in r["checks"].values())
    r = run_connections(
        {
            "check_type": "hole_deduction",
            "gross_area_mm2": 2000,
            "thickness_mm": 10,
            "straight_hole_width_sum_mm": 22,
            "zigzag_hole_width_sum_mm": 44,
            "stagger_pairs": [[30, 50]],
        }
    )
    assert r["intermediate"]["net_area_mm2"] == pytest.approx(1605)


def test_bolt_group_vector_superposition_and_equilibrium():
    r = run_connections(
        bolt(
            check_type="bolt_group",
            shear_action_kn=0,
            tension_action_kn=0,
            points_mm=[[-50, -50], [50, -50], [50, 50], [-50, 50]],
            force_x_kn=40,
            force_y_kn=20,
            moment_z_knm=2,
        )
    )
    forces = r["intermediate"]["bolt_forces_kn"]
    assert forces[0] == [15, 0]
    assert sum(f[0] for f in forces) == pytest.approx(40)
    assert sum(f[1] for f in forces) == pytest.approx(20)
    points = [[-50, -50], [50, -50], [50, 50], [-50, 50]]
    assert sum(
        x * fy - y * fx for (x, y), (fx, fy) in zip(points, forces, strict=True)
    ) == pytest.approx(2000)


def weld_group(**changes):
    return {
        "check_type": "weld_group",
        "weld_strength_mpa": 490,
        "throat_mm": 4,
        "quality": "SP",
        "segments_mm": [
            [[-50, -50], [50, -50]],
            [[50, -50], [50, 50]],
            [[50, 50], [-50, 50]],
            [[-50, 50], [-50, -50]],
        ],
        **{f"force_{a}_kn": 0 for a in "xyz"},
        **{f"moment_{a}_knm": 0 for a in "xyz"},
        **changes,
    }


def test_weld_group_pure_shear_and_bending():
    r = run_connections(weld_group(force_x_kn=40))
    assert r["checks"]["weld_group"]["utilisation"] == pytest.approx(0.1 / 0.9408)
    r = run_connections(weld_group(moment_x_knm=2, moment_y_knm=1))
    assert r["intermediate"]["ix_mm3"] == pytest.approx(2e6 / 3)
    assert max(abs(f[2]) for f in r["intermediate"]["endpoint_forces_kn_per_mm"]) == pytest.approx(
        0.225
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"ultimate_strength_mpa": float("nan")},
        {"lap_length_mm": float("inf")},
        {"filler_thickness_mm": 20},
        {"threaded_planes": 0, "plain_planes": 0},
        {"threaded_planes": True},
        {"unknown": 1},
        {"tensile_area_mm2": 100},
    ],
)
def test_reject_invalid_bolts(changes):
    with pytest.raises(ValueError):
        run_connections(bolt(**changes))


def test_reject_degenerate_group():
    with pytest.raises(ValueError):
        run_connections(weld_group(segments_mm=[[[0, 0], [100, 0]]], moment_x_knm=1))


def test_reject_overlapping_welds():
    with pytest.raises(ValueError, match="overlap"):
        run_connections(weld_group(segments_mm=[[[0, 0], [100, 0]], [[50, 0], [150, 0]]]))


def test_reject_numeric_overflow():
    with pytest.raises(ValueError):
        run_connections(bolt(shank_area_mm2=1e308, plain_planes=2))


def test_reject_yield_strength_above_as4100_scope():
    data = {
        "check_type": "pin",
        "yield_strength_mpa": 690,
        "diameter_mm": 30,
        "shear_planes": 2,
        "ply_thickness_mm": 10,
        "rotates": True,
        "shear_action_kn": 100,
        "bearing_action_kn": 40,
        "moment_action_knm": 1,
    }
    assert run_connections(data)["checks"]["shear"]["satisfied"]
    with pytest.raises(ValueError, match="690 MPa"):
        run_connections({**data, "yield_strength_mpa": 690.1})
