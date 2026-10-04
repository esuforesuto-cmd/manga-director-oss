# v4.2.0 Workflow Regression Verification

The v4.2 integration checks run the following read-only evidence flow:

```text
Project -> Goal -> Planning -> Execution -> Checkpoint -> Supervisor
        -> Human Supervision -> Pipeline -> Reporting -> MCP -> Web UI
```

The existing Repository owns save/reload. v4.2 reports do not save, dispatch,
transition, generate, approve, retry, recover, or publish. Regression tests
retain exactly one Page per workflow execution, no skipped stage, persisted
storyboard before image generation, and completed quality review before
approval.
