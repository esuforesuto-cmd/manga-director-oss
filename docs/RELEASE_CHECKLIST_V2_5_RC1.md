# v2.5.0 RC1 Release Checklist

## Completed locally

- [x] Version alignment: canonical package source, root import, MCP, optional
  OpenAPI, frontend, SBOM, changelog, README, and RC notes.
- [x] Architecture, compatibility, workflow, repository integrity, recovery,
  diagnostics, reporting, health, production, enterprise, documentation-link,
  and benchmark-smoke validation.
- [x] Ruff, strict mypy, pytest/coverage, package build, release-contract, and
  local artifact-validation review.
- [x] Governance, license, supported-version, security, contribution, and CI
  assets present.

## Required before publication

- [ ] Confirm hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, diagnostics, production, and enterprise CI jobs.
- [ ] Run dependency/CVE and secret scan against the exact RC tag.
- [ ] Build wheel/sdist, run Twine check, and perform a clean-install smoke in
  the release environment.
- [ ] Publish only approved `v2.5.0rc1` prerelease artifacts and tag.

## Scope gate

- [x] No new workflow, provider, image backend, cloud, marketplace, or
  distributed-runtime capability was introduced for RC1.
- [x] FastAPI remains DTO-only observability delivery; it is not a workflow API.
