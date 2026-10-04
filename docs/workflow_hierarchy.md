# Workflow Hierarchy

## Purpose

Phase 14 adds a sequential hierarchy without changing the fixed Page workflow:

```text
Project
  -> Chapter
    -> Page
      -> Step
```

The existing `WorkflowEngine` remains the only component that executes Page
steps, selects Agents, validates transitions, and publishes Page events.

## Boundaries

| Component | Responsibility | Must not do |
| --- | --- | --- |
| `ProjectWorkflowEngine` | Project lifecycle, chapter progress, persistence, resume, and Project events | Execute page transitions or call Agents |
| `ChapterWorkflowEngine` | Ordered page selection, chapter progress/review/completion, and Chapter events | Select Agents or modify page state itself |
| `WorkflowCoordinator` | Delegate `Project -> Chapter -> Page` calls | Contain scheduler or transition rules |
| `WorkflowScheduler` | Choose one next page from a `ChapterContext` | Execute a workflow |
| `WorkflowEngine` | Run one Page through its legal automatic steps | Know chapters or projects |

All engines receive `ProjectRepository`, the persistence port, rather than a
local-file implementation. `ProjectLoader` remains a mapping adapter between a
persisted `Page` and `WorkflowContext`.

## Safety rules

- A project or chapter run invokes one Page workflow only.
- The default `PageNumberWorkflowScheduler` chooses the lowest-numbered page
  that is not `Approved`.
- A `QualityChecked` page remains selected until an explicit human `approve`.
- No Project or Chapter operation can auto-approve a page.
- Scheduler replacement is an injected `WorkflowScheduler` protocol; the
  current implementation has no parallel or batch behavior.
