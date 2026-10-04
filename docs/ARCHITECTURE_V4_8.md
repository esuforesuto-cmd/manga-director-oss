# v4.8 Architecture Report: Creative Operating System

## Decision

v4.8 is a design-only consolidation cycle over v4.7.0. It introduces no
runtime, data model, or public-surface change. The target is a conceptual
platform boundary that makes existing capability ownership understandable and
enables future additive composition.

```text
CLI / Python API / FastAPI / REST / MCP / Web UI
                         |
             Unified API Surface (future facade, design only)
                         |
                 Unified Creative Platform
   Workspace | Agents | Knowledge | Production | Enterprise | Decisions
                         |
      Operational Intelligence + Lifecycle Management (read-only)
                         |
StateMachine | WorkflowEngine | Project | Repository | existing adapters
```

The diagram is a responsibility map, not a new execution path. Existing
delivery adapters continue to use their current public services, and every
workflow transition must still be validated by the StateMachine.

## Responsibility map

| Module | Consolidated responsibility | Boundary retained |
| --- | --- | --- |
| Workspace | Project scope, participants, sessions, and activity views. | Does not authorize, schedule, or mutate work. |
| Agent Platform | Agent descriptors, plans, collaboration evidence, and human review context. | Does not autonomously dispatch, learn, or decide. |
| Knowledge | Provenance, graph, memory, references, quality, and lifecycle evidence. | Does not silently load, merge, synchronize, or share knowledge. |
| Production | Pipeline, asset, deliverable, publishing, quality, and operations reports. | Does not execute, publish, or change a pipeline. |
| Enterprise | Organization, portfolio, extension, marketplace, governance, and reliability evidence. | Does not grant access, enforce policy, bill, or operate a marketplace. |
| Decision Platform | Alternatives, recommendations, review, approval-readiness, and trace evidence. | Does not select, approve, enforce, or transition state. |
| Core domain | Project/Page state and legal workflow transitions. | Remains unchanged and authoritative. |

## Consolidation seams

| Existing repeated concern | Shared v4.8 design concept | Compatibility rule |
| --- | --- | --- |
| Dashboard and summary DTOs | `Platform Snapshot` envelope containing supplied domain summaries. | Keep each existing dashboard DTO and adapter. |
| Policy, compliance, audit, and reliability reports | Evidence/requirement/finding/status vocabulary. | Do not centralize enforcement or change domain policy semantics. |
| Workspace, context, session, and project scope | Stable scope reference: project, page, participant, and correlation identifiers. | Existing identifiers and DTO fields remain valid. |
| Snapshot, history, timeline, and trace | Lifecycle reference model with source and freshness metadata. | No shared persistence or migration is introduced. |
| Planning, orchestration, recommendation, and approval | Human-reviewed decision packet with explicit owner and prerequisites. | Never replaces the domain approval transition. |

## Dependency rules

1. Core domain imports no v4.8 platform abstraction.
2. Application and Knowledge modules may produce immutable, caller-supplied
   DTOs but cannot depend on delivery layers.
3. The future unified facade composes existing public services; it cannot
   reimplement workflow rules, repository behavior, or authorization.
4. Operational Intelligence is read-only and accepts evidence explicitly; it
   cannot collect telemetry, persist data, monitor, alert, retry, recover, or
   take an operational action.
5. Workflow evidence is exactly-one-Page scoped and retains storyboard and
   completed-quality-review gates.

## Incremental migration architecture

| Step | Change admission | Compatibility proof |
| --- | --- | --- |
| 0. Inventory | Record public names, DTO schemas, commands, routes, MCP tools, and workflow invariants. | v4.7 contract fixtures remain green. |
| 1. Vocabulary | Add documentation-only cross-domain terms and an ownership map. | No package or runtime diff. |
| 2. Additive facades | Introduce optional adapters over existing public services only when approved. | Legacy and facade results are equivalent for the same supplied evidence. |
| 3. Shared reports | Offer opt-in aggregate DTOs with explicit provenance and redaction. | Existing reports and transports remain unchanged. |
| 4. Deprecation review | Consider documentation notices after a support window. | No removal or behavior change in v4.8. |

The detailed platform boundaries are in [Unified Platform](UNIFIED_PLATFORM.md),
[Modular Runtime](MODULAR_RUNTIME.md), [Lifecycle
Management](LIFECYCLE_MANAGEMENT.md), and [Operational
Intelligence](OPERATIONAL_INTELLIGENCE.md).
