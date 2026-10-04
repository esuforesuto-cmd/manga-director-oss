# Creative Reasoning

Creative Reasoning is the v4.6 design for explaining planning alternatives from
explicitly supplied context. It is decision support, not autonomous reasoning
or content generation.

## Planned reasoning record

| Field | Purpose | Boundary |
| --- | --- | --- |
| Goal and constraints | State the creative objective and non-negotiable constraints. | Does not create or modify a goal. |
| Evidence trace | Link recommendation inputs to context provenance and freshness. | Does not access unprovided or remote data. |
| Alternatives | Compare bounded planning options, assumptions, trade-offs, and dependencies. | Does not select or execute an option. |
| Risk and confidence | Explain uncertainty, inconsistency, safety concerns, and missing evidence. | Does not certify quality, compliance, or approval. |
| Recommendation | Present a human-reviewable next-step proposal and rationale. | Does not delegate, invoke an agent, generate content, or mutate workflow state. |

## Explainability and safety

Every future reasoning output must retain evidence traceability, attribution,
scope, redaction state, confidence limits, and human review requirements. It
must identify when context is incomplete or conflicts rather than inventing a
resolution.

Workflow-linked recommendations remain scoped to exactly one existing Page. The
StateMachine keeps authority over transitions; a recommendation cannot skip a
stage, generate an image, or approve a page.
