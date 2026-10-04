# Collaboration Workflow Foundation

The collaboration workflow DTOs show the handoff that a human may choose to
perform between two registered agents. An `AssignmentWorkflow` remains
unaccepted, a `ReviewWorkflow` remains pending, and an `ApprovalWorkflow`
always reports that quality review and approval are incomplete.

This model does not replace the existing workflow. In particular, it cannot
complete quality review or approve a Page; the StateMachine continues to own
those guarded transitions.

## Safety boundary

- No assignment, handoff, review, or approval is persisted or performed.
- The workflow is diagnostic/planning-only and makes no StateMachine bypass.
- The supplied context represents exactly one page.
