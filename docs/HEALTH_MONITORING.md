# Health Monitoring

`ProductionRuntime.health_report()` composes the existing Runtime Health DTO
with application liveness, startup readiness, and an optional database
dependency check. The report covers:

- application liveness and readiness;
- Provider and Image Backend construction health;
- Repository integrity through the Repository port;
- Workflow and configuration governance health;
- a supplied database dependency result.

The report is transport-neutral and has `to_json()` and `to_markdown()` methods.
It contains no internal model objects, credentials, or network response bodies.

Health monitoring is observational. It cannot transition a Page, retry a
workflow, approve work, or invoke an Agent. A false readiness result should be
handled by the hosting application or deployment platform.
