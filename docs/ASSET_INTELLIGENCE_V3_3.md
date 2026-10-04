# Asset Intelligence for v3.3

Asset Intelligence reads the existing Repository-derived lifecycle projection
and reports bounded usage, dependencies, consistency evidence, recommendations,
and a deliberately non-authoritative health marker. It exposes identifiers and
counts only; metadata values remain redacted.

No asset archive, version creation, dependency resolution, repair, persistence,
remote lookup, or lifecycle action is performed. Repository access remains
through the existing interface.

Use `director asset-intelligence-v33`, `GET /v3.3/asset-intelligence`, or MCP
`asset_intelligence_v33` for the transport-neutral dashboard DTO.
