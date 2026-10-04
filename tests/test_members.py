"""Independent arithmetic and published table checks for member primitives."""

import pytest

from opencalcs_as4100.connections import run_connections
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


def net_i_section_input(**changes):
    data = {
        "operation": "section_moduli",
        "method": "net_section",
        "yield_strength_mpa": 300,
        "ultimate_strength_mpa": 400,
        "gross_area_mm2": 4800,
        "gross_web_area_mm2": 2800,
        "gross_flange_areas_mm2": [1000, 1000],
        "net_flange_areas_mm2": [800, 1000],
        "gross_elastic_modulus_mm3": 402400,
        "gross_plastic_modulus_mm3": 486000,
        "net_i_section_geometry": {
            "overall_depth_mm": 300,
            "flange_thickness_mm": 10,
            "web_thickness_mm": 10,
            "bending_axis": "major",
            "symmetric_sharp_corner_i_section_verified": True,
            "flange_only_holes_verified": True,
            "net_flange_areas_deducted_under_clause_9_1_10_verified": True,
        },
    }
    data.update(changes)
    return data


def net_rhs_section_input(**changes):
    data = {
        "operation": "section_moduli",
        "method": "net_section",
        "yield_strength_mpa": 300,
        "ultimate_strength_mpa": 400,
        "gross_area_mm2": 8600,
        "gross_web_area_mm2": 5600,
        "gross_flange_areas_mm2": [1500, 1500],
        "net_flange_areas_mm2": [1200, 1500],
        "gross_elastic_modulus_mm3": 664577.7777777778,
        "gross_plastic_modulus_mm3": 827000,
        "net_rhs_geometry": {
            "overall_depth_mm": 300,
            "flange_thickness_mm": 10,
            "web_thickness_mm": 10,
            "bending_axis": "major",
            "symmetric_sharp_corner_rhs_section_verified": True,
            "flange_only_holes_verified": True,
            "net_flange_areas_deducted_under_clause_9_1_10_verified": True,
        },
    }
    data.update(changes)
    return data


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


def test_hole_modulus_net_section_derives_sharp_corner_i_section_properties():
    values = run_members(net_i_section_input())["values"]

    assert values["selected_method"] == "net_section"
    assert values["net_area_mm2"] == 4600
    assert values["elastic_modulus_mm3"] == pytest.approx(358086.6944830784)
    assert values["plastic_modulus_mm3"] == pytest.approx(456000)
    assert values["net_section_properties"]["centroid_from_top_mm"] == pytest.approx(
        156.30434782608697
    )
    assert values["net_section_properties"]["plastic_neutral_axis_from_top_mm"] == pytest.approx(
        160
    )
    assert values["net_section_properties"]["second_moment_of_area_mm4"] == pytest.approx(
        55970507.24637682
    )
    assert values["net_section_properties"]["elastic_modulus_top_mm3"] == pytest.approx(
        358086.6944830784
    )
    assert values["net_section_properties"]["elastic_modulus_bottom_mm3"] == pytest.approx(
        389507.3121533032
    )
    assert values["net_section_properties"]["governing_fibre"] == "top"
    assert values["net_section_properties"]["governing_elastic_modulus_mm3"] == pytest.approx(
        358086.6944830784
    )


def test_hole_modulus_net_i_section_uses_clause_9_1_10_and_governing_fibre():
    deduction = run_connections(
        {
            "check_type": "hole_deduction",
            "gross_area_mm2": 1000,
            "thickness_mm": 10,
            "straight_hole_width_sum_mm": 20,
            "zigzag_hole_width_sum_mm": 0,
            "stagger_pairs": [],
        }
    )
    net_flange_areas = [deduction["intermediate"]["net_area_mm2"], 1000]
    geometry = net_i_section_input(
        net_flange_areas_mm2=net_flange_areas,
    )
    values = run_members(geometry)["values"]

    assert deduction["intermediate"]["deduction_mm2"] == 200
    assert values["net_area_mm2"] == 4600
    assert values["net_section_properties"]["governing_fibre"] == "top"
    assert values["elastic_modulus_mm3"] == pytest.approx(358086.6944830784)


