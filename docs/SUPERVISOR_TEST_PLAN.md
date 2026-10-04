# Supervisor Test Plan

- Simulate progress, stale checkpoint, failure, and integrity signals locally.
- Verify every supervisor output is an advisory DTO with source evidence.
- Verify high/critical risks produce human escalation or emergency-stop
  recommendations, never automatic remediation.
- Verify supervisor code has no CLI, FastAPI, MCP, Provider, Backend, or
  repository-write dependency.
