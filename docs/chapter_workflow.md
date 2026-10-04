# Chapter Workflow

`ChapterWorkflowEngine` owns the ordered view of a Chapter's Pages. A `Chapter`
stores its identifier, title, page numbers, metadata, and history; Page artifacts
and state remain owned by the Project's Page aggregate.

## Sequential execution

```text
chapter run
  -> ChapterStarted (once)
  -> WorkflowScheduler.next_page()
  -> WorkflowCoordinator delegates one Page to WorkflowEngine
  -> ChapterCompleted (when all Chapter pages are Approved)
```

The initial `PageNumberWorkflowScheduler` sorts by page number and returns only
the first non-approved Page. It is injected through the `WorkflowScheduler`
protocol so a future Plugin may supply another policy without changing the
Chapter engine.

## Progress and review

Chapter metadata records the most recently scheduled page. `review()` records a
summary of page count, approved count, and completion without changing Page
state. Completion is calculated solely from persisted Page states.

## CLI

```bash
manga-director chapter run PROJECT_ID CHAPTER_ID
manga-director chapter status PROJECT_ID CHAPTER_ID
```

`chapter run` does not perform batch work: one invocation delegates at most one
Page workflow.
