# v4.7 RC1 Compatibility Verification

Baseline: v4.6.0. Candidate: v4.7.0rc1.

| Contract | Result | Evidence |
| --- | --- | --- |
| Python API | Compatible | v4.7 adds immutable DTOs and services without removing or changing v4.6 exports. |
| CLI | Compatible | Existing command help remains available; Decision Platform reports do not replace commands. |
| FastAPI / REST | Compatible | Existing observability routes remain available and derive the candidate version. |
| MCP | Compatible | Initialization and server metadata remain available with the candidate version. |
| Repository | Compatible | The Repository interface is unchanged; save/reload storyboard evidence remains intact. |
| Workflow | Compatible | No transition, stage, workflow-engine, or execution-policy change is introduced. |
| Agent / Plugin / Extension SDK | Compatible | Decision reports do not alter registration, runtime, plugin, or SDK behavior. |
| Provider / Backend / Web UI | Compatible | No provider/backend interface or frontend API contract changed. |

No migration is required. The frontend uses npm prerelease notation
`4.7.0-rc.1`; Python, OpenAPI, MCP, SBOM, and release metadata use
`4.7.0rc1`.

Related evidence: [workflow regression](WORKFLOW_REGRESSION_V4_7_RC1.md) and
[architecture summary](ARCHITECTURE_SUMMARY_V4_7_RC1.md).
