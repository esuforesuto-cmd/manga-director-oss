# v3.4 Development Roadmap

v3.4 is an Issue-driven planning cycle on the `3.3.x` development branch. It
preserves documented v1.x through v3.3 public contracts and keeps each
candidate design-only until a separately reviewed implementation Issue is
accepted.

## Must

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V34-ARC-01 | Ratify v3.4 platform boundaries and migration fixtures. | P0 | New reporting areas must not acquire Core authority. | All public surfaces | M | Architecture / Application | v3.3 baseline |
| V34-KNO-01 | Define Knowledge Catalog and relationship contracts. | P0 | Knowledge evidence needs discoverable, provenance-aware projections. | Knowledge / Repository | M | Knowledge / Application | V34-ARC-01 |
| V34-OPS-01 | Define Operations Dashboard and monitoring-evidence contracts. | P0 | Operators need bounded operational context. | Production / Operations | M | Application / Analytics | V34-ARC-01 |
| V34-ORG-01 | Define redacted organization evidence contracts. | P0 | Collaboration evidence needs human-safe interpretation. | Organization / Collaboration | M | Analytics / Application | V34-ARC-01 |
| V34-REL-01 | Define Release Dashboard and release-health contracts. | P0 | Release evidence must remain explainable and non-authoritative. | Release / Quality | M | Application / Analytics | V34-ARC-01 |

## Should

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V34-KNO-02 | Design search strategy, quality metrics, governance, and insights. | P1 | Catalogs need bounded discovery and quality context. | Knowledge / Governance | L | Knowledge / Analytics | V34-KNO-01 |
| V34-OPS-02 | Design capacity, incident timeline, audit, and analytics reports. | P1 | Operations evidence needs traceable context. | Operations / Diagnostics | L | Analytics / Application | V34-OPS-01 |
| V34-ORG-02 | Design role, workload, collaboration, risk, and confidence projections. | P1 | Teams need explainable planning evidence, not automation. | Organization / Project | L | Analytics | V34-ORG-01 |
| V34-REL-02 | Design metrics, deployment, compatibility, and regression intelligence. | P1 | Release review needs evidence aggregation. | Release / Compatibility | L | Analytics / Developer Platform | V34-REL-01 |
| V34-QG-01 | Define deterministic compatibility, safety, benchmark, and docs gates. | P1 | Issue admission needs objective evidence. | Quality / DX | S | Developer Platform | V34-ARC-01 |

## Could

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V34-KNO-03 | Compare supplied knowledge-policy snapshots. | P2 | Operators may need reviewable policy differences. | Knowledge / Governance | M | Analytics | V34-KNO-02 |
| V34-OPS-03 | Explore advisory capacity recommendation wording. | P2 | Operations reviews may benefit from bounded guidance. | Operations | M | Analytics | V34-OPS-02 |
| V34-ORG-03 | Explore delivery-confidence explanations. | P2 | Assumptions need clear human interpretation. | Organization / Reporting | M | Analytics | V34-ORG-02 |
| V34-REL-03 | Explore release evidence timeline comparisons. | P2 | Maintainers may benefit from historical context. | Release / Reporting | M | Analytics | V34-REL-02 |

## Won't

| Item | Reason |
| --- | --- |
| Autonomous AI execution, approval, personnel assessment, or work assignment | Human review and StateMachine authority remain mandatory. |
| Cloud SaaS, marketplace, or distributed runtime | Requires a separate trust, operations, and ownership model. |
| Core redesign or breaking API change | v3.3 public contracts are the compatibility baseline. |
| Automatic monitoring response, deployment, tagging, signing, publication, or release action | Operations and release work are planning and diagnostics only. |
