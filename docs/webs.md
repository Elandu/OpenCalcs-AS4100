# Web geometry and resistance checks

The `webs` family contains selected AS 4100:2020 web checks. Thickness and opening
operations compare supplied geometry with Clause 5.10 limits. The opening shear
operation also checks shear and whole-section shear/bending resistance using evidenced
opening-area and rational-analysis inputs; it does not perform that analysis.

`web_panel_geometry` derives the Clause 5.9.2 panel dimensions from verified clear
boundary stations. `web_minimum_thickness` records Clause 5.9.3 for each prescriptive
route; a lower thickness supported by rational analysis is assessed separately.

| Operation | Calculated provisions | Required assessment |
| --- | --- | --- |
| `web_panel_geometry` | 5.9.2 longitudinal panel dimension `dp`, clear transverse dimension `d1`, panel list and maximum dimensions from an orthogonal boundary grid; `greatest_panel_longitudinal_dimension_mm` is the maximum `dp` for direct use by 5.10.4 | Supply complete web extents and internal boundary stations measured to clear panel edges. Verify that every boundary is continuous across the full web extent or depth and that free edges/openings are represented. The operation does not authenticate the referenced drawing. |
| `web_minimum_thickness` with `design_case=unstiffened` | 5.10.1 minimum thickness for a web bounded by flanges or with one longitudinal free edge | Verify web depth, yield stress, edge condition and thickness. A lesser thickness based on rational analysis is outside this operation. |
| `web_minimum_thickness` with `design_case=transversely_stiffened` | 5.10.4 thickness bands use `s/d1`; web lengths with `s/dp > 3` use the 5.10.1 unstiffened limit | Supply `greatest_panel_longitudinal_dimension_mm` from 5.9.2 and verify clear web depth `d1`, stiffener spacing `s`, yield stress and layout. The former `greatest_panel_depth_mm` input remains as a deprecated alias. Longitudinal stiffeners are not included in this case. |
| `web_minimum_thickness` with `design_case=longitudinal_and_transverse` | 5.10.5 thickness bands for longitudinal stiffeners at `0.2 d2`, with the additional neutral-axis stiffener limit | Verify the stiffener layout and `d2`, which is twice the distance from the neutral axis to the compression flange. The operation does not check stiffener strength or attachment. |
| `web_minimum_thickness` with `design_case=plastic_hinge` | 5.10.6 minimum web thickness and load-bearing-stiffener trigger near a plastic hinge; optional per-plate 5.2.2 slenderness against the Table 5.2 plasticity limit for flat stiffeners | Verify hinge location, the hinge-zone design load, design web shear yield capacity, stiffener location and Clause 5.14 design. Supply every flat stiffener plate when using the plasticity check, with its clear outstand, thickness, yield stress and residual-stress category. |
| `web_opening_geometry` | 5.10.7 unstiffened opening dimension ratios, spacing between adjacent openings and the multiple-opening condition | Verify opening dimensions and layout. For adjacent openings, supply the greatest internal dimension of the neighboring opening; required boundary spacing uses three times the larger dimension in the pair. Check each adjacent pair. Stiffened openings, castellated members and member capacity at openings require rational analysis. |
| `web_opening_layout_geometry` | 5.10.7 size limits for every opening, longitudinal boundary spacing for every adjacent pair in overlapping transverse bands, and the maximum number of openings at any member cross-section | Supply the complete non-castellated web layout on a common longitudinal/transverse datum. Each opening needs longitudinal and transverse clear bounds and its greatest internal dimension; that dimension must be at least either clear extent. Adjacent pairs are derived by partitioning the web depth at opening boundaries and sorting the openings in each transverse band. The 0.10 limit applies without longitudinal web stiffeners and 0.33 with them. A section through multiple openings requires a referenced, separately verified rational analysis showing stiffeners are unnecessary. Geometry and completeness declarations are not authenticated. |
| `web_shear_stress_field_postprocess` | 5.11.3 area-weighted average design shear stress, governing maximum-to-average ratio and nominal-capacity reduction factor for a flat web at one section cut and load combination | Supply signed longitudinal/transverse shear stresses and cross-section area weights covering the complete actual web steel area. The operation integrates the web shear resultant, compares it with the independently established web share of shear, and checks the integrated area against the declared cut area. Supply the governing peak stress and mesh-sensitivity assessment; the true maximum is not inferred from samples alone. The force-equilibrium tolerance is a software quality threshold, not a standard requirement. It reports the reduction factor only and does not calculate the 5.11.2 uniform-distribution nominal capacity. Circular hollow sections use the separate 5.11.3 exception and are rejected by this operation. |
| `web_opening_shear_design` | 5.10.7 qualifying unstiffened opening geometry; 5.11.1–5.11.5 web shear resistance using the supplied opening web area, panel dimensions and verified maximum/average shear-stress ratio; 5.12.3 whole-section shear/bending interaction | Provide a verified web-area basis and referenced rational elastic analysis for the supplied maximum and average design shear stresses. Check adjacent-opening spacing and all geometry. The operation does not perform or authenticate the analysis and does not calculate local opening bending/bearing resistance; stiffened or castellated openings remain outside this route. |
| `load_bearing_stiffener_requirement` | 5.10.2 load-bearing stiffener trigger when a design bearing force exceeds the design capacity of the web alone, or an end post is required; optional nested calculation of 5.13.1–5.13.4 web bearing capacity | Supply the design web bearing capacity from 5.13.2, or provide the full `web_bearing_inputs` object to calculate it in this operation. Assess the end-post trigger under 5.15.2.2. Stiffener resistance, detailing and force transfer remain separate checks. |
| `load_bearing_stiffener_attachment` | 5.14.4 flange fit or flange-to-stiffener transfer, both-flange provision at a support, and force transfer from the stiffener to the web | Supply capacities from the applicable Clause 9 checks and verify the flange fit and connection arrangement against the details. |
| `rhs_bearing_bending` | 5.2 and 5.13.2 individual design-capacity comparisons; 5.13.5 combined bending and bearing interaction for rectangular/square hollow sections to AS/NZS 1163 | Verify and reference the section form and its geometry separately, the Clause 5.2 design moment capacity and the Clause 5.13.2 design bearing capacity. Supply capacities with capacity factors already included. |
| `transverse_stiffener` | 5.15.2.1 interior-panel spacing via 5.10.4/5.10.5; 5.15.3–5.15.4 area and buckling checks with supplied capacities or geometry-derived 5.11.2/5.11.5 and 5.14.2 capacities (`le=d1`); 5.15.5 minimum inertia; 5.15.6 outstand limit via 5.14.3; 5.15.8 web-connection shear per unit length when no external stiffener actions apply | Verify panel geometry and stiffener layout. For the 5.10.4 route, supply `greatest_panel_longitudinal_dimension_mm` from 5.9.2; the check cannot infer clear panel length from stiffener spacing. For calculated capacities, supply the effective-section radius of gyration and available web widths. Otherwise supply the nominal capacities and shear buckling coefficient. Supply a verified design connection capacity per unit length from the relevant Clause 9 checks. For 5.10.5, supply `d2` and state whether a neutral-axis stiffener set is present. The 5.15.6 outstand limit uses stiffener thickness and design yield stress; declare continuous restraint at the outer edge only when detailed. Use `end_panel_design` for the reduced end-panel alternative. |
| `end_panel_design` | 5.15.2.2 reduced-width end-panel alternative, using 5.11.1 shear capacity and 5.12 shear/bending interaction with `alpha_d=1.0` | Verify original and reduced panel widths, web geometry and stress ratio. Supply concurrent shear/moment actions and the section moment capacity. The alternative end-post route is handled by `end_post_design`. |
| `end_post_design` | 5.15.2.2 end-post alternative, linked 5.14.1–5.14.4 stiffener resistance and attachment checks, optional 5.14.5 torsional restraint, and 5.15.9 end-plate area | Supply the governing bearing reaction, web bearing yield resistance, effective section properties, restraint and connection capacities. Verify that the stiffener is no smaller than the end plate. End-plate connection design and geometry remain separate Section 9 checks. |
| `end_post_area` | 5.15.9 end-plate minimum area calculation when an end post is required under 5.15.2.2 | Supply the assessed shear buckling coefficient, nominal web shear yield capacity, capacity factor, end-plate material, and end-plate-to-stiffener distance. Use `end_post_design` to link this calculation to the load-bearing stiffener checks. |
| `web_side_reinforcement` | 5.10.3 limit on shear allocated to side plates by plate resistance and the fastener transfer capacities to the web and flanges | Supply design capacities from the plate and connection checks. The assigned shear must already account for any asymmetry; the operation requires that assessment to be declared. |

