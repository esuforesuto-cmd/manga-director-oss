# v5.2 Automation Planning Quality Gates

| Gate | Pass criteria |
| --- | --- |
| Automation architecture validation | Framework, templates, events, rules, plans, and governance have explicit non-overlapping owners. |
| Rule safety validation | Rules are deterministic, explainable, side-effect free, and fail closed on missing or conflicting evidence. |
| Event safety validation | Events are supplied immutable evidence with no delivery, queue, retry, replay, or handler semantics. |
| Workflow invariant validation | Plans preserve StateMachine authority, one-Page scope, stages, storyboard, and quality-review boundaries. |
| LTS compatibility validation | Every proposal is optional, additive, and has a legacy-only fallback. |
| Automation governance validation | Owners, provenance, evidence, approval boundary, and audit explanation are required. |
| Documentation validation | Vision, architecture, framework, event, rule, governance, roadmap, migration, and report links resolve. |

No implementation may advance beyond planning until these gates have executable
fixtures reviewed by the owning layer.

## v5.2 Iteration 1 executable gates

| Gate | Pass criteria |
| --- | --- |
| Automation Engine Validation | Preview requires known descriptors, matching Page references, evidence, and a human approval boundary; it never executes or mutates a workflow. |
| Rule Engine Validation | Evaluation is deterministic, explainable, side-effect free, and rejects execution, self-learning, or automatic approval flags. |
| Workflow Template Validation | Templates are exactly one Page, remain human-reviewed, and cannot start or mutate workflows. |
| Event Bus Validation | Local event records reject duplicates and report no dispatch, queue, retry, replay, or handler execution. |
| Automation Registry Validation | Explicit template/rule metadata remains local, duplicate-free, and cannot dynamically discover or activate runtime capabilities. |
| v5.0 LTS Compatibility Validation | The new SDK preview and DTO exports are opt-in; existing public API, Workflow, repository, CLI, FastAPI, MCP, and Web UI paths are unchanged. |

## v5.2 Iteration 2 executable gates

| Gate | Pass criteria |
| --- | --- |
| Automation Intelligence Validation | Dashboard findings and readiness are derived from a local engine preview, require human review, and never execute or decide. |
| Rule Analytics Validation | Analytics expose explicit evidence coverage and safety flags without changing, inferring, or enforcing a rule. |
| Event Processing Validation | Event diagnostics preserve provenance visibility while reporting no dispatch, queue, retry, replay, handler, or processing activity. |
| Workflow Optimization Validation | Recommendations preserve one-Page scope and StateMachine authority; no workflow optimization or mutation is applied. |
| Automation Dashboard Validation | The presentation-neutral DTO remains opt-in and cannot approve, persist, route, schedule, or activate automation. |
| v5.0 LTS Compatibility Validation | Automation Intelligence is additive to v5.0/v5.1 public contracts and leaves existing API, Workflow, repository, CLI, FastAPI, MCP, and Web UI behaviour unchanged. |

## v5.2 Iteration 3 executable gates

| Gate | Pass criteria |
| --- | --- |
| Automation Governance Validation | Policy and compliance reports require one-Page, evidence, rule safety, StateMachine authority, and a declared human approval boundary without enforcement. |
| Rule Governance Validation | Rule audit verifies explicit owner, evidence, and non-execution safety flags without learning, editing, or automatic approval. |
| Automation Observability Validation | Observations are local preview metadata and report no telemetry, monitoring, alert, or persistence activity. |
| Automation Reliability Validation | Reliability is confidence-only and reports no health check, retry, recovery, repair, or runtime reconfiguration. |
| Automation Lifecycle Validation | Lifecycle stays advisory and cannot transition, persist, retain, archive, restore, or recover an automation. |
| Automation Integration Validation | The composed report is planning-only, Human-in-the-Loop, StateMachine-authoritative, and additive to v5.0 LTS contracts. |

## v5.2 RC1 release gates

| Gate | Pass criteria |
| --- | --- |
| RC Readiness Validation | Automation Foundation, Intelligence, Governance, Observability, Reliability, and Lifecycle reports are local, non-executing, human-gated, and documented. |
| Release Compatibility Validation | v5.0 LTS and v5.1 public API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, Extension SDK, Provider, and Backend contracts remain unchanged. |
| Performance Regression Validation | Local Automation maturity reporting completes without runtime activation; existing v5.1 composition reference remains available. |
| Documentation Validation | Release, architecture, compatibility, workflow, benchmark, security, package, checklist, readiness, and GitHub release-note links resolve. |
| Automation Framework End-to-End Validation | One advisory Automation request preserves one-Page repository/workflow behaviour and records no execution, dispatch, mutation, or automatic action. |

## v5.2 final release gates

| Gate | Pass criteria |
| --- | --- |
| Release Readiness | Version, package, documentation, release evidence, and local Automation Framework validation are complete. |
| OSS Readiness | Wheel/sdist, typed marker, LICENSE, optional extras, metadata, and import smoke are verified locally. |
| Backward Compatibility | v5.0 LTS/v5.1 API, Workflow, CLI, FastAPI/REST, MCP, Web UI, Repository, and SDK contracts remain unchanged. |
| Documentation Quality | Final release, migration, architecture, compatibility, benchmark, security, package, summary, and release-ready documents resolve. |
| Package Quality | Final wheel/sdist metadata and content are valid with version `5.2.0`. |
