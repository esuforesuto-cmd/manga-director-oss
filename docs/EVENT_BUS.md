# Production Event Bus

The v5.7 Event Bus report projects events already present in the current
one-Page `WorkflowContext`. It does not publish, subscribe, queue, retry, or
deliver events.

The existing EventBus implementation remains the sole event-delivery owner.

## Public boundary

Use `manga_director.events.EventBus` or `MemoryEventBus` for existing
`WorkflowEvent` delivery. `V57ProductionOrchestrator.event_bus()` is a
read-only production report over events already present in one supplied
`WorkflowContext`; it does not publish, subscribe, or alter workflow state.
