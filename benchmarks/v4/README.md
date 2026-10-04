# v4 Benchmark Planning

v4 benchmark candidates are design-only, deterministic, provider-free, and
one-Page scoped where workflow context is involved. They measure future DTO
projection cost only; they do not create a workspace/memory/graph/quality
store, mutate a Repository, execute a workflow, generate content, approve a
Page, collect remotely, or perform an external action.

| Candidate | Scope | Required guard |
| --- | --- | --- |
| [workspace](workspace.md) | Unified workspace/session/state/snapshot/timeline projection. | No persistence, transition, or scheduling. |
| [memory](memory.md) | Story/character/world/style/production-memory projection. | No store, remote retrieval, retention, or mutation. |
| [graph](graph.md) | Story/character/asset/relationship/timeline graph projection. | No graph persistence, merge, repair, or remote query. |
| [quality](quality.md) | Creative-quality and editorial-review projection. | No generation, automatic review, approval, or enforcement. |
