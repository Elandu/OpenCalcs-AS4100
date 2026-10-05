import pytest

from opencalcs_as4100.advanced_members import run_advanced_members


def closed_torsion_constant_inputs(**changes):
    return {
        "operation": "closed_section_torsion_constant",
        "enclosed_median_line_area_mm2": 10_000,
        "wall_segments": [
            {"median_line_length_mm": 100, "thickness_mm": 5},
            {"median_line_length_mm": 100, "thickness_mm": 5},
            {"median_line_length_mm": 100, "thickness_mm": 5},
            {"median_line_length_mm": 100, "thickness_mm": 5},
        ],
        "single_cell_thin_walled_closed_section_verified": True,
        "median_line_geometry_verified": True,
        **changes,
    }


def open_torsion_constant_inputs(**changes):
    return {
        "operation": "open_section_torsion_constant",
        "wall_segments": [
            {"median_line_length_mm": 1200, "thickness_mm": 3},
            {"median_line_length_mm": 600, "thickness_mm": 6},
        ],
        "all_wall_segments_and_thin_walled_open_geometry_verified": True,
        **changes,
    }


def test_appendix_h4_open_section_torsion_constant_hand_arithmetic():
    out = run_advanced_members(open_torsion_constant_inputs())
    values = out["values"]
    assert values["wall_segment_contributions_mm4"] == [10_800, 43_200]
    assert values["torsion_constant_j_approx_mm4"] == 54_000
    assert out["clauses"] == ["Appendix H.4 (informative)"]
    assert out["full_standard_compliance"] is False


@pytest.mark.parametrize(
    "changes",
    [
        {"wall_segments": []},
        {"wall_segments": [{"median_line_length_mm": 0, "thickness_mm": 3}]},
        {"all_wall_segments_and_thin_walled_open_geometry_verified": False},
    ],
)
def test_appendix_h4_open_section_rejects_invalid_or_unverified_geometry(changes):
    with pytest.raises(ValueError):
        run_advanced_members(open_torsion_constant_inputs(**changes))


def test_amendment_1_appendix_h4_closed_section_torsion_constant_hand_arithmetic():
    out = run_advanced_members(closed_torsion_constant_inputs())
    values = out["values"]
    assert values["wall_length_to_thickness_sum"] == 80
    assert values["torsion_constant_j_mm4"] == 5_000_000
    assert out["clauses"] == ["Appendix H.4 (Amd 1:2021)"]
    assert out["full_standard_compliance"] is False

    nonuniform = closed_torsion_constant_inputs(
        enclosed_median_line_area_mm2=8000,
        wall_segments=[
            {"median_line_length_mm": 100, "thickness_mm": 5},
            {"median_line_length_mm": 80, "thickness_mm": 4},
            {"median_line_length_mm": 100, "thickness_mm": 5},
            {"median_line_length_mm": 80, "thickness_mm": 4},
        ],
    )
    assert run_advanced_members(nonuniform)["values"]["torsion_constant_j_mm4"] == 3_200_000


@pytest.mark.parametrize(
    "changes",
    [
        {"wall_segments": [{"median_line_length_mm": 100, "thickness_mm": 5}] * 2},
        {"single_cell_thin_walled_closed_section_verified": False},
        {"median_line_geometry_verified": False},
    ],
)
def test_amendment_1_appendix_h4_rejects_unsupported_or_unverified_geometry(changes):
    with pytest.raises(ValueError):
        run_advanced_members(closed_torsion_constant_inputs(**changes))


def test_varying_compression_independent_table_reference():
    out = run_advanced_members(
        {
            "operation": "varying_compression",
            "minimum_section_capacity_kn": 1000,
            "elastic_buckling_load_kn": 1000,
            "section_constant": 0,
            "action_kn": 500,
            "flexural_mode_verified": True,
        }
    )
    assert out["values"]["modified_slenderness"] == 90
    assert out["values"]["reduction"] == pytest.approx(0.610, abs=0.0006)
    assert out["checks"][0]["satisfied"]


def torsional_flexural_compression_inputs(**changes):
    return {
        "operation": "torsional_flexural_compression",
        "member_section_form": "fabricated_monosymmetric",
        "bracing_axis": "minor_principal",
        "section_and_axis_applicability_verified": True,
        "as_nzs_4600_nominal_member_capacity_kn": 400,
        "as_nzs_4600_calculation_verified": True,
        "as_nzs_4600_calculation_reference": "TF-ANALYSIS-001",
        "action_kn": 306,
        **changes,
    }


def test_clause_6_3_3_as4100_factors_and_capacity_check():
    out = run_advanced_members(torsional_flexural_compression_inputs())
    assert out["clauses"] == ["6.3.3"]
    assert out["values"]["as_nzs_4600_nominal_member_capacity_kn"] == 400
    assert out["values"]["as_4100_torsional_flexural_reduction_factor"] == 0.85
    assert out["values"]["nominal_member_capacity_kn"] == 340
    assert out["checks"][0]["nominal_capacity"] == 340
    assert out["checks"][0]["capacity_factor"] == 0.90
    assert out["checks"][0]["design_capacity"] == 306
    assert out["checks"][0]["satisfied"]
    assert out["full_standard_compliance"] is False

    over_capacity = run_advanced_members(torsional_flexural_compression_inputs(action_kn=306.001))
    assert not over_capacity["checks"][0]["satisfied"]


@pytest.mark.parametrize(
    "changes",
    [
        {"member_section_form": "unlipped_angle"},
        {"member_section_form": "tee"},
        {"member_section_form": "cruciform"},
        {
            "member_section_form": "hot_rolled_channel",
            "bracing_axis": "minor_principal",
        },
    ],
)
def test_clause_6_3_3_as4100_route_rejects_excluded_member_forms(changes):
    with pytest.raises(ValueError, match="excludes"):
        run_advanced_members(torsional_flexural_compression_inputs(**changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"section_and_axis_applicability_verified": False},
        {"as_nzs_4600_calculation_verified": False},
        {"as_nzs_4600_calculation_reference": "  "},
        {"as_nzs_4600_nominal_member_capacity_kn": 0},
    ],
)
def test_clause_6_3_3_as4100_route_requires_verified_external_capacity(changes):
    with pytest.raises(ValueError):
        run_advanced_members(torsional_flexural_compression_inputs(**changes))


def test_clause_6_3_3_hot_rolled_channel_major_axis_remains_in_scope():
    out = run_advanced_members(
        torsional_flexural_compression_inputs(
            member_section_form="hot_rolled_channel",
            bracing_axis="major_principal",
        )
    )
    assert out["checks"][0]["design_capacity"] == 306


@pytest.mark.parametrize(
    "ends,factor,expected,clauses",
    [
        ("both_restrained", 1, 60, ["5.6.4"]),
        ("both_restrained", 2, 77.4901573278, ["5.6.4"]),
        ("one_unrestrained", 1, 60, ["5.6.2(ii)", "5.6.4"]),
    ],
)
def test_external_lateral_buckling(ends, factor, expected, clauses):
    # Ms=Mob=100: 0.6*(sqrt(4)-1)*100=60 for factor1.
    # factor2: Moa=50 => 120*(sqrt(7)-2)=77.4901573278.
    out = run_advanced_members(
        {
            "operation": "buckling_analysis_bending",
            "section_capacity_knm": 100,
            "elastic_buckling_moment_knm": 100,
            "moment_factor": factor,
            "end_configuration": ends,
            "restraint_and_load_model_verified": True,
            "action_knm": 10,
        }
    )
    assert out["values"]["member_capacity_knm"] == pytest.approx(expected)
    assert out["clauses"] == clauses


def varying_section_buckling_analysis_inputs(**changes):
    return {
        "operation": "buckling_analysis_bending",
        "analysis_scope": "varying_section",
        "section_capacity_knm": 120,
        "elastic_buckling_moment_knm": 100,
        "moment_factor": 1.3,
        "end_configuration": "both_restrained",
        "restraint_and_load_model_verified": True,
        "critical_section_capacity_verified": True,
        "varying_section_buckling_model_verified": True,
        "buckling_analysis_reference": "BUCKLING-ANALYSIS-VAR-01",
        "action_knm": 60,
        **changes,
    }


def test_clause_5_6_1_1_b_iii_uses_critical_capacity_and_variable_section_analysis():
    out = run_advanced_members(varying_section_buckling_analysis_inputs())
    values = out["values"]
    moa = 100 / 1.3
    ratio = 120 / moa
    reduction = 1.8 / ((ratio**2 + 3) ** 0.5 + ratio)
    assert values["analysis_scope"] == "varying_section"
    assert values["reference_analysis_moment_knm"] == pytest.approx(moa)
    assert values["reduction"] == pytest.approx(reduction)
    assert values["member_capacity_knm"] == pytest.approx(1.3 * reduction * 120)
    assert out["clauses"] == ["5.6.1.1(b)(iii)", "5.6.4"]
    assert [check["satisfied"] for check in out["checks"]] == [True, True, True]
    assert values["buckling_analysis_reference"] == "BUCKLING-ANALYSIS-VAR-01"
    assert out["full_standard_compliance"] is False


@pytest.mark.parametrize(
    "changes",
    [
        {"critical_section_capacity_verified": False},
        {"varying_section_buckling_model_verified": False},
        {"buckling_analysis_reference": " "},
        {"end_configuration": "one_unrestrained"},
    ],
)
def test_clause_5_6_1_1_b_iii_requires_verified_variable_section_analysis(changes):
    with pytest.raises(ValueError):
        run_advanced_members(varying_section_buckling_analysis_inputs(**changes))


def unequal_flange_buckling_analysis_inputs(**changes):
    return {
        "operation": "buckling_analysis_bending",
        "analysis_scope": "unequal_flange_i",
        "section_capacity_knm": 100,
        "elastic_buckling_moment_knm": 125,
        "moment_factor": 1.25,
        "end_configuration": "both_restrained",
        "restraint_and_load_model_verified": True,
        "unequal_flange_i_applicability_verified": True,
        "constant_cross_section_verified": True,
        "unequal_flange_buckling_model_verified": True,
        "buckling_analysis_reference": "BUCKLING-ANALYSIS-UI-01",
        "action_knm": 60,
        **changes,
    }


def test_clause_5_6_1_2_b_unequal_flange_i_section_buckling_analysis():
    out = run_advanced_members(unequal_flange_buckling_analysis_inputs())
    assert out["values"]["reference_analysis_moment_knm"] == 100
    assert out["values"]["reduction"] == pytest.approx(0.6)
    assert out["values"]["member_capacity_knm"] == pytest.approx(75)
    assert out["clauses"] == ["5.6.1.2(b)", "5.6.1.1(a)", "5.6.4"]
    assert [check["satisfied"] for check in out["checks"]] == [True, True, True, True]
    assert out["values"]["buckling_analysis_reference"] == "BUCKLING-ANALYSIS-UI-01"
    assert out["full_standard_compliance"] is False


@pytest.mark.parametrize(
    "changes",
    [
        {"unequal_flange_i_applicability_verified": False},
        {"constant_cross_section_verified": False},
        {"unequal_flange_buckling_model_verified": False},
        {"buckling_analysis_reference": " "},
        {"end_configuration": "one_unrestrained"},
    ],
)
def test_clause_5_6_1_2_b_requires_verified_unequal_flange_analysis(changes):
    with pytest.raises(ValueError):
        run_advanced_members(unequal_flange_buckling_analysis_inputs(**changes))


