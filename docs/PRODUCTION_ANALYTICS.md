# Production Analytics

Production Analytics reports counts of supplied artifacts, metadata, events,
and Plugin descriptors together with quality-review and export eligibility. It
uses deterministic evidence counts only.

Analytics are not persisted and do not make a release or publication decision.

## v6.0 Iteration 2 platform analytics

`V60CreativeProductionPlatformIntelligenceService.production_analytics()`
produces deterministic counts for supplied project/workspace references,
knowledge graph nodes and edges, assignments, services, the current Page
state, and quality-review evidence. It generates a report only; it does not
persist metrics, automate a decision, publish, or change workflow state.

This additive projection preserves all v5.x analytics, API, workflow,
repository, CLI, FastAPI, MCP, and Web UI contracts.
