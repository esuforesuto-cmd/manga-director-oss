# v3 Benchmark Plan

These are future, provider-free planning scenarios. This document adds no
benchmark implementation and establishes no machine-dependent performance
budget. Each future measurement must use deterministic fixtures and report
input size, elapsed-time distribution, allocation observation where practical,
and compatibility result.

| Scenario | What it measures | Fixture boundary | Must never do |
| --- | --- | --- | --- |
| `planning_pipeline` | Construction and rendering of a Director/Creative advisory plan. | One Page, local policy, StateMachine evidence. | Execute an Agent or transition state. |
| `knowledge_lookup` | Index/snapshot lookup, bounded graph traversal, and redacted search. | Repository-port projection only. | Require a new database or external search service. |
| `creative_pipeline` | Story-to-review checkpoint plan composition. | One Page with persisted artifact fixtures. | Generate images or bypass storyboard/quality guards. |
| `director_planning` | Goal, task-graph, strategy, and decision-trace composition. | Mock metadata and one legal next step. | Invoke a Provider or scheduler. |
| `multi_agent_simulation` | Capability graph and conflict-policy evaluation. | Declared roles and deterministic mock outputs. | Call agents directly or dispatch a task. |

## Measurement policy

- Benchmarks are diagnostic evidence, not an optimization mandate.
- A regression comparison must use the same fixture shape and declare the
  platform/environment; CI uses smoke checks, not absolute timing gates.
- Metrics and reports must redact secrets and avoid collecting creative content
  outside the supplied fixture.
- No benchmark creates a multi-page execution path.