@pytest.mark.parametrize(
    "distribution,factor,expected_capacity",
    [
        ("uniform_end_moment", 0.25, 15),
        ("tip_force", 1.25, 75),
        ("uniform_load", 2.25, 100),  # alpha_m*alpha_s*Ms is capped at Ms
    ],
)
def test_table_5_6_2_moment_factors(distribution, factor, expected_capacity):
    out = run_advanced_members(
        {
            "operation": "one_unrestrained_table_bending",
            "section_capacity_knm": 100,
            "reference_buckling_moment_knm": 100,
            "moment_distribution": distribution,
            "action_knm": 0,
            "one_end_restraint_and_continuity_verified": True,
            "reference_buckling_moment_verified": True,
        }
    )
    assert out["values"]["moment_factor"] == factor
    assert out["values"]["reduction"] == pytest.approx(0.6)
    assert out["values"]["member_capacity_knm"] == pytest.approx(expected_capacity)
    assert out["clauses"] == [
        "5.6.1.1(1)",
        "5.6.1.1(2)",
        "5.6.1.1(3)",
        "5.6.2",
        "Table 5.6.2",
    ]
    assert out["full_standard_compliance"] is False


def test_table_5_6_2_capacity_limit_boundary_and_case_validation():
    inputs = {
        "operation": "one_unrestrained_table_bending",
        "section_capacity_knm": 100,
        "reference_buckling_moment_knm": 100,
        "moment_distribution": "uniform_end_moment",
        "action_knm": 13.5,
        "one_end_restraint_and_continuity_verified": True,
        "reference_buckling_moment_verified": True,
    }
    assert run_advanced_members(inputs)["checked_conditions_satisfied"]
    inputs["action_knm"] = 13.500001
    assert not run_advanced_members(inputs)["checked_conditions_satisfied"]
    inputs["moment_distribution"] = "cantilever_point_load"
    with pytest.raises(ValueError, match="moment_distribution"):
        run_advanced_members(inputs)


def moment_factor_inputs(**updates):
    return {
        "operation": "moment_modification_factor",
        "maximum_design_moment_knm": 100,
        "quarter_point_moment_2_knm": 80,
        "midpoint_moment_3_knm": 100,
        "quarter_point_moment_4_knm": 80,
        "moment_diagram_verified": True,
        "both_ends_restrained_verified": True,
        **updates,
    }


def test_clause_5_6_1_1_a_iii_moment_modification_factor():
    out = run_advanced_members(moment_factor_inputs())
    assert out["values"]["moment_factor"] == pytest.approx(1.1258525035052873)
    assert out["values"]["uncapped_moment_factor"] == pytest.approx(1.1258525035052873)
    assert out["values"]["upper_cap_applied"] is False
    assert out["clauses"] == ["5.6.1.1(a)(iii)"]


def test_clause_5_6_1_1_a_iii_caps_moment_modification_factor_at_2_5():
    out = run_advanced_members(
        moment_factor_inputs(
            maximum_design_moment_knm=200,
            quarter_point_moment_2_knm=10,
            midpoint_moment_3_knm=10,
            quarter_point_moment_4_knm=10,
        )
    )
    assert out["values"]["uncapped_moment_factor"] > 2.5
    assert out["values"]["moment_factor"] == 2.5
    assert out["values"]["upper_cap_applied"]


def test_clause_5_6_1_1_a_iii_requires_both_ends_restrained():
    with pytest.raises(ValueError):
        run_advanced_members(moment_factor_inputs(both_ends_restrained_verified=False))


def table_5_6_1_inputs(load_case, **updates):
    return {
        "operation": "table_5_6_1_moment_factor",
        "load_case": load_case,
        "both_ends_restrained_verified": True,
        "table_5_6_1_diagram_verified": True,
        **updates,
    }


@pytest.mark.parametrize(
    "load_case,case_inputs,expected",
    [
        ("end_moments", {"beta_m": 0.5}, 2.35),
        ("two_symmetric_point_loads", {"twice_a_over_length": 0.4}, 1.126),
        ("single_point_load", {"twice_a_over_length": 0.4}, 1.414),
        ("midspan_point_load_with_one_end_moment", {"beta_m": 0.9}, 1.5),
        ("midspan_point_load_with_equal_end_moments", {"beta_m": 0.5}, 1.53),
        ("uniform_load_with_one_end_moment", {"beta_m": 0.8}, 1.55),
        ("uniform_load_with_equal_end_moments", {"beta_m": 0.75}, 1.22),
        ("uniform_moment", {}, 1.0),
        ("point_load", {}, 1.75),
        ("uniform_load", {}, 2.5),
    ],
)
def test_table_5_6_1_all_diagram_factors(load_case, case_inputs, expected):
    out = run_advanced_members(table_5_6_1_inputs(load_case, **case_inputs))
    assert out["values"]["moment_factor"] == pytest.approx(expected)
    assert out["clauses"] == ["5.6.1", "Table 5.6.1"]
    assert out["full_standard_compliance"] is False


@pytest.mark.parametrize(
    "load_case,case_inputs,expected",
    [
        ("end_moments", {"beta_m": 0.6}, 2.488),
        ("end_moments", {"beta_m": 0.600001}, 2.5),
        ("midspan_point_load_with_one_end_moment", {"beta_m": 0.899999}, 1.48499985),
        ("midspan_point_load_with_one_end_moment", {"beta_m": 0.9}, 1.5),
        ("uniform_load_with_one_end_moment", {"beta_m": 0.7}, 1.2),
        ("uniform_load_with_equal_end_moments", {"beta_m": 0.75}, 1.22),
    ],
)
def test_table_5_6_1_piecewise_boundaries(load_case, case_inputs, expected):
    out = run_advanced_members(table_5_6_1_inputs(load_case, **case_inputs))
    assert out["values"]["moment_factor"] == pytest.approx(expected)


@pytest.mark.parametrize(
    "load_case,case_inputs",
    [
        ("end_moments", {"beta_m": -1.01}),
        ("uniform_load_with_one_end_moment", {"beta_m": -0.01}),
        ("two_symmetric_point_loads", {"twice_a_over_length": 1.01}),
        ("uniform_moment", {"beta_m": 0.5}),
    ],
)
def test_table_5_6_1_rejects_out_of_scope_inputs(load_case, case_inputs):
    with pytest.raises(ValueError):
        run_advanced_members(table_5_6_1_inputs(load_case, **case_inputs))


def test_table_5_6_1_requires_restraint_and_diagram_verification():
    inputs = table_5_6_1_inputs("uniform_load")
    inputs["both_ends_restrained_verified"] = False
    with pytest.raises(ValueError):
        run_advanced_members(inputs)
    inputs = table_5_6_1_inputs("uniform_load")
    inputs.pop("table_5_6_1_diagram_verified")
    with pytest.raises(ValueError):
        run_advanced_members(inputs)


@pytest.mark.parametrize(
    "inputs,error",
    [
        (moment_factor_inputs(maximum_design_moment_knm=99), "must not be below"),
        (
            moment_factor_inputs(
                quarter_point_moment_2_knm=0,
                midpoint_moment_3_knm=0,
                quarter_point_moment_4_knm=0,
            ),
            "must be non-zero",
        ),
    ],
)
def test_clause_5_6_1_1_a_iii_rejects_inconsistent_moment_diagram(inputs, error):
    with pytest.raises(ValueError, match=error):
        run_advanced_members(inputs)


def unequal_flange_bending(beta_method="compression_flange_inertia", **updates):
    inputs = {
        "operation": "unequal_flange_bending",
        "section_capacity_knm": 200,
        "iy_mm4": 50_000_000,
        "torsion_constant_mm4": 200_000,
        "warping_constant_mm6": 8_000_000_000_000,
        "effective_length_mm": 15_000,
        "moment_factor": 1.2,
        "moment_factor_verified": True,
        "both_ends_restrained_verified": True,
        "action_knm": 120,
        "section_properties_verified": True,
        "constant_cross_section_verified": True,
        "beta_x_method": beta_method,
        "flange_centroid_spacing_mm": 400,
        "compression_flange_minor_inertia_mm4": 30_000_000,
    }
    if beta_method == "section_integral":
        inputs.pop("flange_centroid_spacing_mm")
        inputs.pop("compression_flange_minor_inertia_mm4")
        inputs["beta_x_mm"] = -64
        inputs["beta_x_integral_verified"] = True
    inputs.update(updates)
    return inputs


def test_unequal_flange_bending_from_compression_flange_inertia():
    out = run_advanced_members(unequal_flange_bending())
    values = out["values"]
    assert values["beta_x_mm"] == pytest.approx(64)
    assert values["reference_buckling_moment_knm"] == pytest.approx(208.97650338006295)
    assert values["slenderness_reduction"] == pytest.approx(0.6130961900821329)
    assert values["member_capacity_knm"] == pytest.approx(147.1430856197119)
    assert out["checks"][0]["design_capacity"] == pytest.approx(132.4287770577407)
    assert out["checks"][0]["satisfied"]
    assert out["clauses"] == ["5.6.1.1(a)", "5.6.1.1(2)", "5.6.1.2"]
    assert not out["full_standard_compliance"]


@pytest.mark.parametrize(
    "flange_inertia,beta_x,reference_moment",
    [
        (30_000_000, 64, 208.97650338006295),
        (10_000_000, -192, 156.831254259884),
    ],
)
def test_unequal_flange_inertia_method_sets_beta_sign(flange_inertia, beta_x, reference_moment):
    out = run_advanced_members(
        unequal_flange_bending(compression_flange_minor_inertia_mm4=flange_inertia)
    )
    assert out["values"]["beta_x_mm"] == pytest.approx(beta_x)
    assert out["values"]["reference_buckling_moment_knm"] == pytest.approx(reference_moment)


def test_unequal_flange_bending_accepts_verified_negative_integral_beta():
    out = run_advanced_members(unequal_flange_bending("section_integral"))
    assert out["values"]["beta_x_method"] == "section_integral"
    assert out["values"]["beta_x_mm"] == -64
    assert out["values"]["reference_buckling_moment_knm"] == pytest.approx(180.90296197251985)
    assert out["values"]["member_capacity_knm"] == pytest.approx(136.69231914794057)


def test_unequal_flange_bending_caps_member_capacity_at_section_capacity():
    out = run_advanced_members(unequal_flange_bending(moment_factor=2.5))
    assert out["values"]["member_capacity_knm"] == 200


def test_unequal_flange_bending_rejects_impossible_compression_flange_inertia():
    with pytest.raises(ValueError, match="must not exceed section minor inertia"):
        run_advanced_members(
            unequal_flange_bending(compression_flange_minor_inertia_mm4=50_000_001)
        )


def test_unequal_flange_bending_requires_constant_section_evidence():
    inputs = unequal_flange_bending()
    inputs.pop("constant_cross_section_verified")
    with pytest.raises(ValueError):
        run_advanced_members(inputs)


def test_unequal_flange_bending_requires_both_ends_restrained():
    with pytest.raises(ValueError):
        run_advanced_members(unequal_flange_bending(both_ends_restrained_verified=False))


def varying_section_bending(design_method="critical_section_reduced_reference", **updates):
    inputs = {
        "operation": "varying_section_bending",
        "design_method": design_method,
        "section_capacity_knm": 120,
        "reference_buckling_moment_knm": 100,
        "reference_buckling_moment_verified": True,
        "moment_factor": 1.3,
        "moment_factor_verified": True,
        "both_ends_restrained_verified": True,
        "action_knm": 60,
    }
    if design_method == "minimum_section":
        inputs["minimum_section_values_verified"] = True
    else:
        inputs.update(
            {
                "variation_type": "stepped",
                "segment_length_mm": 6000,
                "reduced_length_mm": 3000,
                "minimum_flange_area_mm2": 10_000,
                "critical_flange_area_mm2": 15_000,
                "minimum_depth_mm": 300,
                "critical_depth_mm": 400,
                "critical_section_values_verified": True,
            }
        )
    inputs.update(updates)
    return inputs


