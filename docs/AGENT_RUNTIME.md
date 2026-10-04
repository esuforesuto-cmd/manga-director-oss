# Agent Runtime Foundation

The v4.1 runtime foundation exposes a bounded description of an agent session,
context, state, execution request, and execution result. It is deliberately a
preparation API, not an execution runtime.

`V41AgentFoundationService.runtime()` returns an `AgentRuntimeReport` for one
existing `WorkflowContext` and one page reference. The returned request keeps
`execution_enabled=False`; the result keeps `executed=False` and
`workflow_changed=False`.

## Safety boundary

- It does not call an agent, LLM, Provider, Backend, or network transport.
- It does not start a session, retain state, self-improve, or run long-lived work.
- It cannot transition a workflow, persist artifacts, complete quality review,
  or approve a Page.
- The existing StateMachine remains the sole workflow transition authority.
