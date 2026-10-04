# v3.4.0 End-to-End Regression Evidence

The mock-only regression suite verifies the existing Application-layer path:

```text
Project -> Chapter -> one Page workflow -> human approval -> save -> reload -> resume
        -> batch / automation / notification / plugin / extension / FastAPI / MCP / Web UI
```

The StateMachine remains the transition authority. Each execution produces one
Page, stages are never skipped, generation requires a persisted storyboard, and
approval requires completed quality review. v3.4 reports are non-executing DTO
projections and do not alter this path.