@pytest.mark.parametrize("variation_type", ["stepped", "tapered"])
def test_clause_5_6_1_1_b_critical_section_reduces_reference_moment(variation_type):
    inputs = varying_section_bending(variation_type=variation_type)
    if variation_type == "tapered":
        inputs.pop("reduced_length_mm")
    out = run_advanced_members(inputs)
    assert out["values"]["alpha_st"] == pytest.approx(0.76)
    assert out["values"]["adjusted_reference_buckling_moment_knm"] == pytest.approx(76)
    assert out["values"]["slenderness_reduction"] == pytest.approx(0.4588701523081464)
    assert out["values"]["member_capacity_knm"] == pytest.approx(71.58374376007083)
    assert out["clauses"][1] == "5.6.1.1(b)(ii)"


def test_clause_5_6_1_1_b_minimum_section_method_uses_unreduced_moment():
    out = run_advanced_members(varying_section_bending("minimum_section"))
    assert out["values"]["alpha_st"] is None
    assert out["values"]["adjusted_reference_buckling_moment_knm"] == 100
    assert out["values"]["member_capacity_knm"] == pytest.approx(84.90743825340327)
    assert out["clauses"][1] == "5.6.1.1(b)(i)"


def test_varying_section_bending_requires_both_ends_restrained():
    with pytest.raises(ValueError):
        run_advanced_members(varying_section_bending(both_ends_restrained_verified=False))


@pytest.mark.parametrize(
    "updates,error",
    [
        ({"reduced_length_mm": 6001}, "must not exceed the segment length"),
        ({"minimum_flange_area_mm2": 15_001}, "must not exceed critical-section area"),
        ({"minimum_depth_mm": 401}, "must not exceed critical-section depth"),
        (
            {
                "reduced_length_mm": 6000,
                "minimum_flange_area_mm2": 1e-9,
                "critical_flange_area_mm2": 1e15,
                "minimum_depth_mm": 1e-9,
                "critical_depth_mm": 1e15,
            },
            "reduction factor must be positive and finite",
        ),
    ],
)
def test_varying_section_bending_rejects_inconsistent_reduction_geometry(updates, error):
    with pytest.raises(ValueError, match=error):
        run_advanced_members(varying_section_bending(**updates))


@pytest.mark.parametrize(
    "arrangement,position,height,rotation_count,factor",
    [
        ("PP", "within_segment", "top_flange", 2, 1.176),
        ("PU", "within_segment", "top_flange", 0, 2.2),
        ("FL", "within_segment", "top_flange", 1, 1.4),
        ("FF", "within_segment", "shear_centre", 1, 0.85),
        ("PP", "at_segment_end", "top_flange", 1, 1.02),
    ],
)
def test_table_5_6_3_effective_length(arrangement, position, height, rotation_count, factor):
    out = run_advanced_members(
        {
            "operation": "lateral_buckling_effective_length",
            "segment_length_mm": 1000,
            "clear_flange_depth_mm": 200,
            "critical_flange_thickness_mm": 20,
            "web_thickness_mm": 10,
            "number_of_webs": 2,
            "restraint_arrangement": arrangement,
            "gravity_load_position": position,
            "load_height_position": height,
            "effective_rotation_restraint_count": rotation_count,
            "effective_rotation_restraints_verified": True,
        }
    )
    assert out["values"]["effective_length_factor"] == pytest.approx(factor)
    assert out["values"]["effective_length_mm"] == pytest.approx(1000 * factor)


def test_table_5_6_3_requires_effective_rotation_restraint_evidence():
    inputs = {
        "operation": "lateral_buckling_effective_length",
        "segment_length_mm": 1000,
        "clear_flange_depth_mm": 200,
        "critical_flange_thickness_mm": 20,
        "web_thickness_mm": 10,
        "number_of_webs": 2,
        "restraint_arrangement": "FF",
        "gravity_load_position": "within_segment",
        "load_height_position": "shear_centre",
        "effective_rotation_restraint_count": 1,
        "effective_rotation_restraints_verified": False,
    }
    with pytest.raises(ValueError, match="effective rotational restraints"):
        run_advanced_members(inputs)


def full_restraint(section_type, **properties):
    return {
        "operation": "full_lateral_restraint_limit",
        "section_type": section_type,
        "segment_length_mm": 1,
        "yield_strength_mpa": 250,
        "beta_m_basis": "conservative_minus_one",
        "section_properties_verified": True,
        "both_ends_restrained_verified": True,
        **properties,
    }


@pytest.mark.parametrize(
    "section_type,properties,length,expected_limit",
    [
        ("equal_flanged_i", {"radius_of_gyration_y_mm": 10}, 300, 30),
        ("equal_flanged_channel", {"radius_of_gyration_y_mm": 10}, 200, 20),
        (
            "unequal_flange_i",
            {
                "radius_of_gyration_y_mm": 10,
                "gross_area_mm2": 10000,
                "flange_centroid_spacing_mm": 400,
                "compression_flange_minor_inertia_mm4": 1000000,
                "section_minor_inertia_mm4": 2000000,
                "effective_section_modulus_ex_mm3": 2000000,
            },
            268.3281572999747,
            26.83281572999748,
        ),
        (
            "rhs_or_shs",
            {
                "radius_of_gyration_y_mm": 10,
                "flange_width_mm": 100,
                "web_depth_mm": 200,
            },
            1500,
            150,
        ),
        (
            "angle",
            {
                "thickness_mm": 10,
                "greater_leg_width_b1_mm": 100,
                "lesser_leg_width_b2_mm": 50,
            },
            247.48737341529164,
            24.748737341529164,
        ),
    ],
)
def test_clause_5_3_2_4_geometry_branches(section_type, properties, length, expected_limit):
    inputs = full_restraint(section_type, **properties)
    inputs["segment_length_mm"] = length
    out = run_advanced_members(inputs)
    assert out["values"]["permitted_slenderness"] == pytest.approx(expected_limit)
    assert out["values"]["full_lateral_restraint_qualifies"]
    assert out["checks"][0]["clause"] == "5.3.2.4"


@pytest.mark.parametrize(
    "beta_basis,extra,expected_beta,expected_limit",
    [
        ("conservative_minus_one", {}, -1.0, 30),
        ("transverse_loads", {}, -0.8, 40),
        (
            "end_moments",
            {
                "end_moment_1_magnitude_knm": 20,
                "end_moment_2_magnitude_knm": 80,
                "curvature": "reverse",
            },
            0.25,
            92.5,
        ),
        (
            "end_moments",
            {
                "end_moment_1_magnitude_knm": 20,
                "end_moment_2_magnitude_knm": 80,
                "curvature": "single",
            },
            -0.25,
            67.5,
        ),
    ],
)
def test_clause_5_3_2_4_beta_m_options(beta_basis, extra, expected_beta, expected_limit):
    inputs = full_restraint(
        "equal_flanged_i",
        radius_of_gyration_y_mm=10,
        beta_m_basis=beta_basis,
        **extra,
    )
    inputs["segment_length_mm"] = expected_limit * 10
    values = run_advanced_members(inputs)["values"]
    assert values["beta_m"] == pytest.approx(expected_beta)
    assert values["permitted_slenderness"] == pytest.approx(expected_limit)
    assert values["full_lateral_restraint_qualifies"]


def test_clause_5_3_2_4_rejects_unqualified_geometry_and_zero_end_moments():
    angle = full_restraint(
        "angle",
        thickness_mm=10,
        greater_leg_width_b1_mm=50,
        lesser_leg_width_b2_mm=100,
    )
    with pytest.raises(ValueError, match="b2 must not exceed b1"):
        run_advanced_members(angle)

    unequal_i = full_restraint(
        "unequal_flange_i",
        radius_of_gyration_y_mm=10,
        gross_area_mm2=10000,
        flange_centroid_spacing_mm=400,
        compression_flange_minor_inertia_mm4=2000000,
        section_minor_inertia_mm4=1000000,
        effective_section_modulus_ex_mm3=2000000,
    )
    with pytest.raises(ValueError, match="must not exceed"):
        run_advanced_members(unequal_i)

    zero_moments = full_restraint(
        "equal_flanged_i",
        radius_of_gyration_y_mm=10,
        beta_m_basis="end_moments",
        end_moment_1_magnitude_knm=0,
        end_moment_2_magnitude_knm=0,
        curvature="single",
    )
    with pytest.raises(ValueError, match="At least one end moment"):
        run_advanced_members(zero_moments)


def test_clause_5_3_2_4_rejects_segment_just_above_length_limit():
    inputs = full_restraint(
        "equal_flanged_i",
        radius_of_gyration_y_mm=10,
    )
    inputs["segment_length_mm"] = 300.001
    result = run_advanced_members(inputs)
    assert result["values"]["permitted_slenderness"] == 30
    assert not result["values"]["full_lateral_restraint_qualifies"]


def test_clause_5_3_2_2_continuous_restraint_route_records_all_conditions():
    result = run_advanced_members(
        {
            "operation": "continuous_lateral_restraints",
            "both_ends_restrained_verified": True,
            "continuous_restraints_at_critical_flange_verified": True,
            "continuous_restraints_satisfy_5_4_3_1_verified": True,
        }
    )
    assert result["values"]["full_lateral_restraint_qualifies"]
    assert [check["clause"] for check in result["checks"]] == [
        "5.3.2.2(a)",
        "5.3.2.2(b)",
        "5.4.3.1",
    ]


def test_clause_5_4_2_full_restraint_has_both_standard_alternatives():
    critical_flange_route = run_advanced_members(
        {
            "operation": "restraint_classification",
            "critical_flange_lateral_deflection_prevented_verified": True,
            "other_cross_section_point_lateral_deflection_prevented_verified": False,
            "twist_rotation_effectively_prevented_verified": False,
            "twist_rotation_partially_prevented_verified": True,
            "critical_flange_out_of_plane_rotation_significantly_restrained_verified": False,
        }
    )
    assert critical_flange_route["values"]["full_lateral_restraint_criterion_a_satisfied"]
    assert not critical_flange_route["values"]["full_lateral_restraint_criterion_b_satisfied"]
    assert critical_flange_route["values"]["full_lateral_restraint_qualifies"]
    assert critical_flange_route["values"]["lateral_restraint_qualifies"]

    other_point_route = run_advanced_members(
        {
            "operation": "restraint_classification",
            "critical_flange_lateral_deflection_prevented_verified": False,
            "other_cross_section_point_lateral_deflection_prevented_verified": True,
            "twist_rotation_effectively_prevented_verified": True,
            "twist_rotation_partially_prevented_verified": False,
            "critical_flange_out_of_plane_rotation_significantly_restrained_verified": True,
        }
    )
    assert not other_point_route["values"]["full_lateral_restraint_criterion_a_satisfied"]
    assert other_point_route["values"]["full_lateral_restraint_criterion_b_satisfied"]
    assert other_point_route["values"]["full_lateral_restraint_qualifies"]
    assert other_point_route["values"]["rotational_restraint_qualifies"]
    assert not other_point_route["values"]["lateral_restraint_qualifies"]


