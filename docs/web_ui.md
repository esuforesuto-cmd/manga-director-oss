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

## Explicit Storyboard confirmation

The UI is an App Router application under `web/app/`. A Page in `Reviewed`
state shows the Storyboard input panel only when both Page Design and Review
artifacts are present. Enter the details for every panel, inspect the captured
source, then select the confirmation checkbox and choose **Confirm storyboard**.
The confirmation is bound to the displayed Reviewed source, including Page
Design and Review, and requires that deliberate user action.

The browser sends this confirmation to the same-origin server route in the
Pages Router at
`web/pages/api/projects/[projectId]/pages/[pageNumber]/storyboard/confirm.ts`.
That route validates the request and proxies it to the local Workflow API; the
browser does not submit this confirmation directly to that API.

- **Success:** the UI requests a route refresh so you can inspect the saved
  Page. It does not submit the confirmation again automatically.
- **HTTP 409:** the source changed or the Page is no longer eligible for
  confirmation. Reload the latest Page and review its current source. Only
  confirm again if it is still `Reviewed` with Page Design and Review present,
  and the entered panels still match that source.
- **HTTP 404:** reload the Project and inspect its current state; the requested
  Project or Page could not be found.
- **Uncertain result, including HTTP 503:** reload the Page and inspect its
  state before taking another action. Do not repeat the confirmation until you
  have checked whether it was saved.

The API returns HTTP 404 (`not_found`) for a missing Project or Page. A missing
Project is not created by this request, and its Project, committed revision,
prepared revision, and activation sidecars remain absent. Damaged or unavailable
durable state returns HTTP 503 (`activation_unavailable`). The regression test
`test_confirmation_missing_project_page_and_damaged_durability_responses` in
`tests/test_localfile_explicit_storyboard_input.py` covers these outcomes.
