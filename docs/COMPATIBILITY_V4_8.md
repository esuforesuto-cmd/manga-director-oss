# v4.8.0 Compatibility Verification

Baseline: v4.7.0. Release: v4.8.0.

| Contract | Result | Evidence |
| --- | --- | --- |
| Python API | Compatible | v4.8 adds immutable `production` DTOs/services without removing or changing v4.7 exports. |
| CLI | Compatible | Existing command help remains available; Creative Operating System reports do not replace commands. |
| FastAPI / REST | Compatible | Existing observability routes remain available and derive `4.8.0`. |
| MCP | Compatible | Initialization and server metadata remain available with `4.8.0`. |
| Repository | Compatible | The Repository interface and persistence formats are unchanged; storyboard save/reload remains intact. |
| Workflow | Compatible | No StateMachine transition, workflow-engine, stage, or execution-policy change is introduced. |
| Agent / Plugin / Extension SDK | Compatible | v4.8 reports do not alter registration, runtime, plugin, or SDK behavior. |
| Provider / Backend / Web UI | Compatible | No provider/backend interface or frontend API contract changed. |

No data or configuration migration is required from v4.7. New v4.8
`production` exports are optional and additive. The frontend, Python, OpenAPI,
MCP, SBOM, and release metadata use the canonical stable version `4.8.0`.