def test_clause_5_4_2_partial_restraint_uses_other_point_and_partial_twist():
    result = run_advanced_members(
        {
            "operation": "restraint_classification",
            "critical_flange_lateral_deflection_prevented_verified": False,
            "other_cross_section_point_lateral_deflection_prevented_verified": True,
            "twist_rotation_effectively_prevented_verified": False,
            "twist_rotation_partially_prevented_verified": True,
            "critical_flange_out_of_plane_rotation_significantly_restrained_verified": False,
        }
    )
    assert result["values"]["partial_lateral_restraint_qualifies"]
    assert not result["values"]["full_lateral_restraint_qualifies"]
    assert not result["values"]["rotational_restraint_qualifies"]
    assert not result["values"]["lateral_restraint_qualifies"]
    assert [check["clause"] for check in result["checks"]] == [
        "5.4.2.1(a)",
        "5.4.2.1(b)",
        "5.4.2.2",
        "5.4.2.3",
        "5.4.2.4",
    ]


@pytest.mark.parametrize(
    "classification,classification_clause,classification_verified,stiffness_verified,expected",
    [
        ("fully_restrained", "5.4.2.1", True, True, True),
        ("partially_restrained", "5.4.2.2", True, True, True),
        ("rotationally_restrained", "5.4.2.3", True, True, True),
        ("partially_restrained", "5.4.2.2", False, True, False),
        ("partially_restrained", "5.4.2.2", True, False, False),
    ],
)
def test_clause_5_4_3_4_comparable_flexural_stiffness_route(
    classification,
    classification_clause,
    classification_verified,
    stiffness_verified,
    expected,
):
    result = run_advanced_members(
        {
            "operation": "lateral_rotation_restraint",
            "method": "comparable_stiffness",
            "cross_section_restraint_classification": classification,
            "cross_section_restraint_classification_verified": classification_verified,
            "restraint_flexural_stiffness_comparable_to_member_verified": stiffness_verified,
            "stiffness_evidence_reference": "CALC-STIFFNESS-01",
        }
    )
    assert result["values"]["lateral_rotation_restraint_effective"] is expected
    assert [check["clause"] for check in result["checks"]] == [
        classification_clause,
        "5.4.3.4 comparable flexural stiffness",
    ]
    assert [check["satisfied"] for check in result["checks"]] == [
        classification_verified,
        stiffness_verified,
    ]
    assert result["clauses"] == ["5.4.3.4"]
    assert result["full_standard_compliance"] is False


@pytest.mark.parametrize(
    "fully_restrained,continuous,expected",
    [(True, True, True), (True, False, False), (False, True, False)],
)
def test_clause_5_4_3_4_adjacent_segment_route_requires_restraint_and_continuity(
    fully_restrained, continuous, expected
):
    result = run_advanced_members(
        {
            "operation": "lateral_rotation_restraint",
            "method": "adjacent_continuous_segment",
            "segment_full_lateral_restraint_verified": fully_restrained,
            "adjacent_segment_laterally_continuous_verified": continuous,
            "restraint_evidence_reference": "DRAWING-REST-01",
        }
    )
    assert result["values"]["lateral_rotation_restraint_effective"] is expected
    assert [check["satisfied"] for check in result["checks"]] == [fully_restrained, continuous]
    assert result["values"]["restraint_evidence_reference"] == "DRAWING-REST-01"


@pytest.mark.parametrize("analysis_verified", [True, False])
def test_clause_5_4_3_4_unrestrained_segment_requires_clause_5_6_4_member_resistance(
    analysis_verified,
):
    result = run_advanced_members(
        {
            "operation": "lateral_rotation_restraint",
            "method": "buckling_analysis",
            "member_resistance_determined_by_buckling_analysis_verified": analysis_verified,
            "buckling_analysis_reference": "BUCKLING-ANALYSIS-01",
        }
    )
    assert result["values"]["lateral_rotation_restraint_effective"] is analysis_verified
    assert result["checks"] == [
        {
            "clause": "5.6.4 member resistance by buckling analysis",
            "satisfied": analysis_verified,
        }
    ]
    assert result["values"]["buckling_analysis_reference"] == "BUCKLING-ANALYSIS-01"


def test_clause_5_4_3_4_evidence_fields_and_classification_are_required():
    comparable = {
        "operation": "lateral_rotation_restraint",
        "method": "comparable_stiffness",
        "cross_section_restraint_classification": "laterally_restrained",
        "cross_section_restraint_classification_verified": True,
        "restraint_flexural_stiffness_comparable_to_member_verified": True,
        "stiffness_evidence_reference": "CALC-STIFFNESS-01",
    }
    with pytest.raises(ValueError):
        run_advanced_members(comparable)

    adjacent = {
        "operation": "lateral_rotation_restraint",
        "method": "adjacent_continuous_segment",
        "segment_full_lateral_restraint_verified": True,
        "adjacent_segment_laterally_continuous_verified": True,
    }
    with pytest.raises(ValueError):
        run_advanced_members(adjacent)


def test_clause_5_3_2_3_checks_each_intermediate_restraint_subsegment():
    first = full_restraint(
        "equal_flanged_i",
        radius_of_gyration_y_mm=10,
    )
    first["segment_length_mm"] = 300
    second = full_restraint(
        "angle",
        thickness_mm=10,
        greater_leg_width_b1_mm=100,
        lesser_leg_width_b2_mm=50,
    )
    second["segment_length_mm"] = 240
    inputs = {
        "operation": "intermediate_lateral_restraints",
        "both_ends_restrained_verified": True,
        "intermediate_restraints_at_critical_flange_verified": True,
        "intermediate_restraints_satisfy_5_4_3_1_verified": True,
        "subsegment_checks": [first, second],
    }
    passed = run_advanced_members(inputs)
    assert passed["values"]["full_lateral_restraint_qualifies"]
    assert passed["values"]["subsegment_count"] == 2
    assert [check["satisfied"] for check in passed["checks"][-2:]] == [True, True]

    inputs["subsegment_checks"][1]["segment_length_mm"] = 250
    failed = run_advanced_members(inputs)
    assert not failed["values"]["full_lateral_restraint_qualifies"]
    assert [check["satisfied"] for check in failed["checks"][-2:]] == [True, False]


def test_clause_5_3_3_selects_largest_design_moment_to_section_capacity_ratio():
    result = run_advanced_members(
        {
            "operation": "critical_section",
            "sections": [
                {
                    "section_id": "A",
                    "design_moment_knm": 20,
                    "section_moment_capacity_knm": 40,
                },
                {
                    "section_id": "B",
                    "design_moment_knm": 36,
                    "section_moment_capacity_knm": 60,
                },
                {
                    "section_id": "C",
                    "design_moment_knm": 30,
                    "section_moment_capacity_knm": 100,
                },
            ],
        }
    )
    assert result["values"]["critical_section_id"] == "B"
    assert result["values"]["critical_section_ids"] == ["B"]
    assert result["values"]["maximum_moment_to_capacity_ratio"] == pytest.approx(0.6)


def test_critical_section_rejects_duplicate_section_identifiers():
    candidate = {
        "section_id": "A",
        "design_moment_knm": 20,
        "section_moment_capacity_knm": 40,
    }
    with pytest.raises(ValueError, match="identifiers must be unique"):
        run_advanced_members({"operation": "critical_section", "sections": [candidate, candidate]})


@pytest.mark.parametrize(
    "inputs,expected_position,expected_location,expected_clause",
    [
        (
            {
                "segment_end_condition": "both_ends_restrained",
                "compression_flange_position": "bottom",
            },
            "bottom",
            "compression",
            "5.5.2",
        ),
        (
            {
                "segment_end_condition": "one_end_unrestrained",
                "dominant_load": "gravity",
            },
            "top",
            "top",
            "5.5.3",
        ),
        (
            {
                "segment_end_condition": "one_end_unrestrained",
                "dominant_load": "wind",
                "wind_case": "external_pressure",
                "exterior_flange_position": "top",
            },
            "top",
            "exterior",
            "5.5.3",
        ),
        (
            {
                "segment_end_condition": "one_end_unrestrained",
                "dominant_load": "wind",
                "wind_case": "internal_suction",
                "exterior_flange_position": "top",
            },
            "top",
            "exterior",
            "5.5.3",
        ),
        (
            {
                "segment_end_condition": "one_end_unrestrained",
                "dominant_load": "wind",
                "wind_case": "internal_pressure",
                "exterior_flange_position": "top",
            },
            "bottom",
            "interior",
            "5.5.3",
        ),
        (
            {
                "segment_end_condition": "one_end_unrestrained",
                "dominant_load": "wind",
                "wind_case": "external_suction",
                "exterior_flange_position": "top",
            },
            "bottom",
            "interior",
            "5.5.3",
        ),
    ],
)
def test_clause_5_5_selects_the_prescribed_critical_flange(
    inputs, expected_position, expected_location, expected_clause
):
    result = run_advanced_members({"operation": "critical_flange", **inputs})
    assert result["values"]["critical_flange_position"] == expected_position
    assert result["values"]["critical_flange_location"] == expected_location
    assert expected_clause in result["clauses"]


def test_nonprincipal_rational_moments():
    inputs = {
        "operation": "nonprincipal_bending",
        "section_axial_capacity_kn": 1000,
        "section_moment_x_knm": 100,
        "section_moment_y_knm": 50,
        "reduced_member_moment_x_knm": 80,
        "reduced_member_moment_y_knm": 40,
        "axial_action_kn": 90,
        "moment_x_knm": 45,
        "moment_y_knm": 22.5,
        "deflections_constrained": True,
        "rational_analysis_verified": True,
    }
    out = run_advanced_members(inputs)
    assert out["values"]["section_interaction"] == pytest.approx(1.1)
    assert not out["checked_conditions_satisfied"]
    assert [check["clause"] for check in out["checks"]] == ["8.3.4"]

    inputs["deflections_constrained"] = False
    unrestrained = run_advanced_members(inputs)
    assert unrestrained["values"]["member_interaction"] == pytest.approx(2 * (0.625**1.4))
    assert [check["clause"] for check in unrestrained["checks"]] == ["8.3.4", "8.4.5"]
    assert not unrestrained["checked_conditions_satisfied"]


def plastic(web_lambda=25, ratio=0.1):
    return {
        "operation": "plastic_in_plane",
        "compact_doubly_symmetric_i_verified": True,
        "section_axial_capacity_kn": 1000,
        "section_moment_x_knm": 100,
        "section_moment_y_knm": 50,
        "axial_action_kn": ratio * 900,
        "axial_mode": "compression",
        "moment_x_knm": 10,
        "moment_y_knm": 0,
        "elastic_buckling_load_actual_length_kn": 4000,
        "beta_m": 0,
        "web_clear_depth_mm": web_lambda * 10,
        "web_thickness_mm": 10,
        "yield_mpa": 250,
    }


@pytest.mark.parametrize(
    "slenderness,limit",
    [
        (25, 1),
        (27.4, 0.91),
        (45, 0.271532846715),
        (82, 0.001459854015),
    ],
)
def test_plastic_web_branches(slenderness, limit):
    out = run_advanced_members(plastic(slenderness))
    assert out["values"]["web_ratio_limit"] == pytest.approx(limit)
    assert out["values"]["reduced_moment_x_knm"] == 100
    assert out["values"]["member_ratio_limit"] == pytest.approx(1.44)


