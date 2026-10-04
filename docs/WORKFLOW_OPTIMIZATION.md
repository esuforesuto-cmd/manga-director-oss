# Workflow Optimization

## Purpose

`WorkflowOptimizationReport` provides recommendations for evidence coverage,
single-Page template selection, event/Page-reference consistency, and an
explicit human approval boundary.

## Boundaries

The report always records that no optimization was applied and no workflow was
mutated. It cannot reorder, skip, start, or transition workflow stages. The
existing StateMachine keeps authority over one-Page scope, persisted storyboard
requirements, quality review, and Page approval.

The default recommendation for a fully valid preview is to retain the existing
workflow and present the plan to the declared human reviewer.