def test_hole_modulus_net_i_section_rejects_inconsistent_geometry():
    data = net_i_section_input(gross_area_mm2=3800, gross_web_area_mm2=1800)
    with pytest.raises(ValueError, match="Gross web area is inconsistent"):
        run_members(data)


def test_hole_modulus_net_i_section_rejects_web_wider_than_gross_flange():
    data = net_i_section_input(gross_area_mm2=32800, gross_web_area_mm2=30800)
    data["net_i_section_geometry"]["web_thickness_mm"] = 110
    with pytest.raises(ValueError, match="Web thickness must not exceed"):
        run_members(data)


def test_hole_modulus_net_i_section_locates_plastic_axis_inside_flange():
    data = net_i_section_input(
        gross_area_mm2=2560,
        gross_web_area_mm2=560,
        net_flange_areas_mm2=[1000, 100],
        gross_elastic_modulus_mm3=304835.55555555556,
        gross_plastic_modulus_mm3=329200,
    )
    data["net_i_section_geometry"].update(
        web_thickness_mm=2,
    )
    values = run_members(data)["values"]

    assert values["net_area_mm2"] == 1660
    assert values["net_section_properties"]["plastic_neutral_axis_from_top_mm"] == pytest.approx(
        8.3
    )
    assert values["net_section_properties"]["plastic_modulus_mm3"] == pytest.approx(111611)
    assert values["elastic_modulus_mm3"] == pytest.approx(72332.02459376372)


def test_hole_modulus_net_i_section_is_limited_to_major_axis_bending():
    data = net_i_section_input()
    data["net_i_section_geometry"]["bending_axis"] = "minor"
    with pytest.raises(ValueError):
        run_members(data)


def test_hole_modulus_net_rhs_section_derives_major_axis_properties():
    deduction = run_connections(
        {
            "check_type": "hole_deduction",
            "gross_area_mm2": 1500,
            "thickness_mm": 10,
            "straight_hole_width_sum_mm": 30,
            "zigzag_hole_width_sum_mm": 0,
            "stagger_pairs": [],
        }
    )
    values = run_members(
        net_rhs_section_input(
            net_flange_areas_mm2=[deduction["intermediate"]["net_area_mm2"], 1500]
        )
    )["values"]

    assert deduction["intermediate"]["deduction_mm2"] == 300
    assert values["selected_method"] == "net_section"
    assert values["net_area_mm2"] == 8300
    assert values["net_section_properties"]["centroid_from_top_mm"] == pytest.approx(
        155.2409638554217
    )
    assert values["net_section_properties"]["second_moment_of_area_mm4"] == pytest.approx(
        93148684.73895583
    )
    assert values["net_section_properties"]["plastic_neutral_axis_from_top_mm"] == pytest.approx(
        157.5
    )
    assert values["net_section_properties"]["elastic_modulus_top_mm3"] == pytest.approx(
        600026.4519467081
    )
    assert values["net_section_properties"]["elastic_modulus_bottom_mm3"] == pytest.approx(
        643474.0602025246
    )
    assert values["net_section_properties"]["governing_fibre"] == "top"
    assert values["elastic_modulus_mm3"] == pytest.approx(600026.4519467081)
    assert values["plastic_modulus_mm3"] == pytest.approx(782375)


def test_hole_modulus_net_rhs_section_checks_both_web_walls_fit_flange():
    data = net_rhs_section_input()
    data["net_rhs_geometry"]["web_thickness_mm"] = 80
    with pytest.raises(ValueError, match="Web thickness must not exceed"):
        run_members(data)


def test_hole_modulus_net_section_rejects_two_derived_geometry_forms():
    data = net_rhs_section_input()
    data["net_i_section_geometry"] = net_i_section_input()["net_i_section_geometry"]
    with pytest.raises(ValueError, match="one derived net-section geometry"):
        run_members(data)


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


