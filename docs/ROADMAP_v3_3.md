# v3.3 Development Roadmap

v3.3 is an Issue-driven planning cycle on the v3.2.x development branch. It
preserves all v1.x–v3.2 public contracts and keeps every candidate design-only
until a separately reviewed implementation Issue is accepted.

## Must

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V33-ARC-01 | Ratify additive platform boundaries and migration fixtures. | P0 | Production evidence must not acquire Core authority. | All public surfaces | M | Architecture / Application | v3.2 baseline |
| V33-PPL-01 | Define Pipeline Template and stage-view contracts. | P0 | Production flow needs visible, reusable legal-stage evidence. | Workflow / Production | M | Application | V33-ARC-01 |
| V33-QLT-01 | Define Quality Dashboard and source-provenance contracts. | P0 | Quality evidence must remain human-owned and explainable. | Quality / Review | M | Application / Analytics | V33-ARC-01 |
| V33-AST-01 | Define Asset Lifecycle and history projection contracts. | P0 | Asset ownership and retention need a safe evidence model. | Repository / Knowledge | M | Knowledge / Application | V33-ARC-01 |
| V33-PRJ-01 | Define Project Health and delivery-forecast contracts. | P0 | Production planning needs bounded, non-authoritative insight. | Project / Operations | M | Analytics / Application | V33-ARC-01 |

## Should

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V33-PPL-02 | Design approval and publishing prerequisite views. | P1 | Human hand-offs need visible required evidence. | Workflow / Release | M | Application | V33-PPL-01 |
| V33-QLT-02 | Design review quality, consistency, regression, and trend reports. | P1 | Review signals need bounded comparison. | Quality / Analytics | M | Analytics | V33-QLT-01 |
| V33-AST-02 | Design dependency graph, archive policy, audit, and analytics. | P1 | Lifecycle evidence needs provenance and retention context. | Asset / Repository | L | Knowledge / Analytics | V33-AST-01 |
| V33-PRJ-02 | Design schedule, resource, milestone, and risk analytics. | P1 | Project insights need transparent assumptions. | Project / Operations | L | Analytics | V33-PRJ-01 |
| V33-QG-01 | Define deterministic compatibility, safety, benchmark, and docs gates. | P1 | Planning needs objective admission evidence. | Quality / DX | S | Developer Platform | V33-ARC-01 |

## Could

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V33-PPL-03 | Compare supplied pipeline policy snapshots. | P2 | Teams may need reviewable policy differences. | Production | M | Analytics | V33-PPL-01 |
| V33-AST-03 | Explore asset lifecycle recommendation wording. | P2 | Operators may benefit from advisory retention evidence. | Asset / Operations | M | Analytics | V33-AST-02 |
| V33-PRJ-03 | Explore delivery forecast explanations. | P2 | Forecast assumptions need clear human interpretation. | Project / Reporting | M | Analytics | V33-PRJ-02 |

## Won't

| Item | Reason |
| --- | --- |
| Autonomous AI execution or approval | Human review and StateMachine authority remain mandatory. |
| Cloud SaaS, marketplace, or distributed runtime | Requires a separate trust, operations, and ownership model. |
| Core redesign or breaking API change | v3.2 public contracts are the compatibility baseline. |
| Automatic archive, delete, publish, scheduling, or release action | Lifecycle and pipeline work is planning and diagnostics only. |
