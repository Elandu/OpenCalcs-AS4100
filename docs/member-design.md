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
| `section_moduli` | 5.2.6 | Checks each flange's fastener-hole area reduction and selects gross moduli, the `An/Ag` area-ratio method, supplied net-section moduli, or derived net properties for verified sharp-corner symmetric I-sections and RHS/SHS with major-axis bending and flange-only holes whose net layout preserves that principal axis. The geometry route reports centroid, plastic neutral axis, second moment, elastic moduli at both extreme fibres and plastic modulus; it uses the lower extreme-fibre elastic modulus. Net flange areas are supplied top-to-bottom after 9.1.10 deductions. For RHS/SHS, gross web area is the sum of both side walls. The area-ratio method uses net flange areas plus gross web area for `An`. |
| `compression` | 6.2.1–6.3.3 | Effective-area form factor, net-section capacity and constant-section flexural buckling about both axes. Only doubly symmetric/RHS/CHS member modes are supported. |
| `bending` | 5.3.2.1, 5.6.1.1 | Constant equal-flanged open section with both segment ends fully/partially restrained; reference elastic buckling moment and lateral-buckling reduction. Reports the capacity-based full-restraint route when nominal Mb reaches Ms. E=200000 MPa and G=80000 MPa. `moment_modification_factor` in `advanced_members` calculates 5.6.1.1(a)(iii) from the segment moment diagram. |
| `shear` | 5.11.2–5.11.5, 5.12.3 | Flat unstiffened/stiffened webs, uniform/nonuniform stress reduction and whole-section shear/bending interaction. Conservative flange factor 1. Optional tension-field credit requires assessed stiffeners/end posts. |
| `shear_with_flange_restraint` | 5.11.2–5.11.5.2, 5.12.3 | Flat-web shear and bending interaction with the calculated flange-restraint factor. The clause route requires verified absence of longitudinal web stiffeners; section geometry and web count must be supplied. |
| `shear_with_rational_flange_restraint` | 5.11.2–5.11.5.2(c), 5.12.3 | Flat-web shear and bending interaction using externally calculated `alpha_f`. Requires a referenced, verified rational buckling analysis, no longitudinal stiffeners, transverse stiffener spacing `s/dp <= 3`, and no tension-field credit. The plugin records but does not authenticate or perform the analysis. |
| `chs_shear` | 5.11.3–5.11.4, 5.12.3 | Circular hollow section shear-yield capacity with the specified gross/net effective-area rule and whole-section shear/bending interaction. Requires supplied gross/net area and section moment capacity. |
| `shear_proportioning` | 5.12.2 | Flange-only bending capacity with separate web shear capacity, using the effective compression-flange area and the net-area/tensile-strength limit for the tension flange. |
| `interaction` | 8.3.2–8.3.4, 8.4.2, 8.4.4–8.4.5 | General linear section interaction; optional Clause 8.3.2(a) compact-section major-axis reduction for tension or verified compression with `kf=1.0`, or 8.3.2(b) for verified compression with `kf<1.0` using the calculated web slenderness and Table 6.2.4 limit; Clause 8.3.3(a)/(b) minor-axis reduction for compact doubly symmetric I or RHS/SHS sections and powered Clause 8.3.4 section interaction; elastic in-plane/out-of-plane compression-tension reduction and biaxial member interaction. Section and member checks are reported separately. |
| `tension_distribution` | 7.3.1–7.3.2 and Table 7.3.2 | Checks supplied connection capacities for the uniform and both-flange routes and looks up a selected Table 7.3.2 case (a)–(g), including the unequal-angle short-leg condition for cases (a)/(b). A failed capacity check returns no usable `kt` factor. Verify the selected table diagram and Clause 7.3.1 symmetry/connection conditions independently. |

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
  limited to inputs where the supplied flange and gross-web areas make up the gross section.
  Derived net moduli support only verified sharp-corner symmetric I-sections and RHS/SHS with
  major-axis bending, flange-only holes and a net hole layout that preserves the principal axis;
  other axes and net-section geometries still require independently established net moduli.
