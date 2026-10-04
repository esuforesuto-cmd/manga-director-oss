# Director Reliability v3

`V3ReadinessService.director_reliability()` validates a Director Session,
planning integrity, decision consistency, creative strategy, and readiness for
a *human decision*. It uses existing Director/Creative DTOs and never calls
`WorkflowEngine` or an Agent.

The report derives its recommendation from existing StateMachine evidence. Its
`execution_enabled` and `automatic_action_taken` fields are always false.

Delivery: `manga-director director reliability-v3`, `GET /v3/reliability`, and
the `director_reliability_v3` MCP tool.
