# v5.0 Platform Consolidation Roadmap

## Baseline and planning constraint

v5.0 starts from stable v4.8.0 on the `4.8.x` development branch. This is an
issue-driven design roadmap: it authorizes no feature implementation, version
change, Core rewrite, API removal, data migration, autonomous execution, or
external operation.

## Must

### V5-01 — Public contract and module inventory

- **Purpose:** Establish the authoritative inventory of public contracts and
  duplicate capability vocabulary from v2 through v4.
- **Background:** Consolidation is unsafe without knowing each owner and
  supported consumer surface.
- **Priority:** Must.
- **Impact:** Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow,
  Workspace, Knowledge, Agents, Production, Enterprise, Decision, Ecosystem.
- **Estimate:** L.
- **Owner layer:** Architecture / Application.
- **Dependencies:** None.

### V5-02 — Unified Creative Context contract

- **Purpose:** Specify stable cross-domain scope, evidence, provenance,
  freshness, and redaction references.
- **Background:** Existing summaries overlap but must not create shared
  persistence or change owner records.
- **Priority:** Must.
- **Impact:** Workspace, Knowledge, Agents, Production, Enterprise, Decision,
  Ecosystem, Repository.
- **Estimate:** M.
- **Owner layer:** Application / Knowledge DTO design.
- **Dependencies:** V5-01.

### V5-03 — Unified Creative Platform composition model

- **Purpose:** Define the optional platform packet and ownership boundaries for
  cross-domain read-only composition.
- **Background:** v4.8 established a vocabulary; v5 needs a single governed
  model without another source of truth.
- **Priority:** Must.
- **Impact:** All affected modules, Python API, MCP, Web UI.
- **Estimate:** L.
- **Owner layer:** Architecture / Application.
- **Dependencies:** V5-01, V5-02.

### V5-04 — Unified API consolidation plan

- **Purpose:** Specify additive facade contracts, transport mapping, aliases,
  equivalence fixtures, and deprecation review rules.
- **Background:** Simplification must be opt-in for every v4.8 client.
- **Priority:** Must.
- **Impact:** Python API, CLI, FastAPI/REST, MCP, Web UI, Extension SDK.
- **Estimate:** L.
- **Owner layer:** Application / Presentation.
- **Dependencies:** V5-01, V5-02, V5-03.

### V5-05 — Unified Runtime boundary design

- **Purpose:** Define declared module descriptors and dependency direction.
- **Background:** Module consolidation needs visibility without dynamic runtime
  replacement.
- **Priority:** Must.
- **Impact:** Workspace, Knowledge, Agents, Production, Enterprise, Decision,
  Ecosystem, Core.
- **Estimate:** M.
- **Owner layer:** Architecture.
- **Dependencies:** V5-01, V5-03.

### V5-06 — Unified SDK compatibility design

- **Purpose:** Define typed opt-in client helpers that delegate to current
  public services.
- **Background:** Consumers need gradual adoption without an SDK lock-in.
- **Priority:** Must.
- **Impact:** Python API, Plugin, Extension SDK, CLI, MCP.
- **Estimate:** M.
- **Owner layer:** SDK / Developer Experience.
- **Dependencies:** V5-02, V5-04, V5-05.

### V5-07 — v4.x to v5.0 migration and compatibility plan

- **Purpose:** Document zero-conversion adoption, rollback, support window,
  and contract regression requirements.
- **Background:** Public compatibility is a release condition, not an intent.
- **Priority:** Must.
- **Impact:** All public surfaces and existing repositories/workflows.
- **Estimate:** M.
- **Owner layer:** Architecture / Documentation / Quality.
- **Dependencies:** V5-01 through V5-06.

## Should

| Issue | Purpose | Background | Priority | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V5-08 Contract-equivalence fixture catalogue | Specify fixtures comparing legacy and facade results. | Additive composition needs executable proof. | Should | Python, CLI, REST, MCP, Web UI | M | Quality | V5-04, V5-07 |
| V5-09 Common evidence vocabulary | Align finding, recommendation, review, status, and source metadata. | v2-v4 report families use overlapping terms. | Should | Knowledge, Production, Enterprise, Decision | M | DTO design | V5-02, V5-03 |
| V5-10 Module ownership map | Publish a static module/dependency visual. | Reviewers need a concise consolidation map. | Should | Architecture, Developer Experience | S | Architecture | V5-01, V5-05 |
| V5-11 SDK migration examples | Design legacy-to-SDK examples without replacing current usage. | Adoption must remain voluntary. | Should | Python, Extension SDK | S | Developer Experience | V5-06, V5-07 |

## Could

| Issue | Purpose | Background | Priority | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V5-12 Static API inventory generator | Generate a documentation-only public-surface catalogue. | Reduces future inventory drift. | Could | Documentation | M | Developer Experience | V5-01 |
| V5-13 Unified report selector design | Explore caller-supplied report selection for a dashboard. | May reduce adapter duplication later. | Could | MCP, Web UI, Analytics | M | Application | V5-03, V5-04 |
| V5-14 Deprecation review board process | Formalize approval criteria for a future alias/deprecation decision. | Long-lived compatibility needs governance. | Could | Public API, SDK | S | Governance | V5-07, V5-08 |

## Won't

- Rewrite or replace Core, StateMachine, WorkflowEngine, or Repository.
- Remove/rename current public APIs or require v4.x data/API migration.
- Implement automatic workflow action, approval, Agent dispatch, policy
  enforcement, service routing, persistence unification, or telemetry.
- Add Cloud SaaS, billing, marketplace operation, new Providers/Backends, or
  distributed runtime.
- Bypass exactly-one-Page scope, stage validation, storyboard persistence,
  completed quality review, or explicit human approval.

## Milestone sequence

1. **Planning:** inventory, vision, architecture, API/SDK/runtime/context
   contracts, migration, and quality gates.
2. **Foundation (future):** additive context and descriptor DTOs.
3. **Composition (future):** opt-in facade and SDK helpers backed by
   equivalence fixtures.
4. **Maturity (future):** docs, governance review, and deprecation review.
5. **Release (future):** compatibility, package, performance, security, and
   documentation evidence; no automatic migration.

