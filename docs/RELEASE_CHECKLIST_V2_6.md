# v2.6.0 Release Checklist

## Completed locally

- [x] Canonical package version, root import, MCP, optional OpenAPI, frontend,
  SBOM, README, changelog, and release notes aligned to `2.6.0`.
- [x] Architecture, compatibility, workflow, recovery, planning, diagnostics,
  reporting, health, production, enterprise, documentation, security, and
  benchmark evidence reviewed.
- [x] Pytest, Ruff, mypy, package build, Twine metadata validation, clean
  install, frontend checks, and dependency audit completed in mock-only mode.
- [x] Governance, license, contribution, security, supported-version, and
  CODEOWNERS assets present.

## Required for publication

- [ ] Verify hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, planning, diagnostics, reporting, production, and
  enterprise jobs for tag `v2.6.0`.
- [ ] Run hosted dependency/CVE and secret scans for the exact tag.
- [ ] Publish approved wheel/sdist and create the GitHub Release for `v2.6.0`.
