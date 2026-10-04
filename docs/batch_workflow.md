# Batch Workflow

## Scope

`BatchWorkflowEngine` is a persisted orchestration layer above the existing
Project and Page workflows. It collects eligible Pages from one or more
Chapters, creates a Queue, delegates each Queue item to one Page-scoped Worker,
and records progress and failures. It does not import Agents or call a
StateMachine directly.

At the aggregate boundary, the Batch runtime starts and refreshes the existing
`ProjectWorkflowEngine`; Page execution itself remains delegated to the Worker
and the unchanged `WorkflowEngine`.

```text
BatchWorkflowEngine
  -> ExecutionPlanner
  -> ExecutionQueue
  -> Worker (one Page)
  -> WorkflowEngine
```

Every Worker invocation receives exactly one `WorkflowContext`. The existing
Page engine still enforces all state transitions, storyboard requirements,
quality review, and explicit approval.

## Persistence and recovery

Each `BatchRecord` is stored in `Project.workflow["batches"]` and includes:

- Queue items and predecessor dependencies
- completed, failed, and pending status
- selected Chapters and execution policy
- logs and lifecycle events

`batch resume` runs pending pages only. Completed Queue items are never sent to
a Worker again. On failure, later items remain pending because their dependency
has not completed; `batch retry` requeues failed items only, then continues
previously pending work in order.

## Events

- `BatchStarted`
- `BatchCompleted`
- `BatchPaused`
- `BatchResumed`
- `BatchFailed`

The events are persisted in the Batch record and published through the existing
`EventBus` interface.

## CLI

```bash
manga-director batch run PROJECT_ID --id BATCH_ID [--chapter CHAPTER_ID]
manga-director batch resume PROJECT_ID BATCH_ID
manga-director batch retry PROJECT_ID BATCH_ID
manga-director batch status PROJECT_ID BATCH_ID
```

`--chapter` may be supplied more than once. Without it, the planner includes
all Project Chapters. Initial planning uses ascending Page number only.
