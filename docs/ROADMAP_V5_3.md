# v5.3 Integration Roadmap

## Baseline

v5.3 starts from v5.2.0 on the `5.2.x` development branch. This is a
design-only roadmap; it authorizes no Connector implementation, network call,
data transfer, event dispatch, credential storage, or API migration.

## Must

| Issue | Purpose / background | Priority | Impact | Estimate | Owner | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V5.3-01 Integration contract inventory | Map existing SDK, Automation, Runtime, Workflow, and Enterprise boundaries. | Must | All integration surfaces | L | Architecture | None |
| V5.3-02 Connector SDK contract | Define transport-neutral descriptor, capability, scope, and compatibility metadata. | Must | SDK, Enterprise | L | SDK / Architecture | V5.3-01 |
| V5.3-03 Data Exchange envelope | Define provenance, schema, classification, consent, and approval metadata. | Must | Automation, Workflow | L | Application / Governance | V5.3-01 |
| V5.3-04 Event Integration reference | Define immutable correlation and provenance references without broker semantics. | Must | Runtime, Automation | M | Runtime / Application | V5.3-01 |
| V5.3-05 Integration Governance | Define policy, audit, privacy, compatibility, and fail-closed validation. | Must | Enterprise, SDK | L | Governance | V5.3-02, V5.3-03 |
| V5.3-06 LTS compatibility plan | Define opt-in equivalence fixtures and legacy-only rollback. | Must | All public surfaces | L | Quality / Architecture | V5.3-01 through V5.3-05 |

## Should

| Issue | Purpose / background | Priority | Impact | Estimate | Owner | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| V5.3-07 Integration preview design | Specify a JSON/Markdown review proposal without action semantics. | Should | SDK, CLI, MCP | M | Developer Experience | V5.3-02 through V5.3-05 |
| V5.3-08 Connector compatibility report | Describe static capability and schema comparison. | Should | SDK, Enterprise | S | Analytics | V5.3-02 |
| V5.3-09 Exchange audit export design | Specify offline audit evidence format. | Should | Governance | M | Documentation | V5.3-03, V5.3-05 |

## Could

- Documentation-only Connector catalogue.
- Data-class comparison report.
- Presentation mock-ups for a human integration review.

## Won't

- Implement Connectors, credentials, remote discovery, network transport,
  automatic synchronization, event brokers, or execution.
- Rewrite Core, StateMachine, WorkflowEngine, Repository, Runtime, or v5.0
  LTS public contracts.
- Add Cloud SaaS, billing, marketplace operations, new Providers/Backends, or
  distributed runtime.
- Permit multi-Page work, skipped stages, image generation without a persisted
  storyboard, or approval without completed quality review.
