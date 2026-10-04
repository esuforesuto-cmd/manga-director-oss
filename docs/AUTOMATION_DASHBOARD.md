# Automation Dashboard

`AutomationDashboardDTO` is a presentation-neutral payload that combines:

- Automation Intelligence
- Rule Analytics
- Event Processing Intelligence
- Workflow Optimization recommendations

It is available as an opt-in SDK preview and may be adapted by a future CLI,
FastAPI, MCP, or Web UI consumer without changing those existing surfaces. The
DTO contains no command, action, approval, persistence, or delivery operation.

## Human-in-the-loop

The dashboard indicates readiness for human review only when the foundation has
an explicit approval boundary and all evidence checks succeed. It never
approves, executes, or mutates the reviewed workflow.
