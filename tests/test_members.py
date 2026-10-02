"""Independent arithmetic and published table checks for member primitives."""

import pytest

from opencalcs_as4100.members import run_members


def compression(length=900, constant=0):
    return {
        "operation": "compression",
        "yield_strength_mpa": 250,
        "gross_area_mm2": 1000,
        "net_area_mm2": 1000,
        "effective_area_mm2": 1000,
        "effective_length_x_mm": length,
        "effective_length_y_mm": length,
        "radius_x_mm": 10,
        "radius_y_mm": 10,
        "section_constant_x": constant,
        "section_constant_y": constant,
        "action_kn": 100,
        "geometry": "doubly_symmetric",
    }


def test_member_yield_strength_scope_boundary():
    data = compression()
    data["yield_strength_mpa"] = 690
    assert run_members(data)["values"]["section_capacity_kn"] > 0
    data["yield_strength_mpa"] = 690.1
    with pytest.raises(ValueError, match="690 MPa"):
        run_members(data)


@pytest.mark.parametrize(
    "slenderness,constant,expected",
    [
        (20, 0, 0.978),
        (50, 0, 0.861),
        (90, 0, 0.610),
        (150, 0, 0.293),
        (90, -1, 0.737),
        (90, -0.5, 0.675),
        (90, 0.5, 0.547),
        (90, 1, 0.487),
        (250, 1, 0.110),
    ],
)
def test_compression_against_standard_table(slenderness, constant, expected):
    # Table 6.3.3(C), rounded to three decimals. No equation-generated oracle.
    out = run_members(compression(slenderness * 10, constant))
    assert out["values"]["reduction_x"] == pytest.approx(expected, abs=0.0006)


def test_compression_axes_and_monotonicity():
    values = [
        run_members(compression(length))["values"]["reduction_x"]
        for length in (10, 135, 300, 900, 2000, 10000)
    ]
    assert values == sorted(values, reverse=True)
    assert values[0] == pytest.approx(1)
    d = compression()
    d["effective_length_y_mm"] = 1800
    out = run_members(d)
    assert out["values"]["member_capacity_y_kn"] < out["values"]["member_capacity_x_kn"]
    assert out["values"]["section_capacity_kn"] == 250


def plate(width=90, edges="one", stress="uniform", residual="HR"):
    return {
        "operation": "plate",
        "yield_strength_mpa": 250,
        "elastic_modulus_mm3": 100000,
        "plastic_modulus_mm3": 130000,
        "plate": {
            "width_mm": width,
            "thickness_mm": 10,
            "edges": edges,
            "stress": stress,
            "residual": residual,
        },
    }


@pytest.mark.parametrize(
    "width,category,modulus",
    [
        (90, "compact", 130000),
        (125, "non_compact", 115000),
        (160, "non_compact", 100000),
        (320, "slender", 50000),
    ],
)
def test_flat_plate_boundaries_and_hand_arithmetic(width, category, modulus):
    out = run_members(plate(width))["values"]
    assert out["classification"] == category
    assert out["effective_modulus_mm3"] == pytest.approx(modulus)
    assert out["compression_effective_width_mm"] == pytest.approx(min(width, 160))


def test_outstand_gradient_and_circular_distinct_rules():
    out = run_members(plate(500, stress="outstand_gradient"))["values"]
    assert out["effective_modulus_mm3"] == 25000  # (25/50)^2 * 100000
    out = run_members(plate(4800, edges="circular"))["values"]
    assert out["effective_modulus_mm3"] == 25000  # min(sqrt(1/4), (1/2)^2)
    assert out["compression_effective_width_mm"] == pytest.approx(1260.75)


def shear(depth=820):
    return {
        "operation": "shear",
        "yield_strength_mpa": 250,
        "web_area_mm2": 1000,
        "panel_depth_mm": depth,
        "web_thickness_mm": 10,
        "action_kn": 50,
        "moment_action_knm": 0,
        "section_moment_capacity_knm": 100,
    }


def test_shear_and_bending_thresholds():
    out = run_members(shear())["values"]
    assert out["shear_capacity_kn"] == 150
    out = run_members(shear(1640))["values"]
    assert out["shear_capacity_kn"] == 37.5
    d = shear()
    d["moment_action_knm"] = 67.5
    assert run_members(d)["values"]["shear_bending_capacity_kn"] == 150
    d["moment_action_knm"] = 90
    assert run_members(d)["values"]["shear_bending_capacity_kn"] == pytest.approx(90)
    d["moment_action_knm"] = 90.1
    assert run_members(d)["values"]["shear_bending_capacity_kn"] == 0


