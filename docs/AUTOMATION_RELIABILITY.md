# Automation Reliability

Automation Reliability describes confidence in preview metadata. It converts
local observations into `metadata_valid` or `metadata_attention_required`
components and makes its non-operational limits explicit.

No health check, retry, recovery, reconfiguration, repair, or automatic action
is attempted. A reliability report therefore never changes workflow state or
substitutes for the StateMachine and completed human quality review.
