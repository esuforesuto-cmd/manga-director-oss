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

The action is one of `design`, `review`, `storyboard`, `dialogue`, `prompt`,
`generate`, `quality`, `continuity`, or `approve`. Dialogue and continuity use
the existing support-operation path. Approval requires a non-empty
`approvedBy` field and a persisted `QualityChecked` Page. DELETE is not part of
the initial server or Web client.

Responses use dedicated camelCase HTTP DTOs. Expected errors are safe JSON:
not found is 404, duplicates and invalid transitions are 409, invalid input is
422, and unexpected failures are a generic 500 without internal paths,
tracebacks, prompts, or credentials.

GET routes do not save Repository data, transition workflow state, run Agents,
or construct Providers. MCP retains its existing import and call contracts but
uses the same neutral Workflow Application Service as HTTP.
