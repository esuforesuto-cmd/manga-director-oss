# Examples

All examples preserve the one-page workflow contract and use only documented
public APIs.

| Track | Example | Status |
| --- | --- | --- |
| Minimal | `minimal.py` | Create a Director and execute one design step. |
| Standard | `workflow.py` | Run a Page through quality, then approve explicitly. |
| Advanced | `custom_generator.py` | Register an image adapter without provider branches. |
| Repository | `repository.py` | Persist a Project through the Repository contract. |
| Performance | `performance/smoke.py` | Run the provider-free benchmark smoke harness. |
| Large Project | `large_project/plan.py` | Plan sequential Chapter/Page work without parallel execution. |
| Database | `database/sqlite.py` | Use the SQLite Repository adapter through its port. |
| Webhook | `webhook/mock_delivery.py` | Exercise notification delivery with a mock provider only. |
| MCP | `mcp/README.md` | Inspect and start the local stdio MCP surface. |
| Repository at scale | `repository_large/selective_read.py` | Use metadata, page, and history selective reads. |
| Batch resume | `batch_resume/README.md` | Inspect sequential checkpoint/resume/retry behavior. |
| Performance measurement | `performance_measurement/workflow_scale.py` | Measure provider-free workflow scale locally. |
| Plugin Runtime | `plugin_runtime/diagnostics.py` | Inspect manifest/discovery/lifecycle cache state. |
| Extension Runtime | `extension_runtime/validator_cache.py` | Reuse cached extension validation safely. |
| Configuration | `configuration/reload.py` | Reuse validated config until a file/env change. |
| Diagnostics | `diagnostics/runtime.py` | Compose a passive runtime diagnostic report. |
| Health check | `health_check/dashboard.py` | Build a safe system-health DTO. |
| System report | `system_report/report.py` | Render JSON and Markdown diagnostics. |
| Recovery | `recovery/integrity.py` | Validate a Project before a manual retry. |
| Production best practices | `production_best_practices/README.md` | Reuse the mock-only readiness report with safe operating steps. |
| Provider selection | `provider_selection/README.md` | Inspect provider-neutral mock selection guidance. |
| Backend selection | `backend_selection/show_selection.py` | Resolve local backend metadata without generation. |
| Upgrade | `upgrade/README.md` | Validate configuration and repository integrity before upgrade/resume. |
| Quality checks | `quality_checks/README.md` | Run provider-free quality evidence for an Issue. |
| Quality pipeline | `quality_pipeline/run.py` | Render six read-only validation DTOs for one Page. |
| Repository validation | `repository_validation/run.py` | Render non-destructive maintenance and integrity evidence. |
| Release validation | `release_validation/run.py` | Check static package, SBOM, and release assets. |
| Workspace validation | `workspace_validation/run.py` | Inspect workspace, build metadata, and declared dependencies. |
| Production summary | `production_summary/run.py` | Combine quality dashboard and repository maintenance DTOs. |
| Observability report | `observability_report/run.py` | Group read-only timelines and metric categories. |
| Diagnostics report | `diagnostics_report/run.py` | Render System through Performance diagnostics sections. |
| Performance analysis | `performance_analysis/run.py` | Compare a local duration snapshot with a baseline. |
| Operations summary | `operations_summary/run.py` | Produce a planning-only maintenance and cleanup report. |
| Performance baseline | `performance_baseline/run.py` | Render baseline comparison and supplied trend direction. |
| v2.6 Workflow planning | `workflow_planning/README.md` | Planning-only track; no workflow execution is implemented. |
| v2.6 Provider selection | `provider_selection/README.md` | Metadata-only orchestration track; no Provider invocation is implemented. |
| v2.6 Provider fallback | `provider_fallback/README.md` | Non-executing fallback-plan track. |
| v2.6 Operations planning | `operations_planning/README.md` | Read-only Enterprise operations planning track. |
| v2.6 Automation plan | `automation_plan/README.md` | Human-reviewed, non-executing automation planning track. |
| v2.7 Director reliability | `director_reliability/README.md` | Validate a single advisory Director plan without executing it. |
| v2.7 Knowledge governance | `knowledge_governance/README.md` | Inspect redacted Repository-port governance evidence. |
| v2.7 Enterprise AI readiness | `enterprise_ai_readiness/README.md` | Generate a checklist-only readiness report. |
| v2.7 Workflow diagnostics | `workflow_diagnostics/README.md` | Render safe Director and Knowledge diagnostics. |
| v2.7 Executive dashboard | `executive_dashboard/director_reliability.md` | Produce a transport-neutral DTO with no UI or release action. |
| v3 Director Platform | `director_platform/README.md` | Design a one-page advisory plan without execution. |
| v3 Multi-Agent | `multi_agent/README.md` | Model role hand-offs without direct agent calls. |
| v3 Creative Pipeline | `creative_pipeline/README.md` | Plan creative checkpoints while retaining workflow guards. |
| v3 Knowledge Graph | `knowledge_graph/README.md` | Describe governed Repository-derived knowledge evidence. |
| v3 Planning Flow | `planning_flow/README.md` | Show the human-decision hand-off to the existing engine. |
| v3 Creative Planning | `creative_planning/run.py` | Render Story through Panel planning without generation. |
| v3 Knowledge Foundation | `knowledge_foundation/run.py` | Render a repository-derived redacted knowledge snapshot. |
| v3 Workflow Intelligence | `workflow_intelligence/run.py` | Inspect a one-page diagnostic dependency/timeline report. |
| v3 Planning Summary | `planning_summary/v3_foundation.py` | Render a compact non-executing Director summary. |
| v3 Multi-Agent | `multi_agent/run.py` | Render proposed roles and hand-offs without Agent execution. |
| v3 Creative Knowledge | `creative_knowledge/run.py` | Render redacted repository-derived knowledge topics. |
| v3 Director Intelligence | `director_intelligence/run.py` | Render advisory alternatives, risks, and recommendations. |
| v3 Review Pipeline | `review_pipeline/run.py` | Render diagnostics that cannot pass quality or approve. |
| v3 Knowledge Relationships | `knowledge_relationship/run.py` | Render bounded identifier/tag relationship evidence. |
| v3 Director Reliability | `director_reliability/v3_readiness.py` | Validate Director evidence without workflow execution. |
| v3 Creative Governance | `creative_governance/run.py` | Render guard/compliance/audit evidence without mutation. |
| v3 Knowledge Integrity | `knowledge_integrity/run.py` | Render redacted integrity, coverage, and risk evidence. |
| v3 Production Readiness | `production_readiness/run.py` | Render checklist-only readiness; no deployment occurs. |
| v3 Release Dashboard | `release_dashboard/run.py` | Render executive readiness with release authorization disabled. |
| v3.1 Creative Collaboration | `creative_collaboration/run.py` | Render human-owned workspace hand-offs without authority. |
| v3.1 Knowledge Evolution | `knowledge_evolution/run.py` | Render redacted version/diff/timeline evidence without writes. |
| v3.1 Operations Foundation | `operations_foundation/run.py` | Render local metrics and health DTOs without automation. |
| v3.1 Developer Productivity | `developer_productivity/run.py` | Render template descriptors without generating files. |
| v3.1 Project Metrics | `project_metrics/run.py` | Render one-Page aggregate metrics without remote collection. |
| v3.1 Creative Review | `creative_review/run.py` | Render advisory review evidence without approval. |
| v3.1 Knowledge Analytics | `knowledge_analytics/run.py` | Render redacted coverage and trend metrics without writes. |
| v3.1 Operations Intelligence | `operations_intelligence/run.py` | Render observations without changing operations. |
| v3.1 Developer Experience | `developer_experience/run.py` | Render DX guidance without files or configuration changes. |
| v3.1 Workflow Efficiency | `workflow_efficiency/run.py` | Render one-Page efficiency evidence without dispatch. |
| v3.3 Production Pipeline | `production_pipeline/run.py` | Render one-page pipeline evidence without execution or publishing. |
| v3.3 Quality Intelligence | `quality_intelligence/run.py` | Render diagnostic quality evidence without scoring or approval. |
| v3.3 Asset Lifecycle | `asset_lifecycle/run.py` | Render Repository-port lifecycle evidence without archive or delete. |
| v3.3 Project Intelligence | `project_intelligence/run.py` | Render advisory project evidence without scheduling or allocation. |
| v3.3 Project Health | `project_health/run.py` | Render project health evidence without Project mutation. |
| v3.3 Production Intelligence | `production_intelligence/run.py` | Render pipeline analysis without execution or optimization. |
| v3.3 Quality Analytics | `quality_analytics/run.py` | Render review evidence without scoring or approval. |
| v3.3 Asset Intelligence | `asset_intelligence/v3_3_insights.py` | Render redacted asset analytics without mutation. |
| v3.3 Project Operations | `project_operations/run.py` | Render project operations evidence without scheduling or allocation. |
| v3.3 Pipeline Efficiency | `pipeline_efficiency/run.py` | Render diagnostic efficiency evidence without workflow changes. |
| v3.3 Production Governance | `production_governance/run.py` | Render policy and audit evidence without enforcement or execution. |
| v3.3 Quality Governance | `quality_governance/run.py` | Render quality policy evidence without scoring or approval. |
| v3.3 Asset Governance | `asset_governance/v3_3_governance.py` | Render redacted asset controls without retention or mutation. |
| v3.3 Project Governance | `project_governance/run.py` | Render project controls without scheduling or allocation. |
| v3.3 Governance Dashboard | `governance_dashboard/run.py` | Render a shared dashboard DTO without policy application. |
| v3.4 Knowledge Platform | `knowledge_platform/run.py` | Render Repository-derived knowledge evidence without writes or remote search. |
| v3.4 Production Operations | `production_operations/run.py` | Render bounded operations evidence without monitoring, remediation, or deployment. |
| v3.4 Organization Intelligence | `organization_intelligence/run.py` | Render redacted organization evidence without personnel action. |
| v3.4 Release Intelligence | `release_intelligence/run.py` | Render release evidence without tagging, publication, or deployment. |
| v3.4 Release Health | `release_health/run.py` | Render local release health without validation or authorization. |
| v3.4 Release Dashboard | `release_dashboard/README.md` | Plan human-review release aggregation without authorization. |
| v3.4 Knowledge Intelligence | `knowledge_intelligence/run.py` | Render Repository-derived knowledge observations without writes or remote search. |
| v3.4 Production Optimization | `production_optimization/run.py` | Render capacity and bottleneck guidance without workflow changes. |
| v3.4 Organization Analytics | `organization_analytics/run.py` | Render bounded organization observations without personnel action. |
| v3.4 Release Analytics | `release_analytics/run.py` | Render release evidence without deployment or publication. |
| v3.4 Capacity Optimization | `capacity_optimization/run.py` | Render recommendations without allocating capacity or resources. |
| v3.4 Knowledge Governance | `knowledge_governance/run.py` | Render read-only Knowledge policy and audit evidence without retention. |
| v3.4 Production Governance | `production_governance/v3_4_governance.py` | Render StateMachine governance evidence without pipeline changes. |
| v3.4 Organization Governance | `organization_governance/run.py` | Render organization policy and audit evidence without personnel action. |
| v3.4 Release Governance | `release_governance/run.py` | Render release policy and audit evidence without authorization or publication. |
| v3.4 Governance Dashboard | `governance_dashboard/v3_4_governance.py` | Render four shared governance DTOs without enforcing policy. |
| v3.5 Unified Knowledge Graph | `v3_5/knowledge_graph/README.md` | Design a read-only graph projection with no persistence or remote lookup. |
| v3.5 Creative Intelligence | `v3_5/creative_intelligence/README.md` | Plan human-review creative evidence without generation or approval. |
| v3.5 Production Intelligence | `v3_5/production_intelligence/README.md` | Plan local production analysis without scheduling or deployment. |
| v3.5 Platform Analytics | `v3_5/platform_analytics/README.md` | Plan deterministic cross-platform reports without collection or action. |
| v3.5 Executive Dashboard | `v3_5/executive_dashboard/README.md` | Plan a DTO-only dashboard without UI ownership or authority. |
| v3.1 Creative Governance | `creative_governance/run_v31.py` | Render governance evidence without remediation or approval. |
| v3.1 Knowledge Reliability | `knowledge_reliability/run.py` | Render redacted reliability evidence without repair. |
| v3.1 Operational Readiness | `operational_readiness/run.py` | Render readiness evidence without deployment. |
| v3.1 Release Quality | `release_quality/run.py` | Render human-only release evidence without publication. |
| v3.1 Compatibility Validation | `compatibility_validation/run.py` | Render stable surface evidence without API changes. |
| Plugin | `plugins/` | Local manifest-based Agent, Image, Prompt, and Repository samples. |
| Batch | CLI and `workflow.py` documentation | Sequential batch remains a workflow feature, not a separate sample runtime. |
| Extension SDK | Documentation only | The SDK needs the existing validation/packaging debt item completed before a canonical sample is published. |
| Notification | Documentation only | Mock and Console providers are covered by tests; no external delivery example is shipped. |
| API / Enterprise / Automation | Not shipped | FastAPI and Automation runtimes are absent from this source baseline. |

Run examples from a development checkout with `PYTHONPATH=src`, or after
installing the package. Do not use examples to bypass `WorkflowEngine` or
StateMachine validation.
