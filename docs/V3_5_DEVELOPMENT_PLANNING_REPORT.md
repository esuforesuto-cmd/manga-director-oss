# manga-director v3.5 Development Planning Report

## Decision

v3.5 planning is ready to begin on the `3.4.x` development branch. The v3.4.0
release is the compatibility baseline. This phase changes no package version,
public API, Workflow, CLI, FastAPI, MCP, Web UI, Repository contract, Core
Architecture, or runtime behavior.

## Planning Outcome

- [Vision](VISION_v3_5.md), [Architecture](ARCHITECTURE_V3_5.md), and the
  [Architecture Index](V3_5_ARCHITECTURE.md) define bounded, additive
  Unified Knowledge Graph, Creative Intelligence, Production Intelligence, and
  Platform Analytics responsibilities.
- The [Roadmap](ROADMAP_v3_5.md) provides Must/Should/Could/Won't Issues with
  objective, background, priority, impact, estimate, owner, and dependencies.
- The [GitHub plan](GITHUB_V3_5_PLAN.md) is import-ready and leaves remote
  GitHub state unchanged.
- [Benchmark planning](V3_5_BENCHMARK_PLAN.md),
  [quality gates](V3_5_QUALITY_GATES.md), examples, and technical debt provide
  repeatable Issue-admission evidence.

## Compatibility and Migration

The [migration strategy](MIGRATION_STRATEGY_V3_5.md) freezes v3.4 contracts
first and permits only optional, typed, transport-neutral projections afterward.
Existing public Python, CLI, FastAPI, REST, MCP, Web UI, Workflow, Repository,
Knowledge, Creative, Asset, Analytics, Review, Diagnostics, Reporting,
Governance, Operations, Health, Plugin, Extension SDK, Provider, Image Backend,
Automation, and Notification surfaces remain unchanged. StateMachine authority
and every one-Page workflow invariant remain mandatory.

## Out of Scope

No autonomous AI execution, Cloud SaaS, marketplace, distributed runtime, Core
redesign, breaking change, automatic approval, remote analytics collection,
scheduling, deployment, tagging, signing, or publication is planned. Every
future implementation requires an approved Issue with compatibility, security,
benchmark, test, documentation, and rollback evidence.
