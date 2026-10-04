# v4.7 Final Decision Platform End-to-End Regression

The final integration projection retains the RC1 review sequence:

```text
Project -> Decision -> Recommendation -> Review -> Approval -> Dashboard
        -> Governance / Audit / Compliance -> Reliability -> Save / Reload
        -> Reporting -> Diagnostics -> MCP -> Web UI
```

It confirms one persisted-storyboard page survives save/reload and that all
v4.7 reports remain non-executing. The StateMachine continues to enforce all
mandatory workflow invariants; no Decision Platform report selects, approves,
transitions, or executes work.

See [the compatibility record](COMPATIBILITY_V4_7.md).
