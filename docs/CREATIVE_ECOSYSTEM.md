# Creative Intelligence Ecosystem

The Creative Intelligence Ecosystem is a planning boundary, not a service
runtime. It aligns local evidence from Creative Service descriptors, Plugin
metadata, Workflow Marketplace candidates, Knowledge Exchange records, and
Federation planning records so a human can assess compatibility and trust.

| Participant | Contributes | Prohibited action in v4.5 planning |
| --- | --- | --- |
| Creative Service | Supplied descriptor, capability, provenance, compatibility evidence. | Registration, invocation, remote discovery, telemetry, billing. |
| Plugin / Extension | Manifest, capability, isolation, lifecycle, policy evidence. | Load, execute, permission grant, SDK mutation. |
| Workflow candidate | Profile, one-Page safety, provenance, policy evidence. | Install, publish, execute, bypass StateMachine. |
| Knowledge exchange record | Redacted schema, trace, quality, sharing evidence. | Persist, synchronize, merge, transfer ownership. |
| Federation record | Trust domain, handshake, consent, rollback evidence. | Authenticate, transport, replicate, coordinate. |

The StateMachine remains the source of truth for any existing workflow
transition. See [Federation Architecture](FEDERATION_ARCHITECTURE.md).
