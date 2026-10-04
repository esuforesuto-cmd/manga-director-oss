# MCP Security

The v1 MCP server is intentionally local-only and uses stdio. It has no
authentication or network listener. Do not expose its standard input/output to
untrusted processes.

Security controls in this phase:

- Pydantic validates Tool input shape and required IDs.
- Application Service delegates state validation to the existing workflow.
- Approval requires `QualityChecked` plus explicit human identity.
- Expected errors map to safe structured DTOs; server logs retain diagnostic
  context without logging full prompt text.
- Resources are read-only and Tool execution is one Page at a time.

Not implemented: OAuth, API keys, JWT, HTTP transport, remote MCP, rate limits,
per-user authorization, audit storage, or tool timeout controls.
