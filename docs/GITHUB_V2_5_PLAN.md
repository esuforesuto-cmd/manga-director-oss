# GitHub Planning: v2.5

## Milestone

Create GitHub milestone **v2.5.0 - Production Excellence and Ecosystem
Readiness** on the v2.4.x development branch. This is an import-ready planning
source only; it does not create remote GitHub resources.

## Issue taxonomy

| Type | Purpose | Required evidence |
| --- | --- | --- |
| Epic | Cross-cutting outcome | measurable result, compatibility boundary, child Issues, owner |
| Feature | Approved additive capability | architecture decision, migration, tests, docs, rollback |
| Maintenance | Compatibility or dependency upkeep | supported-version evidence, regression proof |
| Performance | Measured improvement | baseline, workload, budget, rollback |
| Reliability | Recovery or failure isolation | fault model, admission behavior, recovery test |
| Security | Threat-boundary work | threat model, validation, audit evidence |
| Documentation | User, operator, or contributor guidance | audience, links, release impact |
| Infrastructure | CI, package, or tooling work | reproducibility, ownership, secret policy |
| Developer Experience | Contributor productivity | setup impact, command evidence, documentation |
| Production | Operating readiness | health, diagnostics, rollback, ownership |

## Initial epics

1. **Production Excellence**: workflow/repository recovery, configuration,
   logging, health, diagnostics, deployment, and runbook evidence.
2. **Quality Automation**: architecture, compatibility, upgrade, package,
   benchmark, and release gates.
3. **Provider Ecosystem Contracts**: candidate LLM reviews, deterministic mock
   fixtures, secret policy, and Provider compatibility evidence.
4. **Image Backend Ecosystem Contracts**: candidate backend metadata, presets,
   artifact boundaries, and compatibility evidence.
5. **Long-term Maintainability**: technical-debt triage, large-project evidence,
   documentation upkeep, and contributor automation.

Use one taxonomy label plus area labels such as `workflow`, `repository`,
`database`, `llm`, `image`, `plugin`, `extension`, `notification`,
`automation`, `security`, `performance`, `documentation`, `dx`, and
`production`. Every milestone Issue must state compatibility, scope exclusions,
test plan, benchmark plan where relevant, and rollback plan.
