# Composable Creative Platform

## Composition model

A composition is a declared set of existing capabilities assembled for one use
case. Reading or validating it starts no service, runs no workflow, and changes
no state.

```text
Solution Template
       |
Platform Profile ----> Feature Packs ----> Capability references
       |                                      |
       +------ evidence and constraints -------+
```

## Module contract

Every proposed composable module declares a namespaced identifier, owner layer,
public surface, compatibility range, required/optional dependencies, evidence
requirements, workflow constraints, security expectations, and legacy
contract-equivalence fixtures.

## Initial Feature Pack candidates

| Pack | Reuse scope | Minimum evidence |
| --- | --- | --- |
| `creative-planning` | Workspace, context, decision, and review summaries. | Storyboard and review references where relevant. |
| `production-operations` | Production, asset, quality, and delivery reporting. | Existing workflow and quality evidence. |
| `enterprise-governance` | Governance, reliability, audit, and executive reports. | Policy and human review references. |
| `developer-integration` | SDK, API, runtime, and extension compatibility guidance. | Public-contract equivalence fixtures. |

## Safety

Missing identifiers, dependencies, versions, or evidence are invalid metadata,
not a cue to select an Agent, Provider, Backend, or workflow. Invalid metadata
cannot bypass StateMachine validation.