- 5.3–5.5: restraint stiffness/strength, critical flange/section, continuity and load position.
- 5.6.1.1(b)(iii) elastic buckling-analysis alternative and calculation of the elastic
  buckling moment under 5.6.2(ii)/5.6.4 still require independently verified analysis inputs.
  Table 5.6.1 and the 5.6.1.1(a)(iii) moment factor are in `advanced_members`, with both-end
  restraint and diagram applicability assessed externally. Unequal-flange I-section buckling
  under 5.6.1.2 and selected varying-section methods under 5.6.1.1(b)(i)–(ii) are also
  available; 5.6.3 effective-length factors are available there for selected cases.
- 5.7.1–5.7.2 require rational analysis to establish principal-axis moments and restraint
  forces. `advanced_members.nonprincipal_bending` applies the 8.3.4 section interaction and,
  when deflections are unconstrained, the 8.4.5 biaxial member interaction to those supplied
  results. Rational analysis itself remains external. Rational web configuration and opening
  resistance remain outside the selected 5.10 geometry, thickness and transfer checks.
- Rational flange-restraint buckling analysis itself remains external and is not authenticated;
  longitudinal-stiffener cases remain unsupported.
- The 5.12.2 flange-only proportioning check is available through `shear_proportioning`;
  5.12.3 whole-section interaction is available through `shear` and `chs_shear` for their
  supported section forms. Other applicable forms still require separate review.
- 5.13–5.16 bearing/stiffener design: handled separately where available, never implied
  by a passing shear check.
- 6.3.3 torsional-flexural buckling cases requiring AS/NZS 4600; 6.3.4 varying sections;
  6.4 laced/battened members; 6.5 back-to-back members; 6.6 restraint systems.
- 7.4 built-up tension-member connection/spacing requirements; automatic identification of the
  Table 7.3.2 diagram and Clause 7.3.1 symmetry/connection-layout conditions. Pin-member 7.1–7.2
  capacity/required-area and 7.5 geometry checks are available in `advanced_members`, but require
  assessed gross/net section areas, a verified Clause 7.3 factor, complete beyond-hole plane
  enumeration, and the Clause 7.5(d) load-transfer assessment; pin resistance is checked separately
  under 9.4. For the uniform route, the caller must enumerate every member part and supply its
  maximum design force and connection design capacity. For the both-flange route, the caller must
  supply verified design capacities for each flange connection and the maximum member force.
- 8.3.2(a)/(b), 8.3.3(a)/(b) and the powered 8.3.4 alternative are available for verified
  compact doubly symmetric I or RHS/SHS sections. The 8.3.2(b) route calculates web
  slenderness from supplied clear width, thickness and yield strength, then selects the
  Table 6.2.4 limit from the supplied residual-stress category. Compactness of the remaining
  section elements and consistency of the supplied form factor with Clause 6.2 capacities
  remain assessed inputs. 8.4.3 plastic-analysis eligibility/hinge checks, 8.4.6
  eccentric angle design, and other compact-section paths remain outside this operation.
- Annex H section-constant generation and rational elastic buckling calculations. Section
  properties and effective lengths need an independently verified source.

These are explicit prerequisites or unsupported paths, not evidence of full AS 4100 design.
For a complete project assessment, each applicable item must have a implemented and verified
calculation or a recorded engineering assessment; applicability is never assumed from a pass.

## Verification

Tests use independent hand arithmetic for hole-adjusted section moduli, effective moduli/widths,
moment/shear capacities,
combined action reductions and boundary cases. Compression reduction is checked against
Table 6.3.3(C) at multiple slenderness and imperfection values, including the complete
Amendment No. 1 corrected row at modified slenderness 20 and both ends of the table.
Stiffened shear is checked against Table 5.11.5.2. The table comparisons allow only
the published rounding difference. Additional tests check monotonic reductions, both axes,
unsupported geometries, inconsistent dimensions, nonfinite values and exceeded capacities.

This is numerical verification of implemented primitives, not independent engineering
certification or evidence that every applicable provision of the standard is satisfied.
