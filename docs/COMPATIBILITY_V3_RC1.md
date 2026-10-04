# v3.0.0 RC1 Compatibility Audit

## Scope and method

This audit compares v1.x and v2.0.x-v2.7.x documented contracts with
`3.0.0rc1`. It combines root-export, import/architecture, StateMachine,
release-contract, CLI, FastAPI, MCP, repository, planning, knowledge, director,
creative, review, diagnostics, health, security, and documentation-link tests.

| Surface | RC1 result |
| --- | --- |
| Python API | Existing root exports, DTOs, and documented errors are retained; v3 helpers are optional Production services. |
| CLI | Existing commands remain; added v3 commands render advisory DTOs only. |
| FastAPI / REST / MCP | DTO-only delivery and canonical version metadata are retained. |
| Workflow | Exactly one Page, forward StateMachine order, storyboard-before-generation, quality-before-approval, and explicit approval remain authoritative. |
| Repository / Knowledge | `load`, `save`, `exists`, `delete`, and `list` are unchanged; Knowledge uses redacted, non-mutating repository projections. |
| Director / Planning / Creative / Review | Additive reports cannot dispatch Agents, transition state, generate images, or approve work. |
| Plugin / Extension / Provider / Backend | Existing Registry, Factory, Protocol, lifecycle, and compatibility contracts are unchanged. |
| Automation / Notification / Health / Web UI | Outer adapters retain established Application-layer composition and no Core imports. |

## Versioning

`pyproject.toml` remains dynamically versioned from
`src/manga_director/_version.py`. Python, MCP, optional OpenAPI, and SBOM use
`3.0.0rc1`; the independent npm package uses `3.0.0-rc.1`.

## Conclusion

No breaking change was identified. RC feedback is limited to corrective release
work; new workflows, providers, backends, cloud, marketplace, distributed
runtime, automatic release, and autonomous AI remain out of scope.
