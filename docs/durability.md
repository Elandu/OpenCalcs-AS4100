# Durability, fire and earthquake operations

`run_durability` accepts a strictly validated `check_type` and the matching
operation inputs. Units are MPa, mm, degrees Celsius, minutes and m²/tonne
where named. The source was visually reviewed in the supplied AS 4100:2020
standard, printed pages 139–169 and 171–173. Its scanned source, extracts and
page images are not included in this package.

## Supported numerical checks

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
- `fire_protected_regression`: evaluate the seven-coefficient relation of
  12.6.2.2 with supplied, externally fitted coefficients. Requires at least nine
  tests, temperature above 250°C and explicit declarations that 12.6.2.3
  conditions and the interpolation window are satisfied. This does not fit
  coefficients, prove test adequacy, or extrapolate to a new protection product.
- `brittle_fracture`: Table 10.4.1 steel-type/thickness temperature lookup,
  specified impact-test-temperature adjustment, outer-fibre-strain temperature
  increase and eligible post-weld heat-treatment exception (10.4.3). The
  permissible temperature must be **less** than the supplied design service
  temperature (10.4.1), and fabrication/erection requirements must be confirmed.
  Unavailable table cells fail explicitly. No geographic climate mapping or
  automatic grade-to-steel-type selection is performed.
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
member/connection design. Protected temperature-history interpolation of
12.6.3, regression fitting and automatic convex-window validation, three-sided
group qualification in 12.9, connection protection and web penetration
protection in 12.10 require separate assessed evidence. No protection material
database or proprietary test certificates are supplied. The room-temperature
yield strength must remain in the slenderness expressions identified in 12.4.3.

Brittle-fracture design service temperature requires climate/erection/artificial
cooling assessment under 10.3. Product certification, grade/type mapping
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
