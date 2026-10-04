# v3.5 Development Roadmap

v3.5 is an Issue-driven planning cycle on the `3.4.x` development branch. It
preserves documented v1.x through v3.4 public contracts. Every candidate stays
design-only until a separately reviewed implementation Issue is accepted.

## Must

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V35-ARC-01 | Ratify v3.5 cross-platform boundaries and migration fixtures. | P0 | Cross-cutting analysis must not acquire Core authority. | All public surfaces | M | Architecture / Application | v3.4 baseline |
| V35-KG-01 | Define Unified Knowledge Graph and relationship-engine contracts. | P0 | Knowledge connections need provenance-aware, bounded projections. | Knowledge / Repository | M | Knowledge / Application | V35-ARC-01 |
| V35-CI-01 | Define Creative Dashboard and metric contracts. | P0 | Creative evidence needs transparent human review. | Creative / Review | M | Application / Analytics | V35-ARC-01 |
| V35-PI-01 | Define Production Efficiency and Pipeline Analytics contracts. | P0 | Production evidence needs explainable constraint analysis. | Production / Workflow | M | Application / Analytics | V35-ARC-01 |
| V35-PA-01 | Define Executive Dashboard and cross-platform analytics contracts. | P0 | Leaders need bounded, comparable evidence. | Analytics / Reporting | M | Analytics / Application | V35-ARC-01 |

## Should

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V35-KG-02 | Design context, traceability, quality metrics, and insights. | P1 | Relationships require explainable provenance and quality context. | Knowledge / Governance | L | Knowledge / Analytics | V35-KG-01 |
| V35-CI-02 | Design story, character, page-quality, and recommendation reports. | P1 | Creative review needs consistent evidence, not automated judgment. | Creative / Quality | L | Application / Analytics | V35-CI-01 |
| V35-PI-02 | Design capacity forecast, risk prediction, delivery, and operations insights. | P1 | Operators need advisory forecasts with stated assumptions. | Production / Operations | L | Analytics / Application | V35-PI-01 |
| V35-PA-02 | Design trend, historical, regression, and platform-health reports. | P1 | Cross-platform reports need deterministic local comparison. | Analytics / Operations | L | Analytics | V35-PA-01 |
| V35-QG-01 | Define compatibility, provenance, security, benchmark, and docs gates. | P1 | Issue admission needs objective, repeatable evidence. | Quality / DX | S | Developer Platform | V35-ARC-01 |

## Could

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V35-KG-03 | Explore supplied knowledge-trace comparison views. | P2 | Reviewers may need to compare bounded snapshots. | Knowledge / Reporting | M | Analytics | V35-KG-02 |
| V35-CI-03 | Explore creative recommendation explanation templates. | P2 | Recommendations need transparent wording and uncertainty. | Creative / DX | M | Application | V35-CI-02 |
| V35-PI-03 | Explore delivery-risk explanation and sensitivity views. | P2 | Forecasts need explainable assumptions, not commitments. | Production / Reporting | M | Analytics | V35-PI-02 |
| V35-PA-03 | Explore historical regression comparison presentation. | P2 | Maintainers may benefit from local evidence timelines. | Analytics / Reporting | M | Analytics | V35-PA-02 |

## Won't

| Item | Reason |
| --- | --- |
| Autonomous AI execution, creative decision, workflow action, or approval | Human review and StateMachine authority remain mandatory. |
| Cloud SaaS, marketplace, or distributed runtime | Requires a separate trust, operations, ownership, and security model. |
| Core redesign or breaking API change | v3.4 public contracts are the compatibility baseline. |
| Remote collection, hidden persistence, scheduling, deployment, tagging, signing, or publication | Analytics and intelligence remain local, supplied-input diagnostics only. |
