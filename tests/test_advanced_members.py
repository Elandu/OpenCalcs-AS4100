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
