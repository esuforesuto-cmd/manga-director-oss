# v2.6.0 RC1 Release Checklist

## Completed locally

- [x] Version alignment: canonical package source, root import, MCP, optional
  OpenAPI, frontend, SBOM, changelog, README, and RC notes.
- [x] Architecture, compatibility, workflow regression, integrity, recovery,
  diagnostics, planning, reporting, health, production, enterprise,
  documentation-link, security, and benchmark-smoke validation.
- [x] Ruff, strict mypy, pytest/coverage, package build, release-contract, and
  local artifact-validation review.
- [x] Dependency audit found no known vulnerabilities after raising the
  development `pytest` lower bound to `9.0.3`.
- [x] Governance, license, supported-version, security, contribution, and CI
  assets present.

## Required before publication

- [ ] Confirm hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, diagnostics, planning, production, and enterprise CI jobs.
- [ ] Run dependency/CVE and secret scan against the exact RC tag.
- [ ] Build wheel/sdist, run Twine check, and perform a clean-install smoke in
  the release environment.
- [ ] Publish only approved `v2.6.0rc1` prerelease artifacts and tag.

## Scope gate

- [x] No new workflow, provider, image backend, cloud, marketplace,
  distributed-runtime, or autonomous-AI capability was introduced for RC1.
- [x] FastAPI remains DTO-only delivery; it is not a workflow API.
