# v5.6 RC1 Quality Gate Report

## Completed local checks

- Ruff: six v5.6 Engine modules, the integration test, and the benchmark.
- Ruff: all 211 source files.
- mypy: the complete `manga_director` package.
- pytest: 139 regression test modules in batches, including six Engine suites
  and the end-to-end integration contract.
- Local package: Hatchling wheel/sdist build, Twine metadata check, wheel
  import, CLI/MCP import, and `pip check`.
- Static security: six-Engine dependency-boundary scan, SBOM JSON parsing, and
  private-key/AWS-key pattern scan.

## Pending release checks

- External CVE lookup, protected CI, signing, GitHub pre-release, and PyPI
  upload require maintainer authority.

# v5.7 RC1 Quality Gate Report

## Required local checks

- [x] Ruff: affected v5.7 Production Platform modules, RC contract, and benchmark;
  all `src` and `tests` lint checks pass.
- [x] mypy: complete `manga_director` package (214 source files).
- [x] pytest: full regression suite, including Production Platform end-to-end,
  Workspace, Automation, Plugin, Story, Character, Page, Review, and Export
  contracts. The provider repeatability probe was stabilized without changing
  its acceptance threshold.
- [x] Coverage: complete package suite at 94%, above the configured 80% threshold.
- [x] Package: wheel/sdist build, Twine metadata check, wheel-content and
  zip-import smoke, and dependency check.
- [x] Security: static boundary scan, SBOM parsing, and common secret-pattern
  scan.
- [x] Performance: one-page Production Platform report benchmark completed in
  `0.088377s` for 500 projections. It is a first-release smoke measurement,
  not a cross-version regression comparison.

## External release checks

- [ ] Local `pip --target` installation smoke did not complete in this
  verification environment; a clean maintainer environment must rerun it.
- [ ] Protected CI, external CVE audit, signing, tag creation, GitHub
  pre-release publication, and PyPI upload require maintainer authority.

# v6.0.0 RC1 Quality Gate Report

## Required local checks

- [x] Focused Platform Kernel, SDK, Extension, Marketplace, Governance,
  Observability, AI Orchestrator, and end-to-end compatibility contracts.
- [x] Ruff: all source, test, and benchmark checks; mypy: 217 package sources.
- [x] Full regression: 94.23% coverage, above the configured 80% threshold.
- [x] Package: isolated-environment wheel installation with declared
  dependencies, public wheel import, CLI and MCP symbol smoke, `pip check`,
  wheel/sdist build, and Twine metadata check.
- [x] Static import-boundary, SBOM parse, and common secret-pattern audit.
- [x] Provider-free Platform Kernel benchmark: `0.114873s` for 500 report
  projections. This bounded local measurement has no historical v5.7 baseline.

## External release checks

- [ ] Protected CI, external CVE audit, signing, tag creation, GitHub
  pre-release publication, and PyPI upload require maintainer authority.
