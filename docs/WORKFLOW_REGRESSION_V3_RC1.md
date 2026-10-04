# v3.0.0 RC1 End-to-End Regression Evidence

Existing end-to-end and integration suites cover Project, Story/Chapter/Page/
Panel planning, one Page workflow, explicit Human Approval, save, reload,
resume, Batch, Automation, Notification, Plugin, Extension, FastAPI, MCP, and
Web UI delivery boundaries through established Application composition.

The RC additionally verifies Director planning and reliability, Creative
analysis and governance, Knowledge lookup and integrity, Multi-Agent
coordination, Review Pipeline, diagnostics, reporting, and production-readiness
paths. These services are advisory DTOs: they do not execute Agents, create
multiple Pages, alter workflow state, generate an image, approve work, or bypass
persisted-storyboard and quality-before-approval invariants.

The authoritative execution path remains `WorkflowEngine` -> `StateMachine` ->
Agent. `StateMachine` remains the source of truth for legal transitions.
