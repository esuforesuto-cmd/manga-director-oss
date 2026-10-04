# Approval Workflow Foundation

`V47DecisionFoundationService.approval_workflow()` returns an immutable Approval
Workflow Foundation report. It makes exactly-one-page scope, StateMachine
authority, persisted-storyboard, completed-quality-review, and human-approval
requirements explicit.

It does not submit or grant approval, authenticate a person, grant access,
enforce policy, create an override, transition state, skip a stage, generate an
image, or execute a workflow. The existing StateMachine remains the sole
authority for the domain approval transition.
