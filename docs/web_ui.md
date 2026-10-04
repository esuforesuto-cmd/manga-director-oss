# Web UI

The minimal Web UI lives in `web/` as a separate Next.js TypeScript App Router
application. It is a Presentation Layer only:

```text
Web UI -> REST API Client -> compatible HTTP application -> Application Service -> WorkflowEngine
```

The UI never imports Python Domain, Repository, Agent, MCP, or workflow code.
All production state validation remains in the API and existing workflow.

## Run locally

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

`NEXT_PUBLIC_MANGA_DIRECTOR_API_URL` must be an HTTP(S) URL for a separately
compatible HTTP service. The client encodes route identifiers and displays API
errors without rendering HTML from responses. FastAPI/OpenAPI is a future
delivery adapter, not a shipped RC1 service.

## Implemented views

- Project List with ID, title, state, updated time, and progress
- Project Detail with chapters, workflow history, run, and resume controls
- Chapter Detail with page state, quality, and approval status
- Page Workflow view with artifacts, messages, errors, execution time, and
  API-provided available actions
- Approval form shown only when the API provides `approvalRequired`
- Loading, empty, not-found, and error-boundary states

The initial layout is responsive and uses semantic headings, labels, tables,
keyboard-visible focus, and `aria-live` status/error regions.