def test_stiffened_shear_matches_table_and_no_unverified_credit():
    d = shear(1200)
    d.update(stiffener_spacing_mm=1200, tension_field=True)
    out = run_members(d)["values"]
    # Table 5.11.5.2: lambda=120, s/d=1, alpha_v*alpha_d = 0.930.
    assert out["shear_capacity_kn"] / 150 == pytest.approx(0.930, abs=0.0006)
    d["tension_field"] = False
    assert run_members(d)["values"]["shear_capacity_kn"] < out["shear_capacity_kn"]


def test_equal_flanged_lateral_buckling_hand_case():
    d = {
        "operation": "bending",
        "section_capacity_knm": 100,
        "iy_mm4": 10000000,
        "torsion_constant_mm4": 100000,
        "warping_constant_mm6": 0,
        "effective_length_mm": 3141.592653589793,
        "moment_factor": 1,
        "action_knm": 10,
        "geometry": "equal_flanged_open",
    }
    out = run_members(d)["values"]
    # le=1000*pi => pi²E Iy/le²=2,000,000 N; GJ=8e9 N.mm².
    assert out["reference_buckling_moment_knm"] == pytest.approx(126.491106406735)
    # Ms/Mo=sqrt(0.625); 60*(sqrt(3.625)-sqrt(0.625))=66.8024316854.
    assert out["member_capacity_knm"] == pytest.approx(66.8024316854)
    d["effective_length_mm"] *= 2
    assert run_members(d)["values"]["member_capacity_knm"] < out["member_capacity_knm"]


def interaction(mode="compression"):
    return {
        "operation": "interaction",
        "axial_mode": mode,
        "section_axial_capacity_kn": 1000,
        "member_axial_x_kn": 800,
        "member_axial_y_kn": 500,
        "section_moment_x_knm": 100,
        "section_moment_y_knm": 50,
        "member_moment_x_knm": 70,
        "axial_action_kn": 90,
        "moment_x_knm": 10,
        "moment_y_knm": 5,
    }


def test_general_interaction_independent_arithmetic():
    out = run_members(interaction())
    assert out["values"]["section_reduced_x_knm"] == 90
    assert out["values"]["in_plane_x_knm"] == 87.5
    assert out["values"]["out_of_plane_x_knm"] == 56
    assert out["checks"]["section_combined"]["utilisation"] == pytest.approx(0.3222222222)
    out = run_members(interaction("tension"))
    assert out["values"]["out_of_plane_x_knm"] == pytest.approx(77)


def test_axial_failure_does_not_pass_zero_moment_interaction():
    d = interaction()
    d.update(axial_action_kn=500, moment_x_knm=0, moment_y_knm=0)
    out = run_members(d)
    assert not out["checks"]["member_combined"]["satisfied"]
    assert not out["checks"]["member_axial_y"]["satisfied"]


def test_tension_force_distribution_conditions():
    d = {
        "operation": "tension_distribution",
        "configuration": "both_flanges",
        "connection_conditions_verified": True,
        "connection_length_mm": 200,
        "member_depth_mm": 200,
    }
    assert run_members(d)["values"]["tension_distribution_factor"] == 0.85
    d["connection_length_mm"] = 199
    with pytest.raises(ValueError, match="length"):
        run_members(d)


@pytest.mark.parametrize(
    "mutate",
    [
        {"gross_area_mm2": 900},
        {"action_kn": float("nan")},
        {"geometry": "angle"},
        {"section_constant_x": 0.25},
    ],
)
def test_invalid_or_unsupported_inputs_rejected(mutate):
    d = compression()
    d.update(mutate)
    with pytest.raises(ValueError):
        run_members(d)


def test_unknown_input_and_incompatible_plate_rejected():
    d = plate()
    d["unknown"] = 123
    with pytest.raises(ValueError):
        run_members(d)
    with pytest.raises(ValueError, match="incompatible"):
        run_members(plate(stress="internal_gradient"))
    with pytest.raises(ValueError, match="effective-section"):
        run_members(plate(1200, edges="both", stress="internal_gradient"))


def test_extreme_magnitudes_fail_cleanly():
    d = compression(1e300)
    with pytest.raises(ValueError):
        run_members(d)
