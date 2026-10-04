# v2.3.0 Release Checklist

## Completed locally

- [x] RC1 corrective feedback: measurement batching, observability dependency
  direction, and delivery-scope documentation are resolved without new scope.
- [x] Version alignment: package/root import/MCP/OpenAPI/frontend/SBOM/changelog/
  README/release notes use `2.3.0`.
- [x] Architecture, compatibility, recovery, integrity, diagnostics, enterprise,
  performance, documentation-link, and quality-gate tests pass.
- [x] Ruff, strict mypy, pytest, benchmark smoke, frontend checks, wheel/sdist,
  Twine, clean optional-API install, and dependency audit have passed locally.
- [x] LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, SUPPORTED_VERSIONS,
  MAINTAINERS, GOVERNANCE, roadmap, SBOM, and dependency-license assets exist.

## Required at publication time

- [ ] Confirm hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, diagnostics, and enterprise-smoke jobs for tag `v2.3.0`.
- [ ] Repeat CVE/dependency and secret scans for the exact tag.
- [ ] Publish only signed-off wheel/sdist artifacts and GitHub Release notes.
- [ ] Create the approved Git tag `v2.3.0` and publish matching PyPI artifacts.

## Scope gate

- [x] No new Provider, Backend, Workflow, database, UI redesign, Marketplace,
  Cloud, or distributed workflow was added after RC1.
- [x] FastAPI remains an optional observability-only DTO adapter, not a workflow
  REST service or Web UI backend.
