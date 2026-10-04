# v3.4 Quality Gates

| Gate | Admission requirement |
| --- | --- |
| Knowledge Platform Validation | Uses only existing Repository/public-port evidence, documents provenance/redaction/retention, and cannot write, merge, repair, archive, delete, or fetch remotely. |
| Production Operations Validation | Consumes bounded local evidence and cannot monitor remotely, alert, schedule, deploy, configure, restart, or remediate. |
| Organization Intelligence Validation | Uses redacted supplied evidence, documents attribution/retention/assumptions, and cannot score people, assign work, alter membership, or commit delivery. |
| Release Intelligence Validation | Maps to existing release evidence and cannot tag, sign, publish, deploy, approve, or bypass the release checklist. |
| Backward Compatibility Validation | v1.x-v3.3 Python API, CLI, FastAPI, MCP, Web UI, Workflow, Repository, Knowledge, Creative, Asset, Analytics, Review, Diagnostics, Reporting, Governance, Health, Plugin, SDK, Provider, Backend, Automation, and Notification contracts remain unchanged. |

Every implementation proposal must also pass architecture/import, deterministic
fixture, documentation-link, security/redaction, benchmark-smoke where
applicable, and existing release-contract gates.

## Iteration 1 evidence

| Gate | Evidence |
| --- | --- |
| Knowledge Platform Validation | `test_v3_4_foundation.py` proves Repository reads remain read-only, relationships and indexes are not persisted, and no remote search occurs. |
| Production Operations Validation | Dashboard, status, capacity, timeline, and summary DTOs cannot monitor, allocate, schedule, execute, configure, remediate, or deploy. |
| Organization Intelligence Validation | Team, role, workload, collaboration, risk, and executive DTOs cannot score people, assign work, alter membership, or commit delivery. |
| Release Intelligence Validation | Health, deployment, compatibility, regression, and executive DTOs cannot authorize, tag, sign, publish, deploy, or remediate a release. |
| Release Health Validation | The canonical package version is observed only; release health does not replace compatibility or hosted release validation. |
| Delivery Boundary Validation | New CLI, FastAPI, and MCP entry points return shared immutable Application DTOs only. |

## Iteration 2 evidence

| Gate | Evidence |
| --- | --- |
| Knowledge Intelligence Validation | Repository-derived catalog, relationship, quality, coverage, and recommendation reports remain read-only; no index, relationship, remote search, score, correction, or recommendation is applied. |
| Production Optimization Validation | Efficiency, capacity, allocation, and bottleneck DTOs do not plan capacity, allocate/rebalance resources, modify a workflow, remediate, schedule, or deploy. |
| Organization Analytics Validation | Trend, productivity, collaboration, role, and forecast DTOs do not score people, collect data, assign work, notify, change roles, or commit delivery. |
| Release Analytics Validation | Trend, deployment, regression, compatibility, and forecast DTOs do not collect remote evidence, deploy, remediate, change APIs, authorize, tag, sign, or publish. |
| Capacity Optimization Validation | Capacity recommendations are local, one-Page observations and cannot alter the Production Pipeline or StateMachine. |
| Delivery Boundary Validation | Additive CLI, FastAPI, and MCP adapters return only the corresponding immutable v3.4 dashboard DTO. |

## Iteration 3 evidence

| Gate | Evidence |
| --- | --- |
| Knowledge Governance Validation | Policy, compliance, audit, retention, summary, and dashboard DTOs use only existing Repository-derived evidence and cannot enforce, persist, retain, merge, repair, archive, delete, or expose metadata values. |
| Production Governance Validation | StateMachine and human-approval policies are observed only; reports cannot enforce, alter the pipeline, start an operation, schedule, allocate, remediate, execute, approve, configure, or deploy. |
| Organization Governance Validation | Organization policies and audits cannot collect external data, score people, assign work, change roles or membership, notify, persist evidence, or commit delivery. |
| Release Governance Validation | Release policies and audits cannot collect hosted evidence, enforce a gate, remediate, authorize, tag, sign, publish, or deploy. |
| Governance Dashboard Validation | CLI, FastAPI, and MCP return immutable shared dashboard DTOs only and do not expose internal models or mutation paths. |