def test_plastic_high_axial_branch_and_ineligible_web():
    out = run_advanced_members(plastic(83, 0.2))
    assert out["values"]["member_ratio_limit"] == pytest.approx(1 / 3)
    assert not out["checked_conditions_satisfied"]
    d = plastic()
    d["moment_y_knm"] = 1
    with pytest.raises(ValueError, match="uniaxial"):
        run_advanced_members(d)


def test_battened_slenderness_and_back_to_back_shear():
    d = {
        "operation": "built_up_compression",
        "construction": "back_to_back",
        "section_capacity_kn": 1000,
        "member_capacity_kn": 500,
        "modified_member_slenderness": 100,
        "axial_action_kn": 100,
        "integral_slenderness_perpendicular": 40,
        "integral_slenderness_parallel": 100,
        "component_slenderness": 30,
        "number_of_bays": 3,
        "similar_symmetric_components_verified": True,
    }
    out = run_advanced_members(d)
    assert out["values"]["effective_slenderness_perpendicular"] == 50  # 30-40-50 triangle
    assert out["values"]["transverse_design_shear_kn"] == pytest.approx(3.14159265359)
    assert out["values"]["back_to_back_connection_longitudinal_shear_kn"] == pytest.approx(
        23.5619449019
    )
    assert out["checked_conditions_satisfied"]
    d["number_of_bays"] = 2
    assert not run_advanced_members(d)["checked_conditions_satisfied"]
    demand = out["values"]["back_to_back_connection_longitudinal_shear_kn"]
    d["number_of_bays"] = 3
    d["interconnection_design"] = {
        "design_capacity_kn": demand,
        "capacity_verified": True,
    }
    checked = run_advanced_members(d)
    assert checked["checked_conditions_satisfied"]
    assert checked["checks"][-1]["clause"] == "6.5.1.5"
    d["interconnection_design"]["design_capacity_kn"] = demand - 0.001
    assert not run_advanced_members(d)["checks"][-1]["satisfied"]
    d["construction"] = "laced"
    with pytest.raises(ValueError, match="back-to-back"):
        run_advanced_members(d)


def compression_built_up_member_actions(connection_type="batten", **changes):
    common = {
        "operation": "compression_built_up_member_actions",
        "connection_type": connection_type,
        "section_capacity_kn": 1000,
        "member_capacity_kn": 500,
        "modified_member_slenderness": 100,
        "axial_action_kn": 100,
        "parallel_connection_planes": 2,
        "connection_plane_count_verified": True,
        "equal_connection_plane_participation_verified": True,
        "member_action_envelope_verified": True,
        "all_connection_bays_assessed_verified": True,
        "action_analysis_reference": "verified built-up compression analysis 01",
    }
    if connection_type == "lacing":
        common.update(
            {
                "lacing_arrangement": "double",
                "lacing_force_path_verified": True,
                "bays": [
                    {
                        "start_station_mm": 0,
                        "end_station_mm": 1000,
                        "transverse_connection_spacing_mm": 1000,
                        "bay_geometry_verified": True,
                    }
                ],
            }
        )
    else:
        common["bays"] = [
            {
                "start_station_mm": 0,
                "end_station_mm": 1200,
                "connection_group_centroid_spacing_mm": 300,
                "bay_geometry_verified": True,
            }
        ]
    common.update(changes)
    return common


def test_clause_6_4_1_and_6_4_2_3_compression_lacing_actions():
    out = run_advanced_members(compression_built_up_member_actions("lacing"))
    action = out["values"]["action_intervals"][0]
    assert out["values"]["transverse_design_shear_kn"] == pytest.approx(3.14159265359)
    assert action["lacing_angle_degrees"] == pytest.approx(45)
    assert action["design_transverse_shear_per_plane_kn"] == pytest.approx(3.14159265359 / 2)
    assert action["design_lacing_bar_force_per_plane_kn"] == pytest.approx(
        3.14159265359 / (2 * (2**0.5 / 2))
    )
    assert out["clauses"] == ["6.4.1", "6.4.2.3"]
    assert out["checked_conditions_satisfied"]

    out = run_advanced_members(
        compression_built_up_member_actions(
            "lacing", section_capacity_kn=500, member_capacity_kn=500
        )
    )
    assert out["values"]["strength_based_shear_kn"] == 0
    assert out["values"]["transverse_design_shear_kn"] == pytest.approx(1)


def test_clause_6_4_3_7_compression_batten_and_tie_plate_actions():
    batten = run_advanced_members(compression_built_up_member_actions("batten"))
    action = batten["values"]["action_intervals"][0]
    assert batten["clauses"] == ["6.4.1", "6.4.3.7"]
    assert action["design_batten_longitudinal_shear_per_plane_kn"] == pytest.approx(
        2 * 3.14159265359
    )
    assert action["design_batten_moment_per_plane_knm"] == pytest.approx(0.3 * 3.14159265359)
    assert batten["checked_conditions_satisfied"]

    tie_plate = run_advanced_members(
        compression_built_up_member_actions(
            "lacing_tie_plate",
            bays=[
                {
                    "start_station_mm": 0,
                    "end_station_mm": 1200,
                    "connection_group_centroid_spacing_mm": 300,
                    "bay_geometry_verified": True,
                }
            ],
        )
    )
    assert tie_plate["clauses"] == ["6.4.1", "6.4.2.7", "6.4.3.7"]
    assert tie_plate["checked_conditions_satisfied"]


def test_compression_built_up_action_requires_complete_valid_geometry():
    data = compression_built_up_member_actions()
    data["bays"][0]["end_station_mm"] = 0
    with pytest.raises(ValueError, match="positive length"):
        run_advanced_members(data)

    data = compression_built_up_member_actions()
    data["member_capacity_kn"] = data["section_capacity_kn"] + 1
    with pytest.raises(ValueError, match="cannot exceed section capacity"):
        run_advanced_members(data)

    data = compression_built_up_member_actions("lacing")
    data["lacing_force_path_verified"] = False
    with pytest.raises(ValueError, match="lacing_force_path_verified"):
        run_advanced_members(data)

    data = compression_built_up_member_actions("lacing")
    data["lacing_arrangement"] = "single"
    data["bays"][0]["transverse_connection_spacing_mm"] = 600
    out = run_advanced_members(data)
    assert out["checks"][1]["clause"] == "6.4.2.3"
    assert not out["checks"][1]["satisfied"]
    assert not out["checked_conditions_satisfied"]


def compression_built_up_connection_layout(
    connection_arrangement="separated", end_connection_method="fasteners", **changes
):
    data = {
        "operation": "compression_built_up_connection_layout",
        "connection_arrangement": connection_arrangement,
        "eligible_component_forms_verified": True,
        "similar_sections_verified": True,
        "symmetrical_arrangement_verified": True,
        "rectangular_axes_aligned_verified": True,
        "member_length_mm": 3000,
        "bay_lengths_mm": [1000, 1000, 1000],
        "all_connection_bays_assessed_verified": True,
        "approximately_equal_bays_verified": True,
        "all_end_connection_lines_assessed_verified": True,
        "end_connection_method": end_connection_method,
        "layout_evidence_reference": "verified built-up compression layout 01",
    }
    if connection_arrangement == "separated":
        data["separated_within_end_gusset_spacing_verified"] = True
        data["components_interconnected_by_fasteners_verified"] = True
    else:
        data["components_in_contact_or_continuously_packed_verified"] = True
    if end_connection_method == "fasteners":
        data["fasteners_per_end_connection_line"] = 2
    else:
        data["equivalent_end_welds_verified"] = True
    data.update(changes)
    return data


def test_clause_6_5_compression_built_up_connection_layout_routes():
    separated = run_advanced_members(compression_built_up_connection_layout())
    assert separated["clauses"] == ["6.5.1.1", "6.5.1.2", "6.5.1.4"]
    assert separated["values"]["bay_count"] == 3
    assert separated["values"]["maximum_to_minimum_bay_length_ratio"] == pytest.approx(1)
    assert separated["checked_conditions_satisfied"]

    in_contact = run_advanced_members(
        compression_built_up_connection_layout(
            connection_arrangement="in_contact", end_connection_method="welds"
        )
    )
    assert in_contact["clauses"] == ["6.5.2.1", "6.5.2.2", "6.5.2.4"]
    assert in_contact["checked_conditions_satisfied"]


def test_clause_6_5_compression_built_up_connection_layout_boundaries():
    two_bays = run_advanced_members(
        compression_built_up_connection_layout(
            member_length_mm=2000,
            bay_lengths_mm=[1000, 1000],
        )
    )
    minimum_bay_check = next(
        check
        for check in two_bays["checks"]
        if check["condition"] == "minimum of three connection bays"
    )
    assert not minimum_bay_check["satisfied"]
    assert not two_bays["checked_conditions_satisfied"]

    one_fastener = run_advanced_members(
        compression_built_up_connection_layout(fasteners_per_end_connection_line=1)
    )
    assert not one_fastener["checks"][-1]["satisfied"]

    incomplete_length = run_advanced_members(
        compression_built_up_connection_layout(member_length_mm=3100)
    )
    member_coverage_check = next(
        check
        for check in incomplete_length["checks"]
        if check["condition"] == "complete connection-bay lengths span the member"
    )
    assert not member_coverage_check["satisfied"]

    poor_separation = run_advanced_members(
        compression_built_up_connection_layout(separated_within_end_gusset_spacing_verified=False)
    )
    assert not poor_separation["checks"][1]["satisfied"]

    missing_interconnections = run_advanced_members(
        compression_built_up_connection_layout(
            components_interconnected_by_fasteners_verified=False
        )
    )
    interconnection_check = next(
        check
        for check in missing_interconnections["checks"]
        if check["condition"] == "separated main components are interconnected by fasteners"
    )
    assert not interconnection_check["satisfied"]


@pytest.mark.parametrize(
    ("arrangement", "clause"),
    [
        ("separated_back_to_back", "7.4.3(a)(i)"),
        ("laced", "7.4.4(b)"),
        ("battened", "7.4.5(a)"),
    ],
)
def test_tension_component_slenderness_boundaries(arrangement, clause):
    d = {
        "operation": "tension_component_slenderness",
        "arrangement": arrangement,
        "intervals_and_radii_verified": True,
        "component_intervals": [
            {"unrestrained_length_mm": 1500, "minimum_radius_of_gyration_mm": 5},
            {"unrestrained_length_mm": 600, "minimum_radius_of_gyration_mm": 10},
        ],
    }
    out = run_advanced_members(d)
    assert out["values"]["maximum_component_slenderness"] == 300
    assert out["clauses"] == [clause]
    assert out["checked_conditions_satisfied"]
    d["component_intervals"][0]["unrestrained_length_mm"] = 1500.001
    assert not run_advanced_members(d)["checked_conditions_satisfied"]
    d["intervals_and_radii_verified"] = False
    with pytest.raises(ValueError):
        run_advanced_members(d)


