# Design actions and stability

`run_design_actions` implements selected checks for AS 4100:2020 Sections 3, 4,
and 6.3.2. All action and capacity inputs are kN or kN·m unless the field name states
otherwise. Evidence references identify supporting project records; the plugin
does not authenticate those records.

## Idealized member buckling

`idealized_member_buckling` combines the Clause 4.6.3.2 effective-length
factors from Figure 4.6.3.2 with the Clause 4.6.2 Euler elastic buckling load.
`member_length_mm` is the verified centre-to-centre length between supporting
members, and `second_moment_mm4` is the supplied section property about the
assessed buckling axis.

The case identifiers correspond to the figure as follows:

| Case | End restraints shown in Figure 4.6.3.2 | `k_e` |
| --- | --- | ---: |
| `braced_fixed_fixed` | Both ends rotation-fixed and translation-fixed | 0.70 |
| `braced_top_pinned_bottom_fixed` | Top rotation-free/translation-fixed; bottom rotation-fixed/translation-fixed | 0.85 |
| `braced_pinned_pinned` | Both ends rotation-free and translation-fixed | 1.00 |
| `sway_top_fixed_bottom_fixed` | Top rotation-fixed/translation-free; bottom rotation-fixed/translation-fixed | 1.20 |
| `sway_top_free_bottom_fixed` | Top rotation-free/translation-free; bottom rotation-fixed/translation-fixed | 2.20 |
| `sway_top_fixed_bottom_pinned` | Top rotation-fixed/translation-free; bottom rotation-free/translation-fixed | 2.20 |

The case and centre-to-centre length each require a verified declaration and
evidence reference. These are the figure's idealized cases; the operation does
not determine actual restraint stiffness, select the buckling axis, analyse the
frame, or calculate a Clause 6.3 design capacity.

## Compression-member effective lengths

`compression_member_effective_lengths` applies the independently selected
Figure 4.6.3.2 idealized end-restraint cases to both flexural-buckling axes,
then returns `effective_length_x_mm` and `effective_length_y_mm` for direct use
in `run_members` with `operation="compression"`. Supply the verified member principal axes, one
centre-to-centre member length, and a verified case plus evidence reference for
each axis. It does not infer the restraint case, select the governing mode,
analyse the frame or calculate member resistance. For restraints outside the
listed idealizations, provide effective lengths established by the applicable
frame or rational analysis.

## Frame chart factor and Euler buckling load

`frame_chart_member_buckling` calculates the Clause 4.6.2 elastic buckling load
and can solve the Figure 4.6.3.3 alignment-chart equation directly. Supply the
rigid-jointed frame's braced or sway classification and both end stiffness
ratios. If an independently read chart factor is supplied instead, also supply
`effective_length_factor_chart_verified` and `chart_evidence_reference`; the
operation retains this route for existing integrations.

The numerical route solves the classic elastic alignment-chart equations for
`z = pi / k_e`. For braced members, it solves

`(gamma_1 gamma_2 z^2)/4 + ((gamma_1 + gamma_2)/2)(1 - z cot z) + 2 tan(z/2)/z = 1`

for `pi < z < 2 pi`. For sway members, it solves

`(gamma_1 gamma_2 z^2 - 36)/(6(gamma_1 + gamma_2)) = z cot z`

for `0 < z < pi`. The zero-stiffness limiting cases are `k_e = 0.5` for
braced members and `k_e = 1.0` for sway members. These characteristic
equations are documented as exact numerical forms of the alignment charts by
Dumonteil, “Simple Equations for Effective Length Factors,” *AISC Engineering
Journal*, Third Quarter 1992, pp. 111–115. The solver uses bracketed bisection
on the applicable first-mode interval.

The rigid-jointed frame classification, frame type, end ratios, second moment
of area about the buckling axis, and centre-to-centre member length each require
a verified declaration and evidence reference. A supplied chart reading also
requires its own verification flag and evidence reference. Determine the end
ratios under Clause 4.6.3.4 for rectangular frames or Appendix G where
applicable.

