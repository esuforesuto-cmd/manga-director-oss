# Solution Templates

## Purpose

Solution Templates package an approved planning blueprint: a Platform Profile,
capability references, evidence expectations, and review prompts. They provide
consistent starting points without becoming executable automation.

## Requirements

- Declare audience, scope, and excluded actions.
- Reference only known Capability Registry identifiers.
- List required evidence and responsible human reviewers.
- State project, page, storyboard, or quality-review requirements before
  presenting a recommendation.
- Include a v5.0 LTS-compatible fallback with no template adoption.

## Planned families

| Template | Composition goal | Explicit exclusion |
| --- | --- | --- |
| Story-to-review | Organize planning and review information. | Generate images or approve pages. |
| Asset readiness | Assess catalog and dependency evidence. | Modify or distribute assets. |
| Production checkpoint | Present pipeline and quality evidence. | Publish, deploy, or advance a stage. |
| Enterprise review | Combine audit and governance summaries. | Enforce policy or change permissions. |
| SDK integration | Guide optional API/SDK composition. | Install extensions or change callers. |

Human reviewers retain all decisions. The StateMachine remains the sole
validator for every workflow transition.
