# v3.3 Quality Gates

| Gate | Admission requirement |
| --- | --- |
| Production Pipeline Validation | Candidate maps only existing StateMachine evidence and cannot execute, transition, approve, publish, or schedule. |
| Quality Intelligence Validation | Candidate consumes bounded review/quality evidence, retains human quality and approval authority, and cannot remediate. |
| Asset Lifecycle Validation | Candidate uses the Repository port, preserves ownership/provenance/redaction/retention policy, and cannot archive, delete, or persist implicitly. |
| Project Intelligence Validation | Candidate documents bounded inputs and assumptions and cannot allocate, schedule, mutate, or commit delivery. |
| Backward Compatibility Validation | v1.x–v3.2 Python API, CLI, FastAPI, MCP, Web UI, Workflow, Repository, Knowledge, Plugin, SDK, Provider, Backend, Automation, and Notification contracts remain unchanged. |

Every implementation proposal must also pass architecture/import, deterministic
fixture, documentation-link, security/redaction, benchmark-smoke where
applicable, and existing release-contract gates.

## Iteration 1 evidence

| Gate | Evidence |
| --- | --- |
| Production Pipeline Validation | `test_v3_3_foundation.py` proves stages are observed, the suggested transition is not applied, and approval/publishing stay disabled. |
| Quality Intelligence Validation | Metrics, rules, and findings are diagnostic DTOs; scoring, remediation, and approval authority remain false. |
| Asset Lifecycle Validation | Lifecycle, history, archive, and dependency projections use the existing Repository port and never archive, delete, or persist. |
| Project Intelligence Validation | Health, milestone, resource, schedule, risk, and executive DTOs cannot allocate, schedule, mutate, or commit delivery. |
| Project Health Validation | Existing chapter/page/context evidence is projected without an authoritative score or Project mutation. |
| Delivery Boundary Validation | FastAPI routes, MCP tools, and CLI commands return shared Application DTOs only. |

## Iteration 2 evidence

| Gate | Evidence |
| --- | --- |
| Production Intelligence Validation | Stage/timeline/bottleneck/optimization DTOs observe existing pipeline evidence and cannot execute, transition, or optimize a workflow. |
| Quality Analytics Validation | Trend, regression, coverage, consistency, and executive reports do not score, remediate, complete review, or approve. |
| Asset Intelligence Validation | Usage, dependency, consistency, recommendation, and health reports use redacted Repository-derived lifecycle evidence without writes. |
| Project Operations Validation | Milestone, resource, forecast, and risk reports cannot allocate, schedule, mitigate, or commit delivery. |
| Pipeline Efficiency Validation | The benchmark and service projection are one-Page, provider-free, and do not apply optimization. |
| Delivery Boundary Validation | CLI, FastAPI, and MCP expose the same shared Application dashboard DTOs. |

## Iteration 3 evidence

| Gate | Evidence |
| --- | --- |
| Production Governance Validation | Policy, compliance, pipeline, audit, and summary DTOs cannot enforce a policy, change a pipeline, execute, publish, or approve. |
| Quality Governance Validation | Policy, compliance, audit, and summary DTOs cannot score, remediate, complete review, or authorize approval. |
| Asset Governance Validation | Redacted Repository-derived controls, audit, and retention DTOs cannot evaluate/apply retention, archive, delete, repair, or write. |
| Project Governance Validation | Governance, compliance, risk, dashboard, and summary DTOs cannot schedule, allocate, accept/mitigate risk, or commit delivery. |
| Governance Dashboard Validation | New CLI, FastAPI, and MCP entry points return shared immutable Application DTOs only. |
