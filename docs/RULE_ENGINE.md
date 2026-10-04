# Rule Engine Design

## Purpose

The v5.2 Rule Engine is a deterministic evaluator of explicit, local rule
metadata. It produces eligibility, missing-evidence, and explanation DTOs for
human review. It does not infer rules from data or execute actions.

## Proposed rule contract

| Field | Meaning |
| --- | --- |
| `rule_id` | Stable namespaced ID and named owner. |
| `scope` | Single Page, template, profile, or composition scope. |
| `conditions` | Supplied predicates over declared evidence only. |
| `required_evidence` | Provenance, storyboard, review, or policy references. |
| `outcome` | Advisory eligibility or diagnostic finding. |
| `approval_required` | Human approval boundary for any future action. |

## Evaluation boundaries

Rules must be deterministic, side-effect free, and explainable. Unknown,
conflicting, stale, or incomplete conditions produce `not_eligible` or
`needs_review`; they never select a fallback rule, modify a workflow, or cause
an automatic action.
