# UI Workflow

The UI presents the existing production workflow one Page at a time:

```text
Project -> Chapter -> Page -> Workflow step -> Quality review -> Human approval
```

Project and Chapter controls delegate scheduling to the REST API. Page controls
render only actions supplied by the API's `availableActions` DTO. This prevents
the browser from becoming a second state machine.

The approval form is driven by `approvalRequired`, which the API returns only
for an eligible `QualityChecked` Page. It requires the responsible human's name
and submits the existing approval API command. No project, chapter, page, or
batch control can auto-approve.

The Playwright E2E scenario starts a test-only Node Mock API, prepares a
Project through that REST boundary, advances exactly Page 1 through every state
to `QualityChecked`, and submits an explicit human approval. It never contacts
a real FastAPI instance.
