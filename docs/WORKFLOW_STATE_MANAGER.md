# Workflow State Manager

`V57ProductionWorkspaceService.workflow_state()` reads the current state and
the `StateMachine` next-command diagnostic. It checks storyboard evidence for
generation-or-later states and quality-review evidence before approval.

The manager never executes the command, advances a workflow, skips a stage, or
changes the supplied context.
