# Connection calculations

`run_connections` evaluates a strict `check_type` tagged object. All non-optional
fields in the selected schema are required, additional fields are rejected, and
numbers must be finite. Dimensions are mm, areas mm², stresses MPa, forces kN,
moments kNm.
Supply complete design actions and eccentricities. The bolt check accepts
externally assessed prying tension separately and adds it to bolt tension; other
connection actions must already include applicable eccentricity and prying.
These are component calculations, not a complete connection compliance certificate.

For any nonzero filler thickness, bolt and bolt-group checks require external
verification that the filler extends beyond the connection and that its bolts
transfer the member force through the combined section. Both conditions appear
as Clause 9.2.2.5 checks in the result; an unverified input is rejected and a
verified false input fails the check. The operation does not calculate the
extension geometry or the transfer-bolt capacity. The shear-capacity reduction
is applied only above 6 mm; thicknesses of 20 mm or more are unsupported. Use
`filler_thickness_by_shear_plane_mm` to provide the total filler thickness on
each shear plane, including paint film; the operation selects the maximum.
Alternatively, `filler_thickness_mm` must already be that governing maximum.

The implementation was visually reviewed against the licensed AS 4100:2020
Section 9, printed pages 112–138, including Clause 9.1.9(e) and Clauses 9.1.10.1-3 on pages 116-117, Clause 9.1.4 on page 114, Clauses 9.2.2.4 and 9.3.1 on pages 120 and 122, Clauses 9.4.4 and 9.5.1 on page 124, Clauses 9.5.2-5 on page 125, and Clauses
9.6.2.3(b)(i), 9.6.2.3(b)(iii), 9.6.2.6 on page 127, and 9.6.2.7(c) on page 129,
plus 9.6.3.4 and Figure 9.6.3.4 on page 133, Table 3.4
on page 34, Clause 3.5.5 on page 35, and Appendix J on printed pages 203–206.
The source standard is not redistributed.

