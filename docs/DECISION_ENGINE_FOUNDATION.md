# Decision Engine Foundation

v4.7 adds immutable Application-layer DTOs for one-page-scoped Decision Context,
Evidence, and Summary records. `V47DecisionFoundationService.decision_engine()`
derives identifiers and workflow state from caller-supplied `WorkflowContext` and
returns a `DecisionEngineFoundationReport`.

The report makes provenance, redaction, risk, alternative, and human-owner
requirements visible. It does not collect/load/persist evidence, select a
decision, enforce policy, invoke an Agent, transition StateMachine state, or
execute a workflow.
