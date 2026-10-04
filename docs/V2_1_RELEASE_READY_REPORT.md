# manga-director v2.1.0 Release Ready Report

## Release decision

**v2.1.0 is ready for GitHub and PyPI publication for all shipped surfaces.**
It is the stable promotion of RC1 and adds no new product feature or workflow
behavior.

## RC feedback disposition

| RC feedback | Resolution |
| --- | --- |
| Keep version metadata consistent across delivery surfaces | Python has one `_version.py` source; `__init__` and MCP import it. Frontend and SBOM use the matching stable release value. |
| Verify built distribution contents | Wheel/sdist, `py.typed`, built-in Plugin package, CLI, local MCP, and Plugin command clean-install checks pass. |
| Clarify unavailable delivery scope | FastAPI/OpenAPI and Automation remain explicitly documented as not shipped, rather than represented as validated APIs. |

## Verification summary

- Ruff: passed.
- Strict mypy: 104 source files passed.
- pytest: 121 passed with 84.89% coverage (80% gate).
- Architecture, import, dependency, documentation-link, public API, state,
  workflow, persistence, resume, batch, security, MCP, Plugin, SDK, and
  package-contract regressions: passed.
- Provider-free performance and benchmark smoke: passed with no regression
  observed against the retained v2.0 baseline artifact.
- Frontend lint, typecheck, unit test, and production build: passed.
- wheel/sdist build, Twine check, content check, clean install, CLI/MCP/Plugin
  startup, SQLite migration, dependency audit, SBOM, and license report: passed.

Hosted GitHub Actions remain the final external publication gate because they
cannot be asserted from a local checkout.

## Compatibility

The v1.x and v2.0 shipped Python API, CLI, local MCP, Plugin, Extension SDK,
Repository, and one-page Workflow contracts are preserved. See
[Compatibility Audit](COMPATIBILITY_V2_1.md). FastAPI/REST and Automation have
no shipped implementation in either baseline and are therefore out of scope,
not compatibility failures.

## Self review

| Area | Score | Basis |
| --- | --- | --- |
| Architecture | 5/5 | Dependency direction and page-engine responsibility tests pass. |
| Backward compatibility | 5/5 | Documented v1.x/v2.0 shipped contracts are unchanged. |
| Performance | 4/5 | Local provider-free comparison has no regression; controlled p95 data is future work. |
| Security | 4/5 | Dependency audit, validation, masking, audit controls, and CI scans pass. |
| Maintainability | 5/5 | Typed code, release contracts, coverage gate, and focused boundaries are enforced. |
| Documentation | 5/5 | Release, migration, compatibility, scope caveats, governance, FAQ, and troubleshooting are current. |
| Developer experience | 5/5 | Reproducible local commands and cached CI quality gates are documented. |
| OSS readiness | 5/5 | License, contribution, conduct, security, governance, maintainers, roadmap, SBOM, and license report are present. |
| Release quality | 5/5 | Build, clean-install, static, test, frontend, security, and documentation gates pass locally. |

No category is below 4/5.

## Publication steps

1. Push the reviewed commit and create signed/approved tag `v2.1.0`.
2. Confirm the hosted CI and release workflows are green.
3. Upload the validated wheel and sdist to PyPI.
4. Create the GitHub Release using [RELEASE_V2_1.md](../RELEASE_V2_1.md) as
   its body and attach release artifacts as appropriate.
