# v5.1.0 RC1 Compatibility Verification

## v5.0 LTS contract position

Composition services are optional imports and optional SDK methods. They do not
require profile metadata from legacy callers and do not change existing Python,
CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, Extension SDK, Provider,
or Backend contracts.

## Verified boundaries

- Package, OpenAPI, and MCP report `5.1.0rc1`; the frontend reports
  `5.1.0-rc.1`.
- Existing CLI help remains available.
- Existing Repository save/reload behavior remains unchanged.
- Existing v5 platform and v5.1 composition tests run together.
- Composition reports preserve StateMachine authority and record no workflow
  mutation, service invocation, configuration change, or automatic action.

No migration is required. Removing optional composition metadata restores the
legacy-only v5.0 LTS usage shape without data or workflow rollback.
