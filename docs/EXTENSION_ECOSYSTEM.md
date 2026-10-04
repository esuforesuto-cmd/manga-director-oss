# Extension Ecosystem and Workflow Marketplace Design

## Goal

Define a safe, local-first governance model for future extension and workflow
catalog discovery while preserving the existing Extension SDK, Plugin, Provider,
Backend, and workflow contracts.

## Extension ecosystem model

An extension candidate is described by a manifest projection containing its
identifier, declared version, capabilities, compatibility range, provenance,
requested boundary, isolation expectation, and review state. The model is
descriptive only: it cannot load an extension, grant a permission, invoke a
capability, persist a registry, or modify the SDK.

## Workflow marketplace model

A marketplace candidate is a catalog projection containing a workflow
identifier, revision, declared input/output contract, StateMachine
compatibility, provenance, license, policy result, known limitations, and
human admission state. It does not perform remote discovery, fetch code,
install content, execute a workflow, publish an entry, accept payment, or bill.

## Admission and compatibility policy

1. Human review verifies source provenance, license, version, compatibility,
   security posture, and rollback evidence.
2. A candidate must declare one-Page scope for workflow use and must not bypass
   storyboard, quality-review, or StateMachine gates.
3. Compatibility is reported against the existing Extension SDK; no SDK method
   is altered by marketplace planning.
4. Any future activation is opt-in, local, reversible, auditable, and subject
   to a separate security and release review.

## Explicit non-goals

The v4.4 design does not deliver a Marketplace service, remote registry,
automatic installation, extension execution, payment, billing, Cloud hosting,
telemetry, distributed runtime, or a new Provider or Backend.
