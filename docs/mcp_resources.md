# MCP Resources

Resources are read-only JSON views over persisted Project data.

- `manga://projects`
- `manga://projects/{project_id}`
- `manga://projects/{project_id}/status`
- `manga://projects/{project_id}/chapters/{chapter_id}`
- `manga://projects/{project_id}/chapters/{chapter_id}/pages/{page_number}`
- `manga://projects/{project_id}/history`

Resource reads use the same repository port as the Application Service. They do
not execute agents, perform state transitions, or change stored data.

```bash
manga-director mcp resources
```
