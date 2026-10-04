# v2.5.0 Release Checklist

## Completed locally

- [x] Version alignment: canonical package source, root import, MCP, optional
  OpenAPI, frontend, SBOM, changelog, README, and release notes use `2.5.0`.
- [x] Architecture, compatibility, workflow, recovery, integrity, diagnostics,
  reporting, health, production, enterprise, documentation-link, and benchmark
  smoke validation passed.
- [x] Ruff, strict mypy, pytest/coverage, package build, Twine metadata check,
  clean-install smoke, and release-contract review passed.
- [x] Governance, license, supported-version, security, contribution, CI, and
  release assets are present.

## Required before publication

- [ ] Confirm hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, diagnostics, production, and enterprise CI jobs.
- [ ] Run dependency/CVE and secret scan against the exact `v2.5.0` tag.
- [ ] Publish approved `v2.5.0` artifacts and verify PyPI/GitHub metadata.

## Scope gate

- [x] No new workflow, Provider, Image Backend, Cloud, Marketplace, distributed
  runtime, Core architecture, or breaking change was introduced for v2.5.0.
- [x] FastAPI remains DTO-only observability delivery; it is not a workflow API.
