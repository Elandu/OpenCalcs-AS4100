# Material strength lookup

Calculation `structural.as4100.materials` implements all listed structural steel
rows of Table 2.1. It requires the product standard, material form, certified
grade and thickness. It returns the tabulated yield stress and tensile strength
with clauses 2.1.1 and 2.1.2.

Welded I-sections in accordance with AS/NZS 3679.2 use the parent plate-grade
strengths from AS/NZS 3678, as directed by the Table 2.1 note. Supply the parent
plate grade and governing plate thickness.

The lookup does not establish that a certificate belongs to the member, select a
grade, interpolate thicknesses or accept a product form absent from Table 2.1.
Confirm impact designation and product standard notes. Clauses 2.2–2.5 still
govern structural steel specification, alternative materials, steel toughness,
bolting, welding and lamellar tearing. Heat treatment and actual material
condition need separate assessment. Welded I-sections use the parent plate
strength provisions stated in Table 2.1.

## Design properties

Operation `design_properties` returns the Clause 2.2.4 values for steel:
`E = 200 000 MPa`, `G = 80 000 MPa`, Poisson's ratio `0.25` and thermal
expansion coefficient `11.7 × 10⁻⁶ /°C`. Member buckling and fire-modulus
calculations use these same base properties; their inputs reject conflicting
elastic modulus or Poisson values.

## Steel castings

Operation steel_casting_conformity records the casting grade, a reference to
the conformity evidence, and whether the supplied assessment confirms the
Clause 2.4 requirement that steel castings conform to AS 2074. It reports the
declaration as a check and leaves full_standard_compliance false.

The calculation does not authenticate the reference or determine whether the
grade and material properties conform to AS 2074. Verify the certificate,
casting identity and properties independently. This operation does not calculate
design strengths; use independently established AS 2074 properties in the
member and connection checks.

## Fastener product conformity

Operation `fastener_product_conformity` records a Clause 2.3.1 fastener item or
assembly identifier, its declared product standard, the user's applicability
assessment and a conformity-certificate reference. It checks the listed product
standard against the declared component category: AS 1110 or AS 1111 for bolts
and screws, AS 1112 for nuts, AS 1237.1 for washers, AS/NZS 1252.1 for high-
strength bolting assemblies, and AS/NZS 1559 for galvanized tower bolting
assemblies.

The operation does not authenticate the item, certificate or test report, or
decide whether a standard is suitable for a project. Verify the applicable
certificate and test-report requirements and any laboratory qualification
requirements separately. AS/NZS 1559 is specific to tower construction and may
not suit every structure. Clause 2.3.2 equivalent high-strength fasteners are
checked separately.

## Unidentified steel

Operation `unidentified_steel` implements the strength limits in Clause 2.2.3.
Without a full test to AS 1391, supplied design yield and tensile strengths are
compared with 170 MPa and 300 MPa, respectively. The operation reports a failed
check when either supplied value exceeds its limit; it does not silently lower
the input strength.

The alternate full-test route requires a report reference and an explicit
attestation that testing meets AS 1391. Both routes also require attestations
that the steel is free from surface imperfections and that its physical
properties and weldability will not adversely affect strength or serviceability.
The operation cannot authenticate those attestations or the report, and it does
not assess other applicable requirements of Section 2.

## Through-thickness deformation and lamellar tearing

Operation `through_thickness_deformation` checks the Clause 2.2.5 Z-quality
class and thickness requirements for AS/NZS 3678 plate. For plate thicker than
16 mm, supply the required design Z-value (`ZEd`) from an external Clause 3.8 /
Appendix M assessment, identify its reference and mark it verified. For plate
16 mm or thinner, the `ZEd` input may be omitted because the thickness exemption
applies.

Operation `appendix_m_through_thickness_design` calculates the Table M.2 terms
`Za` through `Ze`, sums them to `ZEd`, and applies the same Clause 2.2.5 material
class check. Supply the effective weld depth `S` shown in Figure M.2, the Table
M.2(b) weld-form/sequence case, the plate thickness, remote restraint and
preheating category. The `verified_applicable` compression basis applies the
Table M.2 footnote's 50% reduction to `Zc` only; assess whether the material is
stressed in through-thickness compression due to predominantly static loads.

The operation does not infer `S` from a drawing or decide which diagrammed
Table M.2(b) case applies. Verify the effective depth, weld form and sequence,
restraint, preheating and compression-reduction classifications from project
evidence before selecting them. The supported `table_m2_b_case` values map to
`Zb` as follows: `t_cruciform_or_corner_diagram_group` = -25;
`corner_joint_diagram_group_1` = -10; `single_run_fillet_with_z_a_zero` = -5;
`fillet_welds_butting_low_strength_material` = -5; `multi_run_fillet` = 0;
`penetration_weld_with_shrinkage_reducing_sequence` = 3;
`penetration_weld_without_shrinkage_reducing_sequence` = 5; and
`corner_joint_diagram_group_2` = 8. Match the joint geometry and sequence to the
figures and descriptions in Table M.2(b). Appendix M is informative guidance.
The single-run case is accepted only when calculated `Za` is zero. The alternate
butting-fillet case is accepted only when `Za` is greater than 1 and a verified
low-strength weld-material reference is supplied. This reference is recorded,
not authenticated; the calculation does not decide whether a weld material is
low strength.

For material thicker than 16 mm, a `ZEd` value of 10 or less requires no Z
quality class. Otherwise, the required class is Z15 for `ZEd` 11–20, Z25 for
21–30, and Z35 above 30. The operation compares the available class and requires
a verified material-certificate reference when a class is required. A stronger
class satisfies a lower threshold. For material 16 mm or thinner, Clause 2.2.5
does not require Z-quality steel, regardless of the supplied `ZEd`.

Certificate references and Table M.2 classifications are recorded but not
authenticated. A passing result covers only the calculated table terms and the
Clause 2.2.5 class comparison. Clause 3.8 still requires assessment of joint
geometry, through-thickness stresses, restraint, welding and detailing; the
calculation does not establish that lamellar tearing has been avoided.

Table-value regressions exercise product/form/grade combinations and thickness
breakpoints. This is a strength lookup, not material certification.
