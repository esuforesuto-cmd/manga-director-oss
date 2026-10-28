# Workflow HTTP API

The optional Workflow FastAPI adapter connects the independent Web UI to the
existing Application, WorkflowEngine, and StateMachine boundaries.

```bash
python -m pip install -e ".[api]"
manga-director api serve
```

The command always binds to `127.0.0.1` and defaults to port `8000`. CORS allows
only `http://127.0.0.1:3000` and `http://localhost:3000`. It provides no remote
transport, authentication, background worker, automatic retry, or automatic
approval.

## Initial routes

- `GET /health`
- `GET /projects`
- `POST /projects`
- `GET /projects/{project_id}`
- `POST /projects/{project_id}/run`
- `POST /projects/{project_id}/resume`
- `GET /projects/{project_id}/chapters/{chapter_id}`
- `POST /projects/{project_id}/chapters/{chapter_id}/run`
- `GET /projects/{project_id}/pages/{page_number}`
- `POST /projects/{project_id}/pages/{page_number}/{action}`
- `POST /projects/{project_id}/pages/{page_number}/panel-aware-generation`

The action is one of `design`, `review`, `storyboard`, `dialogue`, `prompt`,
`generate`, `quality`, `continuity`, or `approve`. Dialogue and continuity use
the existing support-operation path. Approval requires a non-empty
`approvedBy` field and a persisted `QualityChecked` Page. DELETE is not part of
the initial server or Web client.

The dedicated panel-aware route is available only when the HTTP app is composed
with the concrete LocalFile repository. It accepts a closed JSON request with
`requestVersion: 1`, `authorizedBy`, a V7-04 validated `checkpointName`, the
supported `layoutProfileId` and `layoutProfileVersion`, and one explicit
ordered rectangle per persisted panel. Rectangles use integer `left`, `top`,
`right`, and `bottom` coordinates in the V7-13 normalized coordinate space.
Unknown fields, duplicate JSON keys, non-canonical route numbers, queries,
oversized bodies, and requests outside the existing local same-origin browser
admission are rejected. The fixed route is registered before `/{action}`;
generic `/generate` remains unchanged.

The request does not accept authorization IDs, attempt IDs, provider settings,
endpoints, credentials, prompts, or workflow graphs. Responses contain only a
bounded `generated` status or a stable error code. The application delegates to
the existing V7-15 Slice 1 activation and its V7-04/V7-13/V7-14 authorities.
It does not retry or fall back after provider start, and it does not approve a
Page automatically. A generated Page retry follows Slice 1's fail-closed
`revision_conflict` behavior when exact read-only replay evidence is not
available.

This local route does not add authentication. CORS and same-origin request
checks constrain browser access but are not proof of user identity or
authorization. The current HTTP server remains bound to loopback; do not treat
this route as safe for remote exposure or as resolving the existing
authentication gap.

Responses use dedicated camelCase HTTP DTOs. Expected errors are safe JSON:
not found is 404, duplicates and invalid transitions are 409, invalid input is
422, and unexpected failures are a generic 500 without internal paths,
tracebacks, prompts, or credentials.

GET routes do not save Repository data, transition workflow state, run Agents,
or construct Providers. MCP retains its existing import and call contracts but
uses the same neutral Workflow Application Service as HTTP.
