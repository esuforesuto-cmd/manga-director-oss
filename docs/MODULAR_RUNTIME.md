# Modular Runtime Design

## Scope

v4.8 defines a modular-runtime *design*, not a runtime implementation. The
goal is to make capability ownership and composition predictable while keeping
the current import graph, Plugin/Extension SDK, Providers, Backends, and
workflow execution untouched.

## Logical modules

| Module | Provides | May consume | Must not do |
| --- | --- | --- | --- |
| Core | StateMachine, Project/Page state, workflow legality. | Nothing from platform modules. | Depend on or delegate to a platform runtime. |
| Workspace | Scope and collaboration views. | Explicit project and participant references. | Authorize or execute work. |
| Agent Platform | Descriptors, plans, and coordination evidence. | Explicit context and human instructions. | Autonomously dispatch or self-improve. |
| Knowledge | References, graph, memory, quality, and provenance DTOs. | Caller-supplied repository evidence. | Synchronize, transfer, or mutate knowledge. |
| Production | Pipeline, asset, deliverable, and operations reports. | Existing application services. | Publish, deploy, or mutate a workflow. |
| Enterprise | Governance, portfolio, extension, and reliability evidence. | Explicit reports and policies. | Enforce policy, grant access, or bill. |
| Decision | Options, review, approval-readiness, and trace views. | Supplied evidence. | Decide, approve, or transition state. |

## Future capability descriptor

A future module descriptor may publish: stable module identifier, versioned
capability names, accepted DTO types, produced DTO types, required provenance,
and declared side-effect level. It is a static contract description—not plugin
discovery, dynamic loading, capability execution, network registration, or a
permission system.

## Activation and compatibility

Any future composition is explicitly configured by an application owner and
uses injected existing services. Existing plugins/extensions retain their
current discovery and validation path. No module is disabled, relocated, or
required by v4.8, and no legacy import becomes a facade-only import.

## Admission checklist

A future implementation must prove that it adds rather than replaces an API,
does not import Presentation into Application/Knowledge, preserves the
StateMachine authority and one-Page workflow boundaries, uses completed review
evidence before approval, and has no hidden persistence, dispatch, collection,
or external operation.
