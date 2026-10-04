# v4.2.0 RC1 Release Checklist

## Completed locally

- [x] Canonical Python, OpenAPI, and MCP version is `4.2.0rc1`.
- [x] Frontend prerelease metadata is `4.2.0-rc.1`.
- [x] Changelog, README, SBOM, dependency-license report, RC notes, and audit
  records are updated.
- [x] Regression, compatibility, architecture, integration, benchmark smoke,
  documentation, and local safety-boundary tests pass.
- [x] Ruff and mypy pass.
- [x] Built `4.2.0rc1` wheel/sdist and passed Twine metadata validation.
- [x] Verified `py.typed`, package metadata, dependency-license report, and MIT
  License are present in the release artifacts.
- [x] Ran local dependency vulnerability audit; no known vulnerabilities were
  reported for auditable installed dependencies.

## Required before publication

- [ ] Run exact-tag hosted backend, frontend, docs, package, security, and
  release workflows.
- [ ] Run dependency/CVE and secret scans against resolved release artifacts.
- [ ] Rebuild wheel/sdist and validate metadata in the exact-tag release environment.
- [ ] Run clean-install CLI, FastAPI, and MCP smoke tests from the artifacts.
- [ ] Approve GitHub prerelease publication and tag `v4.2.0rc1`.
