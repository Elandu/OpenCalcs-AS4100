import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from engcalcs_as4100.analysis import run_analysis
from engcalcs_as4100.plugin import get_plugin
from engcalcs_as4100.schemas import INPUT_SCHEMA, OUTPUT_SCHEMA


@pytest.fixture
def inputs():
    return json.loads((Path(__file__).parents[1] / "examples/axial_section.json").read_text())


def test_01_net_fracture_benchmark(inputs):
    # 0.85 * 0.8 * 1500 * 400 / 1000 = 408 kN; design = 367.2 kN.
    result = run_analysis(inputs)["tension"]
    assert result["nominal_capacity_kn"] == pytest.approx(408)
    assert result["design_capacity_kn"] == pytest.approx(367.2)
    assert result["utilisation"] == pytest.approx(0.544662309368)
    assert result["governing_mode"] == "net section fracture"


def test_02_gross_yield_benchmark(inputs):
    inputs.update(net_area_mm2=2000, tension_distribution_factor=1)
    result = run_analysis(inputs)["tension"]
    assert result["design_capacity_kn"] == pytest.approx(450)
    assert result["governing_mode"] == "gross section yielding"


def test_03_compression_benchmark(inputs):
    result = run_analysis(inputs)["compression"]
    assert result["nominal_capacity_kn"] == pytest.approx(300)
    assert result["design_capacity_kn"] == pytest.approx(270)
    assert result["utilisation"] == pytest.approx(0.5)


def test_04_capacity_boundary(inputs):
    inputs["compression_action_kn"] = 270
    assert run_analysis(inputs)["compression"]["section_capacity_satisfied"]
    inputs["compression_action_kn"] = 270.0001
    assert not run_analysis(inputs)["compression"]["section_capacity_satisfied"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("net_area_mm2", 2001),
        ("ultimate_strength_mpa", 200),
        ("gross_area_mm2", 0),
        ("compression_form_factor", 1.01),
        ("tension_distribution_factor", 0),
        ("tension_action_kn", -1),
        ("yield_strength_mpa", float("nan")),
        ("tension_action_kn", float("inf")),
        ("net_area_mm2", True),
        ("net_area_mm2", "1500"),
    ],
)
def test_05_invalid_inputs(inputs, key, value):
    inputs[key] = value
    with pytest.raises((ValueError, ValidationError)):
        run_analysis(inputs)


def test_06_no_assumed_factors(inputs):
    del inputs["compression_form_factor"]
    with pytest.raises(ValueError):
        run_analysis(inputs)


def test_07_schema_and_contract(inputs):
    Draft202012Validator.check_schema(INPUT_SCHEMA)
    Draft202012Validator.check_schema(OUTPUT_SCHEMA)
    plugin = get_plugin()
    assert plugin.id == "structural.as4100"
    calculation = plugin.calculations[0]
    Draft202012Validator(OUTPUT_SCHEMA).validate(calculation.run(inputs))
    descriptor = calculation.descriptor()
    descriptor["input_schema"].clear()
    assert calculation.input_schema


def test_08_unexpected_property(inputs):
    inputs["bending_action_knm"] = 10
    with pytest.raises(ValueError):
        run_analysis(inputs)


@pytest.mark.parametrize("value", [None, [], "inputs"])
def test_09_requires_object(value):
    with pytest.raises(ValueError):
        run_analysis(value)


def test_10_numeric_underflow_rejected(inputs):
    inputs.update(
        gross_area_mm2=1e-300,
        net_area_mm2=1e-300,
        yield_strength_mpa=1e-300,
        ultimate_strength_mpa=1e-300,
    )
    with pytest.raises(ValueError):
        run_analysis(inputs)


def test_11_tension_audit_modes(inputs):
    assert run_analysis(inputs)["tension_nominal_modes_kn"] == {
        "gross_yielding": 500,
        "net_fracture": pytest.approx(408),
    }


def test_12_yield_strength_scope_boundary(inputs):
    inputs.update(yield_strength_mpa=690, ultimate_strength_mpa=800)
    assert run_analysis(inputs)["compression"]["design_capacity_kn"] > 0
    inputs["yield_strength_mpa"] = 690.1
    with pytest.raises(ValueError, match="690 MPa"):
        run_analysis(inputs)
