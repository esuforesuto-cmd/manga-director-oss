# Error Handling

`manga-director` exposes typed domain errors at the package root. Delivery
adapters map these errors at their boundary; workflow legality remains owned by
`StateMachine` and `WorkflowEngine`.

| Error family | Boundary response |
| --- | --- |
| `ValidationError` / `ConfigurationError` | Reject invalid input or unsafe configuration without leaking secrets. |
| `WorkflowError` / `StateTransitionError` | Explain the illegal workflow operation without changing page state. |
| `RepositoryError` | Preserve the cause for logs and return a safe persistence failure to clients. |
| `ImageGeneratorError` | Return adapter failure details without provider-specific branching in the workflow. |
| `CLIError` | Render a concise error and non-zero exit status. |

Errors must retain chaining for diagnostics (`raise ... from exc`) but external
HTTP, CLI, and MCP renderers must not expose filesystem paths, credentials, or
unhandled exception traces.
