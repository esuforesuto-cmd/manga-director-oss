# v5.7 Final Quality Gate Report

## Local validation record

- Ruff passed for all `src` and `tests` files.
- mypy passed for the complete `manga_director` package (214 source files).
- Full regression passed, including Platform, Workspace, Automation, Plugin,
  Story, Character, Page, Review, Export, API, CLI, FastAPI, MCP, and Web
  compatibility contracts.
- Coverage completed at 94%, above the configured 80% threshold.
- The one-page Production Platform baseline completed 500 projections in
  `0.087163s`.
- Static architecture-boundary and secret-pattern scans, plus SBOM JSON
  validation, passed.
- Wheel and sdist builds, Twine metadata checks, clean-environment dependency
  installation, wheel import, CLI help, MCP initialization, and `pip check`
  passed.

## Final release boundary

The release must preserve exactly one page per workflow execution, persisted
storyboard before image generation, completed quality review before approval,
and StateMachine-owned workflow transitions. Platform reports remain
read-only.

## External controls

Protected CI, external CVE audit, signing, tag creation, GitHub publication,
and PyPI publication require maintainer authority and are not represented as
local passes.

# v6.0 Final Quality Gate Report

## Release scope

The v6.0 final release promotes the RC1-reviewed, additive Platform Kernel,
SDK, Extension, Marketplace, Governance, and Observability report surfaces.
No feature, workflow, repository, API, or runtime behavior is added after RC1.

## Local validation record

- Ruff passed for all `src`, `tests`, and `benchmarks` files.
- mypy passed for the complete `manga_director` package (217 source files).
- Full regression passed: 888 tests with 94.23% coverage, above the configured
  80% threshold. It includes Platform Kernel, SDK, Extension, Marketplace,
  Governance, Observability, AI Orchestrator, CLI, FastAPI, MCP, and v5.x
  compatibility contracts.
- The provider-free Platform Kernel baseline completed 500 projections in
  `0.111484s`.
- Static v6 architecture-boundary and common secret-pattern scans, plus SBOM
  JSON validation, passed.
- Wheel and sdist builds, Twine metadata checks, clean-environment dependency
  installation, wheel import, CLI help, MCP public-symbol import, and `pip
  check` passed.

## Final release boundary

The frozen v6.0 APIs remain advisory and enforce the established one-Page
workflow boundary. They cannot bypass the StateMachine, generate an image,
approve a Page, load an Extension, publish Marketplace content, enforce a
policy, emit telemetry, or mutate a repository.

## External controls

Protected CI, external CVE audit, signing, tag creation, GitHub publication,
and PyPI publication require maintainer authority and are not represented as
local passes.
