# Fabrication hole checks

The `structural.as4100.fabrication` family implements selected hole-size and
use checks from AS 4100:2020 Clause 14.3.2. It evaluates one declared hole per
call through the `bolt_hole` operation. Inputs are millimetres. This operation
does not determine whether a hole or connection arrangement is appropriate for
the design.

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

The input schemas require confirmation that an oversize or slotted hole is not
a base-plate anchor hole, the connection type and whether shear acts. They also
require side-specific washer/product declarations. Evidence flags are supplied
assertions; the software does not authenticate drawings, measurements, material
certificates, installation or load paths. `full_standard_compliance` remains
false. Clause 14.3.2 is one
limited part of Section 14; material identification, welding/fabrication
procedures, other fabrication requirements and Clause 14.4 tolerances remain
outside this family.
