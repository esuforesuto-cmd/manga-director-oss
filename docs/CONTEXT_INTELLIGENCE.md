# Context Intelligence

v4.6 Iteration 2 adds `ContextIntelligenceReport`, an immutable analysis of
the Unified Creative Context foundation. It exposes supplied reference counts
and unassessed provenance/freshness states for human review.

`V46IntelligenceService.context_intelligence()` cannot collect additional
context, persist a context, inspect a Repository, alter a Project, or take an
automatic action. It remains scoped to exactly one existing Page and retains the
StateMachine-owned workflow boundary.
