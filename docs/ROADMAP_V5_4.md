# v5.4 Quality Roadmap

v5.4 starts from the v5.3 Final baseline on the `5.3.x` development branch.
This roadmap is design-only; it does not authorize implementation, automatic
action, or a version change.

## Must

| Issue | Deliverable | Acceptance criteria |
| --- | --- | --- |
| V5.4-01 | Quality evidence contract | Sources, scope, policy revision, provenance, and unknown state are explicit. |
| V5.4-02 | Review Pipeline | Human-owned gate model respects persisted storyboard and completed quality-review prerequisites. |
| V5.4-03 | Quality Metrics | Deterministic metrics expose inputs, thresholds, calculation status, and no hidden defaults. |
| V5.4-04 | Validation Framework | Contract, compatibility, regression, documentation, package, and security findings remain diagnostic. |
| V5.4-05 | Release Governance | Decision packet records sign-off and v5.0 LTS/v5.3 compatibility evidence without publication control. |

## Should

- Provide presentation-neutral dashboard/report DTO mockups plus JSON/Markdown
  renderer design.
- Add fixture strategy for missing evidence, policy revision changes, and
  complete/blocked/unknown status.
- Define a source-of-truth matrix covering StateMachine, tests, CI/CD, and
  release owners.

## Could

- Publish a documentation-only policy catalogue and review-checklist examples.
- Explore historical metric trend contracts after baseline compatibility is
  measurable.

## Won't

- Automatic review, approval, remediation, workflow mutation, CI/CD control,
  tagging, signing, or publishing.
- Core Architecture redesign, provider/backend additions, Cloud SaaS, or
  distributed runtime.
