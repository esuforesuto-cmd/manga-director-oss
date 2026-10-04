# v5.1.0 Compatibility Verification

v5.1.0 is additive over v5.0 LTS. Existing callers can keep their current
Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, Extension
SDK, Provider, and Backend integration with no Profile or template metadata.

The new Composition services and `UnifiedSDKFoundation` methods are optional.
They do not load modules, alter configuration, route execution, mutate a
workflow, persist composition state, or replace a legacy response shape.

Version, OpenAPI, MCP, frontend, SBOM, wheel, and sdist use `5.1.0`. The
legacy-only v5.0 usage path remains a valid rollback: remove optional metadata
and no data or workflow rollback is needed.
