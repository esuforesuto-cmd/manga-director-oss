# v2.7.0 Architecture Summary

Domain owns page-workflow invariants. `WorkflowEngine` and `StateMachine`
execute exactly one Page and enforce legal forward-only transitions.
Application services compose ports; Infrastructure implements adapters and
repositories; CLI, FastAPI, MCP, and Web UI remain outer delivery adapters.

The v2.7 Director, Intelligence, and Reliability services stay in
`manga_director.production`. They return read-only DTOs, do not import a
Presentation adapter, do not change Domain state, and do not introduce a Core
dependency on scheduling, provider execution, network, or Cloud services.

The root public API, Repository port, Knowledge boundary, Provider and Image
Backend protocols, Plugin boundary, and Extension SDK boundary remain
unchanged.
