# Design actions and stability

`run_design_actions` implements selected checks for AS 4100:2020 Sections 3 and
4. All action and capacity inputs are kN or kN·m unless the field name states
otherwise. Evidence references identify supporting project records; the plugin
does not authenticate those records.

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