For 5.10.4, `s/dp = 3` remains in the transversely stiffened route; only a ratio greater than 3 invokes 5.10.1. The clause gives no thickness band for `s/d1 > 3` when `s/dp` is no greater than 3, so that combination is rejected for separate assessment. Earlier output ratio keys remain available alongside the explicit `s/d1` and `s/dp` names.

`web_bearing` calculates selected Clause 5.13.1 force dispersion for I-sections and
channels when flange thickness, stiff bearing length, flange-to-neutral-axis
distance and `bearing_location` are supplied. It uses `b_bf = b_s + 5 t_f` through
the flange, then a 1:1 spread to the neutral axis. Interior bearing uses
`b_b = b_bf + 2 b_bw`; end bearing uses `b_b = b_o + b_bf + b_bw` and requires
`end_web_unspread_width_mm` for `b_o` in Figure 5.13.1.1(b). Verify the selected
location and geometry against the member details. Assessed bearing widths remain
accepted for cases where dispersion has already been established. RHS/SHS bearing
dispersion is calculated from its Clause 5.13.3 geometry inputs.

`load_bearing_stiffener_requirement` accepts either the design force and web-only
design capacity, or a complete `web_bearing_inputs` object using the `web_bearing`
schema. The nested route calculates the Clause 5.13.2 capacity and uses its action
to determine the 5.10.2 stiffener trigger. A force above web-only capacity triggers
stiffeners; the parent result passes when the required stiffeners are provided.
End-post classification under 5.15.2.2 remains an assessed input.

