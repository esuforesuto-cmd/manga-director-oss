# v4.7 Roadmap: Creative Decision Platform

## Must

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V47-DEC-01 | Decision Engine model | Establish human-owned decision context, alternatives, evidence, risk, uncertainty, and traceability vocabulary. | P0 | Agent / Review / Governance | M | Application | v4.6 Context, Reasoning, Governance, and existing StateMachine contracts |
| V47-REV-01 | Review Intelligence model | Define review aggregation, coverage, consistency, missing-evidence, and escalation DTOs. | P0 | Review / Analytics | M | Application | V47-DEC-01, existing quality review evidence |
| V47-REC-01 | Recommendation Framework | Define explainable advisory options, impact, prerequisites, and human-review requirements. | P0 | Agent / Analytics | M | Application | V47-DEC-01, V47-REV-01 |
| V47-APP-01 | Approval Platform model | Define manual approval readiness, role expectations, escalation, override rationale, and history-reference DTOs. | P0 | Governance / Enterprise | M | Application | V47-DEC-01, existing StateMachine and quality-review boundaries |
| V47-EXE-01 | Executive Dashboard model | Compose redacted Decision, Review, Recommendation, Approval, Analytics, and Enterprise summaries. | P0 | Enterprise Platform | M | Application | V47-REV-01, V47-REC-01, V47-APP-01 |

## Should

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V47-DEC-02 | Decision trace and rationale report | Make assumptions, evidence freshness, uncertainty, and accountable roles reviewable. | P1 | Agent / Governance | S | Application | V47-DEC-01 |
| V47-REV-02 | Review coverage and consistency report | Surface supplied coverage gaps and recurring review findings without changing a review. | P1 | Review / Analytics | M | Application | V47-REV-01 |
| V47-REC-02 | Recommendation comparison report | Compare supplied options and trade-offs without rank selection or automation. | P1 | Agent / Analytics | S | Application | V47-REC-01 |
| V47-APP-02 | Approval readiness and escalation report | Expose prerequisites and human escalation needs without notification or access control. | P1 | Governance / Enterprise | M | Application | V47-APP-01 |
| V47-EXE-02 | Executive decision-health summary | Build a transport-neutral, redacted organizational decision view. | P1 | Enterprise Platform | M | Application | V47-EXE-01 |

## Could

| ID | Issue | Purpose / background | Priority | Scope | Estimate | Layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V47-DEC-03 | Decision relationship visualization DTO | Describe caller-supplied links among decisions, evidence, review, and approval. | P2 | Analytics / Enterprise | S | Application | V47-DEC-01 |
| V47-REV-03 | Review trend recommendation | Explain recurring supplied review patterns without remediation or content changes. | P2 | Review / Analytics | S | Application | V47-REV-02 |
| V47-EXE-03 | Portfolio decision KPI mapping | Document how existing metrics could support human decision review. | P2 | Enterprise Platform | M | Application | V47-EXE-01 |

## Won't

| Item | Reason |
| --- | --- |
| Autonomous decision, approval, policy enforcement, or agent dispatch | Requires separately approved safety, identity, authorization, supervision, and runtime architecture. |
| Automatic workflow mutation, stage skipping, image generation, or approval | Violates StateMachine authority and required human workflow safeguards. |
| Shared decision persistence, organization routing, notification, or cross-tenant transfer | Requires dedicated durability, access-control, privacy, consent, and security design. |
| Cloud decision service, marketplace, billing, payment, or distributed runtime | Outside local-first v4.7 planning scope. |
| Core, Repository, Workflow Engine, Agent, Review, Governance, Analytics, or Enterprise Platform redesign | Would break required v4.6 compatibility. |
