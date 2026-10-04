# Agent Registry Foundation

v4.1 introduces a local, immutable registry projection for describing
potential creative-agent profiles. `AgentRegistryRepository` is not a
replacement for `ProjectRepository`, does not persist registrations, and has
no connection to the existing workflow-agent map.

Each `AgentDTO` contains a profile, role, and declared capabilities. Capability
declarations are informational: they cannot invoke a model, dispatch work,
advance a workflow, generate content, or approve a Page.

Use `V41AgentFoundationService.registry()` to obtain a transport-neutral
snapshot for CLI, FastAPI, MCP, or Web UI presentation.

## Safety boundary

- Registry entries are supplied by the caller and immutable after construction.
- Duplicate agent identifiers are rejected.
- No Project repository interface or persistence schema is changed.
- Existing workflow agents and the StateMachine remain canonical.
