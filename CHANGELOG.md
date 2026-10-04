# Changelog

All notable changes to this project are documented in this file.

## Unreleased

- Added the verified POST-v6.1 I01–I06 read-only project-status readiness
  projections: per-page inspection, summary, outcome, and focus-page evidence.
  These are additive pre-release readiness changes; `6.0.0` remains the stable
  release and no new version, workflow execution, approval, or release action
  is implied.
- Added opt-in, bounded v6.1 Knowledge Graph traversal snapshots for
  caller-supplied v6.0 graph reports. They are deterministic, read-only, and
  advisory; no repository query, persistence, workflow execution, or graph
  mutation was introduced.
- Added an opt-in, read-only v6.1 Knowledge Graph node metadata descriptor
  report. Caller-supplied confidence, retention, redaction, and human-review
  references are diagnosed without changing v6.0 graph provenance, executing
  a review, or persisting, querying, or correcting knowledge.
- Added opt-in, read-only v6.1 pagination reports for caller-supplied Project
  and Workspace references. They reuse v6.0 Hub ordering and duplicate
  validation without querying repositories, executing workflows, or changing
  existing Hub behavior.
- Added `ProjectManagerService`, a repository-port-only and read-only Project
  status inspection for Production Core. It neither executes workflows nor
  persists, approves, or transitions a Page.
- Established the v6.x LTS maintenance baseline, compatibility matrices,
  Marketplace certification standard, security maintenance record, platform
  health report, and technical-debt registry. No product behavior changed.
- Added OSS maturity guidance for contributors, governance, community conduct,
  support, RFCs, security response, roadmap stewardship, and deprecation.
  These documents preserve the v6.x LTS platform scope and public contracts.
- Added the v6.x official LTS charter, including security, compatibility,
  backport, and end-of-life policies. No API or runtime behavior changed.

## 6.0.0 - 2026-08-09

- Added additive, read-only v6.0 Creative Production Platform Foundation
  reports for Production Core, Workspace Hub, Project Hub, Knowledge Core, AI
  Orchestrator, Collaboration Core, and Service Registry. Existing v5.x
  workflow, repository, plugin, CLI, FastAPI, MCP, Web UI, and SDK contracts
  remain unchanged.
- Added additive, read-only v6.0 Iteration 2 reports for Knowledge Graph,
  Context Engine, Workflow Orchestrator, Automation Hub, Collaboration
  Workspace, Production Analytics, and Service Discovery. These reports do
  not persist data, dispatch automation, register services, approve Pages, or
  change workflow state; all v5.x public surfaces remain unchanged.
- Added additive, read-only v6.0 Iteration 3 Platform Kernel, Unified Context,
  Extension Framework, SDK Foundation, Marketplace Framework, Policy Engine,
  Governance Framework, and Observability Platform reports. No runtime is
  started, extension is loaded, listing is published, policy is enforced,
  telemetry is emitted, or workflow is mutated.
- Promoted the RC1-reviewed Platform Kernel, SDK, Extension Framework,
  Marketplace specification, Governance, and Observability reports to the
  stable v6.0 release without changing any runtime, public API, workflow,
  repository, or plugin lifecycle behavior.

## 5.7.0 - 2026-08-09

- Freeze Platform API v1, Plugin API v1, and Workspace Standard v1 as
  additive, read-only v5.x maintenance surfaces.
- Stabilized the provider lifecycle repeatability probe with a longer local
  measurement batch; no runtime behavior changes.
- Added v5.7 read-only Production Platform v1 orchestration, Automation
  Pipeline, Plugin Lifecycle, Event Bus, Task Scheduler, Snapshot, and
  Analytics diagnostics. Existing execution, approval, publishing, scheduling,
  event delivery, and Plugin lifecycle behavior remains unchanged.
- Added read-only v5.7 Production Workspace v2 diagnostics for Asset Registry,
  Project Workspace, Workflow State, Resource capacity, Template compatibility,
  and Production Session recovery eligibility. No allocation, persistence,
  resume, workflow execution, or lifecycle behavior was introduced.
- Added additive, read-only v5.7 Production Platform Foundation reports for
  Workspace, Project, Asset lifecycle evidence, Automation references, and
  Plugin Registry runtime inventory. Existing v5.x workflow, repository,
  plugin lifecycle, CLI, FastAPI, MCP, Web UI, and SDK contracts are unchanged.

## 5.6.0 - 2026-08-09

- Promoted Manga Production OS v5.6 from RC1 to the stable maintenance
  baseline without adding workflow, generation, approval, or publication
  behavior.
- Established post-release audit, regression baseline, stability, quality-trend,
  maintenance-plan, and technical-debt records for the v5.6 maintenance line.
- Preserved all existing Python API, CLI, FastAPI/REST, MCP, Web UI,
  Repository, SDK, and StateMachine contracts.

## 5.6.0rc1 - 2026-08-09

- Prepared Manga Production OS v5.6 RC1 with additive, read-only Story,
  Character, Page, Review, and Export Engine reports for exactly one page.
- Added integration evidence for a storyboarded, quality-reviewed, explicitly
  approved page across the production pipeline and every v5.6 Engine.
- Preserved existing Python API, CLI, FastAPI/REST, MCP, Web UI, Repository,
  SDK, and StateMachine behavior. No generation, approval, publication, or
  workflow transition is automated by the new reports.

## 5.4.0 - 2026-08-03

- Promoted the RC1-reviewed Creative Quality Framework to stable `5.4.0` without
  adding policy enforcement, CI/CD control, automatic review, approval, recovery,
  publication, or workflow mutation.
- Preserved v5.0 LTS/v5.3 public contracts and StateMachine workflow authority.
- Completed local Foundation, Intelligence, Governance, Audit, Reliability, and
  Release Lifecycle release evidence.

## 5.4.0rc1 - 2026-08-03

- Prepared the Creative Quality Framework RC1 with local Quality Engine, Review
  Pipeline, Validation, Metrics, Intelligence, Governance, Audit, Reliability,
  and Release Lifecycle diagnostics.
- Preserved v5.0 LTS/v5.3 public contracts and StateMachine workflow authority.
- Added no automatic review, validation execution, CI/CD control, approval,
  recovery, publication, or workflow mutation.

## 5.3.0 - 2026-08-03

- Promoted the RC1-reviewed Creative Integration Framework to stable `5.3.0` without adding external connectivity or automation execution.
- Preserved v5.0 LTS/v5.2 public contracts across Python API, CLI, FastAPI, MCP, Web UI, Repository, Workflow, SDK, Provider, and Backend.

## 5.3.0rc1 - 2026-08-03

- Prepared the optional Creative Integration Framework for RC review with local Gateway, Connector, Exchange, Event, Registry, Intelligence, Governance, Security, Observability, Reliability, Lifecycle, and SDK diagnostics.
- Preserved v5.0 LTS/v5.2 public contracts; no external connection, synchronization, execution, or workflow mutation is introduced.

## 5.2.0 - 2026-08-03

### Release

- Promoted the RC1-reviewed Creative Automation Framework to stable `5.2.0`
  without adding automation execution or operational-control behaviour.
- Updated canonical Python, frontend, OpenAPI, MCP, SBOM, package,
  documentation, and release metadata to `5.2.0`.
- Completed Automation Engine, Rule Engine, Event Bus, Workflow Templates,
  Automation Registry, Intelligence, Governance, Observability, Reliability,
  Lifecycle, and optional Unified SDK Automation reports.

### Compatibility

- v5.0 LTS and v5.1 Python API, CLI, FastAPI, REST API, MCP, Repository,
  Workflow, Extension SDK, Provider, Backend, and Web UI contracts remain
  compatible. No migration is required.

### Quality

- Final regression, compatibility, Automation Framework end-to-end, benchmark,
  package, documentation, static-security, and local CI-equivalent validation
  completed. External dependency scanning and hosted publication controls remain
  maintainer gates.

## 5.2.0rc1 - 2026-08-03

### Release candidate

- Prepared the optional, human-gated Creative Automation Framework for RC
  review: Automation Engine, Rule Engine, Event Bus, Workflow Templates,
  Automation Registry, Intelligence, Governance, Observability, Reliability,
  Lifecycle, and SDK reports.
