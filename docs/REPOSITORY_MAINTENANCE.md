# Repository Maintenance

`RepositoryMaintenance` adds read-only operations on top of the unchanged
five-method `ProjectRepository` port. A repository implementation does not need
to change to use it.

## Reports

- **Statistics**: Project, Chapter, Page, history-entry, and state counts.
- **Consistency**: existing aggregate integrity self-check results.
- **Cleanup report**: operator-review candidates only; it never deletes data.
- **Large repository summary**: bounded largest-project and history evidence.
- **Maintenance report**: composite JSON/Markdown DTO for operations and CI.

Run integrity checks before a manual resume. Decide on deletion, archival, or
repair through an explicit operator procedure; the maintenance facade never
changes stored Project data.
