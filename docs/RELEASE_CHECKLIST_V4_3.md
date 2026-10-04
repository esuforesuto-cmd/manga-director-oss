# v4.3.0 Release Checklist

## Completed locally

- [x] Canonical Python, OpenAPI, and MCP version is `4.3.0`.
- [x] Frontend metadata, SBOM, dependency-license report, README, changelog,
  migration guide, release notes, and release assets are updated.
- [x] Full unit, integration, contract, architecture, compatibility,
  documentation, security-boundary, and v4.3 end-to-end checks pass.
- [x] Provider-free benchmark smoke completed without a corrective regression.
- [x] Ruff and mypy pass.
- [x] Local dependency audit reported no known vulnerabilities for auditable
  installed dependencies.
- [x] Built wheel/sdist, passed Twine metadata validation, and verified
  `py.typed` and MIT License inclusion.
- [x] Installed the wheel without dependencies into an isolated artifact target;
  package import, v4.3 export, CLI, FastAPI, and MCP smoke passed outside the
  source tree using already-installed validation dependencies.

## Required before publication

- [ ] Run exact-tag hosted backend, frontend, docs, package, security, release,
  diagnostics, and smoke workflows.
- [ ] Run resolved-artifact dependency/CVE and secret scans.
- [ ] Run a dependency-resolving clean-install CLI, FastAPI, and MCP smoke test.
- [ ] Approve GitHub release and tag `v4.3.0`.
- [ ] Approve PyPI publication.
