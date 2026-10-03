# Member calculations

`run_members(inputs)` validates a single `operation` against its exported JSON schema.
AS 4100:2020 was reviewed directly from the licensed scanned standard supplied by the
project owner. No standard pages or extracted source text are distributed with this package.
Capacities are nominal unless a result name says design capacity; the checks apply phi=0.9.
Units are MPa, mm, mm2/mm3/mm4/mm6, kN and kN.m.

## Implemented calculations

| Operation | Reviewed clauses | Behavior and prerequisites |
| --- | --- | --- |
| `plate` | 5.2.2–5.2.5, 6.2.3–6.2.4 | Table-selected slenderness limits; compact/noncompact/slender effective bending modulus, including slender internal-gradient reduction; uniform-compression effective width or CHS effective diameter. Each call is one controlling element. |
| `section_moduli` | 5.2.6 | Checks each flange's fastener-hole area reduction and selects gross moduli, the `An/Ag` area-ratio method, or supplied net-section moduli. The area-ratio method uses the sum of net flange areas plus gross web area for `An`. |
| `compression` | 6.2.1–6.3.3 | Effective-area form factor, net-section capacity and constant-section flexural buckling about both axes. Only doubly symmetric/RHS/CHS member modes are supported. |
| `bending` | 5.3.2.1, 5.6.1.1 | Constant equal-flanged open section with both segment ends fully/partially restrained; reference elastic buckling moment and lateral-buckling reduction. Reports the capacity-based full-restraint route when nominal Mb reaches Ms. E=200000 MPa and G=80000 MPa. `moment_modification_factor` in `advanced_members` calculates 5.6.1.1(a)(iii) from the segment moment diagram. |
| `shear` | 5.11.2–5.11.5, 5.12.3 | Flat unstiffened/stiffened webs, uniform/nonuniform stress reduction and whole-section shear/bending interaction. Conservative flange factor 1. Optional tension-field credit requires assessed stiffeners/end posts. |
| `shear_with_flange_restraint` | 5.11.2–5.11.5.2, 5.12.3 | Flat-web shear and bending interaction with the calculated flange-restraint factor. The clause route requires verified absence of longitudinal web stiffeners; section geometry and web count must be supplied. |
| `chs_shear` | 5.11.3–5.11.4, 5.12.3 | Circular hollow section shear-yield capacity with the specified gross/net effective-area rule and whole-section shear/bending interaction. Requires supplied gross/net area and section moment capacity. |
| `shear_proportioning` | 5.12.2 | Flange-only bending capacity with separate web shear capacity, using the effective compression-flange area and the net-area/tensile-strength limit for the tension flange. |
| `interaction` | 8.3.2–8.3.4, 8.4.2, 8.4.4–8.4.5 | General linear section interaction; elastic in-plane and out-of-plane compression/tension reduction; biaxial member interaction. Section and member checks are reported separately. |
| `tension_distribution` | 7.3.1–7.3.2 | Supported Table 7.3.2 arrangements and both-flange connection length gate. Explicit confirmation of arrangement and force transfer conditions is required. |

All member actions must already include applicable second-order effects under 8.2.
Effective lengths are assessed inputs, not inferred from an analysis mesh.
Section constants for compression must be selected from Table 6.3.3(A/B), including
fabrication, thickness and form-factor distinctions. Effective area is assembled from all
compression elements. A section call must select the controlling bending element by
the greatest element slenderness divided by its yield limit. Supplying one flange only
does not establish the web or the other bending axis classification.

The schemas reject unsupported modes rather than silently applying an equal-flange or
flexural-only equation. Extreme finite inputs producing nonfinite arithmetic are rejected.
Zero available moment/shear capacity returns a failed positive-action check with null
utilisation instead of emitting infinity. No overall structure compliance flag is produced.

## Remaining applicability and implementation requirements

The following cannot currently be claimed as completed by these member primitives:

- 5.2.6: fastener-hole deductions under 9.1.10 remain assessed. The area-ratio path is
  limited to inputs where the supplied flange and gross-web areas make up the gross section;
  the net-section path requires independently established net moduli.
- 5.3–5.5: restraint stiffness/strength, critical flange/section, continuity and load position.
- 5.6.1.1(b)(iii) elastic buckling-analysis alternative and calculation of the elastic
  buckling moment under 5.6.2(ii)/5.6.4 still require independently verified analysis inputs.
  Unequal-flange I-section buckling under 5.6.1.2 and selected varying-section methods under
  5.6.1.1(b)(i)–(ii) are in `advanced_members`; 5.6.3 effective-length factors are available
  there for selected cases.
- 5.7.1–5.7.2 require rational analysis to establish principal-axis moments and restraint
  forces. `advanced_members.nonprincipal_bending` applies the 8.3.4 section interaction and,
  when deflections are unconstrained, the 8.4.5 biaxial member interaction to those supplied
  results. Rational analysis itself remains external. Rational web configuration and opening
  resistance remain outside the selected 5.10 geometry, thickness and transfer checks.
- Rational flange-restraint analysis in 5.11.5.2 and longitudinal-stiffener cases;
  longitudinal-stiffener/rational buckling-analysis alternatives.
- The 5.12.2 flange-only proportioning check is available through `shear_proportioning`;
  5.12.3 whole-section interaction is available through `shear` and `chs_shear` for their
  supported section forms. Other applicable forms still require separate review.
- 5.13–5.16 bearing/stiffener design: handled separately where available, never implied
  by a passing shear check.
- 6.3.3 torsional-flexural buckling cases requiring AS/NZS 4600; 6.3.4 varying sections;
  6.4 laced/battened members; 6.5 back-to-back members; 6.6 restraint systems.
- 7.4 built-up tension-member connection/spacing requirements; 7.5 pin-connected members;
  automatic interpretation of Table 7.3.2 diagrams and connection component force capacity.
- 8.3 optional compact-section enhancements are omitted; the standard's general conservative
  method is used. 8.4.3 plastic-analysis eligibility/hinge checks, 8.4.6 eccentric angle design,
  and alternative enhanced compact-section interactions are not implemented.
- Annex H section-constant generation and rational elastic buckling calculations. Section
  properties and effective lengths need an independently verified source.

These are explicit prerequisites or unsupported paths, not evidence of full AS 4100 design.
For a complete project assessment, each applicable item must have a implemented and verified
calculation or a recorded engineering assessment; applicability is never assumed from a pass.

## Verification

Tests use independent hand arithmetic for hole-adjusted section moduli, effective moduli/widths,
moment/shear capacities,
combined action reductions and boundary cases. Compression reduction is checked against
Table 6.3.3(C) at multiple slenderness and imperfection values, including both ends of the
table. Stiffened shear is checked against Table 5.11.5.2. The table comparisons allow only
the published rounding difference. Additional tests check monotonic reductions, both axes,
unsupported geometries, inconsistent dimensions, nonfinite values and exceeded capacities.

This is numerical verification of implemented primitives, not independent engineering
certification or evidence that every applicable provision of the standard is satisfied.
