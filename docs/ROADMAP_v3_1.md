# v3.1 Development Roadmap

v3.1 is an Issue-driven planning cycle on the v3.0.x development branch. It
preserves all v3.0 public contracts and treats every candidate as design-only
until a separately reviewed implementation Issue is accepted.

## Must

| ID | Objective | Priority | Rationale | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V31-ARC-01 | Ratify v3.1 additive layer, migration, and compatibility contracts. | P0 | Prevent collaboration, Knowledge, or operations work from acquiring Core authority. | M | Architecture / Application | v3.0 baseline |
| V31-DIR-01 | Define long-term objectives, templates, decision history, strategy library, and creative metric DTO contracts. | P0 | Director planning needs consistent, explainable evidence before richer views. | M | Director / Planning | V31-ARC-01 |
| V31-COL-01 | Define Editor through Approval workspace and hand-off contracts. | P0 | Collaboration must retain human review and existing workflow guards. | M | Creative / Review | V31-ARC-01, V31-DIR-01 |
| V31-KNOW-01 | Define version, diff, merge-plan, snapshot, timeline, and analytics policy contracts. | P0 | Knowledge changes require governance before any persistence discussion. | L | Knowledge / Repository | V31-ARC-01 |
| V31-OPS-01 | Define observability, quality, release, project, and workflow report contracts. | P0 | Production operations need bounded evidence with no automation. | M | Operations / Observability | V31-ARC-01 |
| V31-QA-01 | Add architecture, compatibility, collaboration, Knowledge, and operations planning gates. | P0 | Every design needs enforceable admission criteria. | S | Quality / DX | V31-ARC-01 |

## Should

| ID | Objective | Priority | Rationale | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V31-DIR-02 | Design template comparison and strategy explainability fixtures. | P1 | Enables human choice between reproducible plan alternatives. | M | Director / Planning | V31-DIR-01 |
| V31-COL-02 | Design review comments, ownership, and approval-evidence projection. | P1 | Makes hand-offs auditable without creating an approval engine. | M | Creative / Review | V31-COL-01 |
| V31-KNOW-02 | Define conflict taxonomy, timeline pagination, and analytics interpretation guidance. | P1 | Keeps future Knowledge evolution safe and portable. | M | Knowledge / Governance | V31-KNOW-01 |
| V31-OPS-02 | Design dashboard/quality/release analytics preview examples. | P1 | Operations reporting needs contributor-visible contract examples. | S | Operations / DX | V31-OPS-01 |

## Could

| ID | Objective | Priority | Rationale | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V31-DIR-03 | Research deterministic creative metric fixtures. | P2 | Metrics need workload evidence before becoming recommendations. | M | Director / Research | V31-DIR-01 |
| V31-COL-03 | Draft local collaboration conflict simulation fixtures. | P2 | Validates hand-off terminology before any shared-editing design. | M | Quality / Creative | V31-COL-01 |
| V31-KNOW-03 | Research local merge-preview visualization DTOs. | P2 | Useful after conflict and retention policy are reviewed. | M | Knowledge / Presentation | V31-KNOW-02 |
| V31-OPS-03 | Draft capacity and maintenance planning report examples. | P2 | Informative only after metric definitions stabilize. | S | Operations / Research | V31-OPS-01 |

## Won't

| Item | Reason |
| --- | --- |
| Autonomous AI, automatic Agent execution, auto-approval, or multi-page generation | Contradicts human authority and StateMachine workflow invariants. |
| Cloud SaaS, marketplace, distributed runtime, or microservices | Requires separately approved tenancy, security, deployment, and recovery architecture. |
| Core redesign, Repository-port change, or breaking public API | v3.0 is the stable compatibility baseline. |
| Automatic Knowledge merge, remote collaboration write, or release publication | Requires explicit ownership, security, persistence, and authorization design. |

## Issue acceptance rule

Every implementation candidate must specify its human decision boundary,
StateMachine evidence, repository/adapter boundary, compatibility proof,
deterministic test fixture, documentation, and removal or rollback plan.
