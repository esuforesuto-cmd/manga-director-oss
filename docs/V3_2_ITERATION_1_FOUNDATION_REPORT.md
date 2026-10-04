# v3.2 Iteration 1 Foundation Report

## Outcome

The v3.2 foundations add immutable Application DTOs for Creative Studio, Asset
Intelligence, Workflow Profiles, and Production Analytics. They project
existing Project and single-Page workflow data only.

## Compatibility and boundaries

- Core, `WorkflowEngine`, the `ProjectRepository` protocol, and page transition
  rules were not changed.
- All DTO services are read-only. They do not save, execute, approve, generate,
  create external resources, or mutate a workflow context.
- Workflow Profile next-command guidance delegates to the existing
  `StateMachine`; no alternate transition logic was introduced.
- CLI commands, FastAPI routes, and MCP tools are additive and use optional
  dependency injection, preserving existing delivery constructors.

## Verification

The focused contract suite covers Studio, redacted Assets, StateMachine Profiles,
Production Analytics, FastAPI routes, and MCP DTO dispatch. Static linting and
the full repository suite are run as the final iteration verification.

## Architecture difference review

The implementation conforms to the v3.2 architecture plan: DTO composition is
in the Application/production layer; Asset reads use the existing Repository
port; and delivery adapters receive DTO providers only. No proposed Creative
Studio, Asset Platform, Workflow Engine, or Core responsibility moved across a
layer boundary.
