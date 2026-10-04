# Migration Guide: v5.5 to v5.6

v5.6.0 is additive. No data conversion, configuration change, endpoint
change, CLI migration, MCP migration, Web UI migration, repository-interface
change, or workflow migration is required.

To adopt the optional Manga Production OS reports, construct the existing
`WorkflowContext` for exactly one page and call the corresponding
`manga_director.production` service. Storyboard evidence remains required
before generation; quality evidence and explicit human approval remain required
before export readiness. Omitting the new services preserves current behavior.
