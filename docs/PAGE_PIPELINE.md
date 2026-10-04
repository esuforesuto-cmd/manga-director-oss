# Page Pipeline

The Page Pipeline provides a non-executing view of the current one-Page
`WorkflowContext`. It reports the current `PageState`, the persisted storyboard
evidence, and the single next command allowed by the domain StateMachine.

## Required gates

| Gate | Requirement |
| --- | --- |
| Scope | Exactly one existing Page. |
| Storyboard | A persisted `Storyboarded` artifact before image generation. |
| Generation | `generate` must be the StateMachine's next command. |
| Quality | The existing quality stage precedes approval. |
| Approval | The existing approval stage precedes export eligibility. |

The pipeline never calls an image provider or changes an artifact. Its Art
Pipeline result is a readiness signal only, preserving the established prompt
and generation interfaces.
