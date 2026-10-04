# v2.1.0 RC1 Readiness Report

## Release candidate result

**RC1 is ready for GitHub publication for the shipped Core, CLI, local MCP,
Plugin, Repository, and Web UI build/test surfaces.** It is backward
compatible with the documented v2.0 contracts and carries no new product
feature.

## Audit summary

| Area | Score | Evidence |
| --- | --- | --- |
| Architecture | 4/5 | Domain and Page-engine boundary tests pass; architecture audit documents repository-port and presentation boundaries. |
| API | 4/5 | Root Python API, CLI, MCP DTOs, errors, and version metadata are contract-tested. |
| Workflow | 5/5 | State-machine, project/chapter/page, persistence, resume, batch, and explicit approval regressions pass. |
| Performance | 4/5 | Same-environment v2.0.0rc1-to-RC1 smoke comparison found no regression; see the benchmark report. |
| Security | 4/5 | Runtime dependency audit and secret-pattern scan pass; CI adds pip-audit and Gitleaks. |
| Documentation | 4/5 | README, public API, compatibility, troubleshooting, migration, SBOM, license, and release notes are current. |
| DX | 4/5 | Cached CI, Make/Task commands, clean wheel validation, and frontend scripts are available. |
| Maintainability | 4/5 | Ruff, strict mypy, 80% coverage gate, release contracts, and package-content validation are configured. |
| OSS readiness | 4/5 | Governance, conduct, security, supported-version, maintainer, contribution, and release assets are present. |

No area is below 4/5. The ratings intentionally do not score unimplemented
surfaces as shipped capabilities.

## Verification

- Ruff and strict mypy pass.
- Unit, integration, contract, architecture, compatibility, security, and
  benchmark-smoke tests pass under pytest (121 tests; 84.89% coverage against
  the 80% release gate).
- The test suite includes project/chapter/page workflow, explicit approval,
  save/reload/resume, batch, notification provider behavior, MCP, Plugin, and
  Extension-SDK compatibility checks.
- Wheel/sdist build, Twine metadata check, clean wheel installation, CLI/MCP/
  Plugin command startup, and SQLite Alembic migration pass.
- Frontend lint, typecheck, unit test, and production build pass.
- The local one-run benchmark comparison is recorded in
  [Benchmark v2.1 RC1](BENCHMARK_V2_1_RC1.md); it is a regression smoke check,
  not a statistically significant performance claim.

## Scope caveat

FastAPI/OpenAPI and Automation do not exist in the checked source baseline;
their startup, REST DTO, or execution checks are therefore correctly marked
not applicable rather than fabricated. The Web UI is not a bundled HTTP server
client release. These are existing product-scope gaps, not RC regressions.

## Final publishing gate

Publish RC1 only after the hosted GitHub Actions jobs complete successfully.
The final v2.1.0 decision must accept the documented FastAPI/Automation scope
limitation or defer the final release until a separately approved feature phase
implements those surfaces.
