# Creative Studio Foundation

v3.2 introduces a read-only Creative Studio projection in the Application
Layer. `V32FoundationService.creative_studio()` returns an immutable workspace,
creative session, layout descriptor, project dashboard, activity summary, and
advisory next command for exactly one existing page.

The Studio does not persist layouts, start an Agent, execute a workflow command,
approve a page, or modify a `WorkflowContext`. The displayed next command is
derived from the existing `StateMachine`; callers must still invoke the normal
one-page workflow command when a human chooses to proceed.

Use `manga-director director creative-studio --project <id> --page <number>`
for the CLI DTO, or configure the optional `/v3.2/creative-studio` FastAPI and
`creative_studio_v32` MCP delivery providers.

