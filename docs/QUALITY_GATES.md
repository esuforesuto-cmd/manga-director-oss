# v2 Quality Gates

Every v2.4+ implementation Issue must keep these gates green:

| Gate | Required evidence |
| --- | --- |
| Architecture | Domain dependency, Page-engine boundary, and import tests pass. |
| Compatibility | Public API, CLI, MCP, persisted Project, Plugin, and SDK contracts pass. |
| Security | Validation, sanitization, audit, dependency audit, and secret scan evidence pass. |
| Performance regression | Affected benchmark has a recorded baseline and no unapproved regression. |
| Benchmark smoke | Provider-free smoke suite passes. |
| Enterprise smoke | Configuration profile, redaction, audit, diagnostics, and Repository recovery fixtures pass without production credentials. |
| Provider contract | Any LLM Provider uses the existing Protocol/Factory, mock fixture, secret validation, and provider-neutral Agent behavior. |
| Image backend contract | Any ImageGenerator uses the existing Protocol/Factory, mock fixture, persisted-storyboard proof, and one-page result contract. |
| Configuration compatibility | Existing configuration files preserve defaults and reject secrets embedded in project configuration. |
| Repository scalability | Indexed reads, bounded history windows, and large-project scans preserve the existing repository port. |
| Lifecycle contracts | Provider/backend lifecycle, cached metadata validation, and shutdown evidence pass without generation calls. |
| Configuration governance | Schema compatibility, integrity validation, redacted fingerprint, and migration evidence pass. |
| Runtime health | Provider, backend, repository, workflow, configuration, Plugin, and Extension health DTO tests pass. |
| Repository integrity | Aggregate, metadata, history, snapshot, and bounded self-check tests pass. |
| Diagnostics | JSON/Markdown diagnostic DTO and CLI/MCP delivery tests pass without internal-model exposure. |
| Repeatability | Workflow, repository, provider, backend, and configuration smoke measurements stay within variance bounds. |
| Documentation links | README and docs local links resolve. |
| Production smoke | Mock/local production-operation fixture proves recovery, integrity, safe configuration, and explicit approval behavior. |
| Provider compatibility | Any provider candidate preserves the Protocol/Factory contract, provider-neutral Agents, secret boundary, and deterministic mock fixture. |
| Image backend compatibility | Any backend candidate preserves storyboard persistence, one-page generation, Factory contract, and deterministic mock fixture. |
| Configuration migration | Schema migration proposal has dry-run, compatibility, redaction, integrity, and rollback evidence. |
| Observability smoke | Health, diagnostics, timeline, metrics, and safe export remain DTO-only and do not steer workflow. |
| Production startup | Local startup validation, dependency probe, readiness/liveness, graceful shutdown, and DTO rendering tests pass without workflow execution. |
| Provider warmup | Metadata-only warmup, capability/metadata refresh, priority evaluation, and declarative fallback simulation pass without provider invocation. |
| Health monitoring | Application, Provider, Backend, Repository, Database, and Configuration health reports remain safe DTOs. |
| Startup benchmark | The provider-free startup, warmup, configuration, health, and runtime-metrics smoke measurements complete without network access. |
| Configuration validation | Snapshot, compare, fingerprint, redacted export, and import validation are tested without applying configuration changes. |
| Provider inventory | Metadata refresh, priority-plan diagnostics, capabilities, local health, and recommendation evidence pass without Provider invocation. |
| Backend inventory | Preset inventory, capability refresh, local health, and workflow-metadata compatibility pass without image generation. |
| Health history | Bounded configuration/provider/backend/runtime snapshots persist and reload through `ProjectRepository`. |
| Operational diagnostics | Composite configuration, Provider, Backend, compatibility, dependency, and runtime-summary DTO smoke test passes as JSON/Markdown. |
| Reliability smoke | Resume admission, workflow-history consistency, recovery simulation, and aggregate self-check remain read-only and preserve one-page workflow rules. |
| Recovery smoke | Invalid or terminal Pages are rejected for resume; simulations never execute an Agent or save a Project. |
| Long-running smoke | Bounded task lifecycle, batch counters, optional memory evidence, and graceful-recovery summary tests pass without changing host profiling state. |
| Reliability diagnostics | Architecture, dependency, Plugin, Extension, Provider, Backend, Configuration, Workflow, and Repository DTO sections render safely. |
| Production readiness | Deployment, upgrade, backup, and recovery checklists are generated from operations and recovery validation evidence. |
| Delivery quality | Ruff, mypy, pytest/coverage, package build, and relevant frontend checks pass. |
| Production regression | Startup, shutdown, recovery, repository integrity, health, diagnostics, and explicit approval fixtures preserve the v2.4 baseline. |
| Compatibility regression | Root API, CLI, MCP, optional FastAPI DTO, persisted Project, Repository, Plugin, Extension SDK, Provider, and Backend contracts remain compatible. |
| Provider compatibility | Candidate Provider proposals retain `LLMProvider`/Factory boundaries, secret validation, provider-neutral Agents, and deterministic mock fixtures. |
| Backend compatibility | Candidate backends retain `ImageGenerator`/Factory boundaries, storyboard persistence, one-page results, and deterministic mock fixtures. |
| Upgrade validation | Upgrade proposals provide configuration, repository integrity, Plugin/Extension compatibility, rollback, and redaction evidence. |
| Quality pipeline | An Issue records focused unit/integration/contract coverage plus architecture, security, documentation, benchmark, and rollback evidence. |
| Repository validation test | Statistics, integrity, cleanup candidates, and large-repository summary use only the existing repository port and perform no deletion. |
| Quality pipeline smoke test | Repository, Workflow, Configuration, API, documentation, and release-artifact DTO validations pass on a one-page mock fixture. |
| Documentation validation test | Required release assets and local Markdown links resolve without a documentation server. |
| API compatibility smoke test | Root exports and dynamic package-version source match the stable compatibility contract. |
| Release validation test | Package version source, SBOM version, and release asset checks pass before packaging. |
| Observability smoke test | Workflow/operation timelines and Repository, Provider, Backend, Automation, and Release metric categories render as DTOs without workflow execution. |
| Diagnostics smoke test | System, Repository, Workflow, Provider, Backend, Configuration, Environment, and Performance diagnostics render JSON/Markdown safely. |
| Performance analysis test | Baseline comparison, supplied trend, regression summary, and diagnostic-only recommendation remain provider-free and non-mutating. |
| Operations automation test | Maintenance scheduler and cleanup outputs remain plans; they schedule no task, delete no Project, and advance no workflow state. |
| Repository metrics test | Repository metric grouping uses in-process snapshots and does not change persistence semantics. |
| Release readiness smoke test | Local read-only release checklist covers workflow, repository, configuration, artifact, version, documentation, and migration evidence. |
| Artifact verification test | Typed marker, package metadata, required assets, and dynamic-version evidence are checked without building or publishing. |
| Repository health test | Port-based maintenance and integrity reports remain non-destructive. |
| Dependency validation test | Declared dependencies, dependency-license evidence, and policy guidance are present. |
| OSS readiness test | Contribution, governance, license, and community documents are locally verifiable without GitHub access. |
| Workflow planning validation | Advisory planning proposes at most one legal Page step, explains prerequisites, and never transitions state or calls an Agent. |
| Provider selection validation | Capability matching preserves Factory/Protocol boundaries, uses deterministic metadata, and never invokes a Provider. |
| Automation planning validation | Plans expose human decision points and checkpoints but do not schedule work, generate images, or approve Pages. |
| Enterprise operations validation | Dashboard, compliance, maintenance, and capacity DTOs remain redacted, read-only, Repository-port-based, and non-executing. |
| Compatibility regression | Planning additions preserve root API, Workflow, CLI, FastAPI DTO, MCP, Repository, Plugin, Extension SDK, Provider, and Backend contracts. |
| Planning diagnostics test | Workflow-planning, dependency, capability, selection, JSON/Markdown report, and delivery-preview fixtures remain read-only. |
| Execution preview test | Preview returns at most one legal next command and preserves the supplied one-page context exactly. |
| Workflow analysis smoke test | Timeline, graph, bottleneck, and recommendation DTOs have no Agent, Provider, scheduler, or persistence side effect. |
| Workflow analysis validation | Dependency, complexity, bottleneck, critical-path, score, and context comparison remain one-page, StateMachine-derived, and non-mutating. |
| Provider comparison validation | Capability, relative-latency, unknown-cost, local-health, recommendation, and explanation DTOs never invoke a Provider or enable fallback execution. |
| Enterprise diagnostics validation | System, configuration, workflow, Provider, Backend, Repository, and executive DTOs remain redacted, injected, and presentation-independent. |
| Operational analytics validation | Trends analyze bounded supplied/local observations only; they start no collector, persistence loop, scheduler, or automation. |
| Executive report validation | Workflow, Provider, operations, enterprise, and optimization summaries report no automatic action or state transition. |
| Workflow reliability validation | Integrity, validation, consistency, risk, and readiness analysis remain one-page, StateMachine-derived, and non-executing. |
| Provider governance validation | Policy, capability, lifecycle, compatibility, and risk reports use local metadata only and preserve Provider/Factory interfaces. |
| Enterprise readiness validation | Deployment, operations, maintenance, configuration, recovery, and workflow checklist DTOs cannot deploy, repair, or resume work. |
| Workflow diagnostics validation | Health, planning, dependency, execution-readiness, architecture, and executive DTOs redact internals and never invoke a workflow. |
| Executive dashboard validation | Workflow, Provider, enterprise, operations, and release dashboards remain transport-neutral and forbid automatic release/action. |
| Director Planning Validation | Director plans expose at most one StateMachine-legal Page step, decision trace, and policy assumptions without calling an Agent or mutating state. |
| Knowledge Validation | Knowledge candidates use bounded, redacted, deterministic local fixtures and preserve Repository-port semantics without automatic mutation. |
| Workflow Orchestration Validation | Dependency graphs and execution previews remain one-page, StateMachine-derived, human-checkpointed, and non-dispatching. |
| Automation Planning Validation | Automation plans and simulations remain advisory, never schedule work, invoke a provider, generate an image, approve a Page, or write state. |
| Compatibility Regression v2.7 | Director, Knowledge, Orchestration, and Automation additions preserve root API, Workflow, CLI, FastAPI DTO, MCP, Repository, Plugin, Extension SDK, Provider, and Backend contracts. |
| Decision Trace Validation | Traces contain bounded assumptions and StateMachine evidence only; they expose no hidden reasoning and authorize no execution. |
| Execution Strategy Validation | Strategies identify at most one legal next Page command and never dispatch, invoke a provider, or transition state. |
| Director Reliability Validation | Director integrity, consistency, public decision-trace, and readiness reports remain one-page, StateMachine-derived, and non-executing. |
| Knowledge Governance Validation | Policy, integrity, lifecycle, quality, and risk evidence use only redacted Repository-port projections and perform no mutation. |
| Enterprise AI Readiness Validation | Knowledge, workflow, configuration, operations, and governance readiness remain checklist DTOs and cannot deploy, resume, or configure a runtime. |
| AI Workflow Diagnostics Validation | Director, Knowledge, planning, workflow, and architecture diagnostics render JSON/Markdown safely with no internal models or workflow side effects. |
| Director Executive Dashboard Validation | Director, Knowledge, Workflow, Enterprise, and Release dashboard DTOs remain transport-neutral and forbid automatic release/action. |
| Director Planning Validation v3 | Director goals, task graphs, strategies, reviews, and iteration plans identify at most one StateMachine-legal Page step and cannot execute, dispatch, mutate, or invoke an Agent. |
| Knowledge Validation v3 | Knowledge indexes, snapshots, graph/search results, memories, and health reports are bounded, provenance-aware, redacted Repository-port projections with no implicit persistence mutation. |
| Creative Pipeline Validation v3 | Story-through-quality creative plans preserve the existing Page stage order, persisted-storyboard-before-generation rule, quality-before-approval rule, and one-page execution boundary. |
| Architecture Validation v3 | v3 layers are application/DTO-only consumers of existing public ports; v2 Core imports no v3 module and presentation exposes no internal model. |
| Compatibility Validation v3 | v1 through v2.7 root APIs, workflows, CLI, FastAPI, MCP, Web UI, persistence, Plugin, Extension SDK, Provider, and Backend contracts remain unchanged. |
| Director Platform Validation | Project/Creative goals, planning/execution contexts, sessions, and summaries are immutable, one-page scoped, StateMachine-derived, and cannot execute an Agent or transition state. |
| Creative Planning Validation | Story, chapter, page, panel, and timeline DTOs never invoke an image generator, alter Prompt Pipeline behavior, skip a stage, or weaken storyboard/quality guards. |
| Knowledge Foundation Validation | Namespaces, categories, tags, references, snapshots, and indexes use only repository-derived identifiers and metadata keys, redact values, and never mutate persistence. |
| Workflow Intelligence Validation | Dependency, progress, timeline, and recommendation DTOs are diagnostic only, preserve one-page StateMachine order, and cannot schedule, execute, or modify a workflow. |
| Planning Summary Validation | CLI, FastAPI, and MCP render shared DTOs without duplicating workflow rules, exposing internal models, or enabling automatic actions. |
| Multi-Agent Validation | Agent profiles, capabilities, assignments, plans, and coordination reports are advisory, one-page scoped, human-checkpointed, and cannot instantiate, call, or dispatch an Agent. |
| Creative Knowledge Validation | Character, World, Story, Scene, and Asset projections preserve Repository-port semantics, redact metadata values, and never create mutable shared memory. |
| Director Intelligence Validation | Decisions, alternatives, comparisons, risks, and recommendations are explainable diagnostic DTOs that cannot choose an action, invoke a Provider, or alter workflow state. |
| Review Pipeline Validation | Story, storyboard, character/knowledge consistency, and creative-quality reports remain diagnostic; they cannot pass quality, approve a Page, or bypass existing review stages. |
| Knowledge Relationship Validation | Relationship graphs use bounded repository-derived identifiers/tags, include no secret values, perform no persistence mutation, and carry no execution authority. |
| Director Reliability Validation v3 | Session, planning, consistency, strategy, and readiness checks remain one-page, StateMachine-derived, non-executing, and cannot change a workflow. |
| Creative Governance Validation | Policy, standard, compliance, and audit DTOs retain storyboard/quality/approval guards and cannot mutate a creative artifact or grant approval. |
| Knowledge Integrity Validation v3 | Integrity, coverage, lifecycle, quality, governance, and risk evidence remain repository-port-based, metadata-value-redacted, non-mutating, and without automatic remediation. |
| Production Readiness Validation | Deployment/readiness/configuration/operations DTOs expose no values, start no operation, deploy no component, and preserve existing Core boundaries. |
| Release Readiness Validation | Executive dashboards aggregate DTO evidence only; they cannot authorize or automatically create a release. |
| v3 RC1 Architecture Audit | Core remains inward-facing; Director, Creative, Knowledge, Collaboration, Review, and Readiness services are optional Application DTO consumers of existing ports. |
| v3 RC1 Compatibility Audit | v1.x through v2.7.x public Python, CLI, FastAPI, MCP, Workflow, Repository, Plugin, Extension, Provider, Backend, Automation, Notification, and Health contracts are retained. |
| v3 RC1 Workflow Regression | One Page, persisted storyboard, completed quality review, and explicit approval remain StateMachine-enforced for all delivery paths. |
| v3 RC1 Production Smoke | Director, Creative, Knowledge, Multi-Agent, Review, and Readiness reports stay non-executing, non-mutating, and transport-neutral. |
| Creative Collaboration Validation v3.1 | Workspace and hand-off plans preserve human ownership, StateMachine authority, storyboard/quality guards, and contain no Agent invocation, quality pass, or approval authority. |
| Knowledge Evolution Validation v3.1 | Version, diff, merge-plan, snapshot, timeline, and analytics designs remain Repository-port-derived, redacted, bounded, and write-free until separately authorized. |
| Operations Validation v3.1 | Observability, dashboard, quality, release, project, and workflow reports are local DTOs; they cannot collect externally, configure, deploy, schedule, or publish. |
| Architecture Validation v3.1 | v3.1 services are optional application DTO consumers; no Core import, reverse dependency, root-API widening, or adapter-owned workflow rule is allowed. |
| Backward Compatibility Validation v3.1 | v1.x–v3.0 Python API, CLI, FastAPI, MCP, Web UI, Workflow, Repository, Plugin, SDK, Provider, Backend, Automation, Notification, and Health contracts remain unchanged. |

