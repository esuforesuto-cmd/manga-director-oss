# Decision Engine Design

## Purpose

The Decision Engine is a planning surface for making a human-owned decision
reviewable. It assembles caller-supplied decision context, evidence references,
alternatives, assumptions, trade-offs, uncertainty, risks, and accountable
roles into immutable DTOs.

## Proposed DTO vocabulary

| DTO | Meaning | Boundary |
| --- | --- | --- |
| `DecisionContextDTO` | Project, one-page scope, goal, decision type, and supplied evidence references. | Cannot collect or persist context. |
| `DecisionAlternativeDTO` | Human/AI-supplied option, rationale, impact, and prerequisites. | Cannot select or apply an option. |
| `DecisionEvidenceDTO` | Attributable, redacted evidence reference with freshness and confidence notes. | Cannot read a repository or memory store. |
| `DecisionRiskDTO` | Explicit risk, uncertainty, mitigation prerequisite, and escalation need. | Cannot classify or mitigate automatically. |
| `DecisionTraceDTO` | Human-readable rationale, reviewer, approver, and history reference. | Cannot persist a decision or invoke an agent. |
| `DecisionReport` | Transport-neutral aggregation for review. | Cannot transition or execute a workflow. |

## Required safeguards

Every workflow-related decision is exactly-one-page scoped, recognizes
StateMachine authority, requires a persisted storyboard before image generation,
and requires completed quality review before a page can be approved. The engine
returns a recommendation only; it never performs approval, delegation, stage
change, workflow mutation, or execution.
