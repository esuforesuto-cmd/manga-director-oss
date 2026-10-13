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
python -m pip install -e ".[api]"
manga-director api serve

cd web
cp .env.example .env.local
npm install
npm run dev
```

`NEXT_PUBLIC_MANGA_DIRECTOR_API_URL` defaults to `http://127.0.0.1:8000`.
The client encodes route identifiers and displays safe API errors without
rendering HTML from responses. The server permits only the localhost and
127.0.0.1 Web UI origins on port 3000.

## Implemented views

- Project List with ID, title, state, updated time, and progress
- Project Detail with chapters, workflow history, run, and resume controls
- Chapter Detail with page state, quality, and approval status
- Page Workflow view with artifacts, messages, errors, execution time, and
  API-provided available actions
- Approval form shown only when the API provides `approvalRequired`
- No Project deletion control in the initial local Workflow API
- Loading, empty, not-found, and error-boundary states

The initial layout is responsive and uses semantic headings, labels, tables,
keyboard-visible focus, and `aria-live` status/error regions.
