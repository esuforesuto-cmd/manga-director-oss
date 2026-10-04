# v5.2.0 RC1 Workflow Regression Verification

Automation integration validates advisory metadata alongside a persisted
single-Page project and confirms that repository reload behaviour is unchanged.
The v5 test suite continues to verify the authoritative workflow invariants:

- exactly one Page per execution;
- no skipped StateMachine stage;
- persisted storyboard before image generation; and
- completed quality review before approval.

Automation previews, Intelligence, Governance, Observability, Reliability, and
Lifecycle reports cannot invoke a transition, approve a Page, or mutate a
workflow.