def test_lacing_length_slenderness_and_tie_limits():
    d = {
        "operation": "lacing",
        "mode": "double_connected",
        "member_mode": "compression",
        "angle_degrees": 45,
        "inner_connection_distance_mm": 1000,
        "radius_mm": 5,
        "tie_type": "intermediate",
        "component_connection_centroid_distance_mm": 200,
        "tie_width_mm": 150,
        "tie_thickness_mm": 4,
        "tie_inner_connection_distance_mm": 200,
        "tie_edge_stiffened": False,
        "tie_edge_stiffener_slenderness": 0,
    }
    out = run_advanced_members(d)
    assert out["values"]["effective_length_mm"] == 700
    assert out["values"]["slenderness"] == 140
    assert out["checked_conditions_satisfied"]
    d["angle_degrees"] = 50.1
    assert not run_advanced_members(d)["checked_conditions_satisfied"]
    d.update(
        member_mode="tension",
        angle_degrees=45,
        tie_edge_stiffened=True,
        tie_edge_stiffener_slenderness=100,
        tie_thickness_mm=3.39,
    )
    out = run_advanced_members(d)
    checks = {check.get("clause"): check for check in out["checks"]}
    assert out["values"]["required_tie_thickness_mm"] == pytest.approx(3.4)
    assert checks["7.4.4(a)"]["satisfied"]
    assert checks["7.4.4"]["satisfied"] is False
    assert not out["checked_conditions_satisfied"]
    d["tie_thickness_mm"] = 3.4
    assert run_advanced_members(d)["checked_conditions_satisfied"]

    d.update(
        member_mode="compression",
        tie_thickness_mm=3,
        tie_edge_stiffened=True,
        tie_edge_stiffener_slenderness=169.9,
    )
    out = run_advanced_members(d)
    checks = {check.get("clause"): check for check in out["checks"]}
    assert checks["6.4.2.7"]["satisfied"]
    assert out["checked_conditions_satisfied"]


def batten():
    return {
        "operation": "batten",
        "type": "intermediate",
        "member_mode": "compression",
        "centroid_distance_mm": 200,
        "narrower_component_width_mm": 60,
        "radius_mm": 2,
        "width_mm": 120,
        "thickness_mm": 4,
        "inner_connection_distance_mm": 200,
        "edge_stiffened": False,
        "edge_stiffener_slenderness": 0,
        "transverse_shear_kn": 10,
        "longitudinal_spacing_mm": 1000,
        "connection_centroid_distance_mm": 200,
        "parallel_planes": 2,
        "effective_end_width_mm": 200,
    }


def test_batten_force_units_and_dimensions():
    out = run_advanced_members(batten())
    assert out["values"]["effective_length_mm"] == 140
    assert out["values"]["minimum_width_mm"] == 120
    assert out["values"]["connection_longitudinal_shear_kn"] == 25
    assert out["values"]["connection_moment_knm"] == 2.5
    assert out["checked_conditions_satisfied"]
    d = batten()
    d["member_mode"] = "tension"
    d["connection_type"] = "bolted"
    d["bolts_per_component_connection"] = 2
    tension = run_advanced_members(d)
    assert tension["values"]["connection_longitudinal_shear_kn"] is None
    assert tension["checked_conditions_satisfied"]


def test_tension_batten_checks_minimum_thickness_and_two_bolts_per_connection():
    d = batten()
    d.update(
        member_mode="tension",
        connection_type="bolted",
        bolts_per_component_connection=2,
        edge_stiffened=True,
        edge_stiffener_slenderness=100,
        thickness_mm=3.39,
    )
    out = run_advanced_members(d)
    checks = {check["clause"]: check for check in out["checks"]}
    assert out["values"]["minimum_thickness_mm"] == pytest.approx(3.4)
    assert checks["7.4.5(b)"]["satisfied"]
    assert checks["7.4.5(c)"]["satisfied"] is False
    assert checks["7.4.5(d)"]["satisfied"]
    assert "6.4.3.7" not in out["clauses"]
    assert not out["checked_conditions_satisfied"]

    d["thickness_mm"] = 3.4
    d["bolts_per_component_connection"] = 1
    out = run_advanced_members(d)
    checks = {check["clause"]: check for check in out["checks"]}
    assert checks["7.4.5(c)"]["satisfied"]
    assert checks["7.4.5(b)"]["satisfied"] is False
    assert not out["checked_conditions_satisfied"]

    d["connection_type"] = "welded"
    del d["bolts_per_component_connection"]
    assert run_advanced_members(d)["checked_conditions_satisfied"]

    d["connection_type"] = "bolted"
    with pytest.raises(ValueError, match="bolt count"):
        run_advanced_members(d)


def test_tension_connection_actions_are_shared_equally_between_parallel_planes():
    batten_actions = run_advanced_members(
        {
            "operation": "tension_connection_plane_distribution",
            "connection_type": "batten",
            "parallel_connection_planes": 3,
            "total_design_force_kn": 120,
            "total_design_moment_knm": -6,
        }
    )
    assert batten_actions["clauses"] == ["7.4.2"]
    assert batten_actions["values"]["design_force_per_plane_kn"] == 40
    assert batten_actions["values"]["design_moment_per_plane_knm"] == -2
    assert batten_actions["checked_conditions_satisfied"]

    lacing_actions = run_advanced_members(
        {
            "operation": "tension_connection_plane_distribution",
            "connection_type": "lacing",
            "parallel_connection_planes": 2,
            "total_design_force_kn": -45,
        }
    )
    assert lacing_actions["values"]["design_force_per_plane_kn"] == -22.5
    assert lacing_actions["values"]["design_moment_per_plane_knm"] is None

    with pytest.raises(ValueError, match="lacing distribution"):
        run_advanced_members(
            {
                "operation": "tension_connection_plane_distribution",
                "connection_type": "lacing",
                "parallel_connection_planes": 2,
                "total_design_force_kn": 45,
                "total_design_moment_knm": 3,
            }
        )


def tension_built_up_member_actions(**changes):
    data = {
        "operation": "tension_built_up_member_actions",
        "connection_type": "batten",
        "bending_axis": "major_x",
        "parallel_connection_planes": 3,
        "connection_plane_count_verified": True,
        "member_action_analysis_verified": True,
        "all_connection_bays_assessed_verified": True,
        "member_action_analysis_reference": "verified member analysis case 17",
        "batten_connection_centroid_distance_mm": 200,
        "bays": [
            {
                "start_station_mm": 0,
                "end_station_mm": 600,
                "start_design_moment_knm": 0,
                "end_design_moment_knm": 6,
                "linear_moment_distribution_verified": True,
            },
            {
                "start_station_mm": 600,
                "end_station_mm": 1800,
                "start_design_moment_knm": 6,
                "end_design_moment_knm": 18,
                "linear_moment_distribution_verified": True,
            },
        ],
    }
    data.update(changes)
    return data


def test_tension_built_up_batten_actions_from_member_moment_gradient():
    out = run_advanced_members(tension_built_up_member_actions())
    assert out["clauses"] == ["7.4.2"]
    first, second = out["values"]["action_intervals"]
    assert first["signed_member_transverse_shear_kn"] == pytest.approx(10)
    assert first["design_transverse_shear_per_plane_kn"] == pytest.approx(10 / 3)
    assert first["design_batten_longitudinal_shear_per_plane_kn"] == pytest.approx(10)
    assert first["design_batten_moment_per_plane_knm"] == pytest.approx(1)
    assert second["local_design_transverse_shear_kn"] == pytest.approx(10)
    assert second["design_batten_longitudinal_shear_per_plane_kn"] == pytest.approx(20)
    assert second["design_batten_moment_per_plane_knm"] == pytest.approx(2)
    assert "does not invoke the Clause 6.4.3.7" in " ".join(out["limitations"])
    assert out["checked_conditions_satisfied"]


def test_tension_built_up_lacing_actions_and_angle_boundary():
    data = tension_built_up_member_actions(
        connection_type="lacing",
        bending_axis="minor_y",
        parallel_connection_planes=2,
        lacing_arrangement="double",
        lacing_connection_spacing_mm=600,
        bays=[
            {
                "start_station_mm": 0,
                "end_station_mm": 600,
                "start_design_moment_knm": 12,
                "end_design_moment_knm": 0,
                "linear_moment_distribution_verified": True,
            }
        ],
    )
    del data["batten_connection_centroid_distance_mm"]
    out = run_advanced_members(data)
    action = out["values"]["action_intervals"][0]
    assert out["clauses"] == ["7.4.2", "7.4.4", "6.4.2.3"]
    assert action["signed_member_transverse_shear_kn"] == pytest.approx(-20)
    assert action["lacing_angle_degrees"] == pytest.approx(45)
    assert action["design_lacing_bar_force_per_plane_kn"] == pytest.approx(20 / (2**0.5))
    assert out["checked_conditions_satisfied"]

    data["lacing_connection_spacing_mm"] = 300
    out = run_advanced_members(data)
    assert not out["checks"][-1]["satisfied"]
    assert not out["checked_conditions_satisfied"]


def test_tension_built_up_action_analysis_requires_complete_verified_linear_bays():
    data = tension_built_up_member_actions()
    data["bays"][0]["linear_moment_distribution_verified"] = False
    with pytest.raises(ValueError, match="linear_moment_distribution_verified"):
        run_advanced_members(data)

    data = tension_built_up_member_actions()
    data["bays"][1]["start_station_mm"] = 601
    with pytest.raises(ValueError, match="ordered and contiguous"):
        run_advanced_members(data)


def test_tension_back_to_back_connection_layout_routes():
    separated = {
        "operation": "tension_built_up_connection_layout",
        "connection_arrangement": "separated",
        "two_eligible_components_verified": True,
        "discontinuous_back_to_back_connection_verified": True,
        "separated_within_end_gusset_spacing_verified": True,
        "member_length_mm": 3000,
        "bay_lengths_mm": [1000, 1000, 1000],
        "approximately_equal_bays_verified": True,
        "end_connection_method": "fasteners",
        "fasteners_per_connection_line_at_each_end": 2,
    }
    out = run_advanced_members(separated)
    assert out["clauses"] == ["7.4.3(a)(ii)", "6.5.1.4"]
    assert out["values"]["bay_count"] == 3
    assert out["values"]["end_connection"]["satisfied"]
    assert out["checked_conditions_satisfied"]

    in_contact = dict(separated)
    in_contact.update(
        connection_arrangement="in_contact",
        bay_lengths_mm=[990, 1000, 1010],
        end_connection_method="welds",
        equivalent_end_welds_verified=True,
    )
    del in_contact["separated_within_end_gusset_spacing_verified"]
    del in_contact["fasteners_per_connection_line_at_each_end"]
    out = run_advanced_members(in_contact)
    assert out["clauses"] == ["7.4.3(b)", "6.5.2.4"]
    assert out["values"]["end_connection"]["method"] == "equivalent_welds"
    assert out["checked_conditions_satisfied"]

    separated["bay_lengths_mm"] = [1000, 1000, 999]
    with pytest.raises(ValueError, match="sum to the member length"):
        run_advanced_members(separated)
    separated["bay_lengths_mm"] = [1000, 1000, 1000]
    del separated["fasteners_per_connection_line_at_each_end"]
    with pytest.raises(ValueError, match="Fastener end connections"):
        run_advanced_members(separated)


def tension_built_up_interconnection(**changes):
    data = {
        "operation": "tension_built_up_interconnection",
        "connection_arrangement": "separated",
        "parallel_connection_planes": 2,
        "connection_plane_count_verified": True,
        "all_interconnections_assessed_verified": True,
        "interconnections": [
            {
                "local_design_transverse_shear_kn": 40,
                "transverse_shear_verified": True,
                "component_length_between_connections_mm": 600,
                "minimum_radius_of_gyration_mm": 20,
                "geometry_verified": True,
                "design_capacity_by_plane_kn": [150, 149.99],
                "capacity_verified": True,
            },
            {
                "local_design_transverse_shear_kn": 32,
                "transverse_shear_verified": True,
                "component_length_between_connections_mm": 500,
                "minimum_radius_of_gyration_mm": 25,
                "geometry_verified": True,
                "design_capacity_by_plane_kn": [100, 100],
                "capacity_verified": True,
            },
        ],
    }
    data.update(changes)
    return data


