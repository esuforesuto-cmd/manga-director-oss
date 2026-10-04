# Health Checks

`HealthMonitor` executes each probe in isolation. `SystemHealthDashboard` is a
transport-neutral DTO containing an aggregate boolean, timestamp, and safe
component details. It can be returned by the CLI, MCP, or a future HTTP adapter
without exposing a Repository, Engine, Plugin, or secret.

```bash
manga-director health check --config config.yaml
manga-director system-summary --config config.yaml
```

The bundled CLI checks configuration, Repository access, local Plugin discovery,
and Extension SDK availability. Notification and Automation are reported as
`not_configured` when no runtime is composed; they do not make a process
unhealthy merely because the optional runtime is absent.

This source baseline has no FastAPI runtime. A future FastAPI adapter should
return `SystemHealthDashboard` from `/health` and `/health/details` rather than
constructing a second health model.
