# v4.5 RC1 Compatibility Verification

Baseline: v4.4.0. Candidate: v4.5.0rc1.

| Contract | Result | Evidence |
| --- | --- | --- |
| Python API | Compatible | v4.5 adds immutable DTOs and services without removing or changing v4.4 exports. |
| CLI | Compatible | Existing command help remains available; ecosystem review services do not replace commands. |
| FastAPI / REST | Compatible | Existing observability routes remain available and retain the candidate version. |
| MCP | Compatible | Initialization and server metadata remain available with the candidate version. |
| Repository | Compatible | The Repository interface is unchanged; save/reload storyboard evidence remains intact. |
| Workflow | Compatible | No transition, stage, or workflow-engine change is introduced. |
| Plugin / Extension SDK | Compatible | Analytics and governance only inspect supplied metadata and do not alter SDK behavior. |
| Provider / Backend / Web UI | Compatible | No provider/backend interface or frontend API contract changed. |

No migration is required. The frontend uses npm prerelease notation
`4.5.0-rc.1`; Python, OpenAPI, MCP, SBOM, and release metadata use
`4.5.0rc1`.

Related evidence: [workflow regression](WORKFLOW_REGRESSION_V4_5_RC1.md) and
[architecture summary](ARCHITECTURE_SUMMARY_V4_5_RC1.md).
