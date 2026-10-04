# v6.1 Epic 3 Product Decision

## Status

Approved. Option A closes Epic 3. This document authorizes no code change.

## Approved decision

Use the existing v6.0 Platform Analytics and Observability reports as the
available Portfolio/Enterprise read-only evidence. Do not create a v6
Portfolio or Enterprise identity, runtime contract, public API, or benchmark.

## Repository evidence

- `docs/ROADMAP_V6.md` lists Portfolio/Enterprise observability and
  scalability benchmarks as an Iteration 2 outcome.
- `docs/PLATFORM_BLUEPRINT.md` identifies a portfolio and production overview
  as the Production Platform responsibility.
- `docs/ARCHITECTURE_V6_0.md` limits scale work to identifiers, summaries,
  pagination, bounded traversal, and immutable snapshots.
- `V60CreativeProductionPlatformIntelligenceService.production_analytics()`
  already supplies deterministic caller-supplied counts for projects,
  workspaces, knowledge, assignments, and services.
- `V60CreativeProductionPlatformCoreService.observability_platform()` already
  supplies bounded metrics without telemetry or alerts.
- The v4.4 Portfolio DTO is a separate, single-project versioned surface; it
  is evidence only and is not selected as a v6 dependency.

## Options

### A. Close Epic 3 with existing v6 reports (recommended)

Treat the existing v6.0 analytics and observability reports as the available
Portfolio/Enterprise read-only evidence. Do not add a new identity, report, or
benchmark.

- Compatibility: preserves all v5.x, v6.0, and v6.1 contracts.
- Scope: no code, test, API, dependency, or migration change.
- Limitation: no named v6 Portfolio or Enterprise identity is introduced.

### B. Define a new additive v6 Portfolio or Enterprise read model

Approve a subsequent contract decision that defines the identity,
caller-supplied input shape, summary fields not covered by existing reports,
and any required deterministic local workload.

- Compatibility: must remain additive, opt-in, immutable, read-only, and
  transport-neutral.
- Scope: requires a separately approved implementation Issue after the
  missing product contract is defined.
- Limitation: current sources do not supply those semantics.

### C. Adopt or re-export the v4.4 Portfolio surface

Use the separately versioned v4.4 Portfolio DTOs as a v6 surface.

- Compatibility: requires an explicit version-compatibility decision.
- Scope: not authorized by the current v6 architecture.
- Limitation: v4.4 describes a single caller-supplied project and does not
  establish a v6 multi-project or Enterprise contract.

## Recommendation

**Option A** is approved. It is the only option fully supported by the current
v6 source and accepted architecture without inventing a new product identity or
workload. Option B remains available when Product Owner requirements define a
genuine v6 Portfolio or Enterprise contract.

## Retained boundaries

- No Repository or remote discovery, persistence, caching, telemetry,
  background processing, Provider call, or external communication.
- No Workflow execution, StateMachine transition, approval, scheduling, or
  Plugin lifecycle action.
- The one-page workflow, storyboard-before-generation, and
  review-before-approval invariants remain unchanged.
- Cross-version benchmark comparison and hosted Enterprise deployment probes
  remain deferred in `docs/TECHNICAL_DEBT_REGISTER.md`.

## Outcome after decision

- **Option A:** v6.1 Epic 3 is closed with no implementation Issue.
- **Option B:** create one source-backed contract-decision Issue before any
  implementation planning.
- **Option C:** do not proceed without a dedicated compatibility decision.
