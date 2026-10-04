# Operations Automation

v2.5 Iteration 2 introduces planning DTOs only. `MaintenanceSchedulerPlan` and
`CleanupPlan` describe operator-triggered tasks and Repository maintenance
candidates. They never create a timer, queue work, delete a Project, repair
storage, or advance a workflow state.

`OperationsReport` combines health summary input, diagnostics summary,
Repository maintenance, cleanup candidates, and the non-executing schedule.
`ExecutiveSummary` provides a compact release/operations view for a transport
adapter to render.

Operators must review a plan, run repository validation, and use existing
WorkflowEngine-backed commands for any state change. Cloud scheduling,
distributed workers, automatic cleanup, and automatic approval remain out of
scope.
