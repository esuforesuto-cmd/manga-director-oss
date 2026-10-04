# Knowledge Reliability

Knowledge Reliability composes an integrity score, consistency validation,
dependency report, lifecycle validation, governance summary, and reliability
report from existing redacted, Repository-port Knowledge analytics.

It neither adds Repository behavior nor writes snapshots, repairs data, exposes
metadata values, or starts an external lookup.

## Delivery

- CLI: `manga-director director knowledge-reliability`
- FastAPI: `GET /v3.1/knowledge-reliability`
- MCP: `knowledge_reliability`

See [the example](../examples/knowledge_reliability/run.py).
