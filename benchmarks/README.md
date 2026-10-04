# Benchmarks

Run the deterministic smoke harness with `PYTHONPATH=src python -m benchmarks.smoke`.
It exercises one provider-free operation for Workflow, in-memory and SQLite
repositories, Prompt-adjacent LLM/Image adapters, Notification, Batch
planning, and the v6 Platform Kernel. It intentionally has no performance
budget: elapsed time varies by machine and it is a regression signal, not a
benchmark laboratory.

## v6.x LTS Platform Kernel

The shared smoke harness runs one provider-free `platform_kernel` projection
through `v6_0_platform_rc1`. It is read-only and one-Page scoped: it does not
execute a Workflow, transition the StateMachine, persist data, call a Provider,
contact an external service, or automate approval. The standalone scenario
retains its 500-projection local-baseline default.

For a repeatable comparison, record the Python version, OS, CPU, database URL,
command, iteration count, and median/p95 results. Do not benchmark networked
providers with this harness. Automation is not included because no Automation
runtime exists in the current source baseline.

The v2.3 measurement backlog and Issue evidence requirements are defined in
[Performance Guide](../docs/PERFORMANCE_GUIDE.md),
[v2.3 Quality Gates](../docs/QUALITY_GATES.md), and the
[v2.3 benchmark backlog](v2_3_backlog.md) and the
[v2.4 benchmark backlog](v2_4_backlog.md).

## v3.3 Iteration 1 scenarios

- `production_pipeline`: stage, transition, approval, timeline, and summary
  projection without execution or publishing.
- `quality_intelligence`: metric, rule, finding, dashboard, and summary
  projection without score or approval authority.
- `asset_lifecycle`: Repository-port lifecycle, history, archive-policy, and
  dependency projection without archive/delete.
- `project_intelligence` and `project_health`: bounded Project diagnostics
  without scheduling, allocation, or Project mutation.

## v3.4 planned scenarios

`knowledge_platform`, `operations_dashboard`, `organization_health`,
`release_health`, and `deployment_analytics` are design-only, provider-free
benchmark specifications. They require deterministic local fixtures and must
not perform Repository writes, personnel action, monitoring/remediation,
deployment, tagging, signing, publication, or workflow execution. See the
[v3.4 benchmark plan](../docs/V3_4_BENCHMARK_PLAN.md).

## v3.5 planned scenarios

`knowledge_graph`, `creative_metrics`, `production_metrics`, `platform_health`,
and `analytics_dashboard` are design-only, provider-free benchmark
specifications. They require deterministic local fixtures and must not write a
Repository, generate content, schedule work, deploy, publish, collect remotely,
or execute a workflow. See the [v3.5 benchmark plan](../docs/V3_5_BENCHMARK_PLAN.md).

## v3.4 Iteration 1 scenarios

- `knowledge_platform`: catalog, relationship, classification, quality, and
  index projection through the existing Repository port only.
- `production_operations`: dashboard, status, capacity, timeline, and summary
  projection without monitoring, scheduling, or deployment.
- `organization_intelligence`: team, role, workload, collaboration, risk, and
  executive projection without personnel action.
- `release_intelligence` and `release_health`: release evidence and version
  projection without validation, tagging, signing, publishing, or deployment.

These scripts are provider-free, one-Page scoped, read-only regression signals,
not hardware-dependent production service-level objectives.

## v2.5 planned scenarios

`provider_selection`, `backend_selection`, `production_workflow`,
`large_repository`, `diagnostics_pipeline`, and `quality_pipeline` are planning
specifications in [the v2.5 backlog](v2_5_backlog.md). Existing provider
selection and repository scenarios may be reused only after the relevant Issue
records an environment, mock/local fixture, baseline, budget, and rollback
criterion. They do not authorize networked Provider calls or image generation.

## v2.5 Iteration 1 quality scenarios

- `repository_validation`: in-memory statistics, integrity, cleanup-candidate,
  and large-repository maintenance DTO composition.
- `quality_pipeline`: Repository, Workflow, Configuration, API,
  documentation, and release-artifact validation over a one-page fixture.
- `documentation_validation`: required release assets and local Markdown links.
- `api_compatibility`: root-export and version-source compatibility only.
- `development_workspace`: static workspace, declared-dependency, and build
  metadata diagnostics.

These scripts are provider-free, read-only, and regression signals rather than
hardware-dependent service-level objectives.

## v2.4 planned scenarios

