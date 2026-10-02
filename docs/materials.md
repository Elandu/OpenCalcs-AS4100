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
The plugin does not derive `ZEd` or interpret Appendix M's weld-layout diagrams.

For material thicker than 16 mm, a `ZEd` value of 10 or less requires no Z
quality class. Otherwise, the required class is Z15 for `ZEd` 11–20, Z25 for
21–30, and Z35 above 30. The operation compares the available class and requires
a verified material-certificate reference when a class is required. A stronger
class satisfies a lower threshold. For material 16 mm or thinner, Clause 2.2.5
does not require Z-quality steel, regardless of the supplied `ZEd`.

Certificate and Appendix M references are recorded but not authenticated. A
passing result covers only this comparison. Clause 3.8 still requires assessment
of joint geometry, through-thickness stresses, restraint, welding and detailing;
the calculation does not establish that lamellar tearing has been avoided.

Table-value regressions exercise product/form/grade combinations and thickness
breakpoints. This is a strength lookup, not material certification.
