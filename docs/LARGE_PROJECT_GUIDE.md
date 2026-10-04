# Large Project Guide

## Scope

v2.2 Iteration 1 supports large Projects without changing the Project aggregate,
`ProjectRepository` port, or Page Workflow. A workflow execution still handles
exactly one page.

## Read-side optimization

Built-in repositories expose optional read helpers in addition to the stable
`load`, `save`, `exists`, `delete`, and `list` contract:

- `list_metadata(offset=..., limit=...)` lists small Project records.
- `load_page(project_id, page_number)` reads one Page.
- `load_history(project_id, page_number, offset=..., limit=...)` returns a
  paginated history window.

These methods are optional capabilities, not new requirements for third-party
`ProjectRepository` implementations. Existing callers can continue to use the
original aggregate methods unchanged.

`LocalFileRepository` maintains an atomic metadata index and private per-page
JSON sidecars. This makes page and history reads selective; existing Projects
without sidecars safely fall back to the full aggregate until their next save.
SQLite and PostgreSQL use indexed Project/page records for selective reads.
Full `load()` continues to return the complete, validated Project aggregate for
compatibility.

## Safe operating guidance

1. Use metadata listing for project pickers and dashboards.
2. Load only the Page or history window needed by an operational view.
3. Keep workflow writes through the existing Project/Repository boundary.
4. Use `SequentialExecution`; parallel execution remains unavailable.
5. Measure realistic project fixtures before changing cache, pagination, or
   connection-pool settings.

See [Performance Tuning](PERFORMANCE_TUNING.md) and
[Batch Guide](BATCH_GUIDE.md).