- Synchronized canonical package, frontend, OpenAPI, MCP, SBOM, documentation,
  and release metadata to `5.2.0rc1` (`5.2.0-rc.1` for the frontend).

### Compatibility

- v5.0 LTS and v5.1 Python API, CLI, FastAPI, REST API, MCP, Repository,
  Workflow, Extension SDK, Provider, Backend, and Web UI contracts remain
  compatible. No migration is required.

### Validation

- Completed local architecture, compatibility, Automation Framework end-to-end,
  benchmark, static-security, package, documentation, and CI-equivalent review.
  External scanning and publication controls remain maintainer gates.

## 5.1.0 - 2026-08-03

### Release

- Promoted the RC1-reviewed Composable Creative Platform to stable `5.1.0`
  without adding execution or operational-control behavior.
- Updated canonical Python, frontend, OpenAPI, MCP, SBOM, package,
  documentation, and release metadata to `5.1.0`.
- Completed Capability Registry, Feature Packs, Platform Profiles, Solution
  Templates, Composition Engine, Governance, Observability, Lifecycle,
  Reliability, and optional Unified SDK composition previews.

### Compatibility

- v5.0 LTS Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow,
  Plugin, Extension SDK, Provider, Backend, and Web UI contracts remain
  compatible. No migration is required.

### Quality

- Final regression, compatibility, Composition Platform end-to-end, benchmark,
  package, documentation, static-security, and local CI-equivalent validation
  completed. External dependency scanning and hosted publication controls remain
  maintainer gates.

## 5.1.0rc1 - 2026-08-03

### Release candidate

- Prepared the Composable Creative Platform for RC review with Capability
  Registry, Feature Packs, Platform Profiles, Solution Templates, Composition
  Engine, Governance, Observability, Lifecycle, Reliability, and SDK previews.
- Synchronized canonical Python, OpenAPI, MCP, SBOM, package, frontend, and
  release metadata to `5.1.0rc1` (`5.1.0-rc.1` for the frontend).

### Compatibility

- Preserved v5.0 LTS Python API, CLI, FastAPI, REST API, MCP, Repository,
  Workflow, Plugin, Extension SDK, Provider, Backend, and Web UI contracts.
- Composition remains optional, local, declarative, read-only, and
  human-governed; no migration is required.

### Validation

- Added RC architecture, compatibility, Composition Platform end-to-end,
  benchmark, security, package, documentation, and local CI-equivalent
  validation evidence. External dependency scanning and hosted publication
  controls remain maintainer gates.

## 5.0.0 - 2026-08-03

### Release

- Promoted the RC1-reviewed One Creative Platform to stable `5.0.0` without
  adding functionality or changing the v5 public surface.
- Updated canonical Python, frontend, OpenAPI, MCP, SBOM, package,
  documentation, and release metadata to `5.0.0`.
- Completed Unified Platform, Context, API Surface, Runtime, SDK, Governance,
  Observability, Reliability, Lifecycle, Developer Experience, and Maturity
  diagnostics as an additive v5 consolidation layer.

### Compatibility

- v4.8 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow, Plugin,
  Extension SDK, Provider, Backend, and Web UI contracts remain backward
  compatible. No migration is required.

### Quality

- Final regression, compatibility, architecture, One Creative Platform
  end-to-end, benchmark, package, documentation, static-security, and local
  CI-equivalent validation completed. External dependency scanning and hosted
  publication controls remain maintainer gates.

## 5.0.0rc1 - 2026-08-03

### Release candidate

- Prepared One Creative Platform for RC review without adding an execution,
  routing, persistence, monitoring, or policy-enforcement capability.
- Synchronized canonical Python, OpenAPI, MCP, SBOM, package, frontend, and
  release metadata to `5.0.0rc1` (`5.0.0-rc.1` for the frontend).

### Compatibility

- Retained v4.8 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow,
  Plugin, Extension SDK, Provider, Backend, and Web UI contracts. Unified
  Context, API Surface, Runtime, SDK, Governance, Observability, Reliability,
  Lifecycle, and DX capabilities remain additive, diagnostic, and opt-in.

### Validation

- Added RC architecture, compatibility, Unified Platform end-to-end,
  benchmark, security, package, documentation, and local CI-equivalent
  validation evidence.

## 4.8.0 - 2026-08-02

### Release

- Promoted the RC1-reviewed Creative Operating System to stable `4.8.0`
  without adding functionality or changing the v4.8 public surface.
- Updated canonical Python, frontend, OpenAPI, MCP, SBOM, package,
  documentation, and release metadata to `4.8.0`.
- Marked v4 as complete with Unified Platform, Modular Runtime, Unified API
  Surface, Operational Intelligence, Lifecycle Management, Governance, and
  Reliability delivered as compatible, diagnostic platform capabilities.

### Compatibility

- v4.7 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow, Agent,
  Plugin, Provider, Backend, Web UI, and Extension SDK contracts remain
  additive-only and backward compatible. No migration is required.

### Quality

- Final regression, compatibility, architecture, Creative Operating System
  end-to-end, benchmark, security, package, documentation, and local
  CI-equivalent validation completed.

## 4.8.0rc1 - 2026-08-02

### Release candidate

- Prepared the Creative Operating System for RC review without adding a runtime
  execution capability. Unified Platform, Modular Runtime, Service Registry,
  Lifecycle, Operations, Governance, Observability, and Reliability remain
  immutable, diagnostic, and human-operated projections.
- Synchronized Python, OpenAPI, MCP, SBOM, and release metadata on canonical
  prerelease version `4.8.0rc1` (`4.8.0-rc.1` for the frontend).

### Compatibility

- Retained v4.7 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow,
  Agent, Plugin, Extension SDK, Provider, Backend, and Web UI contracts. No
  public interface, persistence format, or StateMachine transition changed.

### Validation

- Added RC architecture, compatibility, Creative Operating System end-to-end,
  benchmark, security, package, documentation, and local CI-equivalent quality
  evidence.

## 4.7.0 - 2026-08-02

### Release

- Promoted the RC1-reviewed Creative Decision Platform to stable `4.7.0`
  without adding functionality or changing the v4.7 public surface.
- Updated canonical Python, frontend, OpenAPI, MCP, SBOM, package,
  documentation, and release metadata to `4.7.0`.

### Compatibility

- v4.6 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow, Agent,
  Plugin, Provider, Backend, Web UI, and Extension SDK contracts remain
  additive-only and backward compatible. No migration is required.

### Quality

- Final regression, compatibility, architecture, Decision Platform end-to-end,
  benchmark, security, package, documentation, and local CI-equivalent
  validation completed.

## 4.7.0rc1 - 2026-08-02

### Release candidate

- Prepared the Creative Decision Platform for RC review without adding a runtime
  capability. Decision, Recommendation, Review, Approval, Dashboard,
  Governance, Audit, Compliance, and Reliability remain immutable, advisory,
  and human-operated projections.
- Synchronized Python, OpenAPI, MCP, frontend, SBOM, and release metadata on
  canonical prerelease version `4.7.0rc1` (`4.7.0-rc.1` for the frontend).

### Compatibility

- Retained v4.6 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow,
  Agent, Plugin, Extension SDK, Provider, Backend, and Web UI contracts. No
  public interface or StateMachine transition changed.

### Validation

- Added RC architecture, compatibility, Decision Platform end-to-end,
  performance, security, package, documentation, and local CI-equivalent
  quality evidence.

## 4.6.0 - 2026-08-02

### Release

- Promoted the RC1-reviewed Creative Intelligence OS to stable `4.6.0` without
  adding functionality or changing the v4.6 public surface.
- Updated canonical Python, frontend, OpenAPI, MCP, SBOM, dependency-license,
  package, documentation, and release metadata to `4.6.0`.

### Compatibility

- v4.5 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow, Agent,
  Plugin, Provider, Backend, Web UI, and Extension SDK contracts remain
  additive-only and backward compatible. No migration is required.

### Quality

- Final regression, compatibility, architecture, Creative Intelligence
  end-to-end, benchmark, security, package, documentation, and local
  CI-equivalent validation completed.