`provider_selection`, `provider_failover`, `workflow_production`,
`repository_large_project`, and `diagnostics_large_project` are planning
specifications. They are not runnable benchmarks until their Issue evidence is
accepted.

## v2.2 Iteration 1 scenarios

- `large_project`: construct a several-hundred-page aggregate fixture.
- `repository_index`: exercise local metadata index, page, and history reads.
- `database_query`: exercise indexed SQLite metadata and page reads.
- `batch_resume`: exercise sequential checkpoint, resume, and retry behavior.
- `workflow_scale`: execute many independent one-page mock transitions.

`baselines/v2_1.json` contains conservative local smoke references. The
regression test permits normal machine variation but fails on a material
slowdown. It is not a throughput service-level objective.

## v2.2 Iteration 2 runtime scenarios

- `plugin_loading`: cache-aware manifest discovery, dependency ordering, and lifecycle setup.
- `extension_loading`: repeated SDK compatibility and entry-point validation.
- `event_dispatch`: subscription lookup and synchronous in-memory delivery.
- `configuration_load`: cached validated configuration reads.
- `diagnostics`: passive runtime diagnostic composition.

`baselines/v2_2_iteration_1_runtime.json` preserves a conservative local
reference for the Runtime boundaries. The normal pytest suite executes the
provider-free regression smoke test.

## v2.2 Iteration 3 repeatability scenarios

- `workflow_repeatability`, `repository_repeatability`, and
  `database_repeatability` measure repeated Core/Repository paths.
- `notification_repeatability` and `plugin_repeatability` measure deterministic
  optional-boundary behavior.

The stability test checks relative timing spread across repeated provider-free
runs. It detects pathological variance without creating a hardware-dependent
throughput SLO.

## v2.3 planned scenarios

`provider_latency`, `image_backend_latency`, `repository_large_scale`, and
`workflow_large_scale` are planning specifications. They become runnable only
with an accepted Issue, deterministic mock fixture, retained baseline, and no
network credentials in CI.

## v2.3 Iteration 1 runtime scenarios

- `provider_discovery`: registered LLM metadata and capability lookup.
- `provider_selection`: alias selection without LLM execution.
- `backend_discovery`: image backend metadata, capability, and preset lookup.
- `configuration_profile`: cached profile resolution and validation.
- `provider_health`: local adapter-construction checks with no network probe.

## v2.3 Iteration 2 enterprise runtime scenarios

- `repository_large_history`: bounded retrieval across a high-history page.
- `provider_lifecycle` and `backend_lifecycle`: local lifecycle transitions only.
- `configuration_validation`: schema, integrity, migration, and fingerprint checks.
- `diagnostics_summary`: transport-neutral enterprise diagnostics composition.

## v2.3 Iteration 3 repeatability scenarios

- `workflow_repeatability` and `repository_repeatability`: existing Core and
  Repository stability checks.
- `provider_repeatability` and `backend_repeatability`: local adapter lifecycle
  checks without network calls or generation.
- `configuration_repeatability`: schema governance and fingerprint stability.

## v2.4 Iteration 1 production-runtime scenarios

- `startup_time`: application-layer validation and metadata-only adapter warmup.
- `provider_warmup`: local Provider lifecycle warmup without LLM invocation.
- `configuration_reload`: deterministic in-memory governance validation.
- `health_check`: transport-neutral production health composition.
- `runtime_metrics`: bounded in-process category aggregation.

They are provider-free smoke measurements, not service-level objectives. Run
them with `PYTHONPATH=src python -m benchmarks.<scenario>` and record local
hardware evidence only when comparing changes.

## v2.4 Iteration 2 operations scenarios

- `configuration_snapshot`: redacted snapshot, governance, and fingerprint composition.
- `provider_inventory`: local Provider metadata, capability, health, and recommendation evidence.
- `backend_inventory`: Image Backend metadata, preset, and workflow-compatibility evidence.
- `health_history`: bounded Project-metadata history persistence through the Repository port.
- `runtime_diagnostics`: composite operations DTO construction.

All five use mock/local boundaries only and do not invoke Provider generation,
Image generation, workflow execution, or network probes.

## v2.4 Iteration 3 reliability scenarios

- `workflow_resume`: read-only resume admission and consistency validation.
- `repository_integrity`: aggregate integrity self-check through the Repository port.
- `long_running_runtime`: bounded task and batch stability capture.
- `memory_growth`: optional host-enabled tracemalloc snapshot capture.
- `diagnostics_generation`: architecture and operational diagnostic DTO composition.
- `recovery_validation`: non-executing recovery simulation.

