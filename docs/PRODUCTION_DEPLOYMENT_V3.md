# v3.0.0 Production Deployment Guide

Deploy v3.0.0 through existing Application services and Repository ports.
Validate startup dependencies and configuration, inspect health and repository
integrity, and use read-only Director, Creative, Knowledge, Review, planning,
diagnostics, reporting, governance, and readiness evidence before workflow
execution.

The deployment boundary remains one Page per `WorkflowEngine` execution. `run`
stops at `QualityChecked`; human approval remains explicit. Production helpers
must not bypass the StateMachine, generate multiple pages, or auto-approve.

See [Operations](OPERATIONS_V3.md), [Migration](MIGRATION_V3.md),
[AI Director Platform Guide](AI_DIRECTOR_PLATFORM_GUIDE_V3.md),
[Creative Pipeline Guide](CREATIVE_PIPELINE_GUIDE_V3.md), and
[Knowledge Guide](KNOWLEDGE_GUIDE_V3.md).
