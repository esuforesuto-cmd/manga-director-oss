# v5.1.0 RC1 Workflow Regression Verification

Composition metadata cannot alter a Project, Page, Repository, WorkflowEngine,
or StateMachine transition. RC integration verification confirms that reports
are planning-only and retain StateMachine authority.

The following invariants remain unchanged:

- one workflow execution produces exactly one Page;
- no workflow stage can be skipped;
- image generation requires a persisted storyboard; and
- page approval requires a completed quality review.

Composition Governance references these requirements but never enforces or
overrides them. Repository save/reload remains an existing owner operation and
is not part of the Composition Engine.
