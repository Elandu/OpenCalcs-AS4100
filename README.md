# OpenCalcs AS 4100

OpenCalcs plugin version 0.6.0 provides eleven bounded calculation families for
AS 4100:2020 steel design. It evaluates selected equations and declared
conditions; it does not establish full standard or project compliance. Every
applicable member, connection, action, detail and construction requirement needs
an engineering assessment supported by evidence.

| Calculation ID suffix | Scope |
| --- | --- |
| `materials` | Table 2.1 strength lookups; Clauses 2.2.3, 2.2.4 and 2.2.5 material checks, including assessed through-thickness Z demand versus Z-quality class. |
| `section_analysis` | Axial tension and compression section capacities (7.2, 6.2.1). |
| `member_design` | Plate slenderness, 5.2.6 net/gross section modulus selection for fastener holes, compression, selected bending, flat-web and CHS shear, selected flange-restraint enhancement and Clause 5.12.2 proportioning, combined actions and tension distribution. |
| `advanced_members` | Selected full-restraint length limits, critical-section/flange checks, variable/built-up member, buckling-analysis, plastic, restraint, separator/diaphragm, lacing, batten and pin/angle geometry checks. |
| `connection_design` | Selected bolts, pins, welds, groups, holes and connection detailing. |
| `durability` | Selected brittle-fracture, fatigue, fire and earthquake checks. |
| `design_actions` | Stability, serviceability, notional load and selected buckling/amplification calculations. |
| `webs` | Selected web thickness/opening limits, bearing, bearing/bending and stiffener checks. |
| `fabrication` | Clause 14.3.2 standard, base-plate, oversize and slotted-hole size/use checks. |
| `design_review` | Calculation schedule and engineering-evidence register across Sections 1–17. |
| `testing` | Selected proof/prototype load-test comparisons, existing-material prerequisites and informative Appendix B deflection suggestions. |

All IDs have the `structural.as4100.` prefix. Each family exposes an input
schema through the installed `opencalcs.plugins` entry point. Most families
accept one tagged operation per call; `design_review` accepts a schedule of
calculation tasks and evidence records. Use the descriptors for exact input
fields, units and result shapes. Start with [coverage](docs/coverage.md) to
identify what is calculated, what requires external assessment and what remains
unsupported. The detailed family notes are in
[member design](docs/member-design.md),
[further members](docs/advanced-members.md),
[web checks](docs/webs.md),
[connections](docs/connections.md),
[durability](docs/durability.md) and
[testing](docs/testing.md), and [materials](docs/materials.md).
Clause 14.3.2 hole checks are detailed in [fabrication](docs/fabrication.md).

Install with `pip install .`, then restart OpenCalcs. For development and host
integration verification from a sibling checkout:

```bash
python -m pip install -e ".[dev]" -e ../OpenCalcs
python -m pytest
```

The host exposes each installed calculation at
`GET /api/v1/calculations/{calculation_id}` and
`POST /api/v1/calculations/{calculation_id}/run`, using its normal credentials.
The POST body is `{"inputs": <calculation input object>}`. For example,
`examples/axial_section.json` is the input object for
`structural.as4100.section_analysis`; it returns tension design capacity
367.2 kN and compression section design capacity 270 kN. These are illustrative
section results, not a compression-member design.
`examples/material_strength.json` demonstrates the Table 2.1 material lookup.

Inputs such as material strengths, section properties, effective lengths,
restrained lengths, design actions, connection geometry and fatigue categories
must be assessed for the actual product and structure. A grade label or a
passing isolated check cannot replace that assessment. See
[scope and provenance](docs/provenance.md) for the reviewed source and
verification limits.
