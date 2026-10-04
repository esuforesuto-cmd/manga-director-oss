# REST API Client

The TypeScript REST client groups calls by resource:

- `api.health`
- `api.projects`
- `api.chapters`
- `api.pages`
- `api.workflow`

It centralizes JSON handling, error conversion, identifier encoding, and the
configured API base URL. Components call methods such as
`api.projects.resume(projectId)` or
`api.workflow.execute(projectId, pageNumber, action, metadata)` rather than using
`fetch` themselves.

Any separately compatible HTTP application remains the authority for request
validation and workflow legality. `ApiClientError` carries HTTP status and the
safe API error DTO so the UI can show useful messages without interpreting
Domain exceptions. A FastAPI service is not shipped in this source baseline.
