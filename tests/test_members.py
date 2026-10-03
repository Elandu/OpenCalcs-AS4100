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


@pytest.mark.parametrize(
    "width,category,expected_modulus",
    [
        (1150, "non_compact", 100000),
        (1200, "slender", 100000 * (115 / 120) ** 2),
    ],
)
def test_clause_5_2_5_internal_gradient_effective_modulus(width, category, expected_modulus):
    out = run_members(plate(width, edges="both", stress="internal_gradient"))["values"]
    assert out["classification"] == category
    assert out["yield_limit"] == 115
    assert out["effective_modulus_mm3"] == pytest.approx(expected_modulus)
    assert out["compression_yield_limit"] is None
    assert out["compression_effective_width_mm"] is None


def section_moduli(method="area_ratio", **changes):
    data = {
        "operation": "section_moduli",
        "method": method,
        "yield_strength_mpa": 300,
        "ultimate_strength_mpa": 400,
        "gross_area_mm2": 4000,
        "gross_web_area_mm2": 2000,
        "gross_flange_areas_mm2": [1000, 1000],
        "net_flange_areas_mm2": [900, 1000],
        "gross_elastic_modulus_mm3": 100000,
        "gross_plastic_modulus_mm3": 130000,
    }
    if method == "net_section":
        data.update(
            {
                "net_elastic_modulus_mm3": 90000,
                "net_plastic_modulus_mm3": 115000,
            }
        )
    data.update(changes)
    return run_members(data)


def test_hole_modulus_gross_section_is_permitted_below_and_at_limit():
    below = section_moduli(net_flange_areas_mm2=[900, 1000])["values"]
    assert below["gross_section_moduli_permitted"] is True
    assert below["selected_method"] == "gross_section"
    assert below["elastic_modulus_mm3"] == 100000

    yield_strength, ultimate_strength = 300, 400
    limit_ratio = yield_strength / (0.85 * ultimate_strength)
    at_limit = section_moduli(net_flange_areas_mm2=[1000 * limit_ratio, 1000])["values"]
    assert at_limit["gross_section_moduli_permitted"] is True
    assert at_limit["flange_area_reductions_pct"][0] == pytest.approx(
        at_limit["permitted_flange_area_reduction_pct"]
    )


def test_hole_modulus_area_ratio_method_above_limit_matches_hand_calculation():
    values = section_moduli(net_flange_areas_mm2=[800, 1000])["values"]
    assert values["gross_section_moduli_permitted"] is False
    assert values["selected_method"] == "area_ratio"
    assert values["net_area_mm2"] == 3800
    assert values["net_to_gross_area_ratio"] == pytest.approx(0.95)
    assert values["elastic_modulus_mm3"] == pytest.approx(95000)
    assert values["plastic_modulus_mm3"] == pytest.approx(123500)


def test_hole_modulus_net_section_method_uses_supplied_net_moduli():
    values = section_moduli(
        "net_section",
        net_flange_areas_mm2=[800, 1000],
        net_elastic_modulus_mm3=91000,
        net_plastic_modulus_mm3=113000,
    )["values"]
    assert values["selected_method"] == "net_section"
    assert values["elastic_modulus_mm3"] == 91000
    assert values["plastic_modulus_mm3"] == 113000


def test_hole_modulus_rejects_inconsistent_areas_and_moduli():
    with pytest.raises(ValueError, match="same length"):
        section_moduli(net_flange_areas_mm2=[900])
    with pytest.raises(ValueError, match="must not exceed"):
        section_moduli(net_flange_areas_mm2=[1001, 1000])
    with pytest.raises(ValueError, match="Gross area must equal"):
        section_moduli(gross_area_mm2=3999)
    with pytest.raises(ValueError, match="Selected plastic modulus"):
        section_moduli(
            "net_section",
            net_flange_areas_mm2=[800, 1000],
            net_elastic_modulus_mm3=100000,
            net_plastic_modulus_mm3=90000,
        )


