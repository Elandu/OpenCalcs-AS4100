# OpenCalcs AS 4100

An installed OpenCalcs plugin for bounded AS 4100:2020 axial **section** checks.
The first release implements clause 7.2 tension (gross yielding and net fracture)
and clause 6.2.1 compression section capacity, using capacity factor 0.9.

Install with `pip install .`, then discover calculation
`structural.as4100.section_analysis` through the `opencalcs.plugins` entry point.
For development and host integration verification from a sibling checkout:

```bash
python -m pip install -e ".[dev]" -e ../OpenCalcs
python -m pytest
```

Restart OpenCalcs after installing the plugin. Its existing API exposes
`GET /api/v1/calculations/structural.as4100.section_analysis` and
`POST /api/v1/calculations/structural.as4100.section_analysis/run`.
The POST body is `{"inputs": <contents of examples/axial_section.json>}`; use
the host's normal credentials. The example returns tension design capacity
367.2 kN and compression section design capacity 270 kN.

Supply gross and net areas in mm², strengths in MPa, assessed tension distribution
factor `kt`, compression form factor `kf`, and nonnegative factored action magnitudes
in kN. Neither factor defaults to 1.0. Material strengths must reflect product and
thickness; a grade label is insufficient. The example contains explicit illustrative inputs.

Results show nominal/design capacities, utilisation and section capacity satisfaction.
They do not establish full member or structure compliance. Member buckling,
bending, shear, combined actions, connections, fatigue, fire, section classification
and selection of factors are outside this release. Compression section capacity
alone is insufficient for a compression member design.

See [provenance](docs/provenance.md) for sources and verification limits.
