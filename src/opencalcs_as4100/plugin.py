# SPDX-License-Identifier: AGPL-3.0-only
"""OpenCalcs installed-plugin contract for steel sections."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from opencalcs_as4100 import __version__
from opencalcs_as4100.schemas import INPUT_SCHEMA, OUTPUT_SCHEMA
from opencalcs_as4100.standards import STANDARD, StandardReference

CALCULATION_ID = "structural.as4100.section_analysis"


@dataclass(frozen=True)
class SectionAnalysis:
    id: str = CALCULATION_ID
    name: str = "Steel axial section checks"
    description: str = (
        "Calculate section axial tension and compression capacities with explicit "
        "properties and assessed factors; excludes member buckling and combined actions."
    )
    discipline: str = "structural"
    category: str = "section-analysis"
    jurisdiction: str = "AU"
    version: str = "1"
    input_schema: dict[str, Any] = field(default_factory=lambda: deepcopy(INPUT_SCHEMA))
    output_schema: dict[str, Any] = field(default_factory=lambda: deepcopy(OUTPUT_SCHEMA))
    standard: StandardReference = STANDARD

    def run(self, inputs: Mapping[str, Any]) -> dict[str, Any]:
        # Keep solver imports out of host discovery and descriptor requests.
        from opencalcs_as4100.analysis import run_analysis

        return run_analysis(inputs)

    def descriptor(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "discipline": self.discipline,
            "category": self.category,
            "jurisdiction": self.jurisdiction,
            "version": self.version,
            "standard": self.standard.descriptor(),
            "input_schema": deepcopy(self.input_schema),
            "output_schema": deepcopy(self.output_schema),
        }


@dataclass(frozen=True)
class ClauseCalculation:
    """Lazy-imported calculation family with the shared installed-host contract."""

    id: str
    name: str
    module: str
    runner: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    version: str = "1"
    standard: StandardReference = STANDARD

    def run(self, inputs: Mapping[str, Any]) -> dict[str, Any]:
        from importlib import import_module

        return getattr(import_module(f"opencalcs_as4100.{self.module}"), self.runner)(inputs)

    def descriptor(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": "Clause checks with assessed inputs and explicit applicability.",
            "discipline": "structural",
            "category": "steel-design",
            "jurisdiction": "AU",
            "version": self.version,
            "standard": self.standard.descriptor(),
            "input_schema": deepcopy(self.input_schema),
            "output_schema": deepcopy(self.output_schema),
        }


def _calculations():
    from importlib import import_module

    families = [
        ("materials", "Steel material properties", "materials", "run_materials"),
        ("member_design", "Steel member design", "members", "run_members"),
        (
            "advanced_members",
            "Advanced member and restraint checks",
            "advanced_members",
            "run_advanced_members",
        ),
        ("connection_design", "Steel connection design", "connections", "run_connections"),
        ("durability", "Fatigue, fire, fracture and earthquake", "durability", "run_durability"),
        (
            "design_actions",
            "Design actions and serviceability",
            "design_actions",
            "run_design_actions",
        ),
        ("webs", "Web bearing and stiffeners", "webs", "run_webs"),
        ("design_review", "Steel design schedule and evidence review", "review", "run_review"),
        ("testing", "Load testing and existing structures", "testing", "run_testing"),
    ]
    calculations = [SectionAnalysis()]
    for suffix, name, module_name, runner in families:
        module = import_module(f"opencalcs_as4100.{module_name}")
        calculations.append(
            ClauseCalculation(
                f"structural.as4100.{suffix}",
                name,
                module_name,
                runner,
                deepcopy(module.INPUT_SCHEMA),
                deepcopy(module.OUTPUT_SCHEMA),
            )
        )
    return tuple(calculations)


@dataclass(frozen=True)
class AS4100Plugin:
    id: str = "structural.as4100"
    name: str = "OpenCalcs Steel Design"
    version: str = __version__
    revision: str | None = None
    license: str = "AGPL-3.0-only"
    source: str = "https://github.com/Elandu/OpenCalcs-AS4100"
    calculations: tuple[Any, ...] = field(default_factory=_calculations)

    def descriptor(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "revision": self.revision,
            "license": self.license,
            "source": self.source,
            "calculations": [calculation.descriptor() for calculation in self.calculations],
        }


def get_plugin() -> AS4100Plugin:
    """Return the installed plugin without starting a service or importing the solver."""
    return AS4100Plugin()
