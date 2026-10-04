# v3.2 Quality Gates

| Gate | Admission requirement |
| --- | --- |
| Creative Studio Validation | Workspace/session/dashboard candidate is DTO-only, human-owned, and cannot execute, write, or approve. |
| Asset Intelligence Validation | Candidate uses the Repository port, preserves provenance/redaction policy, and cannot fetch or persist implicitly. |
| Workflow Evolution Validation | Template/profile candidate observes StateMachine authority and cannot change transitions, stages, or page count. |
| Production Analytics Validation | Report uses bounded local evidence and cannot collect remotely, configure, deploy, schedule, or publish. |
| Backward Compatibility Validation | v1.x–v3.1 Python API, CLI, FastAPI, MCP, Web UI, Workflow, Repository, Plugin, SDK, Provider, Backend, Automation, and Notification contracts remain unchanged. |

Every implementation proposal must also pass architecture/import, deterministic
fixture, documentation-link, security/redaction, benchmark-smoke where
applicable, and existing release-contract gates.

## Iteration 1 evidence

| Gate | Evidence |
| --- | --- |
| Creative Studio Validation | `test_v3_2_foundation.py` proves the workspace/session projection never persists, executes, or approves. |
| Asset Intelligence Validation | The same contract test proves metadata values remain redacted and the Repository remains readable after projection. |
| Workflow Profile Validation | The profile reports the existing StateMachine next command but does not transition the one-page context. |
| Production Analytics Validation | Review/quality/approval and runtime automation flags stay false in the report. |
| Workspace Dashboard Validation | FastAPI and MCP delivery tests assert only immutable Application DTO payloads cross the boundary. |

## Iteration 2 evidence

| Gate | Evidence |
| --- | --- |
| Creative Workspace Validation | Workspace sessions, timelines, tasks, activities, and progress remain analysis-only; task assignment and approval are prohibited. |
| Asset Analytics Validation | Usage, dependency, quality, and relationship metrics retain metadata-value redaction and read-only Repository access. |
| Workflow Intelligence Validation | Efficiency, bottleneck, recommendation, timeline, and health use StateMachine observation only and cannot transition the Page. |
| Production Insights Validation | Quality/review/productivity/forecast reports cannot score, forecast, automate, publish, or authorize a release. |
| Pipeline Analysis Validation | Pipeline bottleneck delivery is a DTO-only projection and cannot apply a profile or execute a workflow command. |

## Iteration 3 evidence

| Gate | Evidence |
| --- | --- |
| Creative Reliability Validation | Validation, consistency, integrity, workspace reliability, and readiness reports retain one-Page scope and human approval. |
| Asset Governance Validation | Integrity, lifecycle, compliance, quality-evidence, and risk reports preserve redaction and cannot write or repair Repository data. |
| Operational Intelligence Validation | Workflow health, analytics validation, uncomputed trends, and deployment readiness remain diagnostic-only. |
| Release Readiness Validation | Readiness, regression, quality-gate, production, and recommendation DTOs never authorize or publish a release. |
| Compatibility Validation | The additive Python API, CLI, FastAPI, and MCP seams are contract-tested without public-interface changes. |
