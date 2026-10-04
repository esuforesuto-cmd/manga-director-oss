# v2.6.0 AI Workflow Guide

v2.6 provides planning, analysis, reliability, Provider Orchestration, and
Provider Governance as advisory Application-layer services. Their outputs help
users understand a single-page workflow, capability fit, estimated cost or
latency, critical paths, risks, and readiness.

They never call an Agent, execute a workflow step, transition state, generate
an image, approve a Page, or write Project data. The authoritative path remains
`WorkflowEngine` -> `StateMachine` -> Agent, preserving the one-page and
human-approval invariants.
