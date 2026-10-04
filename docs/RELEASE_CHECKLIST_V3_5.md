# v3.5.0 Release Checklist

## Completed Locally

- [x] Canonical version, root export, dynamic pyproject package metadata, MCP,
  optional OpenAPI, frontend, SBOM, README, changelog, and release notes align.
- [x] Architecture, compatibility, workflow regression, Unified Knowledge
  Graph, Creative Intelligence, Production Intelligence, Platform Analytics,
  Governance, diagnostics, reporting, security, package, and migration
  evidence is documented.
- [x] Ruff, strict mypy, pytest, benchmark smoke, frontend typecheck/test/build,
  wheel/sdist, Twine, clean-install CLI/MCP smoke, and dependency audit pass in
  mock-only local validation.
- [x] License, contribution, conduct, security, support, maintainers,
  governance, roadmap, and CODEOWNERS assets are present.

## Required Before Publication

- [ ] Confirm hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, production, diagnostics, reporting, and Governance jobs
  on tag `v3.5.0`.
- [ ] Run hosted dependency/CVE and secret scans against the exact release tag.
- [ ] Repeat package validation in the tagged release environment.
- [ ] Publish approved wheel/sdist and create the GitHub Release for `v3.5.0`.

## Scope Gate

- [x] No new workflow, Provider, Backend, autonomous AI, Cloud, marketplace,
  distributed runtime, or breaking public contract was introduced.
