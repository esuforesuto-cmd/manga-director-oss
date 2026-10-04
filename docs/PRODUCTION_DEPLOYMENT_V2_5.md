# v2.5.0 Production Deployment Guide

Deploy v2.5.0 through the existing Application services and repository ports.
Validate startup dependencies and configuration, check health and repository
integrity, and use read-only diagnostics before workflow execution.

The deployment boundary remains one page per Workflow Engine execution. `run`
stops at `QualityChecked`; human approval remains explicit. Production helpers
must not bypass the StateMachine, generate multiple pages, or auto-approve.

See [Operations v2.5](OPERATIONS_V2_5.md), [Release Process](RELEASE_PROCESS.md),
and [Migration v2.5](MIGRATION_V2_5.md).