| check_type | Calculation and prerequisites |
| --- | --- |
| joint_eccentricity_action | 9.1.5 signed joint moment vector from `r × F`; axes should meet at a point where practicable. For fatigue-loaded angle details, externally verify weld balancing or bolt gauge-line eccentricity from the connection geometry. |
| fastener_selection_suitability | 9.1.6 rule checks for avoiding serviceability slip and for impact/vibration. Friction-category 8.8/TF or 10.9/TF bolts, fitted bolts and welds satisfy slip avoidance; friction-category bolts, locking devices and welds satisfy impact/vibration. |
| combined_connection_action_assignment | 9.1.7 assigns explicit design-action shares only to non-slip groups in a non-weld stage; slip-type groups receive none. Initial weld actions and actions applied after welding go wholly to one aggregate weld group. Verify the supplied share fractions and installation sequence from engineering records. |
| minimum_beam_shear_action | 9.1.4(b)(ii) minimum simple-construction beam-connection shear: the greater of actual member design shear and the lesser of 0.15 times member design shear capacity or 40 kN. When supplied, 9.1.2.3 uses the assessed unit shear direction and eccentricity vector to calculate the corresponding signed moment vector. Optionally compares a supplied connection design shear capacity with the required shear. No capacity factor is applied again. |
| minimum_rigid_connection_action | 9.1.4(b)(i) rigid-construction connection moment: the greater of actual design moment and 0.5 times member design moment capacity. |
| minimum_member_end_action | 9.1.4(b)(iii) tensile/compression member-end action: the greater of actual axial action and 0.3 times member design capacity. For verified threaded tension bracing with turnbuckles, the minimum is the full member design capacity. |
| minimum_axial_splice_action | 9.1.4(b)(iv) axial-tension splice minimum of 0.3 times member design capacity; 9.1.4(b)(v) axial-compression splice minimum of 0.15 for verified full-contact bearing or 0.3 when not prepared for full contact. The latter route also requires evidence that the splice material and fasteners hold all parts in line. |
| minimum_compression_splice_between_supports | 9.1.4(b)(v) compression-splice axial action plus moment `M* = δ N* Ls / 1000`; select the Clause 4.4 `δb` or `δs` value externally and verify its basis. The calculated minimum moment uses the greater of actual axial action and the splice's minimum axial action as a conservative `N*` basis. When not prepared for full contact, evidence that the splice parts are held in line is required. Optional connection axial and moment capacities are compared separately. |
| minimum_flexural_splice_action | 9.1.4(b)(vi) flexural-splice moment: the greater of actual design moment and 0.3 times member design moment capacity. Do not use for a shear-only splice. |
| shear_only_splice_eccentric_action | 9.1.4(b)(vi) shear-only splice: retains the design shear and calculates the moment from the force eccentricity relative to the connector-group centroid. |
| minimum_combined_splice_actions | 9.1.4(b)(vii) axial tension or compression plus bending; calculates the applicable axial minimum and flexural minimum simultaneously. For compression splices between effective lateral supports, also applies the Clause 4.4 amplified moment from 9.1.4(b)(v). The non-full-contact compression route requires evidence that the splice parts are held in line. |
| bolt | 9.1.8 externally assessed prying tension is added to member tension; the supplied prying assessment must use a recognized method supported by experimental evidence. 9.2.2.1–3 shear, tension, squared interaction; lap length, grade 10.9 threaded-plane ductility and filler reduction under 9.2.2.5. Supply minor area (not tensile area) for threaded shear and certified bolt strength/areas. Filler thickness >=20 mm is unsupported. Zero lap length means a non-lap connection. |
| bearing | 9.2.2.4 ply bearing and edge tear-out. Effective edge distance is clear hole-edge distance towards the loaded edge or adjacent hole plus half bolt diameter. Each ply and action direction needs its own check. |
| slip | 9.2.3.1 service shear and 9.2.3.3 linear shear/tension interaction, phi=0.7 under 3.5.5. Clause 9.2.3.2 reports whether 0.35 is based on verified clean as-rolled surfaces or a supplied slip factor has test evidence; Appendix J testing is a recognized evidence route. It also records whether the friction bolt category plus surface-treatment and paint-masking requirements appear on drawings. Missing or false evidence fails this separate check. Installation tension and separate strength checks remain engineering inputs. |
| slip_factor_test | Appendix J.1–J.5: calculates the design slip factor from two bolt positions per specimen, using the measured bolt tension from a load-cell calibration curve or Equation J.1; checks Table 15.2.2.2 minimum bolt tension and the Equation J.1 80%–100% proof-load range. Figure J.1 dimensions are calculated for the 10df test-section length, 6df specimen width and bolt spacing, 2df end distance, 3df edge distance, df+5 inner-plate thickness, df/2+2 cover-plate thickness, df+2/df+3 hole diameters and 8 mm butt gap. J.3 calculates each position's assumed slip load as 2 x 0.35 x bolt tension, uses the lower position load for the two positions in series, and checks the lesser of 25 kN or one-quarter of that load, the 50 kN/min limit up to first measured slip, and creep cessation between increments. J.4 accepts a clear observed slip load or derives the 0.13 mm slip load from the mean of the two edge readings. Four specimens are rejected because Appendix J gives no k value; five or more use k=0.90. Specimen form, faying-surface condition, assembly, calibration-batch, bolt geometry, instrumentation, rate uniformity and creep records remain explicit evidence. |
| block_shear | 9.1.9(e) net rupture capped by gross shear yielding, phi=0.75, eccentricity factor 1 or 0.5. Evaluate one externally enumerated rupture path from areas. |
| block_shear_paths | 9.1.9(e) calculates gross/net shear and net tension areas from the supplied path lengths and thickness, checks each candidate path, and selects the least design resistance. Requires a verified complete path set and net lengths derived under 9.1.10. It does not generate paths or derive hole deductions from bolt geometry. |
| block_shear_grid | 9.1.9(e) and 9.1.10 for a complete rectangular grid of circular holes in a flat plate. From the declared longitudinal load-introduction edge, generates every pair of transverse columns at each terminal row, derives two shear lengths and the terminal tension length from gross hole diameters, checks every candidate, and selects the least design resistance. Supply plate dimensions, thickness, material strengths, complete hole coordinates/diameters, load edge, tension-stress classification and explicit verification of the layout, topology, action direction and edge. Staggered/incomplete grids, non-circular holes, alternate section geometries, other load paths and full connection detailing are outside this route. |
| pin | 9.4.1–3 circular solid pin shear, pin bearing with rotation factor, and bending using plastic modulus d³/6; 9.4.4 checks every connected ply under 9.2.2.4 using its supplied force share, tensile strength, thickness, force-to-edge condition and effective edge distance. Confirm the connected-ply list and force distribution from the connection analysis. |
| fillet | 9.6.3.10 strength using externally established design throat and effective length; includes the capacity calculation used by 9.6.2.7(c) when an incomplete-butt throat is supplied. Thin RHS longitudinal SP weld factor 0.7. Geometry and weld-size detailing are separate prerequisites. |
| fillet_design | 9.6.3.1–6 leg sizes, root gap, throat, minimum/maximum size, effective length and area; optional 9.6.3.4 automatic-arc production-weld macro-test throat increase using `t_t1 + 0.85t_t2`; 9.6.3.7–8 built-up parallel/intermittent weld spacing; 9.6.3.10 weld strength. | Supply the weld-metal strength and verify weld geometry, edge build-out, root gap and load sharing. The optional increase requires a production-weld macro-test record demonstrating required penetration. Declarations and measurements are not authenticated. Use the resulting capacity in the attached component or stiffener check; fatigue quality and complete connection design remain separate. |
| built_up_component_end_weld | 9.6.3.9(a) minimum weld length at built-up component ends, including tapered components. | Supply each connected width and taper length; the requirement applies when side fillet welds alone are used. |
| cap_plate_weld | 9.6.3.9(b) minimum weld length per joint line at a compression-member cap/base plate. | Supply member width at the contact face and weld length on each joint line. |
| beam_compression_member_weld | 9.6.3.9(c) weld extent between beam faces and the restraint-dependent extension around a beam-to-compression-member connection. | Supply beam depth, compression-member maximum dimension, restraint condition and measured weld extents. |
| packing_construction | 9.8 flush trimming and edge-weld size increase for thin packing; extension beyond member edges and welding to the fitted piece for the other branch. | Supply required/provided edge-weld sizes and assess whether packing is too thin for adequate welds or to prevent buckling. |
| fastener_detailing | Bolt-only numerical route: 9.5.1 checks minimum pitch for every fastener pair using the larger pair diameter; 9.5.2 checks Table 9.5.2 edge distances for every connected ply/physical edge; 9.5.3 checks ordered collinear consecutive lines under the general, non-action/non-corrosive, or outside-line-in-action case; and 9.5.4 checks the nearest contacting-part edge using the thinnest outer connected ply. Non-standard holes use nearest hole-edge clearance plus half nominal fastener diameter. Clause 9.5.5 records the separate AS/NZS 5131 hole-conformity assessment for bolts and pins. | Supply the complete bolt layout, ordered pitch lines, connected-ply and physical-edge inventory, standard/non-standard hole classification and measured distances. References and classification flags are required; they do not authenticate the source drawing, edge finish, region classification or AS/NZS 5131 compliance. Pin resistance and pin-specific detailing remain separate. |
| butt_weld_transition | 9.6.2.6 checks the maximum 1:1 slope for a verified thickness/width transition in a tension-loaded butt joint. An optional, stricter fatigue slope can be supplied. | Verify the actual smooth transition and effective run. Fatigue classification and any stricter slope limit need an external assessment and reference. |
| complete_butt | 9.6.2.7(a) weaker-part nominal capacity multiplied by quality factor; requires qualified procedure and matching consumable attestation. |
| incomplete_butt_design | 9.6.2.3(b)(ii)(A)–(B), 9.6.2.4–5 and 9.6.2.7(c): for θ≤60°, uses `d−3` for single-V and `d3+d4−6` for double-V; above 60°, uses `d` and `d3+d4`, respectively. Optional 9.6.2.3(b)(iii)/Figure 9.6.3.4 macro-test route uses the preparation depth plus `0.85` times verified penetration beyond it. Calculates effective area and checks strength under 9.6.3.10. | Verify the preparation classification, measured depth(s), continuous full-size length, weld quality, qualified procedure and consumable basis. The macro-test route requires an automatic arc process, required penetration demonstrated on a production-weld macro test, and a traceable record reference. Declarations and measurements are not authenticated. Other preparation forms remain outside this route. |
| prequalified_incomplete_butt_design | 9.6.2.3(b)(i) accepts the design throat established for an AS/NZS 1554.1 or AS/NZS 1554.4 prequalified preparation, then calculates effective length/area under 9.6.2.4–5 and strength under 9.6.2.7(c)/9.6.3.10. Optional 9.6.2.3(b)(iii)/Figure 9.6.3.4 macro-test throat increase is also calculated. | Verify the prequalified preparation and throat against the referenced welding standard and project records, plus the welding procedure, consumable strength, weld quality and inspection requirements. References, declarations and measurements are not authenticated. |
| incomplete_compound_weld_design | 9.6.5.2(b) calculates the shortest root-to-fillet-face distance for a straight planar face, caps the throat at the butting-part thickness, and checks effective area and strength under 9.6.5.3, 9.6.2.4–5, 9.6.2.7(c) and 9.6.3.10. | Verify the compound-weld classification to AS 1101.3 and cite the detail; the projection must fall on the supplied straight face segment. Curved/non-planar faces and the evidence records require separate assessment. |
| plug_slot | 9.6.4.2 calculates filled-hole shear area at the faying plane from a verified circular hole, round-ended slot (overall length and width) or rectangular slot (length and width), or accepts an externally assessed nominal area. Capacity is `0.6 fuw Aw`; 9.6.4.3 permitted shear applications require attestation. Circumferential fillet welds use `fillet`. | Verify hole dimensions/profile, faying-plane geometry and the allowed application: shear transfer in lap joints, preventing buckling of lapped parts, or joining built-up-member components. Unsupported profiles need an externally assessed nominal area. |
| layout | Compact 9.5.1–4 screening calculation for one supplied pitch and edge distance. Use `fastener_detailing` for complete multi-fastener layouts, per-ply edge checks, non-standard holes, and 9.5.3 exceptions. |
| hole_deduction | 9.1.10 governing straight/zigzag deduction. Supply maximum straight width sum and each candidate zigzag path separately; each stagger pair is [pitch, gauge]. Includes actual gross hole width, countersink where relevant. Enumerate all paths externally. |
| hole_deduction_layout | 9.1.10.1-3 derives the maximum straight-row deduction and searches every progressive zig-zag path for a complete flat, uniform-thickness plate. Supply hole-centre coordinates and each gross hole width across the plate; verify the member/action axes and complete layout. |
| angle_hole_deduction | 9.1.10.1-3 compares a verified straight-row width with every supplied ordered zig-zag path. Same-leg gauges use back-mark differences; opposite-leg gauges use the sum of back marks less leg thickness under Figure 9.1.10.3(B). Supply the complete path set and verified angle geometry. |
| angle_hole_deduction_layout | 9.1.10.1-3 derives straight rows and searches every progressive zig-zag chain through a complete two-leg angle hole layout. Leg 1 is ordered toe-to-heel and leg 2 heel-to-toe. Same-leg gauges use back-mark differences; cross-leg gauges use Figure 9.1.10.3(B). Supply all hole coordinates, gross hole widths and verified angle orientation, dimensions and action axis. |
| combined_weld_types | 9.7.4 sums already-calculated Section 9 design capacities for at least two different weld types and compares the total with one force or moment action. Declare the complete non-overlapping component set and a common action basis/direction. It does not calculate individual weld capacities or apply another capacity factor. |
| bolt_group | 9.3.1 rigid-group elastic superposition of centroidal signed Fx, Fy and Mz. Checks each bolt; identical bolts, in-plane actions only. Component actions must be zero. Separate ply bearing and detailing remain necessary. |
| bolt_group_with_ply_bearing | 9.3.1 and 9.2.2.1/9.2.2.4 for a rigid-plate, centroidal-action group with exactly two plies, one shear plane, standard round holes and no filler. Checks each bolt and each ply; the full bolt force acts on both plies. Oblique bolt vectors use the least capacity from the non-zero component directions as a conservative bearing envelope. |
| bolt_group_out_of_plane | 9.3.2–3 checks user-supplied per-bolt Fx/Fy/tension actions, their six-resultant equilibrium under 9.1.3(a), and each bolt's shear, tension, prying addition and combined interaction. Bolt tension acts along z; positions are (x,y) about the verified common action origin and moments follow right-handed `r × F`. Load distribution and component stability require verified analysis inputs. Check compression/contact actions and ply bearing separately. |
| bolt_group_elastic_3d | 9.1.3(a), 9.3.2–3 resolves a planar bolt group's six centroidal resultants with rigid-plate, equal-bolt-stiffness linear elastic distribution, then checks equilibrium and each bolt's shear, tension, prying addition and interaction. Requires a non-collinear layout, verified method/experimental basis, and nonnegative calculated bolt tension. Compression/contact and slack-bolt redistribution, ply bearing and complete connection-component checks remain separate. |
| weld_group | 9.7.1–3 constant-throat straight-line fillet group, signed Fx/Fy/Fz and Mx/My/Mz at centroid. Exact line integrals including product inertia; vector resultant checked at every endpoint. Forces and moments are in a right-handed xyz system; weld lies in xy plane. |

