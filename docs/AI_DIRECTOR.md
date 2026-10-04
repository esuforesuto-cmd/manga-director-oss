# AI Director Foundation

The v2.7 AI Director is a planning and recommendation boundary in the
Application layer, not an autonomous actor. Candidate work includes Director
Planning, task orchestration, execution strategy, decision traces, execution
preview, recommendation engine, task dependency graph, and planning policy.

Every proposed result must be explainable, deterministic under mock inputs,
and limited to at most one legal next Page step. It must not call an Agent,
schedule a task, choose a live provider, transition state, write a Project,
generate an image, or approve a Page.
