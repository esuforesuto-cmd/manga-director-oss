# MCP example

The shipped MCP transport is local stdio. Inspect its typed tool contract with:

```text
manga-director mcp tools
```

Then start the server with `manga-director mcp serve`. The server delegates to
the existing application and workflow boundaries; it does not call Agents or
the StateMachine directly. See [MCP Server](../../docs/mcp_server.md).
