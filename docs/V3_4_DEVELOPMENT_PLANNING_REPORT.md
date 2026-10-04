# manga-director v3.4 Development Planning Report

## Decision

v3.4 planning is ready to begin on the `3.3.x` development branch. The v3.3.0
release remains the compatibility baseline. This phase changes no package
version, public API, Workflow, CLI, FastAPI, MCP, Web UI, Repository contract,
Core Architecture, or runtime behavior.

## Planning Outcome

- [Vision](VISION_v3_4.md), [Architecture](ARCHITECTURE_V3_4.md), and the
  [Architecture Index](V3_4_ARCHITECTURE.md) define bounded additive
  Application-layer responsibilities and inward dependency direction.
- The [Roadmap](ROADMAP_v3_4.md) supplies Must/Should/Could/Won't Issues with
  purpose, background, priority, impact, estimate, owner, and dependencies.
- The [GitHub plan](GITHUB_V3_4_PLAN.md) supplies an import-ready milestone,
  taxonomy, epics, and labels without changing remote GitHub state.
- Knowledge Platform, Production Operations, Organization Intelligence, and
  Release Intelligence plans document safety, privacy, ownership, and
  non-execution constraints.
- [Benchmark planning](V3_4_BENCHMARK_PLAN.md),
  [quality gates](V3_4_QUALITY_GATES.md), examples, and technical debt provide
  repeatable Issue-admission evidence.

## Compatibility and Migration

The migration strategy freezes v3.3 contracts first and admits only optional,
typed, transport-neutral DTO projections afterward. Existing public Python,
CLI, FastAPI, REST, MCP, Web UI, Workflow, Repository, Knowledge, Creative,
Asset, Analytics, Review, Diagnostics, Reporting, Governance, Health, Plugin,
Extension SDK, Provider, Image Backend, Automation, and Notification surfaces
remain unchanged. StateMachine authority and every one-Page workflow invariant
remain mandatory.

## Out of Scope

No autonomous AI, Cloud SaaS, marketplace, distributed runtime, Core redesign,
breaking change, automatic personnel action, deployment, tagging, signing, or
publication is planned. Any future implementation needs an approved Issue with
compatibility, security, benchmark, test, documentation, and rollback evidence.
