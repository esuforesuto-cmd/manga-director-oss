# v3.5.0 RC1 Workflow Regression Verification

The RC integration flow was verified as a one-Page, read-only projection:

```text
Project -> Knowledge Graph -> Creative Intelligence -> Production Intelligence
-> Platform Analytics -> Governance -> Review -> Save / Reload -> Reporting
-> Diagnostics -> MCP -> Web UI
```

The v3.5 steps consume a supplied `WorkflowContext` and existing Repository
data only. They do not create a Project/Page, execute or skip a workflow stage,
generate an image, persist a graph, complete a quality review, approve a Page,
or save a report. Save/reload is performed by the existing Repository flow.

The StateMachine remains the source of truth: every workflow execution produces
exactly one Page, a persisted storyboard remains required before image
generation, and completed quality review remains required before approval.