def test_hole_modulus_net_section_requires_net_moduli_when_selected():
    with pytest.raises(ValueError, match="net_elastic_modulus_mm3"):
        run_members(
            {
                "operation": "section_moduli",
                "method": "net_section",
                "yield_strength_mpa": 300,
                "ultimate_strength_mpa": 400,
                "gross_area_mm2": 4000,
                "gross_web_area_mm2": 2000,
                "gross_flange_areas_mm2": [1000, 1000],
                "net_flange_areas_mm2": [800, 1000],
                "gross_elastic_modulus_mm3": 100000,
                "gross_plastic_modulus_mm3": 130000,
            }
        )


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


def chs_shear(**changes):
    return {
        "operation": "chs_shear",
        "yield_strength_mpa": 250,
        "gross_area_mm2": 3000,
        "net_area_mm2": 2500,
        "oversized_fastener_holes_present": True,
        "action_kn": 202.5,
        "moment_action_knm": 0,
        "section_moment_capacity_knm": 100,
        **changes,
    }


def test_clause_5_11_4_chs_effective_area_and_shear_capacity():
    reduced = run_members(chs_shear())
    assert reduced["values"]["effective_shear_area_mm2"] == 2500
    assert reduced["values"]["effective_area_method"] == "net"
    assert reduced["values"]["nominal_shear_yield_capacity_kn"] == 225
    assert reduced["checks"]["shear_bending"]["design_capacity"] == 202.5
    assert reduced["checks"]["shear_bending"]["satisfied"]

    above_nine_tenths = run_members(chs_shear(net_area_mm2=2701))
    assert above_nine_tenths["values"]["effective_shear_area_mm2"] == 3000
    at_nine_tenths = run_members(chs_shear(net_area_mm2=2700))
    assert at_nine_tenths["values"]["effective_shear_area_mm2"] == 2700


def test_clause_5_12_3_chs_shear_reduction_uses_bending_utilisation():
    boundary = run_members(chs_shear(moment_action_knm=67.5, action_kn=202.5))
    assert boundary["values"]["nominal_shear_capacity_with_bending_kn"] == 225

    reduced = run_members(chs_shear(moment_action_knm=90, action_kn=121.5))
    assert reduced["values"]["nominal_shear_capacity_with_bending_kn"] == pytest.approx(135)
    assert reduced["checks"]["shear_bending"]["satisfied"]

    over_moment = run_members(chs_shear(moment_action_knm=90.001, action_kn=0))
    assert over_moment["values"]["nominal_shear_capacity_with_bending_kn"] == 0
    assert not over_moment["checks"]["bending"]["satisfied"]


def proportioning_shear(**changes):
    return {
        "operation": "shear_proportioning",
        "yield_strength_mpa": 250,
        "compression_flange_gross_area_mm2": 1800,
        "compression_flange_effective_area_mm2": 1500,
        "tension_flange_gross_area_mm2": 1600,
        "tension_flange_net_area_mm2": 1000,
        "tension_flange_ultimate_strength_mpa": 400,
        "flange_centroid_spacing_mm": 250,
        "nominal_web_shear_capacity_kn": 100,
        "action_kn": 90,
        "moment_action_knm": 76.5,
        **changes,
    }


def test_clause_5_12_2_flange_proportioning_and_web_shear_boundaries():
    out = run_members(proportioning_shear())
    assert out["values"]["tension_flange_area_by_fracture_limit_mm2"] == 1360
    assert out["values"]["effective_tension_flange_area_mm2"] == 1360
    assert out["values"]["effective_flange_area_mm2"] == 1360
    assert out["values"]["nominal_flange_moment_capacity_knm"] == 85
    assert out["values"]["design_flange_moment_capacity_knm"] == 76.5
    assert out["checks"]["flange_moment"]["satisfied"]
    assert out["checks"]["web_shear"]["satisfied"]

    compression_limited = run_members(
        proportioning_shear(compression_flange_effective_area_mm2=900)
    )
    assert compression_limited["values"]["effective_flange_area_mm2"] == 900
    gross_limited = run_members(
        proportioning_shear(
            tension_flange_gross_area_mm2=1000,
            tension_flange_net_area_mm2=1000,
            tension_flange_ultimate_strength_mpa=450,
        )
    )
    assert gross_limited["values"]["effective_tension_flange_area_mm2"] == 1000

    over_shear = run_members(proportioning_shear(action_kn=90.001))
    assert not over_shear["checks"]["web_shear"]["satisfied"]
    over_moment = run_members(proportioning_shear(moment_action_knm=76.501))
    assert not over_moment["checks"]["flange_moment"]["satisfied"]


