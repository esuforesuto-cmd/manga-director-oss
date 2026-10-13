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

Approval has a dedicated call,
`api.workflow.approve(projectId, pageNumber, approvedBy)`, so the human identity
uses the HTTP `approvedBy` field and is never inferred from page state. Project
deletion is intentionally absent from the initial client.

Any separately compatible HTTP application remains the authority for request
validation and workflow legality. `ApiClientError` carries HTTP status and the
safe API error DTO so the UI can show useful messages without interpreting
Domain exceptions. The optional local Workflow FastAPI adapter implements this
contract without exposing Domain DTOs.
