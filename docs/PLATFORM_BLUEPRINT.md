# Creative Production Platform Blueprint

## Service map

| Service | First responsibility | Initial contract |
| --- | --- | --- |
| Production Platform | Portfolio and production overview. | Project reference, workspace summary, report. |
| Workspace Service | Multi-workspace navigation and state view. | Workspace identity, membership reference, snapshot metadata. |
| Collaboration Service | Assignment, handoff, review, decision history. | Human-gated task and review DTOs. |
| Knowledge Service | Reference graph and provenance. | Node, edge, source, confidence, retention metadata. |
| Automation Service | Rule/template/event planning. | Plan, policy, event reference, approval checkpoint. |
| Extension Service | Capability discovery and compatibility. | Manifest reference, capability, compatibility report. |

## Implementation sequence

1. Define transport-neutral DTOs and port contracts.
2. Add read-only composition services for existing one-page evidence.
3. Add opt-in adapters without changing existing endpoints or commands.
4. Add governance, audit, and scalability validation before any execution path.

## Prompt economy

All services exchange stable identifiers, concise summaries, provenance, and
approved references. Context is retrieved on demand rather than copied into
each prompt. This minimizes prompt size without discarding review evidence.
