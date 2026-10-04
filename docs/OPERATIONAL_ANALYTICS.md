# Operational Analytics

Operational analytics converts supplied or local bounded observations into
workflow, Repository, Provider, performance, and operations trends. It does
not begin a collector, save trend history, schedule maintenance, or execute
automation. A trend is an immutable DTO with supplied values, latest value, and
direction (`up`, `down`, or `stable`).

`AnalyticsService` also builds executive reports for workflow, Provider, and
operations review. Recommendations remain descriptive. The executive DTO sets
`automatic_action_taken` to `false` by design.

```bash
manga-director analytics operations PROJECT PAGE
manga-director analytics executive PROJECT PAGE
```

