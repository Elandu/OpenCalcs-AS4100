# SPDX-License-Identifier: AGPL-3.0-only
"""Immutable reference metadata for the reviewed edition."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StandardReference:
    code: str = "AS 4100"
    edition: str = "2020"
    title: str = "Steel structures"

    def descriptor(self):
        return {
            "code": self.code,
            "edition": self.edition,
            "title": self.title,
            "amendments": (
                "AS 4100:2020 Amendment No. 1 (2021) reviewed; only the covered "
                "corrected provisions are applied."
            ),
        }


STANDARD = StandardReference()

# AS 4100:2020 Clause 2.2.4 design properties.
ELASTIC_MODULUS_MPA = 200_000
SHEAR_MODULUS_MPA = 80_000
POISSON_RATIO = 0.25
THERMAL_EXPANSION_PER_C = 11.7e-6
