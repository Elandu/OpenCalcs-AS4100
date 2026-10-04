import pytest
from jsonschema import Draft202012Validator

from opencalcs_as4100.testing import INPUT_SCHEMA, OUTPUT_SCHEMA, run_testing


def specimen(op="proof_strength"):
    d = {
        "check_type": op,
        "design_load_kn": 100,
        "calibrated_loading_without_artificial_restraints": True,
        "representative_force_distribution_and_duration": True,
        "loading_rate_as_uniform_as_practicable_verified": True,
        "deformations_recorded_before_during_after": True,
        "loading_method_recorded": True,
        "deflection_measurement_method_recorded": True,
        "other_relevant_test_data_recorded": True,
        "acceptance_statement_recorded": True,
        "test_report_complete": True,
    }
    if op.startswith("prototype"):
        d.update(
            number_similar_units=1,
            materials_conform_section_2_verified=True,
            fabrication_conforms_section_14_verified=True,
            manufacturing_specification_requirements_met_verified=True,
            erection_method_represents_production_verified=True,
            production_units_similar=True,
        )
    if op.endswith("strength"):
        d.update(sustained_load_kn=150, sustained_duration_min=15)
        if op.startswith("proof"):
            d.update(post_test_damage_inspected=True, damage_review_and_repairs_complete=True)
    else:
        d.update(applied_load_kn=120, maximum_deformation_mm=10, applicable_deformation_limit_mm=10)
    return d


def result(d):
    out = run_testing(d)
    Draft202012Validator(OUTPUT_SCHEMA).validate(out)
    return out["results"]


@pytest.mark.parametrize(
    "units,strength,serviceability",
    [(1, 150, 120), (2, 140, 120), (3, 130, 120), (4, 130, 110), (5, 130, 110), (10, 120, 110)],
)
def test_t01_prototype_table(units, strength, serviceability):
    d = specimen("prototype_strength")
    d.update(number_similar_units=units, sustained_load_kn=strength, sustained_duration_min=5)
    assert result(d)["required_test_load_kn"] == pytest.approx(strength)
    assert result(d)["check_satisfied"]
    d = specimen("prototype_serviceability")
    d["number_similar_units"] = units
    d["applied_load_kn"] = serviceability
    assert result(d)["required_test_load_kn"] == pytest.approx(serviceability)
    assert result(d)["check_satisfied"]


def test_t02_proof_duration_and_damage_inspection():
    d = specimen()
    d["sustained_load_kn"] = 100
    assert result(d)["required_duration_min"] == 15
    assert result(d)["check_satisfied"]
    d["sustained_duration_min"] = 14.999
    assert not result(d)["check_satisfied"]
    d["sustained_duration_min"] = 15
    d["post_test_damage_inspected"] = False
    assert not result(d)["check_satisfied"]
    d["post_test_damage_inspected"] = True
    d["sustained_load_kn"] = 100.001
    assert not result(d)["check_satisfied"]


def test_t03_prototype_duration_and_load_boundaries():
    d = specimen("prototype_strength")
    d.update(sustained_load_kn=150, sustained_duration_min=5)
    assert result(d)["check_satisfied"]
    d["sustained_load_kn"] = 149.999
    assert not result(d)["check_satisfied"]
    d.update(sustained_load_kn=150.001, sustained_duration_min=5)
    assert not result(d)["check_satisfied"]
    d.update(sustained_load_kn=150, sustained_duration_min=4.999)
    assert not result(d)["check_satisfied"]


def test_t04_report_and_production_similarity():
    d = specimen("prototype_strength")
    d["test_report_complete"] = False
    assert not result(d)["check_satisfied"]
    d["test_report_complete"] = True
    d["production_units_similar"] = False
    assert not result(d)["check_satisfied"]


@pytest.mark.parametrize(
    "field",
    [
        "loading_method_recorded",
        "loading_rate_as_uniform_as_practicable_verified",
        "deflection_measurement_method_recorded",
        "other_relevant_test_data_recorded",
        "acceptance_statement_recorded",
    ],
)
def test_t04_report_must_include_clause_17_6_content(field):
    d = specimen()
    d[field] = False
    assert not result(d)["check_satisfied"]


@pytest.mark.parametrize(
    "field",
    [
        "materials_conform_section_2_verified",
        "fabrication_conforms_section_14_verified",
        "manufacturing_specification_requirements_met_verified",
        "erection_method_represents_production_verified",
        "production_units_similar",
    ],
)
def test_t04_prototype_specimen_and_production_requirements(field):
    d = specimen("prototype_strength")
    d[field] = False
    assert not result(d)["check_satisfied"]


def test_t13_test_scope_and_applicability_clauses_17_1_and_17_2():
    output = run_testing(
        {
            "check_type": "test_scope_applicability",
            "test_article": "individual_member",
            "test_type": "proof",
            "test_purpose": "specific_unit_characteristics",
            "design_complies_with_as_4100_verified": True,
            "special_circumstances_require_test_verified": False,
            "test_used_as_alternative_to_calculation_verified": False,
        }
    )
    results = output["results"]
    assert output["clauses"] == ["17.1.1", "17.1.2", "17.2"]
    assert results["check_satisfied"]
    assert results[
        "testing_not_required_for_standard_compliant_design_without_special_circumstances"
    ]

    out_of_scope = run_testing(
        {
            "check_type": "test_scope_applicability",
            "test_article": "structural_model",
            "test_type": "prototype",
            "test_purpose": "general_design_criteria_or_data",
            "design_complies_with_as_4100_verified": False,
            "special_circumstances_require_test_verified": False,
            "test_used_as_alternative_to_calculation_verified": True,
        }
    )
    assert not out_of_scope["results"]["check_satisfied"]


