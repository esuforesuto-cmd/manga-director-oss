# v3 Architecture

## Status and boundary

This is the authoritative v3 architecture design. It introduces no runtime
feature and changes no v2.7 source or public API. The design is additive:
application services consume existing ports and return transport-neutral DTOs.

## Existing system that remains unchanged

| Existing layer | Authority retained in v3 |
| --- | --- |
| Domain / `StateMachine` | State definitions and legal Page transitions. |
| `WorkflowEngine` | Determines the executable Agent, invokes it, updates state, and publishes events. |
| `Director` | Coordination only; it owns no transition logic. |
| Agent layer | Stateless execution behind the shared Agent interface; Agents never call each other. |
| Repository interface | Project persistence port and canonical project evidence. |
| Provider / image adapter factories | Provider-neutral construction; no provider-specific application branching. |
| Presentation | CLI, FastAPI, MCP, and Web UI remain adapters over application services. |

## Proposed v3 layers

| Layer | Responsibility | Inputs | Outputs | Must not do |
| --- | --- | --- | --- | --- |
| Director | Compare goals, constraints, and legal next steps; formulate advisory strategy. | Page context, policy, StateMachine evidence | Strategy, decision trace, readiness DTO | invoke Agents, transition state, dispatch work |
| Planning | Build task graphs, dependency views, estimates, and previews. | Existing workflow metadata and policies | Execution-plan DTOs | alter `WorkflowEngine` or schedule work |
| Knowledge | Produce bounded projections of project facts, history, and relationships. | Repository interface, redaction policy | Index, snapshot, search, health DTOs | replace persistence, mutate source records implicitly |
| Creative | Represent story-to-review hand-offs and assets as a planned pipeline. | Briefs, knowledge projections, Page state evidence | Creative-plan and checkpoint DTOs | generate images, write prompts, bypass stages |
| Agent | Describe proposed agent capabilities, contracts, and collaboration boundaries. | Agent registry metadata, policies | Capability matrix and assignments | direct agent-to-agent execution |
| Review | Express editorial, consistency, quality, and human-review checkpoints. | Existing review artifacts and policies | Review strategy / evidence DTOs | auto-approve or overrule `ApprovalAgent` |
| Memory | Define retention, provenance, snapshot, and redaction requirements for derived knowledge. | Repository-port projections | Memory lifecycle and health DTOs | store secrets or add a mandatory new database |
| Presentation | Render application DTOs for CLI, FastAPI, MCP, and Web UI. | DTOs only | Stable view models / transport responses | expose internal models or contain workflow logic |

## Dependency direction

```text
Presentation adapters
        ↓
v3 application services (Director / Planning / Knowledge / Creative / Review)
        ↓
existing public ports (Repository, factories, EventBus, StateMachine reads)
        ↓
v2 Core and infrastructure adapters
```

No v2 Core module imports a v3 module. A proposed v3 service may query legal
transition information, but only the existing engine can perform it.

## Execution safety contract

For every plan, report, preview, graph, or recommendation:

1. Its scope is one explicitly identified Page execution.
2. It derives a next step from `StateMachine`, not duplicated transition logic.
3. It returns no callable execution token and does not invoke an Agent,
   Provider, backend, scheduler, or persistence mutation.
4. It treats storyboard persistence, quality review, and human approval as
   existing mandatory guards.
5. It is safe to render through CLI, FastAPI, MCP, and Web UI without exposing
   secrets or internal models.

## Compatibility matrix

| Contract | v3 approach |
| --- | --- |
| Python public API | Preserve existing exports; add only documented opt-in namespaces after a future compatibility review. |
| CLI / FastAPI / MCP / Web UI | Consume shared DTOs; no duplicated workflow rules. |
| Projects and repositories | Preserve current serialization and repository port; knowledge is derived, not authoritative. |
| Plugins / Extension SDK | Add capability descriptors through current registry boundaries; never require a v3-only loader. |
| LLM and image providers | Use metadata and factory contracts only; planning does not call a provider. |
| Workflow invariants | Exactly one Page per execution, no skipped stage, persisted storyboard before generation, quality before approval, no multi-page generation. |

## Architecture decisions for future Issues

- Prefer read-only application services and immutable DTOs for analysis.
- Introduce a new port only when the existing Repository, EventBus, factory, or
  StateMachine read boundary cannot express a reviewed need.
- Keep multi-agent collaboration as a planning graph until a separately
  approved execution model exists.
- Treat memory and knowledge as derived records with explicit provenance,
  retention, redaction, and deletion policy.

See [V3 Architecture index](V3_ARCHITECTURE.md) and
[AI Director Platform](AI_DIRECTOR_PLATFORM.md) for the delivery plan.
