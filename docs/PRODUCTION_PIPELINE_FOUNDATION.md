# Production Pipeline Foundation

v3.3 introduces a read-only Production Pipeline projection in the Application
Layer. `V33FoundationService.production_pipeline()` returns immutable pipeline
stages, a suggested transition, approval prerequisites, a session, observed
timeline, and summary for exactly one existing Page.

The service does not persist a pipeline, start an Agent, execute a workflow
command, apply a transition, approve a Page, publish an artifact, or modify a
`WorkflowContext`. The suggested command is derived from the existing
`StateMachine`; callers must still invoke the normal one-page workflow command
when a human chooses to proceed.

Use `manga-director director production-pipeline-v33 --project <id> --page
<number>`, the optional `/v3.3/production-pipeline` FastAPI provider, or the
`production_pipeline_v33` MCP tool.

## v4.3 Foundation

`V43ProductionFoundationService.production_pipeline()` adds a separate,
transport-neutral planning projection for a Production Project, observed
Production Stage, Milestone, Deliverable, and Pipeline Summary. It is a
one-Page, Application-layer DTO report; it does not modify the v3.3 service or
add a CLI, FastAPI, MCP, or Web UI route.

The v4.3 report cannot start or complete a stage, transition a workflow, mark a
milestone complete, create a deliverable, approve a Page, schedule a release,
publish an artifact, or persist data. StateMachine remains authoritative,
persisted storyboard remains required before image generation, and completed
quality review remains required before approval.
