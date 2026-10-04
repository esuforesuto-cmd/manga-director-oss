# v3 Development Roadmap

v3 is an Issue-driven, staged design program on the v2.7.x development
baseline. It is not a Core rewrite and does not authorize autonomous execution.
Each implementation Issue must preserve public contracts, include a rollback
plan, and pass the v3 quality gates.

## Must

| ID | Objective | Priority | Rationale | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V3-ARC-01 | Ratify additive layer and compatibility contracts. | P0 | Prevent a v3 feature from acquiring Core authority. | M | Architecture / Application | None |
| V3-DIR-01 | Define Director planning, goal, task-graph, and decision-trace DTO contracts. | P0 | Plans need a bounded, explainable foundation. | M | Director / Planning | V3-ARC-01 |
| V3-KG-01 | Define repository-derived knowledge index, snapshot, provenance, and health contracts. | P0 | Knowledge must be portable and governed before recommendations use it. | M | Knowledge / Repository | V3-ARC-01 |
| V3-CP-01 | Define the creative planning pipeline and mandatory existing workflow checkpoints. | P0 | Creative plans must never bypass Page safety. | M | Creative / Review | V3-DIR-01, V3-KG-01 |
| V3-QA-01 | Add architecture, compatibility, Director, Knowledge, and Creative Pipeline validation evidence. | P0 | Planning requires enforceable safety proof. | S | Quality / DX | V3-ARC-01 |

## Should

| ID | Objective | Priority | Rationale | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V3-DIR-02 | Design creative planning, execution strategy, review strategy, and iteration planning. | P1 | Teams need comparable alternatives before acting. | M | Director / Planning | V3-DIR-01 |
| V3-MA-01 | Define agent capability catalog and coordinator planning graph. | P1 | Collaboration needs explicit ownership and review boundaries. | M | Agent / Planning | V3-DIR-01 |
| V3-KG-02 | Design relationship graph, character/world/lore memory, and knowledge search. | P1 | Continuity work needs evidence relationships, not opaque context. | L | Knowledge / Memory | V3-KG-01 |
| V3-CP-02 | Design panel-level plans, consistency review, and asset-library hand-offs. | P1 | Creative intent needs traceable transitions between stages. | M | Creative / Review | V3-CP-01, V3-KG-02 |
| V3-DX-01 | Provide planning previews and example contracts for all presentation adapters. | P1 | Contributors need safe demonstrations without execution. | S | Presentation / DX | V3-QA-01 |

## Could

| ID | Objective | Priority | Rationale | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V3-KG-03 | Research deterministic local similarity and knowledge-health metrics. | P2 | Useful only after governance and workload evidence exist. | L | Knowledge / Research | V3-KG-02 |
| V3-MA-02 | Draft multi-agent simulation and conflict-resolution fixtures. | P2 | Validates contracts before any execution discussion. | M | Agent / Quality | V3-MA-01 |
| V3-CP-03 | Draft visual creative-pipeline dashboards as transport-neutral DTO examples. | P2 | Presentation should follow stable planning contracts. | M | Presentation / Creative | V3-CP-02 |

## Won't (v3 planning scope)

| Item | Reason |
| --- | --- |
| Autonomous AI execution, auto-approval, task dispatch, or multi-page generation | Contradicts human authority and the one-page workflow contract. |
| Automatic LLM billing or live-provider dependency | Planning remains deterministic, provider-neutral, and safe to test locally. |
| Cloud SaaS, marketplace, distributed runtime, or microservices | Requires a separate security, tenancy, deployment, and recovery design. |
| Core redesign or breaking compatibility change | v2.7 remains the baseline; migration is additive and opt-in. |

## Issue acceptance rule

An accepted v3 Issue includes: a stated human decision boundary, StateMachine
evidence for any Page recommendation, no hidden execution side effect, public
API compatibility proof, deterministic tests, documentation, and a removal or
rollback plan.