The equation route calculates the factor from the supplied stiffness ratios;
the chart-reading route accepts the separately verified factor. Neither route
calculates the stiffness ratios or checks whether the complete frame model
satisfies the chart's idealized assumptions. The result is an elastic buckling
load, not a Clause 6.3 member design capacity or a whole-frame buckling
analysis.

## Whole-frame elastic buckling

`whole_frame_elastic_buckling` solves the in-plane elastic buckling eigenvalue
for a planar frame under one proportional member-force pattern, tracing Clauses
4.7.1 and 4.7.2(b). `lambda_c` (also returned as
`elastic_buckling_load_factor`) is the multiplier on the supplied member axial
forces at the first positive elastic buckling eigenvalue.
Compression is positive and tension is negative. The operation reports the
results from four, eight, sixteen, and (if needed) thirty-two elements per
member. It accepts the first consecutive pair that agrees within 0.1%; otherwise
it rejects the calculation.

The model uses 200 000 MPa elastic modulus, Euler-Bernoulli frame members, in-plane
area and second moment, and rigid connections at shared joints. A physical member
with discrete changes in section or axial force can be represented by separate
prismatic segments meeting at explicitly listed rigid joints; each segment must
have verified constant properties. Smoothly varying sections are outside this
bounded model. Axial force may be constant along a segment or supplied at both
ends for linear interpolation; both end values must belong to the same
proportional load set, ordered from `start_joint_id` to `end_joint_id`. Provide
complete joint coordinates and restrained `ux`,
`uy`, and `rz` degrees of freedom, plus each segment's area, in-plane second
moment, and axial-force profile. Supply exactly one of `axial_force_kn` for a
constant member force or `axial_force_profile_kn: [N_start, N_end]` for a linear
profile, with force values in kN. The result preserves the supplied form.
The input separately records complete joint and member inventories. Geometry,
restraints, frame completeness, member properties, force pattern, and analysis
assumptions require evidence references and engineering assessment.

This route excludes out-of-plane or torsional modes, member-end releases,
connection flexibility, shear deformation, initial imperfections, residual
stress, material nonlinearity, and second-order design actions. It calculates
elastic frame stability only; it does not determine the load combinations or
member design capacities, and a passing check does not establish full AS 4100
compliance. Independent checks compare pin-ended and fixed-ended columns with
Euler solutions. The stepped-member route was checked against the exact
beam-column transfer solution for a pin-ended 4 m column with 2 m segments,
`I=8e6 mm4` and `I=2e6 mm4`, and 100 kN compression in each segment: the exact
factor is `3.650519`, and the operation returns `3.650534` (0.0004% difference).
The linearly varying axial-force route was checked against independent RK4
integration of the continuous beam-column transfer equations for a pinned 4 m
column with compression varying from 100 kN to 20 kN: the reference factor is
`15.983725`, and the operation returns `15.984568` (0.0053% difference).
A one-bay portal frame was also cross-checked against the
zero crossing of the lowest tangent-stiffness eigenvalue in OpenSeesPy 3.8.0:
6 m bay, 4 m columns, fixed bases, `E=200000 MPa`, `A=10000 mm2`,
`I=8e6 mm4`, and column compression forces of 30 kN and 20 kN. The OpenSees
P-Delta model used 32 elements per member and returned `lambda_c=26.422688`;
this operation returns `26.413048` (0.037% difference). OpenSees is an
independent verification reference only and is not a runtime dependency or a
published Standard example. To apply the Clause 4.5.4 threshold route, pass
`lambda_c` as `frame_buckling_factor` to `plastic_amplification`.

## Linearized second-order elastic frame analysis

`second_order_elastic_frame_analysis` provides a bounded in-plane linearized
second-order response route for Clauses 4.4.1.2, 4.5.1, 4.7.1, 4.7.2(b) and
Appendix E.1/E.2(b). It assembles elastic and initial-stress geometric
stiffness matrices, solves the supplied joint-action vector with the supplied
first-order member axial-force pattern, and reports the greatest element-end
moment in each member. The 4-, 8-, 16- and 32-element-per-member results are
compared; the calculation accepts the first consecutive meshes agreeing
within 0.1% in model-joint response, member end moments and elastic buckling
factor.

