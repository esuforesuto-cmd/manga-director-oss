# v3.5.0 Workflow Regression Verification

v3.5 reports consume a supplied one-Page `WorkflowContext` and existing
Repository evidence only. The integration flow is:

```text
Project -> Knowledge Graph -> Creative Intelligence -> Production Intelligence
-> Platform Analytics -> Governance -> Review -> Save / Reload -> Reporting
-> Diagnostics -> MCP -> Web UI
```

No v3.5 report creates a Project/Page, executes or skips a workflow stage,
generates an image, persists a graph or audit, completes review, approves a
Page, or saves a report. The StateMachine remains the source of truth: every
execution produces exactly one Page, a persisted storyboard is required before
image generation, and quality review is required before approval.
