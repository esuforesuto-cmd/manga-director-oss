# GitHub Planning: v2.2

## Milestone

Create the GitHub milestone **v2.2.0 — Scalability and Operations** after this
plan is merged. Target: planning-led, non-breaking v2.1.x development.

## Issue taxonomy

| Type | Purpose | Required Issue fields |
| --- | --- | --- |
| Epic | Cross-cutting outcome spanning multiple Issues | target metrics, compatibility boundary, child Issues |
| Feature | Approved additive capability | architecture impact, migration, tests, docs |
| Performance | Measured optimization or benchmark work | baseline, workload, budget, rollback criterion |
| Refactor | Internal quality change | public-contract proof, tests, before/after dependency diagram |
| Infrastructure | CI, packaging, benchmark runner, or tooling | reproducibility, security, ownership |
| Documentation | User, operator, or contributor guidance | audience, affected release, link checks |
| Security | Threat-boundary or dependency work | threat model, validation, audit evidence |
| Maintenance | Dependency, compatibility, or release upkeep | affected supported versions, regression checks |

## Initial Epic candidates

1. **Large Project Readiness** — Repository, persistence, query, and resume
   measurement; no Repository-port redesign.
2. **Measured Execution Performance** — Workflow, Batch, Plugin, and adapter
   benchmark baselines with regression thresholds.
3. **Extension Ecosystem Readiness** — SDK compatibility fixtures, Plugin
   guidance, and provider feasibility records.
4. **Operational Confidence** — Notification and database operational evidence,
   release automation, and security gates.

## Label and milestone use

Use existing area labels (`workflow`, `database`, `plugin`, `extension`, `llm`,
`image`, `notification`, `automation`, `frontend`, `backend`, `api`) together
with one taxonomy label above. Apply `breaking-change` only to proposals that
must be deferred from v2.2. All implementation Issues must be assigned to the
v2.2 milestone before work begins.

This repository cannot create remote GitHub milestones or Issues itself; this
document is the import-ready planning source for maintainers.