The result also reports `support_reactions` at restrained joint degrees of
freedom and a `global_equilibrium` diagnostic. Reactions are calculated from
the assembled tangent stiffness and supplied joint actions. The reported
resultants separately show applied joint actions, support reactions and the
geometric-stiffness contribution; the residual is their sum in kN and kN·m.
The solver marks the diagnostic satisfied when each force residual is within
`1e-8` times the sum of the absolute applied, reaction and geometric-stiffness
force resultants in both axes; the moment residual uses the corresponding
absolute moment resultants. Each scale has a minimum of 1 kN or 1 kN·m. This is
a numerical check of the assembled
linearized model, not independent evidence that the load list, restraints,
member-force pattern or analysis assumptions are complete or correct.

Use a complete planar frame of prismatic Euler-Bernoulli members with rigid
connections at shared joints. The elastic modulus is fixed at 200 000 MPa.
Supply all joints and members, each member's area and in-plane second moment,
restraints in `ux`, `uy` and `rz`, and one complete `joint_actions` record for
each joint. Joint forces are in kN and moments in kN·m. The member's
`axial_force_kn` or `[N_start, N_end]` profile is separately supplied in kN,
ordered from `start_joint_id` to `end_joint_id`; compression is positive and
tension is negative. Include every applied design action in the joint-action
vector, including the axial actions that correspond to the member-force
pattern. The solver rejects a design load set whose elastic buckling factor
is at or below 1.0. It returns a null elastic buckling factor when the supplied
axial-force pattern has no positive elastic buckling mode, as with zero or
tension-only force patterns; the frame response remains available.

This solver holds the assessed first-order axial-force profile fixed and does
not iterate the deformed frame geometry or member forces. AS 4100 Appendix E.1
requires second-order geometry effects to be accounted for; therefore set
`linearized_model_applicability_verified` only when the engineer has assessed
that this fixed-force linearization is adequate for the design case. Likewise,
`frame_action_equilibrium_verified` records the engineer's evidence that the
complete joint actions and member-force pattern are in equilibrium. The
calculation records these assessments but does not establish them, derive the
member-force pattern from the joint actions, or authenticate the evidence.
Members' elastic response is also an evidenced input, not a capacity check.

Distributed member loads, member-end releases, connection flexibility, shear
deformation, initial imperfections, residual stress, material nonlinearity,
out-of-plane and torsional response, iterative second-order analysis and
member design capacities remain outside this model. Do not use it as a full
Appendix E analysis where the fixed-force linearization is not adequate; use
an independently verified second-order model that accounts for the required
geometry and axial-force changes. The operation does not determine load
combinations or establish full AS 4100 compliance.

The fixed-free-column benchmark uses `E=200000 MPa`, `I=8e6 mm4`, `L=4000 mm`,
50 kN compression and a 10 kN transverse tip force. The independent elastic
beam-column solution gives a 48.338410 kN·m base moment and 166.768194 mm tip
displacement; the refined operation agrees within 0.0001%. This is an analytic
verification case, not a worked example from the Standard.

## Braced-member moment amplification

`moment_amplification` calculates the Clause 4.4.2.2 braced-member factor and
applies it to the supplied first-order maximum moment. With compression, the
member buckling load `elastic_buckling_load_kn` is the Clause 4.6.2 value about
the same axis as the bending moment. The braced-member factor is
`max(1, Cm / (1 - N*/Nomb))`, where `Cm = min(1, 0.6 - 0.4 beta_m)`. The
operation rejects `N* >= Nomb`. If a Clause 4.4.2.3 sway buckling factor is
also supplied, the larger braced or sway factor governs.

For zero axial force or axial tension, enter zero or a negative value in
`compression_kn`; the Clause 4.4.2.2 result is the supplied first-order moment
without a braced-member amplification factor, `beta_m`, or elastic buckling
load. A supplied sway factor is still applied and checked separately.

