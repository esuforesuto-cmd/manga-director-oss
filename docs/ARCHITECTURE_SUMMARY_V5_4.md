# v5.4.0 Architecture Summary

v5.4 completes the Creative Quality Framework as an optional, additive diagnostic layer above the existing platform architecture. It introduces no new execution path and does not alter workflow, repository, provider, backend, or state-machine ownership.

## Quality Framework scope

- Quality Engine and Review Pipeline provide DTO-based quality observations.
- Validation Engine, Quality Metrics, and Release Criteria express local, deterministic diagnostics and readiness evidence.
- Intelligence, Governance, Audit, Reliability, and Lifecycle reports provide analysis and reporting only.
- The SDK exposes opt-in report helpers; existing SDK entry points remain unchanged.

## Explicit non-actions

The framework never auto-approves, mutates a workflow, executes a review or validation, controls CI/CD, enforces policy, recovers a run, signs artifacts, or publishes a release.

## Invariants and compatibility

The domain StateMachine remains the sole transition authority. Every workflow execution produces exactly one Page; stages cannot be skipped; image generation requires a persisted storyboard; and Page approval requires a completed quality review. The v5.0 LTS public API surface remains compatible.