def rational_flange_restraint_shear(**changes):
    return {
        "operation": "shear_with_rational_flange_restraint",
        "yield_strength_mpa": 250,
        "web_area_mm2": 1000,
        "panel_depth_mm": 1000,
        "web_thickness_mm": 10,
        "stiffener_spacing_mm": 3000,
        "tension_field": False,
        "action_kn": 110,
        "moment_action_knm": 0,
        "section_moment_capacity_knm": 100,
        "alpha_f": 1.15,
        "rational_analysis_verified": True,
        "rational_analysis_reference": "CALC-SHEAR-017",
        "no_longitudinal_stiffeners_verified": True,
        **changes,
    }


def test_clause_5_11_5_2_c_rational_flange_restraint_input_route():
    result = run_members(rational_flange_restraint_shear())
    values = result["values"]
    assert values["flange_restraint_factor"] == 1.15
    assert values["flange_restraint_method"] == "rational_buckling_analysis"
    assert values["rational_analysis_reference"] == "CALC-SHEAR-017"
    assert values["stiffener_spacing_to_panel_depth_ratio"] == 3
    assert values["buckling_reduction"] == pytest.approx(0.7284333333333334)
    assert values["tension_field_factor"] == 1
    assert result["checks"]["shear_bending"]["design_capacity"] == pytest.approx(113.089275)
    assert result["checks"]["shear_bending"]["satisfied"]
    assert {"clause": "5.11.5.2"} in result["trace"]
    assert any("not authenticated" in item for item in result["manual_requirements"])


def test_clause_5_11_5_2_c_rational_flange_restraint_scope_is_enforced():
    for changes in (
        {"rational_analysis_verified": False},
        {"rational_analysis_reference": "   "},
        {"no_longitudinal_stiffeners_verified": False},
        {"tension_field": True},
        {"stiffener_spacing_mm": 3000.1},
        {"alpha_f": 0},
    ):
        with pytest.raises(ValueError):
            run_members(rational_flange_restraint_shear(**changes))

    missing_evidence = rational_flange_restraint_shear()
    del missing_evidence["rational_analysis_reference"]
    with pytest.raises(ValueError):
        run_members(missing_evidence)

    missing_evidence = rational_flange_restraint_shear()
    del missing_evidence["rational_analysis_verified"]
    with pytest.raises(ValueError):
        run_members(missing_evidence)


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
    assert "compact_section_reduced_y_knm" not in out["values"]


def test_clause_8_3_3a_and_8_3_4_compact_i_section_hand_arithmetic():
    d = interaction()
    d.update(
        axial_action_kn=450,
        moment_x_knm=10,
        moment_y_knm=20,
        compact_doubly_symmetric_i_verified=True,
    )
    out = run_members(d)
    values = out["values"]

    # N*/(phi Ns)=0.5; Clause 8.3.3(a) gives 1.19*50*(1-0.5^2)=44.625.
    assert values["compact_section_reduced_x_knm"] == 50
    assert values["compact_section_reduced_y_knm"] == pytest.approx(44.625)
    assert values["compact_section_design_capacity_x_knm"] == 45
    assert values["compact_section_design_capacity_y_knm"] == pytest.approx(40.1625)
    assert values["compact_section_biaxial_gamma"] == pytest.approx(1.9)
    assert values["compact_section_x_reduction_method"] == "8.3.2 general"
    # Clause 8.3.4: (10/45)^1.9 + (20/40.1625)^1.9.
    assert out["checks"]["compact_section_biaxial"]["utilisation"] == pytest.approx(
        0.32328522582491365
    )
    assert out["checks"]["compact_section_biaxial"]["satisfied"]
    assert out["checks"]["compact_minor_axis_component"]["satisfied"]
    assert {"clause": "8.3.3(a)"} in out["trace"]


def test_clause_8_3_2a_compact_major_axis_route_for_tension_and_kf_one_compression():
    d = interaction()
    d.update(
        axial_action_kn=450,
        moment_x_knm=10,
        moment_y_knm=20,
        compact_doubly_symmetric_i_verified=True,
        compression_form_factor_one_verified=True,
    )
    compression_out = run_members(d)
    assert compression_out["values"]["compact_section_reduced_x_knm"] == 59
    assert compression_out["values"]["compact_section_x_reduction_method"] == "8.3.2(a)"
    assert {"clause": "8.3.2(a)"} in compression_out["trace"]
    assert compression_out["checks"]["compact_section_biaxial"]["utilisation"] == pytest.approx(
        0.30779756197106134
    )

    d = interaction("tension")
    d.update(
        axial_action_kn=450,
        compact_doubly_symmetric_i_verified=True,
    )
    tension_out = run_members(d)
    assert tension_out["values"]["compact_section_reduced_x_knm"] == 59
    assert tension_out["values"]["compact_section_x_reduction_method"] == "8.3.2(a)"


