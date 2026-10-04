# Creative Pipeline Design

## Purpose

The v3 Creative Pipeline makes creative hand-offs visible as an advisory plan.
It does not replace or reorder the persisted v2 Page workflow.

## Planned pipeline

```text
Story Planning → Chapter Planning → Page Planning → Panel Planning
      → Prompt Building → Image Review → Consistency Review → Quality Review
```

Each arrow is a planned evidence hand-off. The only execution workflow remains:

```text
Draft → Designed → Reviewed → Storyboarded → PromptBuilt → Generated
      → QualityChecked → Approved
```

The persisted storyboard requirement before image generation and completed
quality review before approval remain mandatory.

## Candidate planning components

| Component | Planned output | Existing guard it exposes |
| --- | --- | --- |
| Story Planning | Story goals, theme, and chapter inputs. | No Page transition. |
| Chapter Planning | Chapter rhythm and page-order context. | No multi-page execution. |
| Page Planning | Page purpose, moment, hook, and reader effect. | Exactly one Page scope. |
| Panel Planning | Panel roles, composition intent, dialogue and continuity links. | Storyboard stage remains mandatory. |
| Prompt Building | Template and evidence lineage plan. | Current Prompt Pipeline remains authoritative. |
| Image Review | Visual review criteria and artifact references. | Does not call ImageGenerator. |
| Consistency Review | Character, setting, prop, time, and style risks. | Advisory only. |
| Quality Review | Existing quality dimensions and human decision evidence. | Cannot pass quality or approve. |

## Issue backlog

| ID | Design item | Priority | Dependency |
| --- | --- | --- | --- |
| V3-CP-01 | Creative pipeline DTO and checkpoint map. | P0 | V3-DIR-01, V3-KG-01 |
| V3-CP-02 | Story, chapter, page, and panel planning evidence schema. | P1 | V3-CP-01 |
| V3-CP-03 | Prompt provenance and asset-review hand-off design. | P1 | V3-CP-02 |
| V3-CP-04 | Consistency and quality review strategy design. | P1 | V3-KG-02, V3-DIR-04 |
| V3-CP-05 | Creative pipeline fixtures and compatibility tests. | P0 | V3-CP-01 |

## Design rules

- A creative plan has no side effect and no image-generation capability.
- Revisions are proposed as same-state re-execution options, never as a
  new rejection state or skipped workflow stage.
- A visual review is evidence for a human; it is not quality approval.
- Plans can describe project and chapter context, but they can only recommend
  at most one legal Page action at a time.

See [Creative Pipeline example](../examples/creative_pipeline/README.md).

## v4.2 Autonomous Creative System planning

The v4.2 cycle extends this document with a **design-only** automation model.
It does not add a dispatcher, scheduler, provider call, repository write,
workflow transition, publishing action, or approval authority.

| Pipeline | Proposed planning output | Hard boundary |
| --- | --- | --- |
| Story Pipeline | Goal, narrative context, and review checkpoints. | Cannot create or change a Page. |
| Manga Pipeline | One-page-scoped workflow recommendation. | StateMachine remains the transition authority. |
| Asset Pipeline | Asset evidence and dependency review plan. | Cannot generate, alter, or publish an asset. |
| Review Pipeline | Review evidence, risk level, and escalation packet. | Cannot complete quality review or approve a Page. |
| Publishing Pipeline | Release/publishing checklist and human handoff. | Cannot publish or notify an external system. |

Each proposed handoff is checkpointed, policy-classified, reviewable, and
pausable. A future implementation must fail closed when it cannot prove that
the action is for exactly one Page, follows a legal StateMachine transition,
has a persisted storyboard before image generation, and has a completed
quality review before approval.

| ID | Planning issue | Priority | Dependency |
| --- | --- | --- | --- |
| V42-PIPE-01 | Define pipeline-plan and checkpoint evidence DTOs. | Must | V42-AUTO-01 |
| V42-PIPE-02 | Define one-page scope and StateMachine revalidation rules. | Must | V42-PIPE-01 |
| V42-PIPE-03 | Define review, escalation, and publishing handoff packets. | Should | V42-SUP-01, V42-SAFE-01 |
| V42-PIPE-04 | Define deterministic pipeline simulation fixtures. | Should | V42-PIPE-02 |

See the [v4.2 creative pipeline design example](../examples/creative_pipeline/v4_2_design.md)
and [Pipeline Test Plan](PIPELINE_TEST_PLAN.md).
