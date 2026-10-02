# Testing and suggested serviceability limits

Source review: AS 4100:2020, printed pages 180–183 and 185, visually reviewed.
The supplied edition contains clauses 16.1 and 16.2, followed by Section 17;
there are no clauses 16.3 or 16.4 in this source. No scanned pages are packaged.

`run_testing` accepts a tagged, strict input object and returns results with
clause identifiers and warnings. Declared test conditions require supporting
records. Numerical acceptance does not issue a test certificate.

- `proof_strength`: test action equals the supplied strength-limit-state design
  action, sustained for at least 15 minutes; damage inspection, review/repairs,
  load/measurement conditions and reporting must be declared complete.
- `prototype_strength`: Table 17.5.2 strength factors for 1, 2, 3, 4, 5 or 10
  similar units and a minimum five-minute dwell. Representative fabrication,
  materials and erection, and production similarity, are required declarations.
- `proof_serviceability` and `prototype_serviceability`: required test action
  and measured maximum deformation against an explicitly supplied applicable
  limit. Prototype serviceability factors follow Table 17.5.2.
- All test operations require calibrated loading without artificial restraint,
  representative distribution/duration, deformation readings before loading,
  under loading and after unloading, and a complete report under 17.6.
- `existing_material_audit`: prerequisite review of metal identification and
  evidence before modification or repair. It does not assume material grades
  or supply invented acceptance criteria for unidentified steel. Section 16.2
  requires base-metal identification; it does not give a numerical test method.
- `suggested_vertical_limit`: Table B.1 total beam deflection or deflection
  after masonry partition attachment, explicit movement provision and
  span/cantilever selection. Cantilever calculations must include support rotation.
- `suggested_portal_horizontal_limit`: Appendix B.2 industrial portal frames
  under serviceability wind, with the stated steel/aluminium or externally
  supported masonry cladding and no ceilings/internal partitions against external
  walls. Relative inter-frame and absolute-frame limits use distinct reference
  dimensions. Combined masonry/gantry-crane cases require a project-specific limit.

Loads are represented by a scalar equivalent test action in kN; actual load
patterns, combinations, restraint, calibration and force distribution remain
the test engineer's responsibility. Design actions must be supplied from clause
3.2.3. Values at or above required action are accepted by the numerical comparison
only when the other required evidence is declared; this does not authorise a
different loading protocol. Prototype counts absent from the table are rejected
without interpolation or invented factors. Reduced factors from reliability
analysis are outside these operations.

Appendix B is informative: its limits are suggestions rather than universal
serviceability acceptance requirements, and they may not safeguard against
ponding. Actual project, equipment, cladding and applicable loading-standard
requirements must be selected separately.

Tests verify table cells, load/dwell/deformation boundaries, evidence gates,
deflection scope and schema/numerical domains using independent arithmetic.
Physical test execution and report authenticity are not verified by software.
