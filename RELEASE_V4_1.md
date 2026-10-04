# manga-director v4.1.0

## What's New

v4.1.0 promotes the RC1-reviewed Multi-Agent Platform foundations without
adding autonomous execution. The release provides typed, transport-neutral
evidence for registered agents, runtime preparation, task planning,
orchestration, collaboration, human review, governance, observability, and
reliability.

## Multi-Agent Platform Improvements

- Immutable Agent Registry, Profile, Capability, Role, Session, Context, State,
  Request, Result, Communication, and Collaboration DTOs.
- One-page Task Planning, Orchestration, Queue, Dependency, Handoff, and
  Conflict Resolution DTOs with dispatch and execution disabled.
- Human-in-the-Loop approval/review/feedback/history DTOs that cannot complete
  quality review, grant approval, or bypass the StateMachine.

## Enterprise and Reliability Improvements

- Advisory Agent Policy, Permission, Capability Restriction, Governance, and
  Compliance DTOs with enforcement disabled.
- Local Agent Metrics, Trace, Event Timeline, Collaboration Metrics, and
  Runtime Dashboard DTOs with no telemetry export or retention.
- Manual-only Retry, Timeout, Recovery, Failure, and Reliability DTOs with no
  retry, cancellation, recovery, remediation, or memory optimization execution.

## Developer Experience

The additive DTO services, examples, benchmarks, tests, quality gates, and
documentation provide an implementation-ready, compatibility-safe foundation
without changing existing CLI, FastAPI, MCP, Web UI, Provider, Backend,
Workflow, or Repository contracts.

## Compatibility and Migration

v4.1.0 is backward compatible with v4.0 and the documented v1.x, v2.x, and
v3.x public contracts. No data migration, configuration migration, or code
change is required. See the [Migration Guide](docs/MIGRATION_V4_1.md) and
[Compatibility Verification](docs/COMPATIBILITY_V4_1.md).

## Known Limitations

Agent execution, automatic task dispatch, policy enforcement, durable decision
or audit history, message transport, telemetry export, retry/recovery execution,
autonomous AI, self-learning, long-term memory optimisation, Cloud services,
and distributed runtime are intentionally out of scope.

## v4.2 Candidate Roadmap

v4.2 planning may consider controlled persistence and operational integrations
only after a separate architecture, compatibility, security, and human-governance
review. No v4.2 feature scope is approved by this release.
