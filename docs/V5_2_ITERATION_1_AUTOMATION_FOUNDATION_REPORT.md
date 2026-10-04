# v5.2 Iteration 1 Automation Foundation Report

## Outcome

v5.2 Iteration 1 adds a typed, rule-based Automation Foundation while preserving
the v5.0 LTS public surface. The addition provides human-gated planning and
diagnostics only; it does not implement autonomous judgement, self-learning,
workflow execution, or event delivery.

## Delivered components

| Component | Delivered responsibility | Explicitly excluded |
| --- | --- | --- |
| Automation Engine | Builds an advisory plan from known template, rule, and event metadata. | Execution, scheduling, persistence, and workflow mutation. |
| Rule Engine | Deterministically checks required evidence and safety flags. | Inference, automatic decisions, approval, and self-learning. |
| Workflow Templates | Validates one-Page, human-reviewed evidence requirements. | Starting or changing a workflow. |
| Event Bus | Maintains local provenance records for previews. | Delivery, queues, handlers, retry, replay, and networking. |
| Automation Registry | Holds explicit local templates and rules. | Dynamic discovery, plugin loading, activation, and runtime changes. |

## Human-in-the-loop and workflow safety

Automation plans require an explicit approval boundary before they can be
eligible for human review. They stay non-executing even when eligible. The
StateMachine remains the source of truth: no template, rule, event, registry,
engine, or SDK method can transition a workflow. Single-Page scope,
storyboard-before-image, and quality-review-before-approval stay under the
existing domain rules.

## Compatibility

The feature is opt-in through `UnifiedSDKFoundation.automation_preview()` and
new DTOs exported by `manga_director.platform`. Existing Python APIs, workflow
behaviour, repository interfaces, CLI, FastAPI, MCP, and Web UI are untouched.
Version remains `5.1.0` on the 5.1.x development branch.

## Quality evidence

- Automation Engine, Rule Engine, Workflow Template, Event Bus, and Automation
  Registry contract tests cover the non-execution and human-review boundaries.
- v5 platform/composition regression tests verify additive SDK compatibility.
- Quality gates are recorded in [V5_2_QUALITY_GATES.md](V5_2_QUALITY_GATES.md).

## Deferred work

Rule enforcement, automatic task execution, event transport, retries,
scheduling, remote registries, plugin discovery, persistence, Cloud operation,
and autonomous AI remain outside this iteration.
