# GitHub Planning: v2.6

## Milestone

Create GitHub milestone **v2.6.0 — AI Workflow Intelligence and Enterprise
Operations** on the v2.5.x development branch. This file is import-ready
planning source only; it does not create remote GitHub resources.

## Issue taxonomy

| Type | Purpose | Required evidence |
| --- | --- | --- |
| Epic | Cross-cutting outcome | measurable result, compatibility boundary, child Issues, owner |
| Feature | Approved additive capability | architecture decision, migration, tests, docs, rollback |
| Reliability | Recovery or failure isolation | fault model, admission behavior, recovery test |
| Performance | Measured planning or optimization | baseline, workload, budget, rollback |
| Automation | Advisory planning only | human approval boundary, no execution, audit evidence |
| Enterprise | Operating, compliance, or capacity evidence | ownership, security, retention, runbook |
| Documentation | User, operator, or contributor guidance | audience, links, release impact |
| Developer Experience | Contributor productivity | setup impact, command evidence, documentation |
| Maintenance | Compatibility or dependency upkeep | supported-version evidence, regression proof |

## Initial epics

1. **AI Workflow Intelligence**: planning, coordination, prompt diagnostics,
   checkpoints, analytics, and execution-plan evidence.
2. **Provider Orchestration**: capability matching, selection, fallback, cost,
   latency, caching, and policy recommendation designs.
3. **Enterprise Operations**: dashboard, deployment validation, configuration,
   compliance, audit, maintenance, and capacity planning.
4. **Automation Planning**: task scheduling and checkpoints as non-executing
   designs with explicit human control.
5. **Developer Productivity and Quality**: planning fixtures, benchmarks,
   documentation, compatibility gates, and technical-debt review.

Use one taxonomy label plus area labels such as `workflow`, `agent`, `prompt`,
`provider`, `image`, `automation`, `enterprise`, `operations`, `security`,
`performance`, `documentation`, and `dx`. Every Issue must state scope
exclusions, test plan, benchmark plan where relevant, and rollback plan.
