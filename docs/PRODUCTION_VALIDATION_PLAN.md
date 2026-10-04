# Production Validation Plan

## Objective

Validate one complete, local Manga Director production project using existing
workflow and production-engine contracts. The validation covers exactly one
Page and does not introduce a new production feature or public API.

## Scenario

- Project: `production-validation`
- Chapter: `production-validation-chapter-1`
- Page: `production-validation-chapter-1-page-1`
- Story: Aki meets the witness at the final train.
- Providers: existing `mock` LLM and image adapters only.

The scenario supplies existing story, character, world, timeline, continuity,
export-target, publishing, quality-score, and human-approval evidence. No
network provider, repository scan, Plugin, or external delivery service is
used.

## Execution Plan

1. Build one `WorkflowContext` in `Draft` with caller-supplied evidence for
   the single Page.
2. Use `Director.default(image_generator="mock", llm_provider="mock")` to
   execute the legal StateMachine commands in order: `design`, `review`,
   `storyboard`, `prompt`, `generate`, `quality`, and `approve`.
3. Confirm the completed context is `Approved`, contains the persisted
   `Storyboarded` artifact before `Generated`, records passing quality
   evidence, and records the supplied human approver.
4. Submit the approved context to the existing read-only v5.6 production
   services: Production Pipeline, Story Engine, Character Engine, Page Engine,
   Review Engine, and Export Engine.
5. Confirm each report is eligible or valid without changing the completed
   context. Export validation means readiness only: no file, bundle, archive,
   publication, or upload is created by this validation.
6. Run the focused production, workflow-assurance, and repository-quality
   tests, followed by Ruff and mypy. Run the full test suite as regression
   evidence when the local environment permits completion.

## Acceptance Criteria

- Exactly one Page advances through every legal StateMachine stage to
  `Approved`.
- The storyboard exists before mock image generation, and quality review
  completes before the human approval record is accepted.
- Story, Character, Page, Review, and Export Engine reports all validate the
  supplied approved Page.
- The review score is 100 with no revision suggestions.
- Print, web, and eBook delivery readiness, release-bundle eligibility, and
  archive-integrity validation are reported without performing delivery.
- The validation uses no external provider, network communication, automatic
  approval, or multi-page workflow execution.
- Only confirmed behavior gaps are recorded as implementation Issues.

## Boundaries

- This is a local deterministic validation scenario, not a real artwork,
  publishing, or remote-provider run.
- `mock://generated-page.png` is adapter evidence, not a persisted image file.
- The Export Engine is intentionally a read-only readiness evaluator. Its lack
  of file creation is an established boundary, not a confirmed gap.
- The source tree, public APIs, dependencies, StateMachine, WorkflowEngine,
  and production-service contracts remain unchanged.
