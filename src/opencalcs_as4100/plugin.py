# SPDX-License-Identifier: LicenseRef-EngCalcs-Proprietary
"""OpenCalcs installed-plugin contract for steel sections."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from opencalcs_as4100 import __version__
from opencalcs_as4100.schemas import INPUT_SCHEMA, OUTPUT_SCHEMA

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
    standard: None = None

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
            "standard": self.standard,
            "input_schema": deepcopy(self.input_schema),
            "output_schema": deepcopy(self.output_schema),
        }


@dataclass(frozen=True)
class AS4100Plugin:
    id: str = "structural.as4100"
    name: str = "EngCalcs Steel Sections"
    version: str = __version__
    revision: str | None = None
    license: str = "LicenseRef-EngCalcs-Proprietary"
    source: str = "https://github.com/Elandu/EngCalcs-AS4100"
    calculations: tuple[SectionAnalysis, ...] = field(default_factory=lambda: (SectionAnalysis(),))

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
