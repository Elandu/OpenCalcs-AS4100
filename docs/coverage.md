# AS 4100:2020 coverage map

This map describes the bounded version 0.2.0 implementation. **Calculated**
means a stated operation evaluates an equation or compares supplied values.
**Assessed** means the user must establish applicability, inputs and supporting
evidence independently. **Missing** identifies examples of provisions for
which no complete software check is available. An operation's pass applies only
to its declared scope; it is not a Section or whole-standard pass. The
`design_review` family schedules operations and records engineering evidence
for every Section, but does not independently validate that evidence.

| Section | Calculated or compared in this release | Assessed externally; remaining gaps |
| --- | --- | --- |
| 1 — Scope and general | No normative design check. `design_review` records scope evidence. | Applicability, exclusions, edition, referenced standards and project basis; no automatic scope decision. |
| 2 — Materials | Supplied strengths and elastic properties feed selected calculations. | Certified steel, bolt and weld properties, thickness/product effects and material suitability; no material catalogue or automatic grade selection. |
| 3 — Design requirements | `design_actions`: 3.2.4 notional horizontal load, 3.3 stability effect and 3.5 serviceability deflection comparison. | Select governing action combinations, reliability/serviceability criteria, restraint and load paths; no load generator or complete limit-state assessment. |
| 4 — Structural analysis | `design_actions`: selected Euler load, elastic moment/storey sway and plastic amplification calculations. | Establish analysis model, effective lengths, second-order effects and restraints; no full frame analysis, eigenvalue analysis or model verification. |
| 5 — Bending members | `member_design`: selected 5.2 plate classification, 5.6.1 equal-flange lateral buckling, 5.11 shear and 5.12.3 interaction. `advanced_members`: selected 5.6.4 analysis-input buckling, 5.7 nonprincipal bending, 5.4.3 restraint force and 5.8 separator/diaphragm minimum force. `webs`: selected 5.13–5.16 bearing/stiffener checks. | Supply section properties, actual restraints and load position, web configuration and force paths. Unequal-flange/monosymmetric LTB, several 5.3–5.10 paths and complete web/stiffener detailing remain unsupported. |
| 6 — Compression members | `section_analysis`: 6.2.1 section capacity. `member_design`: selected 6.2–6.3 constant-section flexural buckling. `advanced_members`: 6.3.4 varying-section and selected 6.4–6.6 built-up/restraint calculations. | Supply assessed section constants, effective lengths, rational variable-section buckling load and component/connection checks. Rational torsional-flexural analysis and complete restraint-system design are missing. |
| 7 — Tension members | `section_analysis`: 7.2 gross/net section capacity. `member_design`: selected 7.3 tension-distribution arrangements. `advanced_members`: selected 7.4 lacing/batten and 7.5 pin-member geometry. | Establish all net paths, `kt`, force transfer, built-up spacing and pin/connection capacities; no automatic arrangement or complete built-up-member approval. |
| 8 — Combined actions | `member_design`: selected 8.3 section and 8.4 elastic member interactions. `advanced_members`: selected 8.4.3 plastic in-plane check and 8.4.6 angle eccentricity/minimum moment. | Supply concurrent design actions and reduced capacities. 8.4.6 special angle interaction capacity, further compact-section alternatives and plastic frame eligibility remain unresolved. |
| 9 — Connections | `connection_design`: selected bolt, bearing, slip, block-shear, pin, weld, group, layout and hole-deduction operations. | Enumerate all components/paths and externally assess eccentricity, prying, nonstandard geometry, fabrication and installation. No complete connection certificate. |
| 10 — Brittle fracture | `durability`: selected 10.4 temperature/thickness table and adjustments. | Determine service temperature, product type, grade/certification and fabrication condition; 10.5 fracture-mechanics assessment is absent. |
| 11 — Fatigue | `durability`: selected 11.4 exemption, 11.6–11.9 constant/variable stress-range and damage checks. | Classify details, obtain stress spectra and cycle counts, verify weld/inspection conditions and reference-detail applicability; no automatic stress extraction or category selection. |
| 12 — Fire | `durability`: selected 12.4 material reductions, 12.5 limiting temperature, 12.6.2.2 regression evaluation, 12.7 unprotected time and 12.8 single-test comparison. | Establish FRL, member and connection response, protection test evidence and actual exposure. Regression fitting, complete protected-member interpolation, grouping and connection protection are missing. |
| 13 — Earthquake | `durability`: selected Table 13.3.4 factors, grade limit and panel movement comparison; manual-review flags. | Establish seismic category, system, external loading standards, ductility detailing and connections. No complete earthquake design or approval. |
| 14 — Fabrication | No fabrication calculation. `design_review` records evidence. | Drawings, tolerances, welding procedures, inspection and referenced construction requirements require records and review. |
| 15 — Erection | No erection calculation. `design_review` records evidence. | Temporary stability, installation, inspection and site records require review. |
| 16 — Modification of existing structures | `testing`: existing-material prerequisite audit for 16.1–16.2. | Identify base metal, condition and repairs, then reanalyse the structure. No material-test acceptance method or existing-structure certificate. |
| 17 — Load testing | `testing`: selected 17.3–17.6 proof/prototype load, dwell, deformation and declared-condition comparisons. | Plan/calibrate physical tests, establish representative loading/restraints, inspect damage and authenticate reports. No physical test execution or certification. |

Appendix B deflection suggestions are available in `testing`; they are
informative and require a project-selected serviceability limit. No numerical
coverage in a Section should be read as coverage of every clause in that
Section. Detailed operation limits are documented in the family notes linked
from the [README](../README.md).
