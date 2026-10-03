# Connection calculations

`run_connections` evaluates a strict `check_type` tagged object. Every field in the
selected schema is required, additional fields are rejected, and numbers must be
finite. Dimensions are mm, areas mm², stresses MPa, forces kN, moments kNm.
Design actions must include externally assessed eccentricity and prying. These
are component calculations, not a complete connection compliance certificate.

The implementation was visually reviewed against the licensed AS 4100:2020
Section 9, printed pages 116–138, Table 3.4 on page 34, and Clause 3.5.5 on page 35.
The source standard is not redistributed.

| check_type | Calculation and prerequisites |
| --- | --- |
| bolt | 9.2.2.1–3 shear, tension, squared interaction; lap length, grade 10.9 threaded-plane ductility and filler reduction under 9.2.2.5. Supply minor area (not tensile area) for threaded shear and certified bolt strength/areas. Filler thickness >=20 mm is unsupported. Zero lap length means a non-lap connection. |
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
| weld_group | 9.7.1–3 constant-throat straight-line fillet group, signed Fx/Fy/Fz and Mx/My/Mz at centroid. Exact line integrals including product inertia; vector resultant checked at every endpoint. Forces and moments are in a right-handed xyz system; weld lies in xy plane. |

Weld lap reduction is calculated from the supplied lap length in millimetres.
The enlarged source Table 9.6.3.10(B) specifies metres; the implementation converts
millimetres to metres before selecting its piecewise factor. Zero denotes a
non-lap connection. Weld group inputs describe a non-lap connection; lap weld groups
are outside this operation's scope. Group geometry must not contain duplicate
or overlapping weld lengths, and does not include thin RHS longitudinal welds.

The following still require engineering assessment: 9.1 connection modelling,
minimum design actions, force transfer, restraint, prying, local hollow-section
effects; plate/component section/member checks; out-of-plane bolt groups;
nonstandard holes; weld preparation, enhanced penetration, compound weld
geometry and built-up-member detailing outside the listed Clause 9.6.3.9 termination checks;
fabrication, inspection and installation Sections 14/15 and referenced standards.
Fatigue, brittle fracture, seismic and fire applicability are separate checks.

Verification includes independent arithmetic benchmarks, table boundaries,
service and strength capacity factors, signed vector group equilibrium, exact
square weld line inertia, invalid/nonfinite inputs and degenerate geometry.
