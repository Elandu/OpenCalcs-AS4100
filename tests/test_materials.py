# SPDX-License-Identifier: AGPL-3.0-only
import pytest

from engcalcs_as4100.materials import run_materials


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


def test_clause_2_4_steel_casting_conformity_is_traceable_but_not_authenticated():
    result = run_materials(
        {
            "operation": "steel_casting_conformity",
            "casting_grade": "Supplier grade record",
            "as_2074_conformity_verified": True,
            "conformity_evidence_reference": "CASTING-CERTIFICATE-01",
        }
    )
    assert result["clauses"] == ["2.4"]
    assert result["values"] == {
        "casting_grade": "Supplier grade record",
        "product_standard": "AS 2074",
        "as_2074_conformity_verified": True,
        "conformity_evidence_reference": "CASTING-CERTIFICATE-01",
    }
    assert result["checks"][0]["satisfied"]
    assert result["checked_conditions_satisfied"]
    assert result["full_standard_compliance"] is False
    assert any("does not authenticate" in warning for warning in result["warnings"])
    assert any("does not calculate" in warning for warning in result["warnings"])


def test_clause_2_4_unverified_casting_conformity_fails_and_needs_no_reference():
    result = run_materials(
        {
            "operation": "steel_casting_conformity",
            "casting_grade": "Supplier grade record",
            "as_2074_conformity_verified": False,
            "conformity_evidence_reference": None,
        }
    )
    assert not result["checks"][0]["satisfied"]
    assert not result["checked_conditions_satisfied"]


def test_clause_2_4_verified_casting_requires_evidence_reference_and_grade():
    base = {
        "operation": "steel_casting_conformity",
        "casting_grade": "Supplier grade record",
        "as_2074_conformity_verified": True,
        "conformity_evidence_reference": None,
    }
    with pytest.raises(ValueError, match="requires an evidence reference"):
        run_materials(base)
    with pytest.raises(ValueError, match="grade must not be blank"):
        run_materials({**base, "casting_grade": "  ", "conformity_evidence_reference": "CERT-01"})


def test_clause_2_3_1_fastener_product_standard_and_certificate_are_traceable():
    result = run_materials(
        {
            "operation": "fastener_product_conformity",
            "item_or_assembly_identifier": "BOLT-SET-01",
            "component_type": "high_strength_bolting_assembly",
            "product_standard": "AS/NZS 1252.1",
            "product_standard_applicability_verified": True,
            "conformity_certificate_verified": True,
            "conformity_evidence_reference": "BOLT-CERTIFICATE-01",
        }
    )
    assert result["clauses"] == ["2.3.1"]
    assert result["values"]["item_or_assembly_identifier"] == "BOLT-SET-01"
    assert result["checks"][0]["standard_listed_for_component"]
    assert result["checks"][0]["satisfied"]
    assert result["checked_conditions_satisfied"]
    assert result["full_standard_compliance"] is False
    assert any("does not authenticate" in warning for warning in result["warnings"])
    assert any("laboratory accreditation" in warning for warning in result["warnings"])


def test_clause_2_3_1_unlisted_component_standard_fails_declared_check():
    result = run_materials(
        {
            "operation": "fastener_product_conformity",
            "item_or_assembly_identifier": "NUT-01",
            "component_type": "nut",
            "product_standard": "AS 1110",
            "product_standard_applicability_verified": True,
            "conformity_certificate_verified": True,
            "conformity_evidence_reference": "NUT-CERTIFICATE-01",
        }
    )
    assert not result["checks"][0]["standard_listed_for_component"]
    assert not result["checks"][0]["satisfied"]
    assert not result["checked_conditions_satisfied"]


def test_clause_2_3_1_tower_bolting_standard_records_project_suitability_assessment():
    result = run_materials(
        {
            "operation": "fastener_product_conformity",
            "item_or_assembly_identifier": "TOWER-BOLT-01",
            "component_type": "galvanized_tower_bolting_assembly",
            "product_standard": "AS/NZS 1559",
            "product_standard_applicability_verified": False,
            "conformity_certificate_verified": True,
            "conformity_evidence_reference": "TOWER-CERTIFICATE-01",
        }
    )
    assert result["checks"][0]["standard_listed_for_component"]
    assert not result["checks"][0]["satisfied"]
    assert any("specific to tower construction" in warning for warning in result["warnings"])


