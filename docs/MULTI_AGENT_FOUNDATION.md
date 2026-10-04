# Multi-Agent Foundation

`CollaborationPlanningService.multi_agent_foundation()` returns Agent Profile,
Capability, Assignment, Collaboration Plan, Coordination Report, and Summary
DTOs. A profile describes a proposed role only; it is not an Agent instance.

The plan declares review dependencies and human checkpoints for editorial,
story, character, storyboard, and review roles. `execution_dispatched` and all
assignment execution flags are always `false`. Agents never call one another,
and the existing `WorkflowEngine` remains the only workflow execution path.

Delivery: `manga-director director collaboration`, `GET /v3/agents`, and the
`multi_agent_foundation` MCP tool.
