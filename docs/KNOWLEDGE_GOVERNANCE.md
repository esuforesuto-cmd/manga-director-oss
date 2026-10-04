# Knowledge Governance

v3.4 Iteration 3 adds immutable governance evidence for Repository-derived
Knowledge. The DTOs describe policy declarations, compliance observations,
audit counts, and a human-owned retention boundary for one existing Project
and Page context.

## Safety boundary

Knowledge Governance does not enforce policies, persist audits, write an index
or relationship, evaluate or apply retention, merge, repair, archive, delete,
or expose metadata values. The existing Knowledge Repository interface remains
unchanged.

## Delivery surfaces

- CLI: `manga-director director knowledge-governance-v34 --project <id>`
- FastAPI: `GET /v3.4/knowledge-governance`
- MCP: `knowledge_governance_v34`

All transports return `KnowledgeGovernanceDashboardDTO` only.

# v3.5 Governance evidence

v3.5 adds transport-neutral, read-only governance DTOs over the existing
Knowledge Graph and Knowledge Analytics reports. `KnowledgePolicyDTO`,
`KnowledgeComplianceDTO`, `KnowledgeAuditReport`, `KnowledgeLifecyclePolicy`,
and `KnowledgeGovernanceSummary` make review boundaries explicit. They neither
persist a graph nor enforce, remediate, or retain a policy decision.

Use `director knowledge-governance-v35 --project <id>` for a local preview,
`GET /v3.5/knowledge-governance` for the FastAPI DTO, or the
`knowledge_governance_v35` MCP tool. A human owns every policy decision.
