# Prompt Pipeline

## Overview

`PromptPipeline` replaces monolithic prompt construction with four independent, replaceable stages:

```text
PromptBuilder → PromptOptimizer → PromptValidator → PromptRenderer
```

Only `PromptPipeline` controls that order. A stage never calls another stage, workflow agent, image provider, or LLM provider.

## Inputs and output

The pipeline derives one `PromptInput` from the current page's Page Design, Storyboard, optional Dialogue support artifact, Character metadata, World metadata, and page number. `PromptBuilder` produces `StructuredPrompt`.

The final `PromptResult` contains:

- `success`
- rendered Markdown `prompt`
- estimated whitespace-token count `tokens`
- validation `warnings`
- template/source/audit `metadata`
- human-readable `messages`

## Stage responsibilities

| Stage | Responsibility |
| --- | --- |
| Builder | Normalizes one page's storyboard, dialogue, design, character, world, and page number into provider-neutral structured sections. |
| Optimizer | Deterministically removes duplicate lines, redundant whitespace, and generic `provider:` / `model:` directives. It does not call an LLM. |
| Validator | Requires page number, purpose, storyboard panels, character name, supported template variables, allowed length, and no configured forbidden words. It raises `ValidationError` on failure. |
| Renderer | Renders validated sections through one Markdown template and returns `PromptResult`. |

`PromptAgent` invokes only `PromptPipeline.run(context)`. It does not load a template or import Builder, Optimizer, Validator, or Renderer.

## Optimization contract

`PromptOptimizer` preserves page design, storyboard panels, character context,
and first-occurrence order. It returns a new structured prompt after removing
only exact duplicate dialogue or normalized text lines and generic provider or
model directives; it never rewrites story intent or calls a provider.

## Configuration

```yaml
default_prompt_template: image_prompt.md
optimizer_enabled: true
validation_enabled: true
```

The composition root builds the pipeline from these values. Disabling a stage is explicit configuration, useful for controlled migration only; production workflows should keep validation enabled.

## Audit and safety

The rendered result records its template name, source, SHA-256 content hash, structured prompt, page number, and enabled-stage settings. The pipeline does not select an image provider, generate an image, or change a page state.

It operates on exactly one `WorkflowContext`, preserving the one-page workflow invariant.

## Runtime boundary

The Prompt Engine is read-only: it derives a prompt only from persisted
workflow artifacts and never starts image generation, invokes an LLM, changes
`WorkflowContext`, or advances the StateMachine. A missing storyboard is a
validation failure, so an incomplete page cannot produce an image prompt.
