# v5.2 Automation Roadmap

## Baseline

v5.2 starts from v5.1.0 on the `5.1.x` development branch. This is a
design-only roadmap. It authorizes no version change, automatic action,
scheduler, event bus, persistence, or API migration.

## Must

| Issue | Purpose / background | Priority | Impact | Estimate | Owner | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V5.2-01 Automation contract inventory | Identify existing workflow and composition boundaries before defining automation metadata. | Must | Workflow, Runtime, Composition, SDK, Governance | L | Architecture | None |
| V5.2-02 Workflow Template contract | Specify single-Page templates, required evidence, and validation findings. | Must | Workflow, SDK | M | Application | V5.2-01 |
| V5.2-03 Event Record contract | Define immutable local event/provenance DTOs with no dispatch semantics. | Must | Runtime, Composition | M | Application | V5.2-01 |
| V5.2-04 Rule Engine contract | Define deterministic, explainable, side-effect-free rule evaluation. | Must | Workflow, Composition, Governance | L | Application / Governance | V5.2-02, V5.2-03 |
| V5.2-05 Automation Plan contract | Define plan preview, approval boundary, evidence, and no-op execution boundary. | Must | Workflow, SDK, Composition | M | Application | V5.2-02 through V5.2-04 |
| V5.2-06 Automation Governance | Define policy, audit, approval, compatibility, and fail-closed validation. | Must | Governance, SDK | M | Governance | V5.2-04, V5.2-05 |
| V5.2-07 LTS compatibility plan | Define v5.0/v5.1 equivalence fixtures, opt-in use, and metadata-only rollback. | Must | All public surfaces | L | Quality / Architecture | V5.2-01 through V5.2-06 |

## Should

| Issue | Purpose / background | Priority | Impact | Estimate | Owner | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V5.2-08 Automation simulation design | Describe plan outcomes for supplied evidence without running an action. | Should | Workflow, Runtime | M | Application | V5.2-05 |
| V5.2-09 Rule explanation report | Specify JSON/Markdown explanation and conflict reporting. | Should | SDK, Governance | S | Developer Experience | V5.2-04, V5.2-06 |
| V5.2-10 Automation observability design | Define local plan/event diagnostic records with no telemetry. | Should | Runtime, Governance | S | Operations | V5.2-03, V5.2-05 |
| V5.2-11 Presentation preview design | Specify optional CLI/REST/MCP/Web UI plan previews. | Should | CLI, FastAPI, MCP, Web UI | M | Presentation | V5.2-05, V5.2-07 |

## Could

| Issue | Purpose / background | Priority | Impact | Estimate | Owner | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V5.2-12 Static rule catalogue | Generate documentation-only rule inventory. | Could | Documentation | S | Developer Experience | V5.2-04 |
| V5.2-13 Template comparison report | Compare supplied template metadata. | Could | SDK, Enterprise | S | Analytics | V5.2-02 |
| V5.2-14 Audit export design | Specify offline audit-report export shape. | Could | Governance | M | Documentation | V5.2-06 |

## Won't

- Implement automatic execution, dispatch, scheduling, retry, routing, policy
  enforcement, approval, or state mutation.
- Rewrite Core, StateMachine, WorkflowEngine, Repository, Runtime, or v5.0 LTS
  public contracts.
- Add remote event brokers, Cloud SaaS, billing, marketplaces, new
  Providers/Backends, or distributed runtime.
- Accept multi-Page workflow work, skipped stages, image generation without a
  persisted storyboard, or approval without a completed quality review.

## Milestones

1. **Planning:** contracts, governance, migration, and quality strategy.
2. **Foundation:** additive DTOs and offline diagnostics only.
3. **Intelligence:** simulation and explanation reports only.
4. **Maturity:** compatibility, audit, and reliability evidence; execution
   remains a separately approved future decision.
