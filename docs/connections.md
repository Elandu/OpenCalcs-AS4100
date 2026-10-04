# Connection calculations

`run_connections` evaluates a strict `check_type` tagged object. All non-optional
fields in the selected schema are required, additional fields are rejected, and
numbers must be finite. Dimensions are mm, areas mm², stresses MPa, forces kN,
moments kNm.
Supply complete design actions and eccentricities. The bolt check accepts
externally assessed prying tension separately and adds it to bolt tension; other
connection actions must already include applicable eccentricity and prying.
These are component calculations, not a complete connection compliance certificate.

The implementation was visually reviewed against the licensed AS 4100:2020
Section 9, printed pages 112–138, including Clause 9.1.4 on page 114, Table 3.4
on page 34, and Clause 3.5.5 on page 35.
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
| slip | 9.2.3 service shear and linear shear/tension interaction, phi=0.7 under 3.5.5. Installation tension and slip coefficient require compliant installation and surface evidence. As-rolled clean surfaces use 0.35; other surfaces require testing. Separate strength checks remain necessary. |
| block_shear | 9.1.9(e) net rupture capped by gross shear yielding, phi=0.75, eccentricity factor 1 or 0.5. Enumerate all feasible rupture paths externally. |
| pin | 9.4.1–3 circular solid pin shear, pin bearing with rotation factor, and bending using plastic modulus d³/6. Pin actions and plate load distribution require external analysis; ply bearing also uses bearing. |
| fillet | 9.6.3.10 strength using externally established design throat and effective length, including 9.6.2.7(c) incomplete butt capacity. Thin RHS longitudinal SP weld factor 0.7. Geometry and weld-size detailing are separate prerequisites. |
| fillet_design | 9.6.3.1–6 leg sizes, root gap, throat, minimum/maximum size, effective length and area; 9.6.3.7–8 built-up parallel/intermittent weld spacing; 9.6.3.10 weld strength. | Supply the weld-metal strength and verify weld geometry, edge build-out, root gap and load sharing. Use the resulting capacity in the attached component or stiffener check; welding procedures and production inspection remain separate. |
| built_up_component_end_weld | 9.6.3.9(a) minimum weld length at built-up component ends, including tapered components. | Supply each connected width and taper length; the requirement applies when side fillet welds alone are used. |
| cap_plate_weld | 9.6.3.9(b) minimum weld length per joint line at a compression-member cap/base plate. | Supply member width at the contact face and weld length on each joint line. |
| beam_compression_member_weld | 9.6.3.9(c) weld extent between beam faces and the restraint-dependent extension around a beam-to-compression-member connection. | Supply beam depth, compression-member maximum dimension, restraint condition and measured weld extents. |
| packing_construction | 9.8 flush trimming and edge-weld size increase for thin packing; extension beyond member edges and welding to the fitted piece for the other branch. | Supply required/provided edge-weld sizes and assess whether packing is too thin for adequate welds or to prevent buckling. |
| complete_butt | 9.6.2.7(a) weaker-part nominal capacity multiplied by quality factor; requires qualified procedure and matching consumable attestation. |
| plug_slot | 9.6.4.2 filled-hole shear on externally assessed faying-plane area, permitted applications under 9.6.4.3 require attestation. Circumferential fillet welds use fillet. |
| layout | 9.5.1–4 pitch and edge limits for standard holes; supply thinnest applicable ply and edge finish. Nonstandard hole-edge reference, corrosion and non-load conditions require external assessment. |
| hole_deduction | 9.1.10 governing straight/zigzag deduction. Supply maximum straight width sum and each candidate zigzag path separately; each stagger pair is [pitch, gauge]. Includes actual gross hole width, countersink where relevant. Enumerate all paths externally. |
| bolt_group | 9.3.1 rigid-group elastic superposition of centroidal signed Fx, Fy and Mz. Checks each bolt; identical bolts, in-plane actions only. Component actions must be zero. Separate ply bearing and detailing remain necessary. |
| bolt_group_out_of_plane | 9.3.2–3 checks user-supplied per-bolt Fx/Fy/tension actions, their six-resultant equilibrium under 9.1.3(a), and each bolt's shear, tension, prying addition and combined interaction. Bolt tension acts along z; positions are (x,y) about the verified common action origin and moments follow right-handed `r × F`. Load distribution and component stability require verified analysis inputs. Check compression/contact actions and ply bearing separately. |
| weld_group | 9.7.1–3 constant-throat straight-line fillet group, signed Fx/Fy/Fz and Mx/My/Mz at centroid. Exact line integrals including product inertia; vector resultant checked at every endpoint. Forces and moments are in a right-handed xyz system; weld lies in xy plane. |

Weld lap reduction is calculated from the supplied lap length in millimetres.
The enlarged source Table 9.6.3.10(B) specifies metres; the implementation converts
millimetres to metres before selecting its piecewise factor. Zero denotes a
non-lap connection. Weld group inputs describe a non-lap connection; lap weld groups
are outside this operation's scope. Group geometry must not contain duplicate
or overlapping weld lengths, and does not include thin RHS longitudinal welds.

The following still require engineering assessment: share fractions and installation
sequence under 9.1.7; special fatigue-angle detail assessment under 9.1.5; actual design
actions and classification evidence, force transfer, restraint and Clause 9.1.3 load
distribution method for out-of-plane bolt groups; local hollow-section effects; plate/component
section/member checks;
nonstandard holes; weld preparation, enhanced penetration, compound weld
geometry and built-up-member detailing outside the listed Clause 9.6.3.9 termination checks;
fabrication, inspection and installation Sections 14/15 and referenced standards.
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
