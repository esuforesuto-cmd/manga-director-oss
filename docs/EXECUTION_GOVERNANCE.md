# Execution Governance

Execution Governance is an advisory policy and risk view. It exposes safety
boundaries but does not enforce policy, accept risk, confirm compliance, or
perform a corrective action.

| DTO | Purpose | Disabled boundary |
| --- | --- | --- |
| `ExecutionPolicyDTO` | Declares human-review and StateMachine-validation actions. | Policy persistence and enforcement. |
| `RiskAssessmentDTO` | Marks local evidence risk and requires human review. | Risk acceptance and retention. |
| `SafetyBoundaryDTO` | States canonical one-Page, storyboard, review, and StateMachine constraints. | Runtime enforcement. |
| `ComplianceReportDTO` | Represents an uncompleted compliance assessment. | Compliance confirmation and persistence. |
| `GovernanceSummary` | Counts advisory policy/boundary evidence. | Automatic action. |

Governance output is never a replacement for domain validation or human
approval.
