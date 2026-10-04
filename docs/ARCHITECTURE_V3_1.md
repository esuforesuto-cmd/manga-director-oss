# v3.1 Architecture Planning

## Status

This document extends the v3.0 architecture through additive planning only. It
does not change Core Architecture, public APIs, workflow execution, repository
serialization, or adapter contracts.

## Planned responsibilities

| Platform | v3.1 planning responsibility | Existing inputs | DTO outputs | Must not do |
| --- | --- | --- | --- | --- |
| Director Platform | Long-term objectives, templates, strategy library, decision history, and creative metrics. | `WorkflowContext`, StateMachine evidence, existing planning reports | Objective, template, strategy, history, metric reports | execute, dispatch, transition, approve |
| Creative Pipeline | Workspace hand-offs, role ownership, review criteria, and approval-plan visibility. | Creative/Review DTOs, artifact evidence | Collaboration and compliance reports | mutate artifacts, pass quality, approve |
| Knowledge Platform | Version, diff, merge-plan, snapshot, timeline, and analytics designs. | Repository-port projections and redaction policy | Version/diff/merge/timeline reports | replace repository, persist or merge implicitly |
| Review Platform | Review workspace criteria, comments-as-evidence, and human decision queues. | Existing quality/review evidence | Review plan and decision-pending DTOs | overrule approval or quality gates |
| Workflow Intelligence | Cross-report metrics, quality trends, and bottleneck explanations. | Existing timeline/metric DTOs | Metrics and recommendation DTOs | schedule, auto-optimize, mutate workflow |
| Observability | Bounded collection schema and report composition. | Existing metrics/tracing/health DTOs | Dashboard/report DTOs | start collectors or emit external telemetry |
| Operations | Maintenance, release, quality, project, and workflow analytics plans. | Diagnostics and release-readiness evidence | Operational plan and summary DTOs | deploy, configure, publish, remediate |
| Developer Platform | Templates, examples, contracts, fixtures, and compatibility tooling. | Public APIs and test evidence | Contributor artifacts | widen root API or bypass admission gates |

## Dependency direction

```text
CLI / FastAPI / MCP / Web UI
        ↓
v3.1 application DTO services
        ↓
v3.0 application services and existing public ports
        ↓
v3.0 Core: Domain / StateMachine / WorkflowEngine / Repository contracts
```

No Core module imports a v3.1 module. Presentation adapters render shared DTOs
and contain no workflow rule. The Repository interface remains the canonical
persistence port, and `WorkflowEngine` remains the only Agent-execution path.

## Implemented v3.1 DTO slices

Iteration 1 implements read-only Collaboration, Knowledge Evolution, Operations,
and Developer Productivity foundations. Iteration 2 adds Creative Review,
Knowledge Analytics, Operations Intelligence, and Developer Experience as a
second Application-layer DTO service. It depends on the Iteration 1 service,
`WorkflowContext`, and the existing `ProjectRepository` port only.

Both slices are delivered through optional CLI, FastAPI, and MCP adapters. They
cannot run a review, transition state, approve a Page, write a Project, mutate
configuration, schedule work, invoke an Agent or Provider, or publish a release.

Iteration 3 adds `V31AssuranceService` as another Application DTO consumer. It
composes the first two slices with the unchanged Repository port for governance,
reliability, readiness, release-quality, and compatibility evidence. It has no
authority to remediate, repair, deploy, enforce a gate, or authorize release.

## Admission constraints

Every future v3.1 implementation must prove: one explicitly scoped Page per
execution; StateMachine-derived legal transitions; no stage skip; persisted
storyboard before generation; quality review before approval; no multi-page
generation; no implicit write, Provider call, Agent call, scheduler, or release
action.
