# Design actions and stability

`run_design_actions` implements selected checks for AS 4100:2020 Sections 3 and
4. All action and capacity inputs are kN or kN·m unless the field name states
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
