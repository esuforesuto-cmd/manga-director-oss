# v2.7.0 AI Director Guide

v2.7 provides AI Director planning, decision traces, strategy analysis,
reliability validation, and dashboards as advisory Application-layer services.
Their outputs help users understand exactly one Page's legal next step,
prerequisites, risks, and readiness.

They never call an Agent, execute a workflow step, transition state, generate
an image, approve a Page, or write Project data. The authoritative path remains
`WorkflowEngine` -> `StateMachine` -> Agent, preserving one-page and
human-approval invariants.
