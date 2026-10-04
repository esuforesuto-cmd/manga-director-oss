# v6.1 Epic 3 Proposal: Portfolio and Enterprise Observability Scope Decision

## Status

Complete. Option A was approved: existing v6 reports close Epic 3. This
document authorizes no code change.

## Repository evidence

- `docs/ROADMAP_V6.md` identifies "Portfolio/enterprise observability and
  scalability benchmarks" as the remaining Iteration 2 scale outcome.
- `docs/PLATFORM_BLUEPRINT.md` identifies portfolio and production overview as
  a Platform responsibility, and requires scalability validation before any
  execution path.
- `docs/ARCHITECTURE_V6_0.md` requires identifier-based summaries, pagination,
  bounded traversal, and immutable snapshots; execution, persistence, and
  queueing remain out of scope.
- `V60CreativeProductionPlatformIntelligenceService.production_analytics()`
  already reports deterministic caller-supplied project, workspace, knowledge,
  assignment, and service counts. `V60CreativeProductionPlatformCoreService`
  already derives bounded, non-telemetry observability metrics.
- Existing v4.4 Portfolio and Enterprise reports are separately versioned
  surfaces. No v6 source artifact currently selects them as the v6 Portfolio
  or Enterprise contract.
- The only v6 benchmark baseline is the local, provider-free Platform Kernel
  baseline. It has no fixed timing threshold and no cross-version comparison.

## Objective

Resolve the outstanding roadmap scope without duplicating existing analytics:
determine whether v6.0 analytics and observability already satisfy the intended
Portfolio and Enterprise view, or define the smallest additive, caller-supplied
read-model contract that is still required.

## Scope

1. Produce a contract decision for Portfolio and Enterprise identity,
   caller-supplied inputs, summary fields, and relationship to the existing
   v6.0 analytics and observability reports.
2. Assess reuse of v4.4 Portfolio and Enterprise DTOs as evidence only; do not
   adopt, change, or re-export them without an approved compatibility decision.
3. Decide whether a v6.1 scale benchmark is necessary for the accepted
   contract. A benchmark requires a deterministic local fixture and an explicit
   workload definition before implementation.
4. If a new report is approved, keep it additive, opt-in, deterministic,
   immutable, read-only, transport-neutral, and limited to caller-supplied
   references.

## Explicit non-goals

- Repository, database, filesystem, remote, or cross-workspace discovery.
- Persistence, caching, background processing, telemetry, alerting, or hosted
  Enterprise probes.
- Workflow execution, StateMachine transitions, approval, scheduling, Provider
  calls, or external communication.
- Fixed performance thresholds or cross-version benchmark comparison.
- Replacing v6.0 analytics, observability, Project Hub, Workspace Hub, or the
  completed v6.1 pagination and Knowledge Graph contracts.

## Acceptance criteria

- The decision identifies an actual v6 gap or records that the existing v6.0
  reports are sufficient.
- Any proposed input is caller-supplied and any output is an immutable,
  deterministic summary; no source record is changed.
- Any proposed scale validation has a documented local fixture, workload, and
  no-threshold rationale. It does not reuse the deferred cross-version
  comparison debt as an implementation requirement.
- Existing one-page workflow, storyboard-before-generation, and
  review-before-approval invariants remain outside the proposed read model and
  unchanged.
- The proposal maps each future code, test, and documentation change to a
  source-backed requirement before implementation begins.

## Deliverables

- A v6.1 Portfolio and Enterprise observability contract-decision record.
- A decision on whether a deterministic local scale benchmark is justified.
- If and only if a gap is confirmed, one approved implementation Issue with
  precise DTO, service, test, and documentation scope.

## Dependencies

- Completed v6.1 Project and Workspace pagination contract.
- Completed v6.1 Knowledge Graph metadata and bounded traversal contracts.
- Existing v6.0 Production Analytics and Observability Platform reports.
- `docs/TECHNICAL_DEBT_REGISTER.md`; external hosted deployment probes and
  cross-version benchmark comparison remain deferred.

## Risks

- "Portfolio" and "Enterprise" have no selected v6 DTO contract; creating one
  without the decision step would duplicate v4.4 surfaces or invent semantics.
- A benchmark without an accepted workload would be speculative and could be
  misread as a performance guarantee.
- Hosted Enterprise validation is owner-controlled and cannot be satisfied by
  a local read-model implementation.

## Outcome

`V6.1-E03-I01` completed the contract decision. The approved Product Owner
decision is recorded in `V6_1_E03_PRODUCT_DECISION.md`: use the existing v6
Analytics and Observability reports and create no implementation Issue.

## Historical proposed issue order

1. `V6.1-E03-I01 — Portfolio and Enterprise Observability Contract Decision`
   (documentation and source review only).
2. Do not create an implementation Issue unless I01 confirms an unmet,
   source-backed local contract.

## Compatibility

Preserve all v5.x and v6.0 public APIs and the existing v6.1 additive
contracts. This proposal does not change code, package metadata, dependencies,
or release state.
