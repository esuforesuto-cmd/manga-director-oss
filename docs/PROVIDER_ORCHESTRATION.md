# Provider Orchestration

Provider orchestration is a planning boundary above existing `LLMProvider` and
`ImageGenerator` protocols. It may inspect registered metadata, capabilities,
health snapshots, aliases, and static configuration, then return an explainable
recommendation DTO.

Candidate planning topics are selection, capability matching, fallback planning,
cost and latency estimation, recommendations, capability caching, and execution
policy. No v2.6 planning item may call a provider, use credentials, change a
Factory registry, hide a Provider name in an Agent, or implement fallback
execution. All estimates require documented inputs and deterministic mocks.
