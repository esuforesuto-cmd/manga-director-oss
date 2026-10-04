# v4.1.0 Compatibility Verification

v4.1.0 is additive over v4.0. It retains documented v1.x, v2.x, v3.x, and v4.0
public contracts.

| Surface | Result |
| --- | --- |
| Python API | Pass — v4.1 services are additive exports only. |
| CLI | Pass — existing commands and help contract unchanged. |
| FastAPI / REST | Pass — existing health, diagnostics, and repository endpoints unchanged. |
| MCP | Pass — server metadata derives from the canonical package version. |
| Repository | Pass — no ProjectRepository method or persistence contract changed. |
| Workflow | Pass — StateMachine remains sole transition authority. |
| Extension SDK | Pass — existing validator and compatibility boundary unchanged. |
| Providers / Backends | Pass — no Provider or Backend interface changed. |
| Web UI | Pass — metadata updated only; no UI contract replacement. |

No migration or breaking change was identified.
