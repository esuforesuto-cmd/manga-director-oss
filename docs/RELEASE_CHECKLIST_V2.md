# v2.2.0 Release Checklist

## Automated in CI

- [x] Ruff, strict mypy, pytest, architecture/import/dependency/doc-link, and
  benchmark smoke checks are configured.
- [x] Python 3.11/3.12 test matrix and coverage XML artifact are configured.
- [x] Frontend lint, typecheck, unit test, and production build are configured.
- [x] Package build and wheel-install smoke validation are configured.

## Completed locally for v2.2.0

- [x] Run the full supported workflow in a clean release environment.
- [x] Verify package wheel/sdist, `py.typed`, CLI entry point, MCP stdio
  initialization, local plugin loading, and SQLite migration.
- [x] Review dependency audit, secret scan, SBOM, and license report.
- [x] Confirm release notes, migration guide, supported versions, and security
  policy are current.
- [x] Validate the final release notes, compatibility audit, benchmark report,
  architecture summary, and GitHub Release body.

## Required at publication time

- [ ] Confirm hosted backend, frontend, package, security, nightly, and release
  workflows are green for the `v2.2.0` tag.
- [ ] Publish only the approved `v2.2.0` tag and matching PyPI artifacts.

## Baseline scope gate

- [x] Do not claim FastAPI, OpenAPI, or Automation validation: those runtimes
  are absent from this source baseline and require a separate feature release.
