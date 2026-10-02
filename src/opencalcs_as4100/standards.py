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
            "amendments": "No separate amendments supplied or verified",
        }


STANDARD = StandardReference()
