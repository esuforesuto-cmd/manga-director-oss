# v6.1 Epic 3 Architecture Record

## Status

Complete. `V6.1-E03-I01` closed as a contract-decision record. No runtime or
public API implementation is approved or required for Epic 3.

## Decision

Treat the remaining v6 roadmap outcome, Portfolio/Enterprise observability and
scalability validation, as a contract-decision concern before any new runtime
or public surface is considered.

Existing v6.0 Production Analytics supplies deterministic counts of
caller-supplied project, workspace, knowledge, assignment, and service
references. Existing v6.0 Observability supplies bounded computed or supplied
metrics without telemetry or alerts. Neither is a selected v6 Portfolio or
Enterprise identity contract. The separately versioned v4.4 Portfolio and
Enterprise reports are evidence for review, not a v6 dependency or reuse
decision.

## Architecture position

If a local gap is confirmed in a later approved implementation Issue, its
contract belongs in the v6 Application query/report layer. It may compose only
caller-supplied v6 references and existing report evidence. It must not take
ownership of Project, Workspace, Repository, Workflow, StateMachine, Plugin,
or delivery-adapter responsibilities.

The future contract must remain additive, opt-in, deterministic, immutable,
read-only, advisory, and transport-neutral. It must use concise identifiers
and summaries rather than raw cross-project or asset payloads.

## Retained boundaries

- Existing `project_hub()` and `workspace_hub()` semantics remain unchanged.
- Existing v6.1 pagination, Knowledge metadata, and traversal contracts remain
  independent and unchanged.
- No Repository lookup, persistence, caching, background processing, telemetry,
  alerting, remote query, Provider call, or hosted Enterprise probe is allowed.
- No Workflow execution, StateMachine transition, approval, or scheduling is
  allowed. The one-page workflow, storyboard-before-generation, and
  review-before-approval invariants remain owned by existing authorities.
- No CLI, FastAPI, MCP, Web UI, Plugin, SDK, or package contract is added in
  this architecture phase.

## Scalability validation position

The current v6 Platform Kernel baseline is local, single-page, provider-free,
and threshold-free. It does not define a Portfolio/Enterprise workload.
Consequently, this record does not authorize a new benchmark. Any later
benchmark requires an approved deterministic fixture, caller-supplied workload,
and explicit no-threshold rationale. Cross-version comparison remains deferred
under the Technical Debt Register.

## Required decision before implementation

An implementation approval must identify all of the following from source
evidence:

1. the Portfolio or Enterprise identity and caller-supplied input shape;
2. the minimum summary fields not already supplied by v6.0 analytics;
3. the relationship to existing v4.4 reports without changing or re-exporting
   them; and
4. deterministic test fixtures and affected documentation.

`V6.1-E03-I01` is complete. These conditions apply only to a future,
separately approved Portfolio or Enterprise implementation proposal.

## Compatibility

This record introduces no code, public API, dependency, package, or release
change. It preserves the v5.x, v6.0, and completed v6.1 additive contracts.
