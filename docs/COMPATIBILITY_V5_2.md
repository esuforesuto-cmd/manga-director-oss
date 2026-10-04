# v5.2.0 Compatibility Verification

v5.2.0 is additive over v5.0 LTS and v5.1. Existing callers can retain their
Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, Extension
SDK, Provider, and Backend integrations without rule, event, template, or
registry metadata.

Package, OpenAPI, MCP, frontend, SBOM, wheel, and sdist use `5.2.0`. The
Automation SDK methods and DTO exports are opt-in. Their reports preserve
StateMachine authority and record no workflow mutation, event delivery, service
invocation, configuration change, or automatic action.

No data, configuration, workflow, or API migration is required.