def test_clause_2_3_1_verified_fastener_certificate_requires_identifier_and_reference():
    base = {
        "operation": "fastener_product_conformity",
        "item_or_assembly_identifier": "BOLT-SET-01",
        "component_type": "high_strength_bolting_assembly",
        "product_standard": "AS/NZS 1252.1",
        "product_standard_applicability_verified": True,
        "conformity_certificate_verified": True,
        "conformity_evidence_reference": None,
    }
    with pytest.raises(ValueError, match="requires an evidence reference"):
        run_materials(base)
    with pytest.raises(ValueError, match="identifier must not be blank"):
        run_materials(
            {
                **base,
                "item_or_assembly_identifier": "  ",
                "conformity_certificate_verified": False,
            }
        )


def ancillary_conformity(**overrides):
    inputs = {
        "operation": "ancillary_conformity",
        "item_identifier": "ITEM-01",
        "application": "welding",
        "anchor_bolt_material_standard": None,
        "primary_requirement_verified": True,
        "primary_evidence_reference": "EVIDENCE-01",
        "secondary_requirement_verified": None,
        "secondary_evidence_reference": None,
    }
    inputs.update(overrides)
    return run_materials(inputs)


@pytest.mark.parametrize(
    "application,clause,standard",
    [
        ("welding", "2.3.3", "AS/NZS 5131"),
        ("welded_studs_prequalified", "2.3.4", "AS/NZS 1554.2"),
        ("explosive_fasteners", "2.3.5", "AS/NZS 1873"),
        ("mechanical_anchors", "2.3.7", "AS 5216"),
        ("chemical_anchors", "2.3.7", "AS 5216"),
    ],
)
def test_clause_2_3_3_to_2_3_7_fixed_standard_evidence_routes(application, clause, standard):
    result = ancillary_conformity(application=application)
    assert result["clauses"] == [clause]
    assert result["checks"][0]["product_standard"] == standard
    assert result["checks"][0]["satisfied"]
    assert result["checked_conditions_satisfied"]
    assert result["full_standard_compliance"] is False
    assert "does not authenticate" in result["warnings"][0]


def test_clause_2_3_4_non_prequalified_studs_require_iso_13918_collar_evidence():
    result = ancillary_conformity(
        application="welded_studs_non_prequalified",
        secondary_requirement_verified=True,
        secondary_evidence_reference="STUD-COLLAR-01",
    )
    assert result["clauses"] == ["2.3.4"]
    assert [check["product_standard"] for check in result["checks"]] == [
        "AS/NZS 1554.2",
        "ISO 13918",
    ]
    assert all(check["satisfied"] for check in result["checks"])


def test_clause_2_3_4_non_prequalified_studs_fail_without_verified_collar():
    result = ancillary_conformity(
        application="welded_studs_non_prequalified",
        secondary_requirement_verified=False,
    )
    assert result["checks"][0]["satisfied"]
    assert not result["checks"][1]["satisfied"]
    assert not result["checked_conditions_satisfied"]
    with pytest.raises(ValueError, match="requires a secondary requirement assessment"):
        ancillary_conformity(application="welded_studs_non_prequalified")


@pytest.mark.parametrize(
    "application,material_standard,standard_listed",
    [
        ("anchor_bolts_clause_2_3_1", "AS 1110", True),
        ("anchor_bolts_clause_2_3_1", "AS/NZS 3678", False),
        ("anchor_bolts_clause_2_2_1_steel_rod", "AS/NZS 3678", True),
        ("anchor_bolts_clause_2_2_1_steel_rod", "AS 1112", False),
    ],
)
def test_clause_2_3_6_anchor_bolt_material_routes(application, material_standard, standard_listed):
    overrides = {
        "application": application,
        "anchor_bolt_material_standard": material_standard,
    }
    if application == "anchor_bolts_clause_2_2_1_steel_rod":
        overrides.update(
            secondary_requirement_verified=True,
            secondary_evidence_reference="THREAD-CHECK-01",
        )
    result = ancillary_conformity(**overrides)
    assert result["clauses"] == ["2.3.6"]
    assert result["checks"][0]["standard_listed_for_route"] is standard_listed
    assert result["checks"][0]["satisfied"] is standard_listed
    if application == "anchor_bolts_clause_2_2_1_steel_rod":
        assert result["checks"][1]["product_standard"] == "AS 1275"
        assert result["checks"][1]["satisfied"]
        assert result["checked_conditions_satisfied"] is standard_listed


