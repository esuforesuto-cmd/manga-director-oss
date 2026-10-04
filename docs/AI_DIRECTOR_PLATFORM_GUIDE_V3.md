# v3.0.0 AI Director Platform Guide

v3.0.0 provides Director goals, planning/execution contexts, sessions,
strategies, public decision traces, reliability validation, and dashboards as
advisory Application-layer services. Their outputs help users understand one
Page's legal next step, prerequisites, risks, governance, and readiness.

They never call an Agent, execute a workflow step, transition state, generate
an image, approve a Page, or write Project data. The authoritative path remains
`WorkflowEngine` -> `StateMachine` -> Agent, preserving one-page and
human-approval invariants.
