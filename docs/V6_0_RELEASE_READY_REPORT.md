# manga-director v6.0.0 Release Ready Report

## Scope

v6.0 final contains RC1 feedback resolution, release metadata finalization,
documentation freeze, and final validation only. The Platform Kernel,
Foundation, Intelligence, SDK, Extension, Marketplace, Governance, and
Observability services retain their RC1 additive, read-only behavior.

## API freeze

Platform API v1.0, SDK v1.0, Extension API v1.0, and Marketplace Specification
v1.0 are documented as stable descriptor/report contracts. Existing v5.x
Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, SDK, Plugin,
and StateMachine interfaces remain available and unchanged.

## Release decision

Local release readiness passes: Ruff, mypy, 888 regression tests at 94.23%
coverage, compatibility, architecture-boundary, SBOM, secret-pattern,
benchmark, wheel/sdist, Twine, clean package installation, CLI/MCP smoke, and
documentation-link validation completed successfully. Protected CI, external
CVE audit, signing, tag creation, GitHub publication, and PyPI publication
remain maintainer-controlled release controls.

## v6.x LTS transition

The stable v6.0 baseline enters the v6.x LTS maintenance policy. The
post-release plan, health evidence, compatibility matrices, Marketplace
certification standard, security maintenance record, and technical-debt
registry add no product behavior and do not alter the frozen APIs.
