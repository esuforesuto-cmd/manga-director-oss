# v4.2.0 Compatibility Verification

## Result

v4.2.0 preserves v4.1 public contracts. All v4.2 additions are optional,
Application-layer DTO projections; no existing symbol, workflow transition,
Repository interface, or delivery interface is replaced.

| Surface | Result |
| --- | --- |
| Python API | Additive v4.2 production exports; v4.1 exports retained. |
| CLI | Existing commands and help remain available. |
| FastAPI / REST | Existing routes and derived version metadata remain available. |
| MCP | Existing initialization and derived server version remain available. |
| Repository | `ProjectRepository` unchanged; checkpoint data is a separate immutable projection. |
| Workflow | StateMachine remains canonical; v4.2 cannot transition workflow state. |
| Extension SDK / Plugin | No interface change. |
| Provider / Image Backend | No interface or runtime change. |
| Web UI | Existing UI package identity and contracts retained. |

No migration is required.
