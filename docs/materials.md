# Material strength lookup

Calculation `structural.as4100.materials` implements the listed structural steel
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

Table-value regressions exercise product/form/grade combinations and thickness
breakpoints. This is a strength lookup, not material certification.
