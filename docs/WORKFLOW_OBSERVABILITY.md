# Workflow Observability

v4.6 Iteration 3 adds `WorkflowObservabilityReport`, an immutable observation
and summary projection over Adaptive Workflow Intelligence. It can describe a
supplied workflow state and empty future trace/metric readiness fields.

The report is diagnostic only. It cannot collect telemetry, monitor, poll,
detect an incident, send an alert, mutate or execute a workflow, schedule work,
retry, recover, skip a stage, generate an image, or approve a page. The domain
StateMachine remains the authority for legal transitions.
