# v4.5 Vision: Creative Intelligence Ecosystem

## Vision

v4.5 designs a Creative Intelligence Ecosystem above stable v4.4.0. It defines
how independently owned creative services, plugins, workflow catalog entries,
and knowledge exchange records can describe capabilities and relationships
without making manga-director a hosted service, federation runtime, marketplace
operator, or execution authority.

## Desired outcomes

- Define a Creative Service Platform vocabulary for supplied service identity,
  capability, compatibility, provenance, and human-reviewed availability.
- Define a Plugin Ecosystem model that complements existing Plugin and
  Extension SDK contracts without loading or executing third-party code.
- Define a local Workflow Marketplace exchange model for catalog metadata,
  compatibility, provenance, and policy review without discovery, installation,
  publishing, payment, billing, or workflow execution.
- Define Knowledge Exchange records for redacted knowledge descriptors,
  traceability, quality, and human-approved sharing boundaries.
- Define Federation Architecture trust domains, capability handshakes, and
  interoperability evidence without remote identity or distributed coordination.

## Design principles

- **Additive:** Preserve v4.4 public Python API, CLI, FastAPI, REST, MCP, Web
  UI, Repository, Workflow, Plugin, Extension SDK, Provider, and Backend contracts.
- **Core authority:** The StateMachine, WorkflowEngine, Project, and existing
  Repository interfaces remain canonical.
- **Human governed:** Service admission, capability trust, plugin use,
  knowledge exchange, and federation participation are explicit human choices.
- **Evidence first:** Designs describe supplied local evidence and never write,
  discover, negotiate, synchronize, dispatch, load, execute, publish, pay,
  bill, or call a network service.
- **One Page:** Workflow-related evidence is scoped to exactly one existing
  Page and retains storyboard and completed-quality-review gates.
- **Local by default:** v4.5 is not Cloud SaaS, a marketplace service, or a
  distributed/federated runtime.

## Non-goals

v4.5 does not authorize autonomous AI, automatic approval, multi-page
generation, skipped workflow stages, plugin or extension execution,
marketplace operation, remote discovery, knowledge synchronization, federation
networking, identity/access enforcement, payment/billing, Cloud SaaS,
distributed runtime, or a Core architecture redesign.

## Migration strategy

| Stage | Additive planning outcome | Compatibility guard |
| --- | --- | --- |
| Vocabulary | Service, plugin, exchange, catalog, and federation terminology. | Existing Project, Repository, Workflow, Plugin, and Extension SDK contracts remain canonical. |
| Evidence projection | Immutable compatibility, provenance, policy, and relationship reports. | No write, transition, discovery, install, load, execute, sync, publish, or network action. |
| Trust design | Human review, redaction, ownership, isolation, and rollback requirements. | StateMachine, storyboard, quality-review, and human-approval gates remain authoritative. |
| Future opt-in delivery | Separately approved implementation candidates. | Compatibility, security, ownership, consent, rollback, and operational reviews are required per capability. |

The development branch remains `4.4.x`; this planning cycle does not change the
package version.
