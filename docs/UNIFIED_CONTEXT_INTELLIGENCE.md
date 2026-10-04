# Unified Context Intelligence

`UnifiedContextIntelligenceService` analyzes only the references already
present in a `UnifiedCreativeContextDTO`. It reports supported-domain coverage,
missing-reference findings, and an advisory recommendation; it does not load,
merge, mutate, persist, or synchronize a Workspace, Knowledge, Agent, or
Production context.

The supported context domains remain Workspace, Knowledge, Agent, and
Production. Full coverage means all were supplied explicitly, not that external
data was fetched or validated.

