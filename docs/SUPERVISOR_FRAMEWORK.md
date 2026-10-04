# Supervisor Framework Design

## Purpose

The proposed Supervisor is a bounded monitor and escalation coordinator. It is
not an approval authority, workflow engine, recovery executor, or autonomous
agent controller.

| Component | Proposed responsibility | Must not do |
| --- | --- | --- |
| Supervisor Agent | Compare local evidence to policy and checkpoints. | Dispatch, transition, approve, or mutate. |
| Progress Monitor | Report bounded progress and stale checkpoint signals. | Extend budgets or continue work autonomously. |
| Failure Detection | Classify missing evidence, timeout, policy, or integrity risks. | Diagnose remote systems or auto-remediate. |
| Recovery Strategy | Recommend pause, human review, or discard/restart paths. | Retry, recover, or repair automatically. |
| Human Escalation | Produce a decision packet with context and rationale. | Send external notifications without explicit integration. |

All future supervisor observations must remain explainable, attributable, and
scoped to one Page execution session.
