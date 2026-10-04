# Project Hub v1

Project Hub groups unique, caller-supplied `ProjectHubReferenceDTO` records for
portfolio-level planning. It neither loads nor persists projects and never
executes a workflow across projects.

## v6.1 opt-in pagination

`V61ProjectWorkspaceQueryScaleService.project_summary_page()` reuses Project
Hub's existing identifier ordering and duplicate validation before returning a
read-only window. It accepts `offset=0` and `limit=50`; negative offsets and
limits below one are invalid. An empty input or an offset beyond the supplied
snapshot returns an empty page without loading projects or changing Hub
behavior.
