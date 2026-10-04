# v2.7.0 Production Deployment Guide

Deploy v2.7.0 through existing Application services and Repository ports.
Validate startup dependencies and configuration, inspect health and repository
integrity, and use read-only Director, Knowledge, planning, diagnostics,
reporting, and governance evidence before workflow execution.

The deployment boundary remains one Page per WorkflowEngine execution. `run`
stops at `QualityChecked`; human approval remains explicit. Production helpers
must not bypass the StateMachine, generate multiple pages, or auto-approve.

See [Operations](OPERATIONS_V2_7.md), [Migration](MIGRATION_V2_7.md),
[AI Director Guide](AI_DIRECTOR_GUIDE_V2_7.md), and
[Knowledge Guide](KNOWLEDGE_GUIDE_V2_7.md).
