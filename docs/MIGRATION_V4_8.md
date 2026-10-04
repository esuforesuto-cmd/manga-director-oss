# Migrating from v4.7 to v4.8.0

## Status

v4.8.0 is an additive final release. Users of v4.7.0 need no code,
configuration, repository, workflow, CLI, API, FastAPI, MCP, or Web UI change.
Install `manga-director==4.8.0` when adopting the release.

## Public-surface preservation

| Surface | v4.8.0 commitment |
| --- | --- |
| Python API | Existing import paths, DTOs, service signatures, and semantics remain supported. |
| CLI | Existing command names, flags, output behavior, and exit contracts remain valid. |
| FastAPI / REST | Existing routes, schemas, status behavior, and OpenAPI compatibility remain valid. |
| MCP / Web UI | Existing tools, payloads, and presentation adapters remain valid. |
| Repository | Existing interfaces, persistence formats, and save/reload behavior remain canonical. |
| Workflow | StateMachine remains authoritative; exactly-one-Page, storyboard, review, and approval gates remain intact. |
| Agent / Plugin / Extension SDK | Existing registration, validation, and extension contracts remain supported. |
| Provider / Backend | Existing protocols and selection paths remain unchanged. |

## v4.8 release commitment

1. Add an optional facade beside existing module APIs; never replace them in a
   single release.
2. Adapt at the edge using existing public services rather than copying or
   relocating Core behavior.
3. Preserve identifiers, output fields, error semantics, and transport
   contracts; new fields must be optional and safely ignored by older clients.
4. Test legacy and consolidated pathways against identical supplied evidence
   and the same StateMachine rules.
5. Announce any future deprecation in documentation, include a support window
   and migration example, and do not remove the old surface in v4.8.0.

## Data and lifecycle migration

No data migration is introduced. Existing project, repository, knowledge,
workspace, production, audit, and release records remain in their owner
formats. A future aggregate report links to existing identifiers and
provenance; it does not copy, rewrite, merge, or delete records.

## Rollback

No data conversion is introduced. If an additive v4.8 report is not adopted,
continue using the unchanged v4.7 module pathways; no rollback procedure or
data transformation is required.

## Verification requirements

Before any implementation issue is accepted, it must add contract tests for
Python, CLI, FastAPI/REST, MCP, Web UI, Repository save/reload, Workflow
invariants, Agent/Plugin/Extension SDK, Provider, and Backend behavior relevant
to its affected surface.
