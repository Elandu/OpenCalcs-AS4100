import pytest
from jsonschema import Draft202012Validator

from opencalcs_as4100.durability import INPUT_SCHEMA, OUTPUT_SCHEMA, run_durability


def fatigue(kind="fatigue_constant", stress="normal"):
    values = {
        "check_type": kind,
        "stress_type": stress,
        "detail_category_mpa": 100,
        "plate_thickness_mm": 25,
        "transverse_weld": True,
        "capacity_factor": 1,
        "redundant_load_path": True,
        "reference_conditions_satisfied": True,
        "yield_strength_mpa": 350,
        "maximum_stress_magnitude_mpa": 200,
        "punched_holes": False,
    }
    values.update(
        {"stress_range_mpa": 100, "cycles": 2e6}
        if kind == "fatigue_constant"
        else {"events": [{"stress_range_mpa": 100, "cycles": 1e6}]}
    )
    return values


def result(d):
    output = run_durability(d)
    Draft202012Validator(OUTPUT_SCHEMA).validate(output)
    return output["results"]


def test_d01_reference_normal_and_shear():
    for stress in ["normal", "shear"]:
        r = result(fatigue(stress=stress))
        assert r["design_fatigue_strength_mpa"] == pytest.approx(100)
        assert r["utilisation"] == pytest.approx(1)
        assert r["check_satisfied"]


def test_d02_normal_first_slope_and_knee():
    d = fatigue()
    d.update(cycles=250000, stress_range_mpa=200)
    assert result(d)["design_fatigue_strength_mpa"] == pytest.approx(200)
    d["cycles"] = 5e6
    assert result(d)["design_fatigue_strength_mpa"] == pytest.approx(73.6806299728)
    d["cycles"] = 1e8
    assert result(d)["design_fatigue_strength_mpa"] == pytest.approx(40.471316447)


def test_d03_thickness_and_punching():
    d = fatigue()
    d["plate_thickness_mm"] = 400
    r = result(d)
    assert r["thickness_factor"] == pytest.approx(0.5)
    assert r["design_fatigue_strength_mpa"] == pytest.approx(50)
    d.update(punched_holes=True, plate_thickness_mm=12)
    assert result(d)["punching_limit_satisfied"]
    d["plate_thickness_mm"] = 12.001
    assert not result(d)["check_satisfied"]


def test_d04_variable_normal_damage():
    d = fatigue("fatigue_variable")
    # At category100 reference stress100, 1e6 cycles consume half the life2e6.
    assert result(d)["damage"] == pytest.approx(0.5)
    d["events"] *= 2
    assert result(d)["damage"] == pytest.approx(1)
    assert result(d)["check_satisfied"]
    d["events"].append({"stress_range_mpa": 20, "cycles": 1e9})
    assert result(d)["damage"] == pytest.approx(1)


def test_d05_shear_and_low_normal_branch():
    d = fatigue("fatigue_variable", "shear")
    assert result(d)["damage"] == pytest.approx(0.5)
    d["events"] = [{"stress_range_mpa": 50, "cycles": 64e6}]
    assert result(d)["damage"] == pytest.approx(1)
    d = fatigue("fatigue_variable")
    d["events"] = [{"stress_range_mpa": 50, "cycles": 5e6}]
    # 0.5**5 / (0.4**(5/3)) = 0.1439074804.
    assert result(d)["damage"] == pytest.approx(0.143907480416)


def test_d06_fatigue_phi_and_stress_domains():
    d = fatigue()
    d["redundant_load_path"] = False
    with pytest.raises(ValueError):
        result(d)
    d["capacity_factor"] = 0.7
    assert result(d)["design_fatigue_strength_mpa"] == pytest.approx(70)
    d.update(maximum_stress_magnitude_mpa=351)
    with pytest.raises(ValueError):
        result(d)


def test_d07_exemption_strict_boundary():
    d = {
        "check_type": "fatigue_exemption",
        "normal_stress_range_mpa": 27,
        "shear_stress_range_mpa": 27,
        "cycles": 1e9,
        "capacity_factor": 1,
        "redundant_load_path": True,
        "reference_conditions_satisfied": True,
    }
    assert not result(d)["assessment_exempt"]
    d["normal_stress_range_mpa"] = d["shear_stress_range_mpa"] = 26.999
    assert result(d)["assessment_exempt"]
    d.update(normal_stress_range_mpa=36, shear_stress_range_mpa=36, cycles=2e6)
    assert not result(d)["assessment_exempt"]
    d["cycles"] = 1999999
    assert result(d)["assessment_exempt"]


def test_d08_fire_yield_and_moduli():
    d = {
        "check_type": "fire_material",
        "temperature_c": 215,
        "yield_strength_20_mpa": 350,
        "elastic_modulus_20_mpa": 200000,
        "poisson_ratio": 0.3,
    }
    assert result(d)["yield_ratio"] == 1
    d["temperature_c"] = 560
    assert result(d)["yield_ratio"] == pytest.approx(0.5)
    d["temperature_c"] = 800
    r = result(d)
    assert r["elastic_ratio"] == pytest.approx(138 / 746.5)
    assert r["shear_modulus_mpa"] == pytest.approx(r["elastic_modulus_mpa"] / 2.6)
    d["temperature_c"] = 905
    assert result(d)["yield_strength_mpa"] == 0


