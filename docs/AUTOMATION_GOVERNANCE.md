# Automation Governance Design

## Governance model

Automation Governance defines the evidence and human-review requirements that
apply to templates, events, rules, plan previews, and any future execution
proposal. It is a reporting and validation design, not a policy-enforcement
system.

## Required controls

- Explicit rule/template owner and compatibility range.
- Local provenance and evidence classification.
- Single-Page scope validation.
- Persisted storyboard and completed quality-review requirements when relevant.
- Named approval boundary and decision-history reference.
- Audit-ready explanation of why a plan is eligible, ineligible, or deferred.

## Non-enforcement boundary

Governance cannot grant a permission, advance a stage, approve a Page, invoke
a rule handler, configure a runtime, send an event, or persist audit data.
Those responsibilities remain with existing owners and explicitly authorized
human actions.

## v5.2 Iteration 3 implementation

`AutomationGovernanceService` reports a declarative policy and compliance
evidence for an existing automation preview. It checks one-Page template scope,
evidence validity, the named approval boundary, rule safety flags, and
StateMachine authority. `policy_enforced`, `enforcement_action_taken`, and
automatic-action fields remain false; the report is not a permission system.
