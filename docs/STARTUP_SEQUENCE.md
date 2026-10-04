# Startup Sequence

The production startup sequence is a read-only application operation:

```text
Configuration governance -> dependency probes -> provider warmup -> backend warmup -> StartupReport
```

1. Read a redacted configuration-governance mapping from the application.
2. Execute injected local dependency checks and record one `DependencyCheck` per boundary.
3. Initialize and health-refresh the Provider runtime. This is construction and metadata only.
4. Initialize and health-refresh the Image Backend runtime. This does not generate an image.
5. Emit a `StartupReport` and startup metrics.

The sequence is idempotent per `ProductionRuntime` instance. It does not create
or load a Project, execute a Page, publish a workflow event, select a provider,
or bypass the StateMachine.

## Readiness and liveness

- **Liveness** is process-local and answers whether the application runtime can respond.
- **Readiness** requires configuration integrity, passing injected dependencies,
  and healthy local adapter warmups.

Use readiness for admission decisions and health reporting. Keep real network
probes in an adapter-specific future implementation; they are deliberately not
performed by this v2.4 runtime.
