# Sequential Batch Guide

Batch execution remains sequential. `ParallelExecution` and `AutoExecution`
are non-executable placeholders.

## Read progress safely

`ExecutionResult` and persisted `BatchRecord` now include:

- `statistics`: total, completed, failed, skipped, attempts, and elapsed time.
- `progress`: total, completed, current page, and next page.
- `checkpoint`: completed page numbers and the next resumable page.
- `retry_summary`: latest failed-page retry count and requeued pages.

These additions are additive. Existing consumers of `completed`, `failed`,
`skipped`, `logs`, and `status` continue to work unchanged.

## Resume and retry

`resume` processes only pending work. Completed queue items remain immutable.
`retry` requeues failed pages only; it does not re-run completed pages. Use the
checkpoint for UI/operations visibility, not as a replacement for repository
state.

See [Large Project Guide](LARGE_PROJECT_GUIDE.md) for storage guidance.