For `pin`, provide one `connected_plies` item per physically connected ply,
with a unique `ply_id`, thickness, tensile strength, bearing action and whether
that action has a component towards a ply edge. The listed thicknesses must sum
to `ply_thickness_mm`, the complete ply set and action distribution must be
verified, and each ply is checked independently. When the force has a component
towards an edge, `effective_edge_distance_mm` is required: use the minimum clear
distance from the pin hole to a ply edge or adjacent hole in that direction,
plus half the pin diameter. These geometry and load-distribution inputs remain
engineering evidence; the plugin does not authenticate them.

For `bolt_group_with_ply_bearing`, provide exactly two complete connected plies,
one shear plane, standard round holes and no filler plates. The supplied group
force and moment are the resultant applied to the reference connected ply; the
computed distributed bolt-action vectors sum to that resultant. For each ply,
set `bearing_force_relative_to_bolt_action` to state whether the bolt bearing
force on that ply follows or opposes its computed per-bolt action vector. The
per-bolt convention defines directions for a pure couple as well, where no
global force direction exists. Supply a direction-specific
`effective_edge_distances_by_bolt_mm` entry for every point in the same order as
`points_mm`; each distance is the minimum clear distance from the hole edge to a
free edge or adjacent hole in that force direction, plus half the nominal bolt
diameter. The full resultant force on each bolt is checked against each ply,
with that ply's own thickness, tensile strength and edge distance. The route
also accepts oblique bolt-force vectors. For each non-zero force component it
checks the full resultant against the bearing capacity in that component's
direction, using the lesser directional capacity as a conservative envelope.
This can be more conservative than a direction-specific interaction model; the
geometry and force components still need independent verification. Verify the
centroidal actions, rigid plates, complete ply set, geometry and Clause 9.5
detailing independently.
Net/block shear, slip resistance, component stability and other connection
checks remain separate.

