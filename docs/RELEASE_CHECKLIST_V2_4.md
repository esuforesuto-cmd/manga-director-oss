# v2.4.0 Release Checklist

## Completed locally

- [x] RC1 feedback was handled as release-process clarification only; no
  product scope, provider, backend, workflow, or architecture change was made.
- [x] Version alignment: package/root import/MCP/OpenAPI/frontend/SBOM/changelog/
  README/release notes use `2.4.0`.
- [x] Architecture, compatibility, recovery, integrity, diagnostics, health,
  production, enterprise, performance, documentation-link, and quality-gate
  tests pass.
- [x] Ruff, strict mypy, pytest, benchmark smoke, frontend checks, wheel/sdist,
  Twine, and clean package installation pass locally.
- [x] LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SUPPORTED_VERSIONS,
  MAINTAINERS, GOVERNANCE, roadmap, SBOM, dependency-license, migration,
  production deployment, and operations assets exist.

## Required at publication time

- [ ] Confirm hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, diagnostics, production-smoke, and enterprise-smoke jobs
  are green for tag `v2.4.0`.
- [ ] Repeat CVE/dependency and secret scans in the clean hosted release
  environment for the exact tag.
- [ ] Publish only signed-off wheel/sdist artifacts and GitHub Release notes.
- [ ] Create the approved Git tag `v2.4.0` and publish matching PyPI artifacts.

## Scope gate

- [x] No new Provider, Backend, Workflow, database, UI redesign, Marketplace,
  Cloud, or distributed runtime was added after RC1.
- [x] FastAPI remains an optional observability-only DTO adapter, not a workflow
  REST service or Web UI backend.
