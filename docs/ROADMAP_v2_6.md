# v2.6 Roadmap

v2.6 is an Issue-driven development cycle on the v2.5.x development branch.
The v2 Core architecture, public contracts, StateMachine, and one-page workflow
invariants are fixed. A roadmap entry is not implementation approval: every
accepted Issue needs compatibility, security, tests, documentation, benchmark
where applicable, and rollback evidence.

## Must

| ID | Objective | Background | Priority | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V26-AIW-01 | Define read-only workflow planning DTOs and validation. | Operators need explainable next-step planning without changing Engine authority. | P0 | Application, Workflow, Tests, Docs | M | Application / Workflow | None |
| V26-PROV-01 | Define provider-selection and capability-matching planning contracts. | Existing Provider protocols need a policy-neutral recommendation boundary. | P0 | Adapters, Application, Tests | M | Adapters / Application | V26-AIW-01 |
| V26-ENT-01 | Define Enterprise operations dashboard, compliance, and deployment-validation DTO requirements. | Production evidence needs consistent ownership and audit-ready planning. | P0 | Operations, Security, Docs | M | Application / Enterprise | V26-AIW-01 |
| V26-QA-01 | Establish v2.6 planning/compatibility quality evidence and Issue templates. | Intelligence features require stronger scope and rollback discipline. | P0 | CI, Docs, Tests | S | Quality / DX | None |

## Should

| ID | Objective | Background | Priority | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V26-AIW-02 | Plan Agent coordination, prompt-pipeline diagnostics, checkpoints, and workflow analytics. | Coordination must remain advisory and not let Agents invoke each other. | P1 | Agents, Prompting, Observability | M | Application / Observability | V26-AIW-01 |
| V26-PROV-02 | Plan fallback, cost, latency, cache, and execution-policy recommendations. | Provider choices need transparent estimates before any execution policy is considered. | P1 | Adapters, Configuration, Diagnostics | M | Adapters / Operations | V26-PROV-01 |
| V26-AUTO-01 | Define task scheduling, execution planning, and automation checkpoints as designs only. | Automation must never bypass human approval or one-page workflow rules. | P1 | Automation, Workflow, Security | M | Application / Automation | V26-AIW-01 |
| V26-ENT-02 | Plan operational audit, maintenance, and capacity-planning evidence. | Enterprise operators need action plans, not autonomous controls. | P1 | Repository, Observability, Security | M | Enterprise / Operations | V26-ENT-01 |
| V26-DX-01 | Improve planning fixtures, decision records, and contributor workflows. | Proposal evidence should be reproducible and easy to review. | P1 | Tooling, CI, Docs | S | DX / Quality | V26-QA-01 |

## Could

| ID | Objective | Background | Priority | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V26-ANL-01 | Explore anonymized, local workflow analytics summaries. | Aggregate evidence could help planning if privacy and retention are approved. | P2 | Observability, Repository | L | Observability / Security | V26-AIW-02 |
| V26-PROV-03 | Draft bounded provider simulation fixtures. | Candidate fallback policies need deterministic mock evidence. | P2 | Adapters, Tests | M | Adapters / Quality | V26-PROV-02 |
| V26-ENT-03 | Draft capacity and compliance checklist templates. | Enterprise operating standards vary and need scoped review. | P2 | Docs, Security, Operations | S | Enterprise / Documentation | V26-ENT-02 |

## Won't (v2.6)

| Item | Reason |
| --- | --- |
| Breaking Core redesign or StateMachine change | Violates established v2 contracts and workflow safety rules. |
| Autonomous AI execution, auto-approval, or multi-page generation | Violates explicit human approval and exactly-one-page invariants. |
| Cloud SaaS, Marketplace, distributed runtime, or microservices | Requires a separate trust, deployment, and recovery architecture. |
| Live credentials or network calls in CI | Mock-only deterministic evidence remains mandatory. |

## Sequencing

1. Create Must Issues with acceptance, security, compatibility, and rollback criteria.
2. Agree planning DTO and diagnostic-only boundaries before implementation.
3. Add deterministic mock fixtures and benchmarks before selecting policies.
4. Promote Should/Could items only while every mandatory quality gate remains green.
