# GitHub Planning: v2.4

## Milestone

Create GitHub milestone **v2.4.0 — Production and Ecosystem Readiness** on the
v2.3.x development branch. This file is the import-ready source; it does not
create remote GitHub resources.

## Issue taxonomy

| Type | Purpose | Required evidence |
| --- | --- | --- |
| Epic | Cross-cutting outcome | measurable result, compatibility boundary, child Issues, owner |
| Feature | Approved additive capability | architecture decision, migration, tests, docs, rollback |
| Enhancement | Safe improvement | affected contract, before/after evidence, tests |
| Performance | Measured change | baseline, workload, budget, rollback |
| Security | Threat-boundary work | threat model, validation, audit evidence |
| Infrastructure | CI/package/tooling work | reproducibility, ownership, secret policy |
| Documentation | User/operator/contributor guidance | audience, links, release impact |
| Maintenance | Compatibility/dependency upkeep | supported versions, regression evidence |
| Developer Experience | Contributor productivity | setup impact, command evidence, documentation |

## Initial epics

1. **Production Operations Readiness** — workflow/repository/database recovery,
   configuration governance, logging, diagnostics, health, and runbooks.
2. **Observability Evidence** — stable DTOs, safe exports, timelines, metrics,
   benchmark recording, and operational smoke fixtures.
3. **Provider Ecosystem Contracts** — LLM provider proposals, selection/failure
   tests, secrets policy, and compatibility fixtures.
4. **Image Backend Ecosystem Contracts** — backend discovery, workflow metadata,
   presets, artifact boundaries, and compatibility fixtures.
5. **Developer Productivity** — reproducible quality gates, benchmark workflow,
   contributor feedback, and documentation maintenance.

Use one taxonomy label plus area labels (`workflow`, `repository`, `database`,
`llm`, `image`, `plugin`, `extension`, `notification`, `automation`,
`security`, `performance`, `documentation`, `dx`). Every milestone Issue must
state backward compatibility, scope exclusions, test plan, and rollback plan.
