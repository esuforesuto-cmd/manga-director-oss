# v2 Delivery API and Web UI Design

## REST API (FastAPI target)

FastAPI is a future delivery adapter, not a domain dependency. It maps HTTP requests to application commands and serializes typed results/errors. Endpoint handlers never call agents directly and never calculate state transitions.

| Resource / operation | Planned method and path | Application action |
| --- | --- | --- |
| projects | `POST /v2/projects`, `GET /v2/projects/{id}` | create/read project |
| chapters | `POST /v2/projects/{id}/chapters` | add/manage chapter plan |
| pages | `GET /v2/projects/{id}/pages/{number}` | read page and workflow status |
| page step | `POST /v2/projects/{id}/pages/{number}/commands/{command}` | call page `WorkflowEngine` |
| run | `POST /v2/projects/{id}/pages/{number}/run` | run only through quality |
| approval | `POST /v2/projects/{id}/pages/{number}/approve` | explicit human approval command |
| batches | `POST /v2/projects/{id}/batches`, `GET /v2/batches/{id}` | submit/read batch plan |
| artifacts/events | `GET /v2/projects/{id}/events` | read audit trail with filters |

Commands include a request ID, idempotency key, expected page revision, actor, and optional policy/template/provider references. A transition conflict returns `409`; invalid input `422`; missing resources `404`; authorization failure `403`; and unhandled adapter failures a documented typed `5xx` response. Error bodies contain a stable code, message, correlation ID, and safe details.

Authentication, authorization roles, rate limits, and tenant boundaries require a dedicated security design before the API is implemented. They are not implied by this endpoint map.

## MCP server target

An MCP server is another delivery adapter over the same application services. Planned tools are:

- `design_page`
- `review_page`
- `storyboard`
- `build_prompt`
- `generate`
- `quality`
- `approve`

Each tool requires a project/page identity and expected revision, returns a workflow result plus artifact references, and respects the same error and approval rules as CLI/REST. `approve` requires an explicit human actor context. MCP resources may expose read-only project, page, template, and event views. The server has no direct repository mutation or agent invocation path.

## Web UI target (React or Next.js)

The UI consumes REST/MCP-compatible application views; it does not embed workflow logic. Planned screens are:

| Screen | Primary information / action |
| --- | --- |
| Project dashboard | project health, chapter progress, batch status, recent activity |
| Chapter board | ordered pages, dependencies, continuity warnings, readiness |
| Page workspace | current state, artifacts, one eligible command, event/history timeline |
| Storyboard and prompt review | panel-level artifact inspection, template/provenance, warnings |
| Quality and approval | scorecard, evidence, explicit human approval control |
| Batch monitor | queued/running/completed/failed items, concurrency and retry status |
| Settings | repository/provider/template/plugin configuration references; never raw secrets |

Disabled controls are explanatory: a UI tells the user which prerequisite is missing, but enforcement remains server-side. Every mutation uses an expected revision and idempotency key to prevent duplicate submissions.
