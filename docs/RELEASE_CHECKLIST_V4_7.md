# v4.7.0 Release Checklist

## Completed local release validation

- [x] Stable version synchronized to `4.7.0` across Python, OpenAPI, MCP, SBOM, and frontend metadata.
- [x] RC feedback review identified no source change beyond release metadata and assets.
- [x] Regression, compatibility, integration, Decision Platform end-to-end, benchmark, security, package, and documentation checks pass.
- [x] Ruff, mypy, Web UI type validation, and Web UI tests pass.
- [x] Wheel/sdist, Twine, typed-marker/license, and installed-wheel smoke pass.
- [x] Release notes, migration, SBOM, dependency-license report, quality gates, and README are synchronized.

## Maintainer-controlled publication

- [ ] Confirm protected CI for the final tagged commit.
- [ ] Create and sign the `v4.7.0` tag.
- [ ] Publish [GitHub release notes](GITHUB_RELEASE_V4_7.md).
- [ ] Upload signed artifacts to PyPI after final approval.

The unchecked publication steps require repository credentials and release
authority not available to local validation.
