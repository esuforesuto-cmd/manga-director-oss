# manga-director v2.2.0 RC1 Readiness Report

## Release decision

**v2.2.0rc1 is a GitHub/PyPI-ready release candidate for every shipped
surface, subject to the hosted CI checks for the release tag.** It introduces
no new workflow or product capability during the RC cycle.

## Architecture audit

| Boundary | RC1 finding |
| --- | --- |
| Domain and Workflow | `StateMachine` remains the source of truth for forward-only, one-page transitions. `Director` coordinates; `WorkflowEngine` executes. |
| Application | CLI and MCP compose application services and DTOs; neither embeds workflow transition logic. |
| Infrastructure | Local-file and SQLAlchemy adapters implement Repository ports; generator, LLM, EventBus, Plugin, and SDK integrations stay behind interfaces. |
| Presentation | The Web UI is independent. No FastAPI/OpenAPI runtime is present, so there is no unshipped REST surface to validate. |
| Plugin and SDK | Manifests, registries, validators, loaders, and lifecycle errors stay outside Core. |

Import, dependency-direction, architecture, public-export, and page-invariant
tests enforce these findings. No circular or reverse Core dependency was
identified by the RC suite.

## Compatibility

The documented v1.x, v2.0.0, and v2.1.0 public Python API, CLI, local MCP,
workflow, Repository, Plugin API, and Extension SDK remain compatible. The
detail is recorded in [the compatibility audit](COMPATIBILITY_V2_2_RC1.md).
Diagnostics, health, integrity, and recovery entry points are additive.

## Verification summary

- Ruff and strict mypy: passed.
- Unit, integration, contract, E2E-style workflow, architecture,
  compatibility, security, recovery, diagnostics, and benchmark-smoke tests:
  passed (138 tests, 85.07% coverage; 80% gate).
- Frontend lint, typecheck, unit test, and production build: passed.
- Provider-free benchmark and repeatability smoke: passed against retained
  v2.1 thresholds; see [benchmark comparison](BENCHMARK_V2_2_RC1.md).
- Wheel/sdist, Twine metadata, typed marker, package exports, SBOM,
  dependency-license report, wheel-install CLI/MCP smoke, Plugin inclusion,
  Extension checks, and SQLite migration SQL compilation: passed.
- `pip-audit --strict .` and `npm audit --omit=dev --audit-level=high` found
  no known vulnerabilities. Secret scanning remains a hosted CI release gate.
  Hosted CI is the final publication authority and must run against the RC tag.

## Scope caveats

FastAPI/OpenAPI and Automation are not shipped runtimes in this source
baseline. They are deliberately excluded from the local compatibility and E2E
claims. Network-backed image and LLM providers remain intentional adapter
stubs. No parallel or distributed execution is introduced.

## Final self review

| Area | Score | Evidence |
| --- | --- | --- |
| Architecture | 5/5 | Layer, import, dependency, and workflow-invariant checks pass. |
| Performance | 4/5 | Threshold and repeatability smoke pass; controlled median/p95 studies remain future work. |
| Reliability | 5/5 | Recovery, integrity, health, diagnostics, and retry paths are covered. |
| Security | 4/5 | Validation, masking, audit, rate-limit, manifest checks, and CI audit gates remain in place. |
| Documentation | 5/5 | README, release notes, compatibility, performance, recovery, diagnostics, FAQ, and troubleshooting are current. |
| Developer experience | 5/5 | Unified local commands, fixtures, examples, release contracts, and CI lanes are documented. |
| Maintainability | 5/5 | Typed interfaces, stable public exports, focused adapters, and regression gates are retained. |
| Backward compatibility | 5/5 | No documented shipped entry point was removed or renamed. |
| OSS readiness | 5/5 | Governance, security, contribution, support, SBOM, license report, and RC assets are present. |

No score is below 4/5.

## Remaining improvements after v2.2

1. Establish controlled multi-run median/p95 performance baselines.
2. Add real network-provider integration tests only when provider adapters are
   intentionally implemented.
3. Deliver any FastAPI/Automation runtime through a separately reviewed
   feature release, not through RC scope expansion.