def test_tension_built_up_interconnection_demand_and_plane_capacity():
    out = run_advanced_members(tension_built_up_interconnection())
    values = out["values"]
    assert out["clauses"] == ["7.4.2", "7.4.3(a)(ii)", "6.5.1.5"]
    assert values["interconnections"][0]["component_slenderness"] == pytest.approx(30)
    assert values["interconnections"][0]["local_design_transverse_shear_kn"] == pytest.approx(40)
    assert values["interconnections"][0]["total_design_longitudinal_shear_kn"] == pytest.approx(300)
    assert values["interconnections"][0]["design_shear_per_plane_kn"] == pytest.approx(150)
    assert values["interconnections"][1]["local_design_transverse_shear_kn"] == pytest.approx(32)
    assert values["interconnections"][1]["design_shear_per_plane_kn"] == pytest.approx(80)
    assert out["checks"][0]["satisfied"]
    assert not out["checks"][1]["satisfied"]
    assert all(check["satisfied"] for check in out["checks"][2:])
    assert not out["checked_conditions_satisfied"]


def test_tension_built_up_interconnection_in_contact_clause_and_exact_capacity():
    data = tension_built_up_interconnection(
        connection_arrangement="in_contact",
        interconnections=[
            {
                "local_design_transverse_shear_kn": 40,
                "transverse_shear_verified": True,
                "component_length_between_connections_mm": 600,
                "minimum_radius_of_gyration_mm": 20,
                "geometry_verified": True,
                "design_capacity_by_plane_kn": [150, 150],
                "capacity_verified": True,
            }
        ],
    )
    out = run_advanced_members(data)
    assert out["clauses"] == ["7.4.2", "7.4.3(b)", "6.5.2.5"]
    assert out["checks"][0]["design_demand_kn"] == pytest.approx(150)
    assert out["checked_conditions_satisfied"]


def test_tension_built_up_interconnection_rejects_missing_plane_capacity():
    data = tension_built_up_interconnection(
        interconnections=[
            {
                "local_design_transverse_shear_kn": 40,
                "transverse_shear_verified": True,
                "component_length_between_connections_mm": 600,
                "minimum_radius_of_gyration_mm": 20,
                "geometry_verified": True,
                "design_capacity_by_plane_kn": [150],
                "capacity_verified": True,
            }
        ]
    )
    with pytest.raises(ValueError, match="one verified design capacity"):
        run_advanced_members(data)
    data = tension_built_up_interconnection()
    data["all_interconnections_assessed_verified"] = False
    with pytest.raises(ValueError, match="all_interconnections_assessed_verified"):
        run_advanced_members(data)


def pin_member(**changes):
    d = {
        "operation": "pin_tension_member",
        "design_tension_kn": 306,
        "yield_strength_mpa": 300,
        "ultimate_strength_mpa": 400,
        "gross_area_mm2": 2000,
        "member_net_area_mm2": 1500,
        "tension_distribution_factor": 0.85,
        "member_net_area_assessed_verified": True,
        "tension_distribution_factor_assessed_verified": True,
        "thickness_mm": 10,
        "hole_to_edge_distance_mm": 40,
        "internal_nut_clamped_ply": False,
        "net_area_beyond_hole_planes_mm2": [1200, 1190],
        "net_area_perpendicular_mm2": 1600,
        "all_beyond_hole_planes_assessed_verified": True,
        "pin_plates_distribute_load_without_eccentricity_verified": True,
    }
    d.update(changes)
    return d


def test_pin_member_derives_required_area_and_checks_clause_7_2_capacity():
    out = run_advanced_members(pin_member())
    values = out["values"]
    required_net_area = 306000 / (0.9 * 0.85 * 0.85 * 400)
    assert values["required_gross_area_mm2"] == pytest.approx(306000 / (0.9 * 300))
    assert values["required_member_net_area_mm2"] == pytest.approx(required_net_area)
    assert values["minimum_net_area_perpendicular_mm2"] == pytest.approx(1.33 * required_net_area)
    assert values["gross_yield_nominal_capacity_kn"] == pytest.approx(600)
    assert values["net_fracture_nominal_capacity_kn"] == pytest.approx(433.5)
    assert values["design_section_tension_capacity_kn"] == pytest.approx(390.15)
    assert values["governing_capacity_mode"] == "net section fracture"
    assert out["clauses"] == ["7.1", "7.2", "7.5"]
    assert out["checked_conditions_satisfied"]


def test_pin_member_checks_every_beyond_hole_plane_and_pin_exemption():
    required_net_area = 306000 / (0.9 * 0.85 * 0.85 * 400)
    out = run_advanced_members(
        pin_member(
            thickness_mm=9,
            internal_nut_clamped_ply=True,
            net_area_beyond_hole_planes_mm2=[1200, required_net_area - 0.01],
        )
    )
    assert out["checks"][2]["clause"] == "7.5(a)"
    assert out["checks"][2]["satisfied"]
    assert out["checks"][4]["plane_index"] == 2
    assert not out["checks"][4]["satisfied"]
    assert not out["checked_conditions_satisfied"]


def test_pin_member_thickness_and_area_limits_are_inclusive():
    required_net_area = 306000 / (0.9 * 0.85 * 0.85 * 400)
    out = run_advanced_members(
        pin_member(
            thickness_mm=10,
            net_area_beyond_hole_planes_mm2=[required_net_area],
            net_area_perpendicular_mm2=1.33 * required_net_area,
        )
    )
    assert out["checked_conditions_satisfied"]


def test_pin_member_rejects_invalid_strength_area_and_distribution_factor():
    with pytest.raises(ValueError, match="Ultimate strength"):
        run_advanced_members(pin_member(ultimate_strength_mpa=299))
    with pytest.raises(ValueError, match="net area must not exceed gross"):
        run_advanced_members(pin_member(member_net_area_mm2=2001))
    with pytest.raises(ValueError, match="not valid under any"):
        run_advanced_members(pin_member(tension_distribution_factor=0.8))


def test_pin_member_fails_when_either_section_capacity_is_below_design_tension():
    net_fracture_failure = run_advanced_members(pin_member(member_net_area_mm2=1000))
    assert net_fracture_failure["checks"][0]["satisfied"]
    assert not net_fracture_failure["checks"][1]["satisfied"]
    assert not net_fracture_failure["checked_conditions_satisfied"]

    gross_yield_failure = run_advanced_members(
        pin_member(
            gross_area_mm2=1000,
            member_net_area_mm2=1000,
            ultimate_strength_mpa=600,
            tension_distribution_factor=1.0,
            net_area_beyond_hole_planes_mm2=[800, 800],
            net_area_perpendicular_mm2=900,
        )
    )
    assert not gross_yield_failure["checks"][0]["satisfied"]
    assert gross_yield_failure["checks"][1]["satisfied"]
    assert not gross_yield_failure["checked_conditions_satisfied"]


def test_parallel_restraint_and_analysis_force_envelope():
    d = {
        "operation": "restraint_action",
        "type": "compression",
        "connected_force_kn": 100,
        "beyond_forces_kn": [100, 100, 100, 100, 100, 100],
        "analysis_restraint_force_kn": 8,
    }
    out = run_advanced_members(d)
    assert out["values"]["minimum_transverse_force_kn"] == 10
    assert out["values"]["design_restraint_force_kn"] == 10
    d["analysis_restraint_force_kn"] = 11
    assert run_advanced_members(d)["values"]["design_restraint_force_kn"] == 11
    d["beyond_forces_kn"].append(100)
    with pytest.raises(ValueError):
        run_advanced_members(d)


def test_separator_diaphragm_minimum_and_equal_share():
    d = {
        "operation": "separator_diaphragm",
        "device_type": "diaphragm",
        "member_count": 3,
        "device_count": 4,
        "maximum_compression_flange_force_kn": 800,
        "external_vertical_force_transfer_required": True,
        "side_by_side_i_sections_or_channels_verified": True,
    }
    out = run_advanced_members(d)
    assert out["values"]["minimum_total_transverse_force_kn"] == pytest.approx(20)
    assert out["values"]["minimum_transverse_force_per_device_kn"] == pytest.approx(5)
    assert out["full_standard_compliance"] is False
    d["device_type"] = "separator"
    with pytest.raises(ValueError, match="diaphragms"):
        run_advanced_members(d)
    d["external_vertical_force_transfer_required"] = False
    assert run_advanced_members(d)["values"]["minimum_transverse_force_per_device_kn"] == 5


def test_separator_diaphragm_scope_and_count_are_enforced():
    d = {
        "operation": "separator_diaphragm",
        "device_type": "separator",
        "member_count": 2,
        "device_count": 1,
        "maximum_compression_flange_force_kn": 400,
        "external_vertical_force_transfer_required": False,
        "side_by_side_i_sections_or_channels_verified": True,
    }
    assert run_advanced_members(d)["values"]["minimum_transverse_force_per_device_kn"] == 10
    d["device_count"] = 0
    with pytest.raises(ValueError):
        run_advanced_members(d)
    d["device_count"] = 1
    d["side_by_side_i_sections_or_channels_verified"] = False
    with pytest.raises(ValueError):
        run_advanced_members(d)


def test_angle_eccentricity_minimum_moment_only():
    d = {
        "operation": "angle_eccentricity",
        "arrangement": "same_side",
        "compression_centroid_offset_mm": 20,
        "tension_centroid_offset_mm": 25,
        "leg_thickness_mm": 10,
        "axial_action_kn": 100,
        "rational_analysis_moment_knm": 1,
    }
    out = run_advanced_members(d)
    assert out["values"]["eccentricity_mm"] == 15
    assert out["values"]["design_moment_knm"] == 1.5
    d["arrangement"] = "opposite_sides"
    assert run_advanced_members(d)["values"]["minimum_design_moment_knm"] == 4.5
    assert out["full_standard_compliance"] is False


def test_clause_8_4_6_rational_moment_alternative_has_no_ne_floor():
    common = {
        "operation": "angle_eccentricity",
        "arrangement": "same_side",
        "compression_centroid_offset_mm": 20,
        "tension_centroid_offset_mm": 25,
        "leg_thickness_mm": 10,
        "axial_action_kn": 100,
    }
    rational = run_advanced_members(
        {
            **common,
            "moment_method": "rational_analysis",
            "rational_analysis_moment_knm": 0.5,
        }
    )
    assert rational["values"]["minimum_design_moment_knm"] == 1.5
    assert rational["values"]["design_moment_knm"] == 0.5

    minimum = run_advanced_members({**common, "moment_method": "minimum_eccentricity"})
    assert minimum["values"]["rational_analysis_moment_knm"] is None
    assert minimum["values"]["design_moment_knm"] == 1.5

    conservative = run_advanced_members(
        {
            **common,
            "moment_method": "conservative_max",
            "rational_analysis_moment_knm": 2.0,
        }
    )
    assert conservative["values"]["design_moment_knm"] == 2.0


def angle_section_bending_inputs(**updates):
    return {
        "operation": "angle_section_bending_capacity",
        "section_capacity_knm": 100,
        "iy_mm4": 50_000_000,
        "torsion_constant_mm4": 200_000,
        "effective_length_mm": 15_000,
        "moment_factor": 1,
        "moment_factor_verified": True,
        "section_properties_verified": True,
        "angle_section_verified": True,
        "constant_cross_section_verified": True,
        "segment_without_full_lateral_restraint_verified": True,
        "both_ends_restrained_verified": True,
        **updates,
    }


