# v4.4 RC1 Compatibility Verification

## Baseline

The v4.3 release is the compatibility baseline for v4.4 RC1.

## Result

| Contract | Result |
| --- | --- |
| Python API | Retained; Enterprise DTOs are additive exports. |
| CLI | Retained; command help contract remains available. |
| FastAPI / REST API | Retained; observability routes and version derivation remain available. |
| MCP | Retained; initialization continues to advertise the canonical package version. |
| Repository | Retained; save/reload of persisted storyboard evidence passes. |
| Workflow | Retained; no StateMachine transition or engine modification. |
| Plugin / Extension SDK | Retained; registry reports do not load, execute, or alter SDK contracts. |
| Web UI | Retained; package metadata stays available with prerelease notation. |

No migration is required. See the [release notes](../RELEASE_V4_4_RC1.md).