| Operations Foundation Validation v3.1 | Project, workflow, quality, release, health, and project-metric DTOs aggregate local or Repository-port evidence only; they cannot schedule, configure, deploy, publish, approve, or execute. |
| Developer Productivity Validation v3.1 | Project, planning, validation, and workspace templates are descriptor-only; they create no file, persist no workspace, validate no workflow, and contain no automatic action. |
| Project Metrics Validation v3.1 | Aggregate counts retain a single supplied Page context, use no remote collection, and preserve Repository semantics without changing a Project. |
| Creative Review Validation v3.1 | Checklists, findings, and recommendations preserve storyboard, quality, and human-approval guards; they cannot execute review, pass quality, approve, or transition a Page. |
| Knowledge Analytics Validation v3.1 | Coverage, usage, relationships, and baseline trends use bounded Repository-port projections, redact metadata values, and neither persist analytics nor collect externally. |
| Operations Intelligence Validation v3.1 | Efficiency, health, quality, release, and insight DTOs observe only one supplied Page and local aggregate evidence; they cannot start, schedule, configure, deploy, or publish operations. |
| Developer Experience Validation v3.1 | Workspace diagnostics, template recommendations, and configuration-shape health expose no values and cannot generate files, validate a workflow, or apply a configuration change. |
| Workflow Efficiency Validation v3.1 | History/artifact metrics retain the exact one-Page context and cannot dispatch, optimize, or modify the WorkflowEngine. |
| Creative Governance Validation v3.1 | Policy, validation, compliance, and quality-score DTOs preserve storyboard, quality, and human-approval guards; they cannot remediate, approve, or transition a Page. |
| Knowledge Reliability Validation v3.1 | Integrity, consistency, dependency, lifecycle, and reliability evidence remains redacted, Repository-port-based, non-mutating, and without repair or external lookup. |
| Operational Readiness Validation v3.1 | Operation, deployment, configuration-shape, environment, release, and health DTOs cannot deploy, probe externally, change configuration, or start runtime work. |
| Release Quality Validation v3.1 | Quality, gate, regression, production, and release-recommendation DTOs are diagnostic; they cannot enforce a gate, publish, or authorize a release. |
| Compatibility Validation v3.1 | Compatibility DTOs enumerate stable public surfaces without changing Python API, CLI, FastAPI, MCP, Workflow, Repository, or persisted data contracts. |

Mock providers are mandatory for CI. Network calls, real credentials, and
machine-specific performance budgets are excluded from CI. The v2.3 Iteration 1
runtime metadata, profile, lifecycle, and governance fixtures exercise these gates; every future
Provider or backend implementation must extend the same contract tests rather
than bypass them.