## 4.6.0rc1 - 2026-08-02

### Release candidate

- Prepared the Creative Intelligence OS for RC review without adding a runtime
  capability. Unified Creative Context, Cross-Agent Memory, Creative Reasoning,
  Adaptive Workflow, Intelligence Hub, Governance, Observability, and
  Reliability remain immutable, advisory, and human-operated projections.
- Synchronized Python, OpenAPI, MCP, frontend, SBOM, dependency-license, and
  release metadata on canonical prerelease version `4.6.0rc1` (`4.6.0-rc.1`
  for the frontend package).

### Compatibility

- Retained v4.5 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow,
  Agent, Plugin, Extension SDK, Provider, Backend, and Web UI contracts. No
  public interface or StateMachine transition changed.

### Validation

- Added RC architecture, compatibility, Creative Intelligence end-to-end,
  performance, security, package, documentation, and local CI-equivalent
  quality evidence.

## 4.5.0 - 2026-08-02

### Release

- Promoted the RC1-reviewed Creative Intelligence Ecosystem to stable `4.5.0`
  without adding functionality or changing the v4.5 public surface.
- Updated canonical Python, frontend, OpenAPI, MCP, SBOM, dependency-license,
  package, documentation, and release metadata to `4.5.0`.

### Compatibility

- v4.4 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow, Plugin,
  Provider, Backend, Web UI, and Extension SDK contracts remain additive-only
  and backward compatible. No migration is required.

### Quality

- Final regression, compatibility, architecture, Ecosystem end-to-end,
  benchmark, security, package, documentation, and local CI-equivalent
  validation completed.

## 4.5.0rc1 - 2026-08-02

### Release candidate

- Prepared the Creative Intelligence Ecosystem for RC review without adding a
  runtime capability. Creative Services, Plugins, Workflow Marketplace,
  Knowledge Exchange, Federation, Governance, and Reliability remain immutable,
  advisory, and human-operated projections.
- Synchronized Python, OpenAPI, MCP, frontend, SBOM, and dependency-license
  metadata on canonical prerelease version `4.5.0rc1` (`4.5.0-rc.1` for the
  frontend package).

### Compatibility

- Retained v4.4 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow,
  Plugin, Provider, Backend, Web UI, and Extension SDK contracts. No public
  interface or StateMachine transition changed.

### Validation

- Added RC architecture, compatibility, ecosystem end-to-end, performance,
  security, package, documentation, and local CI-equivalent quality evidence.

## 4.4.0 - 2026-08-02

### Release

- Promoted the RC1-reviewed Enterprise Creative Platform to stable `4.4.0`
  without adding functionality or changing the v4.4 public surface.
- Updated canonical Python, frontend, OpenAPI, MCP, SBOM, dependency-license,
  package, documentation, and release metadata to `4.4.0`.

### Compatibility

- v4.3 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow, Plugin,
  Provider, Backend, Web UI, and Extension SDK contracts remain additive-only
  and backward compatible. No migration is required.

### Quality

- Final regression, compatibility, architecture, Enterprise end-to-end,
  benchmark, security, package, documentation, and local CI-equivalent
  validation completed.

## 4.4.0rc1 - 2026-08-02

### Release candidate

- Prepared the Enterprise Creative Platform for RC review without adding a
  runtime capability: Enterprise Workspace, Collaboration, Portfolio,
  Extension Registry, Marketplace, Governance, and Reliability remain
  immutable, advisory, and human-operated projections.
- Synchronized Python, OpenAPI, MCP, frontend, SBOM, and dependency-license
  metadata on canonical prerelease version `4.4.0rc1` (`4.4.0-rc.1` for the
  frontend package).

### Compatibility

- Retained v4.3 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow,
  Plugin, Provider, Backend, Web UI, and Extension SDK contracts. No public
  interface or StateMachine transition changed.

### Validation

- Added RC architecture, compatibility, Enterprise end-to-end, performance,
  security, package, documentation, and local CI-equivalent quality evidence.

## 4.3.0 - 2026-08-02

### Release

- Promoted the reviewed Creative Production Platform from `4.3.0rc1` to the
  stable `4.3.0` release without adding functionality or changing the v4.3
  public surface.
- Updated canonical Python, frontend, OpenAPI, MCP, SBOM, dependency-license,
  package, documentation, and release metadata to `4.3.0`.

### Compatibility

- v4.2 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow,
  Extension SDK, Plugin, Provider, Backend, and Web UI contracts remain
  additive-only and backward compatible. No migration is required.

### Quality

- Final regression, compatibility, architecture, integration, benchmark,
  package, documentation, and local security-boundary validation completed.

## 4.3.0rc1 - 2026-07-29

### Added

- Creative Production Platform DTO foundations for Production Pipeline, Asset
  Management, Project Workspace, and Deliverable Management.
- Planning and intelligence DTOs for Production Automation, Asset Intelligence,
  Publishing Workflow, and Project Analytics.
- Governance, Quality Assurance, Operations Monitoring, and Platform
  Reliability DTOs that remain human-reviewed and non-executing.

### Changed

- The canonical prerelease version is `4.3.0rc1`, with frontend metadata
  `4.3.0-rc.1`, matching SBOM and release records.

### Compatibility

- v4.2 Python API, CLI, FastAPI, REST API, MCP, Repository, Workflow,
  Extension SDK, Plugin, Provider, Backend, and Web UI contracts remain
  additive-only and backward compatible.

### Security

- Production policies, QA, monitoring, reliability, export, and publishing
  projections remain advisory. They cannot enforce, approve, monitor, alert,
  recover, export, publish, distribute, bill, or call external services.

### Documentation

- Added v4.3 RC1 architecture, compatibility, workflow, performance, security,
  release checklist, and readiness records.

## 4.2.0 - 2026-07-29

### Added

- Promoted the reviewed Autonomous Creative System foundations for execution,
  checkpoints, supervision, planning, pipeline, governance, observability, and
  reliability to the stable v4.2.0 release.

### Changed

- Promoted the canonical Python version and derived OpenAPI/MCP metadata to
  `4.2.0`, with matching frontend metadata, SBOM, README, and release assets.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Completed RC feedback review and final architecture, compatibility,
  integration, benchmark, security, package, and documentation validation.

### Security

- Retained human approval, StateMachine, one-Page, storyboard, and
  quality-review boundaries with policy enforcement, override, telemetry,
  retry, recovery, and autonomous execution disabled.

### Performance

- Retained provider-free DTO projection benchmark smoke for all v4.2
  Autonomous Creative System modules.

### Documentation

- Added stable release, migration, architecture, security, package, checklist,
  and release-ready records for v4.2.0.

### Developer Experience

- Retained typed additive DTO exports and the single canonical version source.

## 4.2.0rc1 - 2026-07-29

### Added

- Added additive, non-executing v4.2 DTO foundations for Autonomous Execution,
  Checkpoint Management, Supervisor Runtime, Long-running Tasks, Goal
  Management, Adaptive Planning, Pipeline Automation, Execution Recovery,
  Human Supervision, Execution Governance, Execution Observability, and
  Execution Reliability.

### Changed

- Promoted the canonical Python version and derived OpenAPI/MCP metadata to
  `4.2.0rc1`, with matching frontend prerelease metadata `4.2.0-rc.1`, SBOM,
  README, and RC release assets.

### Fixed

- Completed the v4.2 architecture, compatibility, integration, benchmark,
  security-boundary, documentation, and release-readiness review.

### Security

- Retained human approval, StateMachine, one-Page, storyboard, and
  quality-review boundaries with policy enforcement, override, telemetry,
  retry, recovery, and autonomous execution disabled.

### Performance

- Added provider-free benchmark smoke coverage for execution, checkpoint,
  supervisor, task, planning, pipeline, recovery, governance, monitoring, and
  reliability DTO projections.

### Documentation

- Added v4.2 RC1 architecture, compatibility, workflow, benchmark, security,
  checklist, and readiness records.

## 4.1.0 - 2026-07-29

### Added

- Promoted the reviewed Multi-Agent Registry, Runtime, Orchestration,
  Collaboration, Human-in-the-Loop, Governance, Observability, and Reliability
  DTO foundations to the stable v4.1.0 release.

