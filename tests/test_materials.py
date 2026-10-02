# SPDX-License-Identifier: AGPL-3.0-only
import pytest

from opencalcs_as4100.materials import run_materials


def strength(product, form, grade, thickness):
    return run_materials(
        {
            "operation": "tabulated_strength",
            "product_standard": product,
            "form": form,
            "grade": grade,
            "material_thickness_mm": thickness,
        }
    )["values"]


@pytest.mark.parametrize(
    "product,form,grade,t,fy,fu",
    [
        ("AS/NZS 1163", "hollow_sections", "C250", 40, 250, 320),
        ("AS/NZS 1594", "plate_strip_floorplate", "HA400", 80, 380, 460),
        ("AS/NZS 1594", "plate_strip", "XF500", 8, 480, 570),
        ("AS/NZS 1594", "plate_strip", "XF400", 8, 380, 460),
        ("AS/NZS 3678", "plate_floorplate", "450", 20, 450, 520),
        ("AS/NZS 3678", "plate_floorplate", "450", 20.001, 420, 500),
        ("AS/NZS 3678", "plate_floorplate", "350", 80, 340, 450),
        ("AS/NZS 3678", "plate_floorplate", "350", 80.001, 330, 450),
        ("AS/NZS 3678", "plate_floorplate", "300", 12, 310, 430),
        ("AS/NZS 3678", "plate_floorplate", "300", 12.001, 300, 430),
        ("AS/NZS 3678", "plate_floorplate", "250", 80, 240, 410),
        ("AS/NZS 3679.1", "flats_sections", "350", 11, 360, 480),
        ("AS/NZS 3679.1", "flats_sections", "350", 11.001, 340, 480),
        ("AS/NZS 3679.1", "flats_sections", "350", 40, 330, 480),
        ("AS/NZS 3679.2", "welded_i_sections", "350", 16, 350, 450),
        ("AS/NZS 3679.1", "hexagons_rounds_squares", "300", 100, 280, 440),
        ("AS 3597", "plate", "700", 5, 650, 750),
        ("AS 3597", "plate", "700", 5.001, 690, 790),
        ("AS 3597", "plate", "700", 65.001, 620, 720),
    ],
)
def test_table_2_1_product_grade_and_thickness(product, form, grade, t, fy, fu):
    assert strength(product, form, grade, t) == {
        "yield_strength_mpa": fy,
        "tensile_strength_mpa": fu,
    }


@pytest.mark.parametrize(
    "product,form,grade,t",
    [
        ("AS/NZS 3678", "plate_floorplate", "450", 50.001),
        ("AS/NZS 3678", "plate_floorplate", "350", 150.001),
        ("AS 3597", "plate", "600", 110.001),
    ],
)
def test_table_2_1_rejects_out_of_range_thickness(product, form, grade, t):
    with pytest.raises(ValueError, match="No unique Table 2.1"):
        strength(product, form, grade, t)


def unidentified_steel(**overrides):
    inputs = {
        "operation": "unidentified_steel",
        "design_yield_strength_mpa": 170,
        "design_tensile_strength_mpa": 300,
        "surface_imperfections_verified": True,
        "properties_and_weldability_verified": True,
        "full_test_to_as1391_verified": False,
    }
    inputs.update(overrides)
    return run_materials(inputs)


def test_unidentified_steel_clause_2_2_3_strength_limits_at_boundary():
    result = unidentified_steel()
    assert result["clauses"] == ["2.2.3"]
    assert result["checked_conditions_satisfied"]
    assert [check["limit_mpa"] for check in result["checks"]] == [170, 300]
    assert all(check["satisfied"] for check in result["checks"])
    assert result["full_standard_compliance"] is False


@pytest.mark.parametrize(
    "field,value,check_index",
    [("design_yield_strength_mpa", 170.001, 0), ("design_tensile_strength_mpa", 300.001, 1)],
)
def test_unidentified_steel_exceeding_either_limit_fails_without_reducing_input(
    field, value, check_index
):
    result = unidentified_steel(**{field: value})
    assert result["values"][field] == value
    assert not result["checks"][check_index]["satisfied"]
    assert not result["checked_conditions_satisfied"]


