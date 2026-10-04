# v5.6.0 RC1 Release Checklist

- [x] Dynamic Python version updated to `5.6.0rc1`.
- [x] Frontend metadata updated to `5.6.0-rc.1`.
- [x] SBOM and declared dependency-license report synchronized.
- [x] Story, Character, Page, Review, Export, and integration contracts added.
- [x] Release, integration, compatibility, performance, quality-gate, and known-issues records added.
- [x] Full regression passed in batched execution; Ruff and mypy passed.
- [x] Wheel and sdist built; Twine, local wheel smoke, and `pip check` passed.
- [x] Static Engine-boundary, SBOM, and common-secret-pattern audit passed.
- [ ] Protected CI, external CVE audit, signing, tag creation, GitHub pre-release, and PyPI publication require maintainer authority.

# v5.7.0 RC1 Release Checklist

- [x] Dynamic Python version set to `5.7.0rc1`.
- [x] Frontend metadata set to `5.7.0-rc.1`.
- [x] SBOM and dependency-license declaration synchronized.
- [x] RC release notes, integration, Workspace compatibility, Automation,
  quality-gate, checklist, and known-issues records added.
- [x] Focused and full local quality checks recorded in the v5.7 quality gate.
- [x] Wheel/sdist build, Twine metadata check, wheel zip-import smoke, and
  dependency check recorded.
- [ ] Clean-environment `pip --target` install smoke remains to be rerun; the
  local verification command did not complete.
- [ ] Protected CI, external CVE audit, signing, tag creation, GitHub
  pre-release, and PyPI publication require maintainer authority.

# v6.0.0 RC1 Release Checklist

- [x] Python version is `6.0.0rc1`; Web metadata is `6.0.0-rc.1`.
- [x] SBOM and dependency-license declaration are synchronized.
- [x] RC release, integration, compatibility, governance, observability, and
  known-issues records are present.
- [x] Full regression passes at 94.23% coverage; Ruff and mypy pass.
- [x] Wheel/sdist build and Twine metadata check pass; an isolated wheel
  installation with declared dependencies, CLI/MCP symbol smoke, and `pip check`
  pass.
- [x] Static import-boundary, SBOM, and common secret-pattern audit pass.
- [x] Provider-free Platform Kernel benchmark is recorded in the v6.0 RC1
  quality gate.
- [ ] Protected CI, external CVE audit, signing, tag creation, GitHub
  pre-release publication, and PyPI upload require maintainer authority.

# v6.0.0 Final Release Checklist

- [x] Python and Web package versions are `6.0.0`; OpenAPI and MCP derive the
  same dynamic package version.
- [x] CHANGELOG, README, SBOM, dependency-license declaration, migration,
  release notes, frozen API references, Marketplace specification, and
  Enterprise Deployment Guide are synchronized.
- [x] Platform API v1.0, SDK v1.0, Extension API v1.0, and Marketplace
  Specification v1.0 are documented as additive, read-only stable surfaces.
- [x] Ruff, mypy, full regression (888 tests / 94.23% coverage), architecture
  boundary, SBOM, secret-pattern, and benchmark validations pass.
- [x] Wheel/sdist build, Twine metadata check, clean-environment installation,
  package import, CLI/MCP smoke, and dependency check pass.
- [ ] Protected CI, external CVE audit, signing, tag creation, GitHub
  publication, and PyPI upload require maintainer authority.
