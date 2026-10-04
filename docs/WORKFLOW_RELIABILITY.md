# Workflow Reliability

`WorkflowReliabilityAnalyzer` evaluates exactly one existing
`WorkflowContext`. It returns immutable integrity, validation, consistency,
risk, and execution-readiness DTOs derived from the StateMachine planning
surface and persisted context evidence.

The analyzer never invokes `WorkflowEngine`, calls an Agent, mutates a context,
saves a Project, resumes a workflow, or bypasses storyboard and quality-review
requirements. Its readiness result is advisory; only `WorkflowEngine` may run
the StateMachine-approved next step.

```bash
manga-director assurance workflow PROJECT PAGE
```

