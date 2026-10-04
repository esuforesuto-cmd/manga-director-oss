# v4.7 Final Architecture Summary

v4.7 final retains the RC1-reviewed additive Application/Production projection
architecture. `v4_7_decision_foundation`, `v4_7_decision_intelligence`, and
`v4_7_decision_governance` consume caller-supplied DTO evidence only.

Decision Engine, Recommendation Framework, Review Intelligence, Approval
Platform, Executive Dashboard, Governance, Audit, Compliance, and Reliability
remain transport-neutral, exactly-one-page-scoped, and non-executing. No module
depends on API, CLI, MCP, Repository, presentation, workflow execution, or an
external service.

The StateMachine remains authoritative. The one-page, no-stage-skip, persisted
storyboard, completed-quality-review, and manual-approval safeguards are
unchanged. See [the release notes](../RELEASE_V4_7.md).