def test_clause_8_3_2a_kf_confirmation_cannot_be_used_outside_its_scope():
    d = interaction()
    d["compression_form_factor_one_verified"] = True
    with pytest.raises(ValueError, match="requires a verified compact"):
        run_members(d)

    d["compact_doubly_symmetric_i_verified"] = True
    d["axial_mode"] = "tension"
    with pytest.raises(ValueError, match="applies only to compression"):
        run_members(d)


def test_clause_8_3_2b_compact_major_axis_route_uses_web_slenderness_hand_arithmetic():
    d = interaction()
    d.update(
        axial_action_kn=450,
        moment_x_knm=10,
        moment_y_knm=20,
        compact_doubly_symmetric_i_verified=True,
        compression_form_factor_below_one_verified=True,
        compression_form_factor=0.8,
        web_clear_width_mm=65,
        web_thickness_mm=1,
        web_yield_strength_mpa=250,
        web_residual_stress_category="HR",
    )

    out = run_members(d)
    values = out["values"]
    assert values["compact_section_compression_form_factor"] == 0.8
    assert values["compact_section_web_lambda_w"] == 65
    assert values["compact_section_web_lambda_wy"] == 45
    assert values["compact_section_x_reduction_factor"] == pytest.approx(
        1 + 0.18 * (82 - 65) / (82 - 45)
    )
    assert values["compact_section_reduced_x_knm"] == pytest.approx(54.13513513513514)
    assert values["compact_section_x_reduction_method"] == "8.3.2(b)"
    assert out["checks"]["compact_section_biaxial"]["utilisation"] == pytest.approx(
        0.3152420180103579
    )
    assert {"clause": "8.3.2(b)"} in out["trace"]


@pytest.mark.parametrize(
    "residual_stress,expected_limit",
    [("SR", 45), ("HR", 45), ("LW", 40), ("CF", 40), ("HW", 35)],
)
def test_clause_8_3_2b_uses_table_6_2_4_internal_web_yield_limit(residual_stress, expected_limit):
    d = interaction()
    d.update(
        compact_rhs_shs_verified=True,
        compression_form_factor_below_one_verified=True,
        compression_form_factor=0.8,
        web_clear_width_mm=20,
        web_thickness_mm=1,
        web_yield_strength_mpa=250,
        web_residual_stress_category=residual_stress,
    )
    out = run_members(d)
    assert out["values"]["compact_section_web_lambda_wy"] == expected_limit


def test_clause_8_3_2b_rejects_inconsistent_scope_and_web_compactness():
    d = interaction()
    d.update(
        compact_doubly_symmetric_i_verified=True,
        compression_form_factor_below_one_verified=True,
        compression_form_factor=1.0,
        web_clear_width_mm=20,
        web_thickness_mm=1,
        web_yield_strength_mpa=250,
        web_residual_stress_category="HR",
    )
    with pytest.raises(ValueError, match="kf<1.0"):
        run_members(d)

    d["compression_form_factor"] = 0.8
    d["web_clear_width_mm"] = 83
    with pytest.raises(ValueError, match="Clause 5.2.3 compactness limit"):
        run_members(d)

    d["web_clear_width_mm"] = 20
    d["axial_mode"] = "tension"
    with pytest.raises(ValueError, match="applies only to compression"):
        run_members(d)


