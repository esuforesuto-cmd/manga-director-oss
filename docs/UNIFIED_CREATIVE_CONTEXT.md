# Unified Creative Context

Unified Creative Context is the v4.6 planning contract for assembling a
reviewable, local view of one creative decision. It aligns supplied Project,
story, character, asset, workflow, review, agent, knowledge, and operational
evidence without creating a second source of truth.

## Context model

| Element | Planning responsibility | Required boundary |
| --- | --- | --- |
| Context envelope | Identity, scope, owner, timestamp, provenance, freshness, and redaction metadata. | Caller supplies it; no implicit collection or persistence. |
| Creative references | Links to existing story, character, page, asset, and review evidence. | References do not mutate or duplicate canonical Project/Repository state. |
| Workflow references | Exactly-one-page workflow stage, storyboard, quality-review, and approval prerequisites. | StateMachine remains authoritative; no transition or stage bypass. |
| Cross-agent memory references | Attributable source, consent, relevance, confidence, and conflict findings. | No cross-agent read, write, sharing, merge, or synchronization occurs. |
| Operational references | Supplied quality, reliability, and governance signals. | No monitoring, alerting, remediation, or external operation occurs. |

## Cross-Agent Memory design

Cross-Agent Memory is a reference-and-review model, not a shared mutable memory
store. A future DTO must identify the source, owner, consent state, sensitivity,
redaction state, freshness, intended scope, and supporting evidence. Conflicts
and missing consent are findings for human review.

No future context implementation may silently persist memory, change ownership,
retrieve remote records, synchronize content, message an agent, grant access,
or use memory as authority for an action.

See [Creative Reasoning](CREATIVE_REASONING.md) and
[Intelligence Hub](INTELLIGENCE_HUB.md).
