# Workspace Compliance

`V44EnterpriseGovernanceService.workspace_compliance(project_id, context)`
returns a read-only Workspace Compliance DTO. It exposes one-Page, storyboard,
quality-review, and human-review requirements without making an access-control
or approval decision.

Compliance cannot be confirmed automatically. Workspace creation, persistence,
membership changes, permission changes, workflow changes, and task assignment
remain outside this foundation.