`hole_deduction_layout` treats `longitudinal_mm` as parallel to the design action and `transverse_mm` as perpendicular to it. `gross_hole_width_mm` is the gross hole width across the plate at the section, including any applicable countersink. The result reports the controlling straight row, the maximum progressive zig-zag chain and its individual stagger corrections, then selects the greater deduction under Clause 9.1.10.3. This flat-plate route does not cover other section forms, net-section modulus calculations or block-shear path enumeration. It also does not authenticate the declared layout or replace Clause 9.5 detailing checks.

For `angle_hole_deduction`, provide the straight-row width and every progressive zig-zag path. The calculation derives each gauge for consecutive holes, applies the Clause 9.1.10.3 stagger correction, and selects the greatest deduction. The angle geometry, Figure 9.1.10.3(B) back marks, straight-row width and completeness/order of candidate paths remain verified engineering inputs.

`angle_hole_deduction_layout` accepts all holes from both legs, groups holes at each longitudinal coordinate for straight deductions, orders leg 1 from toe to heel and leg 2 from heel to toe, and searches every positive-gauge forward chain. It uses absolute back-mark differences within a leg and the Figure 9.1.10.3(B) sum-minus-thickness gauge across legs. Each `gross_hole_width_mm` is the gross hole width across the net section and must fit within its leg. Supply the gross section area and verify angle orientation, leg widths, all hole coordinates, action axis, hole sizes (including countersinks where relevant), and constant thickness. The calculation does not derive gross angle area or check other angle design provisions.

