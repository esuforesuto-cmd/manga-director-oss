# v5.3 Vision: Creative Integration Framework

## Vision

v5.3 designs a **Creative Integration Framework** that lets manga-director
describe and review integrations with external creative tools and services
without transferring workflow authority, approval, or execution rights.

## Mission

Make external data exchange and Connector intent explicit, portable,
auditable, and human-reviewed while preserving the local v5.0 LTS workflow.

## Principles

1. **Integration is opt-in.** Existing callers require no Connector, event, or
   external-service configuration.
2. **Human approval precedes exchange.** A proposal never connects, sends, or
   imports data by itself.
3. **StateMachine authority is absolute.** One execution remains one Page;
   workflow stages, storyboard, and quality-review rules are unchanged.
4. **Contracts precede transport.** SDK DTOs and compatibility fixtures are
   designed before credentials, network clients, or runtime adapters.
5. **Governance is explicit.** Ownership, provenance, data classification,
   scope, and audit evidence are required for every future Connector proposal.

## Non-goals

- Autonomous decisions, automatic synchronization, external execution, or
  self-learning.
- Credential handling, network clients, hosted services, Cloud SaaS,
  marketplace publication, billing, or distributed runtime.
- Core, StateMachine, WorkflowEngine, Repository, Runtime, or public API
  redesign.

## Migration strategy

v5.3 is designed as additive metadata above v5.2. A legacy-only v5.0 LTS path
remains valid; removing optional Integration metadata requires no data or
workflow rollback.
