# v3.2 Development Roadmap

v3.2.0 is the stable baseline for the v3.2 cycle. It preserves v3.1 public
contracts and treats every future item below as design-only until a separately
reviewed implementation Issue is accepted.

## Must

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V32-ARC-01 | Ratify additive platform boundaries and migration fixtures. | P0 | Studio and asset work must not acquire Core authority. | All public surfaces | M | Architecture / Application | v3.1 baseline |
| V32-STU-01 | Define workspace layout, session, and dashboard contracts. | P0 | Creative collaboration needs a consistent human view. | Creative / Presentation | M | Creative Studio | V32-ARC-01 |
| V32-AST-01 | Define catalog, metadata, relationship, search, and version policies. | P0 | Asset evidence needs ownership before implementation. | Knowledge / Repository | L | Asset Platform | V32-ARC-01 |
| V32-WFL-01 | Define workflow-template, profile, validation, and metric contracts. | P0 | Workflow evolution must preserve StateMachine authority. | Workflow / DX | M | Workflow Intelligence | V32-ARC-01 |
| V32-ANL-01 | Define bounded project, quality, review, Knowledge, release, and productivity analytics. | P0 | Production insights require a no-automation model. | Operations / Observability | M | Analytics Platform | V32-ARC-01 |
| V32-QA-01 | Define compatibility, architecture, benchmark, and safety gates. | P0 | Planning must have enforceable admission criteria. | Quality / DX | S | Developer Platform | V32-ARC-01 |

## Should

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V32-STU-02 | Design Story, Page, and Review workspace evidence contracts. | P1 | Human hand-offs need consistent terminology. | Creative / Review | M | Creative Studio | V32-STU-01 |
| V32-AST-02 | Define asset provenance, retention, deletion, and cross-project rules. | P1 | Catalog design is unsafe without lifecycle policy. | Knowledge / Security | M | Asset Platform | V32-AST-01 |
| V32-WFL-02 | Design pipeline-profile comparison and stage-validation fixtures. | P1 | Profiles need deterministic compatibility evidence. | Workflow / Test | M | Workflow Intelligence | V32-WFL-01 |
| V32-ANL-02 | Design analytics observation windows and interpretation guidance. | P1 | Reports need safe, comparable meanings. | Operations / Documentation | S | Analytics Platform | V32-ANL-01 |

## Could

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V32-STU-03 | Draft local layout and accessibility fixtures. | P2 | Visual composition needs evidence before implementation. | Presentation / DX | S | Creative Studio | V32-STU-01 |
| V32-AST-03 | Research deterministic local asset-search fixtures. | P2 | Search needs a workload baseline. | Asset / Test | M | Asset Platform | V32-AST-02 |
| V32-WFL-03 | Draft pipeline analytics benchmark fixtures. | P2 | Metrics need repeatability evidence. | Workflow / Performance | S | Workflow Intelligence | V32-WFL-02 |
| V32-ANL-03 | Draft executive analytics dashboard examples. | P2 | Helpful only after metrics are reviewed. | Operations / Presentation | S | Analytics Platform | V32-ANL-02 |

## Won't

| Item | Reason |
| --- | --- |
| Autonomous AI, automatic Agent execution, auto-review, auto-approval, or multi-page generation | Contradicts human authority and StateMachine invariants. |
| Cloud SaaS, marketplace, distributed runtime, or microservices | Requires separately approved tenancy, security, deployment, and recovery architecture. |
| Core redesign, Repository-port change, or breaking public API | v3.1 is the stable compatibility baseline. |
| Implicit asset writes, remote asset fetches, or automatic profile application | Requires explicit persistence, authorization, and safety design. |

## Issue Acceptance Rule

Every Issue must declare its human decision boundary, StateMachine evidence,
Repository/adapter boundary, compatibility proof, deterministic fixture,
documentation, benchmark expectation where relevant, and rollback/removal plan.