### Changed

- Promoted the canonical Python version and derived OpenAPI/MCP metadata to
  `4.1.0`, with matching frontend metadata, SBOM, README, and release assets.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Completed RC feedback review and final architecture, compatibility,
  integration, benchmark, security, package, and documentation validation.

### Security

- Retained disabled policy enforcement, message transport, telemetry export,
  automatic retry/recovery, and autonomous agent execution boundaries.

### Performance

- Retained provider-free Agent Runtime, Orchestration, Collaboration,
  Observability, and Repository projection regression smoke.

### Documentation

- Added stable release, migration, package, architecture, security, benchmark,
  checklist, and release-ready records for v4.1.0.

### Developer Experience

- Retained typed additive DTOs, a single derived version source, and package
  build/install validation.

## 4.1.0rc1 - 2026-07-29

### Added

- Added additive Multi-Agent Registry, Runtime, Orchestration, Collaboration,
  Human-in-the-Loop, Governance, Observability, and Reliability DTO surfaces.

### Changed

- Promoted the canonical Python version and derived OpenAPI/MCP metadata to
  `4.1.0rc1`, with matching frontend prerelease metadata `4.1.0-rc.1` and SBOM.

### Fixed

- Completed v4.1 architecture, compatibility, integration, benchmark, security,
  documentation, and release-readiness review.

### Security

- Retained disabled policy enforcement, message transport, remote telemetry,
  automatic retry/recovery, and autonomous agent execution boundaries.

### Performance

- Added provider-free Agent Runtime, Orchestration, Collaboration, and event
  processing micro-benchmark smoke evidence.

### Documentation

- Added v4.1 RC1 release notes and architecture, compatibility, workflow,
  benchmark, security, checklist, and readiness records.

## 4.0.0 - 2026-07-29

### Added

- Promoted the RC1-reviewed Creative Workspace, Creative Memory, Creative
  Knowledge Graph, Creative Quality, Intelligence, and Governance DTO surfaces
  to the stable v4.0.0 release.

### Changed

- Promoted the canonical Python version and derived OpenAPI/MCP metadata to
  `4.0.0`, with matching frontend metadata, SBOM, README, and release assets.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Completed RC feedback review and final architecture, compatibility,
  integration, benchmark, security, package, and documentation evidence.

### Security

- Retained memory validation, graph integrity, DTO, Plugin, and Extension
  validation; local dependency audit found no known vulnerabilities among
  auditable dependencies.

### Performance

- Retained provider-free regression smoke for Workspace, Memory, Graph,
  Quality, Intelligence, Governance, Repository, and reporting projections.

### Documentation

- Added stable release, migration, package, architecture, security, benchmark,
  checklist, and release-ready records for v4.0.0.

### Developer Experience

- Retained typed DTOs, package metadata derivation, frontend validation, and
  clean-install CLI/MCP verification.

## 4.0.0rc1 - 2026-07-29

### Added

- Promoted the additive Creative Workspace, Creative Memory, Creative Knowledge
  Graph, Creative Quality, Intelligence, and Governance DTO modules to v4.0 RC1
  review scope.

### Changed

- Promoted the canonical Python version and its derived OpenAPI/MCP metadata to
  `4.0.0rc1`, with matching frontend prerelease metadata `4.0.0-rc.1` and SBOM.

### Fixed

- Completed local architecture, compatibility, integration, benchmark, security,
  release-asset, and documentation review for the v4.0 RC candidate.

### Security

- Retained read-only memory, graph-integrity, DTO, Plugin, and Extension
  validation boundaries; publication still requires tagged hosted security scans.

### Performance

- Added provider-free RC regression smoke for Workspace, Memory, Graph,
  Intelligence, Governance, and Repository DTO projections.

### Documentation

- Added RC1 release, architecture, compatibility, workflow, benchmark, security,
  checklist, and readiness records for v4.0.

## 3.5.0 - 2026-07-29

### Added

- Promoted the RC1-reviewed Unified Knowledge Graph, Creative Intelligence,
  Production Intelligence, Platform Analytics, and Governance DTO surfaces to
  the stable v3.5.0 release.

### Changed

- Promoted the canonical Python version and derived OpenAPI/MCP metadata to
  `3.5.0`, with matching frontend metadata, SBOM, README, release assets, and
  dependency-license review record.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Completed RC feedback review and final architecture, compatibility,
  integration, benchmark, security, package, and documentation evidence.

### Security

- Retained Knowledge Graph integrity, DTO, Plugin, and Extension validation;
  local dependency audit found no known vulnerabilities among auditable
  dependencies.

### Performance

- Retained provider-free regression smoke for graph, analytics, dashboard,
  Repository, and reporting projections without changing workflow execution.

### Documentation

- Added stable release, migration, package, architecture, security, benchmark,
  checklist, and release-readiness records for v3.5.0.

### Developer Experience

- Retained typed DTO delivery through CLI, FastAPI, and MCP, together with
  frontend typecheck, contract tests, and production-build validation.

## 3.5.0rc1 - 2026-07-29

### Added

- Added additive v3.5 Unified Knowledge Graph, Creative Intelligence,
  Production Intelligence, Platform Analytics, and Governance DTO surfaces for
  CLI, optional FastAPI, and MCP.

### Changed

- Promoted the canonical Python version and derived OpenAPI/MCP metadata to
  `3.5.0rc1`, with matching frontend prerelease metadata `3.5.0-rc.1`.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Consolidated RC architecture, compatibility, integration, benchmark,
  security, documentation, and governance validation evidence for v3.5.

### Security

- Retained DTO validation, Knowledge Graph integrity boundaries, Plugin and
  Extension validation, secret redaction, and publication-time dependency/CVE
  and secret-scan gates.

### Performance

- Added provider-free regression-smoke evidence for v3.5 graph, analytics,
  dashboard, Repository, and reporting projections without changing execution.

### Documentation

- Added v3.5 RC1 release, architecture, compatibility, workflow, benchmark,
  security, checklist, and readiness records.

### Developer Experience

- Kept shared typed DTO delivery through additive CLI, FastAPI, and MCP seams,
  with deterministic local tests and provider-free benchmarks.

## 3.4.0 - 2026-07-29

### Added

- Promoted the RC1-reviewed, read-only Knowledge Platform, Production
  Operations, Organization Intelligence, Release Intelligence, and Governance
  DTO surfaces to the stable v3.4.0 release.

### Changed

- Promoted the canonical Python version and its derived OpenAPI/MCP metadata,
  matching frontend metadata, SBOM, README, and release assets to `3.4.0`.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Completed final release evidence for architecture, compatibility, workflow,
  package, security, benchmark, production, diagnostics, reporting, recovery,
  and governance validation.

### Security

- Retained secret redaction, SSRF, webhook, injection, manifest, Plugin,
  Extension SDK, validation, audit, and publication-time CVE/secret-scan gates.

### Performance

- Retained provider-free benchmark smoke for v3.4 projection paths without
  changing workflow execution behavior or asserting machine-independent SLOs.

### Documentation

- Added stable release, migration, compatibility, architecture, deployment,
  operations, package, security, checklist, and readiness evidence.

### Developer Experience

- Retained shared typed DTO delivery through additive CLI, FastAPI, and MCP
  seams, with mock-only checks for developer and release workflows.

### Knowledge Platform

- Stabilized catalog, classification, relationship, quality, index,
  intelligence, and governance reporting as non-mutating Repository-port
  projections.

### Production Operations

- Stabilized operations status, capacity, timeline, optimization, and
  governance reports as human-reviewed Application-layer evidence.

### Organization Intelligence

- Stabilized team health, role, workload, collaboration, risk, analytics, and
  governance projections without creating employee-management authority.

### Release Intelligence

- Stabilized release health, deployment, compatibility, regression, analytics,
  forecast, and governance evidence without publication authority.

### Governance

- Stabilized additive policy, compliance, audit, retention, and dashboard DTOs
  that support review and do not enforce, approve, deploy, or publish.

## 3.4.0rc1 - 2026-07-29

### Added