Supply `beta_m`, `beta_m_figure_case` for a distribution in Figure
4.4.2.2(A)/(B), both end-moment magnitudes for the end-moments-only route,
`conservative_transverse_beta_m: true` for the Clause 4.4.2.2(a) choice
`beta_m = -1`, or both deflections for the Clause 4.4.2.2(c) route. These
routes are mutually exclusive, except the symbolic Figure B, left, row 6 case.
The figure-case identifier uses the panel side and top-to-bottom row number.
For that symbolic case, set
`beta_m_figure_case` to `figure_b_left_6` and supply the signed ratio of the
smaller to larger end moment in `beta_m`; the Standard defines it as positive
for reverse curvature, and the figure gives `beta_m = beta`. Select the
conservative route only for a member with transverse loading. `delta_ct_mm` is
the mid-span deflection from the transverse load together
with both end bending moments. `delta_cw_mm` is the mid-span deflection from
the transverse load together with only the end moments that produce a
mid-span deflection in the same direction as that transverse load. The
operation calculates `beta_m = 1 - 2(delta_ct_mm / delta_cw_mm)` and enforces
the Standard's `-1 <= beta_m <= 1` limit. Do not provide `beta_m` together
with these deflections. The direct `beta_m` route accepts an independently
assessed value and does not verify its basis.

For the end-moments-only route, provide nonnegative `end_moment_1_abs_knm` and
`end_moment_2_abs_knm`, `end_moment_curvature` as `single_curvature` or
`reverse_curvature`, `end_moments_only_verified: true`,
`end_moment_curvature_verified: true`, and an evidence reference. The operation
calculates the smaller-to-larger magnitude ratio, assigning a positive sign for
reverse curvature. It requires `first_order_moment_knm` to equal the larger
end-moment magnitude. Use this route only when the member has end moments and
no transverse loading; the calculation does not authenticate the analysis or
curvature classification.

| `beta_m_figure_case` | `beta_m` |
| --- | ---: |
| `figure_a_left_1` | -1.0 |
| `figure_a_left_2` | +0.2 |
| `figure_a_left_3` | +0.6 |
| `figure_a_left_4` | -0.5 |
| `figure_a_left_5` | +0.2 |
| `figure_a_left_6` | +0.2 |
| `figure_a_right_1` | -1.0 |
| `figure_a_right_2` | +0.5 |
| `figure_a_right_3` | +1.0 |
| `figure_a_right_4` | +0.4 |
| `figure_a_right_5` | 0.0 |
| `figure_a_right_6` | +0.5 |
| `figure_b_left_1` | -0.4 |
| `figure_b_left_2` | +0.1 |
| `figure_b_left_3` | +0.7 |
| `figure_b_left_4` | -0.5 |
| `figure_b_left_5` | -0.2 |
| `figure_b_right_1` | -0.5 |
| `figure_b_right_2` | -0.1 |
| `figure_b_right_3` | +0.3 |
| `figure_b_right_4` | -0.4 |
| `figure_b_right_5` | -0.1 |
| `figure_b_right_6` | +1.0 |

The numeric entries are from AS 4100:2020 Figures 4.4.2.2(A) and (B), printed
pages 42–44. Figure B, left, row 6 is symbolic, with `beta_m = beta`; enter
its assessed ratio through `beta_m`. The calculation records the figure
reference but does not decide whether a member's analysed moment distribution
matches the selected diagram.

The operation uses analysis results supplied by the caller; it does not
classify an actual moment diagram into a figure case, calculate member
deflections, the first-order maximum moment or the elastic buckling load. Check
that the selected diagram matches the member's analysed moment distribution.
A moment amplification factor above 1.4 is diagnostic and requires
second-order analysis under Clause 4.4.1.2. The route covers all 23 numeric
figure values and the Figure B symbolic case; it does not infer diagram
applicability.

## Triangulated-member effective length

`triangulated_member_buckling` calculates the Clause 4.6.2 elastic buckling
load for a Clause 4.6.3.5 member. It uses the centre-to-centre length between
member intersections as the minimum effective length. If the supplied
effective length is shorter and no Appendix G-consistent rational elastic
buckling analysis is verified, it raises the value used to that minimum.

