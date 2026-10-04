# v2.4.0 RC1 Readiness Report

## Release decision

**v2.4.0rc1 is ready for GitHub/PyPI prerelease publication, subject to hosted
CI and publication-time dependency/CVE and secret-scan evidence on the RC tag.**

## Audit evidence

| Audit | Result |
| --- | --- |
| Architecture | Layer direction, Core isolation, Repository port, Provider/Backend runtime, Plugin/SDK, Application, Infrastructure, and Presentation boundaries verified. |
| Compatibility | v1.x and v2.0–v2.3 public contracts retained; v2.4 additions are optional diagnostic/helper layers. |
| Workflow | One-page workflow, approval, save/reload/resume, Project/Chapter/Batch, automation, notification, Plugin, Extension, CLI, MCP, Web UI, production diagnostics, and health monitoring use established application boundaries. |
| Performance | Provider-free benchmark/repeatability smoke completes without an identified local regression. |
| Reliability | Workflow/Repository recovery, integrity, health, diagnostics, recovery validation, long-running stability, graceful shutdown, and configuration validation are covered. |
| Security | Secret/configuration controls, webhook/SSRF/input/output/manifest checks, rate limit, audit, and dependency/secret-scan CI gates are retained. |
| Package | Typed package, optional extras, README, license, SBOM, dependency license report, and release metadata are aligned. |
| Documentation | README, architecture, production/runtime/operations/reliability/recovery/diagnostics/health, migration, FAQ, troubleshooting, examples, and links audited. |

## Final local validation

- Ruff passed across the repository; strict mypy passed for 123 source modules.
- Full pytest passed: 174 tests with 86.67% total coverage (minimum: 80%).
- Architecture, release-contract, documentation-link, compatibility, security,
  recovery, diagnostics, production, and enterprise fixtures passed.
- Provider-free benchmark smoke and v2.4 recovery/long-running diagnostics
  scenarios completed without network calls or workflow execution.
- Frontend lint, typecheck, Vitest (4 tests), and optimized production build
  passed at npm version `2.4.0-rc.1`.
- Wheel and sdist built as `manga_director-2.4.0rc1`; Twine metadata checks and
  a clean virtual-environment install/import check passed.
- Optional FastAPI/OpenAPI version remains code-derived from the package source;
  the optional `api` extra was not installed in this local verification host.
- The local `pip-audit` host scan could not complete because the bundled Codex
  runtime includes non-PyPI `artifact_tool_v2`; it produced no project dependency
  finding. The clean CI security job is the authoritative dependency/CVE gate.

Hosted CI and live dependency/CVE and secret scans remain publication-time gates
for the exact RC tag.

## Final review

| Area | Score | Rationale |
| --- | ---: | --- |
| Architecture | 5/5 | Core remains inward-facing; outer diagnostics compose stable ports. |
| Performance | 4/5 | Provider-free smoke coverage is broad; production workload SLOs remain deferred. |
| Reliability | 5/5 | Recovery/integrity/readiness/long-running DTO evidence is additive and tested. |
| Security | 4/5 | Local controls and CI audit gates remain; hosted scans are still required. |
| Production readiness | 4/5 | Startup, health, operations, recovery, and checklists are present; deployment automation is deferred. |
| Enterprise readiness | 4/5 | Profiles, governance, repository/runtime evidence, and diagnostics are present; cloud operations remain out of scope. |
| Documentation | 5/5 | Release boundaries and operational guidance are cross-linked. |
| Developer experience | 5/5 | Typed APIs, examples, benchmarks, tests, CI, and release assets are maintained. |
| Backward compatibility | 5/5 | No removal, workflow semantic change, or protocol modification was found. |
| OSS readiness | 5/5 | Governance, security, contribution, packaging, and release controls are present. |

## Known issues

- Hosted CI, dependency/CVE audit, secret scan, and upload verification must run
  on the exact RC tag before publication.
- Non-mock adapters, cloud monitoring, distributed runtime, and marketplace work
  remain intentionally outside v2.4 RC1 scope.
