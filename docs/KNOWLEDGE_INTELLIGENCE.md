# Knowledge Intelligence

v3.4 Iteration 2 adds immutable, Repository-derived Knowledge Intelligence
DTOs. They expose catalog, relationship, quality-evidence, coverage, and
recommendation observations for one existing Project and workflow context.

## Safety boundary

The service is analysis-only. It does not persist an index or relationship,
search remotely, resolve dependencies, score or correct knowledge, mutate the
Repository, or apply a recommendation. Metadata values are not exposed.

## Delivery surfaces

- CLI: `manga-director director knowledge-intelligence-v34 --project <id>`
- FastAPI: `GET /v3.4/knowledge-intelligence`
- MCP: `knowledge_intelligence_v34`

Each surface returns the shared `KnowledgeIntelligenceDashboardDTO`; it does
not expose internal Repository models.

## v3.5 Iteration 2

v3.5 adds Knowledge Insight, Coverage, Relationship Analysis, Recommendation,
Health Summary, and Dashboard DTOs over the Unified Knowledge Graph foundation.
They remain Repository-derived and analysis-only: no graph mutation, remote
lookup, persistent coverage, health enforcement, or recommendation application
is possible.

- CLI: `manga-director director knowledge-insights-v35 --project <id>`
- FastAPI: `GET /v3.5/knowledge-insights`
- MCP: `knowledge_insights_v35`
