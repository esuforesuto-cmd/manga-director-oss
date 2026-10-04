# V6.1-E03-I01 Contract Decision

## Status

Complete. This Issue records a source-backed decision and introduces no runtime
contract.

## Decision

Do not add a Portfolio or Enterprise observability DTO, service, API, or
benchmark in this Issue.

`docs/ROADMAP_V6.md` identifies Portfolio/Enterprise observability and
scalability validation as a v6 roadmap outcome, but the v6 source and
architecture do not define a v6 Portfolio or Enterprise identity, a
caller-supplied input shape, or summary fields beyond the existing reports.
Creating one would therefore invent semantics rather than implement a defined
contract.

## Product outcome

Option A is approved: close v6.1 Epic 3 using the existing v6 Analytics and
Observability reports. Do not create a Portfolio or Enterprise runtime
contract, public API, or benchmark. The Product Owner decision is recorded in
`V6_1_E03_PRODUCT_DECISION.md`.

## Existing v6 coverage

- `V60CreativeProductionPlatformIntelligenceService.production_analytics()`
  provides deterministic counts for caller-supplied projects, workspaces,
  knowledge, assignments, and services.
- `V60CreativeProductionPlatformCoreService.observability_platform()` provides
  bounded computed or caller-supplied metrics without telemetry or alerts.
- The v6 Platform Kernel baseline remains local, provider-free, single-page,
  and threshold-free. It does not define a Portfolio or Enterprise workload.

These reports remain the available v6 read-only evidence. They are not a
selected Portfolio or Enterprise identity contract.

## v4.4 relationship

The separately versioned v4.4 Portfolio and Enterprise DTOs demonstrate prior
concepts only. This Issue neither adopts nor re-exports them. Reuse would
require an explicit compatibility decision in a future approved plan.

## Benchmark decision

No new benchmark is justified. A local scale benchmark would require an
approved deterministic fixture and workload for a defined v6 contract. Fixed
performance thresholds and cross-version comparison remain out of scope.

## Retained boundaries

- Inputs remain caller-supplied; no discovery, Repository access, persistence,
  caching, remote query, or external communication is introduced.
- No Workflow execution, StateMachine transition, approval, scheduling,
  Provider invocation, Plugin registration, or Plugin execution is introduced.
- The one-page workflow, storyboard-before-generation, and
  review-before-approval invariants remain unchanged.
- Existing v5.x, v6.0, and v6.1 public APIs and additive contracts remain
  unchanged.

## Conditions for a future implementation Issue

A future Issue must first define and approve all of the following from
repository evidence:

1. a v6 Portfolio or Enterprise identity and caller-supplied input shape;
2. summary fields not already available through v6.0 Analytics or
   Observability;
3. the compatibility relationship to v4.4 surfaces; and
4. a deterministic local fixture and workload if scale validation is required.

Without those decisions, no source-backed local runtime work remains for this
Epic. Epic 3 is closed.

## Deferred work

Cross-version benchmark comparison and hosted Enterprise validation remain
deferred as recorded in `docs/TECHNICAL_DEBT_REGISTER.md`.
