# Vision v4: Creative Operating System

## Project Vision

v4 plans the next stage of manga-director as a Creative Operating System: an
explainable, human-led operating model that connects Project, Story, Character,
Asset, production process, and quality evidence. It does not turn the product
into an autonomous AI system.

## Design Principles

- Preserve the existing one-Page StateMachine as the sole workflow authority.
- Add bounded, typed, local, read-only projections before any persistence or
  operational authority is considered.
- Keep human creative judgment, completed quality review, and explicit approval
  mandatory.
- Prefer explainable provenance and deterministic fixtures over opaque scoring.
- Admit changes incrementally through compatibility and rollback evidence.

## Non-Goals

v4 planning excludes autonomous AI execution, automatic approval, workflow
automation, a new database, Cloud SaaS, marketplace, distributed runtime, and
a Core Architecture rewrite.

## Migration Strategy

| Stage | Additive outcome | Compatibility boundary |
| --- | --- | --- |
| Foundation | Define workspace, memory, graph, and quality vocabulary as DTOs. | Existing Python API, Repository, Workflow, CLI, FastAPI, MCP, and Web UI stay canonical. |
| Projection | Read existing Project/Repository/WorkflowContext evidence into optional views. | No writes, StateMachine changes, or serialization changes. |
| Review | Compare deterministic fixtures and make provenance visible. | Existing storyboard, quality, and approval gates remain mandatory. |
| Opt-in delivery | Expose reviewed DTOs through additive transport endpoints. | Existing commands and routes retain their behavior. |

No v4 implementation is authorized by this planning document.
