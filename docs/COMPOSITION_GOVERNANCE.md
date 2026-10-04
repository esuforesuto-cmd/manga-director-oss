# Composition Governance

`CompositionGovernanceService` evaluates a supplied
`ModuleCompositionReport` against an advisory `CompositionPolicyDTO`. The
policy explicitly retains StateMachine authority, one-Page scope, persisted
storyboard before image generation, completed quality review before approval,
and human review.

The resulting compliance report indicates metadata validity, legacy fallback,
and preserved public contracts. It never confirms compliance automatically,
enforces policy, grants permission, changes a workflow, or persists a policy.

Use `CompositionPlatformMaturityService` or
`UnifiedSDKFoundation.composition_maturity()` for the combined report.
