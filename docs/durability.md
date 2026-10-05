# Durability, fire and earthquake operations

`run_durability` accepts a strictly validated `check_type` and the matching
operation inputs. Units are MPa, mm, degrees Celsius, minutes and m²/tonne
where named. The source was visually reviewed in the supplied AS 4100:2020
standard, printed pages 139–169 and 171–173. Its scanned source, extracts and
page images are not included in this package.

## Supported numerical checks

- `hollow_section_truss_stress_range`: Table 11.3.1(A)/(B) factors for gap/overlap
  CHS and RHS K/N joints, selected by chord/vertical/diagonal member role.
  Multiplies a supplied unadjusted member stress range and checks the Clause
  11.3.1(c) requirement that fillet-weld design throat exceed connected-member
  wall thickness. The member stress analysis, fatigue category, cycle spectrum,
  joint applicability and connection resistance remain separate checks.
- `fatigue_hollow_section_detail`: detail categories for all entries (43)–(50) in
  Table 11.5.1(D), including the 8 mm wall-thickness divisions and the 100 mm
  non-load-carrying attachment-width limit. Supply the numbered detail and CHS/RHS
  form. Detail conditions, stress direction and weld quality need verified drawing
  or fabrication references; detail (43) also requires the continuous automatic
  weld/no-stop-start condition and detail (48) the non-load-carrying condition.
  Categories 112 and below require referenced Category SP weld-quality evidence
  under AS/NZS 1554.1 or 1554.4, as applicable.
  This lookup reports a normal-stress detail category only. It does not verify the
  physical detail or replace the separate fatigue strength and service-spectrum checks.
- `fatigue_group1_detail`: Table 11.5.1(A) details (1)–(7), including the
  8.8/TF gross-section versus other-bolting net-section stress basis and required
  edge preparation/eccentricity evidence. Supply verified fabrication and stress-
  direction references. For one-sided coverplates, the eccentricity effect must be
  included in the separately calculated stress range.
- `fatigue_bolt_detail`: Table 11.5.1(C) details (41) and (42). Detail (41) is
  limited to 8.8/TB shear bolts and identifies the minor-diameter stress area; a
  referenced slip assessment records whether bolt shear needs fatigue assessment.
  Detail (42) identifies the tensile-stress area for bolts or rods in tension and
  requires a referenced assessment that includes prying effects. Bolt force ranges
  and stress ranges are not calculated by this category lookup.
- `fatigue_welded_detail`: every Table 11.5.1(B) entry (8)–(40), including its
  geometry-dependent category boundaries, stress type and stress-area basis.
  Category 125 requires referenced weld quality to AS/NZS 1554.5; categories 112
  and below require referenced Category SP weld-quality evidence to AS/NZS 1554.1
  or 1554.4, as applicable. Detail 36 requires principal stress range for combined
  web bending and shear. Detail 20 is Category 90 without a cope hole and Category
  71 with a cope hole verified as unfilled. Details 23 and 24 accept a backing-strip
  weld end exactly 10 mm from the stressed-plate edge; Detail 25 applies at 10 mm
  or less. Detail identity, weld examination, geometry and force hierarchy still
  require drawing and fabrication review.
- `fatigue_constant`: normal stress S–N slopes 3/5 and shear slope 5
  (11.6), explicit thickness correction (11.1.6), capacity factor (11.1.5),
  stress limits (11.1.3), exemption below the normal constant-amplitude limit
  (11.7), utilisation (11.8.1), and punching thickness limit (11.9).
  Cycle count is positive and no greater than 10⁸. Detail category is an
  explicitly assessed input; no automatic category is selected from drawings.
  Supported normal curve categories are 36, 40, 41, 45, 50, 56, 63, 71, 80,
  90, 100, 112, 125, 140, 160 and 180 MPa; shear categories are 80 and 100 MPa.
  A stress range incompatible with the declared maximum stress magnitude is rejected.
- `fatigue_variable`: per-event and total damage using both normal branches
  or the shear branch (11.8.2). Events below the corrected design cutoff
  contribute zero. Events exactly on cutoff contribute damage. The normal
  further-assessment exemption is returned separately from calculated damage.
  Stress-range extraction and rainflow counting remain external.
- `fatigue_exemption`: both normal and shear ranges must satisfy the strict
  inequalities in 11.4. This is a fatigue exemption, not a strength check.
- `fire_material`: yield reduction through 905°C and E/G reduction through
  that temperature (12.4.1–12.4.2). `fire_modulus` extends the E/G equations
  through 1000°C. The lower domain is strictly greater than 0°C.
- `fire_limiting_temperature`: 12.5, with supplied fire action ratio between
  zero and one. The denominator is room-temperature **member** design
  capacity, not a section-only value where buckling governs.
