# Adaptive Workflow Foundation

v4.6 Iteration 1 adds `AdaptiveWorkflowFoundationReport` with immutable
adaptation-proposal, safety, and summary DTOs. It shows the prerequisites a
human must review before considering an adaptation; it does not edit or run a
workflow.

`V46IntelligenceFoundationService.adaptive_workflow()` retains exactly-one-page
scope and records StateMachine authority, storyboard, quality-review, human
approval, and rollback requirements. Workflow mutation, execution, scheduling,
retry, recovery, stage skipping, and automatic action remain disabled.

The existing domain StateMachine remains the only authority that may validate a
legal workflow transition.
