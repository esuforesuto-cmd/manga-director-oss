# v3.1.0 Release Checklist

## Completed Locally

- [x] Canonical version, root import, MCP, optional OpenAPI, frontend, SBOM,
  README, changelog, and stable release notes are aligned.
- [x] Architecture, compatibility, workflow regression, Creative, Knowledge,
  Operations, Developer Productivity, diagnostics, reporting, security,
  package, migration, and readiness evidence is documented.
- [x] Ruff, strict mypy, pytest, frontend lint/typecheck/test/build, wheel/sdist,
  Twine, clean-install CLI/MCP smoke, and direct Python/frontend dependency
  audits pass.
- [x] Governance, license, supported-version, security, contribution, and CI
  assets are present.

## Required Before Publication

- [ ] Confirm hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, Creative, Knowledge, Operations, DX, diagnostics,
  reporting, production, and enterprise jobs on tag `v3.1.0`.
- [ ] Run hosted dependency/CVE and secret scans against the exact release tag.
- [ ] Repeat package validation in the tagged release environment.
- [ ] Publish approved wheel/sdist and create the GitHub Release for `v3.1.0`.

## Scope Gate

- [x] No new workflow, Provider, Backend, autonomous AI, Cloud, marketplace,
  distributed runtime, or breaking public contract was introduced.
