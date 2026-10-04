# v2.4 Development Planning Report

## Decision

v2.4 begins as an Issue-driven cycle on the v2.3.x development branch. The
v2.3.0 Core architecture, public API, StateMachine, one-page workflow rule,
persisted-storyboard requirement, quality-before-approval rule, and explicit
human approval remain fixed.

## Planning deliverables

- [Roadmap v2.4](ROADMAP_v2_4.md): Must/Should/Could/Won't priorities, reasons,
  Issue counts, estimates, and owning layers.
- [GitHub Planning v2.4](GITHUB_V2_4_PLAN.md): milestone, Epic/Feature/
  Enhancement/Performance/Security/Infrastructure/Documentation/Maintenance/
  Developer Experience taxonomy, initial epics, and Issue rules.
- [Production](PRODUCTION.md), [Operations](OPERATIONS.md), and
  [Monitoring](MONITORING.md): production readiness and observability backlog.
- [Provider Ecosystem](PROVIDER_ECOSYSTEM.md) and
  [Image Backend Ecosystem](IMAGE_BACKEND_ECOSYSTEM.md): candidate-only
  integration contracts.
- [v2.4 Benchmark Backlog](../benchmarks/v2_4_backlog.md): five proposed,
  non-runnable benchmark specifications.

## Scope controls

No Core redesign, public contract change, Provider/Backend implementation,
Marketplace, Cloud SaaS, distributed workflow, microservice, or live network
test is authorized by this planning phase. Future code requires an accepted
Issue, mock/local fixtures, compatibility evidence, and all quality gates.

## Quality and debt posture

The v2.4 gates now explicitly require production smoke, provider/image backend
compatibility, configuration migration, and observability smoke evidence. The
technical-debt register distinguishes resolved v2.3 work from continuing,
deferred, v3, and production targets.

## Development entry criteria

1. Select a Must Issue and assign an owner/layer.
2. Record affected public contracts and a rollback plan.
3. Define mock/local fixture, security/threat boundary, benchmark, test, and
   documentation evidence.
4. Keep architecture, compatibility, security, and documentation-link gates
   green before review.

## Result

v2.4 is ready for continuous Issue-driven development while preserving the
v2.3.0 baseline and its OSS governance/release standards.
