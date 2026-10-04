# v4.3.0 Compatibility Verification

## Result

v4.3.0 preserves v4.2 public contracts. The final release contains the same
additive v4.3 DTO surface reviewed in RC1; no existing symbol, workflow
transition, Repository interface, or delivery interface is replaced.

| Surface | Result |
| --- | --- |
| Python API | Additive v4.3 production exports; v4.2 and earlier exports retained. |
| CLI | Existing commands and help remain available. |
| FastAPI / REST | Existing routes and derived version metadata remain available. |
| MCP | Existing initialization and derived server version remain available. |
| Repository | `ProjectRepository` is unchanged; v4.3 composes immutable context projections. |
| Workflow | StateMachine remains canonical; v4.3 cannot transition workflow state. |
| Extension SDK / Plugin | No interface change. |
| Provider / Image Backend | No interface or runtime change. |
| Web UI | Existing UI package identity and contracts retained. |

No migration is required.
