# v4.1.0 Release Checklist

## Completed locally

- [x] Canonical version, dynamic package metadata, OpenAPI, MCP, frontend, SBOM,
  README, CHANGELOG, release notes, and release assets align.
- [x] Unit, integration, contract, architecture, compatibility, performance,
  benchmark, security-boundary, documentation, and production-smoke checks pass.
- [x] Ruff, mypy, wheel/sdist, Twine metadata, and local package-install smoke pass.
- [x] License, contribution, conduct, security, support, maintainers, governance,
  roadmap, and dependency-license assets are present.

## Required before publication

- [ ] Confirm hosted CI on tag `v4.1.0`.
- [ ] Run hosted dependency/CVE and secret scans against the exact tag.
- [ ] Review resolved dependency licenses in the tagged environment.
- [ ] Rebuild artifacts from the approved release commit.
- [ ] Publish approved wheel/sdist and create the GitHub Release for `v4.1.0`.

## Scope gate

- [x] No new execution authority, workflow, Provider, Backend, autonomous AI,
  Cloud, marketplace, distributed runtime, or breaking public contract was
  introduced after RC1.
