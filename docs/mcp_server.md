# MCP Server

`manga-director` provides a local Model Context Protocol server over stdio. It
is an Application Layer delivery adapter:

```text
MCP Client -> McpServer -> MangaApplicationService -> WorkflowEngine -> Domain
```

`McpServer` does not import Agents, mutate Domain models directly, or select an
image/LLM provider. Dependencies are injected at the composition root:

- `WorkflowEngine`
- `WorkflowCoordinator`
- `ProjectLoader` and `ProjectRepository`
- resolved configuration and prompt directory

The server supports MCP JSON-RPC methods for initialization, tools, resources,
and prompts. The only transport is line-delimited JSON-RPC via standard input
and output.

```bash
manga-director mcp serve --config config.yaml
```

No HTTP transport, remote server, OAuth, API keys, JWT, GUI, Redis, RabbitMQ,
or Celery is implemented.

## Output DTO

Every Tool call returns `McpToolResult`, never an unwrapped Domain model:

```json
{
  "success": true,
  "operation": "design_page",
  "state": "Designed",
  "data": {},
  "messages": ["design_page completed."],
  "errors": [],
  "metadata": {}
}
```