The optional incomplete-butt macro-test inputs are all required together. The calculation
uses total preparation depth as `t_t1` and measured penetration beyond it as `t_t2` in
Figure 9.6.3.4; for double-V preparations the supplied extra penetration is the sum
across both sides. Confirm those measurements and the production-weld test record.

The Clause 9.6.2.6 transition operation checks only tension-loaded joints. Its
optional fatigue slope limit is an externally assessed dimension-change-to-run
ratio and must be supported by the referenced detail assessment.

Weld lap reduction is calculated from the supplied lap length in millimetres.
The enlarged source Table 9.6.3.10(B) specifies metres; the implementation converts
millimetres to metres before selecting its piecewise factor. Zero denotes a
non-lap connection. Weld group inputs describe a non-lap connection; lap weld groups
are outside this operation's scope. Group geometry must not contain duplicate
or overlapping weld lengths, and does not include thin RHS longitudinal welds.

The following still require engineering assessment: share fractions and installation
sequence under 9.1.7; special fatigue-angle detail assessment under 9.1.5; actual design
actions and classification evidence, force transfer, restraint and alternative Clause 9.1.3
distribution methods when the rigid-plate/equal-stiffness case is inapplicable; compression/contact
and slack-bolt redistribution; local hollow-section effects; plate/component section/member checks;
nonstandard holes; weld preparation routes outside the listed non-prequalified
single- and double-V throat formulas and macro-test route, compound weld geometry and
built-up-member detailing outside the listed Clause 9.6.3.9 termination checks;
fabrication, inspection and installation Sections 14/15 and referenced standards.
Clause 9.7.4 sums capacities only when the supplied Section 9 capacities share
one action basis and direction and represent the complete, non-overlapping set
of weld components. Verify the component capacity calculations and compatible
force-transfer mechanism separately.
These Clause 9.1.4 routes calculate required actions only; supplied member design
capacities must include the applicable capacity factor. Combined splice action
demands are reported together, but connection component resistance and combined-
action interaction require separate checks. Clause 9.1.4 earthquake-combination
action increases are not calculated here and must be assessed under Section 13.
Clause 9.1.8 does not calculate prying force; the supplied force and its supporting
experimental-method evidence need engineering review. Fatigue, brittle-fracture
and fire applicability are separate checks.

Verification includes independent arithmetic benchmarks, table boundaries,
service and strength capacity factors, signed vector group equilibrium, exact
square weld line inertia, invalid/nonfinite inputs and degenerate geometry.

`slip_factor_test` retains every bolt-position estimate and reports the sample
standard deviation across all 2n estimates, together with the declared
prerequisites and evidence references. The test procedure and evidence
declarations are not authenticated: confirm the test specimen, instrumentation,
load-cell calibration from at least three bolts in the tested batch or measured
bolt geometry, loading protocol and reported slip loads against the laboratory
record before using the resulting factor. Figure J.1 dimensions are checked
against the declared nominal geometry; surface preparation and fabrication
records still require review.
