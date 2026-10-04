# Performance

Iteration 2 keeps the one-page workflow contract intact and optimizes for
predictable, safe orchestration rather than throughput at the expense of state
validation. The lightweight benchmark smoke suite is in `benchmarks/smoke.py`.

## Measured boundaries

- Page workflow step through the mock-backed `Director`
- In-memory and SQLite repository save/load
- Mock LLM and image adapter calls
- Mock notification dispatch
- Deterministic sequential batch planning

Run `python -m benchmarks.smoke` after installing the development environment.
Record medians across several runs before proposing an optimization. Networked
providers, file-system cache behavior, and Automation have no benchmark target
in this baseline.

## Guardrails

Performance changes must preserve state-machine validation, one-page execution,
explicit approval, immutable context snapshots, and repository-port usage.
Avoid caching mutable `WorkflowContext` or `Project` aggregates across calls.
