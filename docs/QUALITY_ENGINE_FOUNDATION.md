# Quality Engine Foundation

`QualityEngineFoundation` combines supplied policy, review, validation, metric,
and release-criteria evidence into `QualityEngineReport`. The report is local,
immutable, and advisory: it cannot run checks, mutate workflow state, approve a
Page, control CI/CD, or publish a release.

`QualityScopeDTO` is limited to exactly one requested Page. The engine delegates
no state transition; `state_machine_authoritative` is always true. Missing
storyboard or completed-quality-review evidence blocks human-review eligibility.

Use `UnifiedSDKFoundation.quality_preview(request)` for an additive Python SDK
entry point. Existing SDK, CLI, FastAPI, MCP, repository, and workflow behavior
is unchanged.
