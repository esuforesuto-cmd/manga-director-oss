# Execution Reliability

Execution Reliability provides diagnostic-only failure classification, a
human-review recovery workflow, a zero-retry policy, an unchecked health report,
and a disabled dashboard. It does not monitor, retry, restore, recover,
remediate, persist, or change workflow state.

| DTO | Purpose | Disabled boundary |
| --- | --- | --- |
| `FailureClassificationDTO` | Classifies local missing-evidence signals. | Active detection and automatic remediation. |
| `RecoveryWorkflowDTO` | Recommends human review. | Recovery start or completion. |
| `RetryPolicyDTO` | Establishes zero automatic attempts. | Retry execution or enforcement. |
| `HealthReportDTO` | Represents an unchecked health report. | Health check and remediation. |
| `ReliabilityDashboard` | Declares disabled reliability monitoring. | Monitoring, retry, recovery, and persistence. |

Reliability diagnostics cannot bypass StateMachine, storyboard, quality-review,
or human-approval requirements.
