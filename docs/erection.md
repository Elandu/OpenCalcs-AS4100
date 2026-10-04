# Erection and bolt installation checks

The `structural.as4100.erection` family implements selected provisions of AS
4100:2020 Sections 15 and 17 acceptance cross-references. It evaluates one
declared erection, bolted-assembly, tolerance or item-acceptance operation per
call. This family does not design temporary works or determine whether a
project is safe to erect.

`erection_safety_and_procedure` checks declarations for safety against erection
loads, including equipment and wind, and for erection procedures and site
modifications that comply with AS/NZS 5131 (15.1.2 and 15.2.1). The inputs are
evidence flags; no erection analysis or procedure is generated.

`bolted_connection_assembly` supports snug-tight and fully tensioned
connections. The snug-tight route checks the supplied AS/NZS 5131 assembly
declaration under 15.2.2.1 and does not apply a minimum-tension table. For a
fully tensioned group, the operation checks each listed bolt against Table
15.2.2.2, requires a homogeneous and complete group declaration, and checks
the selected part-turn or direct-tension-indicator method against its AS/NZS
5131 declaration. The table values are:

| Nominal bolt | Grade 8.8 (kN) | Grade 10.9 (kN) |
| --- | ---: | ---: |
| M16 | 95 | 130 |
| M20 | 145 | 205 |
| M24 | 210 | 295 |
| M30 | 335 | 465 |
| M36 | 490 | 680 |

The fully tensioned input requires a unique identifier and measured tension for
each bolt. It cannot establish that every physical bolt has been recorded; the
complete bolt-group declaration must be checked against installation records.
The AS/NZS 5131 method details and measurement procedures are not reproduced.

`geometric_tolerance` compares a measured erection deviation with a permissible
value supplied and verified against AS/NZS 5131. Measurement must be confirmed
after erection is complete (15.3.1). Functional tolerance Class 1 applies when
no class is supplied. An out-of-limit functional tolerance fails. An
out-of-limit essential tolerance passes this check only when its inclusion in
a revised design-capacity calculation is declared under 15.3.2. The revised
capacity analysis remains a separate engineering calculation.

`erected_item_acceptance` evaluates the evidence routes in 15.1.1. An item that
does not satisfy both 15.2 and 15.3 may be accepted through a declared
demonstration that structural adequacy and intended use are unimpaired, or a
declared successful Section 17 test. Bolt hardware that does not conform to
14.3.3 and 15.2 requires the structural-adequacy route; a Section 17 test flag
alone does not override that hardware condition. These inputs summarize
engineering evidence and do not make the acceptance decision.

No result authenticates drawings, measurements, installation or test records.
Complete erection stability, temporary bracing, load sequencing, every
AS/NZS 5131 requirement, numerical tolerance limits, test planning and
acceptance review remain outside this family. `full_standard_compliance`
remains false.
