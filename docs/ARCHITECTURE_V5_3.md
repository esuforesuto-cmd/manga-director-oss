# v5.3 Architecture: Creative Integration Framework

## Architecture decision

v5.3 proposes a declarative Integration Plane above the optional Automation
Framework. It reads caller-supplied connector descriptors, exchange envelopes,
event references, and governance evidence to produce reviewable plans. It is
not a network client, event broker, credential store, synchronization engine,
or workflow controller.

```text
Python API | CLI | FastAPI/REST | MCP | Web UI | Unified SDK
                              |
          Optional Integration Planning / Diagnostic adapters
                              |
 Connector SDK | Exchange Contracts | Event References | Governance
                              |
     Automation Framework | Unified Platform | Existing services
                              |
 Project | Repository | WorkflowEngine | StateMachine | adapters
```

## Responsibility boundaries

| Element | Planned responsibility | Explicitly excluded |
| --- | --- | --- |
| Integration Framework | Compose local Connector and exchange evidence into a review proposal. | Connect, synchronize, route, or mutate data. |
| Connector SDK | Define transport-neutral capability, scope, and compatibility contracts. | Load plugins, hold credentials, or invoke a service. |
| Event Integration | Refer to immutable event provenance and correlation metadata. | Dispatch, queue, retry, replay, or handle an event. |
| Data Exchange | Define classified envelopes, schema references, and human approval boundaries. | Import, export, persist, transform, or transmit data. |
| Integration Governance | Report policy, consent, provenance, and audit requirements. | Enforce policy, grant permission, or approve work. |

## Dependency direction

The Integration Plane may read public Automation, SDK, Workflow, Runtime, and
Governance DTOs. Existing owners must not depend on Integration metadata. Only
the existing StateMachine validates any future workflow transition.