def test_clause_8_3_2b_web_compactness_boundary_and_section_capacity_cap():
    d = interaction()
    d.update(
        axial_action_kn=450,
        compact_doubly_symmetric_i_verified=True,
        compression_form_factor_below_one_verified=True,
        compression_form_factor=0.8,
        web_clear_width_mm=82,
        web_thickness_mm=1,
        web_yield_strength_mpa=250,
        web_residual_stress_category="HW",
    )
    boundary = run_members(d)["values"]
    assert boundary["compact_section_web_lambda_w"] == 82
    assert boundary["compact_section_web_lambda_wy"] == 35
    assert boundary["compact_section_x_reduction_factor"] == pytest.approx(1)
    assert boundary["compact_section_reduced_x_knm"] == pytest.approx(50)

    d.update(axial_action_kn=0, web_clear_width_mm=20)
    capped = run_members(d)["values"]
    assert capped["compact_section_x_reduction_factor"] > 1
    assert capped["compact_section_reduced_x_knm"] == 100


def test_clause_8_3_3b_rhs_shs_minor_axis_and_compact_biaxial_interaction():
    d = interaction()
    d.update(
        axial_action_kn=450,
        moment_x_knm=10,
        moment_y_knm=20,
        compact_rhs_shs_verified=True,
    )
    out = run_members(d)
    assert out["values"]["compact_section_reduced_y_knm"] == pytest.approx(29.5)
    assert out["values"]["compact_section_design_capacity_y_knm"] == pytest.approx(26.55)
    assert out["values"]["compact_section_y_reduction_method"] == "8.3.3(b)"
    assert out["checks"]["compact_section_biaxial"]["utilisation"] == pytest.approx(
        0.6411580100977792
    )
    assert {"clause": "8.3.3(b)"} in out["trace"]


def test_compact_interaction_rejects_two_competing_section_type_confirmations():
    d = interaction()
    d["compact_doubly_symmetric_i_verified"] = True
    d["compact_rhs_shs_verified"] = True
    with pytest.raises(ValueError, match="Select one verified compact section type"):
        run_members(d)


def test_clause_8_3_3a_caps_at_msy_and_fails_after_axial_overload():
    d = interaction()
    d.update(compact_doubly_symmetric_i_verified=True, axial_action_kn=0)
    assert run_members(d)["values"]["compact_section_reduced_y_knm"] == 50

    d.update(axial_action_kn=1000, moment_x_knm=0, moment_y_knm=0)
    zero_moment = run_members(d)
    assert not zero_moment["checks"]["compact_minor_axis_component"]["satisfied"]
    assert not zero_moment["checks"]["compact_section_biaxial"]["satisfied"]

    d.update(axial_action_kn=1000, moment_x_knm=0, moment_y_knm=1)
    out = run_members(d)
    assert out["values"]["compact_section_reduced_y_knm"] == 0
    assert out["checks"]["compact_minor_axis_component"]["satisfied"] is False
    assert out["checks"]["compact_section_biaxial"]["utilisation"] is None
    assert out["checks"]["compact_section_biaxial"]["satisfied"] is False


def test_compact_interaction_route_requires_explicit_positive_scope_confirmation():
    d = interaction()
    d["compact_doubly_symmetric_i_verified"] = False
    with pytest.raises(ValueError):
        run_members(d)


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
        "maximum_member_design_force_kn": 100,
        "top_flange_connection_design_capacity_kn": 50,
        "bottom_flange_connection_design_capacity_kn": 50,
    }
    out = run_members(d)
    assert out["values"]["tension_distribution_factor"] == 0.85
    assert out["checks"]["both_flange_force_transfer"] == {
        "clause": "7.3.2(b)(ii)",
        "maximum_member_design_force_kn": 100,
        "minimum_design_capacity_each_flange_kn": 50,
        "top_flange_connection_design_capacity_kn": 50,
        "bottom_flange_connection_design_capacity_kn": 50,
        "satisfied": True,
    }
    d["top_flange_connection_design_capacity_kn"] = 49.999
    out = run_members(d)
    assert out["values"]["tension_distribution_factor"] is None
    assert not out["checks"]["both_flange_force_transfer"]["satisfied"]
    d["top_flange_connection_design_capacity_kn"] = 50
    d["connection_length_mm"] = 199
    with pytest.raises(ValueError, match="length"):
        run_members(d)