- Added additive, read-only Knowledge Platform, Production Operations,
  Organization Intelligence, Release Intelligence, and Governance DTO delivery
  surfaces for CLI, optional FastAPI, and MCP.

### Changed

- Promoted the canonical Python version, derived OpenAPI/MCP metadata,
  frontend prerelease metadata, SBOM, README, and RC release assets to
  `3.4.0rc1` / `3.4.0-rc.1`.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Consolidated RC architecture, compatibility, workflow, package, security,
  benchmark, reliability, diagnostics, reporting, and governance evidence.

### Security

- Retained redaction, validation, SSRF, webhook, manifest, Plugin, Extension
  SDK, rate-limit, audit, and publication-time dependency/CVE/secret-scan gates.

### Performance

- Added provider-free smoke coverage for v3.4 Foundation, Intelligence, and
  Governance DTO projections; workflow execution paths remain unchanged.

### Documentation

- Added v3.4 RC1 release, migration, compatibility, architecture, workflow,
  benchmark, security, package, checklist, and readiness documentation.

### Developer Experience

- Preserved shared typed DTO delivery through additive CLI, FastAPI, and MCP
  seams, examples, benchmarks, and mock-only validation.

### Production

- Confirmed v3.4 Knowledge, Operations, Organization, Release, and Governance
  reports are non-executing, non-authoritative Application-layer projections.

## 3.3.0 - 2026-07-29

### Added

- Added additive, read-only Production Pipeline, Quality Intelligence, Asset
  Lifecycle, Project Intelligence, and Governance DTO reporting surfaces.

### Changed

- Promoted canonical Python, OpenAPI, MCP, frontend, SBOM, README, and release
  metadata to stable `3.3.0`.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Consolidated final architecture, compatibility, workflow, package, security,
  benchmark, diagnostics, reporting, and governance evidence for publication.

### Security

- Retained secret/configuration redaction, validation, SSRF, webhook,
  manifest, plugin, Extension SDK, rate-limit, and publication-time dependency,
  CVE, and secret-scan gates.

### Performance

- Added provider-free smoke coverage for v3.3 foundation, intelligence, and
  governance DTO projections; no workflow execution path changed.

### Documentation

- Added stable release notes, compatibility, architecture, workflow regression,
  package, security, migration, benchmark, checklist, and readiness reports.

### Developer Experience

- Preserved typed, transport-neutral CLI, FastAPI, and MCP DTO delivery with
  examples, benchmarks, and mock-only validation.

### Production

- Confirmed Production, Quality, Asset, Project, and Governance reports remain
  non-executing, non-authoritative Application-layer projections.

### Production Pipeline

- Finalized additive Pipeline stages, transitions, approval evidence, session,
  timeline, intelligence, and governance DTOs without changing execution.

### Quality Intelligence

- Finalized typed quality metrics, rules, findings, trends, review coverage,
  diagnostics, and governance reports without approval authority.

### Asset Lifecycle

- Finalized Repository-port-only asset lifecycle, history, archive, dependency,
  intelligence, and governance projections with no write authority.

### Project Intelligence

- Finalized advisory project-health, milestone, schedule, resource, risk,
  delivery, operations, and governance reports without scheduling authority.

### Governance

- Finalized diagnostic-only Production, Quality, Asset, and Project policy,
  audit, compliance, retention, and dashboard DTO surfaces.

## 3.2.0 - 2026-07-29

### Added

- Added additive, read-only v3.2 Creative Studio, Asset Intelligence, Workflow
  Profiles, Production Analytics, Workspace/Asset/Workflow/Production Insights,
  and Reliability/Governance/Release Readiness DTOs.

### Changed

- Promoted the canonical Python, OpenAPI, MCP, frontend, SBOM, README, and
  release metadata to the stable `3.2.0` version.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Consolidated v3.2 delivery, compatibility, package, security, benchmark, and
  workflow-regression evidence for stable-release review.

### Security

- Retained redaction, validation, SSRF, webhook, manifest, rate-limit, audit,
  and publication-time dependency/CVE and secret-scan gates.

### Performance

- Added provider-free local smoke coverage for the v3.2 DTO projection paths;
  no workflow execution path was changed.

### Documentation

- Added stable release notes, audits, migration, checklist, and readiness report.

### Developer Experience

- Preserved typed, transport-neutral CLI, FastAPI, and MCP delivery seams with
  examples, benchmarks, and mock-only validation.

### Production

- Confirmed production diagnostics, health, recovery, repository integrity,
  and configuration validation remain advisory and transport-neutral.

### Creative Studio

- Promoted the additive Creative Studio workspace, activity, and reliability
  views without introducing workflow authority or a collaborative write model.

### Asset Intelligence

- Promoted read-only asset catalog, metadata, relationship, analytics,
  governance, lifecycle, and risk evidence through existing Repository ports.

### Workflow Profiles

- Promoted StateMachine-derived profile and pipeline analysis that describes
  legal next steps without changing workflow execution.

### Production Analytics

- Promoted bounded project, workflow, review, quality, insight, and release
  analytics DTOs without automated operational action.

## 3.1.0 - 2026-07-29

### Added

- Promoted the reviewed v3.1 release with additive, diagnostic Creative
  Collaboration, Knowledge Evolution, Operations, Developer Productivity,
  Creative Review, Knowledge Analytics, Operations Intelligence, Creative
  Governance, Knowledge Reliability, Operational Readiness, and Release Quality
  DTOs.

### Changed

- Aligned the Python package, root import, MCP, optional OpenAPI metadata,
  frontend package, SBOM, README, changelog, and stable assets to the single
  canonical `3.1.0` version source.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Resolved release metadata and documentation references identified during RC1
  review; release diagnostics now reference the v3.1 stable asset set.

### Security

- Retained secret/configuration redaction, webhook, SSRF, validation,
  sanitization, manifest, rate-limit, audit, and hosted dependency/CVE and
  secret-scan gates.

### Performance

- Confirmed provider-free benchmark smoke coverage for Creative, Knowledge,
  Operations, Developer Productivity, workflow, repository, diagnostics,
  reporting, and health DTO paths.

### Documentation

- Added stable release notes, architecture/compatibility audits, migration,
  workflow regression, package/security audit, deployment/operations guides,
  and release-readiness reports.

### Developer Experience

- Retained typed, transport-neutral CLI, FastAPI, and MCP DTO delivery, local
  examples/benchmarks, mock-only validation, and release verification.

### Production

- Confirmed startup, health, observability, diagnostics, reporting, recovery,
  repository-integrity, and configuration-validation contracts remain advisory
  Application-layer capabilities.

### Operations

- Promoted the v3.1 operations and production deployment guidance without
  introducing automated deployment, configuration mutation, or release actions.

### Creative

- Promoted Creative Collaboration, Creative Review, and Creative Governance
  DTOs while retaining explicit human review and approval boundaries.

### Knowledge

- Promoted Knowledge Evolution, analytics, reliability, and governance DTOs
  while retaining repository-port-only, redacted, read-only access.

### Developer Productivity

- Promoted workspace, planning, validation, and developer-experience templates
  and reports as non-executing development aids.

## 3.0.0 - 2026-07-29

### Added

- Promoted reviewed v3 AI Director Platform, Creative Pipeline, Knowledge
  Foundation, Creative Knowledge, Multi-Agent Foundation, Review Pipeline, and
  Production Readiness DTOs to the first stable AI Manga Production OS release.

### Changed

- Promoted RC metadata to stable `3.0.0` for the Python package, MCP, optional
  OpenAPI metadata, frontend package, SBOM, README, and release assets through
  the single canonical `_version.py` source.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Finalized release documentation, package evidence, migration guidance,
  compatibility records, and deterministic release-validation evidence.

### Security

- Retained secret/configuration redaction, webhook, SSRF, validation,
  sanitization, manifest, rate-limit, audit, and hosted scan release gates.

### Performance

- Confirmed provider-free planning, knowledge, director, creative, review,
  repository, workflow, diagnostics, reporting, and health smoke paths.

### Documentation

- Added v3 stable release notes, compatibility, architecture, migration,
  deployment, operations, AI Director, Creative Pipeline, Knowledge, checklist,
  and release-ready records.

