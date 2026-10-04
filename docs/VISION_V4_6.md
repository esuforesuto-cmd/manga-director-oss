# v4.6 Vision: Creative Intelligence OS

## Vision

v4.6 plans a Creative Intelligence OS above stable v4.5.0. It defines a
local-first intelligence fabric that can connect existing Agent Platform,
Knowledge, Workflow, Creative Intelligence, and Enterprise Platform evidence
without replacing their contracts or becoming an autonomous runtime.

## Desired outcomes

- Define a Unified Creative Context for explicitly supplied, redacted project,
  story, character, asset, workflow, review, and operational evidence.
- Define Cross-Agent Memory as bounded, attributable, consent-aware memory
  references that agents may review but cannot silently write, share, or use to
  execute work.
- Define Creative Reasoning as an explainable planning, comparison, risk, and
  recommendation model rather than an autonomous decision maker.
- Define Adaptive Workflow as human-approved workflow adaptation proposals that
  preserve StateMachine authority and never skip a stage or execute a change.
- Define an Intelligence Hub that composes these read-only signals into a
  transport-neutral dashboard and review packet.

## Design principles

- **Additive:** Preserve v4.5 public Python API, CLI, FastAPI, REST, MCP, Web
  UI, Repository, Workflow, Agent, Plugin, Extension SDK, Provider, and Backend
  contracts.
- **Core authority:** StateMachine, WorkflowEngine, Project, and existing
  Repository interfaces remain canonical.
- **Human accountable:** Context assembly, memory use, reasoning acceptance,
  workflow adaptation, and operational action remain explicit human decisions.
- **Evidence first:** Inputs are caller-supplied, local, attributable, and
  redacted as needed; planning surfaces return immutable reports only.
- **One Page:** Workflow-related evidence is scoped to exactly one existing
  Page and retains storyboard and completed-quality-review gates.
- **Local by default:** v4.6 does not create a Cloud service, autonomous agent,
  long-running task runner, federation runtime, or marketplace operation.

## Non-goals

v4.6 does not authorize autonomous AI decisions or execution, agent dispatch,
automatic workflow mutation, automatic approval, skipped workflow stages,
multi-page generation, hidden memory writes, remote memory synchronization,
cross-tenant data sharing, external service invocation, payment/billing, Cloud
SaaS, distributed runtime, or a Core architecture redesign.

## Migration strategy

| Stage | Additive planning outcome | Compatibility guard |
| --- | --- | --- |
| Context vocabulary | Local context, provenance, freshness, consent, and redaction records. | Existing data models and Repository interfaces remain canonical. |
| Memory references | Attributable, caller-supplied cross-agent memory references and review findings. | No persistence, synchronization, ownership transfer, or implicit access. |
| Reasoning and workflow proposals | Explainable recommendation and adaptation DTOs. | No StateMachine transition, stage bypass, workflow execution, or approval. |
| Intelligence composition | Transport-neutral review packet and dashboard contract. | No presentation dependency, telemetry, publication, or operational action. |
| Future opt-in delivery | Separately approved implementation candidates. | Security, consent, rollback, compatibility, and human-review evidence are required per capability. |

The development branch remains `4.5.x`; this planning cycle does not change the
package version.
