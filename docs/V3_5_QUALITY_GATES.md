# v3.5 Quality Gates

| Gate | Admission requirement |
| --- | --- |
| Knowledge Graph Validation | Uses existing Repository/Knowledge-port evidence with provenance, redaction, retention, and no-write/no-remote proof. |
| Creative Intelligence Validation | Uses completed local planning/quality evidence and cannot generate, rewrite, decide, bypass review, or approve. |
| Production Intelligence Validation | Uses bounded local evidence and cannot schedule, allocate, alter workflow, remediate, deploy, or commit delivery. |
| Platform Analytics Validation | Uses deterministic supplied snapshots and cannot collect externally, persist telemetry, trigger actions, or authorize a release. |
| Backward Compatibility Validation | v1.x-v3.4 Python API, CLI, FastAPI, REST, MCP, Web UI, Workflow, Repository, Knowledge, Creative, Asset, Analytics, Review, Diagnostics, Reporting, Governance, Operations, Health, Plugin, SDK, Provider, Backend, Automation, and Notification contracts remain unchanged. |

Every implementation proposal must also pass architecture/import, one-Page
StateMachine invariant, deterministic fixture, documentation-link,
security/redaction, benchmark-smoke where applicable, and existing
release-contract gates.

## Iteration 1 evidence

| Gate | Evidence |
| --- | --- |
| Knowledge Graph Validation | Node, edge, context, trace, summary, report, and dashboard DTOs use existing Repository reads only; no graph is persisted or fetched remotely. |
| Creative Intelligence Validation | Creative metrics and analysis DTOs cannot generate, alter a story/storyboard, complete review, or approve a Page. |
| Production Intelligence Validation | Pipeline, capacity, delivery, health, and executive DTOs cannot schedule, allocate, modify workflow, remediate, or deploy. |
| Platform Analytics Validation | Health, trend, historical, KPI, and dashboard DTOs use local evidence and cannot collect, persist, monitor, enforce, or act. |
| Platform Health Validation | Health is a bounded DTO observation and cannot start monitoring or establish a production SLO. |

## Iteration 2 evidence

| Gate | Evidence |
| --- | --- |
| Knowledge Analytics Validation | Insight, coverage, relationship, recommendation, health, and dashboard DTOs derive from the existing graph projection; no graph/coverage persistence or recommendation application is possible. |
| Creative Analytics Validation | Story, character, Page Quality, trend, recommendation, and dashboard DTOs cannot generate, change creative input, complete review, or approve. |
| Production Analytics Validation | Efficiency, forecast, risk, optimization, executive, and dashboard DTOs cannot schedule, allocate, change workflow, remediate, deploy, or commit delivery. |
| Platform Analytics Validation | KPI, historical, regression, executive, health, and dashboard DTOs cannot collect, persist, monitor, enforce, authorize, remediate, or act. |

## Iteration 3 evidence

| Gate | Evidence |
| --- | --- |
| Governance Validation | Knowledge, Creative, Production, and Platform governance DTOs are additive projections with no StateMachine, Repository, workflow, or external authority. |
| Policy Validation | Policy DTOs document human-owned boundaries only; no policy is stored, applied, or enforced. |
| Compliance Validation | Compliance evidence is observational and cannot verify, remediate, authorize, or change source evidence. |
| Audit Validation | Audit DTOs expose bounded local counts only and cannot retain or send an audit record. |

## RC1 evidence

| Gate | Evidence |
| --- | --- |
| RC Readiness Validation | v3.5 Foundation, Intelligence, Governance, integration, delivery, version, release-assets, and invariant checks pass locally. |
| Release Compatibility Validation | v3.4 public Python, CLI, FastAPI, REST, MCP, Repository, Workflow, Extension SDK, and Web UI contracts remain additive-only. |
| Performance Regression Validation | Provider-free graph, analytics, dashboard, Repository, and reporting benchmark smoke reports no local regression requiring correction. |
| Documentation Validation | v3.5 domain guides and RC release, architecture, compatibility, workflow, benchmark, security, checklist, and readiness records are present and linked. |

## Final release evidence

| Gate | Evidence |
| --- | --- |
| Release Readiness | Stable version propagation, full local verification, wheel/sdist, Twine, clean-install CLI/MCP, and release assets pass. |
| OSS Readiness | License, governance, support, contribution, dependency-license, SBOM, and release documentation assets are present. |
| Backward Compatibility | v3.4 and prior public contracts remain additive-only; no migration is required. |
| Documentation Quality | README, release, migration, architecture, workflow, benchmark, security, package, and final-readiness documents are present and linked. |
| Package Quality | Dynamic package version, typed marker, optional extras, README, MIT License, wheel, and sdist validation pass. |
