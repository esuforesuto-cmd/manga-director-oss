# v4.3.0 RC1 Release Checklist

## Completed locally

- [x] Canonical Python, OpenAPI, and MCP version is `4.3.0rc1`.
- [x] Frontend prerelease metadata is `4.3.0-rc.1`.
- [x] Changelog, README, SBOM, dependency-license report, RC notes, and audit
  records are updated.
- [x] Regression, compatibility, architecture, integration, benchmark smoke,
  documentation, and local safety-boundary tests pass.
- [x] Ruff and mypy pass.
- [x] Local dependency audit reports no known vulnerabilities (the editable
  package itself is skipped because it is not published on PyPI).
- [x] Wheel and sdist build; Twine metadata, typed-marker, and MIT License
  checks pass.
- [x] The wheel installs without dependencies into an isolated artifact target;
  package import, v4.3 export, and CLI help smoke pass from outside the source tree.

## Required before publication

- [ ] Run exact-tag hosted backend, frontend, docs, package, security, and
  release workflows.
- [ ] Run dependency/CVE and secret scans against resolved exact-tag release artifacts.
- [ ] Run a dependency-resolving clean-install CLI, FastAPI, and MCP smoke test
  in the exact-tag release environment.
- [ ] Approve GitHub prerelease publication and tag `v4.3.0rc1`.