@pytest.mark.parametrize(
    "case,short_leg,factor",
    [
        ("a", True, 0.75),
        ("a", False, 0.85),
        ("b", True, 0.75),
        ("b", False, 0.85),
        ("c", None, 0.85),
        ("d", None, 0.90),
        ("e", None, 1.0),
        ("f", None, 1.0),
        ("g", None, 1.0),
    ],
)
def test_table_7_3_2_case_factor_lookup(case, short_leg, factor):
    d = {
        "operation": "tension_distribution",
        "configuration": f"table_7_3_2_{case}",
        "connection_conditions_verified": True,
    }
    if short_leg is not None:
        d["unequal_angle_connected_by_short_leg"] = short_leg
    out = run_members(d)
    assert out["values"]["tension_distribution_factor"] == factor
    assert out["checks"]["table_7_3_2_correction_factor"] == {
        "clause": "Table 7.3.2",
        "case": f"({case})",
        "tension_distribution_factor": factor,
        "satisfied": True,
    }


def test_table_7_3_2_short_leg_condition_is_limited_to_cases_a_and_b():
    d = {
        "operation": "tension_distribution",
        "configuration": "table_7_3_2_a",
        "connection_conditions_verified": True,
    }
    with pytest.raises(ValueError, match="short-leg condition"):
        run_members(d)
    d["configuration"] = "table_7_3_2_c"
    d["unequal_angle_connected_by_short_leg"] = True
    with pytest.raises(ValueError, match="applies only"):
        run_members(d)


def test_uniform_tension_distribution_checks_every_member_part_capacity():
    d = {
        "operation": "tension_distribution",
        "configuration": "uniform",
        "connection_conditions_verified": True,
        "member_part_count": 2,
        "member_part_connections": [
            {
                "member_part_id": "web",
                "maximum_part_design_force_kn": 40,
                "part_connection_design_capacity_kn": 40,
            },
            {
                "member_part_id": "flanges",
                "maximum_part_design_force_kn": 60,
                "part_connection_design_capacity_kn": 65,
            },
        ],
    }
    out = run_members(d)
    assert out["values"]["tension_distribution_factor"] == 1
    part_capacity = out["checks"]["uniform_connection_part_capacity"]
    assert part_capacity["clause"] == "7.3.1(b)"
    assert part_capacity["satisfied"]
    assert [part["satisfied"] for part in part_capacity["parts"]] == [True, True]

    d["member_part_connections"][1]["part_connection_design_capacity_kn"] = 59.999
    out = run_members(d)
    assert out["values"]["tension_distribution_factor"] is None
    assert not out["checks"]["uniform_connection_part_capacity"]["satisfied"]


def test_uniform_tension_distribution_rejects_incomplete_or_duplicate_parts():
    d = {
        "operation": "tension_distribution",
        "configuration": "uniform",
        "connection_conditions_verified": True,
        "member_part_count": 2,
        "member_part_connections": [
            {
                "member_part_id": "web",
                "maximum_part_design_force_kn": 40,
                "part_connection_design_capacity_kn": 40,
            },
            {
                "member_part_id": "flange",
                "maximum_part_design_force_kn": 60,
                "part_connection_design_capacity_kn": 60,
            },
        ],
    }
    d["member_part_count"] = 3
    with pytest.raises(ValueError, match="every connected member part"):
        run_members(d)
    d["member_part_count"] = 2
    d["member_part_connections"][1]["member_part_id"] = "web"
    with pytest.raises(ValueError, match="identifiers must be unique"):
        run_members(d)


def test_both_flange_force_transfer_capacity_is_required_for_each_flange():
    d = {
        "operation": "tension_distribution",
        "configuration": "both_flanges",
        "connection_conditions_verified": True,
        "connection_length_mm": 250,
        "member_depth_mm": 200,
        "maximum_member_design_force_kn": 100,
        "top_flange_connection_design_capacity_kn": 75,
        "bottom_flange_connection_design_capacity_kn": 49,
    }
    out = run_members(d)
    assert out["checks"]["both_flange_force_transfer"]["satisfied"] is False
    assert out["values"]["tension_distribution_factor"] is None
    del d["bottom_flange_connection_design_capacity_kn"]
    with pytest.raises(ValueError, match="capacity for each flange"):
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
