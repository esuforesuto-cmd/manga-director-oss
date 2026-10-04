# v2 Hierarchical and Batch Workflow Design

## Hierarchy

```text
Project workflow
  └─ Chapter workflow (one or more ordered chapters)
       └─ Page workflow (one page at a time)
            └─ Step (a named engine operation)
```

The v1 state machine remains the Page workflow:

`Draft → Designed → Reviewed → Storyboarded → PromptBuilt → Generated → QualityChecked → Approved`

There are no v2 backward states. Corrections continue as a re-execution of the current state when permitted by the page policy. `approve` remains an explicit human action and no `run` variant may cross into `Approved` automatically.

## Engine responsibilities

| Engine | Owns | Must not own |
| --- | --- | --- |
| Existing `WorkflowEngine` | one page's state validation, agent selection, execution, page events | chapter ordering, queues, provider selection policy |
| `ChapterWorkflowEngine` | page order, chapter readiness, continuity checkpoints, chapter audit | page transitions or agent-to-agent calls |
| `ProjectWorkflowEngine` | chapter plan, project milestones, aggregate reporting | page state transitions |
| `BatchWorkflowEngine` | scheduling, concurrency limits, retry policy, progress aggregation | calling agents directly or bypassing page-engine checks |

Higher engines submit a page command to the page engine and persist its typed result. They do not infer a state from artifacts, and they cannot call an agent directly.

## Batch execution design

`BatchWorkflowEngine` accepts an immutable `BatchPlan`: target page identities, one permitted step/command, workflow policy version, concurrency limits, priority, idempotency key, and failure policy. It first validates every target against the repository snapshot, then schedules only eligible pages.

Image generation may run in parallel only across different pages that are already `PromptBuilt`. The engine applies configurable limits per project, provider, and worker queue. It preserves each page's single-page lock and records a `BatchItemResult` for every attempted item.

Default failure policy is **continue independent pages, do not approve any page, and report failures**. Retrying uses the same idempotency key and starts from the existing page state. A failed or cancelled item cannot cause another page to advance.

## Continuity and dependencies

Chapter orchestration creates read-only continuity snapshots from approved or specified preceding pages. It can mark a later page as blocked for scheduling when an explicit dependency policy says so, but it cannot create a hidden transition or edit a page's artifacts. Human/editor decisions remain recorded on the affected page.

## Lifecycle and recovery

- Plans and item results are persisted so an interrupted batch can resume.
- Each page command is idempotent and protected by optimistic concurrency.
- A worker acknowledges completion only after the page operation's persistence result is known.
- Observability records correlation IDs from project to batch to page event.
- A reconciliation process reports stranded reservations; it never advances state by itself.

## Acceptance tests required before implementation

Contract tests must demonstrate that concurrent work cannot transition one page twice, that a stale page revision conflicts safely, that batch `run` stops at quality, and that an approval command is never dispatched by a batch worker.
