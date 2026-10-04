# Real-time Collaboration Evidence

`V60CreativeProductionPlatformFoundationService.realtime_collaboration()`
provides a deterministic, project-and-workspace-scoped view of caller-supplied
collaboration update evidence. Updates are ordered by sequence and update ID
for diagnostics and presentation preparation.

This is not a transport, event broker, or presence service. It does not
receive, deliver, persist, publish, subscribe to, or replay updates. The
existing Event Bus and Agent Communication contracts remain the owners of
their respective behavior; workspace, approval, and StateMachine boundaries
remain unchanged.