def test_clause_5_6_1_3_angle_bending_uses_iw_zero():
    out = run_advanced_members(angle_section_bending_inputs())
    values = out["values"]
    assert values["warping_constant_used_mm6"] == 0
    assert values["reference_buckling_moment_knm"] == pytest.approx(83.77580409572782)
    assert values["slenderness_reduction_alpha_s"] == pytest.approx(0.5459194274720188)
    assert values["nominal_member_moment_capacity_mb_knm"] == pytest.approx(54.591942747201884)
    assert out["clauses"][-1] == "5.6.1.3"
    assert out["checks"] == []


def test_clause_5_6_1_3_angle_bending_caps_capacity_at_ms():
    values = run_advanced_members(
        angle_section_bending_inputs(section_capacity_knm=20, moment_factor=2.5)
    )["values"]
    assert values["nominal_member_moment_capacity_mb_knm"] == 20


def test_clause_5_6_1_3_requires_restraint_conditions_at_both_ends():
    with pytest.raises(ValueError):
        run_advanced_members(angle_section_bending_inputs(both_ends_restrained_verified=False))


def hollow_section_bending_inputs(**updates):
    return {
        "operation": "hollow_section_bending_capacity",
        "section_type": "rhs",
        "section_capacity_knm": 100,
        "iy_mm4": 50_000_000,
        "torsion_constant_mm4": 200_000,
        "effective_length_mm": 15_000,
        "moment_factor": 1,
        "action_knm": 45,
        "hollow_section_applicability_verified": True,
        "section_properties_verified": True,
        "section_capacity_verified": True,
        "constant_cross_section_verified": True,
        "effective_length_verified": True,
        "moment_factor_verified": True,
        "segment_without_full_lateral_restraint_verified": True,
        "both_ends_restrained_verified": True,
        **updates,
    }


@pytest.mark.parametrize("section_type", ["rhs", "shs"])
def test_clause_5_6_1_4_hollow_section_bending_uses_iw_zero_and_checks_action(section_type):
    out = run_advanced_members(hollow_section_bending_inputs(section_type=section_type))
    values = out["values"]
    assert values["section_type"] == section_type
    assert values["warping_constant_used_mm6"] == 0
    assert values["reference_buckling_moment_knm"] == pytest.approx(83.77580409572782)
    assert values["slenderness_reduction_alpha_s"] == pytest.approx(0.5459194274720188)
    assert values["nominal_member_moment_capacity_mb_knm"] == pytest.approx(54.591942747201884)
    assert out["clauses"] == ["5.6.1.1(a)(1)", "5.6.1.1(a)(2)", "5.6.1.1(a)(3)", "5.6.1.4"]
    assert out["checks"][0]["design_capacity"] == pytest.approx(49.1327484724817)
    assert out["checks"][0]["satisfied"]
    assert out["full_standard_compliance"] is False


def test_clause_5_6_1_4_caps_member_capacity_at_section_capacity():
    out = run_advanced_members(
        hollow_section_bending_inputs(section_capacity_knm=20, moment_factor=2.5, action_knm=18)
    )
    assert out["values"]["nominal_member_moment_capacity_mb_knm"] == 20
    assert out["checks"][0]["satisfied"]


def test_clause_5_6_1_4_rejects_action_above_design_capacity():
    out = run_advanced_members(hollow_section_bending_inputs(action_knm=50))
    assert out["checks"][0]["design_capacity"] == pytest.approx(49.1327484724817)
    assert not out["checks"][0]["satisfied"]
    assert not out["checked_conditions_satisfied"]


@pytest.mark.parametrize(
    "changes",
    [
        {"hollow_section_applicability_verified": False},
        {"section_properties_verified": False},
        {"section_capacity_verified": False},
        {"constant_cross_section_verified": False},
        {"effective_length_verified": False},
        {"moment_factor_verified": False},
        {"segment_without_full_lateral_restraint_verified": False},
        {"both_ends_restrained_verified": False},
        {"section_type": "chs"},
        {"section_type": "i_section"},
    ],
)
def test_clause_5_6_1_4_requires_verified_hollow_section_scope(changes):
    with pytest.raises(ValueError):
        run_advanced_members(hollow_section_bending_inputs(**changes))


def equal_angle_compression_inputs(**updates):
    return {
        "operation": "angle_compression_capacity",
        "gross_area_mm2": 2000,
        "net_area_mm2": 2000,
        "effective_area_mm2": 2000,
        "yield_strength_mpa": 250,
        "member_length_mm": 1500,
        "radius_about_loaded_leg_h_axis_mm": 10,
        "section_properties_verified": True,
        "figure_8_4_6_connection_and_loading_verified": True,
        "loaded_leg_h_axis_orientation_verified": True,
        **updates,
    }


def test_clause_8_4_6_angle_nch_uses_table_a_constant_for_kf_one():
    out = run_advanced_members(equal_angle_compression_inputs())
    values = out["values"]
    assert values["form_factor_kf"] == 1
    assert values["section_constant_alpha_b"] == 0.5
    assert values["effective_length_mm"] == 1500
    assert values["modified_member_slenderness_lambda_n"] == pytest.approx(150)
    assert values["nominal_section_capacity_ns_kn"] == 500
    assert values["nominal_member_capacity_nch_kn"] == pytest.approx(136.5214318742263)
    assert out["checks"] == []


def test_clause_8_4_6_angle_nch_uses_table_b_other_section_constant_for_kf_below_one():
    out = run_advanced_members(
        equal_angle_compression_inputs(
            net_area_mm2=1800,
            effective_area_mm2=1600,
            yield_strength_mpa=350,
            member_length_mm=5000,
            radius_about_loaded_leg_h_axis_mm=15,
        )
    )
    values = out["values"]
    assert values["form_factor_kf"] == pytest.approx(0.8)
    assert values["section_constant_alpha_b"] == 1
    assert values["nominal_section_capacity_ns_kn"] == pytest.approx(504)
    assert values["nominal_member_capacity_nch_kn"] == pytest.approx(29.516096338384898)
    assert out["checks"] == []


def test_clause_8_4_6_angle_compression_rejects_inconsistent_areas():
    with pytest.raises(ValueError, match="areas must not exceed"):
        run_advanced_members(equal_angle_compression_inputs(net_area_mm2=2001))


def equal_angle_capacity_inputs(**updates):
    return {
        "operation": "angle_bending_capacity",
        "member_length_mm": 5250,
        "angle_thickness_mm": 10,
        "angle_leg_a_width_mm": 100,
        "angle_leg_b_width_mm": 100,
        "yield_strength_mpa": 250,
        "beta_m": 0,
        "moment_gradient_factor_verified": True,
        "section_capacity_knm": 20,
        "section_properties_verified": True,
        "figure_8_4_6_connection_and_loading_verified": True,
        "without_full_lateral_support_verified": True,
        "moment_factor": 1,
        "moment_factor_verified": True,
        **updates,
    }


def test_clause_8_4_6_equal_leg_limit_is_inclusive_and_uses_msx():
    inputs = equal_angle_capacity_inputs(member_length_mm=2100)
    inputs.pop("moment_factor")
    inputs.pop("moment_factor_verified")
    out = run_advanced_members(inputs)
    values = out["values"]
    assert values["member_slenderness_l_over_t"] == 210
    assert values["equal_leg_slenderness_limit_l_over_t"] == 210
    assert values["equal_leg_shortcut_used"]
    assert values["reference_buckling_moment_mo_knm"] is None
    assert values["member_moment_capacity_mbx_knm"] == 20
    assert out["clauses"] == ["8.4.6", "5.2"]


def test_clause_8_4_6_other_equal_leg_route_uses_clause_5_6_reduction():
    values = run_advanced_members(equal_angle_capacity_inputs())["values"]
    assert not values["equal_leg_shortcut_used"]
    assert values["reference_buckling_moment_mo_knm"] == pytest.approx(20)
    assert values["slenderness_reduction_alpha_s"] == pytest.approx(0.6)
    assert values["member_moment_capacity_mbx_knm"] == pytest.approx(12)


def test_clause_8_4_6_reduced_capacity_caps_at_msx_and_scales_for_fy():
    capped = run_advanced_members(equal_angle_capacity_inputs(moment_factor=2.5))["values"]
    assert capped["member_moment_capacity_mbx_knm"] == 20

    scaled = run_advanced_members(
        equal_angle_capacity_inputs(
            member_length_mm=5000,
            yield_strength_mpa=350,
        )
    )["values"]
    assert scaled["reference_buckling_moment_mo_knm"] == pytest.approx(15)
    assert scaled["slenderness_reduction_alpha_s"] == pytest.approx(0.5114877048604001)
    assert scaled["member_moment_capacity_mbx_knm"] == pytest.approx(10.229754097208001)


def test_clause_8_4_6_rejects_unequal_legs_and_requires_factor_outside_limit():
    with pytest.raises(ValueError, match="equal-leg"):
        run_advanced_members(equal_angle_capacity_inputs(angle_leg_b_width_mm=99))

    inputs = equal_angle_capacity_inputs()
    inputs.pop("moment_factor")
    inputs.pop("moment_factor_verified")
    with pytest.raises(ValueError, match="moment_factor"):
        run_advanced_members(inputs)


def angle_combined_interaction_inputs(**updates):
    return {
        "operation": "angle_combined_interaction",
        "design_compression_kn": 90,
        "design_moment_about_h_knm": 9,
        "nominal_member_compression_nch_kn": 200,
        "nominal_member_bending_mbx_knm": 40,
        "angle_between_x_and_h_deg": 60,
        "clause_8_3_interaction_satisfied": True,
        "single_angle_web_compression_member_in_truss_verified": True,
        "end_connection_at_least_two_bolts_or_welded_verified": True,
        "loaded_through_one_leg_figure_8_4_6_verified": True,
        "angle_axis_orientation_verified": True,
        "nominal_nch_mbx_calculations_verified": True,
        **updates,
    }


def test_clause_8_4_6_amendment_interaction_hand_arithmetic_and_boundary():
    out = run_advanced_members(angle_combined_interaction_inputs())
    values = out["values"]
    assert values["amendment_applied"] == "AS 4100:2020 Amd 1:2021"
    assert values["capacity_factor_phi"] == 0.9
    assert values["axial_utilisation"] == pytest.approx(0.5)
    assert values["cos_alpha"] == pytest.approx(0.5)
    assert values["moment_utilisation"] == pytest.approx(0.5)
    assert values["interaction_utilisation"] == pytest.approx(1.0)
    assert out["checked_conditions_satisfied"]
    assert [check["clause"] for check in out["checks"]] == ["8.3", "8.4.6 (Amd 1:2021)"]

    over = run_advanced_members(angle_combined_interaction_inputs(design_moment_about_h_knm=9.001))
    assert not over["checked_conditions_satisfied"]
    assert not over["checks"][1]["satisfied"]

    failed_section = run_advanced_members(
        angle_combined_interaction_inputs(clause_8_3_interaction_satisfied=False)
    )
    assert not failed_section["checked_conditions_satisfied"]
    assert not failed_section["checks"][0]["satisfied"]


@pytest.mark.parametrize("alpha", [-0.1, 90, 90.1])
def test_clause_8_4_6_amendment_rejects_invalid_angle(alpha):
    with pytest.raises(ValueError):
        run_advanced_members(angle_combined_interaction_inputs(angle_between_x_and_h_deg=alpha))


def test_external_prerequisite_cannot_be_false():
    d = plastic()
    d["compact_doubly_symmetric_i_verified"] = False
    with pytest.raises(ValueError):
        run_advanced_members(d)