- `fire_unprotected`: 12.7 three/four-sided equations for 500–750°C,
  with linear interpolation from time zero at 20°C below 500°C. Surface
  area/mass ratio is restricted to 2–35 m²/tonne. Returns PSA and FRL comparison.
- `fire_single_test`: the applicability conditions of 12.8 and comparison
  of supplied prototype PSA with required FRL. AS 1530.4 evidence, same
  protection/exposure/support conditions and no worse restraint must be assessed.
- `fire_single_test_history`: 12.6.1 and 12.6.3 single-test route using the
  representative measured steel-temperature history. Checks matching protection
  system/exposure, protection thickness, surface-area/mass ratio and stickability
  for an unloaded prototype; estimates the first limiting-temperature crossing
  by linear interpolation between readings. A test that has not reached the limit
  provides only a duration lower bound.
- `web_penetration_protection`: 12.10.2 greatest required thickness from the
  above-opening, below-opening and whole-section zones, full-depth coverage and
  minimum extension each side of max(beam depth, 300 mm).
- `concentric_brace_yielding_connection`: Clause 13.3.5(b) comparison of each
  supplied connection capacity with the full design capacity of its diagonal brace
  member expected to yield. Verify the limited-ductility system, yielding-brace
  selection and compatible governing action capacities.
- `concentric_tension_brace`: 13.3.6.2(a) limit of 0.85 times member design
  tensile capacity and connection capacity for the full member design capacity.
  System applicability and both design capacities are supplied verified inputs.
- `intermediate_moment_frame_stiffeners`: Clause 13.3.6.3(b) full-depth web-
  stiffener fit and butt welding to both flanges. Verify frame applicability and
  every relevant beam-to-column stiffener against drawings and inspection records.
- `seismic_plastic_region_fabrication`: Clause 13.3.6.4(a) sheared-edge treatment
  and gas-cut roughness (12 μm maximum), plus 13.3.6.4(b) fastener-hole making
  method. Confirm moderate-ductility applicability and that all plastic-deformation
  regions and fabrication records are included.
- `concentric_brace_connection_detailing`: checks reported beam-to-column web
  stiffeners against 13.3.6.2(b), and each weld group's SP category plus Table
  13.3.6.2 inspection percentages under 13.3.6.2(c). Welds must be grouped as
  butt welds in tension, other butt welds, or all other welds. Supply coverage
  percentages from inspection records; completeness, weld classification and
  AS/NZS 1554.1 compliance remain externally verified.
- `fire_protected_regression_fit`: least-squares fit of the seven coefficients
  in 12.6.2.2 from measured temperature/time observations for at least nine
  qualifying fire tests. The fit rejects rank-deficient test data, unloaded
  prototypes without demonstrated stickability, low-density insulation at or
  above 1000 kg/m³, and three-sided series without declared Clause 12.9 group
  qualification. For intumescent or ablative coatings, the calculated
  coefficient of correlation must exceed 0.9. It reports the convex hull of the
  measured protection-thickness/surface-area-to-mass geometries as the
  interpolation window, measured test-temperature range, protection-material
  category and calibration exposure.
- `fire_three_sided_group`: Clause 12.9 limits on group variation. Computes
  effective concrete thickness as concrete cross-sectional area excluding
  voids divided by tributary width, compares the maximum/minimum concrete
  density and effective thickness ratios with 1.25, and requires rib voids to
  be consistently absent, open or blocked. A protected regression fit for a
  three-sided series can include the same group-member data to calculate this
  prerequisite directly.
- `fire_connection_protection`: Clause 12.10.1 maximum protection thickness
  across all framing members at a connection, applied over each identified
  component. Checks that the supplied thickness is maintained over bolt heads,
  welds, splice plates and other listed components.
- `fire_protected_regression`: evaluate the fitted seven-coefficient relation
  of 12.6.2.2 above 250°C. Supply `interpolation_window_points` and
  `test_temperature_range_c` from the fit to have the operation calculate
  whether the target geometry lies inside the convex test-data window and the
  target temperature lies within the measured range. Include
  `application_conditions` to check Clause 12.6.2.3 reuse: a different system
  must use the same protection material and demonstrate stickability; a
  four-sided calibration may be applied to a three-sided member only with
  demonstrated stickability and a qualifying target group; a three-sided
  calibration cannot qualify a four-sided member. The older
  `inside_reviewed_interpolation_window` declaration remains accepted when no
  geometry points are supplied; that path depends on an external review and
  cannot check geometry, temperature or application conditions itself.
