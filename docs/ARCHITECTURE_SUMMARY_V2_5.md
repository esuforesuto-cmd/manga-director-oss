# v2.5.0 Architecture Summary

v2.5 preserves the established Clean Architecture: Domain owns invariants;
Workflow Engine and StateMachine enforce legal one-page execution; Application
services compose ports; Infrastructure implements adapters and repositories;
CLI, FastAPI, MCP, and Web UI remain outer delivery adapters.

Production reporting remains an optional Application-layer facade. It composes
existing Quality Automation, Repository Maintenance, Configuration, and
Workflow-context contracts into read-only DTOs. It does not import delivery
adapters, mutate Domain state, or introduce dependencies from Core to external
systems.

Repository, Provider Runtime, Image Backend Runtime, Plugin, and Extension SDK
boundaries remain protocol- or port-based. Root-level public Python exports are
unchanged; reporting types remain intentionally namespaced under
`manga_director.production`.
