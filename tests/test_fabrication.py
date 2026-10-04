import pytest

from opencalcs_as4100.fabrication import run_fabrication


def plate(*, thickness=4, clearance=10, product=True, coverage=True, material=True):
    return {
        "type": "plate",
        "thickness_mm": thickness,
        "minimum_edge_clearance_mm": clearance,
        "coverage_geometry_verified": coverage,
        "product_verified": product,
        "material_as_nzs_3678_verified": material,
    }


def side(bears=False, washer=None):
    return {"bears_on_holed_ply": bears, "washer": washer}


def slot(hole_type="short_slot", **changes):
    return {
        "check_type": "bolt_hole",
        "hole_type": hole_type,
        "bolt_diameter_mm": 20,
        "hole_width_mm": 22,
        "hole_length_mm": 30 if hole_type == "short_slot" else 50,
        "not_base_plate_anchor_hole_verified": True,
        "connection_type": "friction_type",
        "subject_to_shear": True,
        "head_side": side(True, {"type": "hardened", "product_verified": True}),
        "nut_side": side(False),
        **({"alternate_plies_verified": True} if hole_type == "long_slot" else {}),
        **changes,
    }


def test_standard_hole_size_at_24_mm_boundary():
    at_24 = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "standard",
            "bolt_diameter_mm": 24,
            "hole_diameter_mm": 26,
        }
    )
    assert at_24["checked_conditions_satisfied"]
    assert at_24["values"]["maximum_hole_diameter_mm"] == 26

    above_24 = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "standard",
            "bolt_diameter_mm": 25,
            "hole_diameter_mm": 28,
        }
    )
    assert above_24["checked_conditions_satisfied"]
    assert above_24["values"]["maximum_hole_diameter_mm"] == 28
    too_large = run_fabrication(
        {
            "check_type": "bolt_hole",
            "hole_type": "standard",
            "bolt_diameter_mm": 25,
            "hole_diameter_mm": 28.001,
        }
    )
    assert not too_large["checked_conditions_satisfied"]


def test_base_plate_anchor_hole_requires_washer_at_three_mm_oversize():
    d = {
        "check_type": "bolt_hole",
        "hole_type": "base_plate_anchor",
        "bolt_diameter_mm": 14,
        "hole_diameter_mm": 20,
        "special_nut_washer": plate(thickness=4, clearance=10),
    }
    passed = run_fabrication(d)
    assert passed["checked_conditions_satisfied"]
    assert passed["values"]["special_nut_washer_required"]

    d["special_nut_washer"]["minimum_edge_clearance_mm"] = 9.99
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["special_nut_washer"] = plate(thickness=3.999, clearance=10)
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["special_nut_washer"] = None
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_base_plate_anchor_hole_maximum_and_washer_threshold():
    d = {
        "check_type": "bolt_hole",
        "hole_type": "base_plate_anchor",
        "bolt_diameter_mm": 14,
        "hole_diameter_mm": 16.999,
    }
    result = run_fabrication(d)
    assert result["checked_conditions_satisfied"]
    assert not result["values"]["special_nut_washer_required"]
    d["hole_diameter_mm"] = 20.001
    assert not run_fabrication(d)["checked_conditions_satisfied"]

    d["hole_diameter_mm"] = 17
    d["special_nut_washer"] = plate(clearance=8.5)
    result = run_fabrication(d)
    assert result["checked_conditions_satisfied"]
    assert result["values"]["special_nut_washer_required"]


def test_oversize_hole_maximum_and_bearing_surface_washers():
    d = {
        "check_type": "bolt_hole",
        "hole_type": "oversize",
        "bolt_diameter_mm": 20,
        "hole_diameter_mm": 28,
        "not_base_plate_anchor_hole_verified": True,
        "connection_type": "bearing_type",
        "subject_to_shear": True,
        "head_side": side(True, {"type": "hardened", "product_verified": True}),
        "nut_side": side(True, plate(clearance=14)),
    }
    assert run_fabrication(d)["checked_conditions_satisfied"]
    d["nut_side"]["washer"]["minimum_edge_clearance_mm"] = 13.99
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["nut_side"]["washer"]["minimum_edge_clearance_mm"] = 14
    d["hole_diameter_mm"] = 28.001
    assert not run_fabrication(d)["checked_conditions_satisfied"]

    d.update(
        bolt_diameter_mm=40,
        hole_diameter_mm=50,
        head_side=side(False),
        nut_side=side(False),
    )
    result = run_fabrication(d)
    assert result["checked_conditions_satisfied"]
    assert result["values"]["maximum_hole_diameter_mm"] == 50


