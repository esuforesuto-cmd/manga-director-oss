# Migration Strategy: v5.0 LTS to v5.1

## Release status

v5.1.0 is an additive stable release. No data conversion, API rewrite,
configuration update, or workflow migration is required.

## Compatibility promise

v5.0 LTS remains fully supported. Existing Python API, CLI, FastAPI/REST,
MCP, Web UI, Repository, Workflow, Extension SDK, Provider, and Backend users
can retain their current integration without a composition profile.

## Optional adoption path

1. Keep the v5.0 integration unchanged.
2. Optionally add a declarative Capability Registry descriptor.
3. Optionally select a Profile or Solution Template for discovery and planning.
4. Compare results with legacy contract-equivalence fixtures.
5. Roll back by removing optional metadata; data and workflows need no rollback.

## Released compatibility evidence

- Python, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, and Extension
  SDK compatibility fixtures.
- StateMachine invariant tests: one Page, complete stages, persisted storyboard
  before image generation, and completed quality review before approval.
- Offline registry/profile/template validation with no service invocation.
- Documentation showing legacy-only adoption.

Removing optional composition metadata restores the v5.0 LTS usage shape. No
data or workflow rollback is required. Remote catalogs, dynamic loading,
installation, billing, hosted marketplaces, and enforcement remain deferred.
