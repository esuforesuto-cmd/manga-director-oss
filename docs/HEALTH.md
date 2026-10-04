# Health

`RuntimeHealth` returns a presentation-independent `RuntimeHealthReport` for
providers, image backends, the repository, workflow readiness, configuration,
plugins, extensions, and the local system boundary. It contains no internal
runtime objects and supports JSON and Markdown rendering.

Use `manga-director health summary` for the complete DTO. `provider check` and
`backend check` only construct local adapters; they never call an AI service or
generate an image. `health check` remains the compact compatibility command.
