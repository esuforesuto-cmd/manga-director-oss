# Director Platform Foundation

The v3 Director Platform is an Application-layer, planning-only facade. Its
`DirectorPlanningService` composes the existing `DirectorFoundationService` and
`PlanningService`; it never calls `WorkflowEngine`, an Agent, a Provider, or a
repository write method.

## DTOs

- `ProjectGoal` and `CreativeGoal`: bounded human/context planning intent.
- `PlanningContext` and `ExecutionContext`: one-page state and a disabled,
  StateMachine-derived next-command view.
- `DirectorSession` and `DirectorSessionReport`: explainable session and
  decision evidence.
- `PlanningSummary` and `DirectorPlatformDTO`: compact presentation DTOs.

The recommended command is advisory. A user must explicitly invoke the
existing CLI, API, MCP, or Web UI workflow action. This preserves exactly one
Page per execution and all existing transition guards.

## Delivery

- CLI: `manga-director director platform` and `director summary`.
- FastAPI: `GET /v3/director` and `GET /v3/summary` when the optional API
  adapter is composed with providers.
- MCP: `director_platform` and `planning_foundation_summary` tools.

See [Director Platform example](../examples/director_platform/run.py) and
[v3 Architecture](ARCHITECTURE_V3.md).