def test_t05_serviceability_boundary():
    d = specimen("proof_serviceability")
    d["applied_load_kn"] = 100
    assert result(d)["check_satisfied"]
    d["maximum_deformation_mm"] = 10.001
    assert not result(d)["check_satisfied"]
    d.update(maximum_deformation_mm=10, applied_load_kn=99.999)
    assert not result(d)["check_satisfied"]
    d["applied_load_kn"] = 100.001
    assert not result(d)["check_satisfied"]


def vertical():
    return {
        "check_type": "suggested_vertical_limit",
        "span_or_cantilever_length_mm": 6000,
        "cantilever": False,
        "application": "all_beams",
        "provision_minimises_partition_movement": False,
        "deflection_scope": "total",
        "support_rotation_included": False,
        "calculated_deflection_mm": 24,
    }


def test_t06_vertical_suggestions():
    d = vertical()
    assert result(d)["suggested_limit_mm"] == pytest.approx(24)
    assert result(d)["suggestion_satisfied"]
    d.update(application="masonry_partitions", deflection_scope="after_partition_attachment")
    assert result(d)["suggested_limit_mm"] == pytest.approx(6)
    d["provision_minimises_partition_movement"] = True
    assert result(d)["suggested_limit_mm"] == pytest.approx(12)
    d.update(cantilever=True, support_rotation_included=True)
    assert result(d)["suggested_limit_mm"] == pytest.approx(24)


def test_t07_vertical_scope_rejection():
    d = vertical()
    d["cantilever"] = True
    with pytest.raises(ValueError):
        result(d)
    d.update(cantilever=False, application="masonry_partitions")
    with pytest.raises(ValueError):
        result(d)


def portal():
    return {
        "check_type": "suggested_portal_horizontal_limit",
        "deflection_type": "absolute_frame",
        "cladding": "steel_or_aluminium_sheet",
        "gantry_cranes": False,
        "no_ceilings_or_internal_partitions_at_external_walls": True,
        "frame_spacing_mm": 6000,
        "eaves_height_mm": 9000,
        "crane_rail_height_mm": 5000,
        "calculated_deflection_mm": 20,
        "serviceability_wind_loading_confirmed": True,
        "masonry_supported_by_steelwork": False,
    }


def test_t08_horizontal_suggestions():
    d = portal()
    assert result(d)["suggested_limit_mm"] == pytest.approx(60)
    d["gantry_cranes"] = True
    assert result(d)["suggested_limit_mm"] == pytest.approx(20)
    d["deflection_type"] = "relative_adjacent_frames"
    assert result(d)["suggested_limit_mm"] == pytest.approx(24)
    d["gantry_cranes"] = False
    assert result(d)["suggested_limit_mm"] == pytest.approx(30)
    d.update(
        deflection_type="absolute_frame",
        cladding="external_masonry",
        masonry_supported_by_steelwork=True,
    )
    assert result(d)["suggested_limit_mm"] == pytest.approx(36)


def test_t09_horizontal_scope_gates():
    d = portal()
    d["no_ceilings_or_internal_partitions_at_external_walls"] = False
    with pytest.raises(ValueError):
        result(d)
    d = portal()
    d.update(cladding="external_masonry", gantry_cranes=True, masonry_supported_by_steelwork=True)
    with pytest.raises(ValueError):
        result(d)


def test_t10_material_audit_never_certifies_design():
    d = {
        "check_type": "existing_material_audit",
        "base_metal_identified": True,
        "material_test_evidence_available": True,
        "modification_repair_procedures_reviewed": True,
        "as_nzs_5131_requirements_satisfied": True,
    }
    assert result(d)["prerequisites_satisfied"]
    assert result(d)["manual_review_required"]
    d["base_metal_identified"] = False
    assert not result(d)["prerequisites_satisfied"]


def test_t11_existing_structure_modification_clause_16_gates():
    d = {
        "check_type": "existing_structure_modification_review",
        "other_as4100_provisions_applied_unless_modified_verified": True,
        "site_modifications_during_erection_applicable": True,
        "site_modifications_conform_as_nzs_5131_verified": True,
        "existing_modification_or_repair_applicable": True,
        "existing_modification_or_repair_conforms_as_nzs_5131_verified": True,
        "strengthening_repair_or_welding_documents_prepared": True,
        "base_metal_types_determined_before_documents_verified": True,
    }
    output = run_testing(d)
    assert output["clauses"] == ["16.1", "16.2"]
    checked = output["results"]
    assert checked["check_satisfied"]
    assert checked["manual_review_required"]

    d["site_modifications_conform_as_nzs_5131_verified"] = False
    failed_erection_route = run_testing(d)["results"]
    assert not failed_erection_route["site_modification_requirements_satisfied"]
    assert not failed_erection_route["check_satisfied"]

    d.update(
        site_modifications_during_erection_applicable=False,
        site_modifications_conform_as_nzs_5131_verified=False,
        base_metal_types_determined_before_documents_verified=False,
    )
    d["strengthening_repair_or_welding_documents_prepared"] = False
    assert run_testing(d)["results"]["check_satisfied"]


@pytest.mark.parametrize("units", [0, 6, 7, 9, 11, True])
def test_t12_unlisted_prototype_counts_rejected(units):
    d = specimen("prototype_strength")
    d["number_similar_units"] = units
    with pytest.raises(ValueError):
        result(d)


def test_t12_schemas_and_domains():
    Draft202012Validator.check_schema(INPUT_SCHEMA)
    Draft202012Validator.check_schema(OUTPUT_SCHEMA)
    d = specimen()
    d["sustained_duration_min"] = float("nan")
    with pytest.raises(ValueError):
        result(d)
    with pytest.raises(ValueError):
        result(None)