def test_d09_fire_limiting_and_unprotected():
    assert result({"check_type": "fire_limiting_temperature", "fire_action_ratio": 0.5}) == {
        "limiting_temperature_c": 560
    }
    d = {
        "check_type": "fire_unprotected",
        "limiting_temperature_c": 500,
        "surface_mass_ratio_m2_per_tonne": 10,
        "exposure_sides": 3,
        "required_frl_min": 27.5,
    }
    assert result(d)["psa_min"] == pytest.approx(27.5)
    assert result(d)["check_satisfied"]
    d["exposure_sides"] = 4
    assert result(d)["psa_min"] == pytest.approx(19.1)
    d["limiting_temperature_c"] = 260
    assert result(d)["psa_min"] == pytest.approx(9.55)
    d["limiting_temperature_c"] = 20
    assert result(d)["psa_min"] == 0
    d["limiting_temperature_c"] = 751
    with pytest.raises(ValueError):
        result(d)


def test_d10_fire_prototype_gates():
    d = {
        "check_type": "fire_single_test",
        "prototype_psa_min": 60,
        "required_frl_min": 60,
        "protection_thickness_mm": 20,
        "prototype_protection_thickness_mm": 20,
        "surface_mass_ratio_m2_per_tonne": 10,
        "prototype_surface_mass_ratio_m2_per_tonne": 10,
        "fire_action_ratio": 0.5,
        "prototype_fire_action_ratio": 0.5,
        "same_protection_system": True,
        "same_exposure": True,
        "same_supports": True,
        "restraints_not_less_favourable": True,
    }
    assert result(d)["check_satisfied"]
    d["same_supports"] = False
    assert not result(d)["check_satisfied"]


def test_d11_protected_regression():
    # Synthetic coefficient evaluation, not a qualifying fire test calibration.
    d = {
        "check_type": "fire_protected_regression",
        "coefficients": [1, 1, 1, 1, 1, 1, 1],
        "temperature_c": 500,
        "protection_thickness_mm": 20,
        "surface_mass_ratio_m2_per_tonne": 10,
        "required_frl_min": 60,
        "test_count": 9,
        "test_series_conditions_satisfied": True,
        "inside_reviewed_interpolation_window": True,
    }
    assert result(d)["psa_min"] == pytest.approx(11573)
    d["inside_reviewed_interpolation_window"] = False
    with pytest.raises(ValueError):
        result(d)


def brittle():
    return {
        "check_type": "brittle_fracture",
        "steel_type": "1",
        "thickness_mm": 6,
        "design_service_temperature_c": -19,
        "outer_fibre_strain_percent": 0,
        "post_weld_heat_treatment_c": 0,
        "impact_test_temperature_c": 100,
        "fabrication_erection_requirements_satisfied": True,
    }


def test_d12_brittle_table_boundaries_and_strain():
    d = brittle()
    assert result(d)["permissible_service_temperature_c"] == -20
    assert result(d)["check_satisfied"]
    d["thickness_mm"] = 6.001
    assert result(d)["permissible_service_temperature_c"] == -10
    assert not result(d)["check_satisfied"]
    d.update(thickness_mm=6, outer_fibre_strain_percent=11)
    assert result(d)["permissible_service_temperature_c"] == 1
    d["post_weld_heat_treatment_c"] = 500
    assert result(d)["permissible_service_temperature_c"] == 1
    d["post_weld_heat_treatment_c"] = 620
    assert result(d)["permissible_service_temperature_c"] == -20
    d["impact_test_temperature_c"] = -40
    assert result(d)["permissible_service_temperature_c"] == -40


def test_d13_unavailable_steel_and_seismic_audit():
    d = brittle()
    d.update(steel_type="8C", thickness_mm=13)
    with pytest.raises(ValueError):
        result(d)
    d = {
        "check_type": "earthquake_audit",
        "structural_system": "intermediate_moment",
        "grade_minimum_yield_mpa": 350,
        "design_storey_deflection_mm": 4,
    }
    r = result(d)
    assert r["ductility_factor"] == 3
    assert r["structural_performance_factor"] == 0.67
    assert r["minimum_panel_movement_mm"] == 6
    assert r["manual_review_required"]


@pytest.mark.parametrize("value", [None, [], {"check_type": "unknown"}])
def test_d14_input_shape(value):
    with pytest.raises(ValueError):
        result(value)


def test_d15_schema_and_nonfinite():
    Draft202012Validator.check_schema(INPUT_SCHEMA)
    Draft202012Validator.check_schema(OUTPUT_SCHEMA)
    d = fatigue()
    d["cycles"] = float("nan")
    with pytest.raises(ValueError):
        result(d)


def test_d16_modulus_upper_domain():
    d = {
        "check_type": "fire_modulus",
        "temperature_c": 1000,
        "elastic_modulus_20_mpa": 200000,
        "poisson_ratio": 0.3,
    }
    assert result(d)["elastic_ratio"] == 0
    d["temperature_c"] = 1000.001
    with pytest.raises(ValueError):
        result(d)


def test_d17_exemption_overrides_normal_damage_only():
    d = fatigue("fatigue_variable")
    d["events"] = [{"stress_range_mpa": 50, "cycles": 1e10}]
    r = result(d)
    assert r["damage"] > 1
    assert r["further_assessment_exempt"]
    assert r["check_satisfied"]
    d["stress_type"] = "shear"
    assert not result(d)["check_satisfied"]


def test_d18_result_schema_rejects_wrong_result_fields():
    output = run_durability({"check_type": "fire_limiting_temperature", "fire_action_ratio": 1})
    output["results"]["made_up_value"] = 1
    assert not Draft202012Validator(OUTPUT_SCHEMA).is_valid(output)


def test_d19_impossible_stress_history_and_unsupported_category():
    d = fatigue()
    d["maximum_stress_magnitude_mpa"] = 49
    with pytest.raises(ValueError):
        result(d)
    d = fatigue()
    d["detail_category_mpa"] = 1000
    with pytest.raises(ValueError):
        result(d)
