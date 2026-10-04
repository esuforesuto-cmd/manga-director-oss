# v2.6.0 RC1 Workflow Regression Evidence

The existing end-to-end and integration suites cover the same Application-layer
composition for Project, Chapter, one Page, explicit Human Approval, save,
reload, resume, Batch, Automation, Notification, Plugin, Extension, FastAPI,
MCP, and Web UI delivery boundaries.

The RC additionally verifies that planning, analysis, provider selection,
Enterprise diagnostics, reporting, and health paths are advisory DTO services:
they do not execute Agents, create multiple pages, alter a workflow state,
generate an image, approve work, or bypass persisted-storyboard and
quality-before-approval invariants.

The authoritative execution path remains `WorkflowEngine` -> `StateMachine` ->
Agent. The StateMachine is still the source of truth for all legal transitions.
