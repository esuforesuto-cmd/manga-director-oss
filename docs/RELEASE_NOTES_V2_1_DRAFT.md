# v2.1.0 Release Notes Draft (Historical)

> Superseded by the final [v2.1.0 Release Notes](../RELEASE_V2_1.md). This
> document remains only as an Iteration 3 planning record.

## Highlights

- Stronger architecture, import, dependency, documentation-link, and benchmark
  smoke quality gates.
- Cached and separated backend/frontend CI checks with coverage artifact output.
- Public API compatibility contract, OSS governance assets, security policy,
  SBOM, dependency license report, and release-readiness documentation.
- More accurate Web UI documentation: it is a tested frontend scaffold, not a
  bundled FastAPI service.

## Compatibility

No public Python root export, page state transition, CLI workflow command, MCP
tool contract, persisted Project model, or adapter selection contract changed.

## Migration

No migration is required for Iteration 3. Optional PostgreSQL and migration
dependencies are now explicitly installed as extras. See
[Migration Guide](MIGRATION_v1_to_v2.md).

## Known limitations

FastAPI and Automation are not shipped in this source baseline. Real provider
network calls, remote extension installation, distributed workers, and parallel
workflow execution remain outside this maintenance release.