All scenarios are provider-free and never run a workflow step, call an Agent,
write a recovery action, or make network requests.

## v2.5 Iteration 3 release and OSS readiness scenarios

- `release_validation`: composite release checklist generation over a one-page fixture.
- `artifact_verification`: static typed-package and release-asset verification.
- `repository_health`: non-destructive repository health evidence through the existing port.
- `dependency_analysis`: declared dependency lifecycle and policy evidence.
- `long_running_validation`: passive bounded-stability contract validation.

These scenarios do not build, publish, delete, repair, or contact GitHub. They
exercise only local DTO composition and are suitable for mock-only CI smoke runs.

## v2.6 Iteration 1 planning scenarios

- `workflow_planner`: StateMachine-derived one-page plan construction.
- `provider_selection` and `capability_scoring`: deterministic registered
  metadata selection; no Provider is created or invoked.
- `execution_preview`: a non-executing one-page plan preview.
- `planning_report`: JSON/Markdown diagnostic rendering.

These scenarios use only local mock metadata. They do not authorize Provider
invocation, task scheduling, image generation, approval, persistence, or
workflow-state changes. `provider_fallback`, cross-page workflow diagnostics,
and operations planning remain specifications in [the v2.6 backlog](v2_6_backlog.md).

## v2.6 Iteration 2 analytics scenarios

- `workflow_analysis` and `critical_path`: one-page dependency and critical-path
  analysis derived from the existing StateMachine plan.
- `provider_comparison`: capability, local construction health, relative latency,
  and unknown-cost comparison without a model request.
- `enterprise_diagnostics`: injected local configuration, workflow, Provider,
  Backend, and Repository audit DTO composition.
- `operational_analytics`: bounded trend and executive-input preparation with no
  collector, persistence loop, scheduler, or automatic action.

## v2.6 Iteration 3 assurance scenarios

- `workflow_validation` and `workflow_integrity`: one-page non-executing
  validation and integrity analysis.
- `provider_governance`: local policy, capability, lifecycle, compatibility,
  and risk DTO composition with no model request.
- `enterprise_readiness`: deployment and operations checklist composition with
  no deployment, repair, recovery, or workflow resume.
- `workflow_health`: health and diagnostics DTO construction with no Agent or
  Provider call.

## v2.7 Iteration 3 Director reliability scenarios

- `director_reliability` and `planning_validation`: one-page Director
  integrity, public trace, and readiness evidence without dispatching work.
- `knowledge_governance`: redacted Repository-port policy, integrity,
  lifecycle, quality, and risk evidence.
- `enterprise_ai_readiness`: checklist-only AI deployment readiness with no
  deploy, resume, configuration, or workflow operation.
- `ai_workflow_diagnostics`: Director, Knowledge, planning, workflow, and
  architecture diagnostics rendered from safe DTOs.

## v3 planned scenarios

The v3 design scenarios are specified in [V3 Benchmark Plan](../docs/V3_BENCHMARK_PLAN.md).
They remain provider-free, advisory, and one-page scoped:

- `planning_pipeline` and `director_planning`: legal-step and decision-trace
  DTO composition without Agent or Provider invocation.
- `knowledge_lookup`: bounded, redacted Repository-port projections and graph
  lookup with no mandatory new store.
- `creative_pipeline`: creative hand-off/checkpoint plan construction without
  image generation or StateMachine transition.
- `multi_agent_simulation`: capability and conflict-policy graph evaluation
  without direct agent calls or task dispatch.

## v3 Iteration 1 foundation scenarios

- `director_platform`: Director goals, session, and legal-step summary DTOs.
- `creative_planning`: Story through Panel planning composition without image generation.
- `knowledge_foundation`: repository-derived, metadata-value-redacted index construction.
- `workflow_intelligence`: dependency/progress/timeline/recommendation DTO composition.
- `planning_summary`: compact one-page planning summary construction.

All v3 foundation scenarios are provider-free, repository-read-only, and
non-executing. They establish a diagnostic baseline only.

## v3.3 Iteration 2 intelligence scenarios

- `production_intelligence` and `pipeline_efficiency`: current one-Page
  StateMachine/pipeline evidence projection without execution or optimization.
- `quality_analytics`: quality trend, regression, coverage, and consistency
  DTO composition without scoring, remediation, or approval.
- `asset_intelligence_v33`: redacted Repository-derived asset usage,
  dependency, consistency, recommendation, and health DTO composition.
