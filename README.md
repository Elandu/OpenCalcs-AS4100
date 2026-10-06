# OpenCalcs AS 4100

OpenCalcs plugin version 0.7.60 provides twelve bounded calculation families for
AS 4100:2020 steel design. It evaluates selected equations and declared
conditions; it does not establish full standard or project compliance. Every
applicable member, connection, action, detail and construction requirement needs
an engineering assessment supported by evidence.

| Calculation ID suffix | Scope |
| --- | --- |
| `materials` | Table 2.1 strength lookups; Clauses 2.2.3 and 2.2.4, Clause 2.2.5 Z-quality comparison, and Appendix M.2 Table M.2 `ZEd` calculation linked to the Clause 2.2.5 class check. |
| `section_analysis` | Axial tension and compression section capacities (7.2, 6.2.1). |
| `member_design` | Clause 5.1 elastic major/minor-axis and plastic-method design comparisons; Clause 5.2.1–5.2.5 flat-plate section moment capacity with automatic controlling-element selection; 5.2.6 net/gross section modulus selection for fastener holes; selected 6.2–6.3 compression member buckling, including the explicit 6.3.3 flexural-only section exceptions; selected bending, flat-web and CHS shear, flange-restraint enhancement, Clause 5.12.2 proportioning, combined actions and tension distribution. |
| `advanced_members` | Selected cross-section restraint classification and full-restraint length limits, critical-section/flange checks, variable/built-up member, buckling-analysis, plastic, restraint, separator/diaphragm, lacing, batten and pin/angle geometry checks; derives selected Clause 7.4.2 lacing/batten actions from verified member moment diagrams. |
| `connection_design` | Selected bolts, pins, welds, groups, holes and connection detailing. |
| `durability` | Selected brittle-fracture, fatigue, fire and earthquake checks. |
| `design_actions` | Stability, serviceability, notional load, selected member and whole-frame buckling/amplification calculations, bounded linearized and corotational second-order frame-response analyses, global/joint equilibrium and support-boundary comparisons under Clause 4.5.1, prescriptive Clause 4.5.2 limits and an alternative-ductility evidence assessment, plus selected Clause 4.5.3 checks ([details](docs/design-actions.md)). |
| `webs` | Selected web thickness/opening limits, bearing, bearing/bending and stiffener checks. |
| `fabrication` | Selected Clause 14.1 acceptance routes, 14.2 material/fabrication checks, 14.3 hole and bolt-assembly checks, and 14.4 tolerance paths. |
| `erection` | Selected Clause 15.1.1 acceptance routes, 15.1.2 safety, 15.2 erection and bolt tensioning, and 15.3 tolerance checks. |
| `design_review` | Calculation schedule and engineering-evidence register across Sections 1–17. |
| `testing` | Selected Section 16 existing-structure review gates; Section 17 scope, proof/prototype load and report checks; existing-material prerequisites; informative Appendix B deflection suggestions. |

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
Fabrication checks are detailed in [fabrication](docs/fabrication.md).
Erection checks are detailed in [erection](docs/erection.md).

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
