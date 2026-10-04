# Creative Review

`V31InsightsService` provides an advisory Creative Review DTO for exactly one
existing Page context. It reports the existing storyboard, quality, and human
approval guard evidence as a checklist, findings, recommendation, report, and
summary.

The review is diagnostic only. It cannot run a review Agent, complete quality,
approve a Page, change StateMachine state, or alter an artifact. A recommendation
of `human_review_required` is never an approval.

## Delivery

- CLI: `manga-director director creative-review --project <id> --page <n>`
- FastAPI: `GET /v3.1/creative-review`
- MCP: `creative_review`

See [the example](../examples/creative_review/run.py).
