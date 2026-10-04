# Event-Driven Automation Design

## Event model

An Event Record represents caller-supplied evidence that something occurred:
for example, a storyboard was persisted, a review was completed, or a human
requested a planning refresh. It has an event ID, producer, timestamp,
provenance, subject reference, and optional correlation ID.

## Constraints

- Events are immutable planning inputs and do not trigger handlers.
- Event ordering is descriptive; no queue, retry, delivery guarantee, or
  background processing is introduced.
- An event cannot cause image generation, stage advancement, approval,
  publication, provider selection, or configuration change.
- Future event consumers must validate the current authoritative workflow
  state; event history alone can never authorize a transition.

## Candidate diagnostics

The future design may report duplicate correlation IDs, missing provenance,
unsupported subjects, and stale event evidence. It must not silently dedupe,
replay, persist, or remediate an event.
