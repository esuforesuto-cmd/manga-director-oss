# v2.2 Scalability Review

This review identifies investigation work, not approved implementation. Every
item keeps the current Core and one-page workflow invariant intact.

| Boundary | Observed scaling risk | Proposed Issue | Priority | Evidence needed |
| --- | --- | --- | --- | --- |
| Workflow | Artifact size may increase step serialization and context-copy cost. | `perf: profile page workflow with realistic artifacts` | P0 | median/p95, memory, state-invariant tests |
| Repository | Whole Project serialization can grow with pages, artifacts, and history. | `perf: characterize repository save/load/list at project scale` | P0 | data-size curve, atomicity, port compatibility |
| Batch | Queue persistence and resume scans can grow with page count. | `perf: benchmark sequential batch plan/resume/retry` | P1 | ordering proof, completed-page skip proof |
| Automation | No runtime exists to profile. | `design: define automation measurement boundary` | P2 | approved runtime scope; no implementation in v2.2 |
| Notification | Synchronous retries may hold callers under repeated failure. | `perf: measure mock notification retry latency` | P1 | deterministic failures, trace/audit coverage |
| Database | Aggregate persistence and query behavior need SQLite/PostgreSQL workloads. | `perf: profile database repository workloads` | P0 | query plan, transaction proof, pool assumptions |
| Plugin | Discovery and manifest processing may grow with installed plugin count. | `perf: benchmark plugin discovery and composition` | P1 | fixture count, lifecycle/compatibility tests |
| Extension SDK | Package validation and entry-point imports need ecosystem-scale fixtures. | `test: expand SDK compatibility and packaging fixtures` | P1 | version matrix, invalid-manifest cases |

## Performance backlog candidates

| Candidate | Status in v2.2 | Guardrail |
| --- | --- | --- |
| Parallel Workflow | Design/benchmark prerequisite only | No actual parallel execution. |
| Async Notification | Design/measurement only | Preserve synchronous provider contract. |
| Streaming LLM | Design/measurement only | No streaming provider behavior. |
| Incremental Save | Investigate behind Repository compatibility tests | No persisted schema break. |
| Lazy Loading | Investigate aggregate access patterns | No hidden workflow state. |
| Repository Cache | Design after invalidation analysis | Do not cache approval or state truth. |
| Batch Scheduler | Profile sequential scheduler first | Preserve page-number/dependency order. |
| Connection Pool | Measure PostgreSQL workloads first | Keep Unit of Work boundary. |

See [Roadmap v2.2](ROADMAP_v2_2.md) and
[Performance Guide](PERFORMANCE_GUIDE.md) for prioritization and method.
