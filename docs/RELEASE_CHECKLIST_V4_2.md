# v4.2.0 Release Checklist

## Completed locally

- [x] Canonical Python, OpenAPI, and MCP version is `4.2.0`.
- [x] Frontend metadata, SBOM, dependency-license report, README, changelog,
  migration guide, release notes, and release assets are updated.
- [x] Full unit, integration, contract, architecture, compatibility,
  documentation, security-boundary, and v4.2 end-to-end checks pass.
- [x] Provider-free benchmark smoke completed without a corrective regression.
- [x] Ruff and mypy pass.
- [x] Local dependency audit reported no known vulnerabilities for auditable
  installed dependencies.
- [x] Built wheel/sdist, passed Twine metadata validation, and verified
  `py.typed` and MIT License inclusion.
- [x] Installed the wheel with the `api` extra in a fresh environment; package
  import, CLI, FastAPI, and MCP smoke passed.

## Required before publication

- [ ] Run exact-tag hosted backend, frontend, docs, package, security, release,
  diagnostics, and smoke workflows.
- [ ] Run resolved-artifact dependency/CVE and secret scans.
- [ ] Approve GitHub release and tag `v4.2.0`.
- [ ] Approve PyPI publication.
