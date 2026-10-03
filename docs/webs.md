# Web geometry and resistance checks

The `webs` family contains selected AS 4100:2020 web checks. Thickness and opening
operations compare supplied geometry with Clause 5.10 limits; they do not calculate
member shear, bearing or reduced capacity at an opening.

| Operation | Calculated provisions | Required assessment |
| --- | --- | --- |
| `web_minimum_thickness` with `design_case=unstiffened` | 5.10.1 minimum thickness for a web bounded by flanges or with one longitudinal free edge | Verify web depth, yield stress, edge condition and thickness. A lesser thickness based on rational analysis is outside this operation. |
| `web_minimum_thickness` with `design_case=transversely_stiffened` | 5.10.4 thickness bands based on stiffener spacing; applies 5.10.1 when `s/dp > 3` | Verify clear web depth, greatest panel depth and transverse stiffener spacing. Longitudinal stiffeners are not included in this case. |
| `web_minimum_thickness` with `design_case=longitudinal_and_transverse` | 5.10.5 thickness bands for longitudinal stiffeners at `0.2 d2`, with the additional neutral-axis stiffener limit | Verify the stiffener layout and `d2`, which is twice the distance from the neutral axis to the compression flange. The operation does not check stiffener strength or attachment. |
| `web_minimum_thickness` with `design_case=plastic_hinge` | 5.10.6 minimum web thickness and the load-bearing-stiffener trigger near a plastic hinge | Verify hinge location, the hinge-zone design load, design web shear yield capacity, stiffener location and Clause 5.14 design. |
| `web_opening_geometry` | 5.10.7 unstiffened opening dimension ratios, spacing between adjacent openings and the multiple-opening condition | Verify opening dimensions and layout; use the greater opening dimension when adjacent openings differ. Stiffened openings, castellated members and member capacity at openings require rational analysis. |
| `load_bearing_stiffener_requirement` | 5.10.2 load-bearing stiffener trigger when a design bearing force exceeds the design capacity of the web alone, or an end post is required | Supply the design web bearing capacity from 5.13.2 and assess the end-post trigger under 5.15.2.2. Stiffener resistance, detailing and force transfer remain separate checks. |
| `load_bearing_stiffener_attachment` | 5.14.4 flange fit or flange-to-stiffener transfer, both-flange provision at a support, and force transfer from the stiffener to the web | Supply capacities from the applicable Clause 9 checks and verify the flange fit and connection arrangement against the details. |
| `end_post_area` | 5.15.9 end-plate minimum area when an end post is required under 5.15.2.2 | Supply the assessed shear buckling coefficient, nominal web shear yield capacity, capacity factor, end-plate material, and end-plate-to-stiffener distance. Design the load-bearing stiffener and end-plate connections separately. |
| `web_side_reinforcement` | 5.10.3 limit on shear allocated to side plates by plate resistance and the fastener transfer capacities to the web and flanges | Supply design capacities from the plate and connection checks. The assigned shear must already account for any asymmetry; the operation requires that assessment to be declared. |

`web_bearing` calculates selected Clause 5.13.1 force dispersion for I-sections and
channels when flange thickness, stiff bearing length and flange-to-neutral-axis
distance are supplied. It uses `b_bf = b_s + 5 t_f` through the flange, then a 1:1
spread to the neutral axis. The caller must verify that the geometry matches
Figure 5.13.1.1; assessed bearing widths remain accepted for cases where the
dispersion has already been established. RHS/SHS bearing dispersion is calculated
from its Clause 5.13.3 geometry inputs.

`transverse_stiffener` checks flange termination gaps under 5.15.1 when both gaps
and verified geometry are supplied. `web_bearing`, `rhs_bearing_bending`,
`load_bearing_stiffener`, `transverse_stiffener` and `longitudinal_stiffener` provide selected checks under
Clauses 5.13–5.16. `load_bearing_stiffener` checks 5.14.1–5.14.3 and calculates
the optional 5.14.5 minimum second moment of area for stiffener pairs when they provide the sole
torsional end restraint; supply the flange centroid spacing, critical flange
thickness, total design load between supports and pair inertia about the web
centreline. Its torsional coefficient is limited to 0–4 as specified by the clause.
Clause 5.14.4 flange fit and force-transfer detailing remains an assessed input.
Their inputs and limitations remain explicit in each result.
General shear/bending interaction, complete
end-post and stiffener design, and all attachment/load-transfer checks still need
engineering review.
