# Unified Platform Foundation

v5 adds `manga_director.platform` as an additive composition package. Its
`UnifiedPlatformFoundationService` produces immutable reports around an
existing `WorkflowContext`; it does not replace Workspace, Knowledge, Agents,
Production, Enterprise, Decision, or Ecosystem owners.

The report is always one-Page scoped, keeps the StateMachine authoritative,
records only caller-supplied context references, and cannot persist an
aggregate, transfer source-of-truth ownership, execute work, or take an action.

