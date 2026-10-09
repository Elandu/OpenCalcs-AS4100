# SPDX-License-Identifier: AGPL-3.0-only
"""Design calculation schedule and explicit engineering evidence register."""

from importlib import import_module

from .validation import object_schema, validate

REQUIREMENTS = {
    "scope": "1: applicability, exclusions, edition and referenced standards",
    "materials": "2: certified steel/bolt/weld properties and thickness effects",
    "design_basis": "3: actions, combinations, stability, reliability and serviceability",
    "analysis": "4: analysis method, second-order effects, restraints and model verification",
    "bending": "5: all bending axes, restraints, webs, bearing and stiffeners",
    "compression": "6: all buckling modes and built-up/variable-section applicability",
    "tension": "7: net paths, connection force transfer and built-up/pin detailing",
    "combined_actions": "8: concurrent signed design actions and section/member interactions",
    "connections": "9: force paths, minimum actions, eccentricity, prying and all components",
    "fracture": "10: grade/thickness/design-temperature and strain assessment",
    "fatigue": "11: detail classification, reference conditions and stress spectrum",
    "fire": "12: FRL, fire tests/protection, grouping and connections",
    "earthquake": "13: system, category, external standards and ductility detailing",
    "fabrication": (
        "14: drawings, hole geometry/use, tolerances, weld procedure and inspection records"
    ),
    "erection": (
        "15: erection safety and procedures, bolt tensioning, tolerances and acceptance evidence"
    ),
    "modification": "16: material identification, condition, repairs and structural reanalysis",
    "testing": "17: load-test planning, specimen representation, acceptance and reporting",
}
_TEXT = {"type": "string", "minLength": 1, "maxLength": 2000}
_EVIDENCE = object_schema(
    {
        "requirement": {"enum": list(REQUIREMENTS)},
        "status": {"enum": ["assessed", "not_applicable", "unresolved"]},
        "reviewer": _TEXT,
        "evidence_reference": _TEXT,
        "reason": _TEXT,
    }
)
_TASK = object_schema(
    {
        "id": _TEXT,
        "family": {
            "enum": [
                "section_analysis",
                "materials",
                "members",
                "advanced_members",
                "connections",
                "durability",
                "design_actions",
                "webs",
                "fabrication",
                "erection",
                "testing",
            ]
        },
        "entity_reference": _TEXT,
        "combination_reference": _TEXT,
        "inputs": {"type": "object"},
    }
)
INPUT_SCHEMA = object_schema(
    {
        "project_reference": _TEXT,
        "tasks": {"type": "array", "minItems": 1, "maxItems": 1000, "items": _TASK},
        "engineering_evidence": {
            "type": "array",
            "maxItems": len(REQUIREMENTS),
            "items": _EVIDENCE,
        },
    }
)
OUTPUT_SCHEMA = {"type": "object"}


def run_review(inputs):
    d = validate(inputs, INPUT_SCHEMA)
    if len({task["id"] for task in d["tasks"]}) != len(d["tasks"]):
        raise ValueError("Task IDs must be unique.")
    evidence = {item["requirement"]: item for item in d["engineering_evidence"]}
    if len(evidence) != len(d["engineering_evidence"]):
        raise ValueError("Each engineering requirement may have only one evidence record.")
    results, failed = [], []
    seen_checks = 0
    runners = {
        "section_analysis": ("analysis", "run_analysis"),
        "materials": ("materials", "run_materials"),
        "members": ("members", "run_members"),
        "advanced_members": ("advanced_members", "run_advanced_members"),
        "connections": ("connections", "run_connections"),
        "durability": ("durability", "run_durability"),
        "design_actions": ("design_actions", "run_design_actions"),
        "webs": ("webs", "run_webs"),
        "fabrication": ("fabrication", "run_fabrication"),
        "erection": ("erection", "run_erection"),
        "testing": ("testing", "run_testing"),
    }

    def flags(value):
        out = []
        if isinstance(value, dict):
            for key, item in value.items():
                if (key.endswith("satisfied") or key == "passes") and isinstance(item, bool):
                    out.append(item)
                elif key not in {"full_standard_compliance", "checked_conditions_satisfied"}:
                    out.extend(flags(item))
        elif isinstance(value, list):
            for item in value:
                out.extend(flags(item))
        return out

    for task in d["tasks"]:
        module_name, runner = runners[task["family"]]
        try:
            module = import_module(f"engcalcs_as4100.{module_name}")
        except ModuleNotFoundError as exc:
            raise ValueError(f"Calculation family {task['family']} is not available.") from exc
        output = getattr(module, runner)(task["inputs"])
        conditions = flags(output)
        seen_checks += len(conditions)
        if any(not condition for condition in conditions):
            failed.append(task["id"])
        results.append(
            {
                "id": task["id"],
                "entity_reference": task["entity_reference"],
                "combination_reference": task["combination_reference"],
                "family": task["family"],
                "inputs": task["inputs"],
                "result": output,
            }
        )
    unresolved = [
        name
        for name in REQUIREMENTS
        if name not in evidence or evidence[name]["status"] == "unresolved"
    ]
    return {
        "standard": "AS 4100:2020",
        "project_reference": d["project_reference"],
        "calculation_results": results,
        "failed_task_ids": failed,
        "evaluated_conditions": seen_checks,
        "all_evaluated_conditions_satisfied": not failed if seen_checks else None,
        "engineering_evidence": d["engineering_evidence"],
        "unresolved_requirements": [
            {"id": name, "requirement": REQUIREMENTS[name]} for name in unresolved
        ],
        "ready_for_engineering_review": seen_checks > 0 and not failed and not unresolved,
        "full_standard_compliance": False,
        "limitations": [
            "Supplied evidence and applicability decisions are not independently authenticated.",
            "A completed register does not certify software coverage or structural compliance.",
            "Schedule all components, stations, directions, combinations and failure paths.",
            "No unrelated extrema may be combined as concurrent member actions.",
        ],
    }
