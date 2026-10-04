# Decision Governance

v4.7 Iteration 3 adds immutable, Application-layer decision-governance DTOs.
They turn caller-supplied Decision Intelligence evidence into a review packet;
they do not create a policy record or make a decision.

## Scope

- `V47DecisionPolicyDTO` makes StateMachine authority, persisted-storyboard,
  completed-quality-review, and human-decision prerequisites explicit.
- `V47DecisionComplianceDTO` records only unconfirmed verification fields.
- `DecisionGovernanceReport` is a read-only composition with no presentation
  dependency.

## Safety boundary

Policy persistence/enforcement, evidence collection, compliance attestation,
decision selection, workflow execution, and external operations are excluded.
Every report is scoped to exactly one page. The domain StateMachine remains the
sole transition authority.
