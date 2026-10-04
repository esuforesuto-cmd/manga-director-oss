# GitHub Planning: v2.3

## Milestone

Create the GitHub milestone **v2.3.0 — Enterprise and Ecosystem Readiness**.
It is a non-breaking, Issue-driven milestone on the v2.2.x development branch.
This repository does not create remote GitHub resources; maintainers can use
this document as the import-ready source.

## Issue taxonomy

| Type | Purpose | Required fields |
| --- | --- | --- |
| Epic | Cross-cutting outcome | measurable outcome, compatibility boundary, child Issues, owner |
| Feature | Approved additive capability | architecture decision, migration, tests, docs, rollback |
| Enhancement | Safe improvement to an existing surface | affected contract, before/after evidence, tests |
| Performance | Measured optimization or benchmark | baseline, workload, budget, rollback criterion |
| Security | Threat-boundary or dependency work | threat model, validation, audit evidence |
| Infrastructure | CI, package, test, benchmark, or tooling | reproducibility, ownership, secret policy |
| Documentation | User/operator/contributor guidance | audience, release, link checks |
| Maintenance | Compatibility, dependency, or release upkeep | supported versions, regression checks |

## Initial Epics

1. **Enterprise Operational Readiness** — configuration profiles, audit,
   diagnostics, security, notification, database, and recovery evidence.
2. **AI Provider Contract Readiness** — provider proposals, mock contracts,
   secret handling, latency measurement, and compatibility fixtures.
3. **Image Backend Contract Readiness** — backend feasibility, workflow input,
   artifact ownership, and mock contract criteria.
4. **Large-Scale Evidence** — repository/workflow measurement, regression
   budgets, and sequential Batch operational evidence.

## Labels and rules

Use one taxonomy label and existing area labels such as `workflow`, `database`,
`plugin`, `extension`, `llm`, `image`, `notification`, `automation`,
`security`, and `performance`. Apply `breaking-change` only to proposals that
must be deferred. Every Issue assigned to the milestone must include a
compatibility statement and an explicit out-of-scope section.
