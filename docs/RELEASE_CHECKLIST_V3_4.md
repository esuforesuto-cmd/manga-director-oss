# v3.4.0 Release Checklist

## Completed Locally

- [x] Canonical version, root import, `__init__` re-export, pyproject dynamic
  version, MCP, optional OpenAPI, frontend, SBOM, README, changelog, and stable
  release notes are aligned.
- [x] Architecture, compatibility, workflow regression, Knowledge Platform,
  Production Operations, Organization Intelligence, Release Intelligence,
  Governance, diagnostics, reporting, security, package, migration, deployment,
  and operations evidence is documented.
- [x] Ruff, strict mypy, pytest, benchmark smoke, frontend lint/typecheck/test/
  build, wheel/sdist, Twine, clean-install CLI/MCP smoke, and dependency audits
  pass in mock-only local validation.
- [x] License, contribution, conduct, security, support, maintainers,
  governance, roadmap, and CODEOWNERS assets are present.

## Required Before Publication

- [ ] Confirm hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, production, enterprise, Knowledge Platform, Production
  Operations, Organization Intelligence, Release Intelligence, Governance,
  diagnostics, and reporting jobs on tag `v3.4.0`.
- [ ] Run hosted dependency/CVE and secret scans against the exact release tag.
- [ ] Repeat package validation in the tagged release environment.
- [ ] Publish approved wheel/sdist and create the GitHub Release for `v3.4.0`.

## Scope Gate

- [x] No new workflow, Provider, Backend, autonomous AI, Cloud, marketplace,
  distributed runtime, or breaking public contract was introduced.
