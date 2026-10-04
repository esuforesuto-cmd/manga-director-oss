# Operational Insights

## Scope

`operational_insights()` translates the v4.8 Foundation's explicit unknown
signals into human-review insight DTOs. It makes missing evidence visible
without collecting, probing, or inferring operational data.

## Output

`OperationalInsightsReport` includes six domain insights for Workspace, Agent
Platform, Knowledge, Production, Enterprise, and Decision. Every initial
insight has `evidence_missing=True` and `human_review_required=True`, so the
report communicates uncertainty rather than manufacturing a health score.

## Non-operational guarantee

No telemetry is collected; no system is probed; no dashboard is published; and
no monitor, alert, schedule, policy, recommendation, approval, retry,
recovery, Workflow change, Agent action, Provider call, or external request is
performed. Existing operations and delivery surfaces remain unchanged.
