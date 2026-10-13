# Frontend Architecture

## Boundaries

`web/lib/api/client.ts` is the only module permitted to call `fetch`. React
components import typed API functions and never construct URLs, infer workflow
states, or call MCP directly.

Types in `web/lib/api/types.ts` represent the intended REST DTO contract. When
the Workflow FastAPI contract changes, these explicit types and its contract
tests must be updated together. They intentionally differ from Python Domain
models: the UI only consumes presentation DTOs.

## State

The minimal application uses React server rendering for server state and local
component state for forms, pending actions, and visible errors. It intentionally
does not add a global state library.

Workflow actions are rendered from `availableActions` supplied by the API. The
UI does not compute legal transitions. A rejected action remains an API error
and is displayed in the originating component.

## Security

- API origin is configured outside source through `MANGA_DIRECTOR_API_URL`.
- The client permits only HTTP(S) API URLs.
- Project and route identifiers are URL-encoded.
- API text is rendered as React text, never injected HTML.
- Prompt text and secrets are never written to browser logs by this UI.
- Project deletion is not present in the initial HTTP or UI surface.
