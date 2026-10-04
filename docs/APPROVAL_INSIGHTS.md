# Approval Insights

`V47DecisionIntelligenceService.approval_insights()` exposes immutable insight
DTOs for prerequisite, escalation, and override-rationale readiness. It retains
exactly-one-page scope, StateMachine authority, persisted-storyboard,
completed-quality-review, and manual human-approval requirements.

It cannot authenticate a user, grant access, enforce policy, submit/grant an
approval, grant an override, transition workflow state, skip a stage, or
execute work.