def test_clause_2_3_6_anchor_rod_threads_require_as_1275_evidence():
    result = ancillary_conformity(
        application="anchor_bolts_clause_2_2_1_steel_rod",
        anchor_bolt_material_standard="AS/NZS 3678",
        secondary_requirement_verified=False,
    )
    assert not result["checks"][1]["satisfied"]
    assert not result["checked_conditions_satisfied"]
    with pytest.raises(ValueError, match="requires a secondary requirement assessment"):
        ancillary_conformity(
            application="anchor_bolts_clause_2_2_1_steel_rod",
            anchor_bolt_material_standard="AS/NZS 3678",
        )


def test_ancillary_conformity_requires_references_and_rejects_inapplicable_route_data():
    with pytest.raises(ValueError, match="requires an evidence reference"):
        ancillary_conformity(primary_evidence_reference=None)
    with pytest.raises(ValueError, match="applies only to anchor-bolt applications"):
        ancillary_conformity(anchor_bolt_material_standard="AS 1110")
    with pytest.raises(ValueError, match="Verified secondary conformity requires an evidence"):
        ancillary_conformity(
            application="welded_studs_non_prequalified",
            secondary_requirement_verified=True,
        )


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


def appendix_m_through_thickness(**overrides):
    inputs = {
        "operation": "appendix_m_through_thickness_design",
        "product_standard": "AS/NZS 3678",
        "material_thickness_mm": 45,
        "effective_weld_depth_mm": 25,
        "table_m2_b_case": "multi_run_fillet",
        "low_strength_weld_material_verified": False,
        "low_strength_weld_material_reference": None,
        "remote_restraint": "high",
        "preheating_condition": "without_preheating",
        "compression_reduction_basis": "not_applicable",
        "effective_weld_depth_assessment_verified": True,
        "table_m2_weld_form_case_verified": True,
        "remote_restraint_classification_verified": True,
        "preheating_condition_verified": True,
        "compression_reduction_applicability_verified": True,
        "available_z_quality_class": "Z25",
        "material_certificate_verified": True,
        "material_certificate_reference": "MILL-CERT-4100-01",
    }
    inputs.update(overrides)
    return run_materials(inputs)


def test_appendix_m_table_m2_hand_benchmark_feeds_clause_2_2_5():
    result = appendix_m_through_thickness()
    values = result["values"]
    assert result["clauses"] == ["2.2.5", "3.8", "Appendix M.2", "Table M.2"]
    assert [values[name] for name in ("z_a", "z_b", "z_c_after_reduction", "z_d", "z_e")] == [
        9,
        0,
        10,
        5,
        0,
    ]
    assert values["required_design_z_value"] == 24
    assert values["required_z_quality_class"] == "Z25"
    assert values["required_reduction_of_area_percent"] == 25
    assert result["checks"][0]["clause"] == "2.2.5"
    assert result["checked_conditions_satisfied"]
    assert result["full_standard_compliance"] is False

    insufficient = appendix_m_through_thickness(available_z_quality_class="Z15")
    assert not insufficient["checks"][0]["class_sufficient"]
    assert not insufficient["checked_conditions_satisfied"]


@pytest.mark.parametrize(
    "depth,expected",
    [
        (7, 0),
        (7.001, 3),
        (10, 3),
        (10.001, 6),
        (20, 6),
        (20.001, 9),
        (30, 9),
        (30.001, 12),
        (40, 12),
        (40.001, 15),
        (60, 15),
    ],
)
def test_appendix_m_weld_depth_table_boundaries(depth, expected):
    values = appendix_m_through_thickness(
        effective_weld_depth_mm=depth,
        material_thickness_mm=10,
        remote_restraint="low",
    )["values"]
    assert values["z_a"] == expected


@pytest.mark.parametrize(
    "thickness,expected",
    [
        (10, 2),
        (10.001, 4),
        (20, 4),
        (20.001, 6),
        (30, 6),
        (30.001, 8),
        (40, 8),
        (40.001, 10),
        (50, 10),
        (50.001, 12),
        (60, 12),
        (60.001, 15),
        (100, 15),
    ],
)
def test_appendix_m_thickness_table_boundaries(thickness, expected):
    values = appendix_m_through_thickness(
        material_thickness_mm=thickness,
        effective_weld_depth_mm=7,
        remote_restraint="low",
    )["values"]
    assert values["z_c_before_reduction"] == expected


