# Workflow Profiles

Workflow Profiles describe the existing Page state machine without changing it.
The profile includes every known stage, highlights the current stage, and uses
`StateMachine.next_command()` only to present the sole legal next command.

Profiles are deliberately diagnostic:

- they never call a workflow engine;
- they never transition a context;
- they retain the one-page execution invariant; and
- they do not enable automatic execution.

Use `manga-director director workflow-profiles --project <id> --page <number>`
to render the current DTO.

