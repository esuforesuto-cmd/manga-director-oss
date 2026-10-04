# v3.0.0 Release Checklist

## Completed locally

- [x] Version alignment: canonical package source, root import, MCP, optional
  OpenAPI, frontend, SBOM, changelog, README, and release notes.
- [x] Architecture, compatibility, workflow regression, planning, Director,
  Creative, Knowledge, Multi-Agent, Review, integrity, diagnostics, reporting,
  health, production, enterprise, documentation-link, security, and benchmark
  validation.
- [x] Ruff, strict mypy, pytest, package build, release-contract, local
  artifact-validation, and frontend lint/typecheck/test/build review.
- [x] Governance, license, supported-version, security, contribution, and CI
  assets present.

## Required before publication

- [ ] Confirm hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, planning, knowledge, director, creative, review,
  diagnostics, reporting, production, and enterprise CI jobs.
- [ ] Run dependency/CVE and secret scans against the exact release tag.
- [ ] Perform a clean-install smoke in the release environment.
- [ ] Publish approved wheel/sdist and create the GitHub Release for `v3.0.0`.

## Scope gate

- [x] No new workflow, Provider, Image Backend, autonomous AI, Cloud,
  marketplace, distributed-runtime, or breaking capability was introduced.
- [x] FastAPI remains DTO-only delivery; it is not a workflow API.
