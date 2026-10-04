# v4.7 RC1 Decision Platform End-to-End Regression

The RC integration projection validates this review sequence without executing
a workflow or an external integration:

```text
Project -> Decision Engine -> Recommendation Framework -> Review Intelligence
        -> Approval Platform -> Executive Dashboard -> Governance / Audit
        -> Reliability -> Save / Reload -> Reporting -> Diagnostics -> MCP -> Web UI
```

The check uses one page with a persisted storyboard and confirms that the
storyboard survives repository save/reload. Every v4.7 report explicitly states
that policy persistence/enforcement, decision selection, recommendation
acceptance, review completion, approval, state transition, monitoring, retry,
and recovery are disabled.

The existing StateMachine continues to enforce the workflow invariants:

- exactly one page per execution;
- no skipped stage;
- storyboard persistence before image generation;
- completed quality review before approval; and
- no multi-page generation request.

See [the compatibility record](COMPATIBILITY_V4_7_RC1.md).
