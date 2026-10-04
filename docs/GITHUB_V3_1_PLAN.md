# GitHub Planning: v3.1

Create a local planning milestone named **v3.1.0 — Production Collaboration and
Evidence**. This document is import-ready planning material only; it does not
create or modify remote Issues, labels, milestones, projects, or releases.

## Issue taxonomy

| Type | Purpose | Required evidence |
| --- | --- | --- |
| Epic | Cross-cutting v3.1 planning outcome. | Child Issues, compatibility boundary, owner, rollback plan. |
| Director | Long-term objective, template, strategy, history, or metric design. | One-Page/StateMachine evidence and no-execution proof. |
| Collaboration | Workspace, hand-off, review, or approval-plan design. | Human ownership and no-approval-authority proof. |
| Knowledge | Version, diff, merge-plan, snapshot, timeline, or analytics design. | Provenance, redaction, retention, and Repository-port proof. |
| Operations | Observability, dashboard, analytics, or metric design. | Bounded window, redaction, and no-operation proof. |
| Quality | Architecture, compatibility, benchmark, security, or documentation evidence. | Deterministic fixture and acceptance gate. |
| Documentation | Contributor-facing design material. | Audience, links, and review owner. |
| Developer Experience | Example, template, contract, or tooling design. | Public-API and mock-only proof. |

## Initial epics

1. **V31-E01 — Director Planning Library:** long-term objectives, templates,
   decision history, strategy library, and creative metrics.
2. **V31-E02 — Creative Collaboration:** Editor, Scenario, Character,
   Storyboard, Review, and Approval workspace contracts.
3. **V31-E03 — Knowledge Evolution:** version, diff, merge-plan, snapshot,
   timeline, analytics, and governance contracts.
4. **V31-E04 — Production Operations:** observability, operational dashboard,
   quality/release/project/workflow analytics.
5. **V31-E05 — Compatibility and DX:** quality gates, benchmark plan, examples,
   migration evidence, and contributor guides.

Recommended labels: `v3.1`, `director`, `planning`, `creative`,
`collaboration`, `review`, `knowledge`, `operations`, `observability`,
`quality`, `compatibility`, `documentation`, `benchmark`, and `dx`.

Every Issue must link [ROADMAP_v3_1.md](ROADMAP_v3_1.md), declare whether it is
design-only or implementation-ready, and retain all v3.0 workflow invariants.
