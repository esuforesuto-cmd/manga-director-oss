# Production Operations Foundation

v3.4 adds a read-only Production Operations projection in the Application
layer. It returns dashboard, status, capacity, timeline, summary, and report
DTOs from one existing Project and Page context.

The service does not poll, monitor, alert, schedule, allocate, configure,
restart, remediate, deploy, persist a timeline, or execute a workflow. The
StateMachine remains the sole transition authority.

Use `manga-director director production-operations-v34 --project <id> --page
<number>`, the optional `/v3.4/production-operations` FastAPI provider, or the
`production_operations_v34` MCP tool.
