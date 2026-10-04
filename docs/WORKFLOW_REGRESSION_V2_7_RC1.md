# v2.7.0 RC1 Workflow Regression Evidence

Existing end-to-end and integration suites cover the same Application-layer
composition for Project, Chapter, one Page, explicit Human Approval, save,
reload, resume, Batch, Automation, Notification, Plugin, Extension, FastAPI,
MCP, and Web UI delivery boundaries.

The RC additionally verifies AI Director planning, Knowledge search and
governance, Workflow analysis and orchestration, Enterprise diagnostics,
reporting, and dashboard paths. These are advisory DTO services: they do not
execute Agents, create multiple pages, alter a workflow state, generate an
image, approve work, or bypass persisted-storyboard and quality-before-approval
invariants.

The authoritative execution path remains `WorkflowEngine` -> `StateMachine` ->
Agent. The StateMachine is still the source of truth for all legal transitions.