def test_clause_5_12_2_rejects_inconsistent_flange_areas():
    with pytest.raises(ValueError, match="Tension flange net area must not exceed its gross area"):
        run_members(proportioning_shear(tension_flange_net_area_mm2=1601))


def flange_restraint_shear(**changes):
    return {
        "operation": "shear_with_flange_restraint",
        "yield_strength_mpa": 250,
        "web_area_mm2": 1000,
        "panel_depth_mm": 1000,
        "web_thickness_mm": 10,
        "action_kn": 50,
        "moment_action_knm": 0,
        "section_moment_capacity_knm": 100,
        "flange_thickness_mm": 10,
        "clear_web_depth_mm": 200,
        "flange_outstand_from_web_midplane_mm": 20,
        "number_of_webs": 1,
        "no_longitudinal_stiffeners_verified": True,
        **changes,
    }


def test_clause_5_11_5_2_flange_restraint_factor_and_effective_outstand():
    out = run_members(flange_restraint_shear())
    expected_factor = 1.6 - 0.6 / (1.2**0.5)
    assert out["values"]["effective_flange_outstand_mm"] == 20
    assert out["values"]["flange_restraint_factor"] == pytest.approx(expected_factor)
    conservative = run_members(shear(1000))
    assert out["values"]["shear_capacity_kn"] > conservative["values"]["shear_capacity_kn"]
    assert {"clause": "5.11.5.2"} in out["trace"]

    multi_web = run_members(
        flange_restraint_shear(
            flange_outstand_from_web_midplane_mm=100,
            number_of_webs=2,
            clear_distance_between_webs_mm=30,
        )
    )
    assert multi_web["values"]["effective_flange_outstand_mm"] == 15


def test_clause_5_11_5_2_requires_web_spacing_and_no_longitudinal_stiffeners():
    with pytest.raises(ValueError, match="Multiple webs require their clear distance"):
        run_members(flange_restraint_shear(number_of_webs=2))
    with pytest.raises(ValueError):
        run_members(flange_restraint_shear(no_longitudinal_stiffeners_verified=False))


def test_chs_shear_rejects_invalid_net_area():
    with pytest.raises(ValueError, match="Net area must not exceed gross area"):
        run_members(chs_shear(net_area_mm2=3001))


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
    assert not out["full_lateral_restraint_qualifies"]
    d["effective_length_mm"] *= 2
    assert run_members(d)["values"]["member_capacity_knm"] < out["member_capacity_knm"]


def test_member_moment_capacity_equal_to_section_capacity_qualifies_under_5_3_2_1():
    out = run_members(
        {
            "operation": "bending",
            "section_capacity_knm": 100,
            "iy_mm4": 10000000,
            "torsion_constant_mm4": 100000,
            "warping_constant_mm6": 0,
            "effective_length_mm": 1000,
            "moment_factor": 2,
            "action_knm": 10,
            "geometry": "equal_flanged_open",
        }
    )
    assert out["values"]["member_capacity_knm"] == 100
    assert out["values"]["full_lateral_restraint_qualifies"]
    assert {"clause": "5.3.2.1"} in out["trace"]


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


def test_extreme_magnitudes_fail_cleanly():
    d = compression(1e300)
    with pytest.raises(ValueError):
        run_members(d)
