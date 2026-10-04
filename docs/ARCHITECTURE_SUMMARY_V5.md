# v5.0.0 Architecture Summary

## One Creative Platform

```text
Existing Python / CLI / FastAPI / REST / MCP / Web UI / SDK contracts
                                |
                  Optional Unified API Surface preview
                                |
 Unified Context -> Dashboard -> Governance / Observability / Reliability
                                |
                      Lifecycle / Developer Experience
                                |
      existing Workspace | Knowledge | Agents | Production | Enterprise | Decision | Ecosystem
                                |
            Project | Repository | WorkflowEngine | StateMachine
```

This is a read-only composition model, not a replacement Runtime or delivery
path. Existing owners and StateMachine validation remain authoritative.

## Final architecture decision

Platform Core stays independent of CLI, MCP, Repository, and FastAPI delivery
modules. Context is caller-supplied; the Unified API and SDK are opt-in;
Runtime Orchestration is a static plan; and Governance, Observability,
Reliability, Lifecycle, and DX reports cannot enforce, monitor, recover,
persist, execute, or act.

