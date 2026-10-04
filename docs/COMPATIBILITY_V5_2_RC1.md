# v5.2.0 RC1 Compatibility Verification

## v5.0 LTS and v5.1 contract position

Automation services are optional imports and optional SDK methods. They do not
require rule, event, template, registry, or governance metadata from legacy
callers and do not change existing Python, CLI, FastAPI/REST, MCP, Web UI,
Repository, Workflow, Extension SDK, Provider, or Backend contracts.

## Verified boundaries

- Package, OpenAPI, and MCP report `5.2.0rc1`; the frontend reports
  `5.2.0-rc.1`.
- Existing CLI help remains available.
- Existing Repository save/reload behaviour remains unchanged.
- Existing v5 platform, v5.1 composition, and v5.2 automation tests run
  together.
- Automation reports preserve StateMachine authority and record no workflow
  mutation, event delivery, service invocation, configuration change, or
  automatic action.

No migration is required. Removing optional Automation metadata restores the
legacy-only v5.0 LTS usage shape without data or workflow rollback.
