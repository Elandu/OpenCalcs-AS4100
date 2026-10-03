import pytest

from opencalcs_as4100.advanced_members import run_advanced_members


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


@pytest.mark.parametrize(
    "ends,factor,expected",
    [
        ("both_restrained", 1, 60),
        ("both_restrained", 2, 77.4901573278),
        ("one_unrestrained", 1, 60),
    ],
)
def test_external_lateral_buckling(ends, factor, expected):
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


def varying_section_bending(design_method="critical_section_reduced_reference", **updates):
    inputs = {
        "operation": "varying_section_bending",
        "design_method": design_method,
        "section_capacity_knm": 120,
        "reference_buckling_moment_knm": 100,
        "reference_buckling_moment_verified": True,
        "moment_factor": 1.3,
        "moment_factor_verified": True,
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
    out = run_advanced_members(
        {
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
    )
    assert out["values"]["section_interaction"] == pytest.approx(1.1)
    assert not out["checked_conditions_satisfied"]


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
    assert run_advanced_members(d)["values"]["connection_longitudinal_shear_kn"] is None


def test_pin_member_net_area_and_thickness():
    d = {
        "operation": "pin_tension_member",
        "thickness_mm": 10,
        "hole_to_edge_distance_mm": 40,
        "internal_nut_clamped_ply": False,
        "net_area_beyond_hole_mm2": 1000,
        "net_area_perpendicular_mm2": 1330,
        "required_member_net_area_mm2": 1000,
        "pin_plates_distribute_load_without_eccentricity_verified": True,
    }
    assert run_advanced_members(d)["checked_conditions_satisfied"]
    d["net_area_perpendicular_mm2"] = 1329
    assert not run_advanced_members(d)["checked_conditions_satisfied"]


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


def test_external_prerequisite_cannot_be_false():
    d = plastic()
    d["compact_doubly_symmetric_i_verified"] = False
    with pytest.raises(ValueError):
        run_advanced_members(d)
