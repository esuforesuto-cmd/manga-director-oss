# manga-director v5.7.0

Release date: 2026-08-09  
Canonical package and frontend version: `5.7.0`

## Manga Production Platform

v5.7 promotes the optional, read-only Production Platform to a stable release.
It standardizes evidence reporting for one existing page across Production,
Workspace, Project, Asset, Automation, Plugin, Story, Character, Page, Review,
and Export components.

No automatic generation, scheduling, Plugin lifecycle change, event publishing,
snapshot restore, workflow transition, approval, export, publication, or
repository mutation is introduced.

## Frozen v1 surfaces

- [Platform API v1](docs/PLATFORM_API_REFERENCE.md)
- [Plugin API v1](docs/PLUGIN_API_REFERENCE.md)
- [Workspace Standard v1](docs/WORKSPACE_SPECIFICATION.md)

The frozen surfaces are additive. Existing v5.x APIs, CLI, FastAPI/REST, MCP,
Web UI, Repository, Workflow, SDK, and StateMachine contracts remain
compatible.

## Release evidence

- [Release-ready report](docs/V5_7_RELEASE_READY_REPORT.md)
- [Final quality gate](docs/FINAL_QUALITY_GATE_REPORT.md)
- [Performance baseline](docs/PERFORMANCE_BASELINE_V5_7.md)
- [Migration guide](docs/MIGRATION_V5_7.md)
- [GitHub release notes](docs/GITHUB_RELEASE_V5_7.md)

## Package

The final wheel and source distribution were built, Twine-checked, installed
into a clean environment with declared dependencies, and exercised through the
package import, CLI, MCP initialization, and dependency check.
