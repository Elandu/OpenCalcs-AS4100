# Scope and provenance

The reference edition is AS 4100:2020, *Steel structures*. The project owner's
licensed scanned copy was reviewed directly for the expanded calculation
families. The scan, page images and extracted standard text are not distributed
with this repository. No separate amendments were supplied or verified;
applicable amendments and project requirements require engineering review.

Table 2.1 material strengths are available for the listed product forms, grades
and thickness ranges. Clause 2.2.3 also compares unidentified-steel design
strengths with its limits or requires an attested full AS 1391 test. Clause
2.2.4 supplies the standard steel design properties used by the applicable
calculations. Clause 2.2.5 compares an externally assessed Appendix M design
Z-value with AS/NZS 3678 Z-quality class and thickness; it does not calculate
the weld/detail demand. Material certification, test evidence, Table 2.1 notes,
Clause 3.8 detailing and clauses 2.3–2.5 remain assessed outside these
calculations.

Version 0.7.1 exposes twelve installed calculation families. The code implements
bounded numerical checks and condition comparisons, with clause identifiers,
declared applicability and explicit prerequisites. [Coverage](coverage.md)
maps each of the standard's 17 sections to calculated, assessed and missing
work. The family notes give operation-level boundaries. `design_review` can
assemble results and an evidence register, but does not authenticate evidence,
decide every provision's applicability or certify a design. Its
`full_standard_compliance` result remains false.

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
