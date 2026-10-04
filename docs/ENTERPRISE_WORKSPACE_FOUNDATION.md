# Enterprise Workspace Foundation

v4.4 Enterprise Workspace Foundation adds immutable Application-layer DTOs for
workspace, session, snapshot, and summary evidence. Use
`V44EnterpriseFoundationService.enterprise_workspace(project_id, context)` to
describe one supplied Project and exactly one existing Page.

The report records identity and readiness only. It cannot create or persist a
workspace, start or persist a session, capture a snapshot, change a workflow,
assign work, enforce access, or call an external service. The StateMachine
remains authoritative.
