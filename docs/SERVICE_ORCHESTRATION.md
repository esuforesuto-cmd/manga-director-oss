# Service Orchestration

## Scope

`service_orchestration()` creates an advisory ordering of the explicit Service
Registry descriptors. It is a human-review planning report—not an orchestration
engine and not a route resolver.

## Output and boundary

`V48ServiceOrchestrationDTO` holds service ids, a one-Page scope marker, and
explicit flags that the order is advisory and human review is required.
`ServiceOrchestrationReport` never imports, instantiates, invokes, delegates,
schedules, dynamically loads, or routes an existing service.

The existing Runtime, Plugin/Extension SDK, Provider/Backend selection,
delivery adapters, and public APIs remain authoritative. The report cannot
alter StateMachine validation, Workflow execution, persisted-storyboard
requirements, quality-review requirements, or manual approval.
