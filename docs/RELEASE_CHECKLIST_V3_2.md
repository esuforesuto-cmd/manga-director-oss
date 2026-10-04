# v3.2.0 Release Checklist

## Completed Locally

- [x] Canonical version, root import, MCP, optional OpenAPI, frontend, SBOM,
  README, changelog, and stable release notes are aligned.
- [x] Architecture, compatibility, workflow regression, Creative Studio, Asset
  Intelligence, Workflow Profiles, Production Analytics, diagnostics,
  reporting, security, package, migration, and readiness evidence is
  documented.
- [x] Ruff, strict mypy, pytest, coverage, frontend lint/typecheck/test/build,
  wheel/sdist, Twine, clean-install CLI/MCP smoke, representative examples,
  and direct Python/frontend dependency audits pass.
- [x] Governance, license, supported-version, security, contribution,
  CODEOWNERS, and CI assets are present.

## Required Before Publication

- [ ] Confirm hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, Creative Studio, Asset Intelligence, Workflow Profiles,
  Production Analytics, diagnostics, reporting, production, and enterprise jobs
  on tag `v3.2.0`.
- [ ] Run hosted dependency/CVE and secret scans against the exact release tag.
- [ ] Repeat package validation in the tagged release environment.
- [ ] Publish approved wheel/sdist and create the GitHub Release for `v3.2.0`.

## Scope Gate

- [x] No new workflow, Provider, Backend, autonomous AI, Cloud, marketplace,
  distributed runtime, or breaking public contract was introduced.
