# v2.5.0 Quality Report

v2.5.0 promotes the reviewed RC1 after release-only corrections. Local quality
evidence includes 191 passing pytest tests with 87.02% coverage, Ruff, strict
mypy, provider-free benchmark smoke, frontend lint/typecheck/Vitest/build,
wheel/sdist generation, Twine validation, and clean-install CLI/MCP/Plugin
smoke checks.

The release preserves one-page StateMachine authority and all documented public
contracts. Hosted CI, dependency/CVE audit, secret scan, and publication checks
remain mandatory external controls for the exact release tag.
