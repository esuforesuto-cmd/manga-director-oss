# v3.5 Architecture Planning

## Status

This document plans additive v3.5 work on the `3.4.x` development branch. It
does not change Core Architecture, public APIs, Workflow execution, Repository
serialization, provider/back-end contracts, or presentation ownership.

## Planned Responsibilities

| Platform | Planned responsibility | Must not do |
| --- | --- | --- |
| Unified Knowledge Graph | Read-only relationship, context, traceability, quality, and insight projections. | Store, merge, repair, fetch remotely, or replace Repository. |
| Creative Intelligence Platform | Creative dashboard and metric/recommendation evidence. | Generate, alter storyboard, decide creatively, or approve. |
| Production Intelligence Platform | Efficiency, pipeline, capacity, risk, delivery, and operations analysis. | Schedule, allocate, remediate, deploy, or alter workflow. |
| Platform Analytics | Cross-platform, trend, history, regression, health, and executive aggregation. | Collect externally, persist telemetry, or assert automatic action. |
| Developer Platform | Deterministic fixtures, examples, benchmarks, migration, and compatibility tooling. | Widen root APIs or bypass quality gates. |
| Operations Platform | Human-reviewed health and report interpretation. | Alert, configure, restart, repair, or operate infrastructure. |

## Dependency Direction

```text
CLI / FastAPI / MCP / Web UI
        -> optional v3.5 Application / Knowledge DTO services
        -> existing v3.4 Application services and public Repository ports
        -> Core Domain / StateMachine / WorkflowEngine
```

No Core module imports a v3.5 module. Presentation adapters render shared DTOs
only. Repository and Knowledge Repository interfaces remain canonical, and
WorkflowEngine remains the only Agent-execution path.

## Admission Constraints

Every v3.5 Issue must prove exactly one Page per execution. StateMachine-derived
legal transitions remain mandatory; no stage can be skipped. A storyboard must
persist before generation and quality must complete before approval. No Issue
may permit multi-page generation, implicit writes, Provider or Agent calls,
remote collection, scheduling, deployment, tagging, signing, publication, or
release action.
