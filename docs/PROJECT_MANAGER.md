# Project Manager

`ProjectManagerService.inspect()` provides a compact, read-only project-status
report through the existing `ProjectRepository` port. It selects at most one
active Page for inspection and reports chapter, approval, storyboard, and
quality-review evidence.

`V57ProductionPlatformFoundationService.project()` remains available for the
existing `WorkflowContext` projection. The new service does not replace it or
`ProjectWorkflowEngine`.

## Boundaries

- No Project, Page, workflow, or repository state is changed.
- No workflow is executed, scheduled, or approved.
- The domain `StateMachine` remains the only owner of legal transitions.
- A storyboard remains required before image generation; a completed quality
  review remains required before approval.

## Compatibility

The service adds no repository port, project schema, endpoint, workflow
command, CLI, FastAPI, MCP, or Web UI contract. Existing project lifecycle
ownership remains in `ProjectWorkflowEngine`.
