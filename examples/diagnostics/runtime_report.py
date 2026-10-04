"""Render a transport-neutral runtime diagnostics DTO."""

from manga_director.observability import MetricsRegistry, RuntimeDiagnostics

print(RuntimeDiagnostics(MetricsRegistry()).report(workflow={"healthy": True}).to_markdown())
