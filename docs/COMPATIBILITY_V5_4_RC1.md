# v5.4.0 RC1 Compatibility Verification

Quality Framework services are optional imports and additive SDK methods. They
do not require quality metadata from v5.0 LTS/v5.3 callers and do not change
Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, Extension
SDK, Provider, or Backend contracts.

- Package, OpenAPI, and MCP obtain `5.4.0rc1` from the canonical version source.
- The frontend metadata reports `5.4.0-rc.1`.
- Quality reports retain StateMachine authority and record no workflow mutation,
  review execution, CI/CD control, approval, or release operation.
- Legacy users may omit all Quality Framework DTOs with no migration or rollback.