@pytest.mark.parametrize(
    "case,expected",
    [
        ("t_cruciform_or_corner_diagram_group", -25),
        ("corner_joint_diagram_group_1", -10),
        ("single_run_fillet_with_z_a_zero", -5),
        ("multi_run_fillet", 0),
        ("penetration_weld_with_shrinkage_reducing_sequence", 3),
        ("penetration_weld_without_shrinkage_reducing_sequence", 5),
        ("corner_joint_diagram_group_2", 8),
    ],
)
def test_appendix_m_weld_form_and_sequence_table_cases(case, expected):
    values = appendix_m_through_thickness(
        table_m2_b_case=case,
        material_thickness_mm=10,
        effective_weld_depth_mm=7,
        remote_restraint="low",
    )["values"]
    assert values["z_b"] == expected


def test_appendix_m_single_run_fillet_zb_case_requires_zero_za():
    valid = appendix_m_through_thickness(
        table_m2_b_case="single_run_fillet_with_z_a_zero",
        effective_weld_depth_mm=7,
        material_thickness_mm=10,
        remote_restraint="low",
    )
    assert valid["values"]["z_a"] == 0
    assert valid["values"]["z_b"] == -5
    assert valid["values"]["table_m2_b_case_eligibility_satisfied"]

    with pytest.raises(ValueError, match="single-run fillet case requires Za = 0"):
        appendix_m_through_thickness(
            table_m2_b_case="single_run_fillet_with_z_a_zero",
            effective_weld_depth_mm=25,
        )


def test_appendix_m_low_strength_butting_fillet_zb_requires_za_and_evidence():
    with pytest.raises(ValueError, match="Za > 1"):
        appendix_m_through_thickness(
            table_m2_b_case="fillet_welds_butting_low_strength_material",
            effective_weld_depth_mm=7,
            low_strength_weld_material_verified=True,
            low_strength_weld_material_reference="WELD-MATERIAL-CERT-01",
        )

    with pytest.raises(ValueError, match="verified weld-material evidence"):
        appendix_m_through_thickness(
            table_m2_b_case="fillet_welds_butting_low_strength_material",
            effective_weld_depth_mm=25,
        )

    allowed = appendix_m_through_thickness(
        table_m2_b_case="fillet_welds_butting_low_strength_material",
        effective_weld_depth_mm=25,
        low_strength_weld_material_verified=True,
        low_strength_weld_material_reference="WELD-MATERIAL-CERT-01",
        available_z_quality_class="Z15",
    )
    values = allowed["values"]
    assert values["z_a"] == 9
    assert values["z_b"] == -5
    assert values["required_design_z_value"] == 19
    assert values["required_z_quality_class"] == "Z15"
    assert allowed["checked_conditions_satisfied"]


def test_appendix_m_restraint_preheat_and_compression_reduction():
    restrained = appendix_m_through_thickness(remote_restraint="medium")
    assert restrained["values"]["z_d"] == 3
    preheated = appendix_m_through_thickness(preheating_condition="at_least_100_c")
    assert preheated["values"]["z_e"] == -8
    reduced = appendix_m_through_thickness(compression_reduction_basis="verified_applicable")
    assert reduced["values"]["z_c_before_reduction"] == 10
    assert reduced["values"]["z_c_after_reduction"] == 5
    assert reduced["values"]["required_design_z_value"] == 19
    assert reduced["values"]["required_z_quality_class"] == "Z15"

    reduced_top_thickness = appendix_m_through_thickness(
        material_thickness_mm=70,
        compression_reduction_basis="verified_applicable",
    )
    assert reduced_top_thickness["values"]["z_c_after_reduction"] == 7.5
    assert reduced_top_thickness["values"]["required_design_z_value"] == 21.5
    assert reduced_top_thickness["values"]["required_z_quality_class"] == "Z25"


def test_appendix_m_requires_verified_table_classifications():
    with pytest.raises(ValueError):
        appendix_m_through_thickness(effective_weld_depth_assessment_verified=False)
    with pytest.raises(ValueError):
        appendix_m_through_thickness(table_m2_weld_form_case_verified=False)
    with pytest.raises(ValueError):
        appendix_m_through_thickness(remote_restraint_classification_verified=False)
    with pytest.raises(ValueError):
        appendix_m_through_thickness(preheating_condition_verified=False)
    with pytest.raises(ValueError):
        appendix_m_through_thickness(compression_reduction_applicability_verified=False)


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