`rhs_bearing_bending` checks the two Clause 5.13.5 interaction branches, selecting
the wider-bearing/compact-web expression only when both `bs/b >= 1.0` and
`d1/tw <= 30`; equality is included in that branch. It separately checks the
supplied design bearing and moment capacities under Clauses 5.13.2 and 5.2.
The capacities must already include their capacity factors. The AS/NZS 1163 section
form, dimensions and both capacity derivations are separately evidence-gated by
nonblank references; the operation does not derive or authenticate them.

`transverse_stiffener` checks the interior-panel web-thickness condition under
5.15.2.1 by selecting the 5.10.4 or 5.10.5 route from the declared longitudinal-
stiffener arrangement. It checks flange termination gaps under 5.15.1 when both gaps
and verified geometry are supplied. For 5.15.5, it selects the minimum-inertia
expression at `s/d1 = sqrt(2)` and reports the controlling expression and ratio.
For 5.15.6, it applies the 5.14.3 outstand limit using the supplied stiffener
thickness and design yield stress, or accepts the declared continuously stiffened
outer edge. When external actions are supplied, it adds
the 5.15.7.1 stiffness increase to the Clause 5.15.5 inertia
minimum, using E from Clause 2.2.4 and the supplied capacity factor. A nonzero
transverse force parallel to the web also invokes 5.15.7.2: it runs the existing
5.14.1–5.14.3 load-bearing resistance checks and the 5.14.4 attachment checks,
using the same web and stiffener geometry as the transverse-stiffener inputs.
Supply the web bearing yield capacity from 5.13.3, contact area, effective radius,
restraint condition, available web widths, and 5.14.4 connection capacities and
force share.
The 5.14.5 torsional-restraint inputs are required when that provision applies.
Verify supplied resistance, force-share and connection evidence against the design
details. It accepts supplied capacities for 5.15.3/5.15.4 or calculates them from geometry:
Clause 5.11.2 and 5.11.5 provide the nominal web shear capacities, while 5.14.2 provides
the nominal stiffener buckling capacity with the 5.15.4 effective length `le=d1`. The
calculated path assumes `alpha_d=1` and `alpha_f=1`; the effective-section radius of
gyration is supplied and must be verified about the axis parallel to the web. With no
external stiffener actions, it checks the 5.15.8 web-connection shear per unit length
against the supplied Clause 9 design capacity and requires that capacity to be declared
verified. `longitudinal_stiffener` checks the 5.16.2
minimum inertia and optionally checks 5.16.1 when continuity and transverse-stiffener
end conditions are supplied. It passes the 5.16.1 detailing condition when continuous,
or when it spans between and is attached to transverse web stiffeners.

