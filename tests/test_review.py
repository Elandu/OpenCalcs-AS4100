# SPDX-License-Identifier: AGPL-3.0-only
import pytest

from engcalcs_as4100.review import REQUIREMENTS, run_review


@pytest.fixture
def schedule():
    return {
        "project_reference": "example",
        "engineering_evidence": [],
        "tasks": [
            {
                "id": "T1",
                "family": "section_analysis",
                "entity_reference": "tie1",
                "combination_reference": "ULS1",
                "inputs": {
                    "gross_area_mm2": 2000,
                    "net_area_mm2": 1500,
                    "yield_strength_mpa": 250,
                    "ultimate_strength_mpa": 400,
                    "tension_distribution_factor": 0.8,
                    "compression_form_factor": 0.8,
                    "tension_action_kn": 200,
                    "compression_action_kn": 135,
                },
            }
        ],
    }


def test_missing_evidence_never_gives_complete_review(schedule):
    r = run_review(schedule)
    assert r["all_evaluated_conditions_satisfied"]
    assert len(r["unresolved_requirements"]) == 17
    assert not r["ready_for_engineering_review"]
    assert not r["full_standard_compliance"]
    assert r["calculation_results"][0]["combination_reference"] == "ULS1"


def test_explicit_evidence_does_not_claim_full_standard(schedule):
    schedule["engineering_evidence"] = [
        {
            "requirement": name,
            "status": "assessed",
            "reviewer": "test engineer",
            "evidence_reference": f"R-{name}",
            "reason": "Reviewed project-specific prerequisites",
        }
        for name in REQUIREMENTS
    ]
    r = run_review(schedule)
    assert r["ready_for_engineering_review"]
    assert not r["full_standard_compliance"]
    schedule["tasks"][0]["inputs"]["tension_action_kn"] = 1000
    r = run_review(schedule)
    assert r["failed_task_ids"] == ["T1"]
    assert not r["ready_for_engineering_review"]


def test_duplicates_and_invalid_nested_calculation_rejected(schedule):
    schedule["tasks"] *= 2
    with pytest.raises(ValueError):
        run_review(schedule)
    schedule["tasks"] = schedule["tasks"][:1]
    schedule["tasks"][0]["inputs"]["unexpected"] = 1
    with pytest.raises(ValueError):
        run_review(schedule)


def test_duplicate_evidence_rejected(schedule):
    e = {
        "requirement": "scope",
        "status": "not_applicable",
        "reviewer": "test engineer",
        "evidence_reference": "R1",
        "reason": "Explicit reasoning",
    }
    schedule["engineering_evidence"] = [e, e]
    with pytest.raises(ValueError):
        run_review(schedule)


def test_clause_14_3_2_fabrication_task_runs_in_review(schedule):
    schedule["tasks"][0]["family"] = "fabrication"
    schedule["tasks"][0]["inputs"] = {
        "check_type": "bolt_hole",
        "hole_type": "standard",
        "bolt_diameter_mm": 24,
        "hole_diameter_mm": 26,
    }
    result = run_review(schedule)
    task = result["calculation_results"][0]["result"]
    assert task["clauses"] == ["14.3.2"]
    assert task["checked_conditions_satisfied"]