The triangulated-structure classification, intersection length, effective
length assessment and second moment about the buckling axis require verified
declarations and evidence references. A shorter effective length is accepted
only when the rational-analysis consistency declaration is verified. This
operation does not perform that analysis and does not calculate Clause 6.3
member capacity.

## Rectangular-frame elastic buckling factors

`braced_frame_buckling_factor` evaluates `lambda_m = N_omb / N*` for every
listed column in a rectangular frame with all members braced. It reports the
whole-frame factor as the lowest column value. Each listed `N*` must be a
positive compression force; this route does not accept tensile columns.

`sway_frame_buckling_factor` evaluates each storey's `lambda_ms` as the sum of
`N_oms / l` divided by the sum of `N* / l` for all columns in that storey. It
reports the whole-frame factor as the lowest storey value; tension design
forces are negative in the denominator.

Both operations require verified frame conditions, complete column/storey
lists, member buckling loads, design axial forces from one named load set, and
evidence references. `N_omb` and `N_oms` are assessed inputs that must follow
the applicable Clause 4.6 route. These operations calculate the approximate
in-plane elastic buckling factors; they do not perform rational whole-frame
buckling analysis or a Clause 6.3 member design check.

## Rectangular-frame end stiffness ratio

`rectangular_frame_stiffness_ratio` calculates one end's `gamma` value under
Clause 4.6.3.4:

`gamma = sum(I/l for connected compression members) / sum(beta_e * I/l for rigidly connected beams)`

Include the member under consideration in `compression_members`. List all
compression members rigidly connected at that joint. List all beams rigidly
connected to the column there; pin-connected beams at that end are excluded.
`second_moment_mm4 / member_length_mm` is the member's in-plane stiffness term.
For each beam, `far_end_fixity` selects `beta_e` from Table 4.6.3.4:

| Far-end condition | Braced member | Sway member |
| --- | ---: | ---: |
| Pinned | 1.50 | 0.50 |
| Rigidly connected to a column | 1.00 | 1.00 |
| Fixed | 2.00 | 0.67 |

The operation requires verified rectangular-frame geometry, regular loading,
negligible beam axial forces, member connectivity, beam far-end fixity and the
column-base condition. At a column base, it checks the Clause 4.6.3.4 minimum
`gamma` of 10 for a base not rigidly connected to a footing or 0.6 for a rigidly
connected base. A rational-analysis alternative remains external.

This returns one end ratio only. Repeat it for the opposite end and use both
values to assess `k_e` from Figure 4.6.3.3. The operation does not read that
figure, calculate a whole-frame buckling load, or validate the supplied frame
model and evidence.

## Global plastic-analysis equilibrium

`plastic_global_equilibrium` checks the three components of total force and
moment resultants for Clause 4.5.1. Supply all applied loads and support
reactions, with at least one of each, using consistent signs, a right-handed
coordinate system and one origin.
For each action, `position_mm` locates its force vector and `moment_knm` is its
applied couple; the operation converts the position to metres and adds
`position × force` to the couple when summing moments about the supplied origin.
It compares each resultant component with the supplied absolute force and
moment tolerances. Those tolerances are project-selected values, not prescribed
by this operation as standard limits.

The `boundary_conditions_verified` declaration and evidence reference are
recorded as supplied evidence. The operation does not authenticate support
conditions, determine whether the action list is complete, check member or joint
equilibrium, or perform or validate the structural analysis and plastic action
distribution. A passing result is limited to the reported global resultants and
the declared boundary-condition evidence. Use
`plastic_support_boundary_conditions` to compare supplied analysis translations
and rotations with prescribed values at listed support degrees of freedom.

## Joint action-distribution equilibrium

`plastic_joint_equilibrium` checks the three force and three moment residuals
at each supplied joint under Clause 4.5.1. At least two actions must be listed
at each joint, including at least one member-end action. Enter member-end
actions, nodal loads and support reactions using consistent signs in one
right-handed coordinate system. Forces are in kN, supplied moments in kN·m, and
`position_offset_mm` is measured from the joint; the operation converts offsets
to metres and adds `position offset × force` to each supplied moment vector.

