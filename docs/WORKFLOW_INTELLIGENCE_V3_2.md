# Workflow Intelligence v3.2

Workflow Intelligence observes the existing one-Page StateMachine. It provides
efficiency, bottleneck, recommendation, timeline, health, and summary DTOs.
Any next-command hint comes exclusively from `StateMachine`; this component
cannot transition a `WorkflowContext`, apply a pipeline profile, or dispatch a
workflow step.

`pipeline-analysis` is a view of the current bottleneck only. In particular,
the QualityChecked-to-Approved boundary remains a human approval decision.

