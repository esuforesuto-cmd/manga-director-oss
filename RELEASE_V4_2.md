# manga-director v4.2.0

## What's New

v4.2.0 promotes the RC1-reviewed Autonomous Creative System foundations. It
adds typed, transport-neutral, one-Page DTO projections for execution planning,
checkpoint evidence, supervision, adaptive planning, pipeline planning,
governance, observability, and reliability—without adding autonomous execution.

## Autonomous Creative System Improvements

- Human-owned Goal, Execution Context, defined Execution Session, Execution
  State, Checkpoint, Snapshot, and denied-by-default Resume projections.
- Supervisor, progress, health, escalation, task queue, scheduled/background
  task, and lifecycle projections with dispatch and worker execution disabled.
- Goal Management, Adaptive Planning, Pipeline Automation, and Execution
  Recovery projections that cannot apply plans, start stages, retry, restore,
  or mutate a workflow.

## Governance and Operations

- Human Supervision, Approval Checkpoint, Intervention, and Override Request
  projections that cannot approve, intervene, override, or bypass StateMachine.
- Execution Policy, Risk, Safety Boundary, Compliance, Metrics, Trace, Event,
  Dashboard, Failure Classification, and Reliability projections with
  enforcement, telemetry, monitoring, retry, and recovery disabled.

## Developer Experience

The additive DTO services, examples, benchmarks, tests, quality gates, and
documentation provide a compatibility-safe foundation for a future supervised
system without changing existing CLI, FastAPI, MCP, Web UI, Provider, Backend,
Workflow, or Repository contracts.

## Compatibility and Migration

v4.2.0 is backward compatible with v4.1 and the documented v1.x, v2.x, v3.x,
and v4.0 public contracts. No data migration, configuration migration, or code
change is required. See the [Migration Guide](docs/MIGRATION_V4_2.md) and
[Compatibility Verification](docs/COMPATIBILITY_V4_2.md).

## Known Limitations

Autonomous execution, automatic approval or override, persistent checkpoints,
policy enforcement, telemetry export, monitoring, retry/recovery execution,
self-learning, self-improvement, Cloud services, and distributed runtime are
intentionally out of scope.

## v4.3 Candidate Roadmap

v4.3 planning may consider only separately approved, human-governed
implementation candidates after stable-release feedback, compatibility, safety,
and rollback review. No v4.3 feature scope is approved by this release.