- `project_operations`: milestone, resource shape, forecast assumptions, and
  risk DTO composition without allocation, scheduling, or delivery commitment.

## v3.3 Iteration 3 governance scenarios

- `production_governance`: production policy, pipeline, audit, compliance, and
  summary DTO composition without policy enforcement or workflow execution.
- `quality_governance`: quality policy, compliance, and audit DTO composition
  without scoring, remediation, or approval.
- `asset_governance_v33`: redacted Repository-derived control, audit, and
  retention-policy DTO composition without retention or writes.
- `project_governance` and `governance_dashboard`: Project control, risk, and
  dashboard DTO composition without allocation, scheduling, mitigation, or
  delivery commitment.

## v3.4 Iteration 2 intelligence scenarios

- `knowledge_intelligence`: Repository-derived catalog, relationship, quality,
  coverage, and recommendation DTO composition without writes or remote search.
- `production_optimization` and `capacity_optimization`: one-Page efficiency,
  capacity, allocation-boundary, and bottleneck projection without workflow
  changes, allocation, scheduling, or remediation.
- `organization_analytics`: redacted local organization observations without
  people scoring, personnel action, notification, or delivery commitment.
- `release_analytics`: local release trend and compatibility evidence without
  remote analytics, deployment, remediation, authorization, tagging, or publication.

## v3.4 Iteration 3 governance scenarios

- `knowledge_governance`: Repository-derived policy, compliance, audit, and
  retention-boundary DTO composition without enforcement, retention, or writes.
- `production_governance_v34`: StateMachine and human-approval governance
  evidence without a pipeline change, execution, approval, allocation, or deployment.
- `organization_governance`: policy and audit observations without personnel
  scoring, assignment, role change, notification, or delivery commitment.
- `release_governance`: release policy and local audit evidence without hosted
  collection, authorization, tagging, signing, publication, or deployment.
- `governance_dashboard_v34`: four shared governance-dashboard DTOs without
  transport-specific mutation or policy enforcement.

## v3 Iteration 2 collaboration scenarios

- `multi_agent_foundation`: role/capability/assignment plan composition without Agent dispatch.
- `creative_knowledge`: repository-derived Creative Knowledge topic composition without writes.
- `director_intelligence`: decision, alternatives, risk, and recommendation composition without workflow mutation.
- `review_pipeline`: diagnostic review aggregation without quality pass or approval.
- `knowledge_relationship`: bounded identifier/tag relationship graph construction without semantic retrieval.

## v3 Iteration 3 readiness scenarios

- `director_reliability`: session/integrity/consistency/readiness validation without workflow execution.
- `creative_governance`: policy/standard/compliance/audit DTO composition without mutation.
- `knowledge_integrity`: redacted integrity/coverage/lifecycle/quality/risk DTO composition.
- `production_readiness`: deployment checklist composition without deployment or operation start.
- `release_readiness`: executive readiness dashboard composition without release authorization.

## v3.1 foundation scenarios

The v3.1 scenarios in [V3.1 Benchmark Plan](../docs/V3_1_BENCHMARK_PLAN.md)
are provider-free DTO microbenchmarks. They preserve the one-Page,
non-executing contract:

- `creative_collaboration`: human workspace, hand-off, and review-plan DTOs.
- `knowledge_evolution`: redacted Knowledge version/diff/snapshot/timeline DTOs.
- `operations_foundation`: local operations, quality, release, and health DTOs.
- `developer_productivity`: template-descriptor DTO composition.
- `project_metrics`: bounded one-Page aggregate metric projection.

## v3.1 Iteration 2 insight scenarios

- `creative_review`: checklist/finding/recommendation DTO construction without review execution.
- `knowledge_analytics`: redacted Repository-port coverage, usage, relationship, and baseline trend DTOs.
- `operations_intelligence`: one-Page operations observations without runtime changes.
- `developer_experience`: workspace/template/configuration-shape diagnostics without writes.
- `workflow_efficiency`: one-Page history/artifact observation without dispatch.

## v3.1 Iteration 3 assurance scenarios

- `creative_governance_v31`: policy, validation, compliance, and quality-score DTOs without remediation.
- `knowledge_reliability`: redacted integrity, consistency, dependency, and lifecycle DTOs without repair.
- `operational_readiness`: readiness DTO composition without deployment or probing.
- `release_quality`: quality, gate, regression, production, and recommendation DTOs without publication.
- `compatibility_validation`: stable public-surface projection without API changes.
