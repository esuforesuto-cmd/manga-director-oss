# v4.8 Consolidation Roadmap

## Planning baseline

v4.8 starts from stable v4.7.0 on the `4.7.x` development branch. This roadmap
is a planning artifact: it approves no implementation, version change, API
removal, Core rewrite, or automatic migration.

## Must

### M48-01 — Public-contract and duplicate-capability inventory

- **Purpose:** Map public surfaces and repeated report concepts before any
  consolidation work.
- **Background:** v4.7 contains mature specialist modules whose compatibility
  must remain explicit.
- **Priority:** Must.
- **Impact:** Python API, CLI, FastAPI, REST, MCP, Web UI, Repository,
  Workflow, Agent Platform, Knowledge, Production, Enterprise, Decision.
- **Estimate:** M.
- **Owner layer:** Architecture / Application.
- **Dependencies:** None.

### M48-02 — Unified Creative Platform contract design

- **Purpose:** Define common scope, evidence, review, lifecycle, and
  operational packet vocabulary.
- **Background:** Cross-domain dashboards need consistent references without
  duplicating ownership.
- **Priority:** Must.
- **Impact:** Workspace, Knowledge, Production, Enterprise, Decision Platform.
- **Estimate:** M.
- **Owner layer:** Application / DTO design.
- **Dependencies:** M48-01.

### M48-03 — Modular Runtime boundary design

- **Purpose:** Publish dependency direction and capability descriptor rules.
- **Background:** A long-lived platform needs predictable module ownership.
- **Priority:** Must.
- **Impact:** Core, Workspace, Agent Platform, Knowledge, Production,
  Enterprise, Decision Platform.
- **Estimate:** M.
- **Owner layer:** Architecture.
- **Dependencies:** M48-01.

### M48-04 — Unified API Surface compatibility design

- **Purpose:** Specify optional additive facade and legacy-name preservation
  rules.
- **Background:** Simplification must not force migration on v4.7 consumers.
- **Priority:** Must.
- **Impact:** Python API, CLI, FastAPI, REST, MCP, Web UI, Extension SDK.
- **Estimate:** M.
- **Owner layer:** Presentation / Application.
- **Dependencies:** M48-01, M48-02, M48-03.

### M48-05 — Lifecycle Management reference design

- **Purpose:** Align descriptive lifecycle and provenance vocabulary.
- **Background:** Snapshot, timeline, history, and trace reports overlap.
- **Priority:** Must.
- **Impact:** Workspace, Knowledge, Production, Decision, Repository.
- **Estimate:** S.
- **Owner layer:** Application / Knowledge.
- **Dependencies:** M48-01, M48-02.

### M48-06 — Operational Intelligence boundary and metric dictionary

- **Purpose:** Define read-only, source-linked cross-domain indicators.
- **Background:** Existing analytics require safe composition without
  monitoring or operations control.
- **Priority:** Must.
- **Impact:** Production, Enterprise, Analytics, Decision, Web UI, MCP.
- **Estimate:** M.
- **Owner layer:** Application.
- **Dependencies:** M48-02, M48-05.

## Should

| Issue | Purpose | Background | Priority | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S48-01 Contract-equivalence fixtures | Compare legacy and future-facade DTO evidence. | Facades require proof they do not change semantics. | Should | Python, CLI, FastAPI, MCP | M | Quality | M48-04 |
| S48-02 Consolidation naming guide | Publish preferred terms and legacy aliases. | Teams need a stable migration vocabulary. | Should | Documentation, SDK | S | Documentation | M48-01, M48-02 |
| S48-03 Evidence provenance profile | Define shared freshness/redaction/source fields. | Cross-platform summaries need traceability. | Should | Knowledge, Enterprise, Decision | M | DTO design | M48-02, M48-05 |
| S48-04 Deprecation-review process | Define support-window and removal decision rules. | Simplification must be predictable. | Should | Public API | S | Governance | M48-01, M48-04 |

## Could

| Issue | Purpose | Background | Priority | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C48-01 Architecture inventory visualizer | Generate a static ownership/dependency map. | Helps maintainers review consolidation. | Could | Documentation | S | Developer Experience | M48-01 |
| C48-02 Cross-report query design | Explore a caller-supplied report selector contract. | Future dashboard composition may benefit. | Could | Analytics, MCP, Web UI | M | Application | M48-02, M48-06 |

## Won't

- Rewrite the Core domain, StateMachine, WorkflowEngine, or Repository
  interfaces.
- Remove, rename, or require migration from existing public APIs in v4.8.
- Implement autonomous agents, workflow mutation/execution, automatic
  approvals, content generation, Cloud SaaS, billing, marketplace operation,
  new Providers/Backends, or distributed runtime.
- Turn planning documents into a permission to bypass one-Page, storyboard,
  quality-review, or human-approval requirements.

## Milestone sequence

1. **Planning:** complete inventory, vocabulary, architecture, migration, and
   compatibility contracts.
2. **Foundation (future):** add opt-in DTO/facade primitives only after design
   review.
3. **Intelligence (future):** compose caller-supplied, read-only reports.
4. **Governance (future):** describe evidence and policy status without
   enforcement.
5. **Release (future):** prove additive compatibility and production quality.
