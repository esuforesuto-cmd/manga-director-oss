# Repository Integrity

`ProjectIntegrityChecker` validates project invariants, page histories,
metadata, and workflow snapshot shape. `RepositorySelfCheck` applies those
read-only checks through the unchanged `ProjectRepository` interface and
returns a `RepositoryCheckReport`.

Run `manga-director repository check` for a bounded repository scan, or add
`--project PROJECT_ID` to check one aggregate. A failed check prevents no data
from being read; it provides evidence for a separate repair or recovery action.