`end_panel_design` evaluates the reduced-width alternative in 5.15.2.2 through the
existing 5.11/5.12 shear design calculation, forcing the tension-field factor
`alpha_d` to 1.0. `end_post_design` evaluates the other alternative: it runs the
5.14 load-bearing stiffener resistance and attachment checks, calculates the 5.15.9
end-plate area, and requires an explicit verification that the stiffener is no smaller
than the plate. The governing bearing reaction and the relationship between end-panel
shear and bearing reaction are supplied engineering inputs. End-plate connections and
geometry still require separate design.

`web_opening_shear_design` combines the 5.10.7 geometry check for an unstiffened
opening with the existing web shear and 5.12.3 member interaction calculations.
It derives the maximum-to-average stress ratio from the referenced rational elastic
analysis inputs and reports separate 5.11.1 shear and 5.12.3 interaction checks.
The supplied opening area and panel geometry must represent the governing section.
Local tee bending, bearing and load redistribution at the opening require separate
engineering analysis.

`web_opening_layout_geometry` checks a complete declared layout of unstiffened openings
under 5.10.7. Opening bounds use a shared longitudinal datum and coordinates through
the clear web depth. It checks every opening's greatest internal dimension against the
applicable 0.10 or 0.33 ratio, derives adjacent longitudinal pairs within each band of
overlapping transverse extents, and finds the maximum number of openings at any
longitudinal station. Every opening that shares a section with another requires a
referenced rational analysis that has been assessed to show stiffeners are unnecessary.
The operation checks the supplied drawing dimensions and declared inventory; it does
not authenticate them or calculate opening actions or resistance. Its result is limited
to Clause 5.10.7 geometry, and `full_standard_compliance` remains false.

`web_shear_stress_field_postprocess` evaluates the stress-distribution inputs for Clause
5.11.3 for flat-web sections at one declared governing section cut and load combination.
Circular hollow sections are excluded because 5.11.3 specifies their shear yield capacity
route separately. Area weights must
represent cross-section integration over the complete actual web steel, not shell-panel
surface area. It derives the signed web shear resultant and average stress, checks area
coverage and force equilibrium, then reports `fvm/fva` and
`min(1, 2 / (0.9 + fvm/fva))`. The separately assessed governing peak must be no lower
than every supplied sample and must include mesh-sensitivity review. The operation does
not establish the uniform-distribution nominal shear capacity under 5.11.2 or calculate
the resulting member capacity; supply its average/maximum stresses or ratio to an
applicable shear design operation. Its equilibrium threshold is a software quality check,
not a code requirement.

`load_bearing_stiffener` checks 5.14.1–5.14.3 and calculates the optional 5.14.5
minimum second moment of area for stiffener pairs when they provide the sole torsional
end restraint. Supply flange centroid spacing, critical flange thickness, total design
load between supports and pair inertia about the web centreline. The torsional factor
is limited to 0–4 by the clause. `load_bearing_stiffener_attachment` checks 5.14.4
fit declarations and force transfer using capacities from Clause 9.

The operations cover selected provisions of Clauses 5.13–5.16. General shear/bending
interaction, complete end-post and stiffener design, and attachment/load-transfer
detailing still need engineering review.
