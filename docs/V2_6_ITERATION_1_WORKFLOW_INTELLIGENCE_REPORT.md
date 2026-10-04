# v2.6 Iteration 1 Workflow Intelligence Report

## Outcome

The optional Application-layer planning surface is implemented without changing
the Core architecture, Page `WorkflowEngine`, StateMachine, Agent interfaces,
Repository port, or Provider protocol. The package version remains `2.5.0` as
required for the v2.5.x development branch.

## Delivered

- `WorkflowPlanner` returns immutable one-page execution-plan, dependency,
  complexity, estimate, and legal-next-step DTOs.
- `ProviderOrchestrator` projects registered metadata into a capability matrix
  and deterministic selection report with relative latency, explicitly unknown
  cost, and declarative fallback candidates.
- `PlanningService` composes workflow intelligence, planning diagnostics,
  configuration/architecture previews, and JSON/Markdown reports.
- CLI planning commands, optional FastAPI callbacks/routes, and injected MCP
  preview tools expose the same read-only DTOs.
- Examples, benchmarks, documentation, unit tests, quality gates, and the
  technical-debt register cover the new advisory surface.

## Architecture and safety review

The planning module depends inward only on the existing `WorkflowContext`,
`StateMachine`, and passive adapter runtime metadata. It does not create an
Agent, call `WorkflowEngine`, invoke a Provider, mutate context, persist a
Project, schedule work, generate an image, or approve a Page. The StateMachine
remains the sole source of legal transitions. Every report is constrained to
one Page context; no multi-page planning or execution is introduced.

## Validation

Focused tests cover legal next-step recommendation, storyboard and approval
dependencies, Provider matrix and scoring, report rendering, execution preview,
and workflow bottleneck diagnostics. The full static-analysis and test suite
is run before iteration handoff.

## Self review (5-point scale)

| Area | Rating | Evidence |
| --- | --- | --- |
| Architecture | 5/5 | Planning is Application-layer only; Core and Engine remain unchanged. |
| Backward compatibility | 5/5 | Root API is unchanged and delivery additions are optional/injected. |
| Workflow safety | 5/5 | StateMachine-derived recommendation, one-page scope, no execution path. |
| Maintainability | 5/5 | Immutable DTOs, focused facade, deterministic tests, and documented boundaries. |
| Documentation and DX | 5/5 | CLI/MCP/FastAPI seams, JSON/Markdown reports, examples, and benchmarks are documented. |

## Improvement candidates

1. Calibrate relative execution and latency estimates only after approved local
   workload baselines are available.
2. Keep future cost data, fallback execution, and cross-page analytics behind
   separate security, compatibility, and StateMachine-boundary reviews.

## Follow-up boundaries

Calibration from measured workloads, live pricing/latency sources, remote
health probes, fallback execution, cross-page analytics, and automatic
workflow control remain explicit future Issues. None is implied by this
iteration.
