# Unified Creative Context Foundation

`UnifiedCreativeContextDTO` begins context consolidation by normalizing four
explicit reference domains: Workspace, Knowledge, Agent, and Production.
References retain their source module, source reference, and freshness label;
the factory never loads, fetches, merges, persists, or mutates owner data.

Only one supplied reference for each domain is permitted in a unified context.
This prevents an implicit selection or merge policy from becoming a hidden
source of truth. Workflow-scoped contexts retain exactly one Page reference and
the current StateMachine state.

