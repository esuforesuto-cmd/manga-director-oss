# Workflow Template Foundation

## Purpose

`WorkflowTemplateDTO` declares a reviewed, single-Page workflow shape and its
required evidence. `WorkflowTemplateFoundation.validate()` reports whether that
metadata is safe for a human-gated automation preview.

## Invariants

- Exactly one Page is represented through the immutable `Literal[1]` count.
- The template carries no stage transition and cannot start or mutate a
  workflow.
- A persisted storyboard and completed quality review remain required whenever
  their evidence keys are declared.
- The StateMachine retains all workflow transition validation.

Templates are advisory metadata only. They do not generate images, bypass a
review, or create a workflow execution.
