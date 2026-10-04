# v5.4.0 RC1 Architecture Summary

The Quality Framework is an optional Application-layer diagnostic plane. It
accepts supplied quality policy, review, validation, metric, release, and
observation evidence, then returns immutable DTO reports. It owns no Core
state, repository persistence, WorkflowEngine transition, or presentation route.

`QualityEngineFoundation`, `QualityIntelligenceService`, and
`QualityFrameworkMaturityService` are additive Python/SDK entry points. The
StateMachine remains the source of truth for all Page transitions and approval
requirements.
