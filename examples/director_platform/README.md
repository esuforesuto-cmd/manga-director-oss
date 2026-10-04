# Director Platform Planning Example

This v3 design example is intentionally documentation-only. A future Director
Planner receives one Page context, policy, and `StateMachine` evidence, then
returns an advisory goal, legal next-step candidate, assumptions, and decision
trace. A person must choose an existing workflow command to execute anything.

It never calls an Agent, advances state, or proposes more than one Page
execution.
