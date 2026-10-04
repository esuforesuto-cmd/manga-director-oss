# v3.5 Migration Strategy

v3.5 planning freezes the v3.4 public contract before any Issue is admitted.
Implementation candidates must add opt-in DTO projections behind existing
Application, Knowledge, Repository, CLI, FastAPI, MCP, and Web UI boundaries.
No data migration, schema migration, configuration migration, or workflow
migration is planned.

Each Issue must provide deterministic compatibility fixtures, provenance and
redaction rules, a no-write/no-execution proof, documentation, benchmark scope,
and rollback instructions. Existing consumers can ignore all v3.5 additions.
