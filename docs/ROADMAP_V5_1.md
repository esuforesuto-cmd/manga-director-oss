# v5.1 Modularization Roadmap

## Baseline

v5.1 starts from v5.0.0 LTS on the `5.0.x` development branch. This roadmap
is design-only. It authorizes no version change, runtime integration, module
loading, or API migration.

## Must

| Issue | Purpose / background | Priority | Impact | Estimate | Owner | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V5.1-01 Capability contract inventory | Identify reusable v5.0 contracts and their source-of-truth owners before composition. | Must | Platform Core, SDK, Runtime, Extensions, Enterprise | L | Architecture | None |
| V5.1-02 Composable module boundary | Define module identifiers, dependencies, evidence, lifecycle, and fail-closed validation. | Must | Platform Core, Runtime | M | Architecture / Application | V5.1-01 |
| V5.1-03 Feature Pack specification | Define curated non-executable packs and compatibility metadata. | Must | SDK, Extensions, Enterprise | M | Application / DX | V5.1-02 |
| V5.1-04 Capability Registry design | Specify local registry DTOs, rules, and offline validation. | Must | Platform Core, SDK, Runtime | M | Application | V5.1-01, V5.1-02 |
| V5.1-05 Platform Profile design | Specify declarative composition profiles and safe legacy fallback. | Must | Runtime, Enterprise | M | Application / DX | V5.1-03, V5.1-04 |
| V5.1-06 Solution Template design | Define human-reviewed blueprints and evidence prompts. | Must | SDK, Enterprise, Extensions | M | Developer Experience | V5.1-03, V5.1-05 |
| V5.1-07 v5.0 LTS compatibility plan | Define equivalence fixtures, support policy, rollback, and migration evidence. | Must | All public surfaces | L | Quality / Architecture | V5.1-01 through V5.1-06 |

## Should

| Issue | Purpose / background | Priority | Impact | Estimate | Owner | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V5.1-08 Composition validation test plan | Produce deterministic validation and invariant fixtures before implementation. | Should | Runtime, SDK, Quality | M | Quality | V5.1-04 through V5.1-07 |
| V5.1-09 Composition visibility design | Specify CLI, REST, MCP, and Web UI discovery views without contract replacement. | Should | CLI, FastAPI, MCP, Web UI | M | Presentation | V5.1-04, V5.1-05 |
| V5.1-10 Feature Pack governance | Define review, ownership transfer, deprecation, and compatibility process. | Should | Extensions, Enterprise | S | Governance | V5.1-03, V5.1-07 |
| V5.1-11 Solution template library plan | Curate starter templates and review evidence. | Should | SDK, Enterprise | S | Developer Experience | V5.1-06 |

## Could

| Issue | Purpose / background | Priority | Impact | Estimate | Owner | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V5.1-12 Static composition diagram generator | Generate documentation-only dependency diagrams. | Could | Documentation | S | Developer Experience | V5.1-04 |
| V5.1-13 Profile comparison report | Compare supplied profile metadata for planning. | Could | Enterprise, SDK | S | Analytics | V5.1-05 |
| V5.1-14 Template example catalogue | Publish non-executable composition examples. | Could | Documentation, SDK | S | Documentation | V5.1-06 |

## Won't

- Remove or rewrite v5.0 LTS contracts, Core, StateMachine, WorkflowEngine, or
  Repository.
- Add automatic loading, routing, execution, approval, policy enforcement, or
  external publication.
- Add Cloud SaaS, billing, marketplace operations, new Providers/Backends, or
  distributed runtime.
- Permit multiple Pages per workflow execution, skipped stages, image creation
  without a persisted storyboard, or approval without a completed quality
  review.

## Milestones

1. **Planning:** contracts, migration, and quality strategy (this phase).
2. **Foundation:** additive descriptors and offline validation only.
3. **Composition:** optional SDK/API discovery adapters backed by equivalence
   fixtures.
4. **Maturity:** governance and compatibility evidence; no forced migration.
