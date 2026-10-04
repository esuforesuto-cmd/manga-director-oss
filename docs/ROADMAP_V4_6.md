# v4.6 Roadmap: Creative Intelligence OS

## Must

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V46-CTX-01 | Unified Creative Context model | Establish local context envelope, provenance, scope, freshness, redaction, and references across creative evidence. | P0 | Agent / Knowledge / Workflow | M | Application | v4.5 Project, Knowledge, Workflow, and Ecosystem contracts |
| V46-MEM-01 | Cross-Agent Memory reference model | Define attributable consent-aware memory references, conflict findings, and review boundaries without shared mutable memory. | P0 | Agent Platform / Knowledge | M | Application / Knowledge | V46-CTX-01, existing Agent context contracts |
| V46-RSN-01 | Creative Reasoning explanation model | Define goal, evidence trace, alternatives, risk, confidence, and recommendation records for human planning review. | P0 | Creative Intelligence | M | Application | V46-CTX-01, V46-MEM-01 |
| V46-AWF-01 | Adaptive Workflow proposal model | Define safe human-reviewable adaptation, dependency, impact, and rollback evidence without changing a workflow. | P0 | Workflow / Enterprise | M | Application | V46-CTX-01, existing StateMachine and WorkflowEngine |
| V46-HUB-01 | Intelligence Hub review-packet model | Compose supplied context, memory, reasoning, workflow, governance, and operational evidence. | P0 | Enterprise Platform | M | Application | V46-RSN-01, V46-AWF-01 |

## Should

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V46-CTX-02 | Context provenance and redaction report | Explain source, ownership, freshness, sensitivity, and missing-context findings. | P1 | Knowledge / Enterprise | S | Application | V46-CTX-01 |
| V46-MEM-02 | Memory coverage and conflict report | Make recall readiness, consent gaps, contradictory references, and uncertainty visible. | P1 | Agent Platform / Knowledge | M | Application / Knowledge | V46-MEM-01 |
| V46-RSN-02 | Reasoning alternative comparison report | Compare human-supplied options and assumptions without selecting or executing them. | P1 | Creative Intelligence | M | Application | V46-RSN-01 |
| V46-AWF-02 | Workflow adaptation safety report | Explain StateMachine, one-page, storyboard, quality-review, approval, and rollback prerequisites. | P1 | Workflow | M | Application | V46-AWF-01 |
| V46-HUB-02 | Intelligence Hub diagnostic summary | Provide transport-neutral, redacted human review packet output. | P1 | Enterprise Platform | M | Application | V46-HUB-01 |

## Could

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V46-CTX-03 | Context relationship visualization DTO | Present caller-supplied context links without persistence or presentation ownership. | P2 | Knowledge / Creative Intelligence | S | Application | V46-CTX-01 |
| V46-MEM-03 | Memory recommendation report | Explain missing consent, stale sources, or unresolved conflicts without retrieval or remediation. | P2 | Agent Platform / Knowledge | S | Application | V46-MEM-02 |
| V46-RSN-03 | Creative reasoning quality rubric | Define review criteria for explainability, provenance, uncertainty, and human override. | P2 | Creative Intelligence | S | Application | V46-RSN-01 |
| V46-HUB-03 | Cross-domain KPI mapping | Document how existing quality, workflow, and enterprise metrics could be aligned for review. | P2 | Enterprise Platform | M | Application | V46-HUB-01 |

## Won't

| Item | Reason |
| --- | --- |
| Autonomous creative decisions, agent dispatch, self-learning, or long-running execution | Requires separately approved safety, runtime, supervision, and operational architecture. |
| Automatic workflow mutation, stage skipping, image generation, or approval | Violates StateMachine authority and the required human workflow safeguards. |
| Shared mutable or remote memory, synchronization, ownership transfer, and cross-tenant sharing | Requires dedicated privacy, consent, durability, access-control, and security design. |
| Cloud Intelligence Hub, telemetry service, federation networking, payment, or billing | Outside local-first v4.6 planning scope. |
| Core, Repository, Workflow Engine, Agent Platform, Plugin, or Extension SDK redesign | Would break required v4.5 compatibility. |