def test_full_as1391_test_route_uses_recorded_strengths():
    result = unidentified_steel(
        design_yield_strength_mpa=250,
        design_tensile_strength_mpa=400,
        full_test_to_as1391_verified=True,
        test_report_reference="TEST-4100-01",
    )
    assert result["checked_conditions_satisfied"]
    assert result["values"]["design_yield_strength_mpa"] == 250
    assert result["values"]["design_tensile_strength_mpa"] == 400
    assert result["values"]["test_report_reference"] == "TEST-4100-01"
    assert [check["limit_mpa"] for check in result["checks"]] == [None, None]


def test_unidentified_steel_requires_prerequisite_attestations_and_test_reference():
    with pytest.raises(ValueError):
        unidentified_steel(surface_imperfections_verified=False)
    with pytest.raises(ValueError):
        unidentified_steel(properties_and_weldability_verified=False)
    with pytest.raises(ValueError):
        unidentified_steel(full_test_to_as1391_verified=True)
    with pytest.raises(ValueError):
        unidentified_steel(full_test_to_as1391_verified=True, test_report_reference="")


def test_clause_2_2_4_design_properties_match_standard_values():
    result = run_materials({"operation": "design_properties"})
    assert result["clauses"] == ["2.2.4"]
    assert result["values"] == {
        "elastic_modulus_mpa": 200000,
        "shear_modulus_mpa": 80000,
        "poisson_ratio": 0.25,
        "thermal_expansion_per_c": 11.7e-6,
    }


def through_thickness(**overrides):
    inputs = {
        "operation": "through_thickness_deformation",
        "product_standard": "AS/NZS 3678",
        "material_thickness_mm": 20,
        "required_design_z_value": 21,
        "appendix_m_assessment_verified": True,
        "appendix_m_assessment_reference": "WELD-DESIGN-4100-01",
        "available_z_quality_class": "Z25",
        "material_certificate_verified": True,
        "material_certificate_reference": "MILL-CERT-4100-01",
    }
    inputs.update(overrides)
    return run_materials(inputs)


@pytest.mark.parametrize(
    "z_ed,required_class,reduction_area,available_class",
    [
        (10, None, None, None),
        (11, "Z15", 15, "Z15"),
        (20, "Z15", 15, "Z15"),
        (21, "Z25", 25, "Z25"),
        (30, "Z25", 25, "Z25"),
        (31, "Z35", 35, "Z35"),
    ],
)
def test_clause_2_2_5_z_quality_thresholds(z_ed, required_class, reduction_area, available_class):
    result = through_thickness(
        required_design_z_value=z_ed,
        available_z_quality_class=available_class,
        material_certificate_verified=available_class is not None,
        material_certificate_reference="MILL-CERT-4100-01" if available_class else None,
    )
    check = result["checks"][0]
    assert result["clauses"] == ["2.2.5"]
    assert result["values"]["required_z_quality_class"] == required_class
    assert check["required_reduction_of_area_percent"] == reduction_area
    assert check["satisfied"]


def test_clause_2_2_5_thickness_exemption_does_not_require_appendix_m_or_z_quality():
    result = run_materials(
        {
            "operation": "through_thickness_deformation",
            "product_standard": "AS/NZS 3678",
            "material_thickness_mm": 16,
            "available_z_quality_class": None,
            "material_certificate_verified": False,
            "material_certificate_reference": None,
        }
    )
    assert result["checks"][0]["exemption_applies"]
    assert result["checked_conditions_satisfied"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"required_design_z_value": 21, "available_z_quality_class": "Z15"},
        {"required_design_z_value": 21, "available_z_quality_class": None},
        {"required_design_z_value": 21, "material_certificate_verified": False},
        {
            "required_design_z_value": 21,
            "appendix_m_assessment_verified": False,
            "appendix_m_assessment_reference": None,
        },
        {"required_design_z_value": None},
    ],
)
def test_clause_2_2_5_missing_or_insufficient_design_evidence_fails(overrides):
    result = through_thickness(**overrides)
    assert not result["checked_conditions_satisfied"]
    assert not result["checks"][0]["satisfied"]


def test_clause_2_2_5_rejects_zed_outside_appendix_m_table_bounds():
    with pytest.raises(ValueError):
        through_thickness(required_design_z_value=44)
