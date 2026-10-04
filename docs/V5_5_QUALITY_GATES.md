# v5.5 Lifecycle Planning Quality Gates

| Gate | Evidence required | Pass condition |
| --- | --- | --- |
| Lifecycle Architecture Validation | Responsibility and ownership matrix. | No Core, StateMachine, WorkflowEngine, repository, or adapter ownership change. |
| Upgrade Compatibility Validation | v5.0 LTS and v5.4 compatibility manifest. | Legacy surfaces retain behavior and no automatic migration is proposed. |
| Deprecation Policy Validation | Notice, replacement, horizon, exception, and owner model. | No v5.x removal, automatic warning, blocking, or deletion. |
| Platform Health Validation | Evidence freshness, unknown-state, and safety model. | Health is read-only and cannot trigger operational action. |
| Documentation Validation | Link and terminology review. | Vision, architecture, roadmap, migration, and policy documents are complete and mutually consistent. |

All gates are design-review gates. They do not grant permission to execute an upgrade, remove a capability, or change a workflow.
