# v4.5.0 Release Checklist

## Completed locally

- [x] Canonical Python, OpenAPI, MCP, frontend, SBOM, and license-report version is `4.5.0`.
- [x] README, changelog, release notes, migration guide, architecture, compatibility, security, package, and readiness records are updated.
- [x] Full unit, integration, contract, architecture, compatibility, documentation, security-boundary, and v4.5 Ecosystem end-to-end checks pass.
- [x] Provider-free benchmark validation completed without a corrective regression.
- [x] Ruff and mypy pass for production source and final release checks.
- [x] Local dependency audit reported no known vulnerabilities for auditable installed dependencies.
- [x] Wheel/sdist build, Twine validation, typed marker, license inclusion, and installed-wheel smoke pass.

## Required before publication

- [ ] Run exact-tag hosted backend, frontend, docs, package, security, release, diagnostics, and smoke workflows.
- [ ] Run resolved-artifact dependency/CVE and secret scans.
- [ ] Run a dependency-resolving clean-install CLI, FastAPI, and MCP smoke test.
- [ ] Approve and create the GitHub release/tag `v4.5.0`.
- [ ] Approve PyPI publication.

Hosted actions require an exact pushed commit/tag and maintainer credentials.