def test_oversize_hole_requires_non_base_plate_applicability():
    d = {
        "check_type": "bolt_hole",
        "hole_type": "oversize",
        "bolt_diameter_mm": 20,
        "hole_diameter_mm": 28,
        "not_base_plate_anchor_hole_verified": False,
        "connection_type": "friction_type",
        "subject_to_shear": False,
        "head_side": side(False),
        "nut_side": side(False),
    }
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_short_slot_size_and_friction_shear_has_no_direction_restriction():
    result = run_fabrication(slot())
    assert result["checked_conditions_satisfied"]
    assert result["values"]["maximum_hole_width_mm"] == 22
    assert result["values"]["maximum_hole_length_mm"] == 30

    too_wide = slot(hole_width_mm=22.001)
    assert not run_fabrication(too_wide)["checked_conditions_satisfied"]
    too_long = slot(hole_length_mm=30.001)
    assert not run_fabrication(too_long)["checked_conditions_satisfied"]

    larger_bolt = slot(
        bolt_diameter_mm=40,
        hole_width_mm=43,
        hole_length_mm=53.2,
    )
    result = run_fabrication(larger_bolt)
    assert result["checked_conditions_satisfied"]
    assert result["values"]["maximum_hole_length_mm"] == pytest.approx(53.2)


def test_short_slot_bearing_shear_conditions_are_required_and_checked():
    d = slot(
        connection_type="bearing_type",
        eccentricity_absent_verified=True,
        uniform_bolt_bearing_verified=True,
        slot_normal_to_action_verified=True,
    )
    assert run_fabrication(d)["checked_conditions_satisfied"]
    d["slot_normal_to_action_verified"] = False
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    del d["slot_normal_to_action_verified"]
    with pytest.raises(ValueError):
        run_fabrication(d)


def test_long_slot_limits_alternate_plies_and_eight_mm_plate_washer():
    d = slot(
        "long_slot",
        head_side=side(True, plate(thickness=8, clearance=11)),
    )
    result = run_fabrication(d)
    assert result["checked_conditions_satisfied"]
    assert result["values"]["maximum_hole_length_mm"] == 50

    d["alternate_plies_verified"] = False
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["alternate_plies_verified"] = True
    d["head_side"]["washer"]["thickness_mm"] = 7.999
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["head_side"]["washer"]["thickness_mm"] = 8
    d["hole_length_mm"] = 50.001
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_long_slot_bearing_shear_requires_unbiased_uniform_normal_loading():
    d = slot(
        "long_slot",
        connection_type="bearing_type",
        head_side=side(True, plate(thickness=8, clearance=11)),
        eccentricity_absent_verified=True,
        uniform_bolt_bearing_verified=True,
        slot_normal_to_action_verified=True,
    )
    assert run_fabrication(d)["checked_conditions_satisfied"]
    d["uniform_bolt_bearing_verified"] = False
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_plate_washer_requires_coverage_and_as_nzs_3678_evidence():
    d = slot(head_side=side(True, plate(clearance=11, coverage=False)))
    assert not run_fabrication(d)["checked_conditions_satisfied"]
    d["head_side"]["washer"]["coverage_geometry_verified"] = True
    d["head_side"]["washer"]["material_as_nzs_3678_verified"] = False
    assert not run_fabrication(d)["checked_conditions_satisfied"]


def test_standard_hole_rejects_unexpected_fields():
    with pytest.raises(ValueError):
        run_fabrication(
            {
                "check_type": "bolt_hole",
                "hole_type": "standard",
                "bolt_diameter_mm": 20,
                "hole_diameter_mm": 22,
                "unexpected": True,
            }
        )
