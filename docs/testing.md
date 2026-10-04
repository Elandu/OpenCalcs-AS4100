# Testing and suggested serviceability limits

Source review: AS 4100:2020, printed pages 181–183 and 185, visually reviewed.
The supplied edition contains clauses 16.1 and 16.2, followed by Section 17;
there are no clauses 16.3 or 16.4 in this source. No scanned pages are packaged.

`run_testing` accepts a tagged, strict input object and returns results with
clause identifiers and warnings. Declared test conditions require supporting
records. Numerical acceptance does not issue a test certificate.

- `test_scope_applicability`: checks the Section 17.1.1–17.2 scope and proof /
  prototype purpose declarations. Structural models and tests intended to
  establish general design criteria or data are outside the scope. Reports
  when a standard-compliant design is not required to be tested, while retaining
  alternative-to-calculation and special-circumstance routes for review.

- `proof_strength`: test action equals the supplied strength-limit-state design
  action, sustained for at least 15 minutes; damage inspection, review/repairs,
  load/measurement conditions and reporting must be declared complete.
- `prototype_strength`: Table 17.5.2 strength factors for 1, 2, 3, 4, 5 or 10
  similar units and a minimum five-minute dwell. Material compliance with
  Section 2, fabrication compliance with Section 14, manufacturing-specification
  compliance, production-like erection and production-unit similarity are
  separately declared under 17.5.1 and 17.5.4.
- `proof_serviceability` and `prototype_serviceability`: required test action
  and measured maximum deformation against an explicitly supplied applicable
  limit. Prototype serviceability factors follow Table 17.5.2.
- All test operations require calibrated loading without artificial restraint,
  a loading rate as uniform as practicable, representative distribution/duration,
  deformation readings before loading,
  under loading and after unloading, recorded loading and deflection-measurement
  methods, other relevant test data, an acceptance statement and a complete
  report under 17.6.
- `existing_structure_modification_review`: Clause 16.1 declaration that other
  AS 4100 provisions were applied unless modified by Section 16, plus separate
  AS/NZS 5131 declarations for applicable erection-stage site changes and
  existing-structure modification/repair. For Clause 16.2 it checks that base-
  metal types were determined before strengthening, repair or welding documents
  were prepared. These gates need supporting records and do not reanalyse the
  structure or assess material-test results.
- `existing_material_audit`: supplementary review of metal-identification and
  test evidence before modification or repair. It does not assume material
  grades or supply acceptance criteria for unidentified steel.
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
3.2.3. The entered test action must equal the prescribed design action, including
the applicable prototype factor; an over- or under-load does not pass this check.
This numerical condition does not replace the physical loading protocol.
Prototype counts absent from the table are rejected
without interpolation or invented factors. Reduced factors from reliability
analysis are outside these operations.

Appendix B is informative: its limits are suggestions rather than universal
serviceability acceptance requirements, and they may not safeguard against
ponding. Actual project, equipment, cladding and applicable loading-standard
requirements must be selected separately.

Tests verify table cells, load/dwell/deformation boundaries, evidence gates,
deflection scope and schema/numerical domains using independent arithmetic.
Physical test execution and report authenticity are not verified by software.
