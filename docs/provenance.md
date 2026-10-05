# Scope and provenance

The reference edition is AS 4100:2020, *Steel structures*. The project owner's
licensed scanned copy was reviewed directly for the expanded calculation
families. Amendment No. 1:2021 (Correction amendment) was reviewed. The supported
routes apply its Clause 5.6.1.1 labels, the corrected Table 6.3.3(C) row, the
Clause 6.4.1 equation label, powered Clause 8.4.5.1–8.4.5.2 interactions and
Clause 8.4.6 interaction. Its corrected Appendix H.4 closed-section torsion-
constant equation is implemented for verified thin-walled single-cell closed
sections. The informative Appendix H.4 open-section approximation
`J ≈ Σ(b t³ / 3)` is also implemented for verified thin-walled open geometry.
The separate multi-cell operation uses a supplemental thin-walled Bredt–Batho
cell-compatibility formulation, not an equation stated by AS 4100, and returns
the torsion property only.
The Appendix H.4 warping-constant expressions are implemented for doubly
symmetric and monosymmetric I-sections and channels, along with its stated zero
for angle, tee and narrow rectangular sections and its permitted zero
approximation for hollow sections. Other section properties and member
resistance remain externally supplied. The amendment
PDF, base-standard scan, page images and extracted standard text are not
distributed with this repository. No later amendments were supplied or verified;
applicable project requirements require engineering review.
Printed page 180 was reviewed for Clauses 16.1–16.2, pages 181–183 for
Section 17, and page 185 for informative Appendix B.

Table 2.1 material strengths are available for the listed product forms, grades
and thickness ranges. Clause 2.2.3 also compares unidentified-steel design
strengths with its limits or requires an attested full AS 1391 test. Clause
2.2.4 supplies the standard steel design properties used by the applicable
calculations. Clause 2.2.5 compares an externally assessed Appendix M design
Z-value with AS/NZS 3678 Z-quality class and thickness; it does not calculate
the weld/detail demand. Material certification, test evidence, Table 2.1 notes,
product/process effects, Clause 3.8 detailing, heat treatment and complete
lamellar-tearing assessment remain external. The selected Clause 2.3.2 route
compares supplied equivalent-fastener dimensions and minimum tension but does
not authenticate certificates or material/installation evidence; the other
Clause 2.3 fastener, weld, stud and anchor provisions and Clause 2.4 castings
remain assessed.

Version 0.7.24 exposes twelve installed calculation families. The code implements
bounded numerical checks and condition comparisons, with clause identifiers,
declared applicability and explicit prerequisites. [Coverage](coverage.md)
maps each of the standard's 17 sections to calculated, assessed and missing
work. The family notes give operation-level boundaries. `design_review` can
assemble results and an evidence register, but does not authenticate evidence,
decide every provision's applicability or certify a design. Its
`full_standard_compliance` result remains false. The selected Clause 7.4.2
operation now derives the transverse shear and per-plane tension-lacing or
tension-batten actions from verified piecewise-linear member moment diagrams.
It does not check connector capacities or cover nonlinear, biaxial, or direct
inter-component load cases. The compression built-up action route calculates
Clause 6.4.1 design shear and derives per-bay lacing, batten and tie-plate
demands from the verified geometry; its scope and limits are recorded in
[advanced member notes](advanced-members.md).
The Clause 6.5 connection-layout route checks the separated and in-contact
member arrangements, minimum bay count, full member coverage, approximately
equal-bay evidence and end fastener/equivalent-weld conditions. Clause 6.5
capacity checks and detailed connection design remain separate.
The compression interconnection route calculates the Clause 6.4.1 shear envelope,
then evaluates `0.25 V* (l_e/r)_c` for each listed interconnection and compares its
supplied design capacity. In-contact members trace Clause 6.5.2.5 back to Clause
6.5.1.5. Completeness, geometry, capacity and connection detailing remain
externally assessed; the operation does not authenticate their evidence.
The Clause 6.6 restraint route applies the greater of the analyzed restraint force
and the minimum force for the connected compression member, adding the 6.6.3
parallel-member allowance when supplied. Its closer-spacing route accepts groups
of actual restraints only with a complete inventory and verified equivalent-position
evidence. For each group it checks `N* = φNc` using the supplied nominal member
capacity and the Table 3.4 compression-member factor, then applies the analyzed-force
envelope and group-specific minimum. Allocated path forces must balance each group;
capacity demands are accumulated for components shared between paths or groups.
The analysis, grouping, capacity derivations and evidence are supplied rather than
authenticated here. Restraint stiffness and complete restraint-system design remain
outside this check.

The original axial section equations were also compared with
[steel-as](https://github.com/Folded-Structures-Lab/steel-as),
revision `3b650048a26ceb816b21431cfc8d723cadaba71e`,
`src/steelas/member/member.py`: `_N_s`, `_N_ty`, `_N_tf`, `_N_t`, and `phi`.
Its MIT notice is retained in [steel-as-LICENSE.txt](steel-as-LICENSE.txt).
The section equations are:

- Section tension: `Nt = min(Ag fy, 0.85 kt An fu)` (7.2).
- Section compression: `Ns = kf An fy` (6.2.1).
- Design capacities use `phi = 0.9`; mm² times MPa gives N, divided by 1000 for kN.

The input factors `kt` and `kf` require assessment.

[BeamDesign](https://github.com/skane88/BeamDesign) was inspected as a comparison;
no license was identified, so no source or test vectors were copied.
[sectionproperties](https://github.com/robbievanleeuwen/section-properties) can
calculate geometric properties such as centroid, inertias, plastic properties,
torsion and warping constants. It cannot select AS 4100 reductions, net areas,
restraints or tension distribution factors. It is not a required dependency;
an optional adapter can be added if geometry-to-property automation is in scope.

[OpenSees](https://github.com/OpenSees/OpenSees) could supply external structural
analysis after separate licensing and model review; it is not bundled. This
package has no runtime solver or geometry library. External buckling loads,
moments and design actions must be verified for the actual modes, restraints
and load cases.

The tests use independent hand calculations, selected table values, boundary
conditions, schema checks and host descriptor checks. They verify implemented
arithmetic and supported input domains. They do not verify product certificates,
construction records, physical tests, a complete AS 4100 implementation or
fitness of a particular structure. In particular, unequal-flange and
monosymmetric lateral-torsional buckling, rational torsional-flexural analysis
and the special 8.4.6 angle interaction remain
unresolved. Engineers must identify every applicable provision before relying
on a result.
