# v5.1 Planning Quality Gates

| Gate | Pass criteria |
| --- | --- |
| Modularization design validation | Module, pack, registry, profile, and template responsibilities are explicit and non-overlapping. |
| v5.0 LTS compatibility validation | Every proposal is additive, optional, and has a legacy-only fallback. |
| Workflow invariant validation | Documents preserve StateMachine authority and all one-Page, stage, storyboard, and review requirements. |
| Composition safety validation | No planned component dynamically loads, invokes, routes, persists, or approves work. |
| Migration validation | No conversion is required; future adoption and rollback are metadata-only. |
| Documentation validation | Architecture, roadmap, registry, profiles, templates, migration, and report links resolve. |

Implementation may begin only after every design gate has an executable
validation plan reviewed by its owning layer.

## Iteration 1 Foundation evidence

| Gate | Validation |
| --- | --- |
| Capability Registry Validation | Duplicate descriptors are rejected; supplied metadata remains local and non-loading. |
| Feature Pack Validation | Unknown and duplicate capability references fail closed without installation or invocation. |
| Platform Profile Validation | Profiles require a legacy fallback and cannot alter configuration or execution routing. |
| Solution Template Validation | Templates require human review and cannot create projects, start workflows, or automate approval. |
| Composition Engine Validation | Preview combines only supplied metadata, retains StateMachine authority, and records no workflow/service action. |
| v5.0 LTS Compatibility Validation | Existing platform tests remain valid and the SDK method is additive. |

## Iteration 3 composition governance evidence

| Gate | Validation |
| --- | --- |
| Composition Governance Validation | Policy retains StateMachine, one-Page, storyboard, quality-review, and human-review safeguards without enforcement. |
| Capability Governance Validation | Local capability declarations expose ownership and compatibility without loading modules or external auditing. |
| Composition Observability Validation | Supplied metadata yields observations without telemetry, monitoring, alerts, or persistence. |
| Module Lifecycle Validation | Module references remain declared and retain ownership without lifecycle transitions or retention actions. |
| Composition Reliability Validation | Metadata confidence is explicit; health checks, retries, recovery, and reconfiguration remain disabled. |
| v5.0 LTS Compatibility Validation | Existing v5 platform contracts and tests remain valid; SDK maturity preview is additive. |

## v5.1 RC1 release evidence

| Gate | Validation |
| --- | --- |
| RC Readiness Validation | Version, composition contracts, architecture, and local release assets are synchronized. |
| Release Compatibility Validation | v5.0 LTS API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, SDK, Provider, and Backend contracts remain additive. |
| Performance Regression Validation | Existing v5 maturity benchmark remains below its prior local reference; Composition benchmark is local metadata-only. |
| Documentation Validation | RC architecture, compatibility, workflow, benchmark, security, package, checklist, readiness, and release notes are linked. |
| Composable Platform End-to-End Validation | Registry through governance/reliability reports are exercised without runtime or workflow action. |

## v5.1 Final release evidence

| Gate | Validation |
| --- | --- |
| Release Readiness | Final version, release assets, package metadata, and completion reports are synchronized. |
| v5.0 LTS Backward Compatibility | Existing public contracts remain valid; composition is optional with legacy-only fallback. |
| Composition Platform Completion | Registry, pack, profile, template, engine, governance, lifecycle, observability, reliability, and SDK previews are integrated. |
| Performance Regression | Existing v5 maturity benchmark remains comparable to the v5.0 local reference. |
| Documentation and Package Quality | Release links, wheel/sdist metadata, typed marker, license, and local import smoke are verified. |
| Security Validation | Local static boundaries pass; external dependency lookup remains an explicit maintainer gate. |