Force and moment residuals are compared component by component with the
project-selected tolerances. `joint_actions_complete_verified` and its evidence
reference record the user's declaration that the listed joint actions are
complete. The calculation does not authenticate that declaration, confirm
member connectivity, check member-span equilibrium, verify support conditions,
or validate the structural analysis. The separate
`plastic_support_boundary_conditions` operation compares listed support
restraints against supplied analysis values.

## Member-span equilibrium

`plastic_member_span_equilibrium` checks the force and moment resultants for
each listed member under Clause 4.5.1. Enter the member vector from its start
end to its end end in global axes. End forces act on the member; the start-end
moment is about the start, and the end-end moment is about the end. Span action
forces and free couples use the same global axes, with each position offset
measured from the member start. This lets a distributed load be represented by
its equivalent resultant and couple, or individual applied loads be entered
separately. The calculation reports the residual moments about the member
start, adding each force's position cross force contribution.

Supply the complete span action list, member geometry and evidence references.
The geometry, member list, load resultants, and completeness declarations are
not authenticated. Tolerances are project-selected. This checks the listed
member free-body resultants; it does not derive distributed-load resultants,
check joint or whole-structure equilibrium, or validate the structural model.

## Support boundary-condition checks

`plastic_support_boundary_conditions` compares supplied analysis translations
and rotations at restrained support degrees of freedom with their prescribed
values. Use `ux`, `uy` and `uz` with millimetre values and tolerances, and `rx`,
`ry` and `rz` with radian values and tolerances. Each restrained degree of
freedom may be listed once per support. Tolerances are project-selected; the
standard does not prescribe values through this operation.

The support restraint and complete support-list declarations require evidence
references. The calculation checks the listed analysis values against the
declared restraints; it does not authenticate support identity, decide which
restraints apply, check other member restraints or solve the structural model.

## Plastic-analysis limits

`plastic_analysis_limits` checks the prescriptive Clause 4.5.2 route. Supply one
material record for every grade used and one member record for each member in the
plastic analysis. For each material, it checks the 450 MPa specified yield limit,
the listed material standard, a yield plateau extending at least six yield
strains, the 1.2 tensile-to-yield ratio, 15% elongation verified to AS 1391, and
verified strain-hardening capability. For each member, it checks hot forming,
doubly symmetric I-section form, compactness to Clause 5.2.3, and assessed
absence of impact loading and fatigue-required fluctuating loading.

The stress-strain curve, material certificate, member form and compactness are
supplied assessments linked by evidence reference. The operation does not
evaluate the alternate Clause 4.5.2 ductility route or design-load rotation
capacity.

## Alternative ductility assessment

`plastic_alternative_ductility_assessment` provides a bounded assessment record
for the Clause 4.5.2 alternative. List each required member and connection with
its design-loading rotation demand and assessed plastic rotation capacity, in
radians. The operation calculates each demand-to-capacity ratio and checks that
the demand does not exceed capacity. It also requires verified declarations
that the member and connection lists are complete, the analysis covers the
design loading conditions, and the structure-level ductility assessment is
complete, each with an evidence reference.

Rotation demands, capacities and adequate structure-level ductility are not
derived by the operation. The evidence declarations and assessed values are
not authenticated. A passing result means the supplied comparisons and gates
pass; it does not independently demonstrate adequate structural ductility or
full Clause 4.5.2 compliance.

## Connection and hinge conditions

`plastic_analysis_connections` checks selected Clause 4.5.3 conditions. Declare
that a rigid-plastic analysis is used, list every assumed full- or partial-
strength connection, and list every hinge in the collapse mechanism. For a
full-strength connection, the operation compares connection design moment
capacity with connected-member design moment capacity. For a partial-strength
connection, it requires verified development of every plastic hinge needed by
the mechanism. Both routes require verified use of connection capacity in the
analysis. For each listed hinge, the rotation capacity must be at least the
assessed rotation demand; rotations are in radians.

Connection capacities, mechanism completeness and hinge rotation assessments
remain evidence inputs. The check does not perform the plastic analysis or
verify global equilibrium, boundary conditions, or the collapse mechanism.