### Developer Experience

- Retained typed DTO delivery through CLI, FastAPI, MCP, and Web UI seams,
  mock-only validation, examples, benchmarks, package verification, and
  frontend checks.

### Production

- Confirmed observability, diagnostics, reporting, recovery, repository
  integrity, configuration validation, and production readiness remain
  additive Application-layer capabilities.

### Enterprise

- Confirmed governance, configuration, workflow, knowledge, and operations
  evidence without introducing Cloud scope.

### AI Director

- Confirmed Director goals, plans, session validation, reliability, public
  decision traces, and readiness reports remain advisory DTO services.

### Creative Planning

- Confirmed Story, Chapter, Page, Panel, policy, governance, compliance, and
  audit evidence preserves existing creative workflow safeguards.

### Knowledge

- Confirmed repository-derived, redacted Knowledge Foundation and Creative
  Knowledge indexes, relationships, integrity, governance, quality, and risk
  reports preserve the Repository interface.

### Multi-Agent

- Confirmed profiles, capability mappings, assignments, and coordination plans
  remain planning-only and cannot execute Agents.

### Review Pipeline

- Confirmed Story, Storyboard, Character, Knowledge consistency, and Creative
  Quality reports are diagnostic only and cannot approve a Page.

## 3.0.0rc1 - 2026-07-29

### Added

- Prepared the v3.0 Release Candidate with reviewed, advisory AI Director
  Platform, Creative Pipeline, Knowledge Foundation, Multi-Agent Foundation,
  Review Pipeline, and Production Readiness DTOs.

### Changed

- Aligned package, MCP, optional OpenAPI metadata, frontend metadata, SBOM,
  README, and release assets to the canonical `3.0.0rc1` version source
  (`3.0.0-rc.1` for npm).

### Deprecated

- None.

### Removed

- None.

### Fixed

- Added RC compatibility, workflow regression, architecture, benchmark,
  security, package, migration, and release-readiness evidence.

### Security

- Retained secret/configuration redaction, webhook and SSRF validation, input
  validation, sanitization, manifest validation, rate limiting, audit logging,
  and hosted scan gates for the exact RC tag.

### Performance

- Confirmed provider-free planning, knowledge, director, review, repository,
  workflow, diagnostics, reporting, and health benchmark smoke paths.

### Documentation

- Added v3 RC release notes and release-audit documentation with explicit
  compatibility and non-autonomous-operation boundaries.

### Developer Experience

- Preserved typed DTO delivery through CLI, FastAPI, MCP, and Web UI seams,
  plus deterministic local validation and benchmark scripts.

## 2.7.0 - 2026-07-28

### Added

- Promoted the reviewed v2.7 AI Director Foundation, Knowledge Intelligence,
  Workflow Orchestration, Enterprise AI readiness, diagnostics, and dashboard
  DTOs to the stable release.

### Changed

- Promoted RC metadata to stable `2.7.0` for the Python package, MCP, optional
  OpenAPI metadata, frontend package, SBOM, README, and release assets from the
  single canonical `_version.py` source.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Finalized release documentation, package evidence, migration guidance,
  compatibility records, and deterministic repeatability measurement evidence.

### Security

- Retained existing secret, configuration, webhook, SSRF, validation,
  sanitization, manifest, rate-limit, audit, and hosted scan release gates.

### Performance

- Confirmed provider-free Workflow, Repository, Knowledge, planning, analysis,
  runtime, diagnostics, reporting, and health smoke paths without a local
  regression.

### Documentation

- Added v2.7 stable release notes, compatibility, architecture, migration,
  production, operations, AI Director, Knowledge, checklist, and release-ready
  records.

### Developer Experience

- Retained typed APIs, mock-only validation, CLI/MCP/FastAPI DTO seams,
  examples, benchmarks, package verification, and frontend checks.

### Production

- Confirmed observability, diagnostics, reporting, recovery, repository
  integrity, configuration validation, and health remain additive
  Application-layer capabilities.

### Enterprise

- Confirmed Enterprise AI readiness, governance, configuration, workflow, and
  operations evidence without introducing Cloud scope.

### AI Director

- Confirmed Director planning, integrity, consistency, public decision trace,
  execution readiness, and dashboard reports remain advisory DTO services.

### Knowledge

- Confirmed repository-derived, redacted Knowledge search, intelligence,
  governance, quality, and risk reports preserve the Repository interface.

## 2.7.0rc1 - 2026-07-28

### Added

- Prepared the v2.7 Release Candidate with reviewed, read-only AI Director
  reliability, Knowledge governance, Enterprise AI readiness, diagnostics,
  and executive-dashboard DTOs.

### Changed

- Aligned Python package, MCP, optional OpenAPI metadata, frontend prerelease
  metadata, SBOM, README, dependency-license report, and RC assets to the
  canonical `2.7.0rc1` version source (`2.7.0-rc.1` for npm).

### Deprecated

- None.

### Removed

- None.

### Fixed

- Added RC architecture, compatibility, workflow-regression, security,
  package, benchmark, and readiness evidence for the AI Director and Knowledge
  additions.

### Security

- Retained existing secret, configuration, webhook, SSRF, validation,
  sanitization, manifest, rate-limit, audit, and hosted dependency/CVE and
  secret-scan release gates.

### Performance

- Verified provider-free Workflow, Repository, Knowledge, planning, analysis,
  runtime, diagnostics, reporting, and health smoke paths locally.

### Documentation

- Added v2.7 RC notes, Architecture Summary, compatibility audit, workflow
  regression evidence, benchmark record, security/package audits, checklist,
  and readiness report.

### Developer Experience

- Retained typed APIs, mock-only validation, CLI/MCP/FastAPI DTO seams,
  examples, benchmarks, package verification, and release-contract coverage.

### Enterprise AI

- Confirmed Director, Knowledge, workflow, configuration, operations, and
  governance readiness remain advisory Application-layer evidence only.

## 2.6.0 - 2026-07-28

### Added

- Promoted the reviewed v2.6 AI Workflow Planning, Workflow Analysis, Provider
  Orchestration, Provider Governance, Enterprise Readiness, and executive
  reporting DTOs to the stable release.

### Changed

- Promoted RC metadata to stable `2.6.0` for the Python package, MCP, optional
  OpenAPI metadata, frontend package, SBOM, README, and release assets from the
  single canonical `_version.py` source.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Finalized release documentation, package evidence, migration guidance, and
  compatibility records for stable publication.

### Security

- Retained the RC dependency-audit correction requiring development
  `pytest>=9.0.3` and all existing secret, configuration, manifest, rate-limit,
  audit, and hosted scan release gates.

### Performance

- Confirmed provider-free Workflow, Repository, planning, analysis, runtime,
  diagnostics, reporting, and health smoke paths without a local regression.

### Documentation

- Added v2.6 stable release notes, compatibility, architecture, migration,
  production, operations, AI Workflow, checklist, and release-ready records.

### Developer Experience

- Retained typed APIs, mock-only validation, package verification, frontend
  checks, examples, benchmarks, and release-contract coverage.

### Production

- Confirmed planning, observability, diagnostics, reporting, recovery,
  repository integrity, configuration validation, and health remain additive
  Application-layer capabilities.

### Enterprise

- Confirmed Provider Governance, configuration readiness, workflow integrity,
  and Enterprise Readiness without introducing Cloud scope.

### AI Workflow

- Confirmed planning, analysis, intelligence, and reliability are advisory DTO
  services; `WorkflowEngine` and the StateMachine remain execution authorities.

## 2.6.0rc1 - 2026-07-28

### Added

- Prepared the v2.6 Release Candidate with the previously reviewed,
  read-only Workflow Planning, Workflow Analysis, Provider Orchestration,
  Provider Governance, Enterprise Readiness, and executive-dashboard DTOs.

### Changed

- Aligned Python package, MCP, optional OpenAPI metadata, frontend prerelease
  metadata, SBOM, README, and release assets to the canonical `2.6.0rc1`
  version source (`2.6.0-rc.1` for npm).

### Deprecated

- None.

### Removed

- None.

### Fixed

- Added explicit RC audit records for architecture, compatibility, workflow
  regression, security, package, benchmark, and release-checklist evidence.

