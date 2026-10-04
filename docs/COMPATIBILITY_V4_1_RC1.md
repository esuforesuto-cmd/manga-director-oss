# v4.1 RC1 Compatibility Audit

## Baseline

The v4.0 stable release is the compatibility baseline. v4.1 adds new DTOs and
services under `manga_director.production`; it does not replace prior names or
change existing method signatures.

| Surface | Result |
| --- | --- |
| Python API | Pass — additive exports only. |
| CLI | Pass — existing command help and commands unchanged. |
| FastAPI / REST | Pass — existing health, diagnostics, and repository routes unchanged. |
| MCP | Pass — initialize metadata remains derived from the one package version source. |
| Repository | Pass — `ProjectRepository` contract unchanged; agent registry is local and immutable. |
| Workflow | Pass — StateMachine remains canonical; v4.1 cannot dispatch or transition. |
| Extension SDK | Pass — existing version validator remains unchanged. |
| Web UI | Pass — package metadata only; no UI contract replacement. |

No breaking changes or migration steps were identified.
