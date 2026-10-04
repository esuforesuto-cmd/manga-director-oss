# GitHub Release Notes: v5.1.0 RC1

## Composable Creative Platform

v5.1.0 RC1 adds optional, local Composition Platform diagnostics: Capability
Registry, Feature Packs, Platform Profiles, Solution Templates, Composition
Engine, Governance, Observability, Lifecycle, Reliability, and SDK maturity
previews.

## Compatibility

v5.0 LTS Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow,
Extension SDK, Provider, and Backend contracts are preserved. No migration is
required and no existing caller must opt into composition metadata.

## Safety

This RC does not load modules, install extensions, invoke services, route
runtime work, enforce policy, collect telemetry, persist composition state,
recover components, execute a workflow, or approve a page automatically.

See [RELEASE_V5_1_RC1.md](../RELEASE_V5_1_RC1.md) for validation evidence and
maintainer-controlled publication gates.
