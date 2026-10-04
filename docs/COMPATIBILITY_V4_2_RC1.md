# v4.2.0 RC1 Compatibility Audit

## Baseline

v4.1.0 is the compatibility baseline. v4.2.0rc1 is additive-only and does not
replace, remove, rename, or reinterpret an existing contract.

| Surface | Result | Evidence |
| --- | --- | --- |
| Python API | Pass | v4.1 exports remain available; v4.2 exports are additive. |
| CLI | Pass | Existing CLI help and commands remain available. |
| FastAPI / REST | Pass | Existing observability routes and derived API version remain available. |
| MCP | Pass | Existing initialization and derived server version remain available. |
| Repository | Pass | `CheckpointRepository` is a separate immutable projection; `ProjectRepository` is unchanged. |
| Workflow | Pass | StateMachine remains canonical; no v4.2 DTO transitions workflow state. |
| Extension SDK / Plugin | Pass | No Extension SDK or Plugin interface change is introduced. |
| Web UI | Pass | Existing package identity remains unchanged; frontend version is prerelease metadata only. |

No migration is required for v4.1 users.
