# Conflict Resolution Foundation

Conflict DTOs capture a possible conflict record, a human-review resolution
strategy, an unapplied merge result, and an unrecorded decision. They provide a
common presentation-neutral vocabulary without resolving or retaining a
conflict.

`V41OrchestrationService.conflict_resolution()` returns local placeholder
evidence for the supplied page. It neither detects remote state nor merges
creative content.

## Safety boundary

- Automatic conflict resolution is disabled.
- Merge application, content mutation, decision recording, and persistence are
  disabled.
- Human review is explicitly required before any separate future action.
