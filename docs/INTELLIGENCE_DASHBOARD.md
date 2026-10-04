# Intelligence Dashboard

v4.6 Iteration 2 adds `IntelligenceDashboardReport`, an immutable composition
of Context Intelligence, Reasoning Engine, Adaptive Workflow Intelligence, and
Cross-Agent Knowledge Sharing reports.

`V46IntelligenceService.intelligence_dashboard()` is transport-neutral and has
no Presentation Layer dependency. It cannot persist or publish a dashboard,
collect telemetry, alert, monitor, enforce a policy, invoke an Agent, or take
an operational action. Existing CLI, FastAPI, MCP, and Web UI contracts remain
unchanged.
