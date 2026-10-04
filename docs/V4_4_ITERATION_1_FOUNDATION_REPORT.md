# v4.4 Iteration 1 Foundation Report

## Outcome

v4.4 Iteration 1 adds Enterprise Creative Platform foundations as immutable,
transport-neutral, non-executing Application-layer DTOs. The package version
remains `4.3.0` on the `4.3.x` development branch.

| Area | Added foundation | Boundary |
| --- | --- | --- |
| Enterprise Workspace | Workspace, session, snapshot, and summary reports. | No workspace/session persistence or workflow change. |
| Team | Team, human-owner member, review prerequisite, and summary reports. | No membership, permission, assignment, or approval change. |
| Portfolio | Portfolio, project observation, and summary reports. | No enumeration, project mutation, allocation, or scheduling. |
| Extension Registry | Manifest, compatibility, registry, and summary reports. | No discovery, load, execution, permission, SDK change, or telemetry. |
| Marketplace Catalog | Catalog, entry, policy, and summary reports. | No remote discovery, download, install, execution, publishing, payment, or billing. |

## Compatibility and quality

The v4.3 Python API, CLI, FastAPI, REST, MCP, Web UI, Repository, Workflow,
Provider, Backend, Plugin, and Extension SDK remain unchanged. New symbols are
additive `manga_director.production` exports. StateMachine authority and the
one-Page, storyboard, and completed-quality-review invariants are preserved.

## Evidence

- [Enterprise Workspace Foundation](ENTERPRISE_WORKSPACE_FOUNDATION.md)
- [Team Foundation](TEAM_FOUNDATION.md)
- [Portfolio Foundation](PORTFOLIO_FOUNDATION.md)
- [Extension Registry](EXTENSION_REGISTRY.md)
- [Marketplace Foundation](MARKETPLACE_FOUNDATION.md)
- [v4 Quality Gates](V4_QUALITY_GATES.md)
- [Technical Debt Register](TECH_DEBT.md)
