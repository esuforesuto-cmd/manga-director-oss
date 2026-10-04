# Workspace Manager Foundation

`V57ProductionPlatformFoundationService.workspace()` creates a
transport-neutral, one-Page workspace projection from an existing
`WorkflowContext`.

It records stable project/page references and available evidence names. It does
not create or persist a workspace, change workflow state, assign work, or copy
story and character content into a new prompt.

## Compatibility

The Workspace Manager is optional and additive. Existing CLI, FastAPI, MCP,
Web UI, SDK, Project, Repository, and workflow callers need not invoke it.