### Security

- Raised the development `pytest` lower bound to `9.0.3` to address the
  dependency-audit finding for earlier pytest releases.
- Retained secret, configuration, manifest, rate-limit, audit, and hosted
  dependency/CVE and secret-scan gates; hosted scans remain required per tag.

### Performance

- Confirmed provider-free workflow, repository, planning, analysis, Provider /
  Backend runtime, automation, diagnostics, reporting, and health smoke paths
  without an identified local regression.

### Documentation

- Added v2.6 RC1 release notes, compatibility, architecture, workflow,
  package, security, benchmark, checklist, and readiness records.

### Developer Experience

- Preserved typed, mock-only local validation across backend, frontend,
  package, planning, diagnostics, production, and enterprise boundaries.

### Enterprise

- Confirmed Provider Governance, configuration readiness, workflow integrity,
  and Enterprise Readiness remain diagnostic-only Application-layer features.

## 2.5.0 - 2026-07-26

### Added

- Promoted the reviewed v2.5 Production quality, observability, diagnostics,
  reliability, release-readiness, and OSS-readiness DTO evidence to the stable
  release without changing Core workflow semantics.

### Changed

- Promoted reviewed RC metadata to stable `2.5.0` for the Python package, MCP,
  optional OpenAPI metadata, SBOM, and frontend package from the single
  canonical `_version.py` source.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Finalized version, artifact, documentation, migration, governance, license,
  and dependency-policy evidence for the stable publication workflow.

### Security

- Retained secret, configuration, manifest, rate-limit, audit, and hosted
  dependency/CVE and secret-scan release gates.

### Performance

- Confirmed provider-free workflow, repository, runtime, diagnostics, reporting,
  health, and release-readiness smoke paths without an identified regression.

### Documentation

- Added v2.5 release notes, compatibility, architecture, migration, production,
  operations, quality, checklist, and release-ready records.

### Developer Experience

- Retained typed APIs, mock-only CI, package validation, frontend checks,
  examples, benchmark smoke, and release-contract coverage.

### Production

- Confirmed startup validation, graceful shutdown, health, observability,
  diagnostics, recovery, repository integrity, configuration validation, and
  reporting remain additive Application-layer capabilities.

### Enterprise

- Confirmed configuration governance, repository/runtime evidence, Provider /
  Backend diagnostics, and release readiness without introducing Cloud scope.

### OSS

- Confirmed contribution, governance, license, dependency license, community,
  supported-version, and release-process evidence for stable publication.

## 2.5.0rc1 - 2026-07-26

### Added

- Prepared the v2.5 Release Candidate with read-only reliability, maintenance,
  release, OSS, and executive readiness evidence in the optional Production
  application layer.

### Changed

- Aligned Python, MCP, optional OpenAPI, SBOM, and frontend prerelease metadata
  to `2.5.0rc1` / `2.5.0-rc.1` from the canonical package version source.

### Fixed

- Made artifact, version, documentation, migration, governance, and dependency
  policy checks explicit release-readiness evidence.

### Security

- Retained existing secret, configuration, manifest, rate-limit, audit, and
  dependency/secret-scan release gates; hosted scans remain required per tag.

### Performance

- Confirmed provider-free diagnostics, reporting, health, and release-readiness
  benchmark smoke paths without an identified local regression.

### Documentation

- Added RC1 release notes, compatibility, architecture, benchmark, checklist,
  and readiness records.

### Developer Experience

- Retained typed, mock-only CI checks for backend, frontend, package, release,
  diagnostics, production, and enterprise boundaries.

### Added

- Added read-only v2.5 Iteration 3 reliability, maintenance, release, OSS, and
  executive readiness DTOs in the optional `manga_director.production` package.

### Changed

- Extended local quality evidence with artifact, version, documentation,
  migration, governance, license, and dependency-policy validation without
  changing the Core, Workflow, Repository port, or root public API.

### Documentation

- Added operational guidance for release process, maintenance, dependency
  policy, and OSS readiness, plus provider-free readiness benchmarks and examples.

## 2.4.0 - 2026-07-26

### Added

- Promoted the reviewed Production Runtime, operations, and reliability DTO
  facades for startup validation, configuration review, provider/backend
  inventory, health history, recovery validation, long-running diagnostics,
  and production-readiness evidence.

### Changed

- Promoted reviewed `2.4.0rc1` metadata to stable `2.4.0` for the Python
  package, MCP, optional OpenAPI metadata, SBOM, and frontend package without
  changing workflow semantics or public contracts. The package build now reads
  its version from the single canonical `_version.py` source.
- Retained documented v1.x and v2.0.x-v2.3.x Python API, CLI, FastAPI, MCP,
  Repository, Plugin, Extension SDK, Provider, Image Backend, Automation,
  Notification, Diagnostics, and Health API contracts.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Made the publication checklist explicit that the exact release tag must pass
  clean hosted dependency/CVE and secret scans before upload.

### Security

- Revalidated secret redaction, configuration/import validation, manifest
  checks, audit/rate-limit controls, and release-time dependency/secret-scan
  gates.

### Performance

- Confirmed provider-free production, operations, recovery, long-running, and
  benchmark smoke paths without a local regression.

### Documentation

- Added stable v2.4 compatibility, architecture, migration, production
  deployment, operations, release checklist, release notes, and readiness
  records.

### Developer Experience

- Retained mock-only CI coverage across backend, frontend, docs, package,
  security, nightly, diagnostics, production, and enterprise boundaries.

### Production

- Confirmed startup validation, graceful shutdown, health monitoring,
  observability, diagnostics, recovery, repository integrity, and
  configuration validation remain additive outer-layer capabilities.

### Enterprise

- Confirmed local configuration governance, repository-port-based operations,
  provider/backend inventory, diagnostics, and health evidence without adding
  Cloud or distributed runtime scope.

## 2.4.0rc1 - 2026-07-26

### Added

- Optional Production Runtime, operations, and reliability DTO facades for
  startup validation, safe configuration review, provider/backend inventory,
  health history, recovery validation, long-running diagnostics, and
  production-readiness checklists.

### Changed

- Published RC metadata as `2.4.0rc1` for Python/MCP/OpenAPI/SBOM and the
  equivalent `2.4.0-rc.1` npm frontend prerelease version.
- Preserved all documented v1.x and v2.0–v2.3 public API, workflow, CLI,
  FastAPI, MCP, Repository, Plugin, Extension SDK, Provider, and Backend
  contracts.

### Fixed

- Kept recovery admission and simulation read-only so no diagnostic path can
  execute an Agent, persist a repair, or bypass StateMachine validation.

### Security

- Retained secret redaction, configuration/import validation, manifest checks,
  audit/rate-limit controls, and dependency/secret-scan CI gates.

### Performance

- Added provider-free production, operations, reliability, recovery, and
  long-running benchmark smoke scenarios.

### Documentation

- Added v2.4 RC compatibility, architecture, benchmark, release checklist,
  release notes, and readiness records.

### Developer Experience

- Retained mock-only CI coverage across backend, frontend, docs, package,
  security, nightly, diagnostics, production, and enterprise boundaries.

## 2.3.0 - 2026-07-26

### Added

- Optional, DTO-only FastAPI observability composition for health, provider,
  backend, diagnostics, and repository-integrity routes.
- Provider/backend lifecycle health summaries, repository self-checks,
  configuration-governance evidence, enterprise diagnostics, and repeatability
  smoke coverage from the reviewed v2.3 iterations.

### Changed

- Promoted the reviewed `2.3.0rc1` candidate to stable `2.3.0` metadata without
  changing page-workflow semantics, public root exports, Repository, Provider,
  ImageGenerator, Plugin, or Extension SDK contracts.
- Aligned package, MCP, optional OpenAPI, frontend metadata, SBOM,
  dependency-license report, documentation, and stable release assets.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Corrected delivery documentation to distinguish the shipped optional
  observability DTO adapter from a general workflow REST API.
- Removed the observability-to-CLI import direction by injecting safe
  configuration summaries at the composition boundary.

### Security

- Revalidated existing secret masking, validation, audit, rate-limit,
  manifest-validation, dependency-audit, and secret-scan release gates.

