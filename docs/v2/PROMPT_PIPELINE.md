# v2 Prompt Pipeline Design

## Status and pipeline

```text
Design artifact
  → PromptBuilder
  → PromptOptimizer
  → PromptValidator
  → PromptRenderer
  → immutable rendered prompt artifact
```

Phase 13 implements the Pipeline as deterministic, independently replaceable components. The current Markdown template approach is retained. Templates stay data files with stable identifiers and versions; prompt content is never embedded as a provider-specific string inside domain or workflow code.

## Stage contracts

Each stage receives an immutable `PromptDocument` and returns a new `PromptStageResult`. The result carries `success`, payload/artifacts, messages, warnings, provenance, and validation findings. A stage cannot mutate page state or invoke a workflow transition.

| Stage | Input | Output / responsibility |
| --- | --- | --- |
| `PromptBuilder` | page design, storyboard, dialogue, template selection | normalized structured prompt sections and required variables |
| `PromptOptimizer` | structured prompt | deterministic removal of redundancy, generic provider/model directives, and excess whitespace |
| `PromptValidator` | structured prompt, policy, template schema | errors/warnings for missing panels, unsafe provider fields, length, or consistency |
| `PromptRenderer` | validated structured prompt and Markdown template | provider-neutral rendered Markdown/text plus content fingerprint |

`PromptAgent` now calls only the complete `PromptPipeline` and retains the existing `AgentResult` shape. It does not know individual pipeline stages.

## Template registry

Template metadata includes `template_id`, semantic version, supported prompt schema version, declared variables, intended media/provider capabilities, and content hash. A registry resolves an explicit template ID; it does not select a template by a hidden provider conditional. Plugins may contribute templates through the namespaced plugin registry.

## Validation and auditability

The persisted prompt artifact records source artifact revisions, template ID and hash, pipeline stage versions, optimization provider/model if used, policy version, and a rendered-content hash. This allows a generated image to be traced to the exact prompt without retaining secrets.

Validation errors prevent rendering/generation. Warnings are advisory and are available to review UI/API clients. Optimisation is optional and deterministic; the Prompt Pipeline makes no LLM calls.

## Provider neutrality

The canonical prompt document is provider-neutral. Image-provider-specific translation is an outer adapter concern with declared capability requirements. The `ImageAgent` remains unaware of provider names and delegates only through the image generation port.
