# Automation Platform

## AI Native Automation

v6.0 designs an event-aware, rule-based planning layer for Story, Character,
Page, Review, Export, and platform operations. A plan may recommend a next
action, identify prerequisites, and request human approval; it cannot dispatch
work or mutate the workflow.

## Contract model

Automation contracts carry a template reference, event reference, rule
reference, policy reference, input evidence, predicted output reference, and
approval checkpoint. Rules are deterministic where possible and preserve a
decision/audit trail.

## Safety boundary

StateMachine remains authoritative for each Page transition. A persisted storyboard
is required before image generation, and a completed quality review
is required before approval. Future automation must call existing transition
validation rather than bypass it.

## Research tracks

- Event ordering and idempotency.
- Rule versioning and policy validation.
- Human escalation and emergency stop semantics.
- Bounded retries and recovery planning.
- Prompt-context minimization using approved references.
