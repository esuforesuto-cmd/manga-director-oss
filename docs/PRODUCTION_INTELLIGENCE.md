# Production Intelligence

v3.3 Iteration 2 exposes a read-only production view for one existing Page.
It combines the current StateMachine state, supplied history labels, and the
existing pipeline projection into immutable DTOs.

`ProductionIntelligenceReport` includes observed efficiency, a current-stage
bottleneck, a timeline, and recommendations. It never executes, transitions,
replays, optimizes, publishes, or schedules a workflow. A suggested command is
informational: callers must continue through the existing Workflow Engine and
StateMachine guards.

Use `director production-intelligence-v33`, `GET /v3.3/production-intelligence`,
or MCP `production_intelligence_v33` to render the same DTO boundary.
