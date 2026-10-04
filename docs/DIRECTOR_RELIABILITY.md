# Director Reliability

`DirectorReliabilityService` evaluates an advisory Director plan without
executing it. It returns integrity, consistency, public decision-trace, and
execution-readiness DTOs for exactly one supplied page context.

The service cannot call an Agent or Provider, persist a Project, dispatch a
command, or transition a page. `WorkflowEngine` remains the only workflow
executor and `StateMachine` remains the source of transition legality.

Use `manga-director director reliability --project <id> --page <number>` for a
local preview. The same DTO is injectable into FastAPI and exposed by MCP as
`director_reliability`.
