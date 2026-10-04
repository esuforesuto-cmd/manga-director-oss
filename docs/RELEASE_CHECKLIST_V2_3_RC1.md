# v2.3.0 RC1 Release Checklist

## Completed locally

- [x] Version alignment: package, root import, MCP, optional OpenAPI, frontend,
  SBOM, changelog, README, and release notes.
- [x] Architecture, import, dependency, compatibility, documentation-link,
  recovery, integrity, diagnostics, enterprise, and repeatability gates.
- [x] Ruff, strict mypy, pytest, benchmark smoke, CLI, MCP, and package
  metadata review.
- [x] Governance, license, supported-version, security, contribution, and
  release-process assets present.

## Required before publication

- [ ] Confirm hosted CI jobs: backend, frontend, docs, package, security,
  release, nightly, benchmark, diagnostics, and enterprise smoke.
- [ ] Run dependency/CVE and secret scan against the exact RC tag.
- [ ] Build wheel/sdist, run Twine check, and perform clean-install smoke in
  the release environment.
- [ ] Publish only the approved `v2.3.0rc1` tag and matching prerelease assets.

## Scope gate

- [x] No new Workflow, Provider, Image Backend, Cloud, distributed workflow,
  or Marketplace capability was introduced for RC1.
- [x] The optional FastAPI adapter is documented only as DTO-only
  observability delivery; no workflow REST API or Web UI backend is claimed.
