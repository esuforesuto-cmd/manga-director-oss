# Supervisor Design Example (v4.2)

This non-executable example describes the information a future supervisor may surface:

| Signal | Advisory output | Human decision |
| --- | --- | --- |
| Checkpoint stale | Pause recommendation and evidence packet. | Resume, discard, or investigate. |
| Policy mismatch | High-risk escalation. | Correct policy or stop. |
| Missing storyboard | Critical-risk stop recommendation. | Restore valid evidence; do not generate. |
| Incomplete quality review | Approval-boundary warning. | Complete review through the existing workflow. |

No action is dispatched, retried, recovered, persisted, or communicated by
this design example. See the [Supervisor Framework](../../docs/SUPERVISOR_FRAMEWORK.md).
