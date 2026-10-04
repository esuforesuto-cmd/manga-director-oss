# Intelligence Hub

Intelligence Hub is the v4.6 design for composing supplied intelligence signals
into a transport-neutral review packet. It brings context, memory references,
creative reasoning, workflow adaptation proposals, quality, governance, and
operational evidence together for a human decision maker.

## Planned review packet

| Section | Supplied evidence | Prohibited operation |
| --- | --- | --- |
| Context overview | Scope, provenance, redaction, freshness, and ownership. | Collection, persistence, access control, or routing. |
| Memory review | Coverage, relationships, consent, conflicts, and recall readiness. | Memory write/read, synchronization, transfer, or communication. |
| Reasoning review | Alternatives, evidence trace, risk, confidence, and recommendation. | Autonomous choice, agent invocation, or content generation. |
| Workflow review | Adaptation candidate, dependencies, safety, impact, and rollback evidence. | Transition, mutation, execution, scheduling, or recovery. |
| Enterprise review | Governance, reliability, quality, and operational summaries. | Enforcement, monitoring, alerting, remediation, or publication. |

The Hub has no Presentation Layer dependency. CLI, FastAPI, MCP, and Web UI may
only expose a future immutable report through separately approved additive
adapters. The Hub itself has no telemetry, persistence, external connectivity,
or action authority.

See [the architecture report](ARCHITECTURE_V4_6.md).
