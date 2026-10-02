import pytest
from jsonschema import Draft202012Validator

from opencalcs_as4100.testing import INPUT_SCHEMA, OUTPUT_SCHEMA, run_testing


def specimen(op="proof_strength"):
    d = {
        "check_type": op,
        "design_load_kn": 100,
        "calibrated_loading_without_artificial_restraints": True,
        "representative_force_distribution_and_duration": True,
        "deformations_recorded_before_during_after": True,
        "test_report_complete": True,
    }
    if op.startswith("prototype"):
        d.update(
            number_similar_units=1,
            materials_fabrication_erection_representative=True,
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
    d.update(number_similar_units=units, sustained_duration_min=5)
    assert result(d)["required_test_load_kn"] == pytest.approx(strength)
    d = specimen("prototype_serviceability")
    d["number_similar_units"] = units
    assert result(d)["required_test_load_kn"] == pytest.approx(serviceability)


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


def test_t03_prototype_duration_and_load_boundaries():
    d = specimen("prototype_strength")
    d.update(sustained_load_kn=150, sustained_duration_min=5)
    assert result(d)["check_satisfied"]
    d["sustained_load_kn"] = 149.999
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


def test_t05_serviceability_boundary():
    d = specimen("proof_serviceability")
    assert result(d)["check_satisfied"]
    d["maximum_deformation_mm"] = 10.001
    assert not result(d)["check_satisfied"]
    d.update(maximum_deformation_mm=10, applied_load_kn=99.999)
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


@pytest.mark.parametrize("units", [0, 6, 7, 9, 11, True])
def test_t11_unlisted_prototype_counts_rejected(units):
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
