# v5.2 Architecture: Creative Automation Framework

## Architecture decision

v5.2 adds a declarative automation planning plane above the existing
Composition Platform. It accepts supplied templates, event records, rules, and
evidence references and returns reviewable plans and diagnostics. It is not an
event processor, scheduler, rule executor, or workflow controller.

```text
Python API | CLI | FastAPI/REST | MCP | Web UI | Unified SDK
                              |
            Optional Automation Planning / Diagnostics adapters
                              |
 Workflow Templates | Event Records | Rule Engine | Governance
                              |
       Composition Platform | Unified Platform | Existing services
                              |
 Project | Repository | WorkflowEngine | StateMachine | adapters
```

## Responsibility boundaries

| Element | Planned responsibility | Explicitly excluded |
| --- | --- | --- |
| Workflow Template | Declare a single-Page workflow shape and required evidence. | Start, alter, or skip a workflow stage. |
| Event Record | Carry supplied occurrence/provenance metadata. | Dispatch a handler, schedule work, or mutate a source. |
| Rule Engine | Evaluate supplied metadata for eligibility and findings. | Execute rules, select goals, or repair state. |
| Automation Plan | Present a human-reviewable proposed action boundary. | Invoke services or create a task. |
| Automation Governance | Validate policy/evidence/approval requirements. | Enforce policy, grant permission, or approve a Page. |

## Dependency direction

Automation planning may read public DTOs from Workflow, Runtime, Composition,
SDK, and Governance. Existing owners must not depend on Automation Framework
metadata. State transitions continue through the existing StateMachine only.

## Future sequence

1. Define DTOs and offline validation with no runtime integration.
2. Add template, rule, and event diagnostics only after contract fixtures.
3. Add optional presentation previews only after compatibility review.
4. Consider any execution separately; no v5.2 planning issue authorizes it.
