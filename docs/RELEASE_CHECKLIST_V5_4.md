# v5.4.0 Release Checklist

## Repository completion

- [x] Canonical Python and frontend versions are `5.4.0`.
- [x] CHANGELOG, README, migration guide, architecture summary, SBOM, and license report are synchronized.
- [x] No new product feature was introduced after RC1.
- [x] Quality Framework remains diagnostic and human-gated.

## Local validation

- [x] Full Python regression: 744 tests passed.
- [x] Static validation: Ruff passed; MyPy passed for 202 source files.
- [x] Wheel and sdist built; both passed `twine check`.
- [x] Dependency-resolved package smoke: import, CLI, MCP initialization, and `pip check` passed.
- [x] Quality benchmark completed in 0.023572 s for 1,000 projections.
- [x] Web lint, TypeScript check, and production build passed.

## Maintainer publication controls

- [ ] Approved external CVE audit.
- [ ] Hosted Web test environment repair and test execution.
- [ ] Protected CI checks, release signing, and tag creation.
- [ ] GitHub release publication.
- [ ] PyPI upload.

The final controls require maintainer credentials or explicit external authorization; they are not performed by local source changes.
