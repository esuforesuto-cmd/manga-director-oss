# Project Workflow

`ProjectWorkflowEngine` manages the persisted Project aggregate above the
existing Page workflow. It creates a Project with `chapter-1`, records the
current chapter/page position, stores lifecycle history, and supports a safe
resume through the repository port.

## Lifecycle

```text
project create
  -> ProjectStarted (once)
  -> delegate current Chapter
  -> ProjectCompleted (only when every Chapter page is Approved)
```

The engine stores `current_chapter`, `current_page`, and event history inside
`Project.workflow`. Legacy projects without chapters are normalized to one
default chapter from their persisted pages when first used.

## Read-only project status

`project status` loads a persisted Project once and adds `page_readiness` to
its existing response. Entries are ordered by `page_number` and include the
persisted `current_state`, cumulative `unmet_prerequisites`, one
`next_operation`, and `non_execution: true`. A consistent non-terminal Page
uses the command returned by `StateMachine`; an approved Page reports
`NO_OP_TERMINAL`; incomplete persisted evidence reports `NO_OP_BLOCKED`.

The same response includes an immutable `readiness_summary`, derived only from
those inspections across all Project pages (including pages outside chapters):

- `completed_page_count`: inspections reporting `NO_OP_TERMINAL`.
- `actionable_page_count`: inspections reporting an existing StateMachine command.
- `blocked_page_count`: inspections reporting `NO_OP_BLOCKED`.
- `next_actionable_page_number`: the smallest actionable `page_number`, or `null`.
- `next_actionable_page`: that same Page's existing `page_readiness` inspection,
  including its state, operation, prerequisites, and `non_execution: true`; or
  `null` when no Page is actionable. Its `page_number` matches
  `next_actionable_page_number`.
- `first_blocked_page`: when no Page is actionable, the lowest-numbered blocked
  inspection, including its existing unmet prerequisites; otherwise `null`.
- `readiness_outcome`: `EMPTY` for zero pages; otherwise `ACTIONABLE` if any
  Page is actionable, `BLOCKED` if none is actionable and any Page is blocked,
  or `COMPLETE` when all pages are terminal. `ACTIONABLE` takes priority over
  `BLOCKED`, and completed-plus-blocked projects remain `BLOCKED`.
- `readiness_focus_page`: the existing `next_actionable_page` for `ACTIONABLE`,
  the existing `first_blocked_page` for `BLOCKED`, or `null` for `EMPTY` and
  `COMPLETE`. This is only a projection of the outcome and existing pointers;
  it introduces no precedence or readiness decision.

The three counts partition all inspected pages. An empty Project has zero counts
and a `null` next page; an approved Page with missing evidence remains blocked.
The blocked-page pointer is derived directly from the ordered inspections and
does not change `current_page` or create a new readiness decision.
This summary does not change `current_page`, which may identify a blocked page
under the existing chapter-position rules. Other ProjectContext operations leave
`readiness_summary` as `null` when readiness has not been inspected. The summary
is response-only and is never added to the persisted Project.
The optional `next_actionable_page` field defaults to `None` for existing summary
construction. It projects the first actionable ordered inspection without
introducing a readiness decision or authorizing execution. Generic and LocalFile
status, CLI `project status`, and MCP `get_project_status` expose the same summary.
The additive optional `readiness_outcome` field defaults to `None` for existing
summary construction. Status always sets one of its four values from the existing
inspections/counts; it does not authorize execution or change counts, pointers,
Page ordering, or persistence.
The additive optional `readiness_focus_page` also defaults to `None` when omitted
from existing summary construction. It adds no execution authorization,
persistence, Provider construction, command, or tool.

To preserve V6-compatible status semantics, this query may normalize the
returned Project/status view in memory for legacy projects; it never saves that
normalization or otherwise persists data, emits events, performs a state
transition, runs a workflow step, or constructs image or Provider
infrastructure.

## CLI

```bash
manga-director project run PROJECT_ID
manga-director project resume PROJECT_ID
manga-director project status PROJECT_ID
```

`run` and `resume` are equivalent sequential scheduling operations. They never
call an Agent directly and never bypass `WorkflowEngine`.

## Events

- `ProjectStarted` is emitted once when a Project workflow first starts.
- `ProjectCompleted` is emitted once only after every Page in every Chapter is
  explicitly `Approved`.
