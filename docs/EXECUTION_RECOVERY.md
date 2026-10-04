# Execution Recovery

Execution Recovery provides local diagnostics and a human-review recovery plan.
It never retries, restores state, resumes a session, repairs an artifact, or
changes workflow state.

| DTO | Purpose | Disabled boundary |
| --- | --- | --- |
| `FailureDetectionDTO` | Reports local evidence such as missing storyboard data. | Active monitoring and persistence. |
| `RecoveryPlanDTO` | Recommends human review. | Recovery execution. |
| `RetryStrategyDTO` | Sets the automatic retry limit to zero. | Retry and policy enforcement. |
| `RecoveryResultDTO` | Records a denied-by-default result. | Restoration, transition, or persistence. |
| `RecoverySummary` | Counts diagnostic signals only. | Automatic remediation. |

Recovery is never a path around storyboard, quality-review, approval, or
StateMachine requirements.
