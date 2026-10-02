# Scope and provenance

Baseline: AS 4100:2020, limited to axial section capacity equations referenced by
steel-as. No claim of complete standard compliance or independent standards audit.
Amendments and project-specific applicability require engineering review.

Reviewed reference: [steel-as](https://github.com/Folded-Structures-Lab/steel-as),
revision `3b650048a26ceb816b21431cfc8d723cadaba71e`,
`src/steelas/member/member.py`: `_N_s`, `_N_ty`, `_N_tf`, `_N_t`, and `phi`.
The MIT notice is retained in `steel-as-LICENSE.txt`. Equations implemented:

- Section tension: `Nt = min(Ag fy, 0.85 kt An fu)` (clause 7.2).
- Section compression: `Ns = kf An fy` (clause 6.2.1).
- Design capacities use `phi = 0.9`; mm² × MPa gives N, divided by 1000 for kN.

[BeamDesign](https://github.com/skane88/BeamDesign) was inspected as a comparison;
no license was identified, so no source or test vectors were copied.
[section-properties](https://github.com/robbievanleeuwen/section-properties) can
provide geometric properties in future. It does not select AS 4100 local
slenderness reductions, net areas, or tension distribution factors.
No solver or geometry library is a runtime dependency in this release.

[OpenSees](https://github.com/OpenSees/OpenSees) is a possible future analysis
backend; its redistribution and commercial licensing require separate review.
It is not bundled. Section checks accept solver-independent explicit actions.

The numbered tests use hand-derived arithmetic examples. They verify equations,
units, schemas, domains and plugin descriptors; they are not independent full
AS 4100 validation. No section catalogue or automatic factor selection is included.
