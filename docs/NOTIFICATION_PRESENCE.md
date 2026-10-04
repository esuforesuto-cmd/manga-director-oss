# Notification & Presence Evidence

`V60CreativeProductionPlatformFoundationService.notification_presence()`
provides a deterministic, project-and-workspace-scoped view of caller-supplied
notification requests and presence update evidence. Presence evidence is
derived only from supplied Collaboration updates whose kind is `presence`.

The report does not prepare or send notifications, connect presence transport,
persist status, subscribe to events, or change memberships. The existing
Notification Service, Event Bus, Agent Communication, Repository interfaces,
and StateMachine authority remain unchanged.
