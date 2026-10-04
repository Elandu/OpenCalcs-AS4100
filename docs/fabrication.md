# Fabrication hole checks

The `structural.as4100.fabrication` family implements selected checks from AS
4100:2020 Clauses 14.1, 14.2.2, 14.3.1–14.3.3 and 14.4. Its operations evaluate one
declared fabrication basis, hole, bolt assembly, tolerance or acceptance route
per call. Dimensional inputs are millimetres. These operations do not determine
whether a hole or connection arrangement is appropriate for the design.

The `fabricated_item_acceptance` operation applies the Clause 14.1 routes. A
fabricated item may be accepted when the declared material, fabrication and
tolerance requirements are all satisfied, or when a declared demonstration
shows that structural adequacy and intended use are unimpaired, or a declared
Section 17 test has passed. If none of these routes applies, the result marks
rejection as required. It records the supplied conditions and does not make an
acceptance decision.

Set `hole_type` to one of `standard`, `base_plate_anchor`, `oversize`,
`short_slot` or `long_slot`:

- Standard round holes are checked against the Clause 14.3.2 clearance for
  nominal bolts up to and including 24 mm, and the maximum clearance for larger
  bolts.
- Base-plate anchor holes are limited to the anchor diameter plus 6 mm. At a
  diameter at least 3 mm larger than the anchor, provide the measured special
  plate-washer thickness and minimum hole-edge clearance under the nut; the
  check requires at least 4 mm thickness and clearance of half the hole
  diameter.
- Oversize round holes are limited to the greater of 1.25 times the bolt
  diameter and bolt diameter plus 8 mm.
- Short slots are limited to the applicable hole clearance in width and the
  greater of 1.33 times the bolt diameter and bolt diameter plus 10 mm in
  length. Long slots use the same width limit and are limited to 2.5 times the
  bolt diameter in total length.
- Oversize holes and slots require washer declarations for the head and nut
  sides that would otherwise bear on the ply containing the hole. Hardened or
  plate washers are accepted for oversize and short-slot holes. Plate washers
  must have verified coverage, the required edge clearance, and material
  verified to AS/NZS 3678. Long slots require plate washers at least 8 mm thick
  at each applicable bearing surface. The supplied edge-clearance measurement
  is compared with half the hole diameter, represented for a slot by its
  width.
- Long slots require a verified alternate-ply arrangement. For a bearing-type
  connection subject to shear, short and long slots require verified absence of
  eccentric loading, uniform bolt bearing and slot orientation normal to the
  design action. Friction-type connections subject to shear have no slot
  direction restriction under this check.

The `fabrication_basis` operation checks referenced material-standard
conformity and surface-defect removal under Clause 14.2.1, grade identification
and non-damaging marking under Clause 14.2.2, and AS/NZS 5131 fabrication and
material-property preservation declarations under Clause 14.3.1. If steel is
classified as unidentified, it calls the Clause 2.2.3 calculation using the
supplied operation inputs.

The `bolt_assembly` operation covers selected Clause 14.3.3.1–14.3.3.4
conditions: verified bolt/nut/washer material conformity, steel within the
bolt grip, at least one clear thread above the nut and thread plus runout clear
beneath it, a washer beneath the rotated part, and vibration securing. It
compares the declared maximum contact-surface slope ratio with 1:20 and, above
that limit, requires evidence of the tapered-washer arrangement. Friction-type
connections require AS/NZS 5131 surface preparation and either clean as-rolled
or equivalent surfaces or an assessed Clause 9.2.3.2 route. Bearing-type
connections report that an applied finish is permitted. A fully tensioned
high-strength bolt installed during fabrication requires a Clause 15.2
installation declaration.

The `geometric_tolerance` operation checks a measured deviation against a
permissible AS/NZS 5131 value supplied with evidence. It requires the final
measurement after fabrication and corrosion protection and confirmation that
coating thickness was excluded. Functional tolerance Class 1 applies when no
class is supplied. A functional deviation outside its limit fails; an
essential deviation outside its limit passes only when its inclusion in a
revised design-capacity calculation is declared.

The input schemas require confirmation that an oversize or slotted hole is not
a base-plate anchor hole, the connection type and whether shear acts. They also
require side-specific washer/product declarations. Evidence flags are supplied
assertions; the software does not authenticate drawings, measurements, material
certificates, installation or load paths. `full_standard_compliance` remains
false. Material certification, detailed fabrication procedures, actual
construction records, other fabrication requirements and the numeric AS/NZS
5131 tolerance limits remain externally assessed.
