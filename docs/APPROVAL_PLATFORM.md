# Approval Platform Design

## Purpose

The Approval Platform models a manual, accountable decision boundary. It makes
approval prerequisites, expected roles, escalation paths, override rationale,
and decision-history references visible without becoming an identity, access,
or workflow-execution system.

## Proposed DTO vocabulary

| DTO | Meaning | Boundary |
| --- | --- | --- |
| `ApprovalRequestDTO` | Requested decision, scope, evidence, prerequisites, and named human owner. | Cannot submit or accept an approval. |
| `ApprovalPolicyReferenceDTO` | Caller-supplied policy reference and review requirements. | Cannot load or enforce a policy. |
| `ApprovalEscalationDTO` | Human escalation role, reason, and evidence gap. | Cannot notify, route, or assign work. |
| `ApprovalOverrideDTO` | Human-provided override rationale and review requirement. | Cannot grant an override or change permissions. |
| `ApprovalReadinessReport` | Readiness, missing prerequisites, and human-review summary. | Cannot change page state or bypass gates. |

## Workflow guardrails

An approval representation never replaces the domain approval transition. The
StateMachine remains authoritative: only exactly one Page may be executed,
workflow stages cannot be skipped, image generation requires a persisted
storyboard, and page approval requires a completed quality review.
