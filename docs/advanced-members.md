# Further member provisions

The `advanced_members` module supplies additional calculations reviewed directly from
AS 4100:2020 pages 61, 65–67, 69, 93–98, 101–102 and 107–112. The licensed document
is not included. `INPUT_SCHEMA`, `OUTPUT_SCHEMA` and `run_advanced_members` are exported.
Every result retains `full_standard_compliance: false` and lists its prerequisites.
Supplied capacities are nominal; strength checks apply phi=0.9.

| Operation | Calculated provisions | External prerequisites |
| --- | --- | --- |
| `varying_compression` | 6.3.4 minimum section capacity and equivalent modified slenderness, then 6.3.3 member reduction | Rational elastic flexural buckling load for actual variation; minimum assessed Ns; applicable section constant; repeat for both axes. |
| `buckling_analysis_bending` | 5.6.4 Moa=Mob/alpha_m and member moment reduction; 5.6.2(ii) unrestrained-end analysis method | Elastic flexural-torsional analysis representing actual restraints/loading. Unrestrained-end path requires opposite-end restraint/continuity and uses alpha_m=1. |
| `one_unrestrained_table_bending` | 5.6.1.1(1)–(3), 5.6.2(i), Table 5.6.2 moment factors and member moment capacity | One end must be restrained and laterally continuous or restrained against lateral rotation; other end unrestrained. Only uniform end moment (alpha_m=0.25), tip force (1.25), and uniform load (2.25) are represented. Supply verified Mo from 5.6.1.1(3); combined/different load cases and 5.6.2(ii) are outside this operation. |
| `lateral_buckling_effective_length` | 5.6.3 effective length from tabulated twist-restraint, gravity-load-height and end-rotation-restraint factors | Supply the applicable end arrangement, restraint spacing/sub-segment length and section dimensions; only listed gravity-load cases are supported. Effective rotation restraint needs assessment to 5.4.3.4. |
| `nonprincipal_bending` | 5.7 section interaction and, for unconstrained deflection, biaxial member interaction | Rational analysis supplies principal moments, restraint forces and reduced member capacities. |
| `plastic_in_plane` | 8.4.3 member/web plastic hinge eligibility and uniaxial reduced plastic moment capacity | Compact doubly symmetric I section, actual-length Euler load, correct beta_m, plastic frame analysis/restraint provisions. |
| `built_up_compression` | 6.4 design transverse shear; component slenderness; laced/battened effective slenderness; 6.5 connection shear and minimum bays | Assessed Ns/Nc/lambda_n, similar symmetric components; iterate Nc with calculated effective slenderness; equal bays/end connections and eligible packing/spacing. |
| `lacing` | 6.4.2 angle/effective-length/slenderness; tie width/thickness; 7.4.4 tensile lacing limit | Double-lacing crossing connection; tie placement and connection force transfer; component slenderness; torsional assessment for opposed lacing. |
| `batten` | 6.4.3 batten geometry/effective length/slenderness, simultaneous connection shear/moment; 7.4.5 thickness and intermediate width | End/component geometry, effective section properties, connection design; tension force distribution and two-bolt requirement. Compression connection force formulas return null for tension members. |
| `pin_tension_member` | 7.5 pin-hole member thickness and beyond-hole/perpendicular net area ratios | Separately assessed member net area, all potential beyond-hole directions, pin capacity under 9.4, eccentricity-free load distribution. |
| `restraint_action` | 5.4.3 minimum flange/twist restraint force; 6.6 compression restraint envelope; parallel-member accumulation up to seven members | Critical flange force/local compression, rational analysis including notional loads and full load path, stiffness/slip/anchor assessment. |
| `separator_diaphragm` | 5.8 minimum transverse force for separators/diaphragms and equal share per supplied device count | Verify side-by-side members act together, external force distribution, resulting shear and device capacities; separators are rejected where external vertical force transfer is required. |
| `angle_eccentricity` | Figure 8.4.6 eccentricity and minimum Nh moment | Loading/geometry as drawn; double-bolted or welded angle. No special angle interaction capacity is claimed. |

The scan's 8.4.6 interaction uses tensile terminology and `Mtx/Mry` while defining
compressive force, `Nch` and angle orientation; a corresponding reduction definition
is not apparent on pages 111–112. The implementation calculates only the clearly
specified eccentricity/moment requirement and requires a separately verified
interpretation for this special interaction. It does not invent an equation.

No operation performs elastic eigenvalue analysis. The external buckling load/moment
must be checked against analytical benchmarks and account for the intended mode,
restraints and loading. A solver eigenvalue without that assessment is insufficient.
Unequal-flange/monosymmetric LTB,
rational torsional-flexural buckling, and automatic built-up
component/connection sizing remain separate requirements. Built-up tension component
slenderness, connection distribution and required tie/batten placement remain assessed
under 7.4, even when the lacing or batten primitive passes.

Tests cover the published compression table and Tables 5.6.2–5.6.3 values and boundaries,
independent buckling/moment arithmetic,
plastic web branch boundaries, the 30–40–50 batten slenderness case, kN/mm to kN.m
connection conversion, lacing and pin boundaries, and restraint force summation.
These verify the implemented arithmetic and conditions; they do not certify a structure.
