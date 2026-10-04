# Migration Strategy: v5.4 to v5.5

## Status

v5.5 planning is additive and design-only. No installation action, data conversion, configuration update, endpoint change, CLI change, MCP change, Web UI migration, repository-interface change, or workflow migration is required.

## Compatibility strategy

Future lifecycle DTOs and reports must be optional. Existing v5.4 callers continue to operate without lifecycle metadata. The v5.0 LTS public API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, Extension SDK, provider, and backend contracts are mandatory compatibility baselines.

## Future adoption path

1. Add presentation-neutral, opt-in evidence DTOs only.
2. Add read-only report services behind additive SDK and adapter queries.
3. Validate legacy calls, workflow invariants, and explicit unknown evidence.
4. Document a human-operated upgrade and rollback procedure before any supported operational adoption.

## Guardrails

The StateMachine remains the sole transition authority. Every workflow execution produces one Page, stages cannot be skipped, image generation needs a persisted storyboard, and Page approval needs a completed quality review. Lifecycle planning cannot alter these rules.

## Rollback

Because planning adds no runtime or persistent state, no rollback is required. A future optional adoption must be removable by omitting its new report calls and metadata.