### Performance

- Confirmed provider-free benchmark and repeatability smoke coverage across
  workflow, repository, database, provider/backend runtime, notification,
  automation, plugin, extension, and batch boundaries.

### Documentation

- Added v2.3 RC compatibility, benchmark, architecture, checklist, release
  notes, and readiness records.

### Developer Experience

- Retained mock-only static analysis, test, package, diagnostics, enterprise,
  and frontend CI gates for stable-release validation.

### Enterprise

- Confirmed configuration profiles/governance, repository scalability,
  provider/backend runtime health, diagnostics, and integrity validation with
  mock-only release evidence.

## 2.2.0 - 2026-07-26

### Added

- Final release assets: compatibility audit, benchmark comparison, architecture
  summary, release checklist, release notes, and release-ready report.
- Additive reliability and diagnostics DTOs, integrity and recovery helpers,
  health summaries, and diagnostic CLI/MCP entry points from the reviewed
  v2.2 iterations.

### Changed

- Promoted the reviewed `2.2.0rc1` candidate to stable `2.2.0` metadata without
  changing page-workflow semantics, the public Python API, CLI, MCP,
  Repository, Plugin, or Extension SDK contracts.
- Kept MCP metadata derived from the package's single Python version source;
  the frontend carries the same stable `2.2.0` version.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Hardened recovery, integrity validation, runtime diagnostics, and cached
  plugin/extension/configuration/event dispatch paths while preserving their
  established interfaces.

### Security

- Retained secret masking, validation, audit, rate-limit, manifest-validation,
  dependency-audit, and secret-scan release gates; no security model change is
  introduced in this stable release.

### Performance

- Added retained-baseline benchmark and repeatability smoke coverage for
  workflow, repository, database, batch, plugin, extension, notification, and
  diagnostics paths.

### Documentation

- Updated public API, README, migration, compatibility, benchmark, release,
  and readiness documentation for the stable release.

### Developer Experience

- Preserved the backend, frontend, package, security, docs, nightly, and
  benchmark-smoke CI gates for the formal release.

## 2.1.0 - 2026-07-26

### Added

- Final release assets: compatibility audit, benchmark report, release-ready
  report, release notes, SBOM, dependency-license report, and release checklist.

### Changed

- Promoted the reviewed `2.1.0rc1` runtime to the stable `2.1.0` metadata line
  without changing workflow semantics, public Python API, CLI, MCP, Repository,
  Plugin, or Extension SDK contracts.
- Marked the PyPI classifier as `Production/Stable` for the formal release.
- Kept MCP metadata derived from the package's single Python version source;
  the frontend carries its matching `2.1.0` package version.

### Deprecated

- None.

### Removed

- None.

### Fixed

- Finalized RC feedback protections for extension core-version comparison,
  built-in Plugin inclusion in wheels, and safe unexpected MCP transport errors.

### Security

- Revalidated the resolved runtime dependencies, documented secret/audit
  controls, and retained CI dependency-audit and secret-scan gates.

### Performance

- Confirmed no provider-free smoke-level regression against the retained v2.0
  baseline artifact.

### Documentation

- Updated the public API, architecture, migration, troubleshooting, FAQ,
  compatibility, release, and governance references for the stable release.

### Developer Experience

- Retained cached backend/frontend/package/security/nightly/release CI jobs,
  release-contract tests, clean-install validation, and unified local commands.

## 2.1.0rc1 - 2026-07-26

### Changed

- Iteration 2 and 3 hardened maintenance quality without changing public
  workflow semantics or public API contracts.
- Added deterministic repository listing, architecture/import/dependency/doc
  link quality gates, benchmark smoke coverage, and cached CI jobs.
- Aligned MCP server metadata with the package version and masked unexpected
  JSON-RPC transport errors.

### Security

- Added release security policy, dependency license report, SBOM, and explicit
  public-boundary documentation.
- Moved PostgreSQL and migration tooling to documented optional extras.

### Fixed

- Restored notification retries for status-less transient delivery failures.
- Restored frontend lint/typecheck gates and framework-safe internal links.
- Corrected wheel packaging so the built-in Plugin package is included in
  distributions.

## 2.0.0rc1 - 2026-07-26

### Added

- v2 integration foundations: extension SDK, security, notification, database,
  observability, and prior reviewed v2 workflow and delivery layers.

### Changed

- Release candidate metadata and v1-to-v2 migration guidance.

### Known limitations

- RC1 remains subject to the documented quality checklist; no remote extension
  delivery, signatures, OAuth/JWT, or distributed queue features are included.

### Added

- Local manifest-based Plugin System with discovery, dependency ordering,
  lifecycle management, typed Registry, CLI administration, examples, and
  documentation.
- Plugin contributions for Agent, Workflow, Repository, ImageGenerator, LLM,
  Prompt, CLI, and EventBus extension types.
- Provider-neutral LLM adapter contracts, Factory Registry, Mock provider,
  network-free OpenAI/Anthropic/Gemini/Ollama/OpenRouter/LiteLLM stubs, and
  Markdown-backed advisory assistance for workflow agents.
- Deterministic Prompt Pipeline with Builder, Optimizer, Validator, Renderer,
  Markdown Template Loader, configuration controls, and prompt audit metadata.
- Sequential Project and Chapter workflow engines, typed hierarchy contexts,
  a replaceable `WorkflowScheduler`, lifecycle events, CLI operations, and
  Project/Chapter workflow documentation.
- Persisted sequential Batch workflow orchestration with Planner, Queue,
  policies, Page-scoped Worker boundary, retry/resume support, batch events,
  CLI operations, and documentation.
- Local stdio MCP server with validated Tool registry, Application Service,
  DTOs, read-only resources, Markdown prompts, dependency injection, safe error
  mapping, CLI inspection commands, and transport tests.
- Minimal independent Next.js/TypeScript Web UI with typed REST client,
  Project/Chapter/Page workflow views, explicit approval form, responsive and
  accessible presentation states, and starter unit/E2E tests.

### Changed

- CLI runtime now composes enabled local image and agent contributions without
  changing the page WorkflowEngine or StateMachine.
- Project and Chapter workflows delegate exactly one page at a time to the
  unchanged Page `WorkflowEngine`; project/chapter engines contain no Agent or
  page-transition logic.
- Batch orchestration now delegates each Queue item through the unchanged Page
  `WorkflowEngine`; parallel and automatic execution remain non-executable API
  placeholders.
- MCP delivery now delegates through the Application Service and existing
  workflow boundaries; it does not call Agents or state-machine methods.
- Web UI is a Presentation Layer that delegates through its typed compatible
  HTTP client and never imports Core, CLI, MCP, or repositories.

## 1.0.0 - 2026-07-25

### Added

- Public Python API with `Director`, `WorkflowEngine`, `WorkflowContext`, Project/Page models, image-generator protocol, and repository protocol.
- One-page-at-a-time CLI, Project persistence, JSON/YAML import/export, and image-adapter registry.
- Mock image provider plus explicit OpenAI and ComfyUI API-boundary stubs.
- Examples, typed-package marker, GitHub Actions CI, contribution guide, and release assets.

### Changed

- Promoted the validated `0.1.0rc1` release candidate to the stable v1.0.0 API.
- Finalized package metadata, public exports, error hierarchy, documentation, and release checklist.

### Architecture

- Clean boundaries remain fixed: Domain → Workflow → Agents/Adapters/Repositories → CLI.
- `StateMachine` owns legal forward transitions; `WorkflowEngine` owns execution and event publication.
- Image providers are selected only through `ImageGeneratorFactory`; repository persistence is isolated behind `ProjectRepository`.

### Breaking Changes

- None from `0.1.0rc1`.
- v1.0.0 treats the documented root package API as stable; use documented public imports rather than internal module paths.

### Known Limitations

- OpenAI and ComfyUI adapters are stubs and make no network calls.
- Local JSON/YAML persistence has no schema migration mechanism yet.
- `run` deliberately stops at `QualityChecked`; human approval stays explicit.

### Future Work

- See [docs/ROADMAP_v2.md](docs/ROADMAP_v2.md) for v2 design candidates.
