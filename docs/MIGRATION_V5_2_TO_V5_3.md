# Migration Strategy: v5.2 to v5.3

## Status

v5.3 is design only. v5.2.0 remains unchanged; no code, package version, data
conversion, Connector setup, credential configuration, event registration, or
workflow migration is required.

## Compatibility promise

v5.0 LTS, v5.1, and v5.2 public contracts remain supported. Existing Python
API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, SDK, Provider, and
Backend users can retain their current integration without Integration metadata.

## Future opt-in path

1. Keep the existing v5.2 integration unchanged.
2. Optionally describe a Connector and exchange envelope after validation
   fixtures exist.
3. Generate a local integration preview and have a named human review it.
4. Compare it with compatibility and workflow-invariant fixtures.
5. Remove optional metadata to return to legacy-only behaviour; no data or
   workflow rollback is needed because the Integration Plane owns neither.

Remote connection, transport, synchronization, enforcement, credential storage,
and automation execution remain deferred.
