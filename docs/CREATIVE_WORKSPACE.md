# Creative Workspace

Creative Workspace adds an analysis-only session, timeline, observed creative
tasks, activity timeline, progress report, and workspace insight report for one
existing Page. It does not create tasks, assign people, persist workspace state,
start a workflow, or grant approval.

`manga-director director creative-workspace --project <id> --page <number>`
returns an immutable DTO. The optional FastAPI and MCP adapters expose the same
DTO through injected providers.

