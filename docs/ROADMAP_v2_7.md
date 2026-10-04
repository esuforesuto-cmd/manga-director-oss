# v2.7 Roadmap

v2.7 is an Issue-driven planning cycle on the v2.6.x development branch. The
v2 Core architecture, public contracts, StateMachine, and one-page workflow
invariants are fixed. Every accepted Issue requires compatibility, security,
tests, documentation, benchmark evidence where relevant, and a rollback plan.

## Must

| ID | Objective | Background | Priority | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V27-DIR-01 | Define an advisory Director Planning DTO and policy boundary. | Operators need explainable plan choices without changing Director or Engine authority. | P0 | Application, Workflow, Tests, Docs | M | Application | None |
| V27-KNOW-01 | Define Knowledge Repository, index, snapshot, and health contracts. | Knowledge-aware recommendations need a bounded, portable evidence model. | P0 | Application, Repository, Security | M | Application / Repository | V27-DIR-01 |
| V27-ORCH-01 | Define task dependency graph, execution strategy, and preview requirements. | Orchestration must expose one legal next-page action without dispatching work. | P0 | Application, Workflow, Diagnostics | M | Application / Workflow | V27-DIR-01 |
| V27-AUTO-01 | Define non-executing Automation Planner, policy, preview, and simulation DTOs. | Enterprise operators need reviewed automation options without automation authority. | P0 | Application, Automation, Security | M | Application / Automation | V27-ORCH-01 |
| V27-QA-01 | Establish v2.7 planning, knowledge, orchestration, and automation quality gates. | Advisory features need reproducible, mock-only safety evidence. | P0 | CI, Docs, Tests | S | Quality / DX | None |

## Should

| ID | Objective | Background | Priority | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V27-DIR-02 | Plan decision traces, recommendations, and strategy explanations. | Recommendations must remain auditable and bounded. | P1 | Diagnostics, Observability | M | Application / Observability | V27-DIR-01 |
| V27-KNOW-02 | Plan knowledge search, summaries, diagnostics, and recommendations. | Search must be deterministic, redacted, and non-mutating. | P1 | Repository, Security, Docs | M | Application / Repository | V27-KNOW-01 |
| V27-ORCH-02 | Plan orchestration diagnostics and complexity analysis. | Large plans need explainable dependencies before execution is considered. | P1 | Observability, Performance | M | Application / Observability | V27-ORCH-01 |
| V27-ENT-01 | Plan Enterprise automation diagnostics and policy evidence. | Enterprise automation requires explicit ownership, retention, and approval checkpoints. | P1 | Enterprise, Security, Operations | M | Enterprise / Operations | V27-AUTO-01 |
| V27-DX-01 | Improve planning fixtures, preview examples, and contributor checklists. | Contributors need safe, reviewable proposal paths. | P1 | Tooling, CI, Docs | S | DX / Quality | V27-QA-01 |

## Could

| ID | Objective | Background | Priority | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V27-KNOW-03 | Explore local semantic index design notes. | Future retrieval requires privacy and retention review. | P2 | Repository, Security | L | Research / Application | V27-KNOW-02 |
| V27-DIR-03 | Draft deterministic execution-strategy comparison fixtures. | Policy proposals need mock evidence before implementation. | P2 | Application, Tests | M | Application / Quality | V27-DIR-02 |
| V27-AUTO-02 | Draft automation simulation benchmark scenarios. | Simulation must stay non-executing and policy-bound. | P2 | Automation, Performance | M | Automation / Quality | V27-AUTO-01 |

## Won't (v2.7)

| Item | Reason |
| --- | --- |
| Breaking Core redesign or StateMachine change | Violates established v2 contracts and workflow safety rules. |
| Autonomous AI execution, task dispatch, auto-approval, or multi-page generation | Violates human approval and exactly-one-page invariants. |
| Cloud SaaS, Marketplace, distributed runtime, or microservices | Requires a separate trust, deployment, and recovery architecture. |
| Live credentials or network calls in CI | Mock-only deterministic evidence remains mandatory. |
