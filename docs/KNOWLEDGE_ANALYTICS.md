# Knowledge Analytics

Knowledge Analytics aggregates bounded counts from the existing
`ProjectRepository`: coverage, usage, relationship metrics, a baseline-only
trend, and an analytics summary. It exposes identifiers and metadata keys only;
metadata values are never returned.

It does not add a Repository method, create an index, persist analytics, collect
external data, or apply a recommendation.

## Delivery

- CLI: `manga-director director knowledge-analytics`
- FastAPI: `GET /v3.1/knowledge-analytics`
- MCP: `knowledge_analytics`

See [the example](../examples/knowledge_analytics/run.py).
