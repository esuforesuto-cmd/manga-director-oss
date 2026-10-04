# v3.2.0 Production Deployment Guide

Deploy v3.2.0 through existing Application services and Repository ports.
Validate startup dependencies and configuration, inspect health and repository
integrity, and use read-only Creative Studio, Asset Intelligence, Workflow
Profiles, Production Analytics, diagnostics, and reporting evidence before
workflow execution.

The deployment boundary remains one Page per `WorkflowEngine` execution. `run`
stops at `QualityChecked`; human approval remains explicit. Production helpers
must not bypass the StateMachine, generate multiple pages, or auto-approve.

See [Operations](OPERATIONS_V3_2.md), [Migration](MIGRATION_V3_2.md),
[Creative Studio](CREATIVE_STUDIO_GUIDE_V3_2.md),
[Asset Intelligence](ASSET_INTELLIGENCE_GUIDE_V3_2.md), and
[Workflow Profiles](WORKFLOW_PROFILES_GUIDE_V3_2.md).
