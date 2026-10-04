# Human-in-the-Loop Design

## Mandatory approval points

| Point | Human decision | Existing authority retained |
| --- | --- | --- |
| Planning acceptance | Choose, revise, reject, or defer an agent plan. | No plan executes automatically. |
| Creative change | Decide whether a proposed story, character, or visual change is adopted. | Repository and authoring flows remain canonical. |
| Storyboard confirmation | Confirm persisted storyboard evidence before generation. | Existing storyboard gate remains mandatory. |
| Quality review | Complete the established quality review. | Only completed review enables approval. |
| Page approval | Explicitly approve a Page after review. | StateMachine remains the source of truth. |

## Feedback loop

Feedback is modelled as a bounded DTO: reviewer, target proposal, rationale,
references, timestamp, and disposition. It is not sent automatically and does
not create a durable decision record in v4.1.

## Manual override

An override is a human-authored decision with rationale and impact summary. It
can only be represented by a future planning DTO; it cannot override the
StateMachine, Repository validation, storyboard requirement, or quality-review
requirement.

## Decision history

Decision history is a future audit-friendly projection. Before persistence is
considered, it requires retention policy, access control, redaction, integrity,
export, and human governance design.

## v4.1 Iteration 3 foundation

`V41PlatformAssuranceService.human_review()` exposes immutable approval-request,
approval-result, review-session, feedback, and decision-history DTOs for one
existing page. The request is not dispatched; the review is not completed; the
feedback is not submitted; and the result cannot approve or transition a Page.

The implementation deliberately reports `quality_review_completed=False` and
`approved=False`. It is therefore impossible for this foundation to bypass the
persisted-storyboard and completed-quality-review gates enforced by the existing
StateMachine.
