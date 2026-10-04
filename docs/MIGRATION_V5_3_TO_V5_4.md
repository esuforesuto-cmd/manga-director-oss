# Migration Guide: v5.3 to v5.4

## Status

v5.4.0 is an additive stable release. No data conversion, configuration update,
endpoint change, CLI command change, MCP change, Web UI migration, repository
interface change, or workflow migration is required.

## Optional adoption

Quality Framework DTOs and `UnifiedSDKFoundation.quality_preview`,
`quality_dashboard`, and `quality_maturity` are optional diagnostic APIs.
Existing v5.3 callers can retain their current behavior without supplying any
quality policy, review, validation, observation, or release-criteria metadata.

## Compatibility guardrails

- The StateMachine remains the sole transition authority.
- Every workflow execution remains limited to one Page.
- Image generation still requires a persisted storyboard.
- Page approval still requires a completed quality review.
- Quality reports cannot execute reviewers/tests, control CI/CD, approve,
  publish, persist audits, recover runtimes, or change workflows.

## Rollback

Remove optional calls and metadata to return to v5.3 usage. No data rollback is
needed because the Quality Framework owns no persistent state or action.