- `brittle_fracture`: Table 10.4.1 steel-type/thickness temperature lookup,
  specified impact-test-temperature adjustment, outer-fibre-strain temperature
  increase and eligible post-weld heat-treatment exception (10.4.3). The
  permissible temperature must be **less** than the supplied design service
  temperature (10.4.1), and fabrication/erection requirements must be confirmed.
  Unavailable table cells fail explicitly. No geographic climate mapping or
  automatic grade-to-steel-type selection is performed.
- `nonconforming_steel_impact_test`: For steel whose Table 10.4.1 permissible
  temperature is unknown or warmer than design, Clause 10.4.3.4(d) checks the
  27 J mean and 20 J individual Charpy energy limits for grades whose product
  standard specifies no impact-energy minimum. Clause 10.4.3.4(e) scales both limits by
  the verified specimen thickness divided by 10 mm for a sub-size specimen.
  Mock-up, sample-location, test-temperature and specimen-selection conditions
  are evidence gates; verify them against the laboratory and fabrication records.
  The calculation assumes a 10 mm specimen width and does not apply the
  grade-standard-minimum route below.
- `specified_impact_properties_test`: For grades whose product standard specifies
  minimum Charpy energy properties, Clause 10.4.3.4(a)–(c) compares the measured
  three-specimen average and, when specified, the minimum individual result with
  supplied product-standard limits. It applies Clause 10.4.3.4(e) proportional
  sub-size reduction to each supplied limit. Mock-up similarity, the maximum-
  strain specimen location, test temperature, grade-standard minima and
  specimen-size selection are evidence gates. Supply at least one specified
  average or individual energy limit; the operation does not derive grade
  minima or authenticate the referenced records. It assumes a 10 mm specimen
  width.
- `design_service_temperature`: Clause 10.3.2 applies the 5 °C reduction for
  verified exceptionally low local ambient conditions and selects a verified
  colder record temperature for critical structures. Clause 10.3.3 uses the
  supplied minimum expected part temperature when verified artificial cooling
  takes the part below the basic design temperature. Supply LODMAT from Figure
  10.3.2 within its 0 °C to 20 °C isotherm range, and verify location, climate
  records and cooling conditions externally; this operation does not determine
  those source values.
- `earthquake_audit`: Table 13.3.4 ductility/performance factors, minimum panel
  movement, grade yield limit for limited/moderate ductility, and an explicit
  manual-review result. Fully ductile design is identified as requiring
  NZS 1170.5/NZS 3404 rather than treated as AS 4100 design approval.

## Engineering prerequisites and outstanding coverage

Fatigue detail assignment requires all illustrated-detail conditions, stress
directions, weld quality, stress concentrations and dynamic service loading.
The inputs must already include those effects. Corrosion/immersion degradation,
low-cycle fatigue, thermal fatigue and stress corrosion are outside Section 11.
The minimum acceptable reduced fatigue factor for non-reference conditions is
an engineering selection; a non-redundant path is limited to factor 0.70.

Fire results apply to the standard fire and must be combined with the actual
member/connection design. Regression fitting uses declared test-system and
exposure checks and supplied AS 1530.4 observations. Clause 12.9 group ratios
can be calculated from supplied densities, cross-sectional concrete areas,
tributary widths and rib-void conditions; those source measurements and test
reports are not authenticated. Applying a regression to another protection
system requires the same protection material, matching fire exposure and
demonstrated stickability. Applying a four-sided calibration to a three-sided
member requires demonstrated stickability and a qualifying target group.
Verify those declarations against test reports and protection-system records.
Clause 12.10.1
compares supplied member thicknesses against listed connection components;
verify the component list, required protection evidence and continuity from
drawings and installation records. Fire-test/group qualification of the
thicknesses used for 12.10.2 still requires separate assessed evidence. No protection material
database or proprietary test certificates are supplied. The room-temperature
yield strength must remain in the slenderness expressions identified in 12.4.3.

Brittle-fracture design service temperature uses the separate
`design_service_temperature` operation for the calculated 10.3.2-10.3.3 routes;
the LODMAT source, location, record assessment and cooling minimum remain
externally verified. Product certification, grade/type mapping
(Table 10.4.4), applicable fabrication provisions, non-conforming-condition
Charpy evidence and fracture-mechanics assessment (10.5) remain external.

Earthquake audit does not verify AS 1170.4 force/category assignment, load paths,
stiff elements, connection deformation, brace overstrength, stiffeners, weld
examination, plastic-hinge detailing or fabrication workmanship. These are
listed for manual review rather than represented as automatically passed.

The numerical tests use independent arithmetic constants and boundary examples;
synthetic protected-regression coefficients test evaluation only and are not a
qualifying protection system. Passing tests does not establish complete AS 4100
implementation or project design compliance.
