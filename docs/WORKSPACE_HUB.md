# Workspace Hub v1

Workspace Hub accepts caller-supplied `WorkspaceHubReferenceDTO` records and
returns a deterministic, multi-workspace summary. It is a cross-project view,
not a workspace store: it cannot create, persist, or mutate a workspace.

## v6.1 opt-in pagination

`V61ProjectWorkspaceQueryScaleService.workspace_summary_page()` reuses
Workspace Hub's existing identifier ordering and duplicate validation before
returning a read-only window. It accepts `offset=0` and `limit=50`; negative
offsets and limits below one are invalid. An empty input or an offset beyond
the supplied snapshot returns an empty page without loading or mutating a
workspace.
